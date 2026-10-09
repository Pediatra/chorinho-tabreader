"""Levantamento denso do marcador: qual canal tem marcador, de que cor, e como ele anda.

Medição que motiva este módulo: no arquivo ``iwaki/henze ｜ nocturno - guitar lesson +
tab.mp4`` a amostragem **esparsa** (um ponto a cada 9 s) dava veredito ``erratico`` e
sustentava a afirmação de que o canal ``iwaki`` não tem marcador; a amostragem **densa**
(0,5 s) dá 141 detecções em 241 amostras e veredito ``desliza``. Conferido no quadro
(regra 4 do AGENTS.md): aquele vídeo tem, sim, um **playhead azul** (matiz 102) que
atravessa partitura e tablatura e volta ao início a cada ~21,5 s. Amostrar uma série
periódica de forma esparsa é **aliasing** — foi assim que uma conclusão errada sobreviveu.

O que este módulo mede, por vídeo:

  - a série ``x(t)`` do marcador com passo denso (0,5 s) numa janela de até 120 s
    começando em 55 % da duração (a tablatura costuma aparecer da metade para o fim);
  - o veredito por ``tab.tempo.resumo`` (desliza / salta / parado / lento / erratico /
    sem_marcador), com velocidade, deslocamento total e a distribuição de **matiz** —
    que é a cor do marcador daquele vídeo;
  - ``duvida`` quando a medida não sustenta veredito (amostragem incompleta, poucas
    detecções, banda larga demais, movimento dominado por saltos).

Recorte: ``fr[300:750, :]`` é o **padrão** (o mesmo já usado na medição anterior — trocar
o recorte invalida a comparação, regra 9 do AGENTS.md). A alternativa ``--painel auto``
escolhe a faixa pelo fundo (``tab.painel.candidatos``) antes de amostrar, e foi **medida e
reprovada** no próprio caso disputado: no ``henze`` ela elege a faixa ``base`` (620–1080,
o vídeo das mãos e do braço) e devolve ``sem_marcador`` onde o recorte fixo acha 141
detecções e veredito ``desliza``. Fica como opção, não como padrão. O recorte usado e a via
de leitura (``cv2`` ou ``ffmpeg``) ficam gravados em cada linha.

Uso:
    python -m tab.marcador --canais "sky guitar" iwaki --por-canal 8
    python -m tab.marcador --resumir        # regenera resumo.json a partir dos JSONL
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import time

import cv2
import numpy as np

from .caminhos import SAIDA, acervo
from .cursor import detectar_cursor
from .painel import candidatos, melhor
from .tempo import SALTO_MAX_PX, resumo
from .varredura import Leitor, _ffmpeg_em, canais_e_videos, duracao_s, ja_feitos

#: Passo da amostragem densa, em segundos. Medido: com 9 s de passo o `iwaki/henze` dava
#: `erratico`; com 0,5 s dá `desliza` (a série é periódica de ~21,5 s — aliasing puro).
PASSO_S = 0.5

#: Janela amostrada, em segundos, contada a partir de ``FRAC_INICIO`` da duração.
JANELA_S = 120.0

#: Onde a janela começa (fração da duração). A tablatura aparece da metade para o fim.
FRAC_INICIO = 0.55

#: Recorte vertical padrão do quadro — o mesmo da medição anterior do marcador.
RECORTE_PADRAO = (300, 750)

#: Orçamento de leitura por vídeo, em segundos. O `ffmpeg` gasta ~0,4 s por quadro em
#: AV1 (44 % do acervo); um vídeo que estoure o orçamento vira `duvida`, não trava a fila.
ORCAMENTO_S = 420.0

#: Veredito abaixo disto não é medido, é duvidado.
MIN_DETECCOES = 5

#: Um marcador de execução aparece na maioria dos quadros; série esparsa é suspeita.
COBERTURA_MINIMA = 0.10

#: Banda do marcador medida no acervo: 5 a 7 px. Acima disto é objeto colorido, não cursor.
LARGURA_MAX_MARCADOR_PX = 40.0

#: Amostragem prevista que precisa ser cumprida para o veredito valer.
FRACAO_AMOSTRAGEM_MINIMA = 0.8

#: Faixas de matiz no histograma (OpenCV: matiz 0–179, então 36 faixas de 5 graus).
N_BINS_MATIZ = 36

#: Os vereditos possíveis. `duvida` é a resposta honesta quando a medida não decide.
VEREDITOS = (
    "desliza",
    "salta",
    "parado",
    "lento",
    "erratico",
    "sem_marcador",
    "duvida",
)

#: Canais do levantamento pedido (o `iwaki` é o que estava em contradição com o dono).
CANAIS_PADRAO = (
    "sky guitar",
    "guitar dell ́arte",
    "cifra club",
    "iwaki",
    "violaodecria",
    "shin izumi",
)


def histograma_matiz(matizes: list[int]) -> list[int]:
    """Histograma de matiz das detecções, em ``N_BINS_MATIZ`` faixas de 5 graus.

    Args:
        matizes: matiz (0–179) de cada detecção.

    Returns:
        Lista de contagens, índice = ``matiz // 5``.
    """
    hist = [0] * N_BINS_MATIZ
    for m in matizes:
        i = min(N_BINS_MATIZ - 1, max(0, int(m) // 5))
        hist[i] += 1
    return hist


def mediana_do_histograma(hist: list[int], largura_bin: float = 5.0) -> float | None:
    """Mediana aproximada de um histograma (resolução de meia faixa).

    Args:
        hist: contagens por faixa.
        largura_bin: largura de cada faixa, em graus de matiz.

    Returns:
        O centro da faixa mediana, ou None se o histograma estiver vazio.
    """
    total = sum(hist)
    if total <= 0:
        return None
    alvo = total / 2
    acumulado = 0
    for i, contagem in enumerate(hist):
        acumulado += contagem
        if acumulado >= alvo:
            return i * largura_bin + largura_bin / 2
    return None


def _acumular(
    deteccao: tuple[int, int, tuple[int, int]] | None,
    t_s: float,
    serie: list[tuple[float, int]],
    larguras: list[int],
    matizes: list[int],
) -> None:
    """Guarda uma detecção na série (e nada, quando o quadro não tem banda).

    Args:
        deteccao: ``(x0, x1, (matiz, sat))`` de ``detectar_cursor``, ou None.
        t_s: instante da amostra, em segundos.
        serie: série ``(t, x)`` sendo montada; recebe o centro da banda.
        larguras: larguras da banda sendo montadas; recebe ``x1 - x0 + 1``.
        matizes: matizes das detecções; recebe o matiz mediano da banda.
    """
    if deteccao is None:
        return
    x0, x1, (matiz, _sat) = deteccao
    serie.append((round(t_s, 3), (x0 + x1) // 2))
    larguras.append(x1 - x0 + 1)
    matizes.append(matiz)


def serie_do_video(
    caminho: str,
    t0_s: float,
    n_previstas: int,
    passo_s: float = PASSO_S,
    recorte: tuple[int, int] = RECORTE_PADRAO,
    orcamento_s: float = ORCAMENTO_S,
) -> dict:
    """Monta a série densa ``x(t)`` do marcador, amostra a amostra.

    A leitura é **sequencial** dentro da janela (um quadro a cada ``passo_s``, pulando os
    intermediários com ``grab``), e não por seek a cada amostra: o seek custa ~80 ms por
    amostra no OpenCV. Quando o OpenCV não abre ou não decodifica o arquivo (44 % do
    acervo é AV1), o resto da série é lido pelo ``ffmpeg``, um quadro por vez.

    Args:
        caminho: vídeo.
        t0_s: início da janela, em segundos.
        n_previstas: quantas amostras a janela pede.
        passo_s: passo entre amostras, em segundos.
        recorte: ``(y0, y1)`` do recorte do painel; x é absoluto no quadro.
        orcamento_s: tempo máximo de leitura antes de cortar e devolver o que tem.

    Returns:
        Dicionário com ``serie`` (pontos ``(t, x)``), ``larguras``, ``matizes``, ``via``
        (``cv2``, ``ffmpeg`` ou ``cv2+ffmpeg``), ``n_lidas`` e ``erro``.
    """
    y0, y1 = recorte
    serie: list[tuple[float, int]] = []
    larguras: list[int] = []
    matizes: list[int] = []
    lidas = 0
    via = "cv2"
    erro: str | None = None
    inicio = time.time()

    cap = cv2.VideoCapture(caminho)
    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
        passo_frames = max(1, round(passo_s * fps))
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t0_s) * 1000.0)
            ok, quadro = cap.read()
            while ok and quadro is not None and quadro.size and lidas < n_previstas:
                det = detectar_cursor(quadro[y0:y1, :])
                _acumular(det, t0_s + lidas * passo_s, serie, larguras, matizes)
                lidas += 1
                if time.time() - inicio > orcamento_s:
                    erro = "orcamento_esgotado"
                    break
                for _ in range(passo_frames - 1):
                    if not cap.grab():
                        break
                ok, quadro = cap.read()
    finally:
        cap.release()

    if erro is None and lidas < n_previstas:
        via = "ffmpeg" if lidas == 0 else "cv2+ffmpeg"
        sem_quadro = 0
        for k in range(lidas, n_previstas):
            quadro = _ffmpeg_em(caminho, t0_s + k * passo_s)
            if quadro is None:
                sem_quadro += 1
            det = detectar_cursor(quadro[y0:y1, :]) if quadro is not None else None
            _acumular(det, t0_s + k * passo_s, serie, larguras, matizes)
            if time.time() - inicio > orcamento_s:
                erro = "orcamento_esgotado"
                break
        if sem_quadro and sem_quadro == n_previstas - lidas:
            erro = erro or "sem_quadro"

    return {
        "serie": serie,
        "larguras": larguras,
        "matizes": matizes,
        "via": via,
        "n_lidas": lidas,
        "erro": erro,
    }


def julgar(
    serie: list[tuple[float, int]],
    larguras: list[int],
    matizes: list[int],
    n_lidas: int,
    n_previstas: int,
) -> dict:
    """Veredito do movimento e estatísticas da série, sem tocar em vídeo.

    O veredito bruto é o de ``tab.tempo.resumo``. Ele é rebaixado para ``duvida`` quando a
    medida não sustenta a conclusão — e os motivos são explícitos, não um julgamento
    solto: amostragem incompleta (é o caso que gera aliasing), poucas detecções, banda
    larga demais para ser cursor, ou movimento dominado por saltos grandes.

    Args:
        serie: pontos ``(t, x)`` do marcador.
        larguras: largura, em px, da banda de cada detecção.
        matizes: matiz (0–179) de cada detecção.
        n_lidas: quantas amostras foram medidas de fato.
        n_previstas: quantas amostras a janela pedia.

    Returns:
        Dicionário com ``veredito``, ``veredito_resumo``, ``motivo_duvida``, ``pontos``,
        ``deslocamento_total_px``, ``velocidade_px_s``, ``velocidade_trechos_px_s``,
        ``passo_mediano_px``, ``n_deteccoes``, ``cobertura``, ``n_saltos_grandes``,
        ``frac_passos_grandes``, ``largura_mediana_px``, ``matiz_mediana``, ``matiz_p10``,
        ``matiz_p90`` e ``matiz_hist``.
    """
    r = resumo(serie)
    veredito = r["veredito"]
    motivo: str | None = None
    pares = list(itertools.pairwise(serie))
    grandes = sum(1 for (_, a), (_, b) in pares if abs(b - a) > SALTO_MAX_PX)
    frac_grandes = grandes / len(pares) if pares else 0.0
    # Velocidade DENTRO dos trechos (entre um salto grande e o seguinte). A velocidade do
    # `resumo` é o deslocamento total sobre a janela inteira; em série que volta ao início
    # (o playhead do `henze` reinicia a cada ~21,5 s) ela subestima o passo real — medido
    # 15,8 px/s ali, onde o trecho anda ~60 px/s.
    dentro = [
        abs(b - a) / (tb - ta)
        for (ta, a), (tb, b) in pares
        if abs(b - a) <= SALTO_MAX_PX and tb > ta
    ]
    cobertura = len(serie) / max(1, n_lidas)
    largura_mediana = float(np.median(larguras)) if larguras else 0.0
    if n_previstas and n_lidas < FRACAO_AMOSTRAGEM_MINIMA * n_previstas:
        motivo = "amostragem_incompleta"
    elif veredito in {"desliza", "salta"}:
        if len(serie) < MIN_DETECCOES:
            motivo = "poucas_deteccoes"
        elif cobertura < COBERTURA_MINIMA:
            motivo = "serie_esparsa"
        elif frac_grandes > 0.5:
            motivo = "movimento_dominado_por_saltos"
        elif largura_mediana > LARGURA_MAX_MARCADOR_PX:
            motivo = "banda_larga"
    if motivo is not None:
        veredito = "duvida"
    return {
        "veredito": veredito,
        "veredito_resumo": r["veredito"],
        "motivo_duvida": motivo,
        "pontos": r.get("pontos", 0),
        "deslocamento_total_px": r.get("deslocamento_total_px"),
        "velocidade_px_s": r.get("velocidade_px_s"),
        "velocidade_trechos_px_s": round(float(np.median(dentro)), 1)
        if dentro
        else None,
        "passo_mediano_px": r.get("passo_mediano_px"),
        "n_deteccoes": len(serie),
        "cobertura": round(cobertura, 3),
        "n_saltos_grandes": grandes,
        "frac_passos_grandes": round(frac_grandes, 3),
        "largura_mediana_px": largura_mediana or None,
        "matiz_mediana": float(np.median(matizes)) if matizes else None,
        "matiz_p10": float(np.percentile(matizes, 10)) if matizes else None,
        "matiz_p90": float(np.percentile(matizes, 90)) if matizes else None,
        "matiz_hist": histograma_matiz(matizes),
    }


def medir_video(
    caminho: str,
    raiz: str,
    passo_s: float = PASSO_S,
    janela_s: float = JANELA_S,
    frac_inicio: float = FRAC_INICIO,
    recorte: tuple[int, int] = RECORTE_PADRAO,
    painel: str = "fixo",
    orcamento_s: float = ORCAMENTO_S,
) -> dict:
    """Mede um vídeo e devolve a linha do JSONL (série resumida, não os pontos).

    Args:
        caminho: vídeo.
        raiz: raiz do acervo (para gravar o caminho relativo).
        passo_s: passo entre amostras, em segundos.
        janela_s: tamanho máximo da janela, em segundos.
        frac_inicio: fração da duração onde a janela começa.
        recorte: ``(y0, y1)`` usado quando ``painel`` é ``fixo`` ou quando a escolha
            automática não acha painel.
        painel: ``auto`` escolhe a faixa pelo fundo; ``fixo`` usa ``recorte`` sempre.
        orcamento_s: tempo máximo de leitura antes de cortar a série.

    Returns:
        Dicionário pronto para virar uma linha de JSONL.
    """
    rel = os.path.relpath(caminho, raiz)
    canal = rel.split(os.sep)[0]
    linha: dict = {"canal": canal, "arquivo": rel}
    dur = duracao_s(caminho)
    linha["duracao_s"] = round(dur, 1)
    if dur <= 0:
        linha.update(
            {"veredito": "duvida", "veredito_resumo": None, "erro": "sem_duracao"}
        )
        return linha
    t0 = frac_inicio * dur
    janela = min(janela_s, max(0.0, dur - t0))
    if janela < 5.0:
        linha.update(
            {"veredito": "duvida", "veredito_resumo": None, "erro": "janela_curta"}
        )
        return linha
    n_previstas = int(janela / passo_s) + 1

    nome_painel = None
    if painel == "auto":
        leitor = Leitor(caminho)
        try:
            quadro = leitor.ler(t0)
        finally:
            leitor.fechar()
        if quadro is not None:
            try:
                cand = melhor(candidatos(quadro))
            except Exception:
                cand = None
            if cand is not None:
                recorte = (cand.y0, cand.y1)
                nome_painel = cand.nome

    medida = serie_do_video(caminho, t0, n_previstas, passo_s, recorte, orcamento_s)
    julgamento = julgar(
        medida["serie"],
        medida["larguras"],
        medida["matizes"],
        medida["n_lidas"],
        n_previstas,
    )
    xs = [x for _, x in medida["serie"]]
    linha.update(julgamento)
    linha.update(
        {
            "t_inicio_s": round(t0, 1),
            "janela_s": round(janela, 1),
            "passo_s": passo_s,
            "n_previstas": n_previstas,
            "n_lidas": medida["n_lidas"],
            "via": medida["via"],
            "painel": nome_painel,
            "recorte": [int(recorte[0]), int(recorte[1])],
            "x_min": min(xs) if xs else None,
            "x_max": max(xs) if xs else None,
            "erro": medida["erro"],
        }
    )
    return linha


def amostra_espacada(
    videos: list[str], quantos: int, incluir: list[str] | None = None
) -> list[str]:
    """Seleciona ``quantos`` vídeos espalhados na lista ordenada.

    Espalhar (em vez de pegar os primeiros) evita que a amostra de um canal seja só o
    bloco alfabético inicial — no `sky guitar`, por exemplo, os primeiros arquivos são
    todos do mesmo autor. ``incluir`` força a entrada de um arquivo pelo nome (usado para
    pôr o `henze` do `iwaki` na amostra, que é o caso medido e disputado).

    Args:
        videos: caminhos, em ordem estável.
        quantos: tamanho desejado da amostra.
        incluir: substrings de arquivos que precisam estar na amostra.

    Returns:
        Lista de caminhos, na ordem da entrada.
    """
    if not videos or quantos <= 0:
        return []
    if len(videos) <= quantos:
        escolhidos = list(videos)
    elif quantos == 1:
        escolhidos = [videos[len(videos) // 2]]
    else:
        passo = (len(videos) - 1) / (quantos - 1)
        escolhidos = [videos[round(i * passo)] for i in range(quantos)]
    for sub in incluir or []:
        if any(sub in v for v in escolhidos):
            continue
        achado = next((v for v in videos if sub in v and v not in escolhidos), None)
        if achado is not None:
            escolhidos[-1] = achado
    return escolhidos


def listar_videos(
    raiz: str,
    canais: list[str],
    por_canal: int,
    incluir: list[str] | None = None,
) -> dict[str, list[str]]:
    """Monta a amostra de vídeos por canal.

    Args:
        raiz: raiz do acervo.
        canais: canais desejados.
        por_canal: quantos vídeos por canal.
        incluir: substrings de arquivos que precisam entrar na amostra.

    Returns:
        Dicionário canal -> lista de vídeos.
    """
    achados = canais_e_videos(raiz, list(canais))
    return {c: amostra_espacada(v, por_canal, incluir) for c, v in achados.items()}


def agregar_canal(resultados: list[dict]) -> dict:
    """Agrega os resultados de um canal: contagem por veredito e matiz mediana.

    A matiz do canal sai de dois jeitos, de propósito: ``matiz_mediana_por_video`` é a
    mediana das medianas (um vídeo, um voto — não deixa um vídeo longo dominar) e
    ``matiz_mediana_global`` é a mediana do histograma somado (todas as detecções, com
    resolução de meia faixa de 5 graus).

    Args:
        resultados: linhas medidas do canal (dicts do JSONL).

    Returns:
        Dicionário com ``videos``, ``por_veredito``, ``por_veredito_resumo``,
        ``marcador_utilizavel``, ``n_deteccoes``, ``matiz_mediana_por_video``,
        ``matiz_mediana_global``, ``velocidade_mediana_px_s``,
        ``velocidade_trechos_mediana_px_s`` e ``por_arquivo``.
    """
    por_veredito = dict.fromkeys(VEREDITOS, 0)
    por_veredito_resumo: dict[str, int] = {}
    for r in resultados:
        v = r.get("veredito", "duvida")
        por_veredito[v] = por_veredito.get(v, 0) + 1
        vr = r.get("veredito_resumo")
        if vr:
            por_veredito_resumo[vr] = por_veredito_resumo.get(vr, 0) + 1
    medias = [
        float(r["matiz_mediana"])
        for r in resultados
        if r.get("matiz_mediana") is not None
    ]
    velocidades = [
        float(r["velocidade_px_s"])
        for r in resultados
        if r.get("velocidade_px_s") is not None
    ]
    velocidades_trecho = [
        float(r["velocidade_trechos_px_s"])
        for r in resultados
        if r.get("velocidade_trechos_px_s") is not None
    ]
    hist = [0] * N_BINS_MATIZ
    for r in resultados:
        h = r.get("matiz_hist") or []
        for i, c in enumerate(h[:N_BINS_MATIZ]):
            hist[i] += int(c)
    utilizavel = por_veredito.get("desliza", 0) + por_veredito.get("salta", 0)
    return {
        "videos": len(resultados),
        "por_veredito": por_veredito,
        "por_veredito_resumo": por_veredito_resumo,
        "marcador_utilizavel": utilizavel,
        "n_deteccoes": sum(int(r.get("n_deteccoes") or 0) for r in resultados),
        "matiz_mediana_por_video": float(np.median(medias)) if medias else None,
        "matiz_mediana_global": mediana_do_histograma(hist),
        "velocidade_mediana_px_s": float(np.median(velocidades))
        if velocidades
        else None,
        "velocidade_trechos_mediana_px_s": float(np.median(velocidades_trecho))
        if velocidades_trecho
        else None,
        "por_arquivo": {
            r.get("arquivo", "?"): r.get("veredito", "duvida") for r in resultados
        },
    }


def agregar_canais(por_canal: dict[str, list[dict]]) -> dict:
    """Agrega todos os canais.

    Args:
        por_canal: canal -> linhas medidas.

    Returns:
        Dicionário ``{"canais": ..., "total_videos": ..., "total_utilizavel": ...}``.
    """
    canais = {c: agregar_canal(rs) for c, rs in por_canal.items()}
    return {
        "canais": canais,
        "total_videos": sum(a["videos"] for a in canais.values()),
        "total_utilizavel": sum(a["marcador_utilizavel"] for a in canais.values()),
    }


def ler_jsonl(caminho: str) -> list[dict]:
    """Lê um JSONL de resultados, ignorando linha corrompida.

    Args:
        caminho: arquivo JSONL.

    Returns:
        Lista de dicionários.
    """
    linhas: list[dict] = []
    with open(caminho, encoding="utf-8") as fh:
        for linha in fh:
            try:
                linhas.append(json.loads(linha))
            except json.JSONDecodeError:
                continue
    return linhas


def escrever_resumo(saida: str, canais: list[str] | None = None) -> dict:
    """Relê os JSONL da pasta e grava ``resumo.json``.

    Args:
        saida: pasta com os ``<canal>.jsonl``.
        canais: canais a resumir; None resume todos os JSONL encontrados.

    Returns:
        O documento gravado.
    """
    if canais is None:
        canais = [
            os.path.basename(p)[: -len(".jsonl")]
            for p in sorted(os.listdir(saida))
            if p.endswith(".jsonl")
        ]
    por_canal: dict[str, list[dict]] = {}
    for canal in canais:
        caminho = os.path.join(saida, f"{canal.replace('/', '_')}.jsonl")
        if os.path.exists(caminho):
            por_canal[canal] = ler_jsonl(caminho)
    doc = agregar_canais(por_canal)
    doc["parametros"] = {
        "passo_s": PASSO_S,
        "janela_s": JANELA_S,
        "frac_inicio": FRAC_INICIO,
        "recorte_fixo": list(RECORTE_PADRAO),
        "n_bins_matiz": N_BINS_MATIZ,
        "min_deteccoes": MIN_DETECCOES,
        "cobertura_minima": COBERTURA_MINIMA,
        "largura_max_marcador_px": LARGURA_MAX_MARCADOR_PX,
    }
    with open(os.path.join(saida, "resumo.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    return doc


def tabela_texto(canais: dict[str, dict]) -> str:
    """Tabela legível do resumo por canal.

    Args:
        canais: campo ``canais`` do resumo.

    Returns:
        Texto pronto para imprimir.
    """
    largura_veredito = 8
    cabecalho = f"{'canal':<20}" + "".join(
        f"{v[: largura_veredito - 3]:>{largura_veredito}}" for v in VEREDITOS
    )
    cabecalho += f"{'util':>6}{'matiz':>8}"
    linhas = [cabecalho]
    for canal, ag in canais.items():
        contagens = ag.get("por_veredito", {})
        matiz = ag.get("matiz_mediana_global")
        if matiz is None:
            matiz = ag.get("matiz_mediana_por_video")
        linha = f"{canal[:19]:<20}" + "".join(
            f"{contagens.get(v, 0):>{largura_veredito}}" for v in VEREDITOS
        )
        linha += f"{ag.get('marcador_utilizavel', 0):>6}"
        linha += f"{matiz:>8.0f}" if matiz is not None else f"{'-':>8}"
        linhas.append(linha)
    return "\n".join(linhas)


def main() -> int:
    """Faz o levantamento denso do marcador nos canais pedidos.

    Returns:
        0 em sucesso; 1 se nenhum canal foi lido.
    """
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raiz", default=str(acervo()))
    ap.add_argument("--saida", default=str(SAIDA / "marcador"))
    ap.add_argument("--canais", nargs="*", default=None)
    ap.add_argument("--por-canal", type=int, default=8)
    ap.add_argument("--passo", type=float, default=PASSO_S)
    ap.add_argument("--janela", type=float, default=JANELA_S)
    ap.add_argument("--frac-inicio", type=float, default=FRAC_INICIO)
    ap.add_argument("--painel", choices=["auto", "fixo"], default="fixo")
    ap.add_argument("--orcamento-s", type=float, default=ORCAMENTO_S)
    ap.add_argument(
        "--incluir",
        nargs="*",
        default=None,
        help="substrings de arquivos que precisam entrar na amostra de cada canal",
    )
    ap.add_argument(
        "--refazer", action="store_true", help="ignora o que já está no JSONL"
    )
    ap.add_argument("--resumir", action="store_true", help="só regrava resumo.json")
    ap.add_argument("--max-segundos", type=float, default=0.0)
    args = ap.parse_args()

    os.makedirs(args.saida, exist_ok=True)
    if args.resumir:
        doc = escrever_resumo(args.saida, args.canais)
        print(tabela_texto(doc["canais"]))
        return 0

    canais = listar_videos(
        args.raiz,
        args.canais or list(CANAIS_PADRAO),
        args.por_canal,
        args.incluir,
    )
    print(
        f"canais: {len(canais)} | vídeos: {sum(len(v) for v in canais.values())} | "
        f"passo: {args.passo}s | janela: {args.janela}s | painel: {args.painel}",
        flush=True,
    )
    inicio = time.time()
    processados = 0
    for canal, videos in canais.items():
        destino = os.path.join(args.saida, f"{canal.replace('/', '_')}.jsonl")
        prontos = set() if args.refazer else ja_feitos(destino)
        pendentes = [v for v in videos if os.path.relpath(v, args.raiz) not in prontos]
        print(
            f"\n=== {canal}: {len(videos)} na amostra, {len(prontos)} já feitos, "
            f"{len(pendentes)} pendentes",
            flush=True,
        )
        if not pendentes:
            continue
        with open(destino, "a", encoding="utf-8") as fh:
            for i, video in enumerate(pendentes, 1):
                if args.max_segundos and time.time() - inicio > args.max_segundos:
                    print("tempo esgotado; retome rodando de novo", flush=True)
                    escrever_resumo(args.saida, list(canais))
                    return 0
                t_video = time.time()
                try:
                    linha = medir_video(
                        video,
                        args.raiz,
                        args.passo,
                        args.janela,
                        args.frac_inicio,
                        RECORTE_PADRAO,
                        args.painel,
                        args.orcamento_s,
                    )
                except Exception as exc:
                    linha = {
                        "canal": canal,
                        "arquivo": os.path.relpath(video, args.raiz),
                        "veredito": "duvida",
                        "veredito_resumo": None,
                        "erro": f"{type(exc).__name__}: {exc}",
                    }
                fh.write(json.dumps(linha, ensure_ascii=False) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
                processados += 1
                print(
                    f"  [{i}/{len(pendentes)}] {os.path.basename(video)[:40]:<40} "
                    f"{linha.get('veredito')} n={linha.get('n_deteccoes')}"
                    f"/{linha.get('n_lidas')} via={linha.get('via')} "
                    f"matiz={linha.get('matiz_mediana')} "
                    f"{time.time() - t_video:.0f}s",
                    flush=True,
                )
    doc = escrever_resumo(args.saida, list(canais))
    print(
        f"\n{processados} vídeos em {(time.time() - inicio) / 60:.1f} min", flush=True
    )
    print(tabela_texto(doc["canais"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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

Recorte: **dois** por vídeo, porque um só dá falso negativo — medido, não suposto:

  - ``painel`` = y colado no sistema de cordas do painel escolhido (``tab.painel.escolher``
    + ``tab.pipeline.roi_das_cordas``), com x no quadro inteiro. **É o método.** Ele é que
    pega o playhead da **altura da tablatura**: no `sky guitar` (`aguado`) o recorte fixo
    tem 450 px e o portão de altura do detector exige banda de 225 px, então a faixa azul
    (~140 px) é **rejeitada** e o detector cai no objeto colorido mais cheio — o corpo do
    violão e a mão (matiz 17) — e o veredito sai ``erratico``. Com o recorte do painel
    (y = 118–347) a mesma série vira ``salta``, matiz 109, com a escada de patamares que a
    rodada 1 descreveu;
  - ``fixo`` = ``fr[300:750, :]``, o da medição ANTERIOR, medido junto só para a comparação
    antes/depois (trocar o recorte invalida a comparação, regra 9 do AGENTS.md). Não
    responde pelo vídeo.

O veredito do vídeo é o do recorte do painel. Quando não há painel no instante amostrado,
o veredito é ``sem_painel`` — que **não** é ``sem_marcador``: ali não se sabe se há
marcador, aqui se sabe que não há. O painel é escolhido uma vez por vídeo (meio da janela;
se não houver, o início), e o instante fica gravado.

A via de leitura (``cv2`` ou ``ffmpeg``) fica gravada em cada linha, e o ``ffmpeg``
decodifica a janela **uma vez** para os dois recortes.

Uso:
    python -m tab.marcador --canais "sky guitar" iwaki --por-canal 8
    python -m tab.marcador --resumir        # regenera resumo.json a partir dos JSONL
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import subprocess
import time

import numpy as np

from tab.comum import leitor
from tab.comum.caminhos import SAIDA, acervo
from tab.tablatura.censo.varredura import (
    Leitor,
    _ffmpeg_em,
    canais_e_videos,
    duracao_s,
    ja_feitos,
)
from tab.tablatura.leitura.cursor import detectar_cursor
from tab.tablatura.leitura.painel import escolher
from tab.tablatura.produto.pipeline import roi_das_cordas
from tab.tablatura.produto.tempo import SALTO_MAX_PX, resumo

#: Passo da amostragem densa, em segundos. Medido: com 9 s de passo o `iwaki/henze` dava
#: `erratico`; com 0,5 s dá `desliza` (a série é periódica de ~21,5 s — aliasing puro).
PASSO_S = 0.5

#: Janela amostrada, em segundos, contada a partir de ``FRAC_INICIO`` da duração.
JANELA_S = 120.0

#: Onde a janela começa (fração da duração). A tablatura aparece da metade para o fim.
FRAC_INICIO = 0.55

#: Recorte vertical fixo do quadro — o da medição ANTERIOR, mantido só para comparação.
RECORTE_PADRAO = (300, 750)

#: Os dois recortes medidos por vídeo: o do painel (método) e o fixo (antes/depois).
CROP_PAINEL = "painel"
CROP_FIXO = "fixo"

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

#: Cobertura mínima para dizer que há BANDA no recorte (não que a série seja invertível).
#: É o que separa `sky guitar` 3/8 utilizável de 8/8 com banda visível: ali a banda azul
#: aparece em ~90 % das amostras, mas a série não tem sentido único — o detector alterna
#: entre duas bandas azuis do MESMO recorte (medido: 89 saltos grandes em 154 passos).
COBERTURA_VISIVEL = 0.6

#: Faixas de matiz no histograma (OpenCV: matiz 0–179, então 36 faixas de 5 graus).
N_BINS_MATIZ = 36

#: Os vereditos possíveis. `duvida` é a resposta honesta quando a medida não decide, e
#: `sem_painel` quando nem houve painel para medir (não é o mesmo que "sem marcador").
VEREDITOS = (
    "desliza",
    "salta",
    "parado",
    "lento",
    "erratico",
    "sem_marcador",
    "sem_painel",
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


def _montar(
    deteccao: tuple[int, int, tuple[int, int]] | None, t_s: float
) -> tuple[float, int, int, int] | None:
    """Uma amostra do marcador (instante, centro, largura, matiz), ou None.

    Args:
        deteccao: ``(x0, x1, (matiz, sat))`` de ``detectar_cursor``, ou None.
        t_s: instante da amostra, em segundos.

    Returns:
        ``(t, x, largura, matiz)`` com ``x`` no centro da banda, ou None se o quadro não
        tem banda nenhuma.
    """
    if deteccao is None:
        return None
    x0, x1, (matiz, _sat) = deteccao
    return (round(t_s, 3), (x0 + x1) // 2, x1 - x0 + 1, matiz)


def _separar(
    amostras: list[tuple[float, int, int, int] | None],
) -> tuple[list[tuple[float, int]], list[int], list[int]]:
    """Separa as amostras em série, larguras e matizes, descartando os quadros sem banda.

    Args:
        amostras: amostras como saem de ``_montar``.

    Returns:
        ``(serie, larguras, matizes)``.
    """
    boas = [a for a in amostras if a is not None]
    return (
        [(t, x) for t, x, _l, _m in boas],
        [largura for _t, _x, largura, _m in boas],
        [matiz for _t, _x, _l, matiz in boas],
    )


def _dimensoes(caminho: str) -> tuple[int, int] | None:
    """Largura e altura do primeiro stream de vídeo, por ``ffprobe``.

    Args:
        caminho: vídeo.

    Returns:
        ``(largura, altura)`` ou None se o ``ffprobe`` não responder.
    """
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "csv=p=0",
                caminho,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        largura, altura = proc.stdout.strip().splitlines()[0].split(",")[:2]
        return int(largura), int(altura)
    except Exception:
        return None


def _amostrar_cv2(
    caminho: str,
    t0_s: float,
    n: int,
    passo_s: float,
    recortes: list[tuple[str, tuple[int, int]]],
    orcamento_s: float,
    inicio: float,
) -> tuple[dict[str, list[tuple[float, int, int, int] | None]], str | None]:
    """Amostra o vídeo em sequência com o OpenCV, pulando os quadros intermediários.

    Os recortes são avaliados no MESMO quadro lido: o custo de ler o vídeo é o gargalo, e
    a detecção em si é barata.

    Args:
        caminho: vídeo.
        t0_s: instante da primeira amostra.
        n: quantas amostras.
        passo_s: passo entre amostras, em segundos.
        recortes: ``[(nome, (y0, y1))]`` dos recortes a medir.
        orcamento_s: tempo máximo desta leitura.
        inicio: instante em que a medição do vídeo começou.

    Returns:
        ``(por_recorte, erro)``; menos de ``n`` amostras por recorte quando o OpenCV falha
        no meio, e ``erro`` ``orcamento_esgotado`` quando o tempo acabou antes do fim.
    """
    amostras: dict[str, list[tuple[float, int, int, int] | None]] = {
        nome: [] for nome, _ in recortes
    }
    estourou = False
    for t, quadro in leitor.quadros_cv2(caminho, t0_s, n, passo_s):
        for nome, (y0, y1) in recortes:
            amostras[nome].append(_montar(detectar_cursor(quadro[y0:y1, :]), t))
        if time.time() - inicio > orcamento_s:
            estourou = True
            break
    return amostras, ("orcamento_esgotado" if estourou else None)


def _amostrar_ffmpeg(
    caminho: str,
    t0_s: float,
    n: int,
    passo_s: float,
    recortes: list[tuple[str, tuple[int, int]]],
    orcamento_s: float,
    inicio: float,
) -> tuple[dict[str, list[tuple[float, int, int, int] | None]], str | None]:
    """Amostra o vídeo pelo ``ffmpeg``, decodificando a janela em uma passada só.

    O caminho lento (um processo por amostra) foi medido em 128 s por vídeo AV1: são 241
    seeks e, a cada seek, o decodificador volta ao *keyframe*. Aqui a janela é
    decodificada **em uma passada**, com o filtro ``fps`` pedindo exatamente o passo
    desejado — menos trabalho de decodificação e muito menos busca no HD (que é
    compartilhado com outros agentes). Os dois recortes saem do mesmo quadro decodificado.

    Args:
        caminho: vídeo.
        t0_s: instante da primeira amostra.
        n: quantas amostras.
        passo_s: passo entre amostras, em segundos.
        recortes: ``[(nome, (y0, y1))]`` dos recortes a medir.
        orcamento_s: tempo máximo desta leitura.
        inicio: instante em que a medição do vídeo começou.

    Returns:
        ``(por_recorte, erro)``. Quando a extração em passada única não devolve quadro
        nenhum, cai para o caminho lento (um processo por amostra).
    """
    dims = _dimensoes(caminho)
    amostras: dict[str, list[tuple[float, int, int, int] | None]] = {
        nome: [] for nome, _ in recortes
    }
    lidas = 0
    if dims is not None:
        largura, altura = dims
        tamanho = largura * altura * 3
        proc = subprocess.Popen(
            [
                "ffmpeg",
                "-v",
                "error",
                "-nostdin",
                "-ss",
                f"{max(0.0, t0_s):.3f}",
                "-i",
                caminho,
                "-t",
                f"{n * passo_s:.3f}",
                "-vf",
                f"fps={1.0 / passo_s:.6f}",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "bgr24",
                "-",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        saida = proc.stdout
        try:
            if saida is not None:
                for k in range(n):
                    bruto = saida.read(tamanho)
                    if not bruto or len(bruto) < tamanho:
                        break
                    quadro = np.frombuffer(bruto, np.uint8).reshape(altura, largura, 3)
                    t = t0_s + k * passo_s
                    for nome, (y0, y1) in recortes:
                        amostras[nome].append(
                            _montar(detectar_cursor(quadro[y0:y1, :]), t)
                        )
                    lidas += 1
                    if time.time() - inicio > orcamento_s:
                        return amostras, "orcamento_esgotado"
        finally:
            if proc.poll() is None:
                proc.kill()
            if saida is not None:
                saida.close()
            proc.wait()
    if lidas:
        return amostras, None
    return _amostrar_ffmpeg_lento(
        caminho, t0_s, n, passo_s, recortes, orcamento_s, inicio
    )


def _amostrar_ffmpeg_lento(
    caminho: str,
    t0_s: float,
    n: int,
    passo_s: float,
    recortes: list[tuple[str, tuple[int, int]]],
    orcamento_s: float,
    inicio: float,
) -> tuple[dict[str, list[tuple[float, int, int, int] | None]], str | None]:
    """Um processo ``ffmpeg`` por amostra — o caminho reserva, para quando a passada falha.

    Args:
        caminho: vídeo.
        t0_s: instante da primeira amostra.
        n: quantas amostras.
        passo_s: passo entre amostras, em segundos.
        recortes: ``[(nome, (y0, y1))]`` dos recortes a medir.
        orcamento_s: tempo máximo desta leitura.
        inicio: instante em que a medição do vídeo começou.

    Returns:
        ``(por_recorte, erro)``; ``erro`` é ``sem_quadro`` quando nenhuma amostra veio.
    """
    amostras: dict[str, list[tuple[float, int, int, int] | None]] = {
        nome: [] for nome, _ in recortes
    }
    vazias = 0
    for k in range(n):
        quadro = _ffmpeg_em(caminho, t0_s + k * passo_s)
        if quadro is None:
            vazias += 1
        t = t0_s + k * passo_s
        for nome, (y0, y1) in recortes:
            det = detectar_cursor(quadro[y0:y1, :]) if quadro is not None else None
            amostras[nome].append(_montar(det, t))
        if time.time() - inicio > orcamento_s:
            return amostras, "orcamento_esgotado"
    return amostras, ("sem_quadro" if n and vazias == n else None)


def serie_do_video(
    caminho: str,
    t0_s: float,
    n_previstas: int,
    recortes: list[tuple[str, tuple[int, int]]],
    passo_s: float = PASSO_S,
    orcamento_s: float = ORCAMENTO_S,
) -> dict:
    """Monta a série densa ``x(t)`` do marcador, amostra a amostra, por recorte.

    A leitura é **sequencial** dentro da janela (um quadro a cada ``passo_s``), e não por
    seek a cada amostra: o seek custa ~80 ms por amostra no OpenCV e obriga o
    decodificador a voltar ao keyframe no ffmpeg. Quando o OpenCV não abre ou não
    decodifica o arquivo (44 % do acervo é AV1), o resto da série é lido pelo ``ffmpeg``,
    que decodifica a janela inteira de uma vez para todos os recortes.

    Args:
        caminho: vídeo.
        t0_s: início da janela, em segundos.
        n_previstas: quantas amostras a janela pede.
        recortes: ``[(nome, (y0, y1))]`` dos recortes a medir; x é absoluto no quadro.
        passo_s: passo entre amostras, em segundos.
        orcamento_s: tempo máximo de leitura antes de cortar e devolver o que tem.

    Returns:
        Dicionário com ``por_recorte`` (nome -> ``serie``/``larguras``/``matizes``), ``via``
        (``cv2``, ``ffmpeg`` ou ``cv2+ffmpeg``), ``n_lidas`` (amostras medidas, com ou sem
        detecção) e ``erro``.
    """
    inicio = time.time()
    por_recorte, erro = _amostrar_cv2(
        caminho, t0_s, n_previstas, passo_s, recortes, orcamento_s, inicio
    )
    lidas = max((len(v) for v in por_recorte.values()), default=0)
    via = "cv2"
    if erro is None and lidas < n_previstas:
        resto, erro = _amostrar_ffmpeg(
            caminho,
            t0_s + lidas * passo_s,
            n_previstas - lidas,
            passo_s,
            recortes,
            orcamento_s,
            inicio,
        )
        via = "ffmpeg" if not lidas else "cv2+ffmpeg"
        for nome in por_recorte:
            por_recorte[nome] = por_recorte[nome] + resto[nome]
        lidas = max((len(v) for v in por_recorte.values()), default=0)
    saida: dict[str, dict[str, list]] = {}
    for nome, amostras in por_recorte.items():
        serie, larguras, matizes = _separar(amostras)
        saida[nome] = {"serie": serie, "larguras": larguras, "matizes": matizes}
    return {
        "por_recorte": saida,
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
    larga demais para ser cursor, ou salto grande **trocando de direção** num `desliza`.

    O último merece explicação, porque já esteve errado aqui: marcador que SALTA anda em
    patamares separados por saltos maiores que ``SALTO_MAX_PX`` — isso é o mecanismo do
    `salta`, não artefato (medido no `sky guitar`: patamares de ~130 px). O que denuncia
    artefato é o salto trocar de direção (o detector alternando entre duas bandas do mesmo
    recorte). Por isso a regra exige as três coisas: `desliza` **e** maioria de passos
    grandes **e** direções trocando. Antes ela disparava só com a maioria de passos
    grandes e reprovava 3 dos 48 vídeos que o `resumo` tinha aprovado.

    Args:
        serie: pontos ``(t, x)`` do marcador.
        larguras: largura, em px, da banda de cada detecção.
        matizes: matiz (0–179) de cada detecção.
        n_lidas: quantas amostras foram medidas de fato.
        n_previstas: quantas amostras a janela pedia.

    Returns:
        Dicionário com ``veredito``, ``veredito_resumo``, ``marcador_visivel``,
        ``motivo_duvida``, ``pontos``, ``deslocamento_total_px``, ``velocidade_px_s``,
        ``velocidade_trechos_px_s``, ``passo_mediano_px``, ``n_deteccoes``, ``cobertura``,
        ``n_saltos_grandes``, ``frac_passos_grandes``, ``frac_trocas_grandes``,
        ``largura_mediana_px``, ``matiz_mediana``, ``matiz_p10``, ``matiz_p90`` e
        ``matiz_hist``.
    """
    r = resumo(serie)
    veredito = r["veredito"]
    motivo: str | None = None
    pares = list(itertools.pairwise(serie))
    grandes = [b - a for (_, a), (_, b) in pares if abs(b - a) > SALTO_MAX_PX]
    frac_grandes = len(grandes) / len(pares) if pares else 0.0
    # Direção dos passos GRANDES. Medido: o marcador do `sky guitar` salta ~130 px de nota
    # em nota — patamares separados por saltos > 60 px são o MECANISMO do `salta`, não
    # artefato. O que denuncia artefato é o salto trocar de direção (o detector alternando
    # entre duas bandas do mesmo recorte), e é isso que `trocas_grandes` mede.
    sinais_grandes = [1 if d > 0 else -1 for d in grandes]
    trocas_grandes = sum(1 for x, y in itertools.pairwise(sinais_grandes) if x != y)
    frac_trocas_grandes = (
        trocas_grandes / len(sinais_grandes) if sinais_grandes else 0.0
    )
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
        elif veredito == "desliza" and frac_grandes > 0.5 and frac_trocas_grandes > 0.3:
            motivo = "movimento_dominado_por_saltos"
        elif largura_mediana > LARGURA_MAX_MARCADOR_PX:
            motivo = "banda_larga"
    if motivo is not None:
        veredito = "duvida"
    # Banda VISÍVEL não é série invertível: no `sky guitar` a banda azul aparece em ~90 %
    # das amostras de 7 de 8 vídeos, e só 3 dão veredito utilizável. Sem esta coluna, o
    # relatório diria "sem marcador" onde o que falta é a série ter sentido único.
    visivel = bool(
        cobertura >= COBERTURA_VISIVEL
        and largura_mediana > 0
        and largura_mediana <= LARGURA_MAX_MARCADOR_PX
    )
    return {
        "veredito": veredito,
        "veredito_resumo": r["veredito"],
        "marcador_visivel": visivel,
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
        "n_saltos_grandes": len(grandes),
        "frac_passos_grandes": round(frac_grandes, 3),
        "frac_trocas_grandes": round(frac_trocas_grandes, 3),
        "largura_mediana_px": largura_mediana or None,
        "matiz_mediana": float(np.median(matizes)) if matizes else None,
        "matiz_p10": float(np.percentile(matizes, 10)) if matizes else None,
        "matiz_p90": float(np.percentile(matizes, 90)) if matizes else None,
        "matiz_hist": histograma_matiz(matizes),
    }


def veredito_do_video(por_crop: dict[str, dict]) -> tuple[str, str]:
    """Veredito do vídeo: o do recorte do PAINEL; ``sem_painel`` quando não houve painel.

    O recorte do painel é o método (é ele que não mistura a tablatura com o vídeo abaixo).
    O recorte fixo é medido junto só para a comparação antes/depois e **não** responde pelo
    vídeo. Sem painel no instante amostrado, o veredito é ``sem_painel`` — que é diferente
    de ``sem_marcador``: ali não se sabe se há marcador, aqui se sabe que não há.

    Args:
        por_crop: nome do recorte -> resultado de ``julgar``.

    Returns:
        ``(veredito, motivo)``.
    """
    if CROP_PAINEL in por_crop:
        return por_crop[CROP_PAINEL]["veredito"], "painel"
    return "sem_painel", "sem_painel"


def recorte_do_painel(quadro: np.ndarray) -> tuple[tuple[int, int], str] | None:
    """Recorte em y colado no sistema de cordas do painel, e o nome da faixa.

    **Por que não usar o recorte fixo**: ``fr[300:750]`` tem 450 px de altura e o portão do
    detector exige banda de 50 % disso (225 px). O playhead do `sky guitar` tem a **altura
    da tablatura** (~140 px, medido no `aguado`): ele é rejeitado, e o detector cai no
    candidato mais cheio do recorte — o corpo do violão e a mão, matiz 17 — produzindo
    ``erratico`` onde há marcador. Colar o recorte nas cordas mede 229 px naquele vídeo e a
    faixa azul (matiz 109) aparece inteira, em escada, veredito ``salta``.

    O y vem de ``tab.pipeline.roi_das_cordas`` (margem de um passo) e a x continua sendo o
    quadro inteiro, como na série original.

    Args:
        quadro: quadro inteiro.

    Returns:
        ``((y0, y1), nome_da_faixa)``, ou None se não há painel de tablatura no quadro.
    """
    try:
        cand = escolher(quadro)
    except Exception:
        return None
    if cand is None:
        return None
    y0, y1 = roi_das_cordas(cand)
    if y1 - y0 < 30:
        return None
    return (int(y0), int(y1)), cand.nome


def medir_video(
    caminho: str,
    raiz: str,
    passo_s: float = PASSO_S,
    janela_s: float = JANELA_S,
    frac_inicio: float = FRAC_INICIO,
    recorte: tuple[int, int] = RECORTE_PADRAO,
    crops: str = "ambos",
    orcamento_s: float = ORCAMENTO_S,
) -> dict:
    """Mede um vídeo e devolve a linha do JSONL (série resumida, não os pontos).

    O painel é escolhido **uma vez** por vídeo, no meio da janela (e, se ali não houver,
    no início dela): `escolher` custa 0,3–1 s por quadro e a tablatura não muda de lugar
    durante o vídeo. O instante usado fica gravado em ``painel_em_s``.

    Args:
        caminho: vídeo.
        raiz: raiz do acervo (para gravar o caminho relativo).
        passo_s: passo entre amostras, em segundos.
        janela_s: tamanho máximo da janela, em segundos.
        frac_inicio: fração da duração onde a janela começa.
        recorte: ``(y0, y1)`` do recorte FIXO (o da medição anterior, para comparação).
        crops: ``ambos`` mede painel e fixo; ``painel`` só o painel; ``fixo`` só o fixo.
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

    recortes: list[tuple[str, tuple[int, int]]] = []
    if crops in {"ambos", "fixo"}:
        recortes.append((CROP_FIXO, recorte))
    nome_painel: str | None = None
    recorte_painel: tuple[int, int] | None = None
    painel_em_s: float | None = None
    tentativas = 0
    if crops in {"ambos", "painel"}:
        leitor = Leitor(caminho)
        try:
            for instante in (t0 + janela / 2, t0):
                tentativas += 1
                quadro = leitor.ler(instante)
                achado = recorte_do_painel(quadro) if quadro is not None else None
                if achado is not None:
                    recorte_painel, nome_painel = achado
                    painel_em_s = round(instante, 1)
                    break
        finally:
            leitor.fechar()
    if recorte_painel is not None:
        recortes.append((CROP_PAINEL, recorte_painel))
    if not recortes:
        recortes.append((CROP_FIXO, recorte))

    medida = serie_do_video(caminho, t0, n_previstas, recortes, passo_s, orcamento_s)
    por_crop = {
        nome: julgar(
            d["serie"], d["larguras"], d["matizes"], medida["n_lidas"], n_previstas
        )
        for nome, d in medida["por_recorte"].items()
    }
    veredito, motivo = veredito_do_video(por_crop)
    linha.update(
        {
            "veredito": veredito,
            "veredito_por": motivo,
            "veredito_fixo": por_crop.get(CROP_FIXO, {}).get("veredito"),
            "veredito_painel": por_crop.get(CROP_PAINEL, {}).get("veredito"),
            "t_inicio_s": round(t0, 1),
            "janela_s": round(janela, 1),
            "passo_s": passo_s,
            "n_previstas": n_previstas,
            "n_lidas": medida["n_lidas"],
            "via": medida["via"],
            "painel": nome_painel,
            "painel_em_s": painel_em_s,
            "painel_tentativas": tentativas,
            "recorte_painel": list(recorte_painel) if recorte_painel else None,
            "recorte_fixo": [int(recorte[0]), int(recorte[1])],
            "erro": medida["erro"],
            "crops": por_crop,
        }
    )
    # Os campos de medida no topo da linha são os do recorte do painel — é ele o método.
    if CROP_PAINEL in por_crop:
        linha.update(por_crop[CROP_PAINEL])
        linha["veredito"] = veredito
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


def _banda_visivel(linha: dict) -> bool:
    """O vídeo tem BANDA no recorte do painel, mesmo sem veredito utilizável?

    Lê ``marcador_visivel`` da linha e, para linhas antigas (gravadas antes deste campo),
    recalcula a partir de ``cobertura`` e ``largura_mediana_px``.

    Args:
        linha: uma linha medida.

    Returns:
        True se há banda estreita na maior parte das amostras do recorte do painel.
    """
    if "marcador_visivel" in linha:
        return bool(linha["marcador_visivel"])
    largura = linha.get("largura_mediana_px")
    return bool(
        float(linha.get("cobertura") or 0.0) >= COBERTURA_VISIVEL
        and largura
        and float(largura) <= LARGURA_MAX_MARCADOR_PX
    )


def agregar_canal(resultados: list[dict]) -> dict:
    """Agrega os resultados de um canal: contagem por veredito e matiz mediana.

    A matiz do canal sai de dois jeitos, de propósito: ``matiz_mediana_por_video`` é a
    mediana das medianas (um vídeo, um voto — não deixa um vídeo longo dominar) e
    ``matiz_mediana_global`` é a mediana do histograma somado (todas as detecções, com
    resolução de meia faixa de 5 graus).

    Args:
        resultados: linhas medidas do canal (dicts do JSONL).

    Returns:
        Dicionário com ``videos``, ``por_veredito``, ``por_veredito_fixo``,
        ``por_veredito_resumo``, ``videos_com_painel``, ``videos_com_banda_visivel``,
        ``marcador_utilizavel``, ``n_deteccoes``, ``matiz_mediana_por_video``,
        ``matiz_mediana_global``, ``velocidade_mediana_px_s``,
        ``velocidade_trechos_mediana_px_s`` e ``por_arquivo``.
    """
    por_veredito = dict.fromkeys(VEREDITOS, 0)
    por_veredito_fixo = dict.fromkeys(VEREDITOS, 0)
    por_veredito_resumo: dict[str, int] = {}
    com_painel = 0
    com_banda = 0
    for r in resultados:
        v = r.get("veredito", "duvida")
        por_veredito[v] = por_veredito.get(v, 0) + 1
        vf = r.get("veredito_fixo") or (r.get("crops") or {}).get(CROP_FIXO, {}).get(
            "veredito"
        )
        if vf:
            por_veredito_fixo[vf] = por_veredito_fixo.get(vf, 0) + 1
        if r.get("recorte_painel"):
            com_painel += 1
        if _banda_visivel(r):
            com_banda += 1
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
        "por_veredito_fixo": por_veredito_fixo,
        "por_veredito_resumo": por_veredito_resumo,
        "videos_com_painel": com_painel,
        "videos_com_banda_visivel": com_banda,
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


def tabela_texto(canais: dict[str, dict], chave: str = "por_veredito") -> str:
    """Tabela legível do resumo por canal.

    Args:
        canais: campo ``canais`` do resumo.
        chave: qual contagem mostrar; ``por_veredito`` é o método (recorte do painel) e
            ``por_veredito_fixo`` é o recorte fixo da medição anterior.

    Returns:
        Texto pronto para imprimir.
    """
    largura_veredito = 9
    cabecalho = f"{'canal':<20}" + "".join(
        f"{v[: largura_veredito - 1]:>{largura_veredito}}" for v in VEREDITOS
    )
    cabecalho += f"{'util':>6}{'banda':>6}{'matiz':>8}"
    linhas = [cabecalho]
    for canal, ag in canais.items():
        contagens = ag.get(chave, {})
        matiz = ag.get("matiz_mediana_global")
        if matiz is None:
            matiz = ag.get("matiz_mediana_por_video")
        linha = f"{canal[:19]:<20}" + "".join(
            f"{contagens.get(v, 0):>{largura_veredito}}" for v in VEREDITOS
        )
        linha += f"{ag.get('marcador_utilizavel', 0):>6}"
        linha += f"{ag.get('videos_com_banda_visivel', 0):>6}"
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
    ap.add_argument("--crops", choices=["ambos", "painel", "fixo"], default="ambos")
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
        print("MÉTODO (recorte do painel):")
        print(tabela_texto(doc["canais"]))
        print("\nANTES (recorte fixo 300:750):")
        print(tabela_texto(doc["canais"], "por_veredito_fixo"))
        return 0

    canais = listar_videos(
        args.raiz,
        args.canais or list(CANAIS_PADRAO),
        args.por_canal,
        args.incluir,
    )
    print(
        f"canais: {len(canais)} | vídeos: {sum(len(v) for v in canais.values())} | "
        f"passo: {args.passo}s | janela: {args.janela}s | crops: {args.crops}",
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
                        args.crops,
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
                    f"{linha.get('veredito')} (fixo={linha.get('veredito_fixo')}) "
                    f"n={linha.get('n_deteccoes')}/{linha.get('n_lidas')} "
                    f"via={linha.get('via')} matiz={linha.get('matiz_mediana')} "
                    f"rec={linha.get('recorte_painel')} {time.time() - t_video:.0f}s",
                    flush=True,
                )
    doc = escrever_resumo(args.saida, list(canais))
    print(
        f"\n{processados} vídeos em {(time.time() - inicio) / 60:.1f} min", flush=True
    )
    print("MÉTODO (recorte do painel):")
    print(tabela_texto(doc["canais"]))
    print("\nANTES (recorte fixo 300:750):")
    print(tabela_texto(doc["canais"], "por_veredito_fixo"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

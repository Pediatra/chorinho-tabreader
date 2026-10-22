"""Censo amostral de pauta de 5 linhas, lendo o cache de quadros do censo.

Pergunta: quantos vídeos do acervo têm pauta? O censo de presença (``tab.censo``) só
mede tablatura; esta CLI mede pauta, em amostra por canal, sobre os quadros já extraídos
(``/cache/png``, 12 quadros por vídeo, nativos). Não abre vídeo.

Por canal, sorteia até ``--por-canal`` vídeos (``random.Random(semente)`` sobre a lista
ordenada por chave), roda ``tab.partitura_pauta.achar_pautas`` nos 12 quadros e grava:

- ``amostra.jsonl``: uma linha por vídeo, com cada quadro, suas pautas e ``sobre_tab``
  (fração da caixa da pauta que cai dentro da tablatura do censo);
- ``resumo.json`` e uma tabela no terminal, com denominador e extrapolação por canal;
- ``folhas/``: miniaturas de conferência visual (positivos e negativos), com ``indice.json``.

Uso::

    python -m tab.partitura_censo --por-canal 30 --semente 0 --saida data/saida/partitura/p0
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np

from tab.comum.cache import ModoCache, caminho_do_quadro, ler_quadro, pasta_do_video
from tab.comum.caminhos import CENSO_V2, RAIZ
from tab.partitura.pauta import achar_pautas, classe_do_quadro, classe_do_video

#: Censo de presença v2: uma linha JSON por vídeo, com os 12 instantes e a tablatura.
CENSO = CENSO_V2 / "censo_v2_completo.jsonl"

#: Instantes por vídeo (``presenca_00`` a ``presenca_11``).
N_QUADROS = 12

#: Largura da miniatura nas folhas, em px.
LARGURA_MINIATURA = 480

#: Miniaturas por página de folha: 4 colunas por 6 linhas.
COLUNAS = 4
POR_PAGINA = 24

#: Quantos quadros por canal entram em cada tipo de folha.
POR_CANAL_FOLHA = 6

#: Espessura (px, no quadro nativo) das caixas desenhadas.
ESPESSURA_CAIXA = 3

#: Cores das caixas, em BGR: verde para pauta, azul para a tablatura do censo.
COR_PAUTA = (0, 255, 0)
COR_TAB = (255, 0, 0)

#: Caixa fixa de cada miniatura (a imagem; a legenda fica embaixo). 16:9.
ALTURA_MINIATURA = 270

#: Cinza escuro do preenchimento da caixa (letterbox), em BGR.
COR_LETTERBOX = (30, 30, 30)

#: Altura da faixa de legenda sob cada miniatura, e espaço entre miniaturas (px).
ALTURA_LEGENDA = 26
ESPACO = 6

#: Qualidade do JPEG das folhas.
QUALIDADE_JPEG = 85

#: Cor de fundo entre as miniaturas, em tons de cinza.
COR_FUNDO = 40

#: A cada quantos vídeos imprime o progresso.
PASSO_PROGRESSO = 50


def ler_censo(caminho: Path) -> list[dict]:
    """Lê o censo de presença e mantém a última linha de cada chave.

    Args:
        caminho: arquivo JSONL do censo.

    Returns:
        Os vídeos com os 12 instantes, ordenados por chave.
    """
    ultimo: dict[str, dict] = {}
    with caminho.open(encoding="utf-8") as arquivo:
        for linha in arquivo:
            if linha.strip():
                registro = json.loads(linha)
                ultimo[registro["chave"]] = registro
    validos = [
        registro
        for registro in ultimo.values()
        if len(registro.get("instantes") or []) == N_QUADROS
    ]
    return sorted(validos, key=lambda registro: registro["chave"])


def sortear_por_canal(
    videos: list[dict], por_canal: int, semente: int
) -> dict[str, list[dict]]:
    """Sorteia até ``por_canal`` vídeos de cada canal, de forma determinística.

    Canal com até ``por_canal`` vídeos entra inteiro.

    Args:
        videos: os vídeos do censo, ordenados por chave.
        por_canal: tamanho máximo da amostra por canal.
        semente: semente do ``random.Random``, usada em cada canal.

    Returns:
        Mapa canal -> vídeos sorteados, em ordem de chave.
    """
    grupos: dict[str, list[dict]] = defaultdict(list)
    for video in videos:
        grupos[video["canal"]].append(video)
    amostra: dict[str, list[dict]] = {}
    for canal in sorted(grupos):
        lista = grupos[canal]
        if len(lista) <= por_canal:
            escolhidos = list(lista)
        else:
            escolhidos = random.Random(semente).sample(lista, por_canal)
        amostra[canal] = sorted(escolhidos, key=lambda video: video["chave"])
    return amostra


def fracao_sobre_tab(
    caixa: tuple[int, int, int, int], rect: list[float] | None
) -> float:
    """Fração da caixa da pauta que cai dentro da caixa da tablatura.

    Args:
        caixa: caixa da pauta ``(x0, y0, x1, y1)``.
        rect: caixa da tablatura do censo ``[x0, y0, x1, y1]``, ou ``None``.

    Returns:
        Valor em ``[0, 1]``; 0 se não há tablatura no quadro.
    """
    if rect is None:
        return 0.0
    x0, y0, x1, y1 = caixa
    rx0, ry0, rx1, ry1 = rect
    largura = min(x1, rx1) - max(x0, rx0)
    altura = min(y1, ry1) - max(y0, ry0)
    if largura <= 0 or altura <= 0:
        return 0.0
    area = (x1 - x0) * (y1 - y0)
    return float(largura * altura / area)


def medir_video(video: dict, modo: ModoCache, tempos: list[float]) -> dict:
    """Mede os 12 quadros de um vídeo no cache.

    Quadro sem PNG no cache vira ``falta`` e não entra na classe do vídeo.

    Args:
        video: linha do censo de presença.
        modo: modo de cache (somente leitura, usado para achar a pasta).
        tempos: lista onde se acumula o tempo (leitura mais detecção) de cada quadro lido.

    Returns:
        O registro do vídeo para ``amostra.jsonl``.
    """
    pasta = pasta_do_video(video["chave"], modo)
    quadros: list[dict] = []
    for indice, instante in enumerate(video["instantes"]):
        rect = instante.get("rect")
        tem_tab = bool(instante.get("tab"))
        base = {
            "frac": instante["frac"],
            "t": instante["t"],
            "tab": tem_tab,
            "rect": rect,
        }
        caminho = caminho_do_quadro(pasta, f"presenca_{indice:02d}", "png")
        if not caminho.exists():
            quadros.append({**base, "falta": True, "pautas": [], "classe": "falta"})
            continue
        inicio = time.perf_counter()
        pautas = achar_pautas(ler_quadro(caminho))
        tempos.append(time.perf_counter() - inicio)
        registros = [
            {
                "ys": list(pauta.ys),
                "entrelinha": round(pauta.entrelinha, 2),
                "caixa": list(pauta.caixa),
                "sobre_tab": round(fracao_sobre_tab(pauta.caixa, rect), 3),
            }
            for pauta in pautas
        ]
        classe = classe_do_quadro(len(pautas), tem_tab)
        quadros.append({**base, "falta": False, "pautas": registros, "classe": classe})
    lidos = [quadro for quadro in quadros if not quadro["falta"]]
    info = video.get("info", {})
    return {
        "canal": video["canal"],
        "arquivo": video["arquivo"],
        "chave": video["chave"],
        "largura": info.get("largura"),
        "altura": info.get("altura"),
        "quadros": quadros,
        "classe_video": (
            classe_do_video([quadro["classe"] for quadro in lidos])
            if lidos
            else "sem_cache"
        ),
        "n_quadros_com_pauta": sum(1 for quadro in lidos if quadro["pautas"]),
        "faltas": len(quadros) - len(lidos),
    }


def _linha_do_canal(canal: str, n_canal: int, registros: list[dict]) -> dict:
    """Resume um canal: contagens de vídeos e quadros, e extrapolação.

    Args:
        canal: nome do canal.
        n_canal: vídeos do canal no censo.
        registros: registros medidos de vídeos desse canal.

    Returns:
        Linha do resumo com contagens, fração (com denominador) e extrapolação.
    """
    n_amostra = len(registros)
    classes_video = Counter(registro["classe_video"] for registro in registros)
    quadros = Counter(
        quadro["classe"] for registro in registros for quadro in registro["quadros"]
    )
    com_pauta = classes_video["pauta+tab"] + classes_video["so_pauta"]
    fracao = com_pauta / n_amostra if n_amostra else 0.0
    entrelinhas = [
        pauta["entrelinha"]
        for registro in registros
        for quadro in registro["quadros"]
        for pauta in quadro["pautas"]
    ]
    return {
        "canal": canal,
        "n_canal": n_canal,
        "n_amostra": n_amostra,
        "video_pauta_tab": classes_video["pauta+tab"],
        "video_so_pauta": classes_video["so_pauta"],
        "video_so_tab": classes_video["so_tab"],
        "video_nenhum": classes_video["nenhum"],
        "video_sem_cache": classes_video["sem_cache"],
        "videos_com_pauta": com_pauta,
        "fracao": round(fracao, 4),
        "extrapolacao": round(fracao * n_canal, 1),
        "quadro_pauta_tab": quadros["pauta+tab"],
        "quadro_so_pauta": quadros["so_pauta"],
        "quadro_so_tab": quadros["so_tab"],
        "quadro_nenhum": quadros["nenhum"],
        "quadro_falta": quadros["falta"],
        "quadros_lidos": sum(quadros.values()) - quadros["falta"],
        "n_pautas": len(entrelinhas),
        "entrelinha_mediana": (
            round(statistics.median(entrelinhas), 2) if entrelinhas else None
        ),
    }


def resumir(
    n_por_canal: dict[str, int], registros: list[dict]
) -> tuple[list[dict], dict]:
    """Resume a amostra por canal e no total.

    Args:
        n_por_canal: vídeos de cada canal no censo.
        registros: todos os registros medidos.

    Returns:
        A lista de linhas por canal e a linha TOTAL (somas e fração global).
    """
    linhas = []
    for canal in sorted(n_por_canal):
        do_canal = [registro for registro in registros if registro["canal"] == canal]
        if do_canal:
            linhas.append(_linha_do_canal(canal, n_por_canal[canal], do_canal))
    soma_campos = [
        "n_canal",
        "n_amostra",
        "video_pauta_tab",
        "video_so_pauta",
        "video_so_tab",
        "video_nenhum",
        "video_sem_cache",
        "videos_com_pauta",
        "extrapolacao",
        "quadro_pauta_tab",
        "quadro_so_pauta",
        "quadro_so_tab",
        "quadro_nenhum",
        "quadro_falta",
        "quadros_lidos",
        "n_pautas",
    ]
    total: dict = {"canal": "TOTAL"}
    for campo in soma_campos:
        total[campo] = sum(linha[campo] for linha in linhas)
    total["fracao"] = (
        round(total["videos_com_pauta"] / total["n_amostra"], 4)
        if total["n_amostra"]
        else 0.0
    )
    total["extrapolacao"] = round(total["extrapolacao"], 1)
    entrelinhas = [
        pauta["entrelinha"]
        for registro in registros
        for quadro in registro["quadros"]
        for pauta in quadro["pautas"]
    ]
    total["entrelinha_mediana"] = (
        round(statistics.median(entrelinhas), 2) if entrelinhas else None
    )
    return linhas, total


def _imprimir_tabelas(linhas: list[dict], total: dict) -> None:
    """Imprime as duas tabelas do resumo: vídeos e quadros.

    Args:
        linhas: linhas por canal de ``resumir``.
        total: linha TOTAL de ``resumir``.
    """
    cabecalho = (
        f"{'canal':<22}{'n_canal':>8}{'amostra':>9}{'pt+tab':>8}{'so_pau':>8}"
        f"{'so_tab':>8}{'nenhum':>8}{'s/cache':>9}{'c/pauta':>10}{'fracao':>9}"
        f"{'extrap':>9}"
    )
    print("\nVIDEOS (classe por video; c/pauta = pauta+tab + so_pauta)")
    print(cabecalho)
    print("-" * len(cabecalho))
    for linha in [*linhas, total]:
        denominador = f"{linha['videos_com_pauta']}/{linha['n_amostra']}"
        print(
            f"{linha['canal'][:21]:<22}{linha['n_canal']:>8}{linha['n_amostra']:>9}"
            f"{linha['video_pauta_tab']:>8}{linha['video_so_pauta']:>8}"
            f"{linha['video_so_tab']:>8}{linha['video_nenhum']:>8}"
            f"{linha['video_sem_cache']:>9}{denominador:>10}"
            f"{linha['fracao']:>9.3f}{linha['extrapolacao']:>9.1f}"
        )
    cabecalho_q = (
        f"{'canal':<22}{'lidos':>8}{'pt+tab':>8}{'so_pau':>8}{'so_tab':>8}"
        f"{'nenhum':>8}{'falta':>8}{'pautas':>8}{'entrel.med':>12}"
    )
    print("\nQUADROS (classe por quadro)")
    print(cabecalho_q)
    print("-" * len(cabecalho_q))
    for linha in [*linhas, total]:
        entrelinha = linha["entrelinha_mediana"]
        texto = f"{entrelinha:.2f}" if entrelinha is not None else "-"
        print(
            f"{linha['canal'][:21]:<22}{linha['quadros_lidos']:>8}"
            f"{linha['quadro_pauta_tab']:>8}{linha['quadro_so_pauta']:>8}"
            f"{linha['quadro_so_tab']:>8}{linha['quadro_nenhum']:>8}"
            f"{linha['quadro_falta']:>8}{linha['n_pautas']:>8}{texto:>12}"
        )


def _ascii(texto: str) -> str:
    """Troca caracteres não-ASCII por ``?``, porque ``cv2.putText`` não os desenha.

    Args:
        texto: texto original.

    Returns:
        O texto só com ASCII.
    """
    return texto.encode("ascii", "replace").decode("ascii")


def escolher_para_folha(
    registros: list[dict], positivos: bool, semente: int
) -> list[dict]:
    """Sorteia, por canal, até ``POR_CANAL_FOLHA`` quadros com ou sem pauta.

    Args:
        registros: registros medidos de ``medir_video``.
        positivos: True para quadros com pelo menos uma pauta; False para os sem pauta.
        semente: semente usada no sorteio de cada canal.

    Returns:
        Os quadros escolhidos, agrupados por canal e em ordem determinística.
    """
    grupos: dict[str, list[dict]] = defaultdict(list)
    for registro in registros:
        for indice, quadro in enumerate(registro["quadros"]):
            if quadro["falta"] or bool(quadro["pautas"]) != positivos:
                continue
            grupos[registro["canal"]].append(
                {
                    "canal": registro["canal"],
                    "arquivo": registro["arquivo"],
                    "chave": registro["chave"],
                    "indice": indice,
                    "frac": quadro["frac"],
                    "classe": quadro["classe"],
                    "pautas": quadro["pautas"],
                    "rect": quadro["rect"],
                }
            )
    tipo = "pos" if positivos else "neg"
    escolhidos: list[dict] = []
    for canal in sorted(grupos):
        lista = sorted(grupos[canal], key=lambda c: (c["chave"], c["indice"]))
        if len(lista) > POR_CANAL_FOLHA:
            rng = random.Random(f"{semente}:{tipo}:{canal}")
            lista = sorted(
                rng.sample(lista, POR_CANAL_FOLHA),
                key=lambda c: (c["chave"], c["indice"]),
            )
        escolhidos.extend(lista)
    return escolhidos


def _caixa_fixa(quadro: np.ndarray) -> np.ndarray:
    """Encaixa o quadro numa caixa fixa de ``LARGURA_MINIATURA`` x ``ALTURA_MINIATURA``.

    Mantém a proporção, centraliza e preenche as sobras com ``COR_LETTERBOX``. Assim toda
    miniatura tem o mesmo tamanho, inclusive vídeo vertical.

    Args:
        quadro: quadro BGR nativo.

    Returns:
        Imagem BGR de ``ALTURA_MINIATURA`` por ``LARGURA_MINIATURA``.
    """
    altura, largura = quadro.shape[:2]
    escala = min(LARGURA_MINIATURA / largura, ALTURA_MINIATURA / altura)
    nova_largura = max(1, round(largura * escala))
    nova_altura = max(1, round(altura * escala))
    redimensionado = cv2.resize(
        quadro, (nova_largura, nova_altura), interpolation=cv2.INTER_AREA
    )
    caixa = np.full((ALTURA_MINIATURA, LARGURA_MINIATURA, 3), COR_LETTERBOX, np.uint8)
    y = (ALTURA_MINIATURA - nova_altura) // 2
    x = (LARGURA_MINIATURA - nova_largura) // 2
    caixa[y : y + nova_altura, x : x + nova_largura] = redimensionado
    return caixa


def _miniatura(candidato: dict, modo: ModoCache, rotulo: str) -> np.ndarray:
    """Miniatura de um quadro, com caixas no quadro nativo e legenda embaixo.

    Args:
        candidato: quadro escolhido (de ``escolher_para_folha``).
        modo: modo de cache, para achar o PNG.
        rotulo: número da miniatura, como ``P001``.

    Returns:
        Imagem BGR da miniatura com a faixa de legenda.
    """
    pasta = pasta_do_video(candidato["chave"], modo)
    caminho = caminho_do_quadro(pasta, f"presenca_{candidato['indice']:02d}", "png")
    quadro = ler_quadro(caminho).copy()
    for pauta in candidato["pautas"]:
        x0, y0, x1, y1 = pauta["caixa"]
        cv2.rectangle(quadro, (x0, y0), (x1, y1), COR_PAUTA, ESPESSURA_CAIXA)
    if candidato["rect"] is not None:
        x0, y0, x1, y1 = (int(valor) for valor in candidato["rect"])
        cv2.rectangle(quadro, (x0, y0), (x1, y1), COR_TAB, ESPESSURA_CAIXA)
    mini = _caixa_fixa(quadro)
    faixa = np.zeros((ALTURA_LEGENDA, LARGURA_MINIATURA, 3), np.uint8)
    texto = _ascii(
        f"{rotulo} {candidato['canal'][:16]} frac={candidato['frac']:.3f} "
        f"{candidato['classe']} p={len(candidato['pautas'])}"
    )
    cv2.putText(
        faixa,
        texto[:60],
        (6, 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    return np.vstack([mini, faixa])


def _pagina(minis: list[np.ndarray]) -> np.ndarray:
    """Monta uma página de miniaturas em grade de ``COLUNAS`` colunas.

    Args:
        minis: miniaturas da página, em ordem de leitura.

    Returns:
        Imagem BGR da página.
    """
    altura_celula = max(mini.shape[0] for mini in minis)
    linhas = math.ceil(len(minis) / COLUNAS)
    tela = np.full(
        (
            linhas * (altura_celula + ESPACO) + ESPACO,
            COLUNAS * (LARGURA_MINIATURA + ESPACO) + ESPACO,
            3,
        ),
        COR_FUNDO,
        np.uint8,
    )
    for k, mini in enumerate(minis):
        linha, coluna = divmod(k, COLUNAS)
        y = ESPACO + linha * (altura_celula + ESPACO)
        x = ESPACO + coluna * (LARGURA_MINIATURA + ESPACO)
        tela[y : y + mini.shape[0], x : x + mini.shape[1]] = mini
    return tela


def gravar_folhas(
    escolhidos: list[dict], positivos: bool, modo: ModoCache, pasta: Path
) -> list[dict]:
    """Grava as páginas de um tipo de folha e devolve o índice das miniaturas.

    Args:
        escolhidos: quadros escolhidos (de ``escolher_para_folha``).
        positivos: True para ``positivos_NN.jpg`` (prefixo P), False para negativos (N).
        modo: modo de cache, para achar os PNGs.
        pasta: diretório das folhas.

    Returns:
        Uma entrada por miniatura, com página, posição, canal, arquivo, frac, classe e pautas.
    """
    nome = "positivos" if positivos else "negativos"
    prefixo = "P" if positivos else "N"
    indice: list[dict] = []
    paginas = math.ceil(len(escolhidos) / POR_PAGINA) if escolhidos else 0
    for pagina in range(paginas):
        bloco = escolhidos[pagina * POR_PAGINA : (pagina + 1) * POR_PAGINA]
        minis = []
        arquivo_jpg = f"{nome}_{pagina + 1:02d}.jpg"
        for posicao, candidato in enumerate(bloco):
            numero = pagina * POR_PAGINA + posicao + 1
            rotulo = f"{prefixo}{numero:03d}"
            minis.append(_miniatura(candidato, modo, rotulo))
            indice.append(
                {
                    "numero": rotulo,
                    "pagina": pagina + 1,
                    "posicao": posicao + 1,
                    "arquivo_jpg": arquivo_jpg,
                    "canal": candidato["canal"],
                    "arquivo": candidato["arquivo"],
                    "chave": candidato["chave"],
                    "indice_quadro": candidato["indice"],
                    "frac": candidato["frac"],
                    "classe": candidato["classe"],
                    "pautas": [pauta["caixa"] for pauta in candidato["pautas"]],
                }
            )
        ok = cv2.imwrite(
            str(pasta / arquivo_jpg),
            _pagina(minis),
            [cv2.IMWRITE_JPEG_QUALITY, QUALIDADE_JPEG],
        )
        if not ok:
            raise OSError(f"não gravou a folha {arquivo_jpg}")
    return indice


def main() -> None:
    """Roda o censo amostral de pauta e grava amostra, resumo e folhas."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--por-canal", type=int, default=30)
    parser.add_argument("--semente", type=int, default=0)
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    saida: Path = args.saida if args.saida.is_absolute() else RAIZ / args.saida
    pasta_folhas = saida / "folhas"
    pasta_folhas.mkdir(parents=True, exist_ok=True)

    videos = ler_censo(CENSO)
    n_por_canal = Counter(video["canal"] for video in videos)
    amostra = sortear_por_canal(videos, args.por_canal, args.semente)
    todos = [video for canal in sorted(amostra) for video in amostra[canal]]
    print(
        f"censo: {len(videos)} videos validos em {len(n_por_canal)} canais; "
        f"amostra: {len(todos)} videos (ate {args.por_canal} por canal, "
        f"semente {args.semente})",
        flush=True,
    )

    modo = ModoCache(usar=True)
    tempos: list[float] = []
    registros: list[dict] = []
    inicio = time.perf_counter()
    for k, video in enumerate(todos, start=1):
        registros.append(medir_video(video, modo, tempos))
        if k % PASSO_PROGRESSO == 0 or k == len(todos):
            decorrido = time.perf_counter() - inicio
            restante = decorrido / k * (len(todos) - k)
            print(
                f"  {k}/{len(todos)} videos, {decorrido:.0f}s, restam ~{restante:.0f}s",
                flush=True,
            )
    tempo_total = time.perf_counter() - inicio

    with (saida / "amostra.jsonl").open("w", encoding="utf-8") as arquivo:
        for registro in registros:
            arquivo.write(json.dumps(registro, ensure_ascii=False) + "\n")

    linhas, total = resumir(dict(n_por_canal), registros)
    faltas_quadros = sum(registro["faltas"] for registro in registros)
    tempo_medio = statistics.fmean(tempos) if tempos else 0.0
    resumo = {
        "semente": args.semente,
        "por_canal": args.por_canal,
        "censo": {"arquivo": str(CENSO), "videos_validos": len(videos)},
        "amostra_videos": len(todos),
        "faltas_de_cache": faltas_quadros,
        "tempo": {
            "total_s": round(tempo_total, 1),
            "quadros_lidos": len(tempos),
            "medio_por_quadro_s": round(tempo_medio, 4),
        },
        "canais": linhas,
        "total": total,
    }
    (saida / "resumo.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    positivos = escolher_para_folha(registros, True, args.semente)
    negativos = escolher_para_folha(registros, False, args.semente)
    indice = {
        "positivos": gravar_folhas(positivos, True, modo, pasta_folhas),
        "negativos": gravar_folhas(negativos, False, modo, pasta_folhas),
    }
    (pasta_folhas / "indice.json").write_text(
        json.dumps(indice, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    _imprimir_tabelas(linhas, total)
    print(
        f"\nTEMPO: total {tempo_total:.1f}s; {len(tempos)} quadros lidos; "
        f"medio {tempo_medio * 1000:.1f} ms por quadro (leitura + deteccao)"
    )
    print(f"FALTAS de cache: {faltas_quadros} quadros de {len(todos) * N_QUADROS}")
    paginas_pos = len({m["pagina"] for m in indice["positivos"]})
    paginas_neg = len({m["pagina"] for m in indice["negativos"]})
    print(
        f"FOLHAS: {len(positivos)} positivos em {paginas_pos} paginas; "
        f"{len(negativos)} negativos em {paginas_neg} paginas; em {pasta_folhas}"
    )
    print(f"SAIDA: {saida}")


if __name__ == "__main__":
    main()

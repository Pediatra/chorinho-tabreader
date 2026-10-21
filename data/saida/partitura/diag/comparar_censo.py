"""Compara o censo de pauta antes (p0) e depois (censo_completar) da passada nova.

Casa vídeo por ``chave`` e quadro por índice. Grava ``comparar_censo.txt`` com os
totais e a lista de mudanças, e a folha ``censo_completar_mudancas*.jpg`` com cada
quadro que mudou (caixas das pautas novas em vermelho, das pautas perdidas em azul).
"""

import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

from tab.caminhos import acervo
from tab.leitor import quadro_em
from tab.partitura_pauta import classe_do_video

RAIZ = Path(__file__).resolve().parents[4]
ANTES = RAIZ / "data/saida/partitura/p0/amostra.jsonl"
DEPOIS = RAIZ / "data/saida/partitura/diag/censo_completar/amostra.jsonl"
SAIDA = RAIZ / "data/saida/partitura/diag"
LARGURA_MINIATURA = 480
MIUDEZA = 3  # px: pautas com ys[0] a até isso são a mesma pauta
POR_FOLHA = 30
COLUNAS = 5


def ler(caminho: Path) -> dict[str, dict]:
    """Lê um amostra.jsonl e indexa os vídeos por chave.

    Args:
        caminho: arquivo jsonl, uma linha por vídeo.

    Returns:
        Mapa chave -> registro do vídeo.
    """
    registros = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if linha.strip():
            registro = json.loads(linha)
            registros[registro["chave"]] = registro
    return registros


def _ascii(texto: str) -> str:
    """Texto só com ASCII, para o putText do OpenCV (ele não desenha Unicode).

    Args:
        texto: texto de entrada.

    Returns:
        O texto com caracteres não ASCII trocados por ``?``.
    """
    return texto.encode("ascii", "replace").decode("ascii")


def _novas(depois: list[dict], antes: list[dict]) -> list[dict]:
    """Pautas de ``depois`` que não estão em ``antes`` (pelo ys[0]).

    Args:
        depois: pautas do quadro depois da passada.
        antes: pautas do quadro antes da passada.

    Returns:
        As pautas novas.
    """
    return [
        p
        for p in depois
        if not any(abs(p["ys"][0] - q["ys"][0]) <= MIUDEZA for q in antes)
    ]


def _perdidas(depois: list[dict], antes: list[dict]) -> list[dict]:
    """Pautas de ``antes`` que sumiram em ``depois`` (pelo ys[0]).

    Args:
        depois: pautas do quadro depois da passada.
        antes: pautas do quadro antes da passada.

    Returns:
        As pautas perdidas.
    """
    return [
        q
        for q in antes
        if not any(abs(q["ys"][0] - p["ys"][0]) <= MIUDEZA for p in depois)
    ]


def _miniatura(
    video: dict,
    quadro: dict,
    antes: list[dict],
    depois: list[dict],
    legenda: str,
) -> np.ndarray:
    """Miniatura de um quadro com as caixas de pautas novas e perdidas.

    Args:
        video: registro do vídeo (campo ``arquivo``).
        quadro: registro do quadro (campo ``t``).
        antes: pautas do quadro antes.
        depois: pautas do quadro depois.
        legenda: texto da faixa de baixo.

    Returns:
        Imagem BGR de largura ``LARGURA_MINIATURA`` com a legenda abaixo.
    """
    img = quadro_em(str(acervo() / video["arquivo"]), quadro["t"])
    altura, largura = img.shape[:2]
    fator = LARGURA_MINIATURA / largura
    img = cv2.resize(img, (LARGURA_MINIATURA, round(altura * fator)))
    for p in _novas(depois, antes):
        x0, y0, x1, y1 = p["caixa"]
        cv2.rectangle(
            img,
            (round(x0 * fator), round(y0 * fator)),
            (round(x1 * fator), round(y1 * fator)),
            (0, 0, 255),
            2,
        )
    for p in _perdidas(depois, antes):
        x0, y0, x1, y1 = p["caixa"]
        cv2.rectangle(
            img,
            (round(x0 * fator), round(y0 * fator)),
            (round(x1 * fator), round(y1 * fator)),
            (255, 0, 0),
            2,
        )
    faixa = np.full((26, LARGURA_MINIATURA, 3), 255, np.uint8)
    cv2.putText(
        faixa, _ascii(legenda), (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
        (0, 0, 0), 1, cv2.LINE_AA,
    )  # fmt: skip
    return np.vstack([img, faixa])


def _folhas(itens: list[tuple[dict, dict, dict, dict, str]], base: str) -> list[Path]:
    """Monta as folhas de contato, ``POR_FOLHA`` miniaturas por arquivo JPEG.

    Args:
        itens: (vídeo, quadro, antes, depois, legenda) de cada quadro que mudou.
        base: prefixo do nome dos arquivos em ``SAIDA``.

    Returns:
        Os caminhos dos JPEGs gravados.
    """
    caminhos = []
    for n, inicio in enumerate(range(0, len(itens), POR_FOLHA), start=1):
        lote = itens[inicio : inicio + POR_FOLHA]
        minis = [_miniatura(*item) for item in lote]
        altura = max(m.shape[0] for m in minis)
        minis = [
            np.pad(m, ((0, altura - m.shape[0]), (0, 0), (0, 0)), constant_values=0)
            for m in minis
        ]
        linhas = math.ceil(len(minis) / COLUNAS)
        vazio = np.zeros_like(minis[0])
        minis += [vazio] * (linhas * COLUNAS - len(minis))
        grades = [
            np.hstack(minis[r * COLUNAS : (r + 1) * COLUNAS]) for r in range(linhas)
        ]
        folha = np.vstack(grades)
        sufixo = "" if len(itens) <= POR_FOLHA else f"_{n}"
        caminho = SAIDA / f"{base}{sufixo}.jpg"
        cv2.imwrite(str(caminho), folha, [cv2.IMWRITE_JPEG_QUALITY, 85])
        caminhos.append(caminho)
    return caminhos


def main() -> None:
    """Compara antes e depois, grava o relatório e as folhas de mudanças."""
    antes_por_video = ler(ANTES)
    depois_por_video = ler(DEPOIS)
    ganhos, perdidos, diferentes, trocas = [], [], [], []
    itens = []
    comuns = 0
    for chave, depois_v in depois_por_video.items():
        antes_v = antes_por_video.get(chave)
        if antes_v is None:
            continue
        comuns += 1
        pares = list(zip(antes_v["quadros"], depois_v["quadros"], strict=True))
        classes_antes = []
        classes_depois = []
        for qa, qb in pares:
            if qa["falta"] or qb["falta"]:
                continue
            assert qa["t"] == qb["t"], (chave, qa["t"], qb["t"])
            na, nb = len(qa["pautas"]), len(qb["pautas"])
            classes_antes.append(qa["classe"])
            classes_depois.append(qb["classe"])
            if na == nb:
                continue
            ref = f"{depois_v['canal']} | {depois_v['arquivo']} | t={qb['t']:.1f}"
            linha = f"{ref}  {na}->{nb}"
            if na == 0:
                ganhos.append(linha)
            elif nb == 0:
                perdidos.append(linha)
            else:
                diferentes.append(linha)
            legenda = (
                f"{depois_v['canal'][:18]} t={qb['t']:.0f} {na}->{nb}"
            )
            itens.append((depois_v, qb, qa["pautas"], qb["pautas"], legenda))
        cl_a = classe_do_video(classes_antes)
        cl_b = classe_do_video(classes_depois)
        if cl_a != cl_b:
            trocas.append(
                f"{depois_v['canal']} | {depois_v['arquivo']}  {cl_a} -> {cl_b}"
            )
    linhas = [
        f"videos comuns: {comuns} (antes {len(antes_por_video)}, depois {len(depois_por_video)})",
        f"quadros ganhos (0 -> >=1): {len(ganhos)}",
        f"quadros perdidos (>=1 -> 0): {len(perdidos)}",
        f"quadros com contagem diferente (n -> m, ambos >=1): {len(diferentes)}",
        f"videos que trocaram de classe: {len(trocas)}",
        "",
        "== ganhos",
        *ganhos,
        "",
        "== perdidos",
        *perdidos,
        "",
        "== contagem diferente",
        *diferentes,
        "",
        "== trocas de classe",
        *trocas,
    ]
    texto = "\n".join(linhas) + "\n"
    (SAIDA / "comparar_censo.txt").write_text(texto, encoding="utf-8")
    sys.stdout.write(texto)
    folhas = _folhas(itens, "censo_completar_mudancas") if itens else []
    print("folhas:", [str(f) for f in folhas])


if __name__ == "__main__":
    main()

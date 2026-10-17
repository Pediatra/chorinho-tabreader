"""Pré-rótulo do ataque por par de notas vizinhas (rodada 0201).

Para cada par de notas vizinhas da mesma corda numa tela conferida do gabarito do ataque,
grava o recorte da imagem entre as duas e mede a tinta que não é algarismo nem linha de
corda (a "regra simples" do plano R3). O par é "ligado" quando a nota da direita é "nao"
no gabarito do dono. Os recortes servem também ao teste do modelo de linguagem.

Uso::

    python -m tab.ataque_pares
"""

import argparse
import itertools
import json
from collections.abc import Sequence
from pathlib import Path

import cv2
import numpy as np

from tab import caminhos

#: Fonte do gabarito -> slug do ouro (a pasta da ferramenta tem o mesmo nome).
FONTES = {
    "end_of_beginning": "end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics",
    "tabroom_335": "tabroom_335_larry_carlton_fingerstyle_guitar",
    "pat_metheny": "tab_from_this_place_pat_metheny_fingerstyle_guitar_cover",
    "la_vie_en_rose": "la_vie_en_rose_edith_piaf_tab",
}

#: Distância máxima entre as duas notas de um par, em passos.
MAX_GAP = 8.0

#: Meia largura da caixa de uma nota de um algarismo, em passos (dois algarismos: dobro).
MEIA_LARGURA = 0.35

#: Meia altura da caixa de uma nota, em passos.
MEIA_ALTURA = 0.45

#: Componente de tinta que conta: largura mínima e altura máxima, em passos.
LARGURA_MIN = 0.25
ALTURA_MAX = 1.4

#: Diferença mínima de cinza para o fundo, em níveis (0-255), para contar como tinta.
LIMIAR_TINTA = 60


def pares_da_tela(notas: Sequence[dict], passo: float) -> list[tuple[int, int]]:
    """Pares de notas vizinhas da mesma corda, da esquerda para a direita.

    Args:
        notas: notas da tela, com ``corda`` e ``x_centro_quadro``.
        passo: passo da tela, em px.

    Returns:
        Lista de ``(i, j)`` com ``i`` à esquerda de ``j``, a até ``MAX_GAP`` passos.
    """
    pares = []
    por_corda: dict[int, list[int]] = {}
    for k, n in enumerate(notas):
        por_corda.setdefault(n["corda"], []).append(k)
    for ks in por_corda.values():
        ks.sort(key=lambda k: notas[k]["x_centro_quadro"])
        for a, b in itertools.pairwise(ks):
            gap = notas[b]["x_centro_quadro"] - notas[a]["x_centro_quadro"]
            if 0 < gap <= MAX_GAP * passo:
                pares.append((a, b))
    return pares


def meia_largura(casa: object, passo: float) -> float:
    """Meia largura da caixa de uma nota, em px.

    Args:
        casa: a casa (número ou texto).
        passo: passo da tela, em px.

    Returns:
        ``MEIA_LARGURA`` passos por algarismo.
    """
    return MEIA_LARGURA * passo * max(1, len(str(casa)))


def mascara_de_tinta(cinza: np.ndarray) -> np.ndarray:
    """Tinta = pixels longe do fundo (a mediana), em qualquer polaridade.

    Linhas longas na horizontal (cordas) e na vertical (barras de compasso) saem.

    Args:
        cinza: imagem em tons de cinza.

    Returns:
        Máscara booleana da tinta.
    """
    fundo = float(np.median(cinza))
    tinta = np.abs(cinza.astype(np.int16) - fundo) > LIMIAR_TINTA
    linhas = tinta.mean(axis=1) > 0.5
    tinta[linhas, :] = False
    colunas = tinta.mean(axis=0) > 0.6
    tinta[:, colunas] = False
    return tinta


def tinta_entre(
    tinta: np.ndarray,
    notas: Sequence[dict],
    a: int,
    b: int,
    y_corda: float,
    passo: float,
    origem: tuple[float, float],
    escala: float,
) -> tuple[float, float]:
    """Tinta entre as notas ``a`` e ``b``, fora das caixas de nota.

    A janela vai do centro de ``a`` ao centro de ``b`` (o arco passa por cima delas), de 1,6 passo acima
    da corda até 1,2 passo abaixo (o arco fica em cima ou embaixo, conforme o canal; o
    slide, na corda). Só contam componentes largos e baixos: traço fino na vertical
    (haste de ritmo, barra) e símbolo alto (arpejo, rasgueado) saem.

    Args:
        tinta: máscara da imagem da tela.
        notas: notas da tela.
        a: índice da nota da esquerda.
        b: índice da nota da direita.
        y_corda: y da corda no quadro.
        passo: passo da tela, em px do quadro.
        origem: ``(x0, y0)`` do painel no quadro.
        escala: ampliação da imagem.

    Returns:
        ``(área, extensão)``: a área de tinta na janela, em passos², e a largura do maior
        componente sobre o vão entre as caixas das duas notas (0 a 1). Arco e slide vão
        de uma nota à outra; pausa, barra e texto ficam no meio.
    """
    na, nb = notas[a], notas[b]
    x0, x1 = na["x_centro_quadro"], nb["x_centro_quadro"]
    if x1 <= x0:
        return 0.0, 0.0
    y0, y1 = y_corda - 1.6 * passo, y_corda + 1.2 * passo

    def img(x: float, y: float) -> tuple[int, int]:
        return round((x - origem[0]) * escala), round((y - origem[1]) * escala)

    c0, r0 = img(x0, y0)
    c1, r1 = img(x1, y1)
    h, w = tinta.shape
    r0, r1, c0, c1 = max(0, r0), min(h, r1), max(0, c0), min(w, c1)
    if r1 <= r0 or c1 <= c0:
        return 0.0, 0.0
    janela = tinta[r0:r1, c0:c1].copy()
    for n in notas:
        mx = meia_largura(n["casa"], passo)
        cy = y_da_corda_de(n, y_corda, passo)
        q0, p0 = img(n["x_centro_quadro"] - mx, cy - MEIA_ALTURA * passo)
        q1, p1 = img(n["x_centro_quadro"] + mx, cy + MEIA_ALTURA * passo)
        janela[max(0, p0 - r0) : max(0, p1 - r0), max(0, q0 - c0) : max(0, q1 - c0)] = (
            False
        )
    px = passo * escala
    vertical = cv2.morphologyEx(
        janela.astype(np.uint8),
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(3, round(0.9 * px)))),
    )
    janela &= ~vertical.astype(bool)
    n, _, stats, _ = cv2.connectedComponentsWithStats(janela.astype(np.uint8), 8)
    vao = max(
        0.3 * px,
        (x1 - x0 - meia_largura(na["casa"], passo) - meia_largura(nb["casa"], passo))
        * escala,
    )
    area, maior = 0, 0
    for k in range(1, n):
        largura, altura = stats[k, cv2.CC_STAT_WIDTH], stats[k, cv2.CC_STAT_HEIGHT]
        if largura >= LARGURA_MIN * px and altura <= ALTURA_MAX * px:
            area += int(stats[k, cv2.CC_STAT_AREA])
            maior = max(maior, int(largura))
    return area / px**2, min(1.0, maior / vao)


def y_da_corda_de(nota: dict, y_corda: float, passo: float) -> float:
    """y aproximado da corda de uma nota, a partir da corda do par.

    Args:
        nota: nota com ``corda`` e ``_corda_par`` (a corda do par em medição).
        y_corda: y da corda do par.
        passo: passo da tela.

    Returns:
        ``y_corda + (corda - corda_do_par) * passo``.
    """
    return y_corda + (nota["corda"] - nota.get("_corda_par", nota["corda"])) * passo


def recorte(
    imagem: np.ndarray,
    notas: Sequence[dict],
    a: int,
    b: int,
    y_corda: float,
    passo: float,
    origem: tuple[float, float],
    escala: float,
) -> np.ndarray:
    """Recorte do par para o olho (dono ou modelo de linguagem), com as duas notas
    sublinhadas em vermelho.

    Args:
        imagem: imagem BGR da tela.
        notas: notas da tela.
        a: índice da nota da esquerda.
        b: índice da nota da direita.
        y_corda: y da corda no quadro.
        passo: passo da tela.
        origem: ``(x0, y0)`` do painel no quadro.
        escala: ampliação da imagem.

    Returns:
        Recorte BGR.
    """
    na, nb = notas[a], notas[b]
    x0 = na["x_centro_quadro"] - 1.2 * passo
    x1 = nb["x_centro_quadro"] + 1.2 * passo
    y0, y1 = y_corda - 1.8 * passo, y_corda + 1.3 * passo
    h, w = imagem.shape[:2]
    c0 = max(0, round((x0 - origem[0]) * escala))
    c1 = min(w, round((x1 - origem[0]) * escala))
    r0 = max(0, round((y0 - origem[1]) * escala))
    r1 = min(h, round((y1 - origem[1]) * escala))
    out = imagem[r0:r1, c0:c1].copy()
    yl = round((y_corda + 0.6 * passo - origem[1]) * escala) - r0
    for n in (na, nb):
        mx = meia_largura(n["casa"], passo)
        q0 = round((n["x_centro_quadro"] - mx - origem[0]) * escala) - c0
        q1 = round((n["x_centro_quadro"] + mx - origem[0]) * escala) - c0
        cv2.line(out, (q0, yl), (q1, yl), (0, 0, 255), 3)
    return out


def processar(fonte: str, pasta: Path, pasta_ataque: Path, saida: Path) -> list[dict]:
    """Pares de uma fonte, com tinta e recorte gravado.

    Args:
        fonte: nome curto da fonte.
        pasta: pasta da ferramenta (``pre.json`` e ``telas/``).
        pasta_ataque: pasta com ``ataque_<fonte>.json`` conferido.
        saida: pasta de saída (recortes em ``recortes/``).

    Returns:
        Lista de pares (dicts).
    """
    gab = json.loads((pasta_ataque / f"ataque_{fonte}.json").read_text("utf-8"))
    pre = json.loads((pasta / "pre.json").read_text("utf-8"))
    telas_pre = {int(t["id"]): t for t in pre["telas"]}
    conferidas = {int(k) for k, v in (gab.get("telas_conferidas") or {}).items() if v}
    por_tela: dict[int, list[dict]] = {}
    for n in gab["notas"]:
        if n["tela"] in conferidas and str(n["casa"]).strip():
            por_tela.setdefault(n["tela"], []).append(dict(n))
    (saida / "recortes").mkdir(parents=True, exist_ok=True)
    pares = []
    for tid, notas in sorted(por_tela.items()):
        tp = telas_pre[tid]
        imagem = cv2.imread(str(pasta / tp["arquivo"]))
        tinta = mascara_de_tinta(cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY))
        passo, escala = float(tp["passo"]), float(tp["escala"])
        origem = (float(tp["painel"][0]), float(tp["painel"][1]))
        for a, b in pares_da_tela(notas, passo):
            corda = notas[a]["corda"]
            for n in notas:
                n["_corda_par"] = corda
            y = float(tp["linhas_y"][corda - 1])
            area, extensao = tinta_entre(tinta, notas, a, b, y, passo, origem, escala)
            nome = f"{fonte}_t{tid}_{notas[a]['nota']}_{notas[b]['nota']}.png"
            cv2.imwrite(
                str(saida / "recortes" / nome),
                recorte(imagem, notas, a, b, y, passo, origem, escala),
            )
            pares.append(
                {
                    "fonte": fonte,
                    "tela": tid,
                    "a": notas[a]["nota"],
                    "b": notas[b]["nota"],
                    "corda": corda,
                    "casas": [notas[a]["casa"], notas[b]["casa"]],
                    "ligado": notas[b]["ataque"] == "nao",
                    "motivo_b": notas[b]["motivo"],
                    "tinta": round(area, 4),
                    "extensao": round(extensao, 3),
                    "recorte": f"recortes/{nome}",
                }
            )
    return pares


def main() -> int:
    """Gera os pares de todas as fontes e grava ``pares.json``.

    Returns:
        0.
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--ataque", type=Path, default=caminhos.TAB_ROTULO / "r2" / "conferir"
    )
    ap.add_argument("--saida", type=Path, default=caminhos.TAB_ROTULO / "r3_pares")
    args = ap.parse_args()
    todos = []
    for fonte, slug in FONTES.items():
        p = processar(
            fonte, caminhos.SAIDA / "ouro_video" / slug, args.ataque, args.saida
        )
        lig = sum(x["ligado"] for x in p)
        print(fonte, len(p), "pares,", lig, "ligados")
        todos += p
    (args.saida / "pares.json").write_text(
        json.dumps(todos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

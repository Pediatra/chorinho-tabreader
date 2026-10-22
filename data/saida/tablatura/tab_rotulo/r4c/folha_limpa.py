"""R4c: folha limpa para o dono — vídeo real ao lado do gerador, um desenho por linha.

O gerador roda sem os distratores (ritmo, faixa, acordes, outras técnicas), só para
mostrar o estilo novo; no treino eles continuam. Uso (container):
env PYTHONPATH=/app python /app/data/saida/tab_rotulo/r4c/folha_limpa.py
"""

import random

import cv2
import numpy as np

from tab import caminhos, sintetico_sistema as G
from tab.detector_tab import FONTES_TREINO

ERROS = caminhos.TAB_ROTULO / "r4b" / "erros"
SAIDA = caminhos.TAB_ROTULO / "r4c"
ALTURA = 170
DESLIGAR = (
    "P_RITMO P_FAIXA P_ACORDE_NOME P_DIAGRAMA P_LET_RING P_PM P_TREM P_RASG P_ARPEJO "
    "P_HARMONICO P_BEND P_VIB P_ORN P_MORDENTE_TRES P_ZIGUE_SOZINHO P_COR_VOZ "
    "P_FUNDO_NOTA P_FORMULA P_GP_INICIO P_TAB P_MARCA_ACIMA P_DESFOQUE P_REESCALA "
    "P_LIGADA P_TIE P_SLIDE_SOLTO P_CASA_ALTA P_MUDO P_CORDA_TRACEJADA P_SERIF "
    "P_BARLINE_INTERNA P_PAUSA_INTERNA P_PAUSA_ENTRE P_RITORNELO P_VOLTA P_NAV "
    "P_FAIXA_AMARELA P_CURSOR_FINO P_ARCO_CENTRO P_ARCO_ABAIXO"
).split()
LINHAS = [
    ("1. TRACO: numeros pequenos e apertados; a corda aparece como '-' (3-0-3)",
     "folha_alarme_1.png", (19, 22),
     {"P_APERTADO": 1.0, "P_TRACO": 1.0, "P_TECNICA_PAR": 0.0}, "traco"),
    ("2. SLIDE CURTO: risco pequeno e inclinado entre dois numeros (1/2)",
     "folha_perdida_1.png", (5, 8),
     {"P_TECNICA_PAR": 0.5, "PESOS_PAR": (0, 0, 0.5, 0.5), "P_SLIDE_CURTO": 1.0},
     "slide"),
    ("3. ARCO LONGO E RASO: arco baixo ligando notas distantes",
     "folha_perdida_1.png", (0, 26),
     {"P_TECNICA_PAR": 0.5, "PESOS_PAR": (0.5, 0.5, 0, 0), "P_PAR_LONGO": 1.0,
      "P_ARCO_RASO": 1.0}, "arco"),
]


def ladrilho(arquivo: str, k: int) -> np.ndarray:
    """O recorte k (sem o texto) de uma folha de erros do R4b."""
    img = cv2.imread(str(ERROS / arquivo))
    r, c = divmod(k, 3)
    t = img[r * 142 + 22:(r + 1) * 142, c * 360:(c + 1) * 360]
    cols = np.flatnonzero((t < 250).any(axis=(0, 2)))
    return t[:, : cols.max() + 1] if cols.size else t


def alto(img: np.ndarray) -> np.ndarray:
    """Redimensiona para a altura da folha."""
    return cv2.resize(img, (max(1, int(img.shape[1] * ALTURA / img.shape[0])), ALTURA))


def recorte_gerado(semente: int, ajustes: dict, tipo: str) -> np.ndarray | None:
    """Um sistema limpo, recortado em volta do desenho novo."""
    originais = {n: getattr(G, n) for n in [*DESLIGAR, *ajustes]}
    try:
        for n in DESLIGAR:
            setattr(G, n, 0.0)
        for n, v in ajustes.items():
            setattr(G, n, v)
        img, info = G.gerar_sistema(random.Random(semente), FONTES_TREINO)
    finally:
        for n, v in originais.items():
            setattr(G, n, v)
    p = info["passo"]
    notas = info["notas"]
    if tipo == "traco":
        if "traco" not in info["variantes"]:
            return None
        por_corda = {}
        for n in notas:
            por_corda.setdefault(n["corda"], []).append(n["x"])
        corda, xs = max(por_corda.items(), key=lambda kv: len(kv[1]))
        x0, x1 = min(xs) - 1.0 * p, max(xs) + 1.0 * p
    else:
        alvo = [n for n in notas if n["tecnica"] in (("/", "\\") if tipo == "slide"
                                                     else ("h", "p"))]
        if tipo == "arco":
            alvo = [n for n in alvo if "arco_raso" in info["variantes"]]
        if not alvo:
            return None
        n = alvo[0]
        corda = n["corda"]
        esq = [m["x"] for m in notas if m["corda"] == corda and m["x"] < n["x"]]
        if tipo == "arco" and (not esq or n["x"] - max(esq) < 2.5 * p):
            return None
        x0 = (max(esq) if esq else n["x"] - 3 * p) - 1.2 * p
        x1 = n["x"] + 1.2 * p
        cx0, cy0, cx1, cy1 = n["caixa"]
        img = img.copy()
        cv2.line(img, (cx0, int(cy1 + 0.25 * p)), (cx1, int(cy1 + 0.25 * p)),
                 (0, 0, 230), max(1, int(p / 10)))
    y = info["linhas_y"][corda - 1]
    r0, r1 = int(max(0, y - 2.2 * p)), int(min(img.shape[0], y + 1.8 * p))
    return img[r0:r1, int(max(0, x0)):int(min(img.shape[1], x1))]


def faixa(texto: str, largura: int, cor: int = 235) -> np.ndarray:
    """Faixa de texto."""
    f = np.full((34, largura, 3), cor, np.uint8)
    cv2.putText(f, texto, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    return f


def main() -> int:
    """Monta e grava folha_limpa.png."""
    linhas = []
    for titulo, arquivo, ks, ajustes, tipo in LINHAS:
        reais = [alto(ladrilho(arquivo, k)) for k in ks]
        gerados, s = [], 0
        while len(gerados) < 3 and s < 3000:
            g = recorte_gerado(s, ajustes, tipo)
            if g is not None and g.size and g.shape[1] > 20:
                gerados.append(alto(g))
            s += 1
        sep = np.full((ALTURA, 30, 3), 255, np.uint8)
        meio = np.full((ALTURA, 6, 3), 0, np.uint8)
        pecas = []
        for r in reais:
            pecas += [r, sep]
        pecas.append(meio)
        for g in gerados:
            pecas += [sep, g]
        corpo = np.hstack(pecas)
        larg_real = sum(r.shape[1] + 30 for r in reais)
        rot = np.full((30, corpo.shape[1], 3), 255, np.uint8)
        cv2.putText(rot, "VIDEO REAL", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                    (150, 0, 0), 2)
        cv2.putText(rot, "GERADOR (o vermelho marca a nota sem ataque)",
                    (larg_real + 20, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 200), 2)
        linhas.append((faixa(titulo, corpo.shape[1]), rot, corpo))
    largura = max(c.shape[1] for _, _, c in linhas)
    blocos = []
    for f, r, c in linhas:
        for parte in (faixa_ajustada(f, largura), faixa_ajustada(r, largura),
                      faixa_ajustada(c, largura), np.full((24, largura, 3), 255, np.uint8)):
            blocos.append(parte)
    cv2.imwrite(str(SAIDA / "folha_limpa.png"), np.vstack(blocos))
    return 0


def faixa_ajustada(img: np.ndarray, largura: int) -> np.ndarray:
    """Completa a largura com branco (a faixa de título fica cinza até o fim)."""
    falta = largura - img.shape[1]
    if falta <= 0:
        return img
    valor = int(img[0, -1, 0]) if img.shape[0] == 34 else 255
    return np.pad(img, ((0, 0), (0, falta), (0, 0)), constant_values=valor)


if __name__ == "__main__":
    raise SystemExit(main())

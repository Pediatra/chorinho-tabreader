"""Cobertura do Audiveris por recorte contra o tamanho e a sujeira da imagem.

Pergunta do dono (2026-10-18): a qualidade da imagem pesa muito na leitura, sobretudo
com muitos elementos na tela? Junta os três gabaritos do dono (P1, sem produto, D1) e,
por recorte, cruza cobertura e precisão com a entrelinha (px no quadro original), a
fração de tinta e a fração de cor do recorte.

Só lê. Uso (no container, na raiz): python data/saida/partitura/diag/qualidade_imagem/medir.py
"""

import json
from pathlib import Path

import cv2
import numpy as np

from tab.caminhos import RAIZ

GABARITOS = ["leitura_p1", "leitura_sem_produto", "leitura_d1"]
SAIDA = Path(__file__).parent / "resultado.json"


def _entrelinha(png: Path, rid: str) -> float | None:
    """Entrelinha do recorte no quadro original, pelo indice.json da pasta do PNG."""
    indice = png.parent / "indice.json"
    if not indice.exists():
        return None
    for e in json.loads(indice.read_text(encoding="utf-8")):
        if e.get("id") in (png.stem, rid) and e.get("entrelinha"):
            return float(e["entrelinha"])
    return None


def _imagem(png: Path) -> dict:
    """Frações de tinta e de cor e a nitidez do recorte."""
    img = cv2.imread(str(png))
    cinza = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    cor = (hsv[..., 1] > 64) & (hsv[..., 2] > 76)
    return {
        "tinta": float((cinza < 128).mean()),
        "cor": float(cor.mean()),
        "nitidez": float(cv2.Laplacian(cinza, cv2.CV_64F).var()),
        "altura_px": int(img.shape[0]),
    }


def _spearman(a: list[float], b: list[float]) -> float:
    """Correlação de Spearman (postos, sem empate tratado)."""
    ra = np.argsort(np.argsort(a))
    rb = np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def main() -> None:
    """Mede e imprime a tabela por faixa de entrelinha e as correlações."""
    linhas = []
    for nome in GABARITOS:
        ouro = json.loads((RAIZ / "data/gold/partitura" / f"{nome}.json").read_text())
        itens = json.loads((RAIZ / ouro["fonte_itens"]).read_text())["itens"]
        por_id = {it["id"]: it for it in itens}
        for rid, r in ouro["recortes"].items():
            if not r.get("confirmado") or rid not in por_id:
                continue
            it = por_id[rid]
            png = RAIZ / it["png"]
            notas = [s for s in r["simbolos"] if not s["palpite"].get("pausa")]
            certos = sum(1 for s in notas if s["dono"] == "certo")
            faltando = len(r["faltando"])
            n_comp = max(1, len(it["compassos"]))
            linhas.append(
                {
                    "gabarito": nome,
                    "id": rid,
                    "canal": it.get("canal"),
                    "entrelinha": _entrelinha(png, rid),
                    **_imagem(png),
                    "lidas": len(notas),
                    "certas": certos,
                    "faltando": faltando,
                    "cobertura": certos / max(1, certos + faltando),
                    "precisao": certos / max(1, len(notas)),
                    "notas_por_compasso": (certos + faltando) / n_comp,
                }
            )
    SAIDA.write_text(json.dumps(linhas, ensure_ascii=False, indent=1), encoding="utf-8")
    com_e = [x for x in linhas if x["entrelinha"]]
    print(f"recortes: {len(linhas)} (com entrelinha: {len(com_e)})")
    faixas = [(0, 11), (11, 13), (13, 16), (16, 99)]
    print("entrelinha | recortes | certas/(certas+faltando) | certas/lidas")
    for lo, hi in faixas:
        g = [x for x in com_e if lo <= x["entrelinha"] < hi]
        if not g:
            continue
        c = sum(x["certas"] for x in g)
        f = sum(x["faltando"] for x in g)
        lid = sum(x["lidas"] for x in g)
        print(f"[{lo},{hi}) px | {len(g)} | {c}/{c + f} = {c / (c + f):.3f} | "
              f"{c}/{lid} = {c / max(1, lid):.3f}")
    cob = [x["cobertura"] for x in com_e]
    for chave in ("entrelinha", "tinta", "cor", "nitidez", "notas_por_compasso"):
        print(f"Spearman cobertura x {chave}: "
              f"{_spearman(cob, [x[chave] for x in com_e]):+.2f}")
    print("piores 8 (cobertura):")
    for x in sorted(com_e, key=lambda x: x["cobertura"])[:8]:
        print(f"  {x['cobertura']:.2f} {x['canal']} {x['id'][:26]} entrelinha "
              f"{x['entrelinha']} tinta {x['tinta']:.3f} cor {x['cor']:.3f} "
              f"notas/compasso {x['notas_por_compasso']:.1f}")


if __name__ == "__main__":
    main()

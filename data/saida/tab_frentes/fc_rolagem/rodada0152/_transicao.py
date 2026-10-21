"""Transição do kenneth 184,5–184,9 s (C4): salto entre o último e o primeiro quadro parados."""

import json
from pathlib import Path

import cv2
import numpy as np

from tab import leitor, rolagem_deslocamento, rolagem_saltos as rs

SAIDA = Path("/app/data/saida/tab_frentes/fc_rolagem/rodada0152/transicao_kenneth")
VIDEO = "/acervo/kenneth acoustic/location - khalid ｜ fingerstyle guitar ｜ tab + chords + lyrics.mp4"
RECORTE = (855, 1085)
XMAX = 1640


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    r = rs.medir(Path(VIDEO), 182.0, 5.0, 10.0, RECORTE, XMAX)
    pares = r["pares"]
    print("quadros", r["quadros"], "pares", len(pares))
    for p in pares:
        if 183.9 <= p["t_a"] <= 185.2:
            print(f"  par {p['t_a']:.1f}->{p['t_b']:.1f} rotulo={p['rotulo']} dx_a={p['dx_a']:.2f} resp={p['resp_a']:.2f}")
    antes = [p for p in pares if p["rotulo"] == "parado" and p["t_a"] < 184.5]
    depois = [p for p in pares if p["rotulo"] == "parado" and p["t_a"] >= 184.9]
    pa = antes[-1]
    pb = depois[0]
    ia, ib = pa["i"], pb["i"]
    tempos = r["tempos"]
    print("quadro antes", tempos[ia], "quadro depois", tempos[ib], "quadros parados entre:", ib - ia)
    x1 = r["x1"]
    frames = r["frames"]
    h, w = frames[ia].shape[:2]
    janela = cv2.createHanningWindow((w, h), cv2.CV_32F)
    m = rs.mascara(frames[ia]) | rs.mascara(frames[ib])
    ca = rs.cinza_mascarado(frames[ia], 0, x1, m)
    cb = rs.cinza_mascarado(frames[ib], 0, x1, m)
    dx, dy, resp = rolagem_deslocamento.deslocar(ca, cb, janela)
    dx_b, n_b = rs.casar(rs.barras(ca), rs.barras(cb))
    cons = rs.consenso(dx, dx_b)
    print(f"salto transicao: dx_a={dx:.2f} resp={resp:.2f} dx_b={dx_b} n_b={n_b} consenso={cons}")
    rel = {
        "video": VIDEO, "t0": 182.0, "dur": 5.0, "qps": 10.0, "recorte": list(RECORTE), "x_max": x1,
        "quadros_lidos": r["quadros"], "contagem_passos": {},
        "saltos": [{
            "i_antes": ia, "i_depois": ib, "dx_total": dx, "n_passos": 1,
            "t_antes": tempos[ia], "t_depois": tempos[ib], "dx_b_total": dx_b,
            "barras_casadas_total": n_b, "sobreposicao": bool(rs.sobrepoe(rs.barras(ca), rs.barras(cb), dx)),
            "dx_consenso": cons, "ultrapassa_limite_passos": False,
        }],
    }
    (SAIDA / "saltos.json").write_text(json.dumps(rel, ensure_ascii=False, indent=1), encoding="utf-8")
    print("gravado", SAIDA / "saltos.json")


if __name__ == "__main__":
    main()

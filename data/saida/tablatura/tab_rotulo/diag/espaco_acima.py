"""Diagnóstico: espaço acima da corda 1 (e abaixo da 6) no recorte que o modelo recebe.

Para cada tela da T8.3: o painel do produto (escolher_ou_mascara), linhas_y no recorte, e o
espaço em passos entre o topo do recorte e a corda 1 (o modelo lê até 2,5 passos; o resto é
preenchido). Uso (container): env PYTHONPATH=/app python /app/data/saida/tab_rotulo/diag/espaco_acima.py
"""

import json

import numpy as np

from tab import caminhos, leitor, painel

INDICE = caminhos.SAIDA / "t83" / "ferramenta" / "indice.json"


def main() -> int:
    acima, abaixo = [], []
    for r in json.loads(INDICE.read_text(encoding="utf-8")):
        q = leitor.quadro_em(str(caminhos.acervo() / r["video"]), float(r["t"]))
        c = painel.escolher_ou_mascara(q) if q is not None else None
        if c is None:
            print(r["id"], "sem painel")
            continue
        ly, p, h = c.grade.linhas_y, c.passo, c.roi.shape[0]
        a, b = ly[0] / p, (h - ly[-1]) / p
        acima.append(a)
        abaixo.append(b)
        print(f"tela {r['id']:2d} {r['canal'][:22]:22s} passo {p:5.1f} y0 {c.y0:4d} "
              f"acima {a:4.2f} abaixo {b:4.2f} roi {c.roi.shape[:2]}")
    print("acima: mediana", round(float(np.median(acima)), 2), "min", round(min(acima), 2),
          "max", round(max(acima), 2))
    print("abaixo: mediana", round(float(np.median(abaixo)), 2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

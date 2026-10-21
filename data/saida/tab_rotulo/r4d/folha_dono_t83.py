"""0207: as notas que o dono marcou "nao/prolongamento" no modo ataque da T8.3, com contexto.

Recorte largo do quadro (nota em verde, caixa da região do dono em laranja), para o dono dizer se
o arco sai da nota (atacada, "sustentada") ou chega nela (prolongamento).
Uso (container): python /app/data/saida/tab_rotulo/r4d/folha_dono_t83.py [saida.png nota ...]
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

R = Path("/app/data/saida")
GAB = R / "tab_rotulo/r2/conferir_t83/ataque_t83.json"
CONF = R / "t83/ferramenta/conferencia_t83.json"
IND = R / "t83/ferramenta/indice.json"
SAIDA = R / "tab_rotulo/r4d/erros_t83/folha_dono_prolongamento.png"


def main() -> None:
    """Grava a folha."""
    notas = json.loads(GAB.read_text())["notas"]
    if len(sys.argv) > 2:
        gab = [n for n in notas if n["nota"] in sys.argv[2:]]
    else:
        gab = [n for n in notas if n.get("fonte") == "dono" and n["motivo"] == "prolongamento"]
    conf = {t["id"]: t for t in json.loads(CONF.read_text())["telas"]}
    ind = {r["id"]: r for r in json.loads(IND.read_text())}
    blocos = []
    for k, n in enumerate(gab, 1):
        pasta = R.parent.parent / ind[n["tela"]]["pasta"]
        tela = json.loads((pasta / "tela.json").read_text())
        img = cv2.imread(str(pasta / "quadro.png"))
        p, ly = tela["passo"], tela["linhas_y"]
        y = ly[n["corda"] - 1]
        reg = conf[n["tela"]]["regioes"][int(n["regiao"].split("-r")[1])]
        for c in range(reg["cordas"][0], reg["cordas"][1] + 1):
            yc = ly[c - 1]
            cv2.rectangle(img, (int(reg["x_quadro"][0]), int(yc - p / 2)),
                          (int(reg["x_quadro"][1]), int(yc + p / 2)), (0, 140, 255), 2)
        x = n["x_centro_quadro"]
        cv2.line(img, (int(x - 0.4 * p), int(y + 0.6 * p)), (int(x + 0.4 * p), int(y + 0.6 * p)),
                 (0, 170, 0), 3)
        x0, x1 = int(max(0, x - 8 * p)), int(min(img.shape[1], x + 8 * p))
        y0, y1 = int(max(0, ly[0] - 2.5 * p)), int(min(img.shape[0], ly[-1] + 1.5 * p))
        sub = img[y0:y1, x0:x1]
        esc = 640 / sub.shape[1]
        sub = cv2.resize(sub, (640, int(sub.shape[0] * esc)))
        faixa = np.full((30, 640, 3), 255, np.uint8)
        cv2.putText(faixa, f"{k}. {n['nota']} casa {n['casa']}", (5, 21),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
        blocos.append(np.vstack([faixa, sub]))
    h = max(b.shape[0] for b in blocos)
    blocos = [np.pad(b, ((0, h - b.shape[0]), (0, 0), (0, 0)), constant_values=255) for b in blocos]
    if len(blocos) % 2:
        blocos.append(np.full_like(blocos[0], 255))
    linhas = [np.hstack([blocos[i], np.full((h, 12, 3), 255, np.uint8), blocos[i + 1]])
              for i in range(0, len(blocos), 2)]
    cv2.imwrite(str(SAIDA.with_name(sys.argv[1]) if len(sys.argv) > 2 else SAIDA), np.vstack(linhas))
    print([n["nota"] for n in gab])


if __name__ == "__main__":
    main()

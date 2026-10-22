"""0207, diagnóstico: as notas "não" da T8.3 que a faixa do _atqt lê como "sim".

Dobra 0, sementes 1–3, faixa de ``tab.ataque_rotulo`` (0,02 / 0,15 e a regra do slide).
Para cada nota "não" do gabarito: o rótulo e o maior ``tecnica_p`` sem ataque por semente.
Grava r4d/erros_t83/erros.json e folha_escapa_<k>.png (nota em verde, vizinha em azul).

Uso (container): env PYTHONPATH=/app python /app/data/saida/tab_rotulo/r4d/folha_erros_t83.py
"""

import json
import sys
from collections import Counter

import cv2
import numpy as np

sys.path.insert(0, "/app/data/saida/tab_rotulo/r4c")

from folha_erros import recorte  # noqa: E402

from tab import ataque_r4 as A  # noqa: E402
from tab import ataque_rotulo, caminhos, detector_tab, leitor, painel  # noqa: E402
from tab.ataque_base import parear  # noqa: E402

GAB = caminhos.TAB_ROTULO / "r2" / "conferir_t83" / "ataque_t83.json"
INDICE = caminhos.SAIDA / "t83" / "ferramenta" / "indice.json"
VERSAO = sys.argv[1] if len(sys.argv) > 1 else "atqt"
SAIDA = caminhos.TAB_ROTULO / "r4d" / ("erros_t83" if VERSAO == "atqt" else f"erros_t83_{VERSAO}")
SUP = [detector_tab.TECNICAS_MODELO.index(t) for t in A.TECNICAS_SUPERVISIONADAS]


def main() -> int:
    """Mede e grava."""
    SAIDA.mkdir(parents=True, exist_ok=True)
    modelos = {s: detector_tab.carregar(A.modelo_da_dobra(VERSAO, 0, s)) for s in (1, 2, 3)}
    indice = {int(r["id"]): r for r in json.loads(INDICE.read_text(encoding="utf-8"))}
    gab = A.gabarito_por_tela(GAB)
    linhas, imgs = [], []
    for tela, notas in sorted(gab.items()):
        r = indice[tela]
        quadro = leitor.quadro_em(str(caminhos.acervo() / r["video"]), float(r["t"]))
        c = painel.escolher_ou_mascara(quadro) if quadro is not None else None
        if c is None:
            continue
        por_s = {}
        for s, m in modelos.items():
            pred = detector_tab.detectar(m, c.roi, c.grade.linhas_y, c.passo, com_escores=True)
            for p in pred:
                p["x_centro_quadro"] = float(p["x"]) + c.x0
            rot = ataque_rotulo.rotular(pred, c.passo)
            por_s[s] = {
                i: (rot[j][0], round(max(pred[j]["tecnica_p"][k] for k in SUP), 4),
                    {t: round(pred[j]["tecnica_p"][detector_tab.TECNICAS_MODELO.index(t)], 4)
                     for t in A.TECNICAS_SUPERVISIONADAS})
                for i, j in parear(notas, pred, c.passo).items()
            }
        for i, n in enumerate(notas):
            if n["ataque"] != "nao":
                continue
            prev = [por_s[s].get(i, ("nao_lida", None, None)) for s in (1, 2, 3)]
            n_sim = sum(1 for v in prev if v[0] == "sim")
            linha = {"tela": tela, "canal": r["canal"], "nota": n["nota"], "corda": n["corda"],
                     "casa": n["casa"], "motivo": n["motivo"],
                     "previsto": [v[0] for v in prev], "escore": [v[1] for v in prev],
                     "tecnicas_s1": prev[0][2], "escapa": n_sim >= 2}
            linhas.append(linha)
            if linha["escapa"]:
                viz = [m for m in notas if m["corda"] == n["corda"]
                       and m["x_centro_quadro"] < n["x_centro_quadro"]]
                vizinha = max(viz, key=lambda m: m["x_centro_quadro"]) if viz else None
                esc = [v[1] for v in prev if v[1] is not None]
                rotulo = f"t{tela} {r['canal'][:16]} {n['nota']} {n['motivo']} esc {max(esc)}"
                imgs.append(recorte(c.roi, c.x0, c.grade.linhas_y, c.passo, n, vizinha, rotulo))
        print(tela, r["canal"], flush=True)
    (SAIDA / "erros.json").write_text(json.dumps(linhas, ensure_ascii=False, indent=1))
    for k in range(0, len(imgs), 30):
        bloco = imgs[k:k + 30]
        while len(bloco) % 3:
            bloco.append(np.full_like(bloco[0], 255))
        grade = np.vstack([np.hstack(bloco[q:q + 3]) for q in range(0, len(bloco), 3)])
        cv2.imwrite(str(SAIDA / f"folha_escapa_{k // 30 + 1}.png"), grade)
    print("escapam:", sum(ln["escapa"] for ln in linhas), "de", len(linhas))
    print(Counter((ln["motivo"], ln["escapa"]) for ln in linhas))
    for ln in linhas:
        if ln["escapa"]:
            print(ln["tela"], ln["canal"], ln["nota"], ln["motivo"], ln["escore"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

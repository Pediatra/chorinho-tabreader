"""0206, piloto: o arco do modelo-piloto nas notas "não" que escapam na faixa da 0205.

T8.2 pela dobra 0. Para cada nota do gabarito: a leitura do _atqg s1 com a faixa (L = 0,02,
técnica 0,15 e a regra do slide) e o ``arco_esq`` do piloto (_arcop_s1). Mostra o arco nas
notas "não" lidas como "sim" (as que escapam) e a separação entre as notas "não" e "sim".

Uso (container): env PYTHONPATH=/app python /app/data/saida/tab_rotulo/a2/medir_piloto.py
"""

import json

import numpy as np

from tab import ataque_r4 as A
from tab import ataque_rotulo, caminhos, detector_tab, leitor, painel
from tab.ataque_base import parear

PILOTO = caminhos.ARTEFATOS / "detector_tab_final_arcop_s1" / "modelo.pt"
SAIDA = caminhos.TAB_ROTULO / "a2" / "piloto.json"


def ler(modelo, c) -> list[dict]:
    """Notas de um painel, com tecnica_p e arco_esq, x no quadro."""
    out = detector_tab.detectar(
        modelo, c.roi, c.grade.linhas_y, c.passo, com_escores=True
    )
    for n in out:
        n["x_centro_quadro"] = float(n["x"]) + c.x0
    return out


def main() -> int:
    """Mede e grava piloto.json."""
    base = detector_tab.carregar(ataque_rotulo.DETECTOR_CALIBRADO)
    piloto = detector_tab.carregar(PILOTO)
    r2 = caminhos.TAB_ROTULO / "r2"
    ferr = caminhos.SAIDA / "t82" / "ferramenta"
    indice = {int(r["id"]): r for r in json.loads((ferr / "indice.json").read_text())}
    gab = A.gabarito_por_tela(r2 / "conferir_novos" / "ataque_t82.json")
    linhas = []
    for tela, notas in sorted(gab.items()):
        r = indice[tela]
        quadro = leitor.quadro_em(str(caminhos.acervo() / r["video"]), float(r["t"]))
        c = painel.escolher_ou_mascara(quadro) if quadro is not None else None
        if c is None:
            continue
        pb, pp = ler(base, c), ler(piloto, c)
        rot = ataque_rotulo.rotular(pb, c.passo)
        par_b, par_p = parear(notas, pb, c.passo), parear(notas, pp, c.passo)
        for i, n in enumerate(notas):
            if i not in par_b or i not in par_p:
                continue
            linhas.append(
                {
                    "tela": tela,
                    "canal": r["canal"],
                    "nota": n["nota"],
                    "motivo": n["motivo"],
                    "ouro": n["ataque"],
                    "faixa": rot[par_b[i]][0],
                    "arco_esq": pp[par_p[i]]["arco_esq"],
                }
            )
    SAIDA.write_text(json.dumps(linhas, ensure_ascii=False, indent=1))
    escapam = [ln for ln in linhas if ln["ouro"] == "nao" and ln["faixa"] == "sim"]
    print("escapam (nao lido sim pela faixa):", len(escapam))
    for ln in escapam:
        print("  ", ln["canal"], ln["nota"], ln["motivo"], "arco_esq", ln["arco_esq"])
    acima = sum(1 for ln in escapam if (ln["arco_esq"] or 0) > 0.5)
    print(f"arco > 0,5 em {acima}/{len(escapam)}")
    for ouro in ("nao", "sim"):
        v = [ln["arco_esq"] for ln in linhas if ln["ouro"] == ouro and ln["arco_esq"] is not None]
        if v:
            q = np.percentile(v, [50, 90, 99])
            print(ouro, len(v), "mediana/p90/p99", [round(float(x), 3) for x in q],
                  "frac>0,5", round(float(np.mean(np.array(v) > 0.5)), 4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""T8.2 com o modelo final antigo e o novo: relê as telas conferidas pelo dono e compara.

As 35 telas são de canais fora do treino dos dois modelos finais, então a medida é honesta.
O gabarito é ``data/saida/t82/ferramenta/conferencia_t82.json`` (só telas ``conferida``).
Pareamento: mesma corda, |dx| <= 0,5 passo, guloso pela menor distância.

Uso (container): python /app/data/saida/fase8/ger/t82_comparar.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, "/app")
from tab import caminhos, detector_tab, leitor, painel  # noqa: E402

RAIZ = Path("/app")
FERR = RAIZ / "data" / "saida" / "t82" / "ferramenta"
MODELOS = {
    "antigo": RAIZ / "artefatos" / "detector_tab_final_s1" / "modelo.pt",
    "novo": RAIZ / "artefatos" / "detector_tab_final_s1_ger" / "modelo.pt",
}


def parear(ouro: list[dict], pred: list[dict], passo: float) -> list[tuple[int, int]]:
    """Pares (índice ouro, índice pred) por corda e distância."""
    cand = sorted(
        (abs(g["x_centro_quadro"] - p["x_centro_quadro"]), i, j)
        for i, g in enumerate(ouro)
        for j, p in enumerate(pred)
        if g["corda"] == p["corda"]
        and abs(g["x_centro_quadro"] - p["x_centro_quadro"]) <= 0.5 * passo
    )
    gi, pj, pares = set(), set(), []
    for _, i, j in cand:
        if i in gi or j in pj:
            continue
        gi.add(i)
        pj.add(j)
        pares.append((i, j))
    return pares


def main() -> int:
    """Relê, pareia e imprime a tabela por modelo e por tela."""
    conf = json.loads((FERR / "conferencia_t82.json").read_text(encoding="utf-8"))
    indice = {
        r["id"]: r
        for r in json.loads((FERR / "indice.json").read_text(encoding="utf-8"))
    }
    modelos = {k: detector_tab.carregar(v) for k, v in MODELOS.items()}
    tot = {k: {"ouro": 0, "entregues": 0, "casadas": 0, "casa_certa": 0} for k in modelos}
    erros = {k: [] for k in modelos}
    n_telas = 0
    for tela in conf["telas"]:
        if not tela.get("conferida"):
            continue
        r = indice[tela["id"]]
        quadro = leitor.quadro_em(str(caminhos.acervo() / r["video"]), r["t"])
        c = painel.escolher_ou_mascara(quadro)
        if c is None:
            print("sem painel na tela", tela["id"], flush=True)
            continue
        n_telas += 1
        ouro = tela["notas"]
        for k, m in modelos.items():
            pred = [
                {
                    "corda": int(d["corda"]),
                    "casa": str(d["rotulo"]),
                    "x_centro_quadro": float(d["x"]) + c.x0,
                }
                for d in detector_tab.detectar(m, c.roi, c.grade.linhas_y, c.passo)
            ]
            pares = parear(ouro, pred, c.passo)
            t = tot[k]
            t["ouro"] += len(ouro)
            t["entregues"] += len(pred)
            t["casadas"] += len(pares)
            for i, j in pares:
                if str(ouro[i]["casa"]) == pred[j]["casa"]:
                    t["casa_certa"] += 1
                else:
                    erros[k].append(
                        (tela["id"], r["canal"], ouro[i]["corda"], ouro[i]["casa"],
                         pred[j]["casa"])
                    )
            gi = {i for i, _ in pares}
            pj = {j for _, j in pares}
            erros[k] += [
                (tela["id"], r["canal"], p["corda"], "-", p["casa"])
                for j, p in enumerate(pred)
                if j not in pj
            ]
            erros[k] += [
                (tela["id"], r["canal"], g["corda"], g["casa"], "-")
                for i, g in enumerate(ouro)
                if i not in gi
            ]
    print("telas", n_telas)
    for k, t in tot.items():
        print(
            f"{k}: ouro {t['ouro']} entregues {t['entregues']} casadas {t['casadas']} "
            f"casa {t['casa_certa']}/{t['casadas']}={t['casa_certa'] / t['casadas']:.4f} "
            f"precisao {t['casadas'] / t['entregues']:.4f} "
            f"revocacao {t['casadas'] / t['ouro']:.4f} "
            f"inventadas {t['entregues'] - t['casadas']} perdidas {t['ouro'] - t['casadas']}"
        )
    saida = RAIZ / "data" / "saida" / "tab_frentes" / "f0_tecnica" / "ca1" / "t82_comparar.json"
    saida.write_text(
        json.dumps({"total": tot, "erros": erros}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

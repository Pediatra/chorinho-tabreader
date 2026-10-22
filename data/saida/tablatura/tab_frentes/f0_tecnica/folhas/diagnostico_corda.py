"""Diagnóstico da F0.1 (não muda a régua): as perdas (a) com alcance vazio.

Para cada perda (a) de classe medida, conta se há nota prevista na faixa de x da região
(qualquer corda) e, dessas, quantas têm técnica, e em qual corda relativa à região (dentro
ou na vizinhança de 1 corda). Não altera a régua: a regra de casamento segue a 0,5 e as
causas da rodada 0101. Grava ``diagnostico_corda.json`` nesta pasta.
"""

import json
from collections import Counter
from pathlib import Path

from tab import caminhos, detector_tab
from tab import tecnica_regua as tr

PASTA = caminhos.TAB_FRENTE_0 / "folhas"
CLASSES = ("h", "p", "mordente", "prolongamento", "slide", "harm", "bend", "arpejo", "rasgueado")


def main() -> None:
    """Conta as perdas (a) por alcance e grava o diagnóstico."""
    rel = json.loads((PASTA.parent / "regua_tecnica.json").read_text(encoding="utf-8"))
    linhas = [ln for ln in rel["linhas_primaria"] if ln["classe"] in CLASSES and ln["causa"] == "a"]
    chaves = {(ln["fonte"], ln["tela"]) for ln in linhas}
    telas = {(t.fonte, t.id): t for t in tr.carregar_telas() if (t.fonte, t.id) in chaves}
    modelo = detector_tab.carregar(caminhos.DETECTOR_PADRAO)
    reserva = rel["telas_lidas"]["passo_reserva"]
    folga = rel["folga"]["usada"]
    contagem: Counter = Counter()
    casos = []
    for ln in linhas:
        tela = telas[(ln["fonte"], ln["tela"])]
        lido = tr.ler_tela(tela, {"primaria": modelo})
        passo = lido.passo or reserva
        notas = lido.notas["primaria"]
        r = next(x for x in tela.regioes if x.indice == ln["indice"])
        alcance = tr.notas_no_alcance(r, notas, passo, folga)
        if alcance:
            contagem[(ln["classe"], "alcance_com_nota")] += 1
            continue
        a, b = r.cordas
        faixa = [
            n
            for n in notas
            if r.x0 - folga * passo <= n["x"] <= r.x1 + folga * passo
        ]
        com_tec = [n for n in faixa if n["tecnica"]]
        vizinha = [n for n in com_tec if a - 1 <= n["corda"] <= b + 1]
        dono_fora = [n for n in tela.notas_dono if r.x0 <= n["x"] <= r.x1 and not a <= n["corda"] <= b]
        chave = "alcance_vazio_com_tecnica_vizinha" if vizinha else "alcance_vazio_sem_tecnica_vizinha"
        contagem[(ln["classe"], chave)] += 1
        casos.append(
            {
                "fonte": ln["fonte"],
                "tela": ln["tela"],
                "indice": ln["indice"],
                "classe": ln["classe"],
                "cordas_regiao": [a, b],
                "notas_na_faixa_x": [{"corda": n["corda"], "tecnica": n["tecnica"]} for n in faixa],
                "notas_do_dono_fora_das_cordas": [{"corda": n["corda"], "casa": n["rotulo"]} for n in dono_fora],
                "classe_vizinha": chave,
            }
        )
    resumo = {f"{k[0]}|{k[1]}": v for k, v in sorted(contagem.items())}
    total_a = len(linhas)
    vazias = sum(v for k, v in contagem.items() if k[1].startswith("alcance_vazio"))
    saida = {
        "perdas_a_medidas": total_a,
        "alcance_vazio": vazias,
        "resumo": resumo,
        "casos": casos,
    }
    (PASTA / "diagnostico_corda.json").write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
    print("perdas a", total_a, "alcance vazio", vazias)
    for k, v in resumo.items():
        print(k, v)


if __name__ == "__main__":
    main()

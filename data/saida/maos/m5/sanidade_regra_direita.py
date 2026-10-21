"""Sanidade indicativa da regra da mão direita contra o gabarito de dedos do M2.

Para cada nota física do gabarito M2 (dedup e exclusões pelo avaliador), monta o compasso
tocado dela no produto do MVP (mesma tela, compasso e exibição), roda a regra e compara o
dedo previsto com o ``direita`` do dono. Ignora ``?``. Não ajusta nada: só relata.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from tab.caminhos import GABARITO_DEDOS, MVP
from tab.maos_avaliar_dedos import carregar_json, notas_fisicas
from tab.maos_regra_direita import atribuir_dedos_direita

SAIDA = Path(__file__).resolve().parent / "sanidade_regra_direita.json"
DEDOS = ("p", "i", "m", "a")


def main() -> None:
    """Roda a comparação e imprime e grava o resultado."""
    gabarito = carregar_json(GABARITO_DEDOS)
    notas_m2, meta = notas_fisicas(gabarito)
    mvp = carregar_json(MVP)["notas"]

    por_compasso: dict[tuple, list[dict]] = {}
    for j, nota in enumerate(mvp):
        if nota.get("t_ini") is None or nota.get("compasso") is None:
            continue
        chave = (nota["tela"], nota["compasso"], nota["exibicao"])
        por_compasso.setdefault(chave, []).append(
            {"corda": nota["corda"], "casa": nota["casa"], "t_ini": nota["t_ini"], "indice": j}
        )

    linhas = []
    divergencias_posicao = []
    for nota in notas_m2:
        esperado = nota["direita"]
        if esperado == "?" or esperado is None:
            continue
        mvp_nota = mvp[nota["indice_mvp"]]
        if (mvp_nota["corda"], mvp_nota["casa"]) != (nota["corda"], nota["casa"]):
            divergencias_posicao.append(nota["id"])
        chave = (mvp_nota["tela"], mvp_nota["compasso"], mvp_nota["exibicao"])
        compasso = por_compasso[chave]
        previstos = atribuir_dedos_direita(compasso)
        alvo = next(p for p in previstos if p["indice"] == nota["indice_mvp"])
        linhas.append(
            {
                "id": nota["id"],
                "indice_mvp": nota["indice_mvp"],
                "corda": nota["corda"],
                "casa": nota["casa"],
                "t_ini": nota["t_ini"],
                "previsto": alvo["dedo"],
                "dono": esperado,
                "regra": alvo["regra"],
                "notas_no_compasso": len(compasso),
            }
        )

    acertos = sum(1 for x in linhas if x["previsto"] == x["dono"])
    confusao = Counter((x["dono"], x["previsto"]) for x in linhas)
    matriz = {
        dono: {previsto: confusao.get((dono, previsto), 0) for previsto in DEDOS}
        for dono in DEDOS
    }
    erros = [x for x in linhas if x["previsto"] != x["dono"]]
    regras_erradas = Counter(x["regra"] for x in erros)
    regras_todas = Counter(x["regra"] for x in linhas)

    resultado = {
        "avaliadas": len(linhas),
        "acertos": acertos,
        "contagem_avaliador": meta["contagem"],
        "avisos_avaliador": meta["avisos"],
        "divergencias_de_posicao": divergencias_posicao,
        "matriz_dono_x_previsto": matriz,
        "regra_em_todas": dict(regras_todas),
        "regra_nos_erros": dict(regras_erradas),
        "erros": erros,
    }
    SAIDA.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"acertos {acertos}/{len(linhas)}")
    print("matriz (linhas = dono, colunas = previsto)")
    print("      " + "  ".join(f"{d:>3}" for d in DEDOS))
    for dono in DEDOS:
        print(f"{dono:>5} " + "  ".join(f"{matriz[dono][p]:>3}" for p in DEDOS))
    print(f"divergências de corda/casa entre gabarito e MVP: {divergencias_posicao}")
    print("erros (id, corda, casa, previsto, dono, regra):")
    for x in erros:
        print(
            f"  {x['id']:>8} c{x['corda']} k{x['casa']} prev={x['previsto']} "
            f"dono={x['dono']} | {x['regra']}"
        )
    print(f"regras que decidiram: {dict(regras_todas)}")
    print(f"gravado em {SAIDA}")


if __name__ == "__main__":
    main()

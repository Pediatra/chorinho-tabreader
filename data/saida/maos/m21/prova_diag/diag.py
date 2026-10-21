"""Diagnóstico pós-prova 1022: erros por quadro (não muda o veredito)."""

import json

from tab import maos_braco_detector as d

entradas = d._entradas_prova()
saida = []
for semente in d.SEMENTES_FINAIS:
    with d._trava_gpu():
        modelo, _ = d._carregar_pesos(f"A3_100_todos_s{semente}", d.PASSOS)
        mapas = d.prever_mapas(modelo, [e["faixa"] for e in entradas])
    for e, m in zip(entradas, mapas, strict=True):
        for versao in (1, 2):
            dec = d.decodificar_versao(m, versao)
            classe, medida = d._medir(dec, e["matriz"], e["marcas"])
            saida.append({"semente": semente, "v": versao, "id": e["id"],
                          "canal": e["canal"], "classe": classe, "erros": medida,
                          "n_trastes": len(dec.get("trastes", []) or [])})
json.dump(saida, open("data/saida/maos/m21/prova_diag/por_quadro.json", "w"),
          ensure_ascii=False, indent=1)

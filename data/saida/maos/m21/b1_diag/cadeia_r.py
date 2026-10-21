"""Diagnóstico 1024 (não é portão): cadeia completa nos R de validação, contra o R."""

import json
from pathlib import Path

from tab import maos_braco_localizador as L
from tab.maos_braco_detector import (
    DIR_PESOS, _carregar_pesos, _imagem, _ler_json, _nome_unidade, canais_g,
)

indice = {c: k for k, c in enumerate(canais_g())}
regs = [r for r in L._registros() if r["origem"] == "R" and r["canal"] in L.CANAIS_VALIDACAO]
d2 = {q["id"]: q["classe_v2"] for q in _ler_json(L.MAOS_M21 / "d2_r_fora.json")["quadros"]}
saida = []
with L._trava_gpu():
    loc = L._carregar_localizador(L.NOME_LOCALIZADOR_VALIDACAO)
    dois = {}
    for r in regs:
        c = r["canal"]
        if c not in dois:
            nome = _nome_unidade("A3", "100", indice[c], 1)
            dois[c], _ = _carregar_pesos(nome, _ler_json(DIR_PESOS / f"{nome}.json")["passos"])
        res = L.cadeia(loc, dois[c], _imagem(Path(r["caminho"])), r["id"])
        saida.append({"id": r["id"], "canal": c, "classe": L._classe(res, r["marcas"]),
                      "sinalizado": L.sinalizado(res), "classe_faixa_rotulo": d2.get(r["id"])})
json.dump(saida, open("data/saida/maos/m21/b1_diag/cadeia_r.json", "w"), indent=1)

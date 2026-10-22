"""Aplica a releitura da página 10 (linhas certas) no pre.json e no ouro (página sem trabalho do dono)."""

import json
from pathlib import Path

from tab.ouro_video import _tela_do_modelo, gravar_atomico, montar_ouro, validar_ouro

S = "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar"
lido = json.load(open("data/saida/fase8/conserto/gymno_p10_lido.json"))
pre_p = Path(f"data/saida/ouro_video/{S}/pre.json")
ouro_p = Path(f"data/gold/ouro_video/{S}.json")
pre = json.loads(pre_p.read_text())
ouro = json.loads(ouro_p.read_text())
tp = next(t for t in pre["telas"] if t["id"] == 10)
for k in ("passo", "linhas_y", "notas", "nao_nota"):
    tp[k] = lido[k]
estado = ouro["ferramenta"]
i = next(i for i, t in enumerate(estado["telas"]) if t["id"] == 10)
velha = estado["telas"][i]
assert not velha["conferida"] and all(
    n["origem"] == "modelo" and not n["removida"] for n in velha["notas"]
), "a página 10 tem trabalho do dono"
nova = _tela_do_modelo({"id": 10, "notas": lido["notas"]})
estado["telas"][i] = nova
for ini in (pre.get("estado_inicial") or {}).get("telas", []):
    if ini["id"] == 10:
        ini["notas"] = nova["notas"]
novo = montar_ouro(pre, estado)
assert not validar_ouro(novo), validar_ouro(novo)
gravar_atomico(pre_p, pre)
gravar_atomico(ouro_p, novo)
print("ok", len(nova["notas"]), "notas na página 10")

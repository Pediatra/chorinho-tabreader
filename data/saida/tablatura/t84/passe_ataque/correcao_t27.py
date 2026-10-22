"""T8.4: o "0" depois de cada arco "p" da tela 27 é não atacado (pull-off), pela palavra do dono.

O dono desenhou as regiões t27-r0 e t27-r1 na altura da corda 1, em cima do arco, e as notas
estão nas cordas 2 e 3: a conversão (que procura nota na corda da região) não as ligou, e as
notas ficaram "atacadas". Dono, 2026-10-22, no chat: "Sim e pull off eu marquei".
Grava uma cópia antes (ataque_t84_antes_t27.json) e muda só essas 2 notas.
"""

import json
from pathlib import Path

A = Path("/app/data/saida/tablatura/tab_rotulo/r2/conferir_t84/ataque_t84.json")
COPIA = A.with_name("ataque_t84_antes_t27.json")
#: nota -> (corda, casa, x_centro_quadro esperados, região do dono)
DONO = {"t27-n62": (2, 0, 729.5, "t27-r0"), "t27-n66": (3, 0, 838.4, "t27-r1")}

doc = json.loads(A.read_text(encoding="utf-8"))
assert len([v for v in doc["telas_conferidas"].values() if v]) == 29
assert not COPIA.exists()
COPIA.write_bytes(A.read_bytes())
for n in doc["notas"]:
    if n["nota"] in DONO:
        corda, casa, x, regiao = DONO[n["nota"]]
        assert (n["corda"], n["casa"], n["x_centro_quadro"]) == (corda, casa, x), n
        assert (n["ataque"], n["motivo"]) == ("sim", "normal"), n
        n.update(ataque="nao", motivo="p", regiao=regiao)
        print("corrigida", n["nota"])
A.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

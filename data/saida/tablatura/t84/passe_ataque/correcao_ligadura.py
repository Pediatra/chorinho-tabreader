"""T8.4: o primeiro número de uma ligadura é atacado, com ou sem segundo número.

Dono, 2026-10-22, no chat: "quando não há segundo número em uma ligadura é a mesma coisa
que quando tem dois números considere o primeiro como atacado". No passe do modo ataque
estas 4 notas (o arco sai delas e não chega em nenhum número) ficaram "nao/prolongamento";
voltam para "sim/sustentada", o valor do pré-preenchimento. Cópia antes:
ataque_t84_antes_ligadura.json.
"""

import json
from pathlib import Path

A = Path("/app/data/saida/tablatura/tab_rotulo/r2/conferir_t84/ataque_t84.json")
COPIA = A.with_name("ataque_t84_antes_ligadura.json")
#: nota -> (corda, casa, x_centro_quadro)
DONO = {"t13-n6": (3, 4, 444.7), "t13-n7": (3, 4, 652.4), "t13-n13": (3, 2, 1148.2),
        "t23-n4": (2, 2, 343.2)}

doc = json.loads(A.read_text(encoding="utf-8"))
assert not COPIA.exists()
COPIA.write_bytes(A.read_bytes())
feitas = 0
for n in doc["notas"]:
    if n["nota"] in DONO:
        assert (n["corda"], n["casa"], n["x_centro_quadro"]) == DONO[n["nota"]], n
        assert (n["ataque"], n["motivo"]) == ("nao", "prolongamento"), n
        n.update(ataque="sim", motivo="sustentada")
        feitas += 1
assert feitas == 4
A.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("corrigidas", feitas)

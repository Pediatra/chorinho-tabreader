"""Volta para "atacada, sustentada" as notas que começam uma ligadura de prolongamento.

No passe do modo ataque da T8.5, o dono marcou como ``l`` (``nao/prolongamento``) 32
notas que a máquina tinha como ``~`` (``sim/sustentada``): um número com arco depois e
sem segundo número. Perguntado, ele disse (chat, 2026-10-22): "Elas são tocadas uma vez
e depois são prolongadas, posso ter entendido errado a ferramenta". Voltam para
``sim/sustentada``. Entram também t30-n1 e t30-n20, do mesmo acorde com arcos (os
outros membros estão nas 32), que ele marcou ``l`` sobre uma nota que a máquina tinha
como ``normal``. Ficam como o dono marcou t9-n80 e t29-n20: o número repetido logo
antes na mesma corda pode ser o começo da ligadura.

Grava uma cópia ``ataque_t85_antes_sustentada.json`` antes de mudar.

Uso (container): python data/saida/tablatura/t85/passe_ataque/correcao_sustentada.py
"""

import json
from pathlib import Path

ATAQUE = Path("/app/data/saida/tablatura/tab_rotulo/r2/conferir_t85/ataque_t85.json")
FONTE = "dono no chat, 2026-10-22: 'Elas são tocadas uma vez e depois são prolongadas'"
NOTAS = (
    "t13-n3 t13-n4 t13-n5 t13-n15 t22-n77 t22-n78 t22-n79 t22-n80 t29-n0 t29-n1 "
    "t29-n2 t29-n13 t29-n14 t29-n21 t30-n0 t30-n2 t30-n3 t30-n4 t30-n6 t30-n9 "
    "t30-n16 t30-n17 t30-n21 t30-n22 t30-n23 t30-n24 t30-n26 t30-n28 t30-n31 "
    "t30-n38 t30-n40 t30-n41 t30-n1 t30-n20"
).split()


def main() -> None:
    """Aplica a correção e grava o arquivo do ataque."""
    copia = ATAQUE.with_name("ataque_t85_antes_sustentada.json")
    assert not copia.exists()
    doc = json.loads(ATAQUE.read_text(encoding="utf-8"))
    por = {n["nota"]: n for n in doc["notas"]}
    assert len(NOTAS) == len(set(NOTAS)) == 34
    for k in NOTAS:
        n = por[k]
        assert (n["ataque"], n["motivo"]) == ("nao", "prolongamento"), n
    copia.write_bytes(ATAQUE.read_bytes())
    for k in NOTAS:
        por[k].update(ataque="sim", motivo="sustentada", fonte=FONTE)
    ATAQUE.write_text(
        json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(len(NOTAS), "notas voltaram para sim/sustentada; cópia em", copia.name)


if __name__ == "__main__":
    main()

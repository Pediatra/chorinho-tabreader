"""Roda os blocos A e B do CA1 com o ouro do Gymnopédie antes de 741f66da (5 notas 8->0)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, "data/saida/partitura/diag/ca1")
import ca1  # noqa: E402
from tab.partitura_avaliar import _carregar_ouro  # noqa: E402

ouro = _carregar_ouro()
antigo = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
ouro[antigo["video"]] = [antigo]
ca1.bloco_a(ouro)
ca1.bloco_b(ouro)

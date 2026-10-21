"""Reavaliação OFFLINE (sem GPU) do detector, com o combinar sem a regra de honestidade.

Lê as detecções cruas (``pessoas_wb`` e ``maos_mp``) de ``detector_validacao.jsonl``,
recalcula as mãos com ``tab.maos_combinar.combinar`` atual e imprime a mesma tabela de
``tab.maos_detector._tabela_de_acertos``. Não roda os modelos.

Uso (na imagem chorinho-maos:dev, sem --device)::

    python data/saida/maos/m1/reavaliar_sem_honestidade.py
"""

import json
from pathlib import Path

from tab.maos_combinar import afirmacoes, combinar
from tab.maos_detector import _tabela_de_acertos

M1 = Path("/app/data/saida/maos/m1")


def main() -> None:
    """Recalcula as afirmações a partir das detecções cruas e imprime a tabela."""
    registros = [
        json.loads(linha)
        for linha in (M1 / "detector_validacao.jsonl").read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]
    for reg in registros:
        maos = combinar(reg["pessoas_wb"], reg["maos_mp"])
        reg["maos"] = maos
        reg["afirma"] = afirmacoes(maos)
    rotulo = json.loads((M1 / "rotulo_agente_validacao.json").read_text(encoding="utf-8"))
    print(f"{len(registros)} quadros reavaliados (combinar sem regra de honestidade)")
    _tabela_de_acertos(registros, rotulo)


if __name__ == "__main__":
    main()

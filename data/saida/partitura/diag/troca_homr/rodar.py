"""Rodada 3025: homr em todos os recortes do piloto sem produto + documentos novos.

O Audiveris já rodou nos recortes atuais (rodada 3022): aqui ele não roda de novo, o
registro sai do execucao.json existente. O homr roda de verdade (rodar_um real).
"""
import json
from pathlib import Path

from tab import partitura_video
from tab.partitura_omr import rodar_um

SP = Path("data/saida/partitura/sem_produto").resolve()


def rodar_reaproveitando(biblioteca, condicao, entrada, pasta_base, origem):
    """Audiveris: devolve o registro existente; homr: roda."""
    if biblioteca == "audiveris":
        registros = json.loads((pasta_base / "execucao.json").read_text("utf-8"))
        return next(r for r in registros if r["id"] == entrada["id"])
    return rodar_um(biblioteca, condicao, entrada, pasta_base, origem=origem)


partitura_video.rodar_um = rodar_reaproveitando
for pasta in sorted(SP.iterdir()):
    indice = json.loads((pasta / "recortes/indice.json").read_text("utf-8"))
    if not any(not e["sem_pauta"] for e in indice):
        continue
    doc = partitura_video.ler_pasta(pasta)
    partitura_video._imprimir_ler_pasta(pasta, doc)

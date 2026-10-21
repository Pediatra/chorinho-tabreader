"""Diagnóstico: aplica a armadura herdada (fifths=1) nos recortes R05, R06 e R07.

Só mede; não é código de produto. Lê ``x2_margem/<id>/saida.musicxml``, aplica
``herdar_armadura`` e grava o resultado em ``x2_margem_armadura/<id>/saida.musicxml``.
A régua é a de ``tab.partitura_avaliar``: modo exato, referência do gabarito.

Uso (dentro do container): python data/saida/partitura/diag/medir_armadura.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ_REPO))

from tab.caminhos import SAIDA  # noqa: E402
from tab.partitura_avaliar import (  # noqa: E402
    _carregar_ouro,
    _referencia_do_item,
    contar,
    eventos_da_biblioteca,
    ler_musicxml,
)
from tab.partitura_omr import herdar_armadura  # noqa: E402

IDS = ("R05", "R06", "R07")
FIFTHS = 1
PASTA_ANTES = SAIDA / "partitura" / "p1" / "omr" / "audiveris" / "x2_margem"
PASTA_DEPOIS = SAIDA / "partitura" / "p1" / "omr" / "audiveris" / "x2_margem_armadura"
INDICE = SAIDA / "partitura" / "p1" / "recortes_margem" / "indice.json"


def _linha(rotulo: str, cont: dict[str, int]) -> str:
    """Uma linha da tabela com os campos da régua exata."""
    return (
        f"{rotulo:<14}{cont['referencia']:>6}{cont['certas']:>8}"
        f"{cont['altura_errada']:>12}{cont['faltando']:>10}{cont['inventada']:>10}"
    )


def main() -> int:
    """Mede antes e depois para R05, R06 e R07 e imprime a tabela.

    Returns:
        Código de saída (0).
    """
    indice = {i["id"]: i for i in json.loads(INDICE.read_text(encoding="utf-8"))}
    ouro = _carregar_ouro()
    print(
        f"{'recorte':<14}{'ref':>6}{'certas':>8}{'altura_err':>12}"
        f"{'faltando':>10}{'inventada':>10}"
    )
    for id_ in IDS:
        item = indice[id_]
        assert item["origem"] == "ouro", id_
        antes_xml = (PASTA_ANTES / id_ / "saida.musicxml").read_text(encoding="utf-8")
        depois_xml = herdar_armadura(antes_xml, FIFTHS)
        destino = PASTA_DEPOIS / id_ / "saida.musicxml"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(depois_xml, encoding="utf-8")
        mudou = depois_xml != antes_xml
        antes = _medir(PASTA_ANTES / id_ / "saida.musicxml", item, ouro)
        depois = _medir(destino, item, ouro)
        print(_linha(f"{id_} antes", antes))
        print(_linha(f"{id_} depois", depois))
        print(f"  texto mudou: {mudou}")
    return 0


def _medir(caminho: Path, item: dict, ouro: dict) -> dict[str, int]:
    """Régua exata de um MusicXML contra a referência do recorte.

    Args:
        caminho: arquivo ``saida.musicxml`` a medir.
        item: entrada do ``indice.json`` do recorte.
        ouro: gabaritos indexados por vídeo.

    Returns:
        Contagem de ``contar`` no modo exato.
    """
    lib = eventos_da_biblioteca(ler_musicxml(caminho).notas)
    cont, _ = contar(lib, _referencia_do_item(item, ouro), "exato")
    return cont


if __name__ == "__main__":
    raise SystemExit(main())

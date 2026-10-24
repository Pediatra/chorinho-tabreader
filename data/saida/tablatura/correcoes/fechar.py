"""Fecha a revisão do X: tela que só ganhou o "conferida" nesta revisão volta a não conferida.

Nesta revisão o dono corrigiu **só o X** (2026-10-24: "eu só corrigi os x, tem muita coisa
errada de números e símbolos"). Uma tela que não estava conferida antes e saiu marcada
como conferida teria as casas e os símbolos do modelo promovidos a ouro sem conferência.
Por isso, nessas telas, o ``conferida`` volta a falso (as notas X do dono ficam). O ouro v1
é refeito com ``montar_ouro``. O resultado vai para ``final_<lote>.json``, e a lista das
telas revistas só no X, para ``revisao_so_x.json``.

Uso:
    python data/saida/tablatura/correcoes/fechar.py
"""

from __future__ import annotations

from pathlib import Path

from tab.comum.arquivos import gravar_atomico, ler_json
from tab.tablatura.ouro.ouro_video import divergencias_do_estado, montar_ouro

RAIZ = Path(__file__).resolve().parents[4]
SAIDA = Path(__file__).resolve().parent


def fechar_lote(lote: str, origem: Path) -> dict:
    """Grava ``final_<lote>.json`` com o ``conferida`` da revisão só de X desfeito.

    Args:
        lote: o lote.
        origem: a conferência de antes da revisão.

    Returns:
        ``{"revertidas": [...], "revistas_no_x": [...]}`` (ids de tela).

    Raises:
        RuntimeError: se o ouro refeito não bater com o estado.
    """
    pasta = SAIDA / lote
    pre = ler_json(pasta / "pre.json")
    revisto = ler_json(pasta / f"conferencia_{lote}.json")
    antes = {t["id"]: bool(t.get("conferida")) for t in ler_json(origem)["telas"]}
    estado = revisto["ferramenta"]
    revertidas = []
    for tela in estado["telas"]:
        if tela.get("conferida") and not antes.get(tela["id"], False):
            tela["conferida"] = False
            revertidas.append(tela["id"])
    final = montar_ouro(pre, estado, agora=revisto.get("rotulado_em"))
    final["como_foi_rotulado"] = revisto.get("como_foi_rotulado")
    erros = divergencias_do_estado(pre, final)
    if erros:
        raise RuntimeError(f"{lote}: {erros[:3]}")
    gravar_atomico(pasta / f"final_{lote}.json", final)
    revistas = sorted({t["id"] for t in estado["telas"] if t.get("notas")})
    return {"revertidas": revertidas, "revistas_no_x": revistas}


def main() -> None:
    """Fecha os sete lotes e grava ``revisao_so_x.json``."""
    resumo = ler_json(SAIDA / "resumo.json")
    saida = {
        lote: fechar_lote(lote, RAIZ / Path(r["origem"]).relative_to("/app"))
        for lote, r in resumo.items()
    }
    gravar_atomico(SAIDA / "revisao_so_x.json", saida)
    for lote, r in saida.items():
        print(lote, "revertidas", r["revertidas"])


if __name__ == "__main__":
    main()

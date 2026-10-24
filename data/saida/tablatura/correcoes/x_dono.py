"""As notas X do dono nas telas conferidas, para o ajuste fino da rodada 0218.

Lê as conferências depois da revisão do X (EOB e Room 335 em ``data/gold/ouro_video``,
T8.2 a T8.6 em ``data/saida/tablatura/t8N/ferramenta``) e grava ``x_dono.json``:
``{slug: {tela: [{"corda", "x_centro_quadro"}]}}``, com o slug que o cache do treino usa.
Só entram as telas conferidas e as notas com casa ``x`` ou ``xs``. A T8.6 fica num bloco à
parte (``prova``): é a prova lacrada da 0218 e não entra no treino.

Uso:
    python data/saida/tablatura/correcoes/x_dono.py
"""

from __future__ import annotations

from pathlib import Path

from tab.comum.arquivos import gravar_atomico, ler_json

RAIZ = Path(__file__).resolve().parents[4]
SAIDA = Path(__file__).resolve().parent
OUROS = (
    "end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics",
    "tabroom_335_larry_carlton_fingerstyle_guitar",
)
LOTES = ("t82", "t83", "t84", "t85")
PROVA = "t86"


def x_da_conferencia(caminho: Path) -> dict[str, list[dict]]:
    """Notas X das telas conferidas de uma conferência.

    Args:
        caminho: a conferência (ouro v1).

    Returns:
        ``{tela: [{"corda", "x_centro_quadro"}]}``, com a tela como texto.
    """
    saida: dict[str, list[dict]] = {}
    for tela in ler_json(caminho)["telas"]:
        if not tela.get("conferida"):
            continue
        xs = [
            {"corda": int(n["corda"]), "x_centro_quadro": float(n["x_centro_quadro"])}
            for n in tela["notas"]
            if str(n["casa"]).lower() in ("x", "xs")
        ]
        if xs:
            saida[str(tela["id"])] = xs
    return saida


def main() -> None:
    """Grava ``x_dono.json`` e imprime as contagens."""
    treino = {
        slug: x_da_conferencia(RAIZ / "data/gold/ouro_video" / f"{slug}.json")
        for slug in OUROS
    }
    for lote in LOTES:
        pasta = RAIZ / "data/saida/tablatura" / lote / "ferramenta"
        treino[lote] = x_da_conferencia(pasta / f"conferencia_{lote}.json")
    prova = x_da_conferencia(
        RAIZ
        / "data/saida/tablatura"
        / PROVA
        / "ferramenta"
        / f"conferencia_{PROVA}.json"
    )
    gravar_atomico(SAIDA / "x_dono.json", {"treino": treino, "prova": {PROVA: prova}})
    for slug, telas in [*treino.items(), (PROVA, prova)]:
        print(slug[:24], len(telas), "telas", sum(len(v) for v in telas.values()), "X")


if __name__ == "__main__":
    main()

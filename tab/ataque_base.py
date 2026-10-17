"""R3: linha de base do ataque — o produto atual contra o gabarito do R2 (rodada 0200).

Lê o gabarito conferido pelo dono (``ataque_<fonte>.json``) e a saída gravada do produto
(cada vídeo lido pela dobra que não o viu), pareia as notas e monta a matriz ouro × previsto.

Uso::

    python -m tab.ataque_base
"""

import argparse
import json
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from tab import caminhos

#: Fonte do gabarito -> slug do ouro (a leitura gravada tem o mesmo nome).
FONTES = {
    "end_of_beginning": "end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics",
    "tabroom_335": "tabroom_335_larry_carlton_fingerstyle_guitar",
    "pat_metheny": "tab_from_this_place_pat_metheny_fingerstyle_guitar_cover",
}

#: Técnicas do modelo que dizem "a nota chega sem ataque" (a técnica fica na chegada).
TECNICAS_SEM_ATAQUE = frozenset({"h", "p", "/", "\\", "lig", "orn", "enfeite"})

#: Folga do pareamento, em passos.
FOLGA = 0.5


def ataque_previsto(tecnica: object) -> str:
    """Ataque que o produto dá a uma nota, pela técnica dela.

    Args:
        tecnica: ``None``, uma string (técnicas unidas por ``+``) ou uma lista.

    Returns:
        "nao" se alguma técnica é de chegada sem ataque; senão "sim".
    """
    if tecnica is None:
        return "sim"
    lista = tecnica.split("+") if isinstance(tecnica, str) else list(tecnica)
    return "nao" if TECNICAS_SEM_ATAQUE & set(lista) else "sim"


def tela_do_produto(telas: Sequence[dict], quadro_s: float) -> dict | None:
    """Tela do produto que tem uma exibição contendo o instante do quadro do ouro.

    Args:
        telas: ``telas`` da leitura gravada.
        quadro_s: ``quadro_ref_s`` da tela do ouro.

    Returns:
        A tela, ou None se nenhuma exibição contém o instante.
    """
    for t in telas:
        for e in t.get("exibicoes") or []:
            if e["t0"] <= quadro_s <= e["t1"]:
                return t
    return None


def parear(
    ouro: Sequence[dict], previstas: Sequence[dict], passo: float
) -> dict[int, int]:
    """Pareia notas do ouro com as do produto: corda igual, ``|dx| ≤ FOLGA·passo``.

    Guloso pela menor distância; cada nota entra em no máximo um par.

    Args:
        ouro: notas do ouro, com ``corda`` e ``x_centro_quadro``.
        previstas: notas do produto, com os mesmos campos.
        passo: passo da tela, em px.

    Returns:
        Mapa índice no ouro -> índice no produto.
    """
    candidatos = sorted(
        (abs(o["x_centro_quadro"] - p["x_centro_quadro"]), i, j)
        for i, o in enumerate(ouro)
        for j, p in enumerate(previstas)
        if o["corda"] == p["corda"]
        and abs(o["x_centro_quadro"] - p["x_centro_quadro"]) <= FOLGA * passo
    )
    pares: dict[int, int] = {}
    usadas: set[int] = set()
    for _, i, j in candidatos:
        if i in pares or j in usadas:
            continue
        pares[i] = j
        usadas.add(j)
    return pares


def medir_fonte(fonte: str, slug: str, pasta_ataque: Path) -> dict:
    """Matriz ouro × previsto de uma fonte.

    Args:
        fonte: nome curto da fonte (``ataque_<fonte>.json``).
        slug: nome do ouro e da leitura gravada.
        pasta_ataque: pasta com o gabarito conferido.

    Returns:
        Dict com ``matriz`` (``"<ouro>|<previsto>"`` -> contagem), ``por_motivo`` (notas
        "nao" do ouro: motivo -> previsto -> contagem), ``telas`` e ``sem_tela``.
    """
    gab = json.loads((pasta_ataque / f"ataque_{fonte}.json").read_text("utf-8"))
    ouro = json.loads((caminhos.OURO_VIDEO / f"{slug}.json").read_text("utf-8"))
    lido = json.loads((caminhos.FASE8_GER / f"{slug}.json").read_text("utf-8"))
    quadro = {int(t["id"]): float(t["quadro_ref_s"]) for t in ouro["telas"]}
    conferidas = {int(k) for k, v in (gab.get("telas_conferidas") or {}).items() if v}
    por_tela: dict[int, list[dict]] = {}
    for n in gab["notas"]:
        if n["tela"] in conferidas:
            por_tela.setdefault(n["tela"], []).append(n)
    matriz: Counter = Counter()
    por_motivo: dict[str, Counter] = {}
    sem_tela = []
    for tid, notas in sorted(por_tela.items()):
        tp = tela_do_produto(lido["telas"], quadro[tid])
        if tp is None:
            sem_tela.append(tid)
            previstas: list[dict] = []
            passo = 0.0
        else:
            previstas = [n for n in lido["notas"] if n["tela"] == tp["id"]]
            passo = float(tp["passo"])
        pares = parear(notas, previstas, passo)
        for i, n in enumerate(notas):
            prev = (
                ataque_previsto(previstas[pares[i]].get("tecnica"))
                if i in pares
                else "nao_lida"
            )
            matriz[f"{n['ataque']}|{prev}"] += 1
            if n["ataque"] == "nao":
                por_motivo.setdefault(n["motivo"], Counter())[prev] += 1
    return {
        "matriz": dict(matriz),
        "por_motivo": {k: dict(v) for k, v in sorted(por_motivo.items())},
        "telas": sorted(por_tela),
        "sem_tela": sem_tela,
        "modelo": lido.get("gerado_por", {}).get("modelo"),
    }


def taxas(matriz: dict) -> dict:
    """ "Sim" falso e "não" falso de uma matriz, com os denominadores.

    Args:
        matriz: ``"<ouro>|<previsto>"`` -> contagem.

    Returns:
        Dict com ``sim_falso`` e ``nao_falso`` (``[numerador, denominador]``) e as notas
        não lidas por classe do ouro.
    """

    def m(chave: str) -> int:
        return int(matriz.get(chave, 0))

    return {
        "sim_falso": [m("nao|sim"), m("nao|sim") + m("nao|nao")],
        "nao_falso": [m("sim|nao"), m("sim|nao") + m("sim|sim")],
        "nao_lidas": {"sim": m("sim|nao_lida"), "nao": m("nao|nao_lida")},
    }


def main() -> int:
    """Mede as fontes e grava ``TAB_ROTULO/r3/linha_de_base.json``.

    Returns:
        0.
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--ataque", type=Path, default=caminhos.TAB_ROTULO / "r2" / "conferir"
    )
    ap.add_argument("--saida", type=Path, default=caminhos.TAB_ROTULO / "r3")
    args = ap.parse_args()
    resultado: dict = {"fontes": {}}
    total: Counter = Counter()
    for fonte, slug in FONTES.items():
        r = medir_fonte(fonte, slug, args.ataque)
        r["taxas"] = taxas(r["matriz"])
        resultado["fontes"][fonte] = r
        total.update(r["matriz"])
        print(fonte, r["matriz"], r["taxas"], "sem tela:", r["sem_tela"])
    resultado["total"] = {"matriz": dict(total), "taxas": taxas(total)}
    print("total", dict(total), resultado["total"]["taxas"])
    args.saida.mkdir(parents=True, exist_ok=True)
    (args.saida / "linha_de_base.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

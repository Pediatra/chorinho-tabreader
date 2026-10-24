"""Monta as cópias da ferramenta para o dono decidir o X empilhado e a auditoria cega.

Para cada lote (EOB, Room 335, T8.2 a T8.6), copia a conferência do dono para
``correcoes/<lote>/conferencia_<lote>.json`` e põe no estado da ferramenta as sugestões,
como notas ``origem: "dono"`` com o campo ``sugestao`` (a ferramenta as desenha como nota do
dono, diferente das notas do modelo):

- ``palpite_x``: uma nota ``x`` por corda com tinta em cada região de X do dono
  (``gap_x/palpite_x.json`` filtrado por ``gap_x/medida_tinta.json``);
- ``auditoria_so_b``: o X que o dono marcou na auditoria cega e falta na conferência;
- ``auditoria_casa``: a casa da marcação cega no lugar da conferida (``casa_antes`` guarda a
  antiga);
- ``auditoria_so_c``: a nota que só a conferência tem, só destacada.

A tela com sugestão volta a ``conferida: false``. O ouro v1 é refeito com ``montar_ouro``, e
o script confere que as telas sem sugestão saem iguais à conferência original. Nada em
``data/gold/`` nem nas conferências originais é escrito.

Uso:
    python data/saida/tablatura/correcoes/montar.py
"""

from __future__ import annotations

import copy
import shutil
from pathlib import Path
from typing import Any

from tab.comum.arquivos import gravar_atomico, ler_json
from tab.tablatura.ouro.ouro_video import divergencias_do_estado, montar_ouro

RAIZ = Path(__file__).resolve().parents[4]
TAB = RAIZ / "data/saida/tablatura"
SAIDA = Path(__file__).resolve().parent
#: Cópia de ``gap_auditoria/divergencias.json`` (worktree ``auditoria-cega``).
AUDITORIA = SAIDA / "divergencias_auditoria.json"
OUROS = {
    "eob": "end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics",
    "room335": "tabroom_335_larry_carlton_fingerstyle_guitar",
}
LOTES = ["eob", "room335", "t82", "t83", "t84", "t85", "t86"]

#: Duas notas na mesma corda a menos disto (em passos) são a mesma.
MESMA_NOTA_PASSOS = 0.5


def origem(lote: str) -> tuple[Path, Path]:
    """Conferência do dono e pasta da ferramenta de um lote.

    Args:
        lote: ``eob``, ``room335`` ou ``t8N``.

    Returns:
        ``(conferência, pasta da ferramenta)``.
    """
    if lote in OUROS:
        nome = OUROS[lote]
        return RAIZ / f"data/gold/ouro_video/{nome}.json", TAB / "ouro_video" / nome
    pasta = TAB / lote / "ferramenta"
    return pasta / f"conferencia_{lote}.json", pasta


def sugestoes_por_tela(lote: str) -> dict[int, list[dict[str, Any]]]:
    """Junta as sugestões do lote, por id de tela.

    Args:
        lote: o lote.

    Returns:
        ``{tela: [sugestão]}``; cada sugestão tem ``tipo``, ``corda``, ``x_quadro`` ou
        ``x_centro``, e a casa.
    """
    tinta = {
        (r["tela"], r["regiao"], r["corda"]): r["tinta"]
        for r in ler_json(TAB / "gap_x/medida_tinta.json")["linhas"]
        if r["arquivo"] == lote
    }
    saida: dict[int, list[dict[str, Any]]] = {}
    for r in ler_json(TAB / "gap_x/palpite_x.json")["regioes"]:
        if r["arquivo"] != lote:
            continue
        for n in r["notas"]:
            if not tinta.get((r["tela"], r["regiao"], n["corda"]), False):
                continue
            saida.setdefault(r["tela"], []).append(
                {
                    "tipo": "palpite_x",
                    "corda": n["corda"],
                    "casa": "x",
                    "x_quadro": n["x_quadro"],
                }
            )
    if lote in ("t85", "t86"):
        for d in ler_json(AUDITORIA):
            if d["lote"] != lote:
                continue
            saida.setdefault(d["id_original"], []).append(
                {
                    "tipo": f"auditoria_{d['tipo']}",
                    "corda": d["corda"],
                    "casa": d["casa_b"] if d["tipo"] != "so_c" else d["casa_c"],
                    "x_centro": d["x"],
                }
            )
    return saida


def aplicar(
    tela_estado: dict, tela_pre: dict, sugestoes: list[dict], estado: dict
) -> int:
    """Põe as sugestões numa tela do estado da ferramenta.

    Args:
        tela_estado: a tela no estado (alterada no lugar).
        tela_pre: a mesma tela no ``pre.json`` (dá o passo).
        sugestoes: as sugestões da tela.
        estado: o estado inteiro (dá o contador ``proximo``).

    Returns:
        Quantas sugestões entraram (as repetidas ficam de fora).
    """
    passo = float(tela_pre.get("passo") or 20.0)
    vivas = [n for n in tela_estado["notas"] if not n.get("removida")]
    entraram = 0
    for s in sugestoes:
        centro = s.get("x_centro", (s.get("x_quadro") or 0.0) + 0.25 * passo)
        perto = [
            n
            for n in vivas
            if n["corda"] == s["corda"]
            and abs(float(n["x_centro_quadro"]) - centro) <= MESMA_NOTA_PASSOS * passo
        ]
        if s["tipo"] in ("auditoria_casa", "auditoria_so_c"):
            if not perto:
                continue
            nota = min(perto, key=lambda n: abs(float(n["x_centro_quadro"]) - centro))
            if s["tipo"] == "auditoria_casa":
                nota["casa_antes"] = nota["casa"]
                nota["casa"] = s["casa"]
            nota["origem"] = "dono"
            nota.pop("caixa", None)
            nota["sugestao"] = s["tipo"]
            entraram += 1
            continue
        if perto:
            continue
        nova = {
            "id": f"d{estado['proximo']}",
            "corda": s["corda"],
            "casa": s["casa"],
            "x_quadro": round(centro - 0.25 * passo, 1),
            "x_centro_quadro": round(centro, 1),
            "origem": "dono",
            "removida": False,
            "sugestao": s["tipo"],
        }
        estado["proximo"] += 1
        tela_estado["notas"].append(nova)
        vivas.append(nova)
        entraram += 1
    if entraram:
        tela_estado["conferida"] = False
    return entraram


def montar_lote(lote: str) -> dict[str, Any]:
    """Grava a cópia da ferramenta de um lote, com as sugestões.

    Args:
        lote: o lote.

    Returns:
        O resumo do lote: telas a rever e sugestões por tipo.

    Raises:
        RuntimeError: se a cópia já existe (o dono pode ter começado) ou se o ouro
            refeito não bater com o estado.
    """
    conferencia, pasta = origem(lote)
    destino = SAIDA / lote
    ouro_novo = destino / f"conferencia_{lote}.json"
    if ouro_novo.exists():
        raise RuntimeError(f"{ouro_novo} já existe; não sobrescrevo o trabalho do dono")
    destino.mkdir(parents=True, exist_ok=True)
    pre = ler_json(pasta / "pre.json")
    gravar_atomico(destino / "pre.json", pre)
    if not (destino / "telas").exists():
        # cópia, não link: o servidor da ferramenta não serve imagem por link simbólico
        shutil.copytree(pasta / "telas", destino / "telas")
    original = ler_json(conferencia)
    novo = copy.deepcopy(original)
    estado = novo["ferramenta"]
    pre_por_id = {t["id"]: t for t in pre["telas"]}
    por_tipo: dict[str, int] = {}
    a_rever = []
    for tid, sugestoes in sorted(sugestoes_por_tela(lote).items()):
        tela = next(t for t in estado["telas"] if t["id"] == tid)
        if aplicar(tela, pre_por_id[tid], sugestoes, estado):
            a_rever.append(tid)
        for n in tela["notas"]:
            if n.get("sugestao"):
                por_tipo[n["sugestao"]] = por_tipo.get(n["sugestao"], 0) + 1
    montado = montar_ouro(pre, estado, agora=original.get("rotulado_em"))
    montado["como_foi_rotulado"] = original.get("como_foi_rotulado")
    erros = divergencias_do_estado(pre, montado)
    if erros:
        raise RuntimeError(f"{lote}: ouro refeito diverge do estado: {erros[:3]}")
    antigas = {t["id"]: t for t in original["telas"]}
    for t in montado["telas"]:
        if t["id"] not in a_rever and t != antigas.get(t["id"]):
            raise RuntimeError(f"{lote}: tela {t['id']} sem sugestão mudou")
    gravar_atomico(ouro_novo, montado)
    return {"telas_a_rever": a_rever, "sugestoes": por_tipo, "origem": str(conferencia)}


def main() -> None:
    """Monta os sete lotes e grava ``resumo.json``."""
    resumo = {lote: montar_lote(lote) for lote in LOTES}
    gravar_atomico(SAIDA / "resumo.json", resumo)
    for lote, r in resumo.items():
        print(lote, len(r["telas_a_rever"]), r["sugestoes"])


if __name__ == "__main__":
    main()

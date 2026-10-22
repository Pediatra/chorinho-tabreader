"""Ouro servido no passe do modo ataque da T8.4, coerente com o estado da ferramenta.

As correções do dono no chat (``r2/novos_t84.py``: o "h" da região "(n)" da tela 9 e as
duas notas <12> da tela 21) foram escritas só em ``telas`` da cópia corrigida. A
ferramenta remonta o ouro a partir de ``ferramenta`` e, por isso, recusa subir. Aqui as
mesmas correções entram no estado, o ouro é remontado pelo ``montar_ouro`` da própria
ferramenta e conferido: notas e regiões iguais às da cópia corrigida, e as chaves
``t<tela>-n<k>`` iguais às do ``ataque_t84.json``. Nenhum arquivo existente é alterado.

Uso (container): python data/saida/tablatura/t84/passe_ataque/montar_servido.py
"""

import copy
import json
from pathlib import Path

from tab.tablatura.ouro import ouro_video as O

RAIZ = Path("/app/data/saida/tablatura")
ORIGEM = RAIZ / "t84/ferramenta/conferencia_t84.json"
CORRIGIDA = RAIZ / "tab_rotulo/r2/conferir_t84/conferencia_t84_corrigida.json"
ATAQUE = RAIZ / "tab_rotulo/r2/conferir_t84/ataque_t84.json"
PRE = RAIZ / "t84/ferramenta/pre.json"
SAIDA = RAIZ / "t84/passe_ataque/conferencia_t84_servida.json"
FONTE = "dono no chat, 2026-10-21 (novos_t84.py)"


def main() -> int:
    """Monta, confere e grava o ouro servido."""
    origem = json.loads(ORIGEM.read_text(encoding="utf-8"))
    corrigida = json.loads(CORRIGIDA.read_text(encoding="utf-8"))
    ataque = json.loads(ATAQUE.read_text(encoding="utf-8"))
    pre = json.loads(PRE.read_text(encoding="utf-8"))
    estado = copy.deepcopy(origem["ferramenta"])
    telas = {int(t["id"]): t for t in estado["telas"]}
    # tela 9: a região "(n)" da corda 1 em x 1266–1314 vira "h"
    alvo = [
        r for r in telas[9]["regioes"]
        if r.get("tecnica") == ["(n)"] and r["corda_ini"] == r["corda_fim"] == 1
        and abs(min(r["x0"], r["x1"]) - 1266.1) < 1 and abs(max(r["x0"], r["x1"]) - 1313.9) < 1
    ]
    assert len(alvo) == 1, alvo
    alvo[0]["tecnica"] = ["h"]
    alvo[0]["obs"] = (alvo[0].get("obs") or "") + f" [h: {FONTE}]"
    # tela 21: as duas notas <12>
    for k, (corda,) in enumerate(((2,), (3,))):
        telas[21]["notas"].append({
            "id": f"dono{k + 1}", "corda": corda, "casa": "12", "x_quadro": 1696.5,
            "x_centro_quadro": 1702.5, "origem": FONTE, "removida": False,
        })
    servido = O.montar_ouro(pre, estado, agora=origem.get("rotulado_em"),
                            como_foi_rotulado=origem.get("como_foi_rotulado"))
    assert not O.divergencias_do_estado(pre, servido)
    # notas e regiões iguais às da corrigida (corda, casa, x; cordas, x, técnica)
    def notas(t):
        return sorted((n["corda"], str(n["casa"]), round(n["x_quadro"], 1)) for n in t["notas"])
    def regioes(t):
        return [(tuple(r["cordas"]), tuple(round(x, 1) for x in r["x_quadro"]), tuple(r["tecnica"]))
                for r in t.get("regioes") or []]
    cor = {int(t["id"]): t for t in corrigida["telas"]}
    srv = {int(t["id"]): t for t in servido["telas"]}
    assert set(cor) == set(srv)
    ruins = [i for i in cor if notas(cor[i]) != notas(srv[i]) or regioes(cor[i]) != regioes(srv[i])]
    assert not ruins, ruins
    # chaves do ataque: a k-ésima nota da tela (ordem do montar_ouro) é t<tela>-n<k>
    chave = {}
    for i, t in srv.items():
        for k, n in enumerate(t["notas"]):
            chave[f"t{i}-n{k}"] = (n["corda"], str(n["casa"]))
    # O novos_t84 numerou as 2 notas do chat no fim da tela 21 (ordem da lista), e a
    # ferramenta numera pela ordem de x: renumera pela posição (corda, casa, x), sem mexer
    # em rótulo nenhum. A medida casa por corda e x, então não muda.
    pos = {}
    for i, t in srv.items():
        for k, nt in enumerate(t["notas"]):
            pos[(i, nt["corda"], str(nt["casa"]), round(nt["x_centro_quadro"], 1))] = f"t{i}-n{k}"
    novo = copy.deepcopy(ataque)
    for a in novo["notas"]:
        a["nota"] = pos[(a["tela"], a["corda"], str(a["casa"]), round(a["x_centro_quadro"], 1))]
    assert len({a["nota"] for a in novo["notas"]}) == len(novo["notas"])
    trocadas = [(a["nota"], b["nota"]) for a, b in zip(ataque["notas"], novo["notas"]) if a["nota"] != b["nota"]]
    print("renumeradas:", trocadas)
    assert all(x["tela"] == 21 for x in ataque["notas"] if x["nota"] in {t for t, _ in trocadas})
    assert not novo.get("telas_conferidas"), "o dono já gravou no ataque: não renumerar"
    ataque = novo
    faltam = [a["nota"] for a in ataque["notas"] if chave.get(a["nota"]) != (a["corda"], str(a["casa"]))]
    assert not faltam and len(chave) == len(ataque["notas"]), (faltam[:5], len(chave))
    SAIDA.write_text(json.dumps(servido, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if trocadas:
        copia = ATAQUE.with_name("ataque_t84_antes_renumerar.json")
        assert not copia.exists()
        copia.write_bytes(ATAQUE.read_bytes())
        ATAQUE.write_text(json.dumps(ataque, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"ataque renumerado em {ATAQUE} (cópia em {copia.name})")
    print(f"ok: {len(srv)} telas, {len(chave)} notas = {len(ataque['notas'])} do ataque; {SAIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

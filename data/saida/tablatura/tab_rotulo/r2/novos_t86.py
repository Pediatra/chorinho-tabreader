"""Prepara o passe do modo ataque da T8.6 (prova lacrada da rodada 0215).

Cópia do ``novos_t86.py``. Lê a conferência do dono em
``data/saida/tablatura/t86/ferramenta/conferencia_t86.json`` (só leitura) e tira duas
telas, marcadas antes de qualquer medida (``docs/rodadas/0215-expressao-e-t86.md``):

- tela 3: o quadro não tem tablatura, só o violão; o dono apagou as notas lidas;
- tela 28: as cordas ficaram em cima do vídeo; o dono não a conferiu.

Grava a ferramenta do passe em ``t86/passe_ataque/ferramenta/`` (``pre.json`` e as telas
das 27 que ficam), o ouro servido ``conferencia_t86_servida.json`` (remontado pelo
``montar_ouro`` da ferramenta e conferido com ``divergencias_do_estado``) e, a partir
dele, ``conferir_t86/ataque_t86.json`` e ``resumo.json``. A regra da ligadura de uma nota
só vale nesta fonte (``converter.PROLONGAMENTO_UMA_NOTA_ATACADA``). As chaves
``t<tela>-n<k>`` saem da ordem do ouro servido, a mesma da ferramenta.

Uso (container): python data/saida/tablatura/tab_rotulo/r2/novos_t86.py
"""

import copy
import json
import shutil
from pathlib import Path

import converter as cv

from tab.tablatura.ouro import ouro_video as O

RAIZ = Path(__file__).resolve().parents[5]
T86 = RAIZ / "data" / "saida" / "tablatura" / "t86"
ORIGEM = T86 / "ferramenta" / "conferencia_t86.json"
PRE = T86 / "ferramenta" / "pre.json"
PASSE = T86 / "passe_ataque"
FERR = PASSE / "ferramenta"
SERVIDO = PASSE / "conferencia_t86_servida.json"
#: tela -> motivo (folhas t86/folha_paineis_*.jpg, 2026-10-23).
FORA = {
    3: "o quadro não tem tablatura, só o violão (o dono apagou as notas lidas)",
    28: "as cordas do painel ficaram em cima do vídeo (o dono não a conferiu)",
}


def main() -> None:
    """Grava a ferramenta do passe, o ouro servido e o arquivo de ataque."""
    saida = cv.SAIDA / "conferir_t86"
    existente = saida / "ataque_t86.json"
    if existente.exists() and json.loads(existente.read_text(encoding="utf-8")).get(
        "telas_conferidas"
    ):
        raise SystemExit("ataque_t86.json já tem telas conferidas no modo ataque")
    saida.mkdir(exist_ok=True)
    origem = json.loads(ORIGEM.read_text(encoding="utf-8"))
    pre = json.loads(PRE.read_text(encoding="utf-8"))
    assert not O.divergencias_do_estado(pre, origem)
    pre_novo = copy.deepcopy(pre)
    pre_novo["telas"] = [t for t in pre["telas"] if t["id"] not in FORA]
    pre_novo["estado_inicial"]["telas"] = [
        t for t in pre["estado_inicial"]["telas"] if t["id"] not in FORA
    ]
    pre_novo["telas_fora"] = {str(k): v for k, v in FORA.items()}
    estado = copy.deepcopy(origem["ferramenta"])
    estado["telas"] = [t for t in estado["telas"] if t["id"] not in FORA]
    estado["tela_atual"] = pre_novo["telas"][0]["id"]
    estado["proximo"] = pre_novo["telas"][0]["id"]
    assert all(t["conferida"] for t in estado["telas"]) and len(estado["telas"]) == 27
    (FERR / "telas").mkdir(parents=True, exist_ok=True)
    for t in pre_novo["telas"]:
        shutil.copy(T86 / "ferramenta" / t["arquivo"], FERR / t["arquivo"])
    (FERR / "pre.json").write_text(
        json.dumps(pre_novo, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    servido = O.montar_ouro(
        pre_novo,
        estado,
        agora=origem.get("rotulado_em"),
        como_foi_rotulado=origem.get("como_foi_rotulado"),
    )
    assert not O.divergencias_do_estado(pre_novo, servido)
    # as notas e regiões de cada tela que fica são as da conferência do dono
    def assinatura(t: dict) -> tuple:
        notas = sorted((n["corda"], str(n["casa"]), round(n["x_quadro"], 1)) for n in t["notas"])
        regs = [(tuple(r["cordas"]), tuple(r["x_quadro"]), tuple(r["tecnica"]))
                for r in t.get("regioes") or []]
        return notas, regs
    orig = {t["id"]: t for t in origem["telas"]}
    for t in servido["telas"]:
        assert assinatura(t) == assinatura(orig[t["id"]]), t["id"]
    SERVIDO.write_text(json.dumps(servido, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    cv.SEM_REGIAO_E_SEM_TECNICA = {"t86"}
    cv.PROLONGAMENTO_UMA_NOTA_ATACADA = {"t86"}
    ataque, res = cv.processar_fonte("t86", SERVIDO)
    # Nota que o conversor não rotula (região de legato sobre uma nota só) entra como
    # "nao_sei", para o dono decidir no modo ataque. O agente não escolhe o rótulo.
    chaves = {a["nota"] for a in ataque["notas"]}
    for t in servido["telas"]:
        for k, n in enumerate(t["notas"]):
            if f"t{t['id']}-n{k}" in chaves:
                continue
            ataque["notas"].append(
                {
                    "ataque": "nao_sei",
                    "casa": n["casa"],
                    "casa_vizinha_dir": None,
                    "casa_vizinha_esq": None,
                    "corda": n["corda"],
                    "motivo": "nao_sei",
                    "nota": f"t{t['id']}-n{k}",
                    "regiao": None,
                    "tela": t["id"],
                    "x_centro_quadro": round(float(n["x_quadro"]), 1),
                }
            )
            print("nao_sei para o dono:", f"t{t['id']}-n{k}", n["corda"], n["casa"])
    ataque["telas_conferidas"] = {}
    ataque["telas_fora"] = pre_novo["telas_fora"]
    # as chaves batem com a ordem do ouro servido (a da ferramenta)
    srv = {t["id"]: t for t in servido["telas"]}
    for a in ataque["notas"]:
        tela, k = a["tela"], int(a["nota"].split("-n")[1])
        n = srv[tela]["notas"][k]
        assert (n["corda"], str(n["casa"])) == (a["corda"], str(a["casa"])), a
    existente.write_text(
        json.dumps(ataque, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (saida / "resumo.json").write_text(
        json.dumps({"campo_x": cv.CAMPO_X, "fontes": {"t86": res}}, ensure_ascii=False,
                   indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("telas", res["telas_conferidas"], "sem tecnica", res.get("telas_sem_tecnica"),
          "notas", res["notas_rotuladas"], "de", sum(len(t["notas"]) for t in servido["telas"]),
          dict(res["ataques"]))
    print("motivos", dict(res["motivos"]))
    print("uma nota atacada", res.get("uma_nota_atacada"), "regioes", res["regioes_lidas"])
    print("ambiguos", res.get("ambiguos_por_tipo"), "acima", res.get("arco_corda_acima"),
          "abaixo", res.get("arco_corda_abaixo"))


if __name__ == "__main__":
    main()

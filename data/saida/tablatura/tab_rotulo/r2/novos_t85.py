"""Prepara o passe do modo ataque da T8.5 (prova lacrada da próxima versão do ataque).

Lê a conferência do dono em ``data/saida/tablatura/t85/ferramenta/conferencia_t85.json``
(só leitura) e tira duas telas, pelo que o dono disse no chat em 2026-10-22:

- tela 5: "pode desconsiderar ele viu a partitura e achou q era tablatura";
- tela 27: o recorte cortou a corda 6 e deslocou as cordas de uma; refeita em
  ``t85/refazer27/``, o dono disse "Nao vou conferir so uma nao vale apena, so segue".

Grava a ferramenta do passe em ``t85/passe_ataque/ferramenta/`` (``pre.json`` e as telas
das 28 que ficam), o ouro servido ``conferencia_t85_servida.json`` (remontado pelo
``montar_ouro`` da ferramenta e conferido com ``divergencias_do_estado``) e, a partir
dele, ``conferir_t85/ataque_t85.json`` e ``resumo.json``. A regra da ligadura de uma nota
só vale nesta fonte (``converter.PROLONGAMENTO_UMA_NOTA_ATACADA``). As chaves
``t<tela>-n<k>`` saem da ordem do ouro servido, a mesma da ferramenta.

Uso (container): python data/saida/tablatura/tab_rotulo/r2/novos_t85.py
"""

import copy
import json
import shutil
from pathlib import Path

import converter as cv

from tab.tablatura.ouro import ouro_video as O

RAIZ = Path(__file__).resolve().parents[5]
T85 = RAIZ / "data" / "saida" / "tablatura" / "t85"
ORIGEM = T85 / "ferramenta" / "conferencia_t85.json"
PRE = T85 / "ferramenta" / "pre.json"
PASSE = T85 / "passe_ataque"
FERR = PASSE / "ferramenta"
SERVIDO = PASSE / "conferencia_t85_servida.json"
#: tela -> motivo, dito pelo dono no chat (2026-10-22).
FORA = {
    5: "o painel pegou a pauta como tablatura (dono: 'pode desconsiderar')",
    27: "o recorte cortou a corda 6 e deslocou as cordas (dono: 'so segue')",
}


def main() -> None:
    """Grava a ferramenta do passe, o ouro servido e o arquivo de ataque."""
    saida = cv.SAIDA / "conferir_t85"
    existente = saida / "ataque_t85.json"
    if existente.exists() and json.loads(existente.read_text(encoding="utf-8")).get(
        "telas_conferidas"
    ):
        raise SystemExit("ataque_t85.json já tem telas conferidas no modo ataque")
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
    assert all(t["conferida"] for t in estado["telas"]) and len(estado["telas"]) == 28
    (FERR / "telas").mkdir(parents=True, exist_ok=True)
    for t in pre_novo["telas"]:
        shutil.copy(T85 / "ferramenta" / t["arquivo"], FERR / t["arquivo"])
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
    cv.SEM_REGIAO_E_SEM_TECNICA = {"t85"}
    cv.PROLONGAMENTO_UMA_NOTA_ATACADA = {"t85"}
    ataque, res = cv.processar_fonte("t85", SERVIDO)
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
        json.dumps({"campo_x": cv.CAMPO_X, "fontes": {"t85": res}}, ensure_ascii=False,
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

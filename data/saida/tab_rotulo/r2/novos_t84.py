"""Prepara a conferência do ataque da T8.4 (2026-10-21, validação da 0211), como a T8.3.

Lê as regiões que o dono marcou em ``data/saida/t84/ferramenta/conferencia_t84.json``. Tela
sem região vem como "sim/normal". Saída em ``conferir_t84/`` (cópia da conferência,
``ataque_t84.json`` e ``resumo.json``).

Uso (container): python /app/data/saida/tab_rotulo/r2/novos_t84.py
"""

import json
import shutil

import converter as cv

ORIGEM = cv.RAIZ / "data" / "saida" / "t84" / "ferramenta" / "conferencia_t84.json"
#: Correções ditas pelo dono no chat, aplicadas a uma cópia (a conferência fica intacta).
#: (tela, índice da região) -> técnica.
CORRECOES_DO_DONO = {
    # 2026-10-21, sobre a região "(n)" do 0 -> 2 na corda 1, sob o "h": "É um Hammer mesmo."
    (9, 9): ["h"],
}

#: Notas que faltavam na lista, ditas pelo dono no chat: tela -> notas (casa, corda, x).
NOTAS_DO_DONO = {
    # 2026-10-21, tela 21, o 2º par <12> depois das ligaduras de prolongamento: "era 2
    # sequências de harm no 12". O x é o centro das regiões "harm" que o dono marcou.
    21: [
        {"corda": 2, "casa": 12, "x_quadro": 1696.5, "x_centro_quadro": 1702.5},
        {"corda": 3, "casa": 12, "x_quadro": 1696.5, "x_centro_quadro": 1702.5},
    ],
}

#: Rótulo de ataque dito pelo dono no chat, por nota (depois da conversão).
ATAQUE_DO_DONO = {
    # 2026-10-21, o 2º par <12> da tela 21: "Nao atacado o ligadura de prolong".
    "t21-n30": ("nao", "prolongamento"),
    "t21-n31": ("nao", "prolongamento"),
}


def corrigida(saida) -> object:
    """Grava a cópia da conferência com as correções do dono e devolve o caminho."""
    doc = json.loads(ORIGEM.read_text(encoding="utf-8"))
    for tela in doc["telas"]:
        tela["notas"] = tela["notas"] + [
            dict(n, origem="dono no chat (novos_t84.NOTAS_DO_DONO)", removida=False)
            for n in NOTAS_DO_DONO.get(int(tela["id"]), [])
        ]
        for k, regiao in enumerate(tela.get("regioes") or []):
            if (int(tela["id"]), k) in CORRECOES_DO_DONO:
                regiao["tecnica"] = CORRECOES_DO_DONO[(int(tela["id"]), k)]
                regiao["fonte"] = "dono no chat (novos_t84.CORRECOES_DO_DONO)"
    caminho = saida / "conferencia_t84_corrigida.json"
    caminho.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return caminho


def main() -> None:
    """Grava a cópia, o arquivo de ataque e o resumo da T8.4."""
    saida = cv.SAIDA / "conferir_t84"
    saida.mkdir(exist_ok=True)
    existente = saida / "ataque_t84.json"
    if existente.exists() and json.loads(existente.read_text(encoding="utf-8")).get(
        "telas_conferidas"
    ):
        raise SystemExit(
            "ataque_t84.json já tem telas conferidas pelo dono no modo ataque: "
            "regravar apagaria o passe dele"
        )
    cv.SEM_REGIAO_E_SEM_TECNICA = {"t84"}
    ataque, res = cv.processar_fonte("t84", corrigida(saida))
    ataque["telas_conferidas"] = {}
    for nota in ataque["notas"]:
        if nota["nota"] in ATAQUE_DO_DONO:
            assert int(nota["tela"]) == 21 and int(nota["casa"]) == 12, nota
            nota["ataque"], nota["motivo"] = ATAQUE_DO_DONO[nota["nota"]]
            nota["fonte"] = "dono no chat (novos_t84.ATAQUE_DO_DONO)"
    print("ataque do dono aplicado:", sum(n["nota"] in ATAQUE_DO_DONO for n in ataque["notas"]))
    (saida / "ataque_t84.json").write_text(
        json.dumps(ataque, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    shutil.copy(ORIGEM, saida / ORIGEM.name)
    (saida / "resumo.json").write_text(
        json.dumps({"campo_x": cv.CAMPO_X, "fontes": {"t84": res}}, ensure_ascii=False,
                   indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("telas", res["telas_conferidas"], "sem tecnica", res.get("telas_sem_tecnica"),
          "notas", res["notas_rotuladas"], dict(res["ataques"]))
    print("motivos", dict(res["motivos"]))
    print("ambiguos", res.get("ambiguos_por_tipo"), "acima", res.get("arco_corda_acima"),
          "abaixo", res.get("arco_corda_abaixo"))


if __name__ == "__main__":
    main()

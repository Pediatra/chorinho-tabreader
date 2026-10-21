"""Prepara a conferência do ataque da T8.3 (2026-10-19), como o novos.py fez com a T8.2.

Lê as regiões que o dono marcou em ``data/saida/t83/ferramenta/conferencia_t83.json``. Tela
sem região vem como "sim/normal". Saída em ``conferir_t83/`` (cópia da conferência,
``ataque_t83.json`` e ``resumo.json``).

Uso (container): python /app/data/saida/tab_rotulo/r2/novos_t83.py
"""

import json
import shutil

import converter as cv

ORIGEM = cv.RAIZ / "data" / "saida" / "t83" / "ferramenta" / "conferencia_t83.json"


def main() -> None:
    """Grava a cópia, o arquivo de ataque e o resumo da T8.3."""
    saida = cv.SAIDA / "conferir_t83"
    saida.mkdir(exist_ok=True)
    cv.SEM_REGIAO_E_SEM_TECNICA = {"t83"}
    ataque, res = cv.processar_fonte("t83", ORIGEM)
    ataque["telas_conferidas"] = {}
    (saida / "ataque_t83.json").write_text(
        json.dumps(ataque, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    shutil.copy(ORIGEM, saida / ORIGEM.name)
    (saida / "resumo.json").write_text(
        json.dumps({"campo_x": cv.CAMPO_X, "fontes": {"t83": res}}, ensure_ascii=False,
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

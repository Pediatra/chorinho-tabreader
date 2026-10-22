"""Prepara a conferência do ataque nas fontes sem marca de técnica (R2, 2026-10-17).

Greensleeves, Gymnopédie, South American, Retrato v2 e a T8.2. Tela sem região vem
pré-preenchida com "sim/normal"; o dono troca as notas não atacadas e confirma a
tela. Saída em ``conferir_novos/`` (cópias do ouro, ataque_*.json, resumo.json).
"""

import json
import shutil

import converter as cv

NOVOS = {
    "greensleeves": cv.OURO / "greensleeves_guia_de_estudio_partitura_tab_pdf.json",
    "gymnopedie": cv.OURO
    / "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar.json",
    "south_american": cv.OURO
    / "south_american_music_easy_guitar_tutorial_with_sheet_and_tab.json",
    "retrato": cv.OURO / "retrato_brasileiro_v2.json",
    "t82": cv.FONTES["t82"],
}


def main() -> None:
    """Grava as cópias, os arquivos de ataque e o resumo das fontes novas."""
    saida = cv.SAIDA / "conferir_novos"
    saida.mkdir(exist_ok=True)
    cv.SEM_REGIAO_E_SEM_TECNICA = set(NOVOS)
    resumo = {"campo_x": cv.CAMPO_X, "fontes": {}}
    for nome, caminho in NOVOS.items():
        ataque, res = cv.processar_fonte(nome, caminho)
        ataque["telas_conferidas"] = {}
        (saida / f"ataque_{nome}.json").write_text(
            json.dumps(ataque, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        shutil.copy(caminho, saida / caminho.name)
        resumo["fontes"][nome] = res
        print(nome, res["telas_conferidas"], res.get("telas_sem_tecnica"),
              res["notas_rotuladas"], dict(res["ataques"]),
              res.get("ambiguos_por_tipo"))
    (saida / "resumo.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

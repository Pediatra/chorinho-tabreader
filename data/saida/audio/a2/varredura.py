"""Varredura explícita (diagnóstico) e diagnóstico do DTW. Roda no container com PYTHONPATH=/app.

Não altera as constantes do módulo: só as sobrescreve em tempo de execução, e grava cada
saída com o valor usado. A escolha final é do dono do projeto.
"""

import json
import os
import sys

from tab import audio_alinhar as aa
from tab.audio_alinhar_avaliar import avaliar, ler_regua
from tab.audio_extrair import garantir, ler

PRODUTO = "data/saida/conserto_v2/mvp.json"
VIDEO = "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4"
REGUA = "data/saida/audio/a1/atraso_mvp.json"
PASTA = "data/saida/audio/a2/varredura"


def resumo(alinhado, nome):
    regua, info = ler_regua(REGUA)
    res = avaliar(alinhado, regua, info)
    t = res["totais"]
    y = t["Y_colunas_regua_com_saida"]
    afirm = t["afirmadas"]
    print(
        f"{nome}: Y={y} afirmadas={afirm} <=50={t['ok50_fluxo']} "
        f"<=100={t['ok100_fluxo']} <=50F/A={t['ok50_fluxo_ou_alturas']} "
        f"falsos={t['falsos_mais_de_200ms']} recusadas={t['recusadas']} "
        f"sem_par={res['sem_par']['colunas_da_saida_sem_par_na_regua']} "
        f"afirm_sem_par={res['sem_par']['afirmadas_sem_par']}",
        flush=True,
    )
    return res


def main():
    os.makedirs(PASTA, exist_ok=True)
    with open(PRODUTO, encoding="utf-8") as f:
        oculto = aa.esconder_marcador(json.load(f))
    flac, meta = garantir(VIDEO)
    amostras, taxa = ler(flac)
    t_am0 = float(meta["t_amostra0"])
    saidas = {}
    for q in (0.0, 0.5, 0.75):
        aa.QUANTIL_PICO_FORTE = q
        alin = aa.alinhar(oculto, amostras, taxa, t_am0, metodo="onsets")
        nome = f"onsets QUANTIL_PICO_FORTE={q}"
        res = resumo(alin, nome)
        saidas[nome] = res
        with open(f"{PASTA}/onsets_q{q}.json", "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1, sort_keys=True)
            f.write("\n")
    aa.QUANTIL_PICO_FORTE = 0.75
    # Diagnóstico do DTW: sem recusa por cosseno (limiares zerados), só para ver a temporização.
    aa.LIMIAR_COSSENO_EXIBICAO = 0.0
    aa.LIMIAR_COSSENO_COLUNA = 0.0
    alin_dtw = aa.alinhar(oculto, amostras, taxa, t_am0, metodo="dtw")
    res = resumo(alin_dtw, "DIAGNOSTICO dtw sem recusa por cosseno")
    with open(f"{PASTA}/dtw_diagnostico_sem_recusa.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

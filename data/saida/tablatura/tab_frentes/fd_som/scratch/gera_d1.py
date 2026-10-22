"""Gera d1.json: tabela por vídeo no limiar L* (calibração nos ouros), parada e diagnóstico."""

import json
from collections import Counter

PASTA = "/app/data/saida/tab_frentes/fd_som/d1"
linhas = [json.loads(x) for x in open(f"{PASTA}/notas_ouros.jsonl", encoding="utf-8")]
cal = json.load(open(f"{PASTA}/calibracao_ouros.json", encoding="utf-8"))
resumo = json.load(open(f"{PASTA}/resumo_ouros.json", encoding="utf-8"))
L = cal["limiar_escolhido"]["L"]

por_video = {}
for r in linhas:
    v = por_video.setdefault(
        r["video"],
        Counter(),
    )
    v["labels_total"] += 1
    if r["rotulo"] in ("certa", "erro_casa", "inventada") and not r["excluida"]:
        v["labels_casa"] += 1
        if r["t_som"] is None:
            v["erro_sem_instante" if r["rotulo"] != "certa" else "certa_sem_instante"] += 1
        else:
            medida = r["score"] is not None
            if medida:
                v["medidas"] += 1
                if r["rotulo"] == "certa":
                    v["certas_medidas"] += 1
                else:
                    v["erros_medidos"] += 1
                    if r["score"] < L:
                        v["erros_sinalizados"] += 1
                    else:
                        v["erros_nao_sinalizados"] += 1
                if r["score"] < L:
                    v["sinalizadas"] += 1
                    if r["cos_som"] is not None and r["cos_som"] < 0.7:
                        v["sinalizadas_alinhamento_fraco"] += 1
                    if r["rotulo"] == "certa":
                        v["sinalizadas_certas"] += 1
    if r["rotulo"] == "perdida":
        v["perdidas"] += 1

tabela = {k: dict(v) for k, v in por_video.items()}
scan = {x["nome"]: {
    "varredura_mediana_certas": x["varredura_transposicao_mediana_certas"],
    "melhor_deslocamento": x["melhor_deslocamento"],
    "flac_cache": x["cache_flac"],
} for x in resumo}
saida = {
    "rodada": "0170",
    "frente": "D1 (som confere a casa)",
    "limiar_L_dB": L,
    "limiar_escolhido_calibracao": cal["limiar_escolhido"],
    "parada_precisao_menor_que_0_3": cal["parada_precisao_menor_que_0_3"],
    "teste_t82": "nao rodado: regra de parada da calibracao acionada (precisao < 0,3)",
    "tabela_por_video_ouros": tabela,
    "afinacao_varredura": scan,
}
import pathlib  # noqa: E402

pathlib.Path(f"{PASTA}/d1.json").write_text(
    json.dumps(saida, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
)
for k, v in tabela.items():
    print(k, v)
print(json.dumps(scan, ensure_ascii=False)[:800])

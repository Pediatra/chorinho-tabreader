"""Verificação depois da medida (1030 Parte A): o k do consenso denso nos 128 revisados."""

import collections
import json

from tab.maos_braco_video import (
    MAOS_M30,
    QUADROS_POR_SEGUNDO,
    RODADAS_REVISADAS,
    ARQUIVO_INDICE,
    _ler_json,
    ler_jsonl,
    nome_jsonl,
    videos_revisados,
)

parte_a = _ler_json(MAOS_M30 / "parte_a.json")
classe = {linha["id"]: linha for linha in parte_a["linhas"]["sozinho"]}
tabela = collections.Counter()
casos = []
for video in videos_revisados():
    registros = ler_jsonl(MAOS_M30 / nome_jsonl(video.numero))
    denso = {round(r["t"] * QUADROS_POR_SEGUNDO): r for r in registros}
    _, pasta = RODADAS_REVISADAS[video.rodada]
    for item in _ler_json(pasta / ARQUIVO_INDICE)["quadros"]:
        if item["arquivo"] != video.arquivo:
            continue
        chave = f"{video.rodada}:{item['id']}"
        rec = denso.get(round(float(item["t"]) * QUADROS_POR_SEGUNDO))
        if rec is None or chave not in classe:
            continue
        s4 = rec.get("S4")
        k = "sem tomada" if not s4 else ("k=None" if s4.get("k") is None else f"k={s4['k']}")
        linha = classe[chave]
        tabela[(linha["classe"], linha["sinalizado"], k)] += 1
        if linha["classe"] == "falso":
            casos.append((chave, linha["sinalizado"], k))
saida = {
    "tabela": [
        {"classe": c, "sinalizado": s, "k": k, "n": n}
        for (c, s, k), n in sorted(tabela.items(), key=str)
    ],
    "falsos": casos,
}
with open(MAOS_M30 / "k_nos_revisados.json", "w", encoding="utf-8") as f:
    json.dump(saida, f, ensure_ascii=False, indent=1)
print(json.dumps(saida, ensure_ascii=False, indent=1))

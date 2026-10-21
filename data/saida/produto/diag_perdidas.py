"""Diagnostico da rodada 0004: lista as notas perdidas e as casas erradas da regua."""

import json

from tab.avaliar_video import FRACAO_PASSO, _x_ouro, casar_notas, ler_predicao, notas_distintas

ouro = json.load(open("data/gold/ouro_video/retrato_brasileiro_v2.json", encoding="utf-8"))
dados = json.load(open("data/saida/produto/mvp.json", encoding="utf-8"))
rel = json.load(open("data/saida/produto/avaliacao_mvp.json", encoding="utf-8"))
pred = ler_predicao(dados)
mapa = {int(k): v for k, v in rel["telas"]["mapa"].items()}
por_id = {t.id: t for t in pred.telas}
for tela in ouro["telas"]:
    oid = int(tela["id"])
    pid = mapa.get(oid)
    if pid is None:
        continue
    t = por_id[pid]
    previstas = notas_distintas([n for n in t.notas if n.casa is not None])
    meia = FRACAO_PASSO * (t.passo or 0.0)
    notas = tela.get("notas", [])
    pares = casar_notas(notas, previstas, meia)
    casados_ouro = {i for i, _ in pares}
    for i, n in enumerate(notas):
        if i not in casados_ouro:
            print(f"PERDIDA ouro_tela={oid} corda={n['corda']} casa={n['casa']} x={_x_ouro(n):.1f}")
    for i, j in pares:
        if int(notas[i]["casa"]) != previstas[j].casa:
            print(
                f"CASA ouro_tela={oid} corda={notas[i]['corda']} x={_x_ouro(notas[i]):.1f} "
                f"ouro={notas[i]['casa']} previsto={previstas[j].casa}"
            )

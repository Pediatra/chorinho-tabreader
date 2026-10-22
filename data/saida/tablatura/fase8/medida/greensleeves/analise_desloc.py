"""Detalha os erros da régua por instante e por nota (só lê; usa as funções da régua)."""

import json
import sys

sys.path.insert(0, "/app")

from tab.avaliar_video import (  # noqa: E402
    _exibicao_em,
    classificar_instante,
    coluna_atual,
    coluna_que_chega,
    ler_predicao,
    ocorrencias,
)

OURO = "/app/data/gold/ouro_video/greensleeves_guia_de_estudio_partitura_tab_pdf.json"
PRED = "/app/data/saida/fase8/medida/greensleeves/run1.json"
PRE = "/app/data/saida/ouro_video/greensleeves_guia_de_estudio_partitura_tab_pdf/pre.json"
FPS = 25.0
import os
DESLOC = float(os.environ.get("DESLOC", "0"))
SAIDA = "/app/data/saida/fase8/medida/greensleeves/analise_desloc%s.json" % DESLOC

ouro = json.load(open(OURO, encoding="utf-8"))
dados = json.load(open(PRED, encoding="utf-8"))
pred = ler_predicao(dados)
telas_pred = {t.id: t for t in pred.telas}
telas_ouro = {int(t["id"]): t for t in ouro["telas"]}
mapa = {k: k for k in telas_ouro}  # pareamento por instantes = identidade (ver relatorio)

instantes = []
for inst in ouro["instantes"]:
    t = float(inst["t"])
    tid = inst.get("tela")
    coluna_ouro = inst.get("coluna_x_quadro")
    tela = telas_pred.get(mapa.get(tid)) if tid is not None else None
    if tela is None:
        instantes.append({"t": t, "tela_ouro": tid, "classe": "sem_tela_prevista"})
        continue
    ocorr = ocorrencias(tela)
    atual = coluna_atual(t, tela, ocorr)
    chega = coluna_que_chega(t, tela, ocorr, FPS)
    coluna_ouro = None if coluna_ouro is None else coluna_ouro + DESLOC
    classe = classificar_instante(t, coluna_ouro, atual, tela.passo, chega)
    ex = _exibicao_em(t, tela)
    # onde o ouro acende: nota da tela ouro mais próxima nesse x (para texto de tab)
    instantes.append(
        {
            "t": t,
            "tela_ouro": tid,
            "exibicao_pred": ex,
            "coluna_ouro_x": coluna_ouro,
            "pred_atual_x": None if atual is None else atual.x,
            "pred_onset": None if atual is None else atual.onset,
            "pred_anterior_x": None if atual is None else atual.anterior_x,
            "pred_chega": chega,
            "classe": classe,
        }
    )

# notas: pelo mesmo casamento da régua (corda + |dx| <= meia), sobre notas distintas
from tab.avaliar_video import FRACAO_PASSO, _x_ouro, casar_notas, notas_distintas  # noqa: E402

notas_erro = []
for tid, tela_ouro in telas_ouro.items():
    tela = telas_pred.get(mapa.get(tid))
    gold = tela_ouro["notas"]
    if tela is None:
        continue
    previstas = notas_distintas([n for n in tela.notas if n.casa is not None])
    meia = FRACAO_PASSO * tela.passo
    pares = casar_notas(gold, previstas, meia)
    ig = {i for i, _ in pares}
    ip = {j for _, j in pares}
    for i, g in enumerate(gold):
        if i in ig:
            p = previstas[[j for a, j in pares if a == i][0]]
            if int(g["casa"]) != p.casa:
                notas_erro.append({"tipo": "casa_errada", "tela": tid, "corda": g["corda"], "casa_ouro": g["casa"], "casa_prevista": p.casa, "x": _x_ouro(g), "t_prev": p.t_ini})
            continue
        notas_erro.append({"tipo": "perdida", "tela": tid, "corda": g["corda"], "casa_ouro": g.get("casa"), "x": _x_ouro(g), "x_centro": g.get("x_centro_quadro")})
    for j, p in enumerate(previstas):
        if j in ip:
            continue
        notas_erro.append({"tipo": "inventada", "tela": tid, "corda": p.corda, "casa_prevista": p.casa, "x": p.x, "t_prev": p.t_ini})

json.dump({"instantes": instantes, "notas": notas_erro}, open(SAIDA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
from collections import Counter  # noqa: E402

print("classes:", Counter(i["classe"] for i in instantes))
print("notas:", Counter(n["tipo"] for n in notas_erro))
for i in instantes:
    print(
        f"t={i['t']:>7} tela={i['tela_ouro']} ouro_x={i.get('coluna_ouro_x')} "
        f"pred_x={i.get('pred_atual_x')} onset={i.get('pred_onset')} "
        f"ant={i.get('pred_anterior_x')} chega={i.get('pred_chega')} -> {i['classe']}"
    )
for n in notas_erro:
    print(n)

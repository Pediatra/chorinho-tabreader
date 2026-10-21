"""Monta o lote de nut fora da 1031 a partir dos vídeos inteiros da 1030 (uma vez só).

Candidato: quadro denso com braço em que a ponta das cordas do lado do nut (ou o nut
previsto) fica a até 3 % da borda da imagem. No máximo 2 por vídeo, a ≥ 10 s um do outro
e a ≥ 3 s de qualquer quadro já revisado. Semente fixa; o gabarito sai preenchido com a
previsão (cordas e trastes), e o dono marca o nut "fora" e o traste de referência.
"""

import json
import random

from tab.caminhos import GABARITO_BRACO_M31, MAOS_M30, MAOS_M31, acervo
from tab.maos_braco_ciclo import ARQUIVO_INDICE, registro_previsto
from tab.maos_braco_gabarito import FORMATO_GABARITO, acrescentar
from tab.maos_braco_video import (
    RODADAS_REVISADAS,
    _ler_json,
    ler_jsonl,
    nome_jsonl,
    videos_revisados,
)
from tab.maos_gabarito import gravar_atomico

SEMENTE = 20261031
FRACAO_BORDA = 0.03
POR_VIDEO = 3
ALVO = 20


def perto_da_borda(p, largura, altura):
    """Se o ponto está a até FRACAO_BORDA da borda (ou fora dela)."""
    mx, my = FRACAO_BORDA * largura, FRACAO_BORDA * altura
    return p[0] <= mx or p[0] >= largura - mx or p[1] <= my or p[1] >= altura - my


rng = random.Random(SEMENTE)
candidatos = []
dimensoes = {}
for video in videos_revisados():
    _, pasta = RODADAS_REVISADAS[video.rodada]
    itens = [i for i in _ler_json(pasta / ARQUIVO_INDICE)["quadros"] if i["arquivo"] == video.arquivo]
    largura, altura = itens[0]["largura"], itens[0]["altura"]
    dimensoes[video.arquivo] = (largura, altura)
    revisados = [float(i["t"]) for i in itens]
    bons = []
    for r in ler_jsonl(MAOS_M30 / nome_jsonl(video.numero)):
        pr = r["previsto"]
        if not pr["achou"] or not pr.get("corda1") or not pr.get("nut"):
            continue
        if min(abs(r["t"] - t) for t in revisados) < 3.0:
            continue
        # A ponta de cada corda mais perto do nut previsto.
        pontas = [
            min(pr[c], key=lambda q: (q[0] - pr["nut"][0]) ** 2 + (q[1] - pr["nut"][1]) ** 2)
            for c in ("corda1", "corda6")
        ]
        if any(perto_da_borda(p, largura, altura) for p in [pr["nut"], *pontas]):
            bons.append(r)
    rng.shuffle(bons)
    escolhidos = []
    for r in bons:
        if all(abs(r["t"] - e["t"]) >= 10.0 for e in escolhidos):
            escolhidos.append(r)
        if len(escolhidos) == POR_VIDEO:
            break
    candidatos += [(video.arquivo, r) for r in escolhidos]
    print(video.arquivo[:50], len(bons), "candidatos;", len(escolhidos), "escolhidos")

rng.shuffle(candidatos)
candidatos = sorted(candidatos[:ALVO], key=lambda c: (c[0], c[1]["t"]))
MAOS_M31.mkdir(parents=True, exist_ok=True)
if (MAOS_M31 / ARQUIVO_INDICE).exists() or GABARITO_BRACO_M31.exists():
    raise SystemExit("lote já existe: nada é sobrescrito")
gravar_atomico(MAOS_M31 / ARQUIVO_INDICE, {"semente": SEMENTE, "quadros": []})
gravar_atomico(
    GABARITO_BRACO_M31,
    {
        "formato": FORMATO_GABARITO,
        "como_foi_rotulado": (
            "dono, por quadro, na ferramenta tab.maos_braco_gabarito; lote de nut fora da "
            "1031 (candidatos da 1030 com a ponta das cordas a ≤ 3 % da borda); "
            "preenchido com a previsão; o dono marca nut fora e o traste de referência"
        ),
        "semente": SEMENTE,
        "ferramenta": "tab.maos_braco_gabarito",
        "quadros": {},
    },
)
itens = [{"arquivo": a, "t": round(r["t"], 2), "tab": None} for a, r in candidatos]
ids = acrescentar(itens, acervo(), MAOS_M31, GABARITO_BRACO_M31)
gabarito = _ler_json(GABARITO_BRACO_M31)
for id_q, (arquivo, r) in zip(ids, candidatos):
    gabarito["quadros"][id_q] = registro_previsto(
        gabarito["quadros"][id_q], r["previsto"], False, dimensoes[arquivo]
    )
    gabarito["quadros"][id_q]["obs"] = None
gravar_atomico(GABARITO_BRACO_M31, gabarito)
gravar_atomico(
    MAOS_M31 / "lote.json",
    {"semente": SEMENTE, "quadros": [{"id": i, "arquivo": a, "t": r["t"], "denso": r["id"]} for i, (a, r) in zip(ids, candidatos)]},
)
print(len(ids), "quadros:", ids)

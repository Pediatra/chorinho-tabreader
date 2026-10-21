"""Diagnóstico pós-calibração (NÃO entra no aceite): é resolução, alinhamento ou o desenho da baseline?

Mede, nas notas certas e nas erradas dos 4 ouros:
  A) a medida congelada (mediana da janela de 2 s), no instante do som;
  B) a mesma banda, com baseline = mediana de [t-1,0 s ; t-0,05 s] (antes do ataque);
  C) a medida congelada deslocada: instante do som -0,2 s e +0,2 s (alinhamento).
Reporta AUC (certa vs erro de casa + inventada): 0,5 = acaso; 1,0 = separa perfeito.
"""

import json
import sys

import numpy as np

sys.path.insert(0, "/app")
from tab.audio_extrair import ler  # noqa: E402
from tab.som_casa_energia import (  # noqa: E402
    ATAQUE_ANTES_S,
    ATAQUE_DEPOIS_S,
    espectro_local,
    energia_faixa_db,
    frequencia_midi,
    pontuar,
)
from tab.som_casa_medida import tarefas_ouros  # noqa: E402
from tab.som_casa_notas import rotular  # noqa: E402
from tab.som_casa_produtos import flac_para  # noqa: E402
from tab.audio_onsets import MIDI_CORDA  # noqa: E402


def auc(pos: np.ndarray, neg: np.ndarray) -> float:
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    todos = np.concatenate([pos, neg])
    ordem = todos.argsort(kind="mergesort")
    ranks = np.empty(len(todos))
    ranks[ordem] = np.arange(1, len(todos) + 1)
    return float((ranks[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def pontuar_pre(amostras, taxa, t, midi):
    tempos, freqs, mag2 = espectro_local(amostras, taxa, t)
    if len(tempos) == 0:
        return None
    ataque = (tempos >= t - ATAQUE_ANTES_S) & (tempos <= t + ATAQUE_DEPOIS_S)
    pre = (tempos >= t - 1.0) & (tempos <= t - 0.05)
    if not ataque.any() or not pre.any():
        return None
    vals = []
    for k in (1, 2, 3):
        f = k * frequencia_midi(midi)
        if f >= 0.5 * taxa * 0.97:
            continue
        e = energia_faixa_db(freqs, mag2, f)
        vals.append(e[ataque].max() - np.median(e[pre]))
    return float(np.mean(vals)) if vals else None


resultados = {}
for tarefa in tarefas_ouros():
    notas = rotular(tarefa["produto"], tarefa["ouro"], tarefa["instantes"], tarefa["audio"], recortado=tarefa["recortado"])
    flac, _ = flac_para(tarefa["video"])
    amostras, taxa = ler(flac)
    grupos = {"A": ([], []), "B": ([], []), "C-": ([], []), "C+": ([], [])}
    for n in notas:
        if n.rotulo not in ("certa", "erro_casa", "inventada") or n.excluida or n.t_som is None:
            continue
        midi = MIDI_CORDA[n.corda] + (n.casa or 0)
        lado = 0 if n.rotulo == "certa" else 1
        a = pontuar(amostras, taxa, n.t_som, midi)["score"]
        b = pontuar_pre(amostras, taxa, n.t_som, midi)
        cm = pontuar(amostras, taxa, n.t_som - 0.2, midi)["score"]
        cp = pontuar(amostras, taxa, n.t_som + 0.2, midi)["score"]
        for chave, v in (("A", a), ("B", b), ("C-", cm), ("C+", cp)):
            if v is not None:
                grupos[chave][lado].append(v)
    linha = {}
    for chave, (certas, erradas) in grupos.items():
        linha[chave] = {
            "AUC": round(auc(np.array(erradas), np.array(certas)), 3),
            "mediana_certa": round(float(np.median(certas)), 2) if certas else None,
            "mediana_errada": round(float(np.median(erradas)), 2) if erradas else None,
            "n_certas": len(certas),
            "n_erradas": len(erradas),
        }
    resultados[tarefa["nome"]] = linha
    print(tarefa["nome"], json.dumps(linha, ensure_ascii=False), flush=True)

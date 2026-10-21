"""Casos olhados da D1 (10 casos): recorte da tela no instante do som + espectro, em PNG.

Escolhe, nos notas_ouros.jsonl, os erros medidos (erro_casa e inventada) e, para completar
10, as notas certas de menor score (as mais suspeitas). Para cada caso, grava um PNG com:
em cima, o recorte da tab (painel) no quadro do instante do som; embaixo, o espectro de
60 a 700 Hz numa janela de ±0,6 s, com o instante do som (vertical branca) e as
frequências esperadas f0, 2f0 e 3f0 (linhas verdes) da altura lida.
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, "/app")
from tab import leitor, painel  # noqa: E402
from tab.audio_onsets import MIDI_CORDA  # noqa: E402
from tab.som_casa_energia import espectro_local, frequencia_midi  # noqa: E402
from tab.som_casa_medida import tarefas_ouros  # noqa: E402
from tab.som_casa_produtos import flac_para  # noqa: E402
from tab.audio_extrair import ler  # noqa: E402

PASTA = Path("/app/data/saida/tab_frentes/fd_som/casos")
PASTA.mkdir(parents=True, exist_ok=True)

linhas = [
    json.loads(x)
    for x in open("/app/data/saida/tab_frentes/fd_som/d1/notas_ouros.jsonl", encoding="utf-8")
]
medidas = [
    r
    for r in linhas
    if r["rotulo"] in ("certa", "erro_casa", "inventada")
    and not r["excluida"]
    and r["t_som"] is not None
    and r["score"] is not None
]
erros = sorted(
    [r for r in medidas if r["rotulo"] != "certa"], key=lambda r: (r["video"], r["t_som"])
)
certas = sorted(
    [r for r in medidas if r["rotulo"] == "certa"], key=lambda r: r["score"]
)
escolhidos = erros[:6] + certas[:10]
escolhidos = escolhidos[:10]
videos = {t["nome"]: t for t in tarefas_ouros()}
cache_audio = {}
for n, r in enumerate(escolhidos, 1):
    t = videos[r["video"]]
    if r["video"] not in cache_audio:
        flac, _ = flac_para(t["video"])
        cache_audio[r["video"]] = ler(flac)
    amostras, taxa = cache_audio[r["video"]]
    midi = MIDI_CORDA[r["corda"]] + (r["casa"] if r["casa"] is not None else 0)
    tempos, freqs, mag2 = espectro_local(amostras, taxa, r["t_som"])
    banda = (freqs >= 60) & (freqs <= 700)
    db = 10 * np.log10(mag2[:, banda] + 1e-12)
    db = (db - db.min()) / max(1e-9, db.max() - db.min())
    img_esp = (db.T[::-1] * 255).astype(np.uint8)  # frequência crescente para cima
    img_esp = cv2.resize(img_esp, (600, 300), interpolation=cv2.INTER_NEAREST)
    img_esp = cv2.cvtColor(img_esp, cv2.COLOR_GRAY2BGR)
    fx = lambda f: int(round((np.log(f) - np.log(60)) / (np.log(700) - np.log(60)) * 299))  # noqa: E731
    f0 = frequencia_midi(midi)
    for k in (1, 2, 3):
        f = k * f0
        if 60 <= f <= 700:
            y = 299 - fx(f)
            cv2.line(img_esp, (0, y), (599, y), (0, 200, 0), 1)
    x_som = int(round((r["t_som"] - tempos[0]) / (tempos[-1] - tempos[0] + 1e-9) * 599))
    cv2.line(img_esp, (x_som, 0), (x_som, 299), (255, 255, 255), 1)
    frame = leitor.quadro_em(t["video"], r["t_som"])
    recorte = None
    if frame is not None:
        c = painel.escolher_ou_mascara(frame)
        if c is not None:
            recorte = cv2.resize(c.roi, (600, max(60, int(600 * c.roi.shape[0] / c.roi.shape[1]))))
    if recorte is None:
        recorte = np.zeros((120, 600, 3), dtype=np.uint8)
    cabecalho = np.zeros((60, 600, 3), dtype=np.uint8)
    texto = (
        f"{n} {r['rotulo']} corda {r['corda']} casa {r['casa']} "
        f"(ouro {r['casa_ouro']}) t={r['t_som']:.2f}s score={r['score']:.1f}"
    )
    cv2.putText(cabecalho, texto[:70], (4, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)
    cv2.putText(cabecalho, f"{r['video'][:40]} tela {r['tela']} col {r['coluna']}", (4, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 200, 200), 1)
    painel_img = np.vstack([cabecalho, recorte, img_esp])
    nome = f"caso_{n:02d}_{r['video']}_{r['rotulo']}_c{r['corda']}_k{r['casa']}_t{r['t_som']:.2f}.png".replace(" ", "_")
    caminho = PASTA / nome
    cv2.imwrite(str(caminho), painel_img)
    print(n, caminho.name, r["rotulo"], r["score"], "quadro" if frame is not None else "sem quadro", flush=True)

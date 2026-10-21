"""CA1 da D1: reproduz a T8.2 (modelo final_s1_ger) e as dobras (avaliar_video) do plano."""

import glob
import json
import os
import subprocess
import sys

RAIZ = "/app"
FRENTE = f"{RAIZ}/data/saida/tab_frentes/fd_som"
CA1 = f"{FRENTE}/ca1"
os.makedirs(CA1, exist_ok=True)

# 1) T8.2: copia da frente, com a saida trocada (feito na pasta ca1)
r = subprocess.run(
    [sys.executable, f"{CA1}/t82_comparar.py"],
    cwd=RAIZ,
    capture_output=True,
    text=True,
)
print("T8.2 rc", r.returncode)
print(r.stdout[-1500:])
print(r.stderr[-800:])

# 2) dobras: avaliar_video sobre as leituras gravadas do gerador novo
resultados = {}
for pred in sorted(glob.glob(f"{RAIZ}/data/saida/fase8/ger/ger/*.json")):
    if pred.endswith(".regua.json"):
        continue
    slug = os.path.basename(pred)[:-5]
    ouro = f"{RAIZ}/data/gold/ouro_video/{slug}.json"
    if not os.path.exists(ouro):
        print("SEM OURO", slug)
        continue
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "tab.avaliar_video",
            "--ouro",
            ouro,
            "--pred",
            pred,
            "--json",
            f"{CA1}/{slug}.aval.json",
        ],
        cwd=RAIZ,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print("ERRO", slug, r.stderr[-600:])
    try:
        d = json.load(open(f"{CA1}/{slug}.aval.json"))
        resultados[slug] = d
    except Exception as e:  # noqa: BLE001
        print("sem json", slug, e)
for k, d in resultados.items():
    print("==", k[:40], "chaves:", list(d.keys())[:12])
    print("   notas:", json.dumps(d.get("notas"), ensure_ascii=False)[:400])

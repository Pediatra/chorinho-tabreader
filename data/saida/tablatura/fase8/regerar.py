"""Regera o ouro v2 inicial dos 7 vídeos da Fase 8 (sem trabalho do dono ainda)."""

import json
import subprocess
from pathlib import Path

ESC = ["south american", "gymnop", "la vie", "end of beginning", "room 335",
       "greensleeves", "from this place"]
d = json.loads(Path("data/saida/fase8/candidatos.json").read_text())
canais = d["canais"]
itens = canais.values() if isinstance(canais, dict) else canais
arqs = []
for v in itens:
    for x in (v["candidatos"] if isinstance(v, dict) else v):
        if any(s in x["arquivo"].lower() for s in ESC):
            arqs.append(x["arquivo"])
gold = sorted(Path("data/gold/ouro_video").glob("*.json"))
for arq in arqs:
    from tab.ouro_video import fazer_slug  # noqa: PLC0415 (script descartável)
    slug = fazer_slug(Path(arq).stem)
    g = Path(f"data/gold/ouro_video/{slug}.json")
    if g.exists():
        assert "conferida\": true" not in g.read_text(), g
        g.unlink()
    subprocess.run(["rm", "-rf", f"data/saida/ouro_video/{slug}"], check=True)
    r = subprocess.run(["python", "-m", "tab.ouro_video", "completar", f"/acervo/{arq}",
                        "--ouro-v2", str(g), "--saida", f"data/saida/ouro_video/{slug}"],
                       capture_output=True, text=True)
    print(slug, "rc", r.returncode, r.stderr[-300:] if r.returncode else "", flush=True)
print("FIM_REGERAR", len(arqs))

"""Rodada 3025: notas do Audiveris que somem ao trocar o compasso, no athletic P01a."""
import json
import re
from collections import Counter
from pathlib import Path

from tab.partitura_gabarito import _e_nota, ler_partitura

LETRAS = "CDEFGAB"
SP = Path("data/saida/partitura/sem_produto")
slug = next(p for p in SP.iterdir() if p.name.startswith("athletic_theme_f"))
doc = json.loads(next(slug.glob("*.partitura.json")).read_text("utf-8"))
pauta = next(p for p in doc["pautas"] if p["recorte"] == "P01a")
aud = ler_partitura(slug / "omr/audiveris/x2_margem_herdada/P01a/saida.musicxml")
homr = ler_partitura(slug / "omr/homr/nativo/P01a/saida.musicxml")


def deg(s):
    m = re.fullmatch(r"([A-G])[#b]*(-?\d+)", s["nome"])
    return int(m.group(2)) * 7 + LETRAS.index(m.group(1))


gab = json.loads(Path("data/gold/partitura/leitura_sem_produto.json").read_text("utf-8"))
reg = gab["recortes"]["athletic_theme_f_P01a"]
print("chaves do registro:", sorted(reg))
for n in pauta["compassos_homr"]:
    k = [c["numero"] for c in aud["compassos"]].index(n)
    a = Counter(deg(s) for s in aud["compassos"][k]["simbolos"] if _e_nota(s))
    h = Counter(deg(s) for s in homr["compassos"][k]["simbolos"] if _e_nota(s))
    na = Counter(s["nome"] for s in aud["compassos"][k]["simbolos"] if _e_nota(s))
    nh = Counter(s["nome"] for s in homr["compassos"][k]["simbolos"] if _e_nota(s))
    print(f"compasso {n}: aud {sum(a.values())} homr {sum(h.values())}"
          f" | degraus do aud ausentes no homr {sum((a-h).values())}"
          f" | nomes do aud ausentes no homr {dict(na-nh)}"
          f" | nomes do homr que diferem só no acidente: {dict(nh-na)}")

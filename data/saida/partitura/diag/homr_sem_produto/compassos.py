"""Notas por compasso: Audiveris (herdada) x homr, nos 3 recortes."""
from pathlib import Path

from tab.partitura_gabarito import _e_nota, ler_partitura

SP = Path("data/saida/partitura/sem_produto")
DH = Path("data/saida/partitura/diag/homr_sem_produto/homr")
for p in sorted(DH.iterdir()):
    slug = next(s.name for s in SP.iterdir() if s.name.startswith(p.name))
    for r in p.iterdir():
        a = ler_partitura(SP / slug / f"omr/audiveris/x2_margem_herdada/{r.name}/saida.musicxml")
        h = ler_partitura(r / "saida.musicxml")
        print(p.name, r.name)
        for nome, doc in (("audiveris", a), ("homr", h)):
            linhas = []
            for c in doc["compassos"]:
                notas = [s for s in c["simbolos"] if _e_nota(s)]
                agudas = sum(s["midi"] >= 64 for s in notas)
                linhas.append(f"{len(notas)}({agudas})")
            print(f"  {nome:9} notas(>=E4) por compasso: {' '.join(linhas)}")

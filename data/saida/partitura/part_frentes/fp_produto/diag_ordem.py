"""Diagnóstico da P4 (só leitura): tipos de `compasso`, `x_quadro` nulo e ordem dos eventos."""

import collections
import json
import pathlib

RAIZ = pathlib.Path("/app/data/saida/partitura/video")
for pasta in sorted(RAIZ.iterdir()):
    arquivo = next(pasta.glob("*.partitura.json"))
    doc = json.loads(arquivo.read_text(encoding="utf-8"))
    eventos = [e for p in doc["pautas"] for e in p["eventos"]]
    tipos = collections.Counter(type(e["compasso"]).__name__ for e in eventos)
    nulos = sum(1 for e in eventos if e["x_quadro"] is None)
    fora_de_ordem = 0
    for pauta in doc["pautas"]:
        xs = [e["x_quadro"] for e in pauta["eventos"]]
        if None not in xs and xs != sorted(xs):
            fora_de_ordem += 1
    erros = [p["recorte"] for p in doc["pautas"] if "erro" in p]
    print(pasta.name[:24], "pautas", len(doc["pautas"]), "eventos", len(eventos))
    print("  tipos compasso", dict(tipos), "x None", nulos, "pautas fora de ordem", fora_de_ordem)
    print("  pautas com erro", erros)
    print("  chaves da pauta", sorted(doc["pautas"][0].keys()))
    print("  chaves do resumo", sorted(doc["resumo"].keys()))
    print("  primeiro evento", json.dumps(doc["pautas"][0]["eventos"][0], ensure_ascii=False)[:400])

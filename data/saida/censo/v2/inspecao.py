"""Inspeção dos JSONL do censo v2 (linhas x vídeos x chaves). NÃO é código do projeto."""

import collections
import json
import sys

for caminho in sys.argv[1:]:
    linhas = [json.loads(x) for x in open(caminho, encoding="utf-8") if x.strip()]
    arquivos = collections.Counter(r["arquivo"] for r in linhas)
    chaves = collections.Counter(r["chave"] for r in linhas)
    tipos = collections.Counter(tuple(sorted(r.keys())) for r in linhas)
    erros = sum(1 for r in linhas if "erro" in r)
    dup_arq = sum(1 for v in arquivos.values() if v > 1)
    print(f"{caminho}: linhas={len(linhas)} arquivos={len(arquivos)} chaves={len(chaves)}")
    print(f"   arquivos repetidos={dup_arq} | linhas com erro={erros}")
    print(f"   formatos de linha distintos={len(tipos)}")
    for t, n in tipos.most_common(4):
        print(f"      {n} x {t}")
    if dup_arq:
        ex = [a for a, v in arquivos.items() if v > 1][:3]
        for a in ex:
            ocorr = [r for r in linhas if r["arquivo"] == a]
            print(f"   exemplo repetido {a}: " + " | ".join(
                f"chave={r['chave']} erro={r.get('erro')}" for r in ocorr))

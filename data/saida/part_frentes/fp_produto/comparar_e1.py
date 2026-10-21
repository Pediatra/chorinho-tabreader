"""Compara um e1.json regerado com o e1.json atual da frente E, campo a campo (P4, passo 1).

Uso (dentro do container): python comparar_e1.py CAMINHO_DO_NOVO
"""

import json
import sys

ATUAL = "/app/data/saida/part_frentes/fe_completar/e1.json"
NOVO = sys.argv[1]


def carregar(caminho):
    with open(caminho, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def comparar(caminho, x, y, diferencas):
    if type(x) is not type(y):
        diferencas.append((caminho, x, y))
        return
    if isinstance(x, dict):
        for chave in sorted(set(x) | set(y)):
            if chave not in x or chave not in y:
                diferencas.append(
                    (f"{caminho}.{chave}", x.get(chave, "<ausente>"), y.get(chave, "<ausente>"))
                )
            else:
                comparar(f"{caminho}.{chave}", x[chave], y[chave], diferencas)
    elif isinstance(x, list):
        if len(x) != len(y):
            diferencas.append((f"{caminho} (tamanho)", len(x), len(y)))
        for i, (p, q) in enumerate(zip(x, y, strict=False)):
            comparar(f"{caminho}[{i}]", p, q, diferencas)
    elif x != y:
        diferencas.append((caminho, x, y))


diferencas: list = []
comparar("", carregar(ATUAL), carregar(NOVO), diferencas)
print(f"e1 atual: {ATUAL}")
print(f"e1 novo:  {NOVO}")
print(f"diferenças campo a campo: {len(diferencas)}")
for caminho, antes, depois in diferencas[:40]:
    print(f"  {caminho}: atual={antes!r} novo={depois!r}")

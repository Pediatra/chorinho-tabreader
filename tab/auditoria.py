"""Lê os rótulos do dono na auditoria e diz se o MODELO erra (e onde).

A auditoria é o único instrumento que responde "o modelo erra?" com o olho do dono em vez de
inferência minha. Duas armadilhas já custaram rodadas e estão tratadas aqui:

1. **A métrica antiga media contra as MARCAS, não contra os rótulos.** Ela contava como falso positivo
   todo aprovado que não estava em cima de uma marca — e o dono confirmou **9 símbolos** que não tinham
   marca nenhuma. Medir contra as marcas pune o modelo por achar o que o dono não marcou.
2. **A amostra pode ser pequena.** A primeira auditoria tinha 30 janelas julgadas; precisão 29/29 = 1,000
   ali **não** prova precisão 1,000 no pool de 1.869 candidatos. Este módulo imprime o `n` junto de cada
   número justamente para isso não se perder.

Uso:

    python -m tab.auditoria <rotulada.json> <itens.json>
"""

import argparse
import json
import pathlib
import sys
from collections import Counter, defaultdict

FAIXAS = ((0.5, 0.7), (0.7, 0.9), (0.9, 1.01))


def carregar(caminho_rotulos: str, caminho_itens: str) -> tuple[list[dict], dict]:
    """Lê os rótulos do dono e os itens que o modelo julgou.

    Args:
        caminho_rotulos: JSON exportado pela página (`{"rotulos": [...]}`).
        caminho_itens: JSON com os itens da auditoria (`{"itens": [...]}`).

    Returns:
        ``(rotulos, itens_por_janela)``.
    """
    rotulos = json.loads(pathlib.Path(caminho_rotulos).read_text(encoding="utf-8"))["rotulos"]
    itens = json.loads(pathlib.Path(caminho_itens).read_text(encoding="utf-8"))["itens"]
    return rotulos, {x["janela"]: x for x in itens}


def resumir(rotulos: list[dict]) -> dict:
    """Resume os rótulos em aprovados/recusados, faixas e erros do modelo.

    Args:
        rotulos: lista de rótulos exportados pela página.

    Returns:
        Dicionário com as contagens e as precisões calculadas.
    """
    com_janela = [x for x in rotulos if x.get("janela")]
    aprovados = [x for x in com_janela if x.get("aprovado")]
    recusados = [x for x in com_janela if not x.get("aprovado")]
    c_aprov = Counter(x["rotulo_do_dono"] for x in aprovados)
    c_recus = Counter(x["rotulo_do_dono"] for x in recusados)
    faixas: dict[str, Counter] = defaultdict(Counter)
    for x in aprovados:
        for baixo, alto in FAIXAS:
            if baixo <= x["prob"] < alto:
                faixas[f"{baixo:.1f}-{alto:.1f}"][x["rotulo_do_dono"]] += 1
    return {
        "rotulos": len(rotulos),
        "com_janela": len(com_janela),
        "aprovados": len(aprovados),
        "aprovados_sim": c_aprov.get("sim", 0),
        "aprovados_nao": c_aprov.get("nao", 0),
        "aprovados_duvida": c_aprov.get("duvida", 0),
        "recusados": len(recusados),
        "recusados_sim": c_recus.get("sim", 0),
        "faixas": {k: dict(v) for k, v in sorted(faixas.items())},
        # ERRO DO MODELO = aprovado que o dono disse que NÃO é símbolo (não inclui recusado!)
        "erros_do_modelo": [
            {"imagem": x["imagem"], "prob": x["prob"], "w": x.get("w"), "h": x.get("h")}
            for x in aprovados
            if x["rotulo_do_dono"] == "nao"
        ],
    }


def main() -> int:
    """Imprime o resumo da auditoria a partir de um arquivo de rótulos."""
    ap = argparse.ArgumentParser()
    ap.add_argument("rotulos")
    ap.add_argument("itens")
    args = ap.parse_args()
    rotulos, _ = carregar(args.rotulos, args.itens)
    r = resumir(rotulos)
    print(
        f"rótulos: {r['rotulos']} | com janela julgada pelo modelo: {r['com_janela']}"
    )
    print(
        f"\nAPROVADOS: {r['aprovados']} | sim={r['aprovados_sim']} nao={r['aprovados_nao']} "
        f"duvida={r['aprovados_duvida']}"
    )
    if r["aprovados"]:
        print(
            f"  -> precisão do modelo NESTA AMOSTRA: "
            f"{r['aprovados_sim']}/{r['aprovados']} = {r['aprovados_sim'] / r['aprovados']:.3f}"
        )
    print(f"RECUSADOS: {r['recusados']} | sim (símbolo perdido) = {r['recusados_sim']}")
    print("\nPOR FAIXA (aprovados):")
    for faixa, c in r["faixas"].items():
        n = sum(c.values())
        print(
            f"  {faixa}: n={n:<4} sim={c.get('sim', 0):<4} nao={c.get('nao', 0):<4} "
            f"duvida={c.get('duvida', 0):<4} precisão={c.get('sim', 0) / n:.3f}"
        )
    print(f"\nERRO DO MODELO (aprovou e NÃO é símbolo): {len(r['erros_do_modelo'])}")
    for e in r["erros_do_modelo"][:15]:
        print(f"   {e['imagem'][:20]:<20} prob={e['prob']} {e['w']}x{e['h']} passos")
    return 0


if __name__ == "__main__":
    sys.exit(main())

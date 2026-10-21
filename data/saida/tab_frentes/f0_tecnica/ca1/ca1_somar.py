"""Soma notas.total das 6 dobras (CA1 da rodada 0101) e compara com o esperado."""

import json
from pathlib import Path

PASTA = Path("/app/data/saida/tab_frentes/f0_tecnica/ca1_dobras_v2")
ESPERADO = {
    "notas_ouro": 1771,
    "entregues": 1799,
    "casadas": 1761,
    "casa_certa": 1744,
    "inventadas": 38,
    "perdidas": 10,
}


def main() -> None:
    """Soma os totais das seis dobras e imprime a comparação com o CA1."""
    soma = {k: 0 for k in ESPERADO}
    for caminho in sorted(PASTA.glob("*.json")):
        total = json.loads(caminho.read_text(encoding="utf-8"))["notas"]["total"]
        for k in soma:
            soma[k] += int(total[k])
        print(caminho.stem, {k: total[k] for k in soma})
    print("soma", soma)
    print("esperado", ESPERADO)
    print("CA1 bate:", soma == ESPERADO)


if __name__ == "__main__":
    main()

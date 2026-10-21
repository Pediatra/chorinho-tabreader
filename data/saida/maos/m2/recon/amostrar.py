"""Sorteia 12 notas com tempo do mvp.json (uma por faixa de tempo, semente 20261012)."""

import json
import random
from pathlib import Path

RAIZ = Path("/var/home/gabriel/Projects/chorinho-dataset")
MVP = RAIZ / "data/saida/produto/mvp.json"
SAIDA = RAIZ / "data/saida/maos/m2/recon/amostra_12.json"


def main() -> None:
    mvp = json.loads(MVP.read_text(encoding="utf-8"))
    notas = [n for n in mvp["notas"] if n.get("t_ini") is not None]
    notas.sort(key=lambda n: n["t_ini"])
    ini, fim = notas[0]["t_ini"], notas[-1]["t_ini"]
    largura = (fim - ini) / 12
    rng = random.Random(20261012)
    escolhidas = []
    for k in range(12):
        lo = ini + k * largura
        hi = ini + (k + 1) * largura
        faixa = [n for n in notas if lo <= n["t_ini"] < hi or (k == 11 and n["t_ini"] == fim)]
        escolha = rng.choice(faixa)
        escolhidas.append(
            {
                "faixa": k,
                "tempo": escolha["t_ini"],
                "tela": escolha["tela"],
                "corda": escolha["corda"],
                "casa": escolha["casa"],
                "coluna": escolha["coluna"],
                "tecnica": escolha["tecnica"],
                "candidatas_na_faixa": len(faixa),
            }
        )
    escolhidas.sort(key=lambda n: n["tempo"])
    SAIDA.write_text(
        json.dumps(
            {
                "semente": 20261012,
                "criterio": "notas do mvp.json com t_ini; 12 faixas de tempo iguais "
                "entre o primeiro e o ultimo t_ini; uma por faixa com random.Random.choice",
                "notas": escolhidas,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"notas com tempo: {len(notas)}; instantes distintos: {len({n['t_ini'] for n in notas})}")
    print(f"faixa de {ini:.2f} a {fim:.2f} s, largura {largura:.2f} s")
    for e in escolhidas:
        print(e)


if __name__ == "__main__":
    main()

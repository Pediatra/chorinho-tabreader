"""D1 da partitura: sorteio da amostra para o gabarito novo (rodada 3160).

Sorteia **antes** de qualquer leitura de vídeo. Peso por canal: a ``extrapolacao`` de
``data/saida/partitura/p0/resumo.json``. Os 10 canais com extrapolação ≥ 5 levam 1 vídeo
cada. Os outros canais com extrapolação > 0 dividem o restante (30 vídeos) em proporção,
pelo método do maior resto. Cada canal sorteia seus vídeos com uma semente fixa, derivada da
semente do P0 e do nome do canal.

A população é o acervo de hoje, menos os 14 vídeos dos gabaritos e os 11 do piloto sem
produto. Canal que não está no P0 fica fora, e é listado.

Só lê o que está gravado e grava ``amostra.json`` na pasta da frente D. O commit não é feito
aqui (esta máquina não tem git); o arquivo é o registro.

Uso (na raiz do projeto)::

    python -m tab.partitura_amostra
"""

from __future__ import annotations

import argparse
import json
import random

from .caminhos import PART_FRENTE_D, SAIDA, acervo

RESUMO = SAIDA / "partitura" / "p0" / "resumo.json"
PASTA_SEM_PRODUTO = SAIDA / "partitura" / "sem_produto"
GABARITO_P1 = SAIDA / "partitura" / "p1" / "conferencia" / "itens.json"
GABARITO_SP = SAIDA / "partitura" / "diag" / "conferencia_sem_produto" / "itens.json"
SAIDA_JSON = PART_FRENTE_D / "amostra.json"

LIMIAR_FORTE = 5.0
TOTAL_PROPORCIONAL = 30
RESERVAS = 10


def _pesos(resumo: dict) -> dict[str, float]:
    """Extrapolação de cada canal do P0 (canal -> peso).

    Args:
        resumo: documento de ``p0/resumo.json``.

    Returns:
        Mapa canal -> extrapolação.
    """
    return {c["canal"]: float(c["extrapolacao"]) for c in resumo["canais"]}


def _excluidos() -> set[str]:
    """Vídeos que saem da população: gabaritos e piloto sem produto.

    Returns:
        Conjunto de ``canal/arquivo`` dos gabaritos, mais os 11 do piloto (pelo campo
        ``video`` do ``.partitura.json`` de cada pasta, quando existe).
    """
    excluidos: set[str] = set()
    for caminho in (GABARITO_P1, GABARITO_SP):
        itens = json.loads(caminho.read_text(encoding="utf-8"))["itens"]
        excluidos.update(item["video"] for item in itens)
    for pasta in sorted(PASTA_SEM_PRODUTO.iterdir()):
        for arquivo in pasta.glob("*.partitura.json"):
            video = json.loads(arquivo.read_text(encoding="utf-8")).get("video")
            if video:
                excluidos.add(video)
    return excluidos


def _populacao(canais: list[str], excluidos: set[str]) -> dict[str, list[str]]:
    """Vídeos de cada canal no acervo de hoje, sem os excluídos, em ordem alfabética.

    Args:
        canais: canais que entram no sorteio.
        excluidos: ``canal/arquivo`` a tirar.

    Returns:
        Mapa canal -> lista ordenada de ``canal/arquivo``.
    """
    raiz = acervo()
    populacao: dict[str, list[str]] = {}
    for canal in canais:
        pasta = raiz / canal
        arquivos = sorted(p.name for p in pasta.iterdir() if p.is_file())
        populacao[canal] = [
            f"{canal}/{nome}" for nome in arquivos if f"{canal}/{nome}" not in excluidos
        ]
    return populacao


def _proporcional(total: int, pesos: dict[str, float]) -> dict[str, int]:
    """Divide ``total`` em proporção aos pesos, pelo método do maior resto.

    Args:
        total: quantidade a dividir.
        pesos: peso de cada canal (zero ou negativo fica de fora).

    Returns:
        Mapa canal -> quantidade inteira, com soma igual a ``total``.
    """
    positivos = {c: p for c, p in pesos.items() if p > 0}
    soma = sum(positivos.values())
    cotas = {c: total * p / soma for c, p in positivos.items()}
    base = {c: int(q) for c, q in cotas.items()}
    faltam = total - sum(base.values())
    ordem = sorted(cotas, key=lambda c: (-(cotas[c] - base[c]), c))
    for c in ordem[:faltam]:
        base[c] += 1
    return base


def _alocar_com_capacidade(
    total: int, pesos: dict[str, float], capacidade: dict[str, int]
) -> dict[str, int]:
    """Divide ``total`` em proporção, sem passar da população de cada canal.

    O excedente de um canal sem vídeos suficientes vai para os outros, na mesma proporção.

    Args:
        total: quantidade a dividir.
        pesos: peso de cada canal.
        capacidade: vídeos disponíveis em cada canal.

    Returns:
        Mapa canal -> quantidade, com soma ``min(total, soma das capacidades)``.
    """
    cota = dict.fromkeys(pesos, 0)
    restante = total
    ativos = {c: p for c, p in pesos.items() if p > 0 and capacidade.get(c, 0) > 0}
    while restante > 0 and ativos:
        parcial = _proporcional(restante, ativos)
        cheios = []
        for c, q in parcial.items():
            dar = min(q, capacidade[c] - cota[c])
            cota[c] += dar
            restante -= dar
            if cota[c] >= capacidade[c]:
                cheios.append(c)
        ativos = {c: p for c, p in ativos.items() if c not in cheios}
    return cota


def sortear(resumo: dict) -> dict:
    """Sorteia a amostra e devolve o documento de ``amostra.json``.

    Args:
        resumo: documento de ``p0/resumo.json``.

    Returns:
        Documento com ``semente``, ``estratos``, ``escolhidos`` (por canal), ``reservas``,
        ``fora_do_p0`` e ``faltou`` (canais com menos vídeos que a cota).
    """
    semente = resumo["semente"]
    pesos = _pesos(resumo)
    fortes = [c for c, p in pesos.items() if p >= LIMIAR_FORTE]
    fracos = {c: p for c, p in pesos.items() if 0 < p < LIMIAR_FORTE}
    acervo_canais = sorted(p.name for p in acervo().iterdir() if p.is_dir())
    fora_do_p0 = [c for c in acervo_canais if c not in pesos]
    populacao = _populacao(fortes + list(fracos), _excluidos())
    capacidade = {c: len(populacao[c]) for c in populacao}
    cota = dict.fromkeys(fortes, 1)
    cota.update(_alocar_com_capacidade(TOTAL_PROPORCIONAL, fracos, capacidade))
    escolhidos: dict[str, list[str]] = {}
    reservas: dict[str, list[str]] = {}
    faltou: dict[str, int] = {}
    for canal in sorted(cota):
        pop = populacao[canal]
        ordem = random.Random(f"{semente}:{canal}").sample(pop, len(pop))
        n = min(cota[canal], len(ordem))
        if n < cota[canal]:
            faltou[canal] = cota[canal] - n
        escolhidos[canal] = ordem[:n]
        reservas[canal] = ordem[n : n + RESERVAS]
    return {
        "frente": "D1",
        "rodada": 3160,
        "semente": semente,
        "estratos": {
            "fortes": {c: cota[c] for c in fortes},
            "proporcionais": {c: cota[c] for c in sorted(fracos)},
            "pesos": pesos,
        },
        "populacao": {c: len(v) for c, v in populacao.items()},
        "escolhidos": escolhidos,
        "reservas": reservas,
        "total_escolhidos": sum(len(v) for v in escolhidos.values()),
        "fora_do_p0": fora_do_p0,
        "faltou": faltou,
    }


def main(argv: list[str] | None = None) -> int:
    """Sorteia e grava ``amostra.json`` na pasta da frente D.

    Args:
        argv: argumentos da linha de comando (não há opções).

    Returns:
        Zero em caso de sucesso.
    """
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    resumo = json.loads(RESUMO.read_text(encoding="utf-8"))
    documento = sortear(resumo)
    SAIDA_JSON.parent.mkdir(parents=True, exist_ok=True)
    SAIDA_JSON.write_text(
        json.dumps(documento, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"total escolhidos: {documento['total_escolhidos']}")
    print(f"fora do P0: {documento['fora_do_p0']}")
    print(f"faltou: {documento['faltou']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Linha de base por regra dos dedos (M3): só a tablatura, sem visão.

Cada variante decide os dedos a partir das notas do MVP (corda, casa, t_ini, tela e
coluna). Nada aqui olha imagem. A linha de base existe para que um método com visão
tenha o que bater.

Definições:

- **ataque**: as notas do MVP com a mesma tela, coluna e ``t_ini`` (uma batida de
  acorde);
- **posição P**: a menor casa maior que zero do conjunto de notas considerado;
- **dedo** = casa - P + 1; vale só se estiver em 1..4. Fora disso a regra devolve
  ``None`` (não decide), e a cobertura do avaliador mede essa parcela;
- corda solta (casa 0) é ``"0"`` em todas as variantes.

Variantes da esquerda (cada uma é um método):

- ``regra_casa``: dedo = casa, para casa de 1 a 4 (primeira posição);
- ``regra_posicao_ataque``: P = menor casa > 0 do próprio ataque;
- ``regra_posicao_janela_J``: P = menor casa > 0 entre TODAS as notas do MVP com
  ``|t_ini - t| <= J`` segundos. J em {0,5; 1; 2}, reportados todos; nenhum é
  escolhido pelo gabarito;
- ``regra_pestana_*``: a mesma base, mais a pestana. Se a menor casa > 0 do ataque é
  tocada por 2 ou mais notas, e entre elas há cordas não vizinhas (diferença de corda
  maior ou igual a 2), essas notas recebem ``"1"``. Há uma variante para cada base.

Direita (``regra_direita``): a mesma em todo arquivo, porque não depende da esquerda.
No ataque, a nota mais grave nas cordas 4 a 6 é ``"p"``; as demais notas por corda:
3 é ``"i"``, 2 é ``"m"``, 1 é ``"a"``. Nota de corda 4 a 6 que não é a mais grave fica
``None``, porque a regra não diz qual dedo é. Nota sozinha segue a mesma regra.

Uso::

    python -m tab.maos_regra_dedos
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .caminhos import GABARITO_DEDOS, MAOS_M3, MVP
from .maos_avaliar_dedos import (
    avaliar,
    carregar_json,
    gravar_avaliacao,
    montar_predicao,
    porcentagem,
)

#: Janelas de tempo medidas, em segundos. As três são reportadas.
JANELAS: tuple[float, ...] = (0.5, 1.0, 2.0)

#: Dedo da direita para as notas que não são a mais grave nas cordas 4 a 6.
DEDO_DIREITA_POR_CORDA: dict[int, str] = {3: "i", 2: "m", 1: "a"}

#: Folga para comparar ``|t - t'| <= J`` em ponto flutuante.
_EPS = 1e-9


def dedo_pela_casa(casa: int) -> str | None:
    """Dedo pela casa, na primeira posição (casa 1 a 4 é o dedo de mesmo número).

    Args:
        casa: casa da nota (0 é corda solta).

    Returns:
        ``"0"`` para corda solta, ``"1"`` a ``"4"`` para as casas 1 a 4, ``None`` fora
        disso.
    """
    if casa == 0:
        return "0"
    if 1 <= casa <= 4:
        return str(casa)
    return None


def posicao(casas: list[int]) -> int | None:
    """Posição da mão: a menor casa maior que zero.

    Args:
        casas: casas das notas do conjunto considerado.

    Returns:
        A menor casa > 0, ou ``None`` se todas são cordas soltas.
    """
    positivas = [c for c in casas if c > 0]
    return min(positivas) if positivas else None


def dedo_pela_posicao(casa: int, pos: int | None) -> str | None:
    """Dedo pela posição P da mão: ``casa - P + 1``, válido só entre 1 e 4.

    Args:
        casa: casa da nota (0 é corda solta).
        pos: posição P, ou ``None`` se não há casa > 0 no conjunto.

    Returns:
        ``"0"`` para corda solta, o dedo ``"1"`` a ``"4"``, ou ``None`` se não decide.
    """
    if casa == 0:
        return "0"
    if pos is None:
        return None
    dedo = casa - pos + 1
    return str(dedo) if 1 <= dedo <= 4 else None


def ataques(mvp: list[dict[str, Any]]) -> dict[tuple[Any, ...], list[int]]:
    """Agrupa as notas do MVP em ataques (mesma tela, coluna e ``t_ini``).

    Nota sem ``t_ini`` não tem ataque (não há como saber quais notas são da mesma
    batida), e fica de fora de :func:`ataques`.

    Args:
        mvp: lista ``notas`` do MVP.

    Returns:
        ``(tela, coluna, t_ini)`` -> índices das notas daquele ataque.
    """
    grupos: dict[tuple[Any, ...], list[int]] = {}
    for indice, nota in enumerate(mvp):
        if nota["t_ini"] is None:
            continue
        chave = (nota["tela"], nota["coluna"], nota["t_ini"])
        grupos.setdefault(chave, []).append(indice)
    return grupos


def _fora_de_ataque(mvp: list[dict[str, Any]], grupos: dict) -> list[int]:
    """Índices das notas que não pertencem a nenhum ataque (sem ``t_ini``).

    Args:
        mvp: lista ``notas`` do MVP.
        grupos: o retorno de :func:`ataques`.

    Returns:
        Os índices fora de todo ataque, em ordem.
    """
    dentro = {i for indices in grupos.values() for i in indices}
    return [i for i in range(len(mvp)) if i not in dentro]


def pestana_do_ataque(mvp: list[dict[str, Any]], indices: list[int]) -> set[int]:
    """Notas de pestana do ataque: as da menor casa > 0, se são 2+ em cordas distantes.

    Args:
        mvp: lista ``notas`` do MVP.
        indices: índices das notas do ataque.

    Returns:
        Os índices que recebem ``"1"``. Vazio se o ataque não tem pestana.
    """
    casas_positivas = [mvp[i]["casa"] for i in indices if mvp[i]["casa"] > 0]
    if not casas_positivas:
        return set()
    menor = min(casas_positivas)
    na_casa = [i for i in indices if mvp[i]["casa"] == menor]
    if len(na_casa) < 2:
        return set()
    cordas = [mvp[i]["corda"] for i in na_casa]
    nao_vizinhas = any(abs(a - b) >= 2 for a in cordas for b in cordas)
    return set(na_casa) if nao_vizinhas else set()


def esquerda_casa(mvp: list[dict[str, Any]]) -> dict[int, str | None]:
    """Regra ``regra_casa``: o dedo é a própria casa, para casa de 1 a 4.

    Args:
        mvp: lista ``notas`` do MVP.

    Returns:
        ``índice -> dedo`` da mão esquerda (``None`` = não decide).
    """
    return {i: dedo_pela_casa(n["casa"]) for i, n in enumerate(mvp)}


def esquerda_posicao_ataque(
    mvp: list[dict[str, Any]], pestana: bool
) -> dict[int, str | None]:
    """Regra ``regra_posicao_ataque``: P é a menor casa > 0 do próprio ataque.

    Args:
        mvp: lista ``notas`` do MVP.
        pestana: se ``True``, aplica a regra de pestana por cima.

    Returns:
        ``índice -> dedo`` da mão esquerda (``None`` = não decide).
    """
    grupos = ataques(mvp)
    saida: dict[int, str | None] = {}
    for indices in grupos.values():
        pos = posicao([mvp[i]["casa"] for i in indices])
        for i in indices:
            saida[i] = dedo_pela_posicao(mvp[i]["casa"], pos)
        if pestana:
            for i in pestana_do_ataque(mvp, indices):
                saida[i] = "1"
    for i in _fora_de_ataque(mvp, grupos):
        saida[i] = dedo_pela_posicao(mvp[i]["casa"], None)
    return saida


def esquerda_posicao_janela(
    mvp: list[dict[str, Any]], janela: float, pestana: bool
) -> dict[int, str | None]:
    """Regra ``regra_posicao_janela``: P vem das notas a até ``janela`` segundos.

    Args:
        mvp: lista ``notas`` do MVP.
        janela: meia-largura da janela de tempo, em segundos.
        pestana: se ``True``, aplica a regra de pestana (por ataque) por cima.

    Returns:
        ``índice -> dedo`` da mão esquerda (``None`` = não decide).
    """
    pestanas: set[int] = set()
    if pestana:
        for indices in ataques(mvp).values():
            pestanas |= pestana_do_ataque(mvp, indices)
    com_tempo = [m for m in mvp if m["t_ini"] is not None]
    saida: dict[int, str | None] = {}
    for i, nota in enumerate(mvp):
        t = nota["t_ini"]
        if t is None:
            saida[i] = dedo_pela_posicao(nota["casa"], None)
            continue
        vizinhas = [
            m["casa"] for m in com_tempo if abs(m["t_ini"] - t) <= janela + _EPS
        ]
        saida[i] = dedo_pela_posicao(nota["casa"], posicao(vizinhas))
    for i in pestanas:
        saida[i] = "1"
    return saida


def direita_do_ataque(
    mvp: list[dict[str, Any]], indices: list[int]
) -> dict[int, str | None]:
    """Dedo da direita das notas de um ataque (``regra_direita``).

    Args:
        mvp: lista ``notas`` do MVP.
        indices: índices das notas do ataque.

    Returns:
        ``índice -> dedo`` da mão direita (``None`` = a regra não diz).
    """
    graves = [i for i in indices if 4 <= mvp[i]["corda"] <= 6]
    principal = max(graves, key=lambda i: mvp[i]["corda"]) if graves else None
    saida: dict[int, str | None] = {}
    for i in indices:
        if i == principal:
            saida[i] = "p"
        else:
            saida[i] = DEDO_DIREITA_POR_CORDA.get(mvp[i]["corda"])
    return saida


def direita(mvp: list[dict[str, Any]]) -> dict[int, str | None]:
    """Dedo da direita de todas as notas do MVP.

    Args:
        mvp: lista ``notas`` do MVP.

    Returns:
        ``índice -> dedo`` da mão direita para cada nota.
    """
    grupos = ataques(mvp)
    saida: dict[int, str | None] = {}
    for indices in grupos.values():
        saida.update(direita_do_ataque(mvp, indices))
    for i in _fora_de_ataque(mvp, grupos):
        saida.update(direita_do_ataque(mvp, [i]))
    return saida


def esquerdas_por_metodo(
    mvp: list[dict[str, Any]],
) -> dict[str, dict[int, str | None]]:
    """Todas as variantes da esquerda, cada uma com o nome do método.

    Args:
        mvp: lista ``notas`` do MVP.

    Returns:
        ``nome do método`` -> ``índice -> dedo``.
    """
    resultado = {
        "regra_casa": esquerda_casa(mvp),
        "regra_posicao_ataque": esquerda_posicao_ataque(mvp, pestana=False),
        "regra_pestana_ataque": esquerda_posicao_ataque(mvp, pestana=True),
    }
    for janela in JANELAS:
        sufixo = f"{janela:g}".replace(".", "_")
        resultado[f"regra_posicao_janela_{sufixo}"] = esquerda_posicao_janela(
            mvp, janela, pestana=False
        )
        resultado[f"regra_pestana_janela_{sufixo}"] = esquerda_posicao_janela(
            mvp, janela, pestana=True
        )
    return resultado


def conferir_indices(gabarito: dict[str, Any], mvp: list[dict[str, Any]]) -> list[str]:
    """Ids das notas do gabarito cujo ``indice_mvp`` não bate com o MVP.

    Compara corda, casa e ``t_ini``. Uma divergência significa índice trocado, e o
    avaliador daria nota a outra nota.

    Args:
        gabarito: o JSON do gabarito (formato 3).
        mvp: lista ``notas`` do MVP.

    Returns:
        Os ids divergentes. Lista vazia quando todos os índices batem.
    """
    divergentes = []
    for nota in gabarito["notas"]:
        indice = nota["indice_mvp"]
        if not 0 <= indice < len(mvp):
            divergentes.append(nota["id"])
            continue
        alvo = mvp[indice]
        bate = (
            alvo["corda"] == nota["corda"]
            and alvo["casa"] == nota["casa"]
            and alvo["t_ini"] is not None
            and abs(alvo["t_ini"] - nota["t_ini"]) < 1e-6
        )
        if not bate:
            divergentes.append(nota["id"])
    return divergentes


def linha_comparativa(rel: dict[str, Any]) -> str:
    """Uma linha da tabela comparativa, com as métricas de um método.

    Args:
        rel: o dicionário devolvido por :func:`avaliar`.

    Returns:
        Linha de Markdown com o método, as acurácias e a cobertura da esquerda, e a
        acurácia da direita.
    """
    esq = rel["esquerda"]
    dir_ = rel["direita"]
    return (
        f"| {rel['metodo']} | {esq['acertos']}/{esq['n_validas']} "
        f"({porcentagem(esq['acerto_total'])}) | {esq['acertos_pisadas']}/"
        f"{esq['n_pisadas']} ({porcentagem(esq['acerto_pisadas'])}) | "
        f"{porcentagem(esq['cobertura'])} | {dir_['acertos']}/{dir_['n_validas']} "
        f"({porcentagem(dir_['acerto_total'])}) |"
    )


def main() -> None:
    """Grava a predição de cada variante, avalia e imprime a tabela comparativa."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--gabarito", type=Path, default=GABARITO_DEDOS)
    parser.add_argument("--mvp", type=Path, default=MVP)
    parser.add_argument("--pasta", type=Path, default=MAOS_M3)
    args = parser.parse_args()
    mvp = carregar_json(args.mvp)["notas"]
    gabarito = carregar_json(args.gabarito)
    divergentes = conferir_indices(gabarito, mvp)
    if divergentes:
        print(f"ATENÇÃO: índice_mvp não bate com o MVP em {divergentes}")
    direita_ = direita(mvp)
    args.pasta.mkdir(parents=True, exist_ok=True)
    linhas = [
        "| método | esq. acerto total | esq. acerto nas pisadas | esq. cobertura "
        "| dir. acerto (gabarito parcial) |",
        "|---|---|---|---|---|",
    ]
    for metodo, esq in esquerdas_por_metodo(mvp).items():
        decisoes = {i: (esq[i], direita_[i]) for i in range(len(mvp))}
        pred = montar_predicao(metodo, decisoes)
        (args.pasta / f"pred_{metodo}.json").write_text(
            json.dumps(pred, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        rel = avaliar(gabarito, pred)
        gravar_avaliacao(rel, args.pasta)
        linhas.append(linha_comparativa(rel))
    print("\n".join(linhas))
    print(f"\nPredições e avaliações em {args.pasta}")


if __name__ == "__main__":
    main()

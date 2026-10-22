"""Mede as variantes da regra da mão direita contra o gabarito do dono (M5).

Para cada variante de ``tab.maos_regra_direita.atribuir_dedos_direita`` (uma grade de
janela do polegar, janela da sequência e alternância m-a), roda a regra nos compassos
confirmados do gabarito e conta quantas notas o palpite acerta.

A nota com dono ``l`` (ligada, sem ataque da direita) entra na regra, porque ela está
no compasso e pode mudar a sequência, mas fica FORA da conta.

Saídas: tabela ordenada por acerto no terminal e
``data/saida/maos/m5/regra_v2_medicao.json``, com a grade inteira, a melhor variante,
a variante atual, a validação deixando um vídeo de fora e a matriz de confusão da
melhor.

Uso::

    python -m tab.maos_regra_direita_medir
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any

from tab.comum.caminhos import GABARITO_PADROES, MAOS_M5_REGRA_V2
from tab.maos.regra_direita import (
    V1_ALTERNAR_MA,
    V1_JANELA_POLEGAR_S,
    V1_JANELA_SEQUENCIA_S,
    atribuir_dedos_direita,
)

#: Grade de ``janela_polegar_s``.
JANELAS_POLEGAR_S: tuple[float, ...] = (0.25, 0.5, 0.7, 1.0)

#: Grade de ``janela_sequencia_s``.
JANELAS_SEQUENCIA_S: tuple[float, ...] = (0.6, 0.8, 1.0, 1.2)

#: Grade de ``alternar_ma``.
ALTERNAR_MA: tuple[bool, ...] = (False, True)

#: A regra v1 (a que o dono viu nos ímpares), como referência de comparação. Não é
#: mais o default de produção, que é a v2.
VARIANTE_ATUAL: dict[str, Any] = {
    "janela_polegar_s": V1_JANELA_POLEGAR_S,
    "janela_sequencia_s": V1_JANELA_SEQUENCIA_S,
    "alternar_ma": V1_ALTERNAR_MA,
}

#: Dono que marca nota ligada (sem ataque da direita): fica fora da conta.
DONO_LIGADA = "l"

#: Dedos da mão direita que entram na matriz de confusão.
DEDOS_DIREITA: tuple[str, ...] = ("p", "i", "m", "a")


def grade_variantes() -> list[dict[str, Any]]:
    """Todas as combinações da grade (4 × 4 × 2 = 32 variantes).

    Returns:
        Lista de dicionários com os argumentos de ``atribuir_dedos_direita``, na ordem
        da grade (polegar, depois sequência, depois alternância).
    """
    return [
        {"janela_polegar_s": jp, "janela_sequencia_s": js, "alternar_ma": am}
        for jp, js, am in itertools.product(
            JANELAS_POLEGAR_S, JANELAS_SEQUENCIA_S, ALTERNAR_MA
        )
    ]


def rotulo_variante(variante: dict[str, Any]) -> str:
    """Nome curto de uma variante, para tabela e JSON.

    Args:
        variante: argumentos de ``atribuir_dedos_direita``.

    Returns:
        Texto no formato ``polegar=0.25 seq=0.60 m-a=não``.
    """
    alternancia = "sim" if variante["alternar_ma"] else "não"
    return (
        f"polegar={variante['janela_polegar_s']:.2f} "
        f"seq={variante['janela_sequencia_s']:.2f} m-a={alternancia}"
    )


def carregar_confirmados(caminho: Path) -> list[dict[str, Any]]:
    """Itens do gabarito que o dono confirmou.

    Args:
        caminho: arquivo do gabarito de padrões (formato 2).

    Returns:
        Itens com ``confirmado: true``, na ordem do arquivo.
    """
    gabarito = json.loads(caminho.read_text(encoding="utf-8"))
    return [
        item for item in gabarito["itens"].values() if item.get("confirmado") is True
    ]


def notas_do_compasso(dedos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Notas do compasso (corda, casa, tempo) reconstruídas do gabarito.

    Args:
        dedos: entradas ``dedos`` de um item do gabarito.

    Returns:
        Uma nota por entrada, na mesma ordem, só com ``corda``, ``casa`` e ``t_ini``.
    """
    return [
        {"corda": d["corda"], "casa": d["casa"], "t_ini": d["t_ini"]} for d in dedos
    ]


def pares_do_compasso(
    dedos: list[dict[str, Any]], variante: dict[str, Any]
) -> list[tuple[str, str]]:
    """Par ``(dono, palpite)`` de cada nota do compasso, sem as ligadas.

    A regra ordena as notas por ``t_ini`` de forma estável. Aqui a mesma ordem é
    refeita sobre a lista do gabarito, para cada palpite casar com a nota de origem.

    Args:
        dedos: entradas ``dedos`` de um item do gabarito.
        variante: argumentos de ``atribuir_dedos_direita``.

    Returns:
        Lista de ``(dono, palpite)`` na ordem de ``t_ini``, sem as notas com dono ``l``.
    """
    saida = atribuir_dedos_direita(notas_do_compasso(dedos), **variante)
    ordem = sorted(range(len(dedos)), key=lambda k: dedos[k]["t_ini"])
    pares: list[tuple[str, str]] = []
    for k, nota in zip(ordem, saida, strict=True):
        dono = dedos[k]["dono"]
        if dono != DONO_LIGADA:
            pares.append((dono, nota["dedo"]))
    return pares


def matriz_confusao(pares: list[tuple[str, str]]) -> dict[str, dict[str, int]]:
    """Matriz 4 × 4 de confusão: linha é o dono, coluna é o palpite.

    Args:
        pares: pares ``(dono, palpite)``, sem notas ligadas.

    Returns:
        Dicionário ``dono -> palpite -> contagem``, com p, i, m, a nas duas dimensões.

    Raises:
        ValueError: se algum dono não for p, i, m ou a.
    """
    matriz = {d: dict.fromkeys(DEDOS_DIREITA, 0) for d in DEDOS_DIREITA}
    for dono, palpite in pares:
        if dono not in matriz:
            raise ValueError(f"dono fora de p/i/m/a: {dono!r}")
        matriz[dono][palpite] += 1
    return matriz


def avaliar_variante(
    itens: list[dict[str, Any]], variante: dict[str, Any]
) -> dict[str, Any]:
    """Acertos de uma variante sobre os itens confirmados, geral e por vídeo.

    Args:
        itens: itens confirmados do gabarito (cada um com ``video`` e ``dedos``).
        variante: argumentos de ``atribuir_dedos_direita``.

    Returns:
        Dicionário com ``variante``, ``rotulo``, ``acertos`` e ``total`` (sem as
        ligadas), ``por_video`` (``acertos`` e ``total`` de cada vídeo), ``ligadas``
        (notas com dono ``l``, fora da conta) e ``matriz`` de confusão.
    """
    por_video: dict[str, dict[str, int]] = {}
    pares: list[tuple[str, str]] = []
    ligadas = 0
    for item in itens:
        contagem = por_video.setdefault(item["video"], {"acertos": 0, "total": 0})
        ligadas += sum(1 for d in item["dedos"] if d["dono"] == DONO_LIGADA)
        for dono, palpite in pares_do_compasso(item["dedos"], variante):
            contagem["total"] += 1
            contagem["acertos"] += int(dono == palpite)
            pares.append((dono, palpite))
    return {
        "variante": variante,
        "rotulo": rotulo_variante(variante),
        "acertos": sum(c["acertos"] for c in por_video.values()),
        "total": sum(c["total"] for c in por_video.values()),
        "por_video": por_video,
        "ligadas": ligadas,
        "matriz": matriz_confusao(pares),
    }


def validar_deixando_video_de_fora(resultados: list[dict[str, Any]]) -> dict[str, Any]:
    """Validação: escolhe a variante nos outros vídeos e mede no que ficou de fora.

    Para cada vídeo V, a variante escolhida é a de mais acertos nos demais vídeos (em
    empate, a primeira da grade). Mede-se essa variante só em V, e somam-se os quatro
    resultados fora da amostra.

    Args:
        resultados: saídas de ``avaliar_variante``, uma por variante, na ordem da grade.

    Returns:
        Dicionário com ``escolhas`` (por vídeo: variante, acertos e total) e os somatórios
        ``acertos`` e ``total`` fora da amostra.
    """
    videos = sorted({v for r in resultados for v in r["por_video"]})
    escolhas: dict[str, dict[str, Any]] = {}
    acertos_fora = 0
    total_fora = 0
    for video in videos:
        pontuacao = [
            sum(r["por_video"][v]["acertos"] for v in videos if v != video)
            for r in resultados
        ]
        melhor = max(range(len(resultados)), key=lambda k: (pontuacao[k], -k))
        medido = resultados[melhor]["por_video"][video]
        escolhas[video] = {
            "variante": resultados[melhor]["rotulo"],
            "acertos": medido["acertos"],
            "total": medido["total"],
        }
        acertos_fora += medido["acertos"]
        total_fora += medido["total"]
    return {"escolhas": escolhas, "acertos": acertos_fora, "total": total_fora}


def tabela_texto(resultados: list[dict[str, Any]], videos: list[str]) -> str:
    """Tabela das variantes, ordenada por acerto (empate: ordem da grade).

    Args:
        resultados: saídas de ``avaliar_variante``, na ordem da grade.
        videos: vídeos na ordem das colunas V1, V2, ...

    Returns:
        Texto com uma linha por variante.
    """
    ordem = sorted(range(len(resultados)), key=lambda k: (-resultados[k]["acertos"], k))
    cabecalho = (
        f"{'#':>3}  {'variante':<36} {'acertos/total':>14} {'taxa':>6}  "
        + "  ".join(f"{'V' + str(n + 1):>7}" for n in range(len(videos)))
    )
    linhas = [cabecalho, "-" * len(cabecalho)]
    for posicao, k in enumerate(ordem, start=1):
        r = resultados[k]
        taxa = r["acertos"] / r["total"] if r["total"] else 0.0
        por = "  ".join(
            f"{r['por_video'][v]['acertos']:>3}/{r['por_video'][v]['total']:<3}"
            for v in videos
        )
        linhas.append(
            f"{posicao:>3}  {r['rotulo']:<36} "
            f"{r['acertos']:>6}/{r['total']:<7} {taxa:>6.3f}  {por}"
        )
    return "\n".join(linhas)


def main() -> None:
    """Mede a grade, grava o JSON e imprime a tabela, a validação e a matriz."""
    itens = carregar_confirmados(GABARITO_PADROES)
    resultados = [avaliar_variante(itens, v) for v in grade_variantes()]
    ordem = sorted(range(len(resultados)), key=lambda k: (-resultados[k]["acertos"], k))
    melhor = resultados[ordem[0]]
    atual = avaliar_variante(itens, VARIANTE_ATUAL)
    validacao = validar_deixando_video_de_fora(resultados)
    videos = sorted(melhor["por_video"])

    relatorio = {
        "gabarito": str(GABARITO_PADROES),
        "itens_confirmados": len(itens),
        "ligadas_fora_da_conta": atual["ligadas"],
        "notas_pontuadas": melhor["total"],
        "videos": videos,
        "melhor": melhor["rotulo"],
        "variante_atual": atual,
        "grade": [resultados[k] for k in ordem],
        "validacao_sem_video": validacao,
    }
    MAOS_M5_REGRA_V2.parent.mkdir(parents=True, exist_ok=True)
    MAOS_M5_REGRA_V2.write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"gabarito: {len(itens)} compassos confirmados")
    print(f"notas ligadas (fora da conta): {atual['ligadas']}")
    for n, video in enumerate(videos, start=1):
        print(f"  V{n} = {video}")
    print()
    print(tabela_texto(resultados, videos))
    print()
    print(f"variante atual ({atual['rotulo']}): {atual['acertos']}/{atual['total']}")
    print(
        f"validação deixando um vídeo de fora: {validacao['acertos']}/"
        f"{validacao['total']} "
        f"({validacao['acertos'] / validacao['total']:.3f})"
    )
    for n, video in enumerate(videos, start=1):
        escolha = validacao["escolhas"][video]
        print(
            f"  V{n}: escolheu {escolha['variante']}, "
            f"{escolha['acertos']}/{escolha['total']}"
        )
    print()
    print(f"matriz de confusão da melhor ({melhor['rotulo']}), linha = dono:")
    print("        " + "  ".join(f"{p:>4}" for p in DEDOS_DIREITA))
    for dono in DEDOS_DIREITA:
        linha = melhor["matriz"][dono]
        print(f"  {dono:>4}  " + "  ".join(f"{linha[p]:>4}" for p in DEDOS_DIREITA))
    print()
    print(f"JSON: {MAOS_M5_REGRA_V2}")


if __name__ == "__main__":
    main()

"""Braço "música + imagem" e as medições da rodada 1007 (M3c).

Três passos, todos sobre o MVP do M3 (``sky guitar/retrato brasileiro``):

1. ``--gerar-mediana`` (precisa do acervo; roda no container com o acervo montado):
   mediana de ``N_QUADROS`` quadros espalhados pela cena. A mão se move e a mediana a
   apaga; sobra o braço e a tablatura.
2. Calibração: H pela música, estabilizada (consenso sobre 3 conjuntos de 10 sementes;
   refino por erro de reprojeção) e "música + imagem" (H ajustada aos cruzamentos
   corda x traste achados na mediana retificada pela H estabilizada). Cada uma com e
   sem os instantes do gabarito de dedos.
3. Medições: (a) contra a calibração à mão ``braco.json``; (b) contra o gabarito do
   dono no quadro q02 do braço; (c) dedo, pelo avaliador oficial (feito pelo chamador
   com ``python -m tab.maos_avaliar_dedos``); (d) imagem de conferência.

Uso::

    host-spawn ... podman run ... python -m tab.maos_medicoes_braco --gerar-mediana
    python -m tab.maos_medicoes_braco
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .caminhos import GABARITO_BRACO, GABARITO_DEDOS, MAOS_M3, MAOS_M3B, MVP, acervo
from .maos_avaliar_dedos import carregar_json, montar_predicao
from .maos_calibrar_por_notas import (
    BRACO_FIXO,
    N_TRASTES,
    PONTAS,
    PONTAS_ANT,
    PONTAS_DEP,
    S_TRASTES,
    SEMENTE_OFICIAL,
    VIDEO,
    _decidir_gabarito,
    aplicar_homografia,
    avaliar,
    comparar_com_fixa,
    diferenca_entre_h,
    estatisticas,
    mapa_de_maos,
    montar_conjunto,
    quadro_bgr,
    s_traste,
    v_corda,
)
from .maos_linhas_braco import (
    FATOR_RUIDO,
    achar_linhas,
    mapa_retificacao,
    perfil_linhas,
    ruido_do_perfil,
)
from .maos_refinar_braco import ajustar_pontos, consenso

#: Pasta da rodada (visível no host).
PASTA = MAOS_M3.parent / "m3c"

#: Mediana do braço e o que entrou nela.
MEDIANA_PNG = PASTA / "mediana_braco.png"
MEDIANA_JSON = PASTA / "mediana_braco.json"

#: Saídas da calibração e das medições.
CALIBRACAO_V2 = PASTA / "calibracao_v2.json"
CALIBRACAO_V2_JPG = PASTA / "calibracao_v2.jpg"

#: Quadros da mediana, espalhados pelos instantes das notas pisadas.
N_QUADROS = 30

#: Quadros da mediana de uma cena do quadro do dono (rodada 1009).
N_QUADROS_CENA = 15

#: Pasta das cenas (``<quadro>_cena.json``, com as notas) e das medianas por quadro.
PASTA_CENAS = MAOS_M3.parent / "m3d"

#: Conjuntos de sementes (cada um com 10) para medir a estabilidade.
SEMENTES_POR_CONJUNTO = 10
CONJUNTOS_DE_SEMENTES = tuple(
    tuple(SEMENTE_OFICIAL + 100 * k + i for i in range(SEMENTES_POR_CONJUNTO))
    for k in range(3)
)

#: Retificação: pixels por unidade de u e de v, e a janela do retângulo.
KU = 2000.0
KV = 800.0
U0 = -0.03
U1 = float(S_TRASTES[N_TRASTES]) + 0.03
V0 = -0.2
V1 = 1.2

#: Janela de busca: fração do espaçamento das cordas e da largura da casa.
FRACAO_CORDA = 0.4
FRACAO_TRASTE = 0.25

#: Larguras do realce de fundo, em pixels da retificada.
JANELA_CORDA = 31
JANELA_TRASTE = 11

#: Margem, em unidades de v, além da corda 1 e da 6 para procurar os trastes.
MARGEM_V = 0.12

#: Quadro do gabarito do dono usado na medição (b).
QUADRO_DONO = "q02"

#: Quadro de conferência: cor (BGR) da grade música + imagem e do dono.
VERMELHO = (0, 0, 255)
VERDE = (0, 255, 0)


def instantes_espalhados(instantes: list[float], n: int) -> list[float]:
    """``n`` instantes igualmente espaçados numa lista ordenada.

    Args:
        instantes: instantes distintos, em ordem crescente.
        n: quantos instantes escolher.

    Returns:
        Os instantes escolhidos, em ordem crescente.
    """
    indices = np.linspace(0, len(instantes) - 1, min(n, len(instantes))).round()
    return [instantes[int(i)] for i in np.unique(indices.astype(int))]


def mediana_de_quadros(quadros: list[np.ndarray]) -> np.ndarray:
    """Mediana, pixel a pixel, de uma lista de quadros BGR.

    Calculada em faixas de linhas para não estourar a memória.

    Args:
        quadros: quadros ``uint8`` de mesma forma.

    Returns:
        Quadro ``uint8`` com a mediana.

    Raises:
        ValueError: se a lista está vazia.
    """
    if not quadros:
        raise ValueError("nenhum quadro para a mediana")
    pilha = np.stack(quadros)
    saida = np.empty(pilha.shape[1:], dtype=np.uint8)
    faixa = 60
    for y in range(0, pilha.shape[1], faixa):
        bloco = np.median(pilha[:, y : y + faixa].astype(np.float32), axis=0)
        saida[y : y + faixa] = np.round(bloco).astype(np.uint8)
    return saida


def gerar_mediana(
    video: Path, instantes: list[float], destino: Path = MEDIANA_PNG
) -> Path:
    """Lê os quadros, faz a mediana e grava a imagem e a lista de instantes.

    A lista vai junto, em ``destino`` com extensão ``.json``.

    Args:
        video: vídeo (precisa do acervo montado).
        instantes: instantes dos quadros.
        destino: PNG de saída (padrão: a mediana do MVP, na pasta m3c).

    Returns:
        O caminho do PNG gravado.
    """
    quadros = [quadro_bgr(video, t) for t in instantes]
    destino.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(destino), mediana_de_quadros(quadros))
    destino.with_suffix(".json").write_text(
        json.dumps(
            {"video": str(video), "instantes": instantes, "n": len(instantes)},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"mediana de {len(instantes)} quadros: {destino}")
    return destino


def instantes_pisados(notas: list[dict[str, Any]]) -> list[float]:
    """Instantes distintos, em ordem, das notas pisadas com tempo.

    Args:
        notas: lista ``notas`` de uma cena (com ``t_ini`` e ``casa``).

    Returns:
        Os ``t_ini`` (3 casas) das notas com casa > 0, sem repetição, em ordem.
    """
    return sorted(
        {
            round(float(n["t_ini"]), 3)
            for n in notas
            if n.get("t_ini") is not None and n["casa"] > 0
        }
    )


def gerar_mediana_da_cena(quadro: str) -> Path:
    """Mediana de ``N_QUADROS_CENA`` quadros da cena do quadro do dono.

    O vídeo vem do índice dos quadros (``m3b/indice.json``) e os instantes das notas
    pisadas da cena (``m3d/<quadro>_cena.json``). Grava ``m3d/<quadro>/mediana.png``.

    Args:
        quadro: id do quadro no gabarito (``q16``, ``q21``...).

    Returns:
        O caminho do PNG gravado.

    Raises:
        ValueError: se o quadro não está no índice dos quadros.
    """
    indice = carregar_json(MAOS_M3B / "indice.json")
    entradas = [q for q in indice["quadros"] if q["id"] == quadro]
    if not entradas:
        raise ValueError(f"quadro {quadro} não está no índice dos quadros")
    video = acervo() / entradas[0]["arquivo"]
    notas = carregar_json(PASTA_CENAS / f"{quadro}_cena.json")["notas"]
    instantes = instantes_espalhados(instantes_pisados(notas), N_QUADROS_CENA)
    return gerar_mediana(video, instantes, PASTA_CENAS / quadro / "mediana.png")


def retificar(mediana: np.ndarray, H: np.ndarray) -> np.ndarray:
    """Retifica o braço pela H: imagem em tons de cinza, ``(v, u)`` com escala KU/KV.

    Args:
        mediana: quadro BGR da mediana.
        H: homografia que leva ``(u, v)`` para pixels.

    Returns:
        Imagem ``float32`` retificada.
    """
    cinza = cv2.cvtColor(mediana, cv2.COLOR_BGR2GRAY).astype(np.float32)
    M = mapa_retificacao(H, KU, KV, U0, V0)
    tamanho = (round((U1 - U0) * KU), round((V1 - V0) * KV))
    return cv2.warpPerspective(cinza, M, tamanho, flags=cv2.INTER_LINEAR)


def _faixa(inicio: float, fim: float, limite: int) -> tuple[int, int]:
    """Faixa de pixels ``[inicio, fim)`` limitada a ``[0, limite)``.

    Args:
        inicio: início, em pixels.
        fim: fim, em pixels.
        limite: tamanho do eixo.

    Returns:
        ``(inicio, fim)`` inteiros, limitados.
    """
    return max(int(inicio), 0), min(int(fim), limite)


def achar_grade(retificada: np.ndarray) -> dict[str, list[dict[str, Any]]]:
    """Procura cada corda (1 a 6) e cada traste (0 = nut, 1 a 14) na retificada.

    Cordas: linhas claras, na janela de ``FRACAO_CORDA`` do espaçamento em volta da
    posição da música. Trastes e nut: linhas em qualquer tom, na janela de
    ``FRACAO_TRASTE`` da largura da casa. Mínimo: ``FATOR_RUIDO`` vezes o ruído do perfil.

    Args:
        retificada: imagem retificada (:func:`retificar`).

    Returns:
        ``cordas`` (6 entradas) e ``trastes`` (15 entradas, do nut para cima), com o
        que :func:`tab.maos_linhas_braco.achar_linhas` devolve, em pixels da retificada.
    """
    altura, largura = retificada.shape[:2]
    espaco_v = (v_corda(2) - v_corda(1)) * KV
    previstos_c = [(v_corda(j) - V0) * KV for j in range(1, 7)]
    x_ini, x_fim = _faixa(
        (S_TRASTES[1] - U0) * KU, (S_TRASTES[N_TRASTES] - U0) * KU, largura
    )
    perfil_c = perfil_linhas(retificada, "horizontal", (x_ini, x_fim), JANELA_CORDA)
    minimo_c = FATOR_RUIDO * ruido_do_perfil(perfil_c)
    cordas = achar_linhas(
        perfil_c,
        previstos_c,
        [FRACAO_CORDA * espaco_v] * 6,
        "claro",
        minimo_c,
    )

    y_ini, y_fim = _faixa(
        (v_corda(1) - MARGEM_V - V0) * KV,
        (v_corda(6) + MARGEM_V - V0) * KV,
        altura,
    )
    perfil_t = perfil_linhas(retificada, "vertical", (y_ini, y_fim), JANELA_TRASTE)
    minimo_t = FATOR_RUIDO * ruido_do_perfil(perfil_t)
    previstos_t = [(float(S_TRASTES[n]) - U0) * KU for n in range(N_TRASTES + 1)]
    meias_t = [
        FRACAO_TRASTE * (float(S_TRASTES[max(n, 1)] - S_TRASTES[max(n - 1, 0)])) * KU
        for n in range(N_TRASTES + 1)
    ]
    trastes = achar_linhas(perfil_t, previstos_t, meias_t, "qualquer", minimo_t)
    return {"cordas": cordas, "trastes": trastes}


def pares_de_ajuste(
    H: np.ndarray, grade: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    """Pares (numeração da música -> onde o cruzamento está na imagem).

    Para cada corda ``j`` e traste ``n``: a origem é ``(u_n, v_j)`` nominal (o traste
    real, não a casa de 70 %); o destino é ``H(u*, v*)``, com ``(u*, v*)`` o cruzamento
    achado na retificada (o da música se a corda ou o traste não foi achado).

    Args:
        H: homografia que serviu para retificar.
        grade: saída de :func:`achar_grade`.

    Returns:
        ``origem`` e ``destino`` ``(90, 2)``, e ``achados`` (quantas cordas e trastes
        foram achados, e quantos cruzamentos usam a posição da música).
    """
    origem, cruzamentos = [], []
    for j in range(1, 7):
        corda = grade["cordas"][j - 1]
        v_nom = v_corda(j)
        v_star = V0 + corda["posicao"] / KV if corda["achado"] else v_nom
        for n in range(N_TRASTES + 1):
            traste = grade["trastes"][n]
            u_nom = float(S_TRASTES[n])
            u_star = U0 + traste["posicao"] / KU if traste["achado"] else u_nom
            origem.append((u_nom, v_nom))
            cruzamentos.append((u_star, v_star))
    origem_arr = np.asarray(origem)
    destino_arr = aplicar_homografia(H, np.asarray(cruzamentos))
    return {
        "origem": origem_arr,
        "destino": destino_arr,
        "achados": {
            "cordas": int(sum(c["achado"] for c in grade["cordas"])),
            "trastes": int(sum(t["achado"] for t in grade["trastes"])),
            "cruzamentos_com_musica": int(
                sum(
                    1
                    for c in grade["cordas"]
                    for t in grade["trastes"]
                    if not (c["achado"] and t["achado"])
                )
            ),
        },
    }


def calibrar_com_imagem(
    H: np.ndarray, mediana: np.ndarray
) -> tuple[np.ndarray, dict[str, Any], dict[str, Any]]:
    """H "música + imagem": retifica pela H, acha a grade e ajusta H aos cruzamentos.

    Args:
        H: homografia da música (estabilizada).
        mediana: quadro BGR da mediana.

    Returns:
        ``(H_imagem, grade, resumo)``. ``resumo`` traz a contagem de achados e o
        erro, em px, do ajuste (mediana e máximo dos cruzamentos).
    """
    retificada = retificar(mediana, H)
    grade = achar_grade(retificada)
    pares = pares_de_ajuste(H, grade)
    H_img = ajustar_pontos(H, pares["origem"], pares["destino"])
    residuo = np.linalg.norm(
        aplicar_homografia(H_img, pares["origem"]) - pares["destino"], axis=1
    )
    resumo = {
        **pares["achados"],
        "residuo_ajuste_px": estatisticas(residuo.tolist()),
        "diferenca_H_imagem_vs_musica": diferenca_entre_h(H, H_img),
    }
    return H_img, grade, resumo


def reta_de_h_corda(H: np.ndarray, j: int) -> tuple[np.ndarray, np.ndarray]:
    """Duas pontas (em px) da reta prevista pela H para a corda ``j``.

    Args:
        H: homografia.
        j: número da corda (1 a 6).

    Returns:
        ``(A, B)``: pontos da reta no nut e no fim do braço.
    """
    v = v_corda(j)
    pa, pb = aplicar_homografia(H, np.array([(0.0, v), (0.5, v)]))
    return pa, pb


def reta_de_h_traste(H: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Duas pontas (em px) da reta prevista pela H para o traste ``n`` (0 é o nut).

    Args:
        H: homografia.
        n: número do traste (qualquer, pela fórmula :func:`s_traste`).

    Returns:
        ``(A, B)``: pontos da reta em ``v = 0`` e ``v = 1``.
    """
    u = float(s_traste(n))
    pa, pb = aplicar_homografia(H, np.array([(u, 0.0), (u, 1.0)]))
    return pa, pb


def distancia_a_reta(P: np.ndarray, A: np.ndarray, B: np.ndarray) -> float:
    """Distância perpendicular, em px, de ``P`` à reta por ``A`` e ``B``.

    Args:
        P: ponto ``(2,)``.
        A: ponto da reta.
        B: outro ponto da reta.

    Returns:
        A distância ``>= 0``.
    """
    d = B - A
    return float(abs(d[0] * (P[1] - A[1]) - d[1] * (P[0] - A[0])) / np.linalg.norm(d))


def y_da_reta(A: np.ndarray, B: np.ndarray, x: float) -> float:
    """Altura, em px, da reta por ``A`` e ``B`` na coluna ``x``.

    Args:
        A: ponto da reta.
        B: outro ponto da reta (com ``B[0] != A[0]``).
        x: coluna.

    Returns:
        ``y`` da reta em ``x``.
    """
    return float(A[1] + (B[1] - A[1]) * (x - A[0]) / (B[0] - A[0]))


def retas_da_calibracao_fixa(
    braco: dict[str, Any],
) -> dict[str, dict[Any, tuple[np.ndarray, np.ndarray]]]:
    """Retas (duas pontas) das cordas, trastes e nut da calibração à mão.

    Args:
        braco: conteúdo de ``braco.json``.

    Returns:
        ``cordas`` (corda -> reta, pela equação ``y = a + b x``), ``trastes`` (traste ->
        reta vertical em ``x``) e a largura de cada casa como ``casas``.
    """
    cordas = {}
    for c in braco["cordas"]:
        a, b = c["a"], c["b"]
        cordas[c["corda"]] = (
            np.array([0.0, a]),
            np.array([1920.0, a + b * 1920.0]),
        )
    trastes = {}
    xs = {int(k): float(v["x"]) for k, v in braco["trastes"].items()}
    for n, x in xs.items():
        trastes[n] = (np.array([x, 0.0]), np.array([x, 1000.0]))
    return {"cordas": cordas, "trastes": trastes, "x": xs}


def retas_da_calibracao(
    H: np.ndarray, n_trastes: int = N_TRASTES
) -> dict[str, dict[Any, tuple[np.ndarray, np.ndarray]]]:
    """Retas das cordas, trastes e nut previstas por uma H.

    Args:
        H: homografia.
        n_trastes: quantos trastes além do nut (1 a ``n_trastes``).

    Returns:
        ``cordas`` (corda -> reta), ``trastes`` (traste 0 a ``n_trastes`` -> reta).
    """
    return {
        "cordas": {j: reta_de_h_corda(H, j) for j in range(1, 7)},
        "trastes": {n: reta_de_h_traste(H, n) for n in range(n_trastes + 1)},
    }


def largura_casa_em_v(H: np.ndarray, n: int) -> float:
    """Largura, em px, da casa ``n`` a meia altura do braço (``v = 0.5``).

    Args:
        H: homografia.
        n: casa (de 1 em diante, qualquer); o nut é a fronteira 0.

    Returns:
        Distância entre os trastes ``n-1`` e ``n``, em px.
    """
    a, b = aplicar_homografia(
        H,
        np.array(
            [
                (float(s_traste(n - 1)), 0.5),
                (float(s_traste(n)), 0.5),
            ]
        ),
    )
    return float(np.linalg.norm(b - a))


def medir_contra_fixa(H: np.ndarray, braco: dict[str, Any]) -> dict[str, Any]:
    """Medição (a): erro da H contra a calibração à mão, por corda e por casa.

    Args:
        H: homografia a medir.
        braco: conteúdo de ``braco.json``.

    Returns:
        ``geral`` (px e fração de casa: mediana, p90, máximo), ``por_corda`` e
        ``por_casa`` (mediana em px e em fração).
    """
    linhas = comparar_com_fixa(H, braco)
    px = [linha["erro_px"] for linha in linhas]
    fr = [linha["fracao"] for linha in linhas]
    por_corda = {}
    for corda in range(1, 7):
        sub = [x for x in linhas if x["corda"] == corda]
        por_corda[corda] = {
            "px": round(float(np.median([x["erro_px"] for x in sub])), 2),
            "fracao": round(float(np.median([x["fracao"] for x in sub])), 3),
        }
    por_casa = {}
    for casa in range(1, 13):
        sub = [x for x in linhas if x["casa"] == casa]
        por_casa[casa] = {
            "px": round(float(np.median([x["erro_px"] for x in sub])), 2),
            "fracao": round(float(np.median([x["fracao"] for x in sub])), 3),
        }
    return {
        "geral_px": estatisticas(px),
        "geral_fracao": estatisticas(fr),
        "por_corda": por_corda,
        "por_casa": por_casa,
    }


def gabarito_dono(caminho: Path, quadro: str) -> dict[str, Any]:
    """Pontos do dono num quadro do braço (cordas 1 e 6, nut e todos os trastes).

    Args:
        caminho: ``data/gold/maos/braco.json``.
        quadro: id do quadro (``q02``, ``q16``...).

    Returns:
        ``corda1``, ``corda6`` (dois pontos cada), ``nut`` e ``trastes`` (um ponto por
        traste marcado, do traste 1 para cima; o número é a posição + 1).

    Raises:
        ValueError: se o quadro não tem o braço ou não tem nenhum traste marcado.
    """
    dados = carregar_json(caminho)["quadros"][quadro]
    if dados.get("braco") != "sim" or not dados["trastes"]:
        raise ValueError(f"quadro {quadro} sem o braço completo")
    return {
        "corda1": np.asarray(dados["corda1"], dtype=float),
        "corda6": np.asarray(dados["corda6"], dtype=float),
        "nut": np.asarray(dados["nut"], dtype=float),
        "trastes": np.asarray(dados["trastes"], dtype=float),
    }


def gabarito_dono_q02(caminho: Path) -> dict[str, Any]:
    """Atalho: :func:`gabarito_dono` no quadro q02 (14 trastes).

    Args:
        caminho: ``data/gold/maos/braco.json``.

    Returns:
        O mesmo que :func:`gabarito_dono` para o q02.
    """
    return gabarito_dono(caminho, QUADRO_DONO)


def medir_contra_dono(
    H: np.ndarray | None, dono: dict[str, Any], braco: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Medição (b): distância dos pontos do dono às retas previstas.

    Cordas 1 e 6: distância média dos dois pontos à reta prevista, em px e como fração
    da distância vertical entre as cordas 1 e 6 no mesmo ``x`` (o espaçamento 1 a 6
    inteiro; dividir por 5 dá o passo). Nut: distância à reta do nut, em fração da casa 1.
    Trastes: para cada traste marcado pelo dono (quantos forem, do traste 1 para cima),
    o traste previsto de mesmo número; conta se a distância é menor que 1/4 da casa;
    fração = distância / largura da casa. Na calibração à mão, só entram os trastes
    que ``braco.json`` tem; os outros não são medidos.

    Args:
        H: homografia, ou ``None`` para a calibração à mão (usa ``braco``).
        dono: saída de :func:`gabarito_dono`.
        braco: conteúdo de ``braco.json``, para a calibração à mão.

    Returns:
        Por corda, nut e trastes, com px e fração, e o resumo.
    """
    n_trastes = len(dono["trastes"])
    if H is None:
        retas = retas_da_calibracao_fixa(braco)
        cordas = retas["cordas"]
        trastes = retas["trastes"]
        largura = {
            n: abs(retas["x"][n] - retas["x"][n - 1])
            for n in range(1, n_trastes + 1)
            if n in retas["x"] and n - 1 in retas["x"]
        }
    else:
        retas = retas_da_calibracao(H, n_trastes)
        cordas = retas["cordas"]
        trastes = retas["trastes"]
        largura = {n: largura_casa_em_v(H, n) for n in range(1, n_trastes + 1)}

    saida: dict[str, Any] = {"cordas": {}}
    for nome, j in (("corda1", 1), ("corda6", 6)):
        A, B = cordas[j]
        dist = [distancia_a_reta(p, A, B) for p in dono[nome]]
        A1, B1 = cordas[1]
        A6, B6 = cordas[6]
        sep = [
            abs(y_da_reta(A1, B1, p[0]) - y_da_reta(A6, B6, p[0])) for p in dono[nome]
        ]
        frac = [d / s for d, s in zip(dist, sep, strict=True)]
        saida["cordas"][nome] = {
            "px_media": round(float(np.mean(dist)), 2),
            "fracao_span_16_media": round(float(np.mean(frac)), 4),
            "pontos_px": [round(float(d), 2) for d in dist],
        }
    A, B = trastes[0]
    d_nut = distancia_a_reta(dono["nut"], A, B)
    saida["nut"] = {"px": round(d_nut, 2), "fracao_casa1": round(d_nut / largura[1], 4)}
    casamentos = []
    for k, p in enumerate(dono["trastes"], start=1):
        if k not in trastes or k not in largura:
            continue
        A, B = trastes[k]
        d = distancia_a_reta(p, A, B)
        w = largura[k]
        casamentos.append(
            {
                "traste": k,
                "px": round(d, 2),
                "fracao": round(d / w, 4),
                "casa_com_traste_previsto": bool(d < w / 4),
            }
        )
    usados = [c for c in casamentos if c["casa_com_traste_previsto"]]
    saida["trastes"] = {
        "casamentos": casamentos,
        "n_com_traste_previsto": len(usados),
        "n_total": len(casamentos),
        "fracao_mediana_dos_casados": (
            round(float(np.median([c["fracao"] for c in usados])), 4)
            if usados
            else None
        ),
        "px_mediana_dos_casados": (
            round(float(np.median([c["px"] for c in usados])), 2) if usados else None
        ),
    }
    return saida


def _pontos_inteiros(pontos: np.ndarray) -> list[tuple[int, int]]:
    """Pontos arredondados para inteiros, como o OpenCV espera.

    Args:
        pontos: ``(N, 2)`` em px.

    Returns:
        Lista de ``(x, y)`` inteiros.
    """
    return [(int(np.rint(x)), int(np.rint(y))) for x, y in pontos]


def desenhar_conferencia(
    quadro: np.ndarray, H: np.ndarray, dono: dict[str, Any]
) -> np.ndarray:
    """Grade "música + imagem" em vermelho e os pontos do dono em verde.

    A grade vai até o último traste marcado pelo dono.

    Args:
        quadro: quadro BGR da mediana (ou do quadro do dono).
        H: homografia "música + imagem".
        dono: saída de :func:`gabarito_dono`.

    Returns:
        Cópia do quadro com as linhas e os pontos.
    """
    img = quadro.copy()
    n_trastes = len(dono["trastes"])
    us = np.linspace(0.0, float(s_traste(n_trastes)), 40)
    vs = np.linspace(0.0, 1.0, 40)
    for j in range(1, 7):
        pts = aplicar_homografia(H, np.column_stack([us, np.full_like(us, v_corda(j))]))
        cv2.polylines(img, [pts.astype(np.int32)], False, VERMELHO, 2)
    for n in range(n_trastes + 1):
        pts = aplicar_homografia(
            H, np.column_stack([np.full_like(vs, s_traste(n)), vs])
        )
        cv2.polylines(img, [pts.astype(np.int32)], False, VERMELHO, 1)
    for nome in ("corda1", "corda6"):
        cv2.polylines(
            img,
            [np.asarray(_pontos_inteiros(dono[nome]), dtype=np.int32)],
            False,
            VERDE,
            2,
        )
    for x, y in _pontos_inteiros(np.vstack([dono["nut"], dono["trastes"]])):
        cv2.circle(img, (x, y), 6, VERDE, -1)
    return img


def predicoes_de_dedo(
    H: np.ndarray,
    nome: str,
    mvp: list[dict[str, Any]],
    gabarito: dict[str, Any],
    maos_meio: dict[float, list[dict[str, Any]]],
    maos_ant: dict[float, list[dict[str, Any]]],
    maos_dep: dict[float, list[dict[str, Any]]],
    pasta: Path,
) -> None:
    """Grava as predições de ponta e de voto para o avaliador oficial.

    Args:
        H: homografia calibrada.
        nome: prefixo do método (``calib_est``, ``calib_img``, com ``_excl``).
        mvp: notas do MVP.
        gabarito: gabarito de dedos.
        maos_meio: mãos em ``t_ini``.
        maos_ant: mãos em ``t_ini - 0,1``.
        maos_dep: mãos em ``t_ini + 0,1``.
        pasta: pasta de saída.
    """
    ponta, voto = _decidir_gabarito(mvp, gabarito, H, maos_meio, maos_ant, maos_dep)
    for sufixo, decisoes in (("ponta", ponta), ("voto", voto)):
        metodo = f"{nome}_{sufixo}"
        pred = montar_predicao(metodo, decisoes)
        (pasta / f"pred_{metodo}.json").write_text(
            json.dumps(pred, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def main() -> None:
    """Gera a mediana (com ``--gerar-mediana``) ou roda a calibração e as medições."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--gerar-mediana", action="store_true")
    parser.add_argument(
        "--gerar-mediana-cena",
        metavar="QUADRO",
        default=None,
        help="mediana da cena do quadro (ex.: q16), em m3d/<quadro>/mediana.png",
    )
    args = parser.parse_args()

    mvp = carregar_json(MVP)["notas"]
    instantes_todos = sorted(
        {
            round(float(n["t_ini"]), 3)
            for n in mvp
            if n.get("t_ini") is not None and n["casa"] > 0
        }
    )
    if args.gerar_mediana:
        gerar_mediana(VIDEO, instantes_espalhados(instantes_todos, N_QUADROS))
        return
    if args.gerar_mediana_cena:
        gerar_mediana_da_cena(args.gerar_mediana_cena)
        return

    gabarito = carregar_json(GABARITO_DEDOS)
    braco = carregar_json(BRACO_FIXO)
    antes = carregar_json(PASTA / "calibracao.json")
    maos_meio = mapa_de_maos(carregar_json(PONTAS)["instantes"])
    maos_ant = mapa_de_maos(carregar_json(PONTAS_ANT)["instantes"])
    maos_dep = mapa_de_maos(carregar_json(PONTAS_DEP)["instantes"])
    gold_t = frozenset(round(float(n["t_ini"]), 3) for n in gabarito["notas"])
    dono = gabarito_dono_q02(GABARITO_BRACO)
    mediana = cv2.imread(str(MEDIANA_PNG))
    if mediana is None:
        raise SystemExit(f"sem a mediana: {MEDIANA_PNG} (rode --gerar-mediana)")

    conj = montar_conjunto(mvp, maos_meio)
    conj_excl = montar_conjunto(mvp, maos_meio, excluir=gold_t)
    H_antes = np.asarray(antes["H"])

    print(
        "consenso com 3 conjuntos de 10 sementes (com todos os instantes)...",
        flush=True,
    )
    consensos = []
    for k, sementes in enumerate(CONJUNTOS_DE_SEMENTES):
        cons = consenso(conj, sementes)
        consensos.append(cons)
        print(f"  conjunto {k}: escolhida semente {cons['semente']}", flush=True)
    H_est = consensos[0]["H"]
    print("consenso sem os instantes do gabarito...", flush=True)
    cons_excl = consenso(conj_excl, CONJUNTOS_DE_SEMENTES[0])
    H_est_excl = cons_excl["H"]

    H_img, grade, resumo_img = calibrar_com_imagem(H_est, mediana)
    H_img_excl, _grade_excl, resumo_img_excl = calibrar_com_imagem(H_est_excl, mediana)

    # Estabilidade: grade de cada conjunto, e da H de imagem de cada conjunto.
    H_conjuntos = [c["H"] for c in consensos]
    H_imgs_conjuntos = [calibrar_com_imagem(h, mediana)[0] for h in H_conjuntos]
    pares = [(0, 1), (0, 2), (1, 2)]
    estab = {
        "estabilizada": {
            "entre_conjuntos": [
                {"par": f"{a}-{b}", **diferenca_entre_h(H_conjuntos[a], H_conjuntos[b])}
                for a, b in pares
            ],
            "vs_antes": diferenca_entre_h(H_est, H_antes),
            "sem_gabarito_vs_principal": diferenca_entre_h(H_est, H_est_excl),
            "inliers_por_conjunto": [
                [c["inliers"] for c in cons["candidatos"]] for cons in consensos
            ],
            "custo_por_conjunto": [
                round(float(cons["custo"]), 4) for cons in consensos
            ],
        },
        "imagem": {
            "entre_conjuntos": [
                {
                    "par": f"{a}-{b}",
                    **diferenca_entre_h(H_imgs_conjuntos[a], H_imgs_conjuntos[b]),
                }
                for a, b in pares
            ],
        },
    }
    # Média e amplitude entre os 3 pares de conjuntos (regra 1: 3 execuções).
    for chave in ("estabilizada", "imagem"):
        mediana_px = [p["mediana_px"] for p in estab[chave]["entre_conjuntos"]]
        maximo_px = [p["maximo_px"] for p in estab[chave]["entre_conjuntos"]]
        estab[chave]["resumo"] = {
            "mediana_px_media": round(float(np.mean(mediana_px)), 3),
            "mediana_px_amplitude": round(float(np.ptp(mediana_px)), 3),
            "maximo_px_media": round(float(np.mean(maximo_px)), 3),
            "maximo_px_amplitude": round(float(np.ptp(maximo_px)), 3),
        }

    # (a) e (b): calibrações lado a lado.
    a_tab = {
        "musica_antes": medir_contra_fixa(H_antes, braco),
        "musica_estabilizada": medir_contra_fixa(H_est, braco),
        "musica_imagem": medir_contra_fixa(H_img, braco),
    }
    b_tab = {
        "fixa": medir_contra_dono(None, dono, braco),
        "musica_antes": medir_contra_dono(H_antes, dono),
        "musica_estabilizada": medir_contra_dono(H_est, dono),
        "musica_imagem": medir_contra_dono(H_img, dono),
    }

    # (c): dedo, com e sem os instantes do gabarito.
    predicoes_de_dedo(
        H_est, "calib_est", mvp, gabarito, maos_meio, maos_ant, maos_dep, PASTA
    )
    predicoes_de_dedo(
        H_img, "calib_img", mvp, gabarito, maos_meio, maos_ant, maos_dep, PASTA
    )
    predicoes_de_dedo(
        H_est_excl,
        "calib_est_excl",
        mvp,
        gabarito,
        maos_meio,
        maos_ant,
        maos_dep,
        PASTA,
    )
    predicoes_de_dedo(
        H_img_excl,
        "calib_img_excl",
        mvp,
        gabarito,
        maos_meio,
        maos_ant,
        maos_dep,
        PASTA,
    )

    # (d): imagem de conferência.
    quadro = desenhar_conferencia(mediana, H_img, dono)
    cv2.imwrite(str(CALIBRACAO_V2_JPG), quadro, [cv2.IMWRITE_JPEG_QUALITY, 92])

    resultado = {
        "mediana": {
            "arquivo": str(MEDIANA_PNG),
            "quadros": json.loads(MEDIANA_JSON.read_text(encoding="utf-8")),
        },
        "H": {
            "antes": H_antes.tolist(),
            "estabilizada": H_est.tolist(),
            "imagem": H_img.tolist(),
            "estabilizada_sem_gabarito": H_est_excl.tolist(),
            "imagem_sem_gabarito": H_img_excl.tolist(),
        },
        "consenso": [
            {
                "conjunto": k,
                "escolhida": c["semente"],
                "candidatos": [
                    {kk: vv for kk, vv in cand.items() if kk != "H"}
                    for cand in c["candidatos"]
                ],
            }
            for k, c in enumerate(consensos)
        ],
        "consenso_sem_gabarito": {
            "escolhida": cons_excl["semente"],
            "inliers": int(avaliar(H_est_excl, conj_excl)["n"]),
            "notas": len(conj_excl.indices),
        },
        "inliers": {
            "antes": int(avaliar(H_antes, conj)["n"]),
            "estabilizada": int(avaliar(H_est, conj)["n"]),
            "notas_com_pontas": len(conj.indices),
        },
        "imagem": {"com_gabarito": resumo_img, "sem_gabarito": resumo_img_excl},
        "grade_achada": {
            "cordas": [
                {k: (round(v, 2) if isinstance(v, float) else v) for k, v in c.items()}
                for c in grade["cordas"]
            ],
            "trastes": [
                {k: (round(v, 2) if isinstance(v, float) else v) for k, v in t.items()}
                for t in grade["trastes"]
            ],
        },
        "estabilidade": estab,
        "a_contra_fixa": a_tab,
        "b_contra_dono": b_tab,
        "a_resumo_geral_px": {k: v["geral_px"] for k, v in a_tab.items()},
        "conferencia_jpg": str(CALIBRACAO_V2_JPG),
    }
    CALIBRACAO_V2.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(resumo_img, ensure_ascii=False))
    print(f"gravado: {CALIBRACAO_V2}")


if __name__ == "__main__":
    main()

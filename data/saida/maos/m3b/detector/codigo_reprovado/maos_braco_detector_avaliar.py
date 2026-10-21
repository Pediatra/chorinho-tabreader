"""Avaliação do detector do braço contra o gabarito do dono (M3b).

Compara a saída de ``tab.maos_braco_detector`` com ``data/gold/maos/braco.json``,
quadro a quadro, e separa desenvolvimento e teste (``divisao.json``). Métricas:

- braço achado; ordem das cordas (qual reta é a corda 1);
- erro das retas das cordas 1 e 6 (px e fração do espaçamento);
- nut: erro em fração da casa 1, ou acerto de "fora";
- trastes: fração com um traste previsto de MESMO número a < 1/4 da casa local,
  e fração com número errado (um traste observado de outro número ali perto);
- falso braço: o detector afirma braço e as cordas estão longe do gabarito.

Uso::

    python -m tab.maos_braco_detector_avaliar --conjunto dev
"""

from __future__ import annotations

import argparse
import json
import sys

import cv2
import numpy as np

from .caminhos import GABARITO_BRACO
from .maos_braco_detector import (
    FRACAO_TOLERANCIA,
    PASTA_DETECTOR,
    PASTA_QUADROS,
    carregar_divisao,
)
from .maos_braco_gabarito import numerar_trastes

#: Fração do espaçamento das cordas acima da qual "achou braço" é falso braço.
FRACAO_FALSO_BRACO = 0.5


def angulo_da_reta(p1: list[float], p2: list[float]) -> tuple[float, float]:
    """Direção e normal de uma reta por dois pontos.

    Args:
        p1: primeiro ponto ``[x, y]``.
        p2: segundo ponto ``[x, y]``.

    Returns:
        ``(theta em graus, d)``: a direção ``theta`` e a distância ``d`` da reta
        à origem, ao longo da normal ``(-sin, cos)``.
    """
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    theta = float(np.degrees(np.arctan2(dy, dx)) % 180.0)
    rad = np.radians(theta)
    normal = np.array([-np.sin(rad), np.cos(rad)])
    return theta, float(np.dot(p1, normal))


def distancia_a_reta(pontos: list[list[float]], theta: float, d: float) -> float:
    """Distância média de pontos a uma reta dada por (theta, d).

    Args:
        pontos: pontos ``[x, y]``.
        theta: direção da reta, em graus.
        d: distância da reta à origem, ao longo da normal ``(-sin, cos)``.

    Returns:
        Média das distâncias perpendiculares, em px.
    """
    rad = np.radians(theta)
    normal = np.array([-np.sin(rad), np.cos(rad)])
    valores = [abs(float(np.dot(p, normal)) - d) for p in pontos]
    return float(np.mean(valores))


def corda1_por_regra(det: dict, regra: str) -> tuple[float, float]:
    """Corda 1 (d, lado) pela regra escolhida, entre as duas de fora.

    Args:
        det: saída do detector com ``faixa`` e ``_lados``.
        regra: ``"baixo"`` (a corda mais baixa na imagem é a 1) ou ``"escuro"``
            (a corda mais escura é a 1).

    Returns:
        ``(d da corda 1, d da corda 6)``.
    """
    d_lo, d_hi = det["faixa"]
    lados = det["_lados"]
    y_lo, brilho_lo = lados["d_lo"]
    y_hi, brilho_hi = lados["d_hi"]
    if regra == "baixo":
        return (d_lo, d_hi) if y_lo > y_hi else (d_hi, d_lo)
    return (d_lo, d_hi) if brilho_lo < brilho_hi else (d_hi, d_lo)


def metricas_do_quadro(
    det: dict,
    registro: dict,
    forma: tuple[int, int],
    regra: str = "baixo",
) -> dict:
    """Compara a detecção de um quadro com o gabarito dele.

    Args:
        det: saída de ``detectar`` para o quadro.
        registro: registro do gabarito (``corda1``, ``corda6``, ``nut``,
            ``trastes``, ``traste_referencia``).
        forma: ``(altura, largura)`` do quadro.
        regra: regra de ordem das cordas (``"baixo"`` ou ``"escuro"``).

    Returns:
        Dicionário com as métricas do quadro.
    """
    _altura, _largura = forma
    saida: dict = {"braco_achado": bool(det["braco"])}
    c1 = [list(p) for p in registro["corda1"]]
    c6 = [list(p) for p in registro["corda6"]]
    theta_g, _ = angulo_da_reta(c1[0], c1[1])
    espaco = distancia_a_reta(c6, theta_g, angulo_da_reta(c1[0], c1[1])[1])
    saida["espaco_gold_px"] = espaco
    if not det["braco"]:
        saida.update(
            {
                "ordem_certa": False,
                "erro_cordas_px": None,
                "erro_cordas_frac": None,
                "falso_braco": False,
                "nut": _nut_do_gabarito(registro, det, forma),
                "trastes": _metricas_trastes(registro, det),
            }
        )
        return saida
    d1, d6 = corda1_por_regra(det, regra)
    theta = det["theta_graus"]
    e11 = distancia_a_reta(c1, theta, d1)
    e16 = distancia_a_reta(c1, theta, d6)
    e61 = distancia_a_reta(c6, theta, d1)
    e66 = distancia_a_reta(c6, theta, d6)
    ordem_certa = (e11 + e66) <= (e16 + e61)
    erro_cordas = (e11 + e66) / 2.0 if ordem_certa else (e16 + e61) / 2.0
    saida["ordem_certa"] = bool(ordem_certa)
    saida["erro_cordas_px"] = float(erro_cordas)
    saida["erro_cordas_frac"] = float(erro_cordas / espaco) if espaco > 0 else None
    saida["falso_braco"] = bool(
        espaco > 0 and erro_cordas / espaco > FRACAO_FALSO_BRACO
    )
    saida["nut"] = _nut_do_gabarito(registro, det, forma)
    saida["trastes"] = _metricas_trastes(registro, det)
    return saida


def _nut_do_gabarito(registro: dict, det: dict, forma: tuple[int, int]) -> dict:
    """Erro do nut em casas, ou acerto de "fora".

    Args:
        registro: registro do gabarito.
        det: saída do detector.
        forma: ``(altura, largura)``.

    Returns:
        ``{"gold": ..., "erro_casas": float | None, "acerto_fora": bool | None}``.
    """
    altura, largura = forma
    gold = registro["nut"]
    if gold == "fora":
        dentro = False
        if det["braco"] and det.get("nut") is not None:
            x, y = det["nut"]["ponto"]
            dentro = 0 <= x <= largura - 1 and 0 <= y <= altura - 1
        return {"gold": "fora", "erro_casas": None, "acerto_fora": not dentro}
    if not det["braco"] or det.get("nut") is None:
        return {"gold": "ponto", "erro_casas": None, "acerto_fora": None}
    theta = det["theta_graus"]
    rad = np.radians(theta)
    v = np.array([np.cos(rad), np.sin(rad)])
    casa1 = _casa_local_gold(registro, 1)
    diferenca = (np.array(det["nut"]["ponto"]) - np.array(gold)) @ v
    erro = abs(float(diferenca)) / casa1 if casa1 else None
    return {"gold": "ponto", "erro_casas": erro, "acerto_fora": None}


def _casa_local_gold(registro: dict, numero: int) -> float | None:
    """Largura da casa ``numero`` no gabarito (distância do traste ``n-1`` ao ``n``).

    Args:
        registro: registro do gabarito.
        numero: número do traste.

    Returns:
        Largura em px, ou ``None`` se o gabarito não tem os dois trastes.
    """
    numerados = {
        t["numero"]: t["ponto"]
        for t in numerar_trastes(registro)
        if t["numero"] is not None
    }
    anterior = numerados.get(
        numero - 1,
        registro["nut"]
        if numero - 1 == 0 and isinstance(registro["nut"], list)
        else None,
    )
    atual = numerados.get(numero)
    if anterior is None or atual is None:
        return None
    return float(np.hypot(atual[0] - anterior[0], atual[1] - anterior[1]))


def _metricas_trastes(registro: dict, det: dict) -> dict:
    """Trastes do gabarito: acerto de número, número errado e total.

    Args:
        registro: registro do gabarito.
        det: saída do detector.

    Returns:
        ``{"total", "mesmo_numero", "numero_errado"}`` contagens do quadro.
    """
    gold = [t for t in numerar_trastes(registro) if t["numero"] is not None]
    if not det["braco"] or not gold:
        return {"total": len(gold), "mesmo_numero": 0, "numero_errado": 0}
    theta = det["theta_graus"]
    rad = np.radians(theta)
    v = np.array([np.cos(rad), np.sin(rad)])
    posicoes = {
        t["numero"]: float(t["ponto"][0] * v[0] + t["ponto"][1] * v[1]) for t in gold
    }
    observados = [(t["numero"], t["u"]) for t in det["trastes"] if t["observado"]]
    previstos = {t["numero"]: t["u"] for t in det["trastes"]}
    mesmo = 0
    errado = 0
    for numero, u in posicoes.items():
        largura = _largura_local(posicoes, numero)
        if largura is None:
            continue
        tolerancia = FRACAO_TOLERANCIA * largura
        if numero in previstos and abs(previstos[numero] - u) <= tolerancia:
            mesmo += 1
        if any(n != numero and abs(uo - u) <= tolerancia for n, uo in observados):
            errado += 1
    return {"total": len(gold), "mesmo_numero": mesmo, "numero_errado": errado}


def _largura_local(posicoes: dict[int, float], numero: int) -> float | None:
    """Largura local da casa no gabarito, em px ao longo do eixo.

    Args:
        posicoes: posição (ao longo do eixo) de cada traste do gabarito.
        numero: número do traste.

    Returns:
        ``|u(n+1) - u(n-1)| / 2`` quando os dois existem; senão a distância
        ao vizinho mais próximo; ``None`` se não há vizinho.
    """
    if numero - 1 in posicoes and numero + 1 in posicoes:
        return abs(posicoes[numero + 1] - posicoes[numero - 1]) / 2.0
    vizinhos = [n for n in (numero - 1, numero + 1) if n in posicoes]
    if not vizinhos:
        return None
    return min(abs(posicoes[n] - posicoes[numero]) for n in vizinhos)


def agregar(linhas: list[dict]) -> dict:
    """Resumo de um conjunto de quadros.

    Args:
        linhas: métricas por quadro (saída de ``metricas_do_quadro`` + ``id``).

    Returns:
        Dicionário com as taxas e as medianas agregadas.
    """
    n = len(linhas)
    if n == 0:
        return {"quadros": 0}
    achados = [item for item in linhas if item["braco_achado"]]
    ordem = [item["ordem_certa"] for item in achados]
    erros = [
        item["erro_cordas_px"] for item in achados if item["erro_cordas_px"] is not None
    ]
    fracoes = [
        item["erro_cordas_frac"]
        for item in achados
        if item["erro_cordas_frac"] is not None
    ]
    casas = [
        item["nut"]["erro_casas"]
        for item in linhas
        if item["nut"]["erro_casas"] is not None
    ]
    fora = [
        item["nut"]["acerto_fora"]
        for item in linhas
        if item["nut"]["acerto_fora"] is not None
    ]
    total = sum(item["trastes"]["total"] for item in linhas)
    mesmo = sum(item["trastes"]["mesmo_numero"] for item in linhas)
    errado = sum(item["trastes"]["numero_errado"] for item in linhas)
    return {
        "quadros": n,
        "braco_achado": len(achados),
        "ordem_certa": int(sum(ordem)),
        "erro_cordas_px_mediana": float(np.median(erros)) if erros else None,
        "erro_cordas_frac_mediana": float(np.median(fracoes)) if fracoes else None,
        "nut_erro_casas_mediana": float(np.median(casas)) if casas else None,
        "nut_fora_acertos": f"{int(sum(fora))}/{len(fora)}" if fora else None,
        "trastes_gold": total,
        "trastes_mesmo_numero": mesmo,
        "trastes_mesmo_numero_frac": mesmo / total if total else None,
        "trastes_numero_errado": errado,
        "trastes_numero_errado_frac": errado / total if total else None,
        "falsos_bracos": int(sum(item["falso_braco"] for item in linhas)),
    }


def desenhar(cinza: np.ndarray, det: dict, registro: dict, saida_jpg: str) -> None:
    """Imagem de conferência: gabarito em verde, detecção em vermelho.

    Args:
        cinza: quadro em tons de cinza.
        det: saída do detector.
        registro: registro do gabarito.
        saida_jpg: caminho do JPG a gravar.
    """
    quadro = cv2.cvtColor(cinza, cv2.COLOR_GRAY2BGR)
    altura, largura = cinza.shape
    verde = (80, 220, 80)
    vermelho = (40, 40, 255)
    for chave in ("corda1", "corda6"):
        p, q = registro[chave]
        cv2.line(quadro, tuple(map(int, p)), tuple(map(int, q)), verde, 2)
    if isinstance(registro["nut"], list):
        cv2.circle(quadro, tuple(map(int, registro["nut"])), 10, verde, 3)
    for t in numerar_trastes(registro):
        if t["numero"] is not None:
            cv2.circle(quadro, tuple(map(int, t["ponto"])), 7, verde, 2)
    if det["braco"]:
        theta = np.radians(det["theta_graus"])
        normal = np.array([-np.sin(theta), np.cos(theta)])
        v = np.array([np.cos(theta), np.sin(theta)])
        for d in det["cordas_d"]:
            meio = normal * d
            a = meio - v * 4000
            b = meio + v * 4000
            cv2.line(quadro, tuple(map(int, a)), tuple(map(int, b)), vermelho, 2)
        if det.get("nut") is not None:
            cv2.circle(quadro, tuple(map(int, det["nut"]["ponto"])), 12, vermelho, 3)
        for t in det["trastes"]:
            x, y = t["ponto"]
            if 0 <= x < largura and 0 <= y < altura:
                cor = vermelho if t["observado"] else (0, 140, 255)
                cv2.putText(
                    quadro,
                    str(t["numero"]),
                    (int(x) - 8, int(y) - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    cor,
                    2,
                )
    cv2.imwrite(saida_jpg, quadro)


def main() -> int:
    """Avalia a detecção de um conjunto e grava métricas e imagens.

    Returns:
        Código de saída (0).
    """
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--conjunto", choices=("dev", "teste"), required=True)
    parser.add_argument("--regra", choices=("baixo", "escuro"), default="baixo")
    args = parser.parse_args()
    divisao = carregar_divisao()
    ids = divisao["quadros_dev" if args.conjunto == "dev" else "quadros_teste"]
    gabarito = json.loads(GABARITO_BRACO.read_text(encoding="utf-8"))["quadros"]
    linhas: list[dict] = []
    for id_quadro in ids:
        cinza = cv2.imread(str(PASTA_QUADROS / f"{id_quadro}.png"), 0)
        det = json.loads(
            (PASTA_DETECTOR / f"{id_quadro}_{args.conjunto}.json").read_text(
                encoding="utf-8"
            )
        )
        registro = gabarito[id_quadro]
        metrica = metricas_do_quadro(det, registro, cinza.shape, args.regra)
        metrica["id"] = id_quadro
        linhas.append(metrica)
        desenhar(cinza, det, registro, str(PASTA_DETECTOR / f"{id_quadro}.jpg"))
    resumo = agregar(linhas)
    relatorio = {
        "conjunto": args.conjunto,
        "regra": args.regra,
        "resumo": resumo,
        "quadros": linhas,
    }
    caminho = PASTA_DETECTOR / f"metricas_{args.conjunto}_{args.regra}.json"
    caminho.write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(json.dumps(resumo, ensure_ascii=False, indent=1), file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

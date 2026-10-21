"""Medição do braço pela mão como âncora (M3b, rodada 1006), contra o gabarito.

Lê ``data/saida/maos/m3b/detector2/maos.json`` (gerado por ``tab.maos_ancora``, com
GPU) e roda a geometria de ``tab.maos_ancora_geometria`` em cada quadro de um conjunto
(``dev`` ou ``teste``, divisão de ``data/saida/maos/m3b/detector/divisao.json``). Sem
GPU. Grava ``resultado_<conjunto>.json`` e, com ``--imagens``, ``qNN.jpg`` (gabarito
verde, detecção vermelha).

Uso::

    python -m tab.maos_ancora_medir --conjunto dev --imagens
    python -m tab.maos_ancora_medir --conjunto teste
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

from .caminhos import GABARITO_BRACO, MAOS_M3B
from .maos_ancora_geometria import (
    achar_cordas,
    achar_trastes,
    base_do_braco,
    de_s_t,
    media_de_orientacoes,
    melhor_angulo,
    numerar_trastes,
    perfil_longitudinal,
    perfil_trastes,
    pontas,
    projetar_em_s,
    raio_do_disco,
    rastrear_linha,
    reta_em,
    tensor_da_orientacao,
)
from .maos_braco_gabarito import numerar_trastes as numerar_gabarito

PASTA_DETECTOR2 = MAOS_M3B / "detector2"
ARQUIVO_MAOS = PASTA_DETECTOR2 / "maos.json"
ARQUIVO_DIVISAO = MAOS_M3B / "detector" / "divisao.json"
PASTA_QUADROS = MAOS_M3B / "quadros"
INDICE = MAOS_M3B / "indice.json"

#: Alcance ao longo do braço e transversal, como múltiplos do raio do disco.
ALCANCE_S = 2.5
ALCANCE_T = 1.5
#: Varredura de ângulo em torno da direção do tensor, em graus.
VARREDURA_GRAUS = 10.0
#: Lacuna sem achado que o rastreio atravessa (a mão cobre as cordas), em px.
LACUNA_MAXIMA = 25.0
#: Fração do espaçamento das cordas acima da qual o braço não é achado.
FRACAO_TOLERANCIA = 0.25
#: Fração do espaçamento acima da qual a afirmação de braço é falsa.
FRACAO_FALSO_BRACO = 0.5
#: Pontos mínimos rastreados para uma corda contar.
PONTOS_MINIMOS_CORDA = 10
#: Cordas mínimas e comprimento mínimo da faixa, em px, para afirmar braço.
CORDAS_MINIMAS = 4
COMPRIMENTO_MINIMO = 60.0


def _xy(pts: list) -> np.ndarray:
    """Pontos ``[x, y]`` (ou ``[x, y, score]``) como matriz ``(n, 2)``.

    Args:
        pts: lista de pontos.

    Returns:
        Matriz ``(n, 2)`` com x e y.
    """
    return np.array([[float(p[0]), float(p[1])] for p in pts])


def mao_esquerda(quadro: dict) -> np.ndarray | None:
    """Pontos da mão esquerda do quadro (a de maior média de scores).

    Args:
        quadro: registro de ``maos.json``.

    Returns:
        Matriz ``(21, 2)``, ou ``None`` se o quadro não tem mão esquerda.
    """
    candidatas = [m for m in quadro["maos"] if m.get("lado") == "esquerda"]
    if not candidatas:
        return None
    melhor = max(candidatas, key=lambda m: m.get("media") or 0.0)
    return _xy(melhor["pts"])


def _resposta_e_gradientes(cinza: np.ndarray) -> tuple[np.ndarray, ...]:
    """Mapa de bordas finas (DoG, qualquer polaridade) e gradientes da imagem.

    Args:
        cinza: imagem em tons de cinza, ``uint8``.

    Returns:
        ``(resposta, gx, gy)``, todos ``float32``.
    """
    g = cinza.astype(np.float32)
    resposta = np.abs(
        cv2.GaussianBlur(g, (0, 0), 1.0) - cv2.GaussianBlur(g, (0, 0), 3.0)
    )
    suave = cv2.GaussianBlur(g, (0, 0), 1.5)
    gx = cv2.Sobel(suave, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(suave, cv2.CV_32F, 0, 1, ksize=3)
    return resposta, gx, gy


def detectar_braco(cinza: np.ndarray, pts: np.ndarray) -> dict:
    """Braço a partir da mão: direção, cordas, faixa, trastes e nut.

    Args:
        cinza: quadro em tons de cinza.
        pts: pontos da mão esquerda ``(21, 2)``.

    Returns:
        Dicionário com ``afirma`` (bool), ``theta``, ``centro``, ``raio``, ``cordas``
        (lista de ``{"a", "b", "s_min", "s_max", "n"}``, da corda de ``t`` menor para
        a de ``t`` maior), ``faixa`` (``s_ini``, ``s_fim``), ``trastes`` (lista de
        ``{"numero", "s"}``), ``nut_s`` e ``numeracao`` (saída de ``numerar_trastes``).
    """
    resposta, gx, gy = _resposta_e_gradientes(cinza)
    tips = pontas(pts)
    centro = tips.mean(axis=0)
    raio = raio_do_disco(pts)
    orient = [tensor_da_orientacao(gx, gy, p, raio) for p in tips]
    theta0, _coer = media_de_orientacoes(orient)
    alc_s, alc_t = ALCANCE_S * raio, ALCANCE_T * raio
    theta = melhor_angulo(
        resposta, centro, theta0, alc_s, alc_t, varredura_graus=VARREDURA_GRAUS
    )
    u, n = base_do_braco(theta)
    t_vals, perfil = perfil_longitudinal(resposta, centro, u, n, alc_s, alc_t)
    cordas_t = achar_cordas(t_vals, perfil)
    saida: dict = {
        "afirma": False,
        "theta": theta,
        "theta_inicial": theta0,
        "centro": [float(centro[0]), float(centro[1])],
        "raio": raio,
        "cordas": [],
        "faixa": None,
        "trastes": [],
        "nut_s": None,
        "numeracao": None,
    }
    if not cordas_t:
        return saida
    pos = [int(np.argmin(np.abs(t_vals - t))) for t in cordas_t]
    limiar = 0.5 * float(np.mean(perfil[pos]))
    faixa_cordas = []
    for t0 in cordas_t:
        a, b, smin, smax, npts = rastrear_linha(
            resposta, centro, u, n, t0, limiar, alc_s, lacuna_max=LACUNA_MAXIMA
        )
        if npts >= PONTOS_MINIMOS_CORDA:
            faixa_cordas.append(
                {"a": a, "b": b, "s_min": smin, "s_max": smax, "n": npts}
            )
    saida["cordas"] = faixa_cordas
    if len(faixa_cordas) < CORDAS_MINIMAS:
        return saida
    lo, hi = faixa_cordas[0], faixa_cordas[-1]
    s_ini = max(lo["s_min"], hi["s_min"])
    s_fim = min(lo["s_max"], hi["s_max"])
    saida["faixa"] = [float(s_ini), float(s_fim)]
    if s_fim - s_ini < COMPRIMENTO_MINIMO:
        return saida
    saida["afirma"] = True
    s_val, sinal = perfil_trastes(
        resposta, centro, u, n, (lo["a"], lo["b"]), (hi["a"], hi["b"]), s_ini, s_fim
    )
    s_trastes = [s for s in achar_trastes(s_val, sinal) if s_ini <= s <= s_fim]
    numeracao = numerar_trastes(s_trastes)
    saida["trastes"] = [{"s": float(s), "numero": None} for s in s_trastes]
    if numeracao is not None:
        saida["numeracao"] = {k: v for k, v in numeracao.items() if k != "numeros"}
        saida["numeracao"]["numeros"] = numeracao["numeros"]
        for traste, numero in zip(saida["trastes"], numeracao["numeros"], strict=True):
            traste["numero"] = numero
        saida["nut_s"] = float(numeracao["s_nut"])
    return saida


def _pontos_do_braco(det: dict) -> tuple[np.ndarray, np.ndarray]:
    """Eixos ``(centro, u, n)`` do braço detectado.

    Args:
        det: saída de ``detectar_braco``.

    Returns:
        ``(centro, u)`` e ``n`` (como ``(centro, u, n)``).
    """
    centro = np.asarray(det["centro"], dtype=float)
    u, n = base_do_braco(det["theta"])
    return centro, u, n


def _erro_linha(pontos: np.ndarray, a: float, b: float) -> float:
    """Erro médio em px entre pontos ``(s, t)`` e a reta ``t = a + b s``.

    Args:
        pontos: matriz ``(n, 2)`` de ``(s, t)``.
        a: intercepto.
        b: inclinação.

    Returns:
        Média de ``|t - (a + b s)|``.
    """
    return float(np.mean(np.abs(pontos[:, 1] - reta_em(a, b, pontos[:, 0]))))


def metricas_do_quadro(det: dict, registro: dict) -> dict:
    """Compara a detecção de um quadro com o gabarito dele.

    Usa o mesmo eixo do braço detectado. Erro das cordas: distância média dos pontos
    do gabarito às retas detectadas, com a ordem de ``regra`` (corda 1 = a de ``t``
    maior, a mais baixa na imagem; ``"punho"`` = a do lado do punho).

    Args:
        det: saída de ``detectar_braco``.
        registro: registro do gabarito (``corda1``, ``corda6``, ``nut``, ``trastes``).

    Returns:
        Dicionário com ``afirma``, ``achado``, ``falso_braco``, ``ordem_certa``,
        ``erro_cordas_px``, ``erro_cordas_frac``, ``nut``, ``trastes``.
    """
    centro, u, n = _pontos_do_braco(det)
    saida: dict = {"afirma": bool(det["afirma"])}
    c1 = _xy(registro["corda1"])
    c6 = _xy(registro["corda6"])
    s1 = np.array([projetar_em_s(p, centro, u, n) for p in c1])
    s6 = np.array([projetar_em_s(p, centro, u, n) for p in c6])
    # espaçamento: distância média de corda 6 ao reta de corda 1 (no gabarito)
    espaco = _espaco_do_gabarito(s1, s6)
    saida["espaco_gold_px"] = espaco
    if not det["afirma"]:
        saida.update(
            {
                "achado": False,
                "falso_braco": False,
                "ordem_certa": False,
                "erro_cordas_px": None,
                "erro_cordas_frac": None,
            }
        )
    else:
        lo, hi = det["cordas"][0], det["cordas"][-1]
        # mesma ordem de cordas: corda 1 é a de t maior (mais baixa na imagem)
        e_hi1 = _erro_linha(s1, hi["a"], hi["b"])
        e_lo6 = _erro_linha(s6, lo["a"], lo["b"])
        e_lo1 = _erro_linha(s1, lo["a"], lo["b"])
        e_hi6 = _erro_linha(s6, hi["a"], hi["b"])
        ordem_certa = (e_hi1 + e_lo6) <= (e_lo1 + e_hi6)
        erro = (e_hi1 + e_lo6) / 2.0 if ordem_certa else (e_lo1 + e_hi6) / 2.0
        frac = erro / espaco if espaco > 0 else None
        saida.update(
            {
                "ordem_certa": bool(ordem_certa),
                "erro_cordas_px": float(erro),
                "erro_cordas_frac": frac,
                "achado": bool(frac is not None and frac <= FRACAO_TOLERANCIA),
                "falso_braco": bool(frac is not None and frac > FRACAO_FALSO_BRACO),
            }
        )
    saida["nut"] = _nut_do_gabarito(det, registro, centro, u, n)
    saida["trastes"] = _trastes_do_gabarito(det, registro, centro, u, n)
    return saida


def _espaco_do_gabarito(s1: np.ndarray, s6: np.ndarray) -> float:
    """Espaçamento das cordas 1 e 6 do gabarito, em px (perpendicular).

    Args:
        s1: pontos ``(s, t)`` da corda 1.
        s6: pontos ``(s, t)`` da corda 6.

    Returns:
        Média da distância transversal da corda 6 à reta da corda 1.
    """
    b, a = np.polyfit(s1[:, 0], s1[:, 1], 1)
    return float(np.mean(np.abs(s6[:, 1] - reta_em(a, b, s6[:, 0]))))


def _nut_do_gabarito(
    det: dict, registro: dict, centro: np.ndarray, u: np.ndarray, n: np.ndarray
) -> dict:
    """Erro do nut em casas (no eixo do braço), ou acerto de "fora".

    Args:
        det: saída de ``detectar_braco``.
        registro: registro do gabarito.
        centro: origem do eixo.
        u: direção do braço.
        n: direção transversal.

    Returns:
        ``{"gold", "erro_casas", "acerto_fora"}``.
    """
    gold = registro["nut"]
    if gold == "fora":
        return {
            "gold": "fora",
            "erro_casas": None,
            "acerto_fora": det.get("nut_s") is None,
        }
    if det.get("nut_s") is None:
        return {"gold": "ponto", "erro_casas": None, "acerto_fora": None}
    s_gold, _ = projetar_em_s(np.asarray(gold, dtype=float), centro, u, n)
    gold_num = [t for t in numerar_gabarito(registro) if t["numero"] is not None]
    casa1 = None
    for t in gold_num:
        if t["numero"] == 1:
            s1, _ = projetar_em_s(np.asarray(t["ponto"], dtype=float), centro, u, n)
            casa1 = abs(s1 - s_gold)
    if not casa1:
        return {"gold": "ponto", "erro_casas": None, "acerto_fora": None}
    return {
        "gold": "ponto",
        "erro_casas": float(abs(det["nut_s"] - s_gold) / casa1),
        "acerto_fora": None,
    }


def _trastes_do_gabarito(
    det: dict, registro: dict, centro: np.ndarray, u: np.ndarray, n: np.ndarray
) -> dict:
    """Trastes: número certo a menos de 1/4 de casa, e número errado.

    Args:
        det: saída de ``detectar_braco``.
        registro: registro do gabarito.
        centro: origem do eixo.
        u: direção do braço.
        n: direção transversal.

    Returns:
        ``{"total", "mesmo_numero", "numero_errado"}``.
    """
    gold = [t for t in numerar_gabarito(registro) if t["numero"] is not None]
    posicoes = {
        t["numero"]: projetar_em_s(np.asarray(t["ponto"], dtype=float), centro, u, n)[0]
        for t in gold
    }
    if not det["afirma"] or not posicoes:
        return {"total": len(posicoes), "mesmo_numero": 0, "numero_errado": 0}
    nossos = [(t["numero"], t["s"]) for t in det["trastes"] if t["numero"] is not None]
    mesmo = errado = 0
    for numero, s_g in posicoes.items():
        largura = _largura_local(posicoes, numero)
        if largura is None:
            continue
        tol = FRACAO_TOLERANCIA * largura
        if any(nn == numero and abs(ss - s_g) <= tol for nn, ss in nossos):
            mesmo += 1
        if any(nn != numero and abs(ss - s_g) <= tol for nn, ss in nossos):
            errado += 1
    return {"total": len(posicoes), "mesmo_numero": mesmo, "numero_errado": errado}


def _largura_local(posicoes: dict[int, float], numero: int) -> float | None:
    """Largura local da casa no gabarito, ao longo do eixo.

    Args:
        posicoes: posição ``s`` de cada traste do gabarito, por número.
        numero: número do traste.

    Returns:
        ``|s(n+1) - s(n-1)| / 2`` se os dois existem; senão a distância ao vizinho.
    """
    if numero - 1 in posicoes and numero + 1 in posicoes:
        return abs(posicoes[numero + 1] - posicoes[numero - 1]) / 2.0
    vizinhos = [k for k in (numero - 1, numero + 1) if k in posicoes]
    if not vizinhos:
        return None
    return min(abs(posicoes[k] - posicoes[numero]) for k in vizinhos)


def _desenhar(
    cinza: np.ndarray, det: dict, registro: dict | None, saida_jpg: Path
) -> None:
    """Imagem do quadro: gabarito em verde, detecção em vermelho.

    Args:
        cinza: quadro em tons de cinza.
        det: saída de ``detectar_braco``.
        registro: registro do gabarito, ou ``None``.
        saida_jpg: arquivo de saída.
    """
    img = cv2.cvtColor(cinza, cv2.COLOR_GRAY2BGR)
    centro, u, n = _pontos_do_braco(det)
    if registro is not None:
        for chave in ("corda1", "corda6"):
            p = _xy(registro[chave])
            d = p[1] - p[0]
            d = d / (np.linalg.norm(d) + 1e-9)
            a = p[0] - 3000 * d
            b = p[0] + 3000 * d
            cv2.line(
                img, tuple(int(v) for v in a), tuple(int(v) for v in b), (0, 255, 0), 1
            )
        if isinstance(registro["nut"], list):
            cv2.circle(img, tuple(int(v) for v in registro["nut"]), 9, (0, 255, 0), 2)
    if det["afirma"]:
        for corda in det["cordas"]:
            s0, s1 = -3000.0, 3000.0
            p0 = de_s_t(s0, reta_em(corda["a"], corda["b"], s0), centro, u, n)
            p1 = de_s_t(s1, reta_em(corda["a"], corda["b"], s1), centro, u, n)
            cv2.line(
                img,
                tuple(int(v) for v in p0),
                tuple(int(v) for v in p1),
                (0, 0, 255),
                1,
            )
        for traste in det["trastes"]:
            t_m = np.mean(
                [
                    reta_em(c["a"], c["b"], traste["s"])
                    for c in (det["cordas"][0], det["cordas"][-1])
                ]
            )
            p = de_s_t(traste["s"], t_m, centro, u, n)
            cv2.circle(img, (int(p[0]), int(p[1])), 4, (0, 0, 255), 1)
        if det["nut_s"] is not None:
            t_m = np.mean(
                [
                    reta_em(c["a"], c["b"], det["nut_s"])
                    for c in (det["cordas"][0], det["cordas"][-1])
                ]
            )
            p = de_s_t(det["nut_s"], t_m, centro, u, n)
            cv2.circle(img, (int(p[0]), int(p[1])), 9, (0, 0, 255), 2)
    cv2.putText(
        img,
        f"{det['afirma']}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (255, 255, 255),
        2,
    )
    cv2.imwrite(str(saida_jpg), img)


def medir(conjunto: str, imagens: bool) -> dict:
    """Roda a geometria nos quadros do conjunto e compara com o gabarito.

    Args:
        conjunto: ``dev`` ou ``teste``.
        imagens: se grava as imagens ``qNN.jpg``.

    Returns:
        Dicionário com ``resumo`` e ``quadros``.
    """
    divisao = json.loads(ARQUIVO_DIVISAO.read_text(encoding="utf-8"))
    ids = divisao[f"quadros_{'dev' if conjunto == 'dev' else 'teste'}"]
    maos = {
        q["id"]: q
        for q in json.loads(ARQUIVO_MAOS.read_text(encoding="utf-8"))["quadros"]
    }
    gabarito = json.loads(GABARITO_BRACO.read_text(encoding="utf-8"))["quadros"]
    indice = {
        q["id"]: q for q in json.loads(INDICE.read_text(encoding="utf-8"))["quadros"]
    }
    linhas = []
    for qid in sorted(ids):
        pts = mao_esquerda(maos[qid])
        cinza = cv2.imread(str(PASTA_QUADROS / f"{qid}.png"), cv2.IMREAD_GRAYSCALE)
        if pts is None:
            det = {
                "afirma": False,
                "theta": 0.0,
                "centro": [0, 0],
                "cordas": [],
                "trastes": [],
                "nut_s": None,
                "faixa": None,
                "numeracao": None,
            }
        else:
            det = detectar_braco(cinza, pts)
        registro = gabarito[qid]
        m = metricas_do_quadro(det, registro)
        linha = {
            "id": qid,
            "canal": indice[qid]["canal"],
            "mao": pts is not None,
            "det": det,
            **m,
        }
        linhas.append(linha)
        if imagens:
            _desenhar(cinza, det, registro, PASTA_DETECTOR2 / f"{qid}.jpg")
    resumo = _resumir(linhas)
    return {"conjunto": conjunto, "resumo": resumo, "quadros": linhas}


def _resumir(linhas: list[dict]) -> dict:
    """Agregação das métricas do conjunto.

    Args:
        linhas: métricas por quadro.

    Returns:
        Contagens e medianas.
    """
    n = len(linhas)
    erros = [
        linha["erro_cordas_px"]
        for linha in linhas
        if linha.get("erro_cordas_px") is not None
    ]
    fracs = [
        linha["erro_cordas_frac"]
        for linha in linhas
        if linha.get("erro_cordas_frac") is not None
    ]
    erros_nut = [
        linha["nut"]["erro_casas"]
        for linha in linhas
        if linha["nut"].get("erro_casas") is not None
    ]
    total = sum(linha["trastes"]["total"] for linha in linhas)
    return {
        "quadros": n,
        "afirma_braco": sum(linha["afirma"] for linha in linhas),
        "braco_achado": sum(linha["achado"] for linha in linhas),
        "falso_braco": sum(linha["falso_braco"] for linha in linhas),
        "ordem_certa": sum(linha["ordem_certa"] for linha in linhas),
        "erro_cordas_px_mediana": float(np.median(erros)) if erros else None,
        "erro_cordas_frac_mediana": float(np.median(fracs)) if fracs else None,
        "nut_erro_casas_mediana": float(np.median(erros_nut)) if erros_nut else None,
        "trastes_gold": total,
        "trastes_mesmo_numero": sum(
            linha["trastes"]["mesmo_numero"] for linha in linhas
        ),
        "trastes_numero_errado": sum(
            linha["trastes"]["numero_errado"] for linha in linhas
        ),
    }


def main() -> int:
    """CLI: roda um conjunto (``dev`` ou ``teste``) e grava o resultado.

    Returns:
        Código de saída do processo.
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--conjunto", choices=["dev", "teste"], required=True)
    ap.add_argument("--imagens", action="store_true")
    args = ap.parse_args()
    PASTA_DETECTOR2.mkdir(parents=True, exist_ok=True)
    resultado = medir(args.conjunto, args.imagens)
    destino = PASTA_DETECTOR2 / f"resultado_{args.conjunto}.json"
    destino.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=1, default=float),
        encoding="utf-8",
    )
    print(json.dumps(resultado["resumo"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

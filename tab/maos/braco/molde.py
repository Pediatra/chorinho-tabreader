"""Violão molde nas marcas do dono: medida (a) da 1009, sem treino e sem acervo.

Para cada quadro do gabarito do braço (``data/gold/maos/braco.json``) que tem uma
câmera (``paineis == "nao"``) e a pestana no quadro, mede o que a geometria do violão
diz sobre as marcas do dono:

1. **retidão**: quanto cada saddle (1 e 6) se afasta da reta da corda dele, em px e em
   vãos no saddle;
2. **s_saddle**: onde o saddle cai na escala, pela regra das 12 notas com perspectiva
   (ajuste projetivo dos trastes, com o nut como número 0). O esperado é perto de 1,0;
3. **boca**: elipse ajustada nos pontos do dono, com o centro, o s do centro e o
   deslocamento lateral em vãos locais;
4. **cavalete**: onde a reta do cavalete cruza o eixo, em s.

Só medidas: nada aqui julga o gabarito. Quadros com a tela dividida em caixas (1008)
ficam de fora, porque cada caixa é uma câmera.

Uso::

    python -m tab.maos_braco_molde

Grava ``MAOS_M11/molde/molde.json`` e os desenhos em ``MAOS_M11/molde/desenhos/``.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import sys

import cv2
import numpy as np

from tab.comum.caminhos import GABARITO_BRACO, MAOS_M3B, MAOS_M3B_QUADROS, MAOS_M11
from tab.maos.braco.geometria import ajustar, eixo_do_braco, prever
from tab.maos.braco.tempo import Marcas, marcas_do_registro

#: Intervalos entre as 6 cordas: vão de corda = distância entre as cordas 1 e 6 / 5.
INTERVALOS_CORDAS = 5
#: Trastes previstos desenhados (1 até este número; s chega a ~0,87 no 36).
TRASTES_DESENHADOS = 36
#: Largura dos desenhos em px (reduzidos só quando o quadro é mais largo).
LARGURA_DESENHO = 1600
#: Versão do formato do ``molde.json``.
FORMATO_MOLDE = 1
#: Número mínimo de pontos da boca para ajustar a elipse.
PONTOS_ELIPSE = 5
#: Razão entre os eixos da elipse acima da qual ela é tida como absurda.
RAZAO_ELIPSE_ABSURDA = 10.0
#: Limites para marcar valores estranhos no relatório.
LIMITE_RETIDAO_VAOS = 0.5
FAIXA_S_SADDLE = (0.9, 1.1)
#: Motivos de quadro fora das medidas que cruzam braço e corpo.
MOTIVO_SEM_BRACO = "braço sem geometria completa"
MOTIVO_PAINEIS = "painéis em caixas (tela dividida: uma câmera por caixa)"
MOTIVO_NUT_FORA = "pestana fora do quadro (nut = fora)"
#: Cores (BGR) dos desenhos.
COR_CORDA = (0, 255, 0)
COR_SADDLE = (0, 0, 255)
COR_PREVISTO = (0, 255, 255)
COR_BOCA = (255, 0, 0)
COR_CAVALETE = (255, 255, 0)
COR_NUT = (255, 0, 255)
COR_TRASTE = (255, 255, 255)
#: Nomes das partes do saddle no gabarito.
NOMES_SADDLE = ("saddle1", "saddle6")
#: Canais em ordem fixa no resumo.
CAMPOS_RESUMO = (
    "retidao_vaos",
    "s_saddle",
    "s_boca",
    "lateral_boca_vaos",
    "s_cavalete",
    "maior_traste",
    "resid_proj_px",
)


@dataclasses.dataclass(frozen=True, eq=False)
class Eixo:
    """Eixo do braço de um quadro, orientado da pestana para o corpo.

    Attributes:
        nut: ponto da pestana (``t = 0``).
        origem: um ponto do eixo (a linha média entre as cordas 1 e 6).
        u: vetor unitário do eixo, no sentido do corpo.
    """

    nut: np.ndarray
    origem: np.ndarray
    u: np.ndarray

    def t(self, ponto: np.ndarray) -> float:
        """Projeção de um ponto no eixo, em px, a partir do nut.

        Args:
            ponto: ponto ``(2,)`` do quadro.

        Returns:
            ``(ponto - nut) . u``.
        """
        return float(np.dot(ponto - self.nut, self.u))

    def no_eixo(self, t: float) -> np.ndarray:
        """Ponto do eixo na posição ``t``, a partir do nut.

        Args:
            t: posição em px, a partir do nut.

        Returns:
            Ponto ``(2,)`` sobre o eixo.
        """
        projecao_do_nut = self.origem + float(
            np.dot(self.nut - self.origem, self.u)
        ) * (self.u)
        return projecao_do_nut + t * self.u


def _f(valor: float | None) -> float | None:
    """Número finito arredondado a 6 casas, ou ``None``.

    Args:
        valor: medida, ou ``None``.

    Returns:
        ``round(valor, 6)``, ou ``None`` se o valor não for finito.
    """
    if valor is None or not math.isfinite(float(valor)):
        return None
    return round(float(valor), 6)


def _cruz(a: np.ndarray, b: np.ndarray) -> float:
    """Produto vetorial 2D (o escalar ``a x b``).

    Args:
        a: vetor ``(2,)``.
        b: vetor ``(2,)``.

    Returns:
        ``a[0]*b[1] - a[1]*b[0]``.
    """
    return float(a[0] * b[1] - a[1] * b[0])


def _distancia_a_reta(p: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    """Distância perpendicular de um ponto à reta que passa por ``a`` e ``b``.

    Args:
        p: ponto ``(2,)``.
        a: primeiro ponto da reta.
        b: segundo ponto da reta.

    Returns:
        Distância em px, sem sinal.
    """
    d = b - a
    return float(abs(_cruz(d, p - a)) / np.linalg.norm(d))


def _s_de_t(t: float, params: np.ndarray) -> float:
    """Inverte o modelo projetivo: a posição ``s`` na escala de um ponto ``t``.

    Args:
        t: posição em px, a partir do nut, sobre o eixo.
        params: ``[a, b, c]`` do ajuste ``proj`` (``t = (a*s + b) / (c*s + 1)``).

    Returns:
        ``(t - b) / (a - c*t)``, ou NaN se o denominador for zero.
    """
    a, b, c = (float(x) for x in params)
    denominador = a - c * t
    if abs(denominador) < 1e-12:
        return float("nan")
    return (t - b) / denominador


def _t_de_s(s: float, params: np.ndarray) -> float:
    """Posição ``t`` de uma escala ``s`` pelo modelo projetivo.

    Args:
        s: fração da escala (0 no nut, 1 no saddle).
        params: ``[a, b, c]`` do ajuste ``proj``.

    Returns:
        ``(a*s + b) / (c*s + 1)``, em px a partir do nut.
    """
    a, b, c = (float(x) for x in params)
    return (a * s + b) / (c * s + 1.0)


def _ponto_int(ponto: np.ndarray) -> tuple[int, int]:
    """Ponto arredondado para o OpenCV.

    Args:
        ponto: ponto ``(2,)``.

    Returns:
        ``(x, y)`` inteiros.
    """
    return (round(float(ponto[0])), round(float(ponto[1])))


def _pontos_de(valor: object) -> np.ndarray | None:
    """Pontos de um campo do gabarito, se for uma lista (senão ``oculto``).

    Args:
        valor: o campo (``boca``, ``cavalete``...), como está no gabarito.

    Returns:
        Array ``(n, 2)``, ou ``None`` se o campo não é uma lista de pontos.
    """
    if not isinstance(valor, list):
        return None
    return np.asarray(valor, dtype=float).reshape(-1, 2)


def _saddles_do_registro(registro: dict) -> dict[str, np.ndarray]:
    """Saddles 1 e 6 que têm ponto (os ``oculto`` ficam de fora).

    Args:
        registro: resposta do quadro no gabarito.

    Returns:
        ``{"saddle1": ponto, ...}`` só com os saddles marcados.
    """
    saddles: dict[str, np.ndarray] = {}
    for nome in NOMES_SADDLE:
        valor = registro.get(nome)
        if isinstance(valor, list) and len(valor) == 2:
            saddles[nome] = np.asarray(valor, dtype=float)
    return saddles


def eixo_do_quadro(marcas: Marcas) -> Eixo:
    """Eixo do quadro, orientado para o corpo (a média dos trastes fica do lado oposto).

    Args:
        marcas: marcas do quadro, com a pestana.

    Returns:
        O eixo, com ``nut`` = pestana.

    Raises:
        ValueError: se o quadro não tem a pestana (nut fora).
    """
    if marcas.nut is None:
        raise ValueError("o molde precisa da pestana no quadro")
    origem, u = eixo_do_braco(marcas.corda1.tolist(), marcas.corda6.tolist())
    media = np.mean(np.stack(list(marcas.trastes.values())), axis=0)
    if float(np.dot(media - marcas.nut, u)) < 0.0:
        u = -u
    return Eixo(nut=marcas.nut, origem=origem, u=u)


def _cordas_em(marcas: Marcas, t: float, eixo: Eixo) -> tuple[np.ndarray, np.ndarray]:
    """Pontos das cordas 1 e 6 sobre a perpendicular ao eixo em ``t``.

    Como os dois pontos ficam na mesma perpendicular, a diferença entre eles é o vão
    de 5 intervalos naquele ponto do braço.

    Args:
        marcas: marcas do quadro.
        t: posição em px, a partir do nut.
        eixo: eixo do quadro.

    Returns:
        ``(q1, q6)``: o ponto da corda 1 e o da corda 6.

    Raises:
        ValueError: se uma corda é paralela ao eixo (não há cruzamento).
    """
    pontos = []
    for corda in (marcas.corda1, marcas.corda6):
        d = corda[1] - corda[0]
        d = d / float(np.linalg.norm(d))
        if abs(float(np.dot(d, eixo.u))) < 1e-9:
            raise ValueError("corda paralela ao eixo")
        lam = (t - eixo.t(corda[0])) / float(np.dot(d, eixo.u))
        pontos.append(corda[0] + lam * d)
    return pontos[0], pontos[1]


def ajustar_projetivo(marcas: Marcas, eixo: Eixo) -> tuple[np.ndarray, float]:
    """Ajusta o modelo projetivo nos trastes, com o nut como número 0.

    Args:
        marcas: marcas do quadro (trastes numerados, pestana no quadro).
        eixo: eixo do quadro.

    Returns:
        ``(params, resid_max)``: ``[a, b, c]`` e o maior resíduo, em px, nos trastes.
    """
    pontos = [(0, 0.0)] + [
        (numero, eixo.t(ponto)) for numero, ponto in sorted(marcas.trastes.items())
    ]
    params = ajustar(pontos, "proj")
    resid = max(abs(prever(params, "proj", n) - t) for n, t in pontos[1:])
    return params, float(resid)


def contexto(marcas: Marcas) -> tuple[Eixo, np.ndarray, float]:
    """Eixo, ajuste projetivo e resíduo de um quadro.

    Args:
        marcas: marcas do quadro, com a pestana.

    Returns:
        ``(eixo, params, resid_max)``.
    """
    eixo = eixo_do_quadro(marcas)
    params, resid = ajustar_projetivo(marcas, eixo)
    return eixo, params, resid


def medir_retidao(
    marcas: Marcas, eixo: Eixo, saddles: dict[str, np.ndarray]
) -> dict | None:
    """Quanto cada saddle se afasta da reta da corda dele, em px e em vãos.

    O vão no saddle é ``|saddle1 - saddle6| / 5`` quando os dois são pontos. Com um só,
    usa-se o vão local no ``t`` desse saddle.

    Args:
        marcas: marcas do quadro.
        eixo: eixo do quadro.
        saddles: saddles marcados (``_saddles_do_registro``).

    Returns:
        Medidas por saddle e ``vaos_max`` (o pior dos saddles), ou ``None`` sem saddle.
    """
    if not saddles:
        return None
    if len(saddles) == len(NOMES_SADDLE):
        vao = float(np.linalg.norm(saddles["saddle1"] - saddles["saddle6"]))
        vao /= INTERVALOS_CORDAS
        fonte = "saddles"
    else:
        ponto = next(iter(saddles.values()))
        q1, q6 = _cordas_em(marcas, eixo.t(ponto), eixo)
        vao = float(np.linalg.norm(q6 - q1)) / INTERVALOS_CORDAS
        fonte = "local"
    medidas: dict = {"vao_px": _f(vao), "vao_fonte": fonte}
    for nome, ponto in saddles.items():
        corda = marcas.corda1 if nome == "saddle1" else marcas.corda6
        px = _distancia_a_reta(ponto, corda[0], corda[1])
        medidas[nome] = {"px": _f(px), "vaos": _f(px / vao)}
    medidas["vaos_max"] = _f(max(medidas[nome]["vaos"] for nome in saddles))
    return medidas


def medir_saddle(
    eixo: Eixo, params: np.ndarray, saddles: dict[str, np.ndarray]
) -> dict | None:
    """Onde o saddle cai na escala pela regra das 12 notas com perspectiva.

    Usa o ponto médio entre os saddles marcados, projetado no eixo. Com um só saddle,
    usa esse.

    Args:
        eixo: eixo do quadro.
        params: ``[a, b, c]`` do ajuste projetivo.
        saddles: saddles marcados.

    Returns:
        ``s_saddle``, ``t_px`` e ``usado``, ou ``None`` sem saddle.
    """
    if not saddles:
        return None
    ponto_medio = np.mean(np.stack(list(saddles.values())), axis=0)
    t = eixo.t(ponto_medio)
    usado = "+".join(saddles) if len(saddles) > 1 else next(iter(saddles))
    return {"s_saddle": _f(_s_de_t(t, params)), "t_px": _f(t), "usado": usado}


def ajustar_elipse(
    pontos: np.ndarray,
) -> tuple[tuple[float, float], tuple[float, float], float]:
    """Elipse de ``cv2.fitEllipse`` nos pontos da boca.

    Args:
        pontos: array ``(n, 2)`` com ``n >= 5``.

    Returns:
        ``((cx, cy), (eixo_1, eixo_2), angulo)``, no formato ``RotatedRect``: os
        eixos são o comprimento completo, não o semieixo.
    """
    box = cv2.fitEllipse(pontos.reshape(-1, 1, 2).astype(np.float32))
    (cx, cy), (w, h), angulo = box
    return (float(cx), float(cy)), (float(w), float(h)), float(angulo)


def cobertura_do_arco(pontos: np.ndarray, centro: tuple[float, float]) -> float:
    """Graus em volta do centro que os pontos cobrem.

    É 360 menos o maior vão angular entre pontos vizinhos, em volta do centro.

    Args:
        pontos: array ``(n, 2)`` da boca.
        centro: centro da elipse ajustada.

    Returns:
        Cobertura em graus (de 0 a 360).
    """
    angulos = np.sort(np.arctan2(pontos[:, 1] - centro[1], pontos[:, 0] - centro[0]))
    vaos = np.diff(np.append(angulos, angulos[0] + 2.0 * np.pi))
    return float(360.0 - math.degrees(float(vaos.max())))


def elipse_absurda(
    centro: tuple[float, float],
    eixos: tuple[float, float],
    dimensoes: tuple[int, int],
) -> bool:
    """Se a elipse ajustada não pode ser a boca do violão.

    É absurda quando não é finita, tem eixo nulo, tem razão entre eixos acima de
    ``RAZAO_ELIPSE_ABSURDA``, tem eixo maior que o dobro da imagem ou o centro fica
    mais de uma imagem fora do quadro.

    Args:
        centro: centro da elipse, em px do quadro.
        eixos: comprimentos completos dos eixos.
        dimensoes: ``(largura, altura)`` do quadro.

    Returns:
        True se a elipse é absurda.
    """
    largura, altura = dimensoes
    w, h = eixos
    if not all(math.isfinite(v) for v in (*centro, w, h)) or min(w, h) <= 0.0:
        return True
    if max(w, h) / min(w, h) > RAZAO_ELIPSE_ABSURDA:
        return True
    if max(w, h) > 2.0 * max(largura, altura):
        return True
    cx, cy = centro
    return not (-largura <= cx <= 2 * largura and -altura <= cy <= 2 * altura)


def medir_boca(
    marcas: Marcas,
    eixo: Eixo,
    params: np.ndarray,
    pontos: np.ndarray,
    dimensoes: tuple[int, int],
) -> dict:
    """Elipse da boca: centro, s do centro, deslocamento lateral e cobertura do arco.

    O deslocamento lateral é o do centro em relação ao ponto médio entre as cordas 1 e
    6 no mesmo ``t``, em vãos locais. Positivo quer dizer para o lado da corda 6.

    Args:
        marcas: marcas do quadro.
        eixo: eixo do quadro.
        params: ``[a, b, c]`` do ajuste projetivo.
        pontos: pontos da boca, ``(n, 2)`` com ``n >= 5``.
        dimensoes: ``(largura, altura)`` do quadro.

    Returns:
        Medidas da boca, com ``arco_parcial`` (cobertura abaixo de 180 graus).
    """
    box = ajustar_elipse(pontos)
    centro, eixos, angulo = box
    c = np.asarray(centro, dtype=float)
    t = eixo.t(c)
    q1, q6 = _cordas_em(marcas, t, eixo)
    span = float(np.linalg.norm(q6 - q1))
    lateral_px = float(np.dot(c - (q1 + q6) / 2.0, (q6 - q1) / span))
    cobertura = cobertura_do_arco(pontos, centro)
    return {
        "centro": [_f(centro[0]), _f(centro[1])],
        "eixos": [_f(eixos[0]), _f(eixos[1])],
        "angulo": _f(angulo),
        "n_pontos": len(pontos),
        "t_px": _f(t),
        "s_boca": _f(_s_de_t(t, params)),
        "lateral_px": _f(lateral_px),
        "lateral_vaos": _f(lateral_px / (span / INTERVALOS_CORDAS)),
        "cobertura_graus": _f(cobertura),
        "arco_parcial": bool(cobertura < 180.0),
        "elipse_absurda": elipse_absurda(centro, eixos, dimensoes),
    }


def medir_cavalete(
    eixo: Eixo, params: np.ndarray, pontos: np.ndarray | None
) -> dict | None:
    """Onde a reta do cavalete cruza o eixo, em s.

    Os 2 pontos dão a reta do cavalete (1008): não são as pontas físicas dele.

    Args:
        eixo: eixo do quadro.
        params: ``[a, b, c]`` do ajuste projetivo.
        pontos: os 2 pontos do cavalete, ou ``None`` se estiver oculto.

    Returns:
        ``s_cavalete`` e ``t_px``, ou ``None`` sem cavalete. Com reta paralela ao
        eixo, ``s_cavalete`` sai ``None`` e o motivo vai junto.
    """
    if pontos is None or len(pontos) != 2:
        return None
    p0, p1 = pontos[0], pontos[1]
    d = p1 - p0
    cruz_du = _cruz(d, eixo.u)
    if abs(cruz_du) < 1e-9 * float(np.linalg.norm(d)):
        return {"s_cavalete": None, "t_px": None, "motivo": "reta paralela ao eixo"}
    lam = -_cruz(p0 - eixo.origem, eixo.u) / cruz_du
    x = p0 + lam * d
    t = eixo.t(x)
    return {"s_cavalete": _f(_s_de_t(t, params)), "t_px": _f(t), "motivo": None}


def motivo_de_fora(registro: dict) -> str | None:
    """Por que o quadro fica de fora das medidas que cruzam braço e corpo.

    Args:
        registro: resposta do quadro no gabarito.

    Returns:
        O motivo, ou ``None`` se o quadro entra.
    """
    if registro.get("paineis") != "nao":
        return MOTIVO_PAINEIS
    if not isinstance(registro.get("nut"), list):
        return MOTIVO_NUT_FORA
    return None


def medir_quadro(
    qid: str, registro: dict, canal: str, dimensoes: tuple[int, int]
) -> dict:
    """Entrada do ``molde.json`` para um quadro: motivo de fora ou as medidas.

    Args:
        qid: id do quadro (``qNN``).
        registro: resposta do quadro no gabarito.
        canal: canal do vídeo (``indice.json``).
        dimensoes: ``(largura, altura)`` do quadro original.

    Returns:
        Dicionário com ``id``, ``canal``, ``dentro``, ``motivo_fora`` e ``medidas``
        (``None`` para os quadros de fora).
    """
    entrada: dict = {
        "id": qid,
        "canal": canal,
        "dentro": False,
        "motivo_fora": None,
        "medidas": None,
    }
    marcas = marcas_do_registro(registro)
    if marcas is None:
        entrada["motivo_fora"] = MOTIVO_SEM_BRACO
        return entrada
    motivo = motivo_de_fora(registro)
    if motivo is not None:
        entrada["motivo_fora"] = motivo
        return entrada
    eixo, params, resid = contexto(marcas)
    saddles = _saddles_do_registro(registro)
    boca = _pontos_de(registro.get("boca"))
    medida_boca = None
    if boca is not None and len(boca) >= PONTOS_ELIPSE:
        medida_boca = medir_boca(marcas, eixo, params, boca, dimensoes)
    entrada["dentro"] = True
    entrada["medidas"] = {
        "trastes_marcados": len(marcas.trastes),
        "maior_traste": max(marcas.trastes),
        "ajuste_proj": {
            "a": _f(params[0]),
            "b": _f(params[1]),
            "c": _f(params[2]),
            "resid_max_px": _f(resid),
        },
        "retidao": medir_retidao(marcas, eixo, saddles),
        "saddle": medir_saddle(eixo, params, saddles),
        "boca": medida_boca,
        "cavalete": medir_cavalete(eixo, params, _pontos_de(registro.get("cavalete"))),
    }
    return entrada


def _estatisticas(valores: list[float | None]) -> dict:
    """Quantidade, mediana, mínimo e máximo dos valores que não são ``None``.

    Args:
        valores: medidas por quadro (``None`` onde não houve medida).

    Returns:
        ``{"n", "mediana", "minimo", "maximo"}``.
    """
    limpos = [float(v) for v in valores if v is not None]
    if not limpos:
        return {"n": 0, "mediana": None, "minimo": None, "maximo": None}
    return {
        "n": len(limpos),
        "mediana": _f(float(np.median(limpos))),
        "minimo": _f(min(limpos)),
        "maximo": _f(max(limpos)),
    }


def _valores_do_canal(dentro: list[dict], chave: str) -> list[float | None]:
    """Valores de uma medida, por quadro, para o resumo do canal.

    Args:
        dentro: entradas com ``dentro`` verdadeiro, do canal.
        chave: nome da medida (``CAMPOS_RESUMO``).

    Returns:
        Um valor por quadro (``None`` onde a medida não existe).
    """
    valores: list[float | None] = []
    for entrada in dentro:
        m = entrada["medidas"]
        if chave == "retidao_vaos":
            valores.append(m["retidao"]["vaos_max"] if m["retidao"] else None)
        elif chave == "s_saddle":
            valores.append(m["saddle"]["s_saddle"] if m["saddle"] else None)
        elif chave == "s_boca":
            valores.append(m["boca"]["s_boca"] if m["boca"] else None)
        elif chave == "lateral_boca_vaos":
            valores.append(m["boca"]["lateral_vaos"] if m["boca"] else None)
        elif chave == "s_cavalete":
            cav = m["cavalete"]
            valores.append(cav["s_cavalete"] if cav else None)
        elif chave == "maior_traste":
            valores.append(m["maior_traste"])
        else:
            valores.append(m["ajuste_proj"]["resid_max_px"])
    return valores


def resumo_por_canal(entradas: list[dict]) -> dict[str, dict]:
    """Resumo das medidas por canal (quantidade, mediana, mínimo e máximo).

    Args:
        entradas: uma entrada por quadro (``medir_quadro``).

    Returns:
        ``{canal: {"quadros", "dentro", <medida>: estatisticas}}``.
    """
    resumo: dict[str, dict] = {}
    for canal in sorted({e["canal"] for e in entradas}):
        do_canal = [e for e in entradas if e["canal"] == canal]
        dentro = [e for e in do_canal if e["dentro"]]
        bloco: dict = {"quadros": len(do_canal), "dentro": len(dentro)}
        for chave in CAMPOS_RESUMO:
            bloco[chave] = _estatisticas(_valores_do_canal(dentro, chave))
        resumo[canal] = bloco
    return resumo


def _suspeitos(entradas: list[dict]) -> list[str]:
    """Quadros com valor estranho, para o relatório: retidão, s_saddle ou elipse.

    Args:
        entradas: uma entrada por quadro.

    Returns:
        Uma linha por achado, com o id do quadro.
    """
    achados: list[str] = []
    for entrada in entradas:
        if not entrada["dentro"]:
            continue
        m = entrada["medidas"]
        qid = entrada["id"]
        if m["retidao"] and m["retidao"]["vaos_max"] > LIMITE_RETIDAO_VAOS:
            achados.append(f"{qid}: retidão {m['retidao']['vaos_max']:.2f} vãos")
        s = m["saddle"]["s_saddle"] if m["saddle"] else None
        if s is not None and not FAIXA_S_SADDLE[0] <= s <= FAIXA_S_SADDLE[1]:
            achados.append(f"{qid}: s_saddle {s:.3f}")
        if m["boca"] and m["boca"]["elipse_absurda"]:
            achados.append(f"{qid}: elipse da boca absurda {m['boca']['eixos']}")
    return achados


def _linha_ate_borda(
    quadro: np.ndarray,
    a: np.ndarray,
    b: np.ndarray,
    cor: tuple[int, int, int],
    grossura: int,
) -> None:
    """Desenha a reta que passa por ``a`` e ``b`` até a borda do quadro.

    Args:
        quadro: imagem BGR, alterada em lugar.
        a: primeiro ponto da reta.
        b: segundo ponto da reta.
        cor: cor BGR.
        grossura: espessura em px.
    """
    altura, largura = quadro.shape[:2]
    d = (b - a) / float(np.linalg.norm(b - a))
    alcance = 4.0 * (largura + altura)
    p = a - alcance * d
    q = a + alcance * d
    ok, p1, p2 = cv2.clipLine((0, 0, largura, altura), _ponto_int(p), _ponto_int(q))
    if ok:
        cv2.line(quadro, p1, p2, cor, grossura)


def _texto(valor: float | None, casas: int = 3) -> str:
    """Número para o desenho e a tabela (``-`` quando não há).

    Args:
        valor: medida, ou ``None``.
        casas: casas decimais.

    Returns:
        Texto formatado.
    """
    if valor is None:
        return "-"
    return f"{valor:.{casas}f}"


def desenhar_quadro(imagem: np.ndarray, registro: dict, entrada: dict) -> np.ndarray:
    """Desenho de conferência de um quadro dentro do molde.

    Verde: as cordas 1 e 6 até a borda. Vermelho: os saddles do dono. Amarelo: o saddle
    previsto em s = 1 e os trastes previstos (de 1 até ``TRASTES_DESENHADOS``). Azul: a
    elipse da boca. Ciano: a reta do cavalete. Magenta: a pestana. Branco: os trastes
    marcados pelo dono.

    Args:
        imagem: quadro original, BGR, no tamanho do gabarito.
        registro: resposta do quadro no gabarito.
        entrada: entrada de ``medir_quadro`` (para o texto).

    Returns:
        Cópia do quadro com os traços.
    """
    marcas = marcas_do_registro(registro)
    if marcas is None:
        raise ValueError("o desenho precisa de um quadro com braço completo")
    eixo, params, _ = contexto(marcas)
    quadro = imagem.copy()
    for corda in (marcas.corda1, marcas.corda6):
        _linha_ate_borda(quadro, corda[0], corda[1], COR_CORDA, 3)
    for n in range(1, TRASTES_DESENHADOS + 1):
        q1, q6 = _cordas_em(marcas, prever(params, "proj", n), eixo)
        meio = (q1 + q6) / 2.0
        extensao = 0.7 * (q6 - q1)
        cv2.line(
            quadro,
            _ponto_int(meio - extensao),
            _ponto_int(meio + extensao),
            COR_PREVISTO,
            2,
        )
    for ponto in marcas.trastes.values():
        cv2.circle(quadro, _ponto_int(ponto), 5, COR_TRASTE, -1)
    cv2.circle(quadro, _ponto_int(marcas.nut), 10, COR_NUT, -1)
    for ponto in _saddles_do_registro(registro).values():
        cv2.circle(quadro, _ponto_int(ponto), 14, COR_SADDLE, 4)
    previsto = eixo.no_eixo(_t_de_s(1.0, params))
    cv2.circle(quadro, _ponto_int(previsto), 26, COR_PREVISTO, 4)
    boca = _pontos_de(registro.get("boca"))
    if boca is not None and len(boca) >= PONTOS_ELIPSE:
        cv2.ellipse(quadro, ajustar_elipse(boca), COR_BOCA, 3)
    cavalete = _pontos_de(registro.get("cavalete"))
    if cavalete is not None and len(cavalete) == 2:
        _linha_ate_borda(quadro, cavalete[0], cavalete[1], COR_CAVALETE, 3)
    medidas = entrada["medidas"]
    s = medidas["saddle"]["s_saddle"] if medidas["saddle"] else None
    ret = medidas["retidao"]["vaos_max"] if medidas["retidao"] else None
    texto = (
        f"{entrada['id']}  s_saddle={_texto(s)}  "
        f"retidao={_texto(ret, 2)} vaos  resid={_texto(medidas['ajuste_proj']['resid_max_px'], 2)}px"
    )
    for cor, grossura in (((0, 0, 0), 6), ((255, 255, 255), 2)):
        cv2.putText(
            quadro,
            texto,
            (24, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            cor,
            grossura,
            cv2.LINE_AA,
        )
    return quadro


def _reduzir(imagem: np.ndarray) -> np.ndarray:
    """Reduz o desenho para ``LARGURA_DESENHO`` de largura, se for mais largo.

    Args:
        imagem: desenho BGR.

    Returns:
        A imagem reduzida, ou a própria imagem se já é estreita.
    """
    altura, largura = imagem.shape[:2]
    if largura <= LARGURA_DESENHO:
        return imagem
    nova_altura = round(altura * LARGURA_DESENHO / largura)
    return cv2.resize(
        imagem, (LARGURA_DESENHO, nova_altura), interpolation=cv2.INTER_AREA
    )


def _imprimir(entradas: list[dict], resumo: dict[str, dict]) -> None:
    """Tabela por quadro, lista de fora, suspeitos e resumo por canal.

    Args:
        entradas: uma entrada por quadro.
        resumo: saída de ``resumo_por_canal``.
    """
    cabeca = (
        f"{'quadro':7}{'canal':18}{'ret_v':>7}{'s_sad':>8} {'usado':15}"
        f"{'s_boca':>8}{'lat_v':>7}{'arco':>6}{'s_cav':>8}{'t_max':>6}{'resid':>7}"
    )
    print(cabeca)
    for e in entradas:
        if not e["dentro"]:
            continue
        m = e["medidas"]
        ret = m["retidao"]["vaos_max"] if m["retidao"] else None
        saddle = m["saddle"]
        boca = m["boca"]
        cav = m["cavalete"]
        print(
            f"{e['id']:7}{e['canal'][:17]:18}"
            f"{_texto(ret, 2):>7}"
            f"{_texto(saddle['s_saddle'] if saddle else None):>8} "
            f"{(saddle['usado'] if saddle else '-'):15}"
            f"{_texto(boca['s_boca'] if boca else None):>8}"
            f"{_texto(boca['lateral_vaos'] if boca else None, 2):>7}"
            f"{('sim' if boca and boca['arco_parcial'] else ('-' if not boca else 'nao')):>6}"
            f"{_texto(cav['s_cavalete'] if cav else None):>8}"
            f"{m['maior_traste']:>6}"
            f"{_texto(m['ajuste_proj']['resid_max_px'], 2):>7}"
        )
    print("\nFora do molde:")
    for e in entradas:
        if not e["dentro"]:
            print(f"  {e['id']} ({e['canal']}): {e['motivo_fora']}")
    print(
        "\nSuspeitos (retidão > 0,5 vão, s_saddle fora de [0,9; 1,1], elipse absurda):"
    )
    suspeitos = _suspeitos(entradas)
    for linha in suspeitos or ["  nenhum"]:
        print(f"  {linha}")
    print("\nResumo por canal (n, mediana, minimo, maximo):")
    for canal, bloco in resumo.items():
        print(f"  {canal}: quadros {bloco['quadros']}, dentro {bloco['dentro']}")
        for chave in CAMPOS_RESUMO:
            est = bloco[chave]
            print(
                f"    {chave:18} n={est['n']:2} med={_texto(est['mediana'])} "
                f"min={_texto(est['minimo'])} max={_texto(est['maximo'])}"
            )


def main() -> int:
    """Mede o violão molde nas marcas do gabarito do braço e grava o ``molde.json``.

    Returns:
        Código de saída (0).
    """
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    gabarito = json.loads(GABARITO_BRACO.read_text(encoding="utf-8"))
    indice = json.loads((MAOS_M3B / "indice.json").read_text(encoding="utf-8"))
    por_id = {item["id"]: item for item in indice["quadros"]}
    quadros = gabarito["quadros"]
    entradas = []
    for qid in sorted(quadros):
        item = por_id[qid]
        entradas.append(
            medir_quadro(
                qid, quadros[qid], item["canal"], (item["largura"], item["altura"])
            )
        )
    pasta = MAOS_M11 / "molde"
    desenhos = pasta / "desenhos"
    desenhos.mkdir(parents=True, exist_ok=True)
    for entrada in entradas:
        if not entrada["dentro"]:
            continue
        qid = entrada["id"]
        imagem = cv2.imread(str(MAOS_M3B_QUADROS / f"{qid}.png"))
        if imagem is None:
            raise FileNotFoundError(f"quadro sem imagem: {qid}")
        desenho = desenhar_quadro(imagem, quadros[qid], entrada)
        cv2.imwrite(
            str(desenhos / f"{qid}.jpg"),
            _reduzir(desenho),
            [cv2.IMWRITE_JPEG_QUALITY, 88],
        )
    resumo = resumo_por_canal(entradas)
    documento = {
        "formato": FORMATO_MOLDE,
        "gabarito": GABARITO_BRACO.name,
        "regras": {
            "vao": "distancia entre as cordas 1 e 6 / 5",
            "t": "projecao no eixo, em px, a partir do nut (positivo para o corpo)",
            "s": "inversa do modelo projetivo dos trastes, com o nut como 0",
            "retidao": "distancia do saddle a reta da corda, em vaos no saddle",
            "boca": "cv2.fitEllipse; eixos sao comprimentos completos",
            "lateral": "centro da boca contra o ponto medio das cordas 1 e 6 no mesmo t, em vaos locais, positivo para a corda 6",
        },
        "quadros": entradas,
        "resumo_por_canal": resumo,
    }
    (pasta / "molde.json").write_text(
        json.dumps(documento, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _imprimir(entradas, resumo)
    print(f"\ngravado: {pasta / 'molde.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

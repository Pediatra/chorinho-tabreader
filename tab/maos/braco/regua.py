"""Rodada 1040: régua de casas, a razão largura da casa ÷ abertura das cordas.

Em cada casa n (entre os trastes n − 1 e n; o traste 0 é o nut), mede a largura ao longo do
eixo e a abertura entre as retas da corda 1 e da corda 6 no meio da casa. A razão
``r = largura / abertura`` cai ~7 % por casa: ~5,6 % porque a casa encolhe (2^(−1/12)), e o
resto porque as cordas se abrem para o corpo.

Medidas, nas marcas do dono (pré-registro ``docs/rodadas/1040-regua-de-casas-sem-nut.md``):

- (a) por vídeo, deixando um quadro de fora: a reta log r = α − β·n dos outros quadros
  escolhe o deslocamento da numeração do quadro de fora;
- (b) sem calibração, deixando o vídeo de fora, com a casa real (capo somado);
- (c) o ruído de log r em torno da reta do vídeo, contra o passo β.

CLI: ``python -m tab.maos_braco_regua`` grava ``data/saida/maos/m40/regua.json``.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import numpy as np

from tab.comum.arquivos import nfc as _nfc
from tab.comum.caminhos import (
    GABARITO_BRACO,
    GABARITO_BRACO_M11B,
    GABARITO_BRACO_M25_PROVA,
    GABARITO_BRACO_M26,
    GABARITO_BRACO_M27,
    GABARITO_BRACO_M29,
    GABARITO_BRACO_M32,
    GABARITO_BRACO_M36,
    MAOS_M3B,
    MAOS_M11B,
    MAOS_M25,
    MAOS_M26,
    MAOS_M27,
    MAOS_M29,
    MAOS_M32,
    MAOS_M36,
    MAOS_M40,
)
from tab.maos.braco.capo import ARQUIVO_SAIDA as ARQUIVO_CAPO
from tab.maos.braco.geometria import eixo_do_braco
from tab.maos.braco.tempo import Marcas, marcas_do_registro
from tab.maos.gabarito import gravar_atomico

#: Gabaritos com marcas completas: (nome curto, ouro, pasta com ``indice.json``).
GABARITOS = (
    ("m3b", GABARITO_BRACO, MAOS_M3B),
    ("m11b", GABARITO_BRACO_M11B, MAOS_M11B),
    ("n", GABARITO_BRACO_M25_PROVA, MAOS_M25 / "prova"),
    ("m26", GABARITO_BRACO_M26, MAOS_M26),
    ("m27", GABARITO_BRACO_M27, MAOS_M27),
    ("m29", GABARITO_BRACO_M29, MAOS_M29),
    ("m32", GABARITO_BRACO_M32, MAOS_M32),
    ("m36", GABARITO_BRACO_M36, MAOS_M36),
)
#: Quadros que a 1037 tirou até o dono confirmar.
EXCLUIDOS = {"m3b": {"q10"}, "m32": {"q14", "q45"}}
#: Deslocamentos testados na numeração do quadro.
DESLOCAMENTOS = (-2, -1, 0, 1, 2)
#: Mínimos do pré-registro: casas por quadro e quadros por grupo.
MINIMO_CASAS = 3
MINIMO_QUADROS = 3
ARQUIVO_SAIDA = MAOS_M40 / "regua.json"


def _reta_cruza(
    ponto: np.ndarray, direcao: np.ndarray, p: np.ndarray, d: np.ndarray
) -> float:
    """Parâmetro ``a`` em que ``ponto + a·direcao`` cruza a reta ``p + b·d``.

    Args:
        ponto: ponto da reta de corte.
        direcao: direção da reta de corte.
        p: ponto da outra reta.
        d: direção da outra reta.

    Returns:
        O parâmetro ``a``.
    """
    matriz = np.column_stack([direcao, -d])
    a, _ = np.linalg.solve(matriz, p - ponto)
    return float(a)


def abertura(marcas: Marcas, ponto: np.ndarray, u: np.ndarray) -> float:
    """Distância entre as retas da corda 1 e da corda 6, no corte perpendicular ao eixo.

    Args:
        marcas: marcas do quadro (``corda1`` e ``corda6`` com 2 pontos).
        ponto: ponto do eixo onde se corta.
        u: vetor unitário do eixo.

    Returns:
        A abertura, em px.
    """
    v = np.array([-u[1], u[0]])
    cortes = []
    for corda in (marcas.corda1, marcas.corda6):
        c = np.asarray(corda, dtype=float)
        cortes.append(_reta_cruza(ponto, v, c[0], c[1] - c[0]))
    return abs(cortes[0] - cortes[1])


def casas_do_quadro(marcas: Marcas) -> list[tuple[int, float]]:
    """As casas com os dois trastes marcados e a razão de cada uma.

    Args:
        marcas: marcas do quadro, com o nut.

    Returns:
        ``(n, r)`` por casa, em ordem de n. Vazio sem nut.
    """
    if marcas.nut is None or not marcas.trastes:
        return []
    nut = np.asarray(marcas.nut, dtype=float)
    _, u = eixo_do_braco(marcas.corda1.tolist(), marcas.corda6.tolist())
    media = np.mean(
        [np.asarray(p, dtype=float) for p in marcas.trastes.values()], axis=0
    )
    if float(np.dot(media - nut, u)) < 0.0:
        u = -u
    posicao = {0: 0.0}
    for numero, ponto in marcas.trastes.items():
        posicao[int(numero)] = float(np.dot(np.asarray(ponto, dtype=float) - nut, u))
    casas = []
    for n in sorted(posicao):
        if n == 0 or n - 1 not in posicao:
            continue
        largura = posicao[n] - posicao[n - 1]
        if largura <= 0.0:
            continue
        meio = nut + u * (posicao[n] + posicao[n - 1]) / 2.0
        casas.append((n, largura / abertura(marcas, meio, u)))
    return casas


def ajustar(pontos: list[tuple[float, float]]) -> tuple[float, float]:
    """Reta log r = α − β·n por mínimos quadrados.

    Args:
        pontos: ``(n, r)``.

    Returns:
        ``(alfa, beta)``.
    """
    n = np.array([p[0] for p in pontos], dtype=float)
    y = np.log([p[1] for p in pontos])
    inclinacao, alfa = np.polyfit(n, y, 1)
    return float(alfa), float(-inclinacao)


def melhor_deslocamento(
    casas: list[tuple[int, float]], alfa: float, beta: float
) -> tuple[int, float]:
    """O deslocamento da numeração que melhor encaixa as casas do quadro na reta.

    Args:
        casas: ``(n, r)`` do quadro.
        alfa: α da reta.
        beta: β da reta.

    Returns:
        ``(s, margem)``: o deslocamento escolhido e a diferença de erro quadrático médio
        para o segundo melhor.
    """
    erros = {}
    for s in DESLOCAMENTOS:
        residuos = [np.log(r) - (alfa - beta * (n + s)) for n, r in casas]
        erros[s] = float(np.mean(np.square(residuos)))
    ordem = sorted(erros, key=erros.get)
    return ordem[0], erros[ordem[1]] - erros[ordem[0]]


def quadros() -> list[dict]:
    """Os quadros utilizáveis, com as casas, o vídeo e a casa do capo.

    Returns:
        Um dicionário por quadro: ``id``, ``video``, ``capo`` (bool), ``casa_capo``
        (int ou None) e ``casas`` (``(n, r)``).
    """
    capos = {
        _nfc(v["arquivo"]): v["casa"]
        for v in json.loads(ARQUIVO_CAPO.read_text(encoding="utf-8"))["videos"]
    }
    lista = []
    for nome, ouro, pasta in GABARITOS:
        registros = json.loads(Path(ouro).read_text(encoding="utf-8"))["quadros"]
        indice = json.loads((pasta / "indice.json").read_text(encoding="utf-8"))
        arquivos = {q["id"]: _nfc(q["arquivo"]) for q in indice["quadros"]}
        for id_q, registro in registros.items():
            if id_q in EXCLUIDOS.get(nome, set()) or registro.get("braco") != "sim":
                continue
            marcas = marcas_do_registro(registro)
            if marcas is None or marcas.nut is None:
                continue
            casas = casas_do_quadro(marcas)
            if len(casas) < MINIMO_CASAS:
                continue
            com_capo = isinstance(registro.get("capo"), list)
            lista.append(
                {
                    "id": f"{nome}:{id_q}",
                    "video": arquivos[id_q],
                    "capo": com_capo,
                    "casa_capo": capos.get(arquivos[id_q]) if com_capo else 0,
                    "casas": casas,
                }
            )
    return lista


def calibrada_por_video(lista: list[dict]) -> dict:
    """Medida (a): reta dos outros quadros do mesmo vídeo e regime de capo.

    Args:
        lista: saída de ``quadros``.

    Returns:
        ``medidos``, ``acertos``, ``por_deslocamento`` e ``quadros`` (id, s, margem).
    """
    grupos: dict[tuple[str, bool], list[dict]] = {}
    for q in lista:
        grupos.setdefault((q["video"], q["capo"]), []).append(q)
    linhas = []
    for grupo in grupos.values():
        if len(grupo) < MINIMO_QUADROS:
            continue
        for q in grupo:
            outros = [c for o in grupo if o is not q for c in o["casas"]]
            alfa, beta = ajustar(outros)
            s, margem = melhor_deslocamento(q["casas"], alfa, beta)
            linhas.append({"id": q["id"], "s": s, "margem": round(margem, 5)})
    return _resumo(linhas)


def sem_calibracao(lista: list[dict]) -> dict:
    """Medida (b): uma reta dos outros vídeos, com a casa real.

    Args:
        lista: saída de ``quadros``.

    Returns:
        ``medidos``, ``acertos``, ``por_deslocamento`` e ``quadros``.
    """
    reais = [q for q in lista if q["casa_capo"] is not None]
    linhas = []
    for q in reais:
        outros = [
            (n + o["casa_capo"], r)
            for o in reais
            if o["video"] != q["video"]
            for n, r in o["casas"]
        ]
        alfa, beta = ajustar(outros)
        casas = [(n + q["casa_capo"], r) for n, r in q["casas"]]
        s, margem = melhor_deslocamento(casas, alfa, beta)
        linhas.append({"id": q["id"], "s": s, "margem": round(margem, 5)})
    return _resumo(linhas)


def ruido(lista: list[dict]) -> dict:
    """Medida (c): desvio de log r em torno da reta de cada grupo, contra o passo β.

    Args:
        lista: saída de ``quadros``.

    Returns:
        Medianas do desvio e de β nos grupos com o mínimo de quadros.
    """
    grupos: dict[tuple[str, bool], list[dict]] = {}
    for q in lista:
        grupos.setdefault((q["video"], q["capo"]), []).append(q)
    desvios, betas = [], []
    for grupo in grupos.values():
        if len(grupo) < MINIMO_QUADROS:
            continue
        pontos = [c for q in grupo for c in q["casas"]]
        alfa, beta = ajustar(pontos)
        residuos = [np.log(r) - (alfa - beta * n) for n, r in pontos]
        desvios.append(float(np.std(residuos)))
        betas.append(beta)
    return {
        "grupos": len(desvios),
        "desvio_mediano": round(statistics.median(desvios), 4) if desvios else None,
        "beta_mediano": round(statistics.median(betas), 4) if betas else None,
    }


def _resumo(linhas: list[dict]) -> dict:
    """Contagem de acertos (s = 0) e de cada deslocamento.

    Args:
        linhas: ``id``, ``s`` e ``margem`` por quadro.

    Returns:
        ``medidos``, ``acertos``, ``por_deslocamento`` e ``quadros``.
    """
    por: dict[str, int] = {}
    for linha in linhas:
        por[str(linha["s"])] = por.get(str(linha["s"]), 0) + 1
    return {
        "medidos": len(linhas),
        "acertos": sum(1 for linha in linhas if linha["s"] == 0),
        "por_deslocamento": dict(sorted(por.items(), key=lambda kv: int(kv[0]))),
        "quadros": linhas,
    }


def medir() -> dict:
    """As três medidas, gravadas em ``regua.json``.

    Returns:
        ``quadros_utilizaveis``, ``a``, ``b`` e ``c``.
    """
    lista = quadros()
    resultado = {
        "quadros_utilizaveis": len(lista),
        "a": calibrada_por_video(lista),
        "b": sem_calibracao(lista),
        "c": ruido(lista),
    }
    gravar_atomico(ARQUIVO_SAIDA, resultado)
    return resultado


def main() -> int:
    """Ponto de entrada da CLI.

    Returns:
        0 ao terminar.
    """
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    resultado = medir()
    for chave in ("a", "b"):
        m = resultado[chave]
        print(
            f"({chave}) acertos {m['acertos']} de {m['medidos']}; "
            f"deslocamentos {m['por_deslocamento']}"
        )
    print(f"(c) {resultado['c']}; quadros {resultado['quadros_utilizaveis']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

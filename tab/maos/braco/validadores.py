"""Rodada 1044: validadores físicos, várias tentativas e um violão por tomada (CPU).

- **A. Validadores**: medidas físicas das marcas de um quadro (escada dos trastes, largura do
  braço em milímetros pela escala de 650 mm, alargamento para o corpo, cordas, primeiro
  degrau do nut). As faixas saem das marcas do dono no desenvolvimento (≥ 98 % aprovadas).
- **B. Tentativas**: as hipóteses (pares × original/espelho, de
  ``tab.maos.braco.validadores_gpu``) que passam nos validadores; entrega o grupo que
  concorda (≤ ¼ de casa) se ele tem ≥ 2/3 delas e ≥ 6; senão sinaliza.
- **C. Tomada**: o consenso da 1028 sobre os entregues; um quadro que discorda da tomada
  (k ≠ 0 ou "sem decisão" com referência) é sinalizado (S4b).

Pré-registro: ``docs/rodadas/1044-validadores-tentativas-e-tomada.md``.

CLI (``python -m tab.maos.braco.validadores``): ``faixas`` (no desenvolvimento) e
``medir --rodada N``.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import statistics
import sys
from pathlib import Path

import numpy as np

from tab.comum.arquivos import gravar_atomico
from tab.comum.caminhos import GABARITO_BRACO_M43, GABARITO_BRACO_M44, MAOS_M44
from tab.maos.braco.ciclo import RODADAS, aplicar_consenso, marcas_do_previsto
from tab.maos.braco.retreino import medir_por_grupo
from tab.maos.braco.tempo import Marcas, marcas_do_registro

#: Escala usada para levar o espaço entre trastes a milímetros.
ESCALA_MM = 650.0
#: Vão mínimo entre as cordas 1 e 6, em px (pré-registro).
VAO_MINIMO_PX = 8.0
#: Fração das marcas do dono que cada validador precisa aprovar.
APROVACAO = 0.98
#: Passo com que a faixa se alarga até aprovar ``APROVACAO`` das marcas do dono.
PASSO_FORA = 0.001
#: Concordância entre hipóteses, em casas.
TOLERANCIA_CASA = 0.25
#: Regra da B.
FRACAO_GRUPO = 2.0 / 3.0
MINIMO_GRUPO = 6
#: Pares de pesos das hipóteses: o antigo, o da 1041 e os 9 da 1042.
PARES = (
    ("L3_todos_s3", "A4_100_todos_s1"),
    ("L5_capo3_s2", "A7_capo3_s2"),
    *((f"L6_capo_s{a}", f"A8_capo_s{b}") for a in (1, 2, 3) for b in (1, 2, 3)),
)
MODOS = ("original", "espelho")
#: A hipótese de referência (o par antigo no quadro original).
REFERENCIA = (PARES[0], "original")

ARQUIVO_FAIXAS = MAOS_M44 / "faixas.json"
PASTA_HIPOTESES = MAOS_M44 / "hipoteses"
#: Gabaritos que não entram no desenvolvimento (as provas).
GABARITOS_PROVA = (GABARITO_BRACO_M43.name, GABARITO_BRACO_M44.name)


def _ler_json(caminho: Path) -> dict:
    """Lê um JSON em UTF-8.

    Args:
        caminho: arquivo.

    Returns:
        O conteúdo.
    """
    return json.loads(caminho.read_text(encoding="utf-8"))


def nome_da_hipotese(par: tuple[str, str], modo: str) -> str:
    """Nome de arquivo de uma hipótese.

    Args:
        par: (estágio 1, estágio 2).
        modo: ``original`` ou ``espelho``.

    Returns:
        ``"<e1>+<e2>_<modo>"``.
    """
    return f"{par[0]}+{par[1]}_{modo}"


def _pontos(marcas: Marcas) -> dict[int, np.ndarray]:
    """O nut (número 0, se visível) e os trastes, por número.

    Args:
        marcas: marcas de um quadro.

    Returns:
        ``{numero: ponto}``.
    """
    pontos = {int(n): np.asarray(p, dtype=float) for n, p in marcas.trastes.items()}
    if marcas.nut is not None:
        pontos[0] = np.asarray(marcas.nut, dtype=float)
    return pontos


def _cruzamento(
    origem: np.ndarray, direcao: np.ndarray, reta: np.ndarray
) -> np.ndarray:
    """O ponto em que a reta ``origem + t·direcao`` corta a reta pelos dois pontos.

    Args:
        origem: ponto ``(2,)``.
        direcao: direção ``(2,)``.
        reta: dois pontos ``(2, 2)``.

    Returns:
        O ponto, ou NaN se as retas são paralelas.
    """
    a, b = reta
    matriz = np.column_stack([direcao, a - b])
    if abs(np.linalg.det(matriz)) < 1e-9:
        return np.array([math.nan, math.nan])
    t, _ = np.linalg.solve(matriz, a - origem)
    return origem + t * direcao


def _distancia_fisica(k: int) -> float:
    """Distância física entre os trastes k e k + 1, em mm (escala ``ESCALA_MM``).

    Args:
        k: número do traste (0 = nut).

    Returns:
        A distância.
    """
    return ESCALA_MM * (2.0 ** (-k / 12.0) - 2.0 ** (-(k + 1) / 12.0))


def medidas(marcas: Marcas) -> dict[str, float | None]:
    """As medidas físicas de um quadro (None quando não há dado para medir).

    Args:
        marcas: marcas de um quadro (do dono ou previstas).

    Returns:
        ``escada`` (mediana da razão entre espaços vizinhos), ``irregular`` (maior desvio
        do log da razão para a mediana), ``largura_mm`` (mediana da largura estimada),
        ``alarga`` (largura no último ÷ no primeiro traste medido), ``vao_px`` (menor vão
        entre as cordas), ``cruzam`` (1.0 se as cordas se cruzam no braço, senão 0.0) e
        ``nut`` (primeiro degrau ÷ segundo).
    """
    pontos = _pontos(marcas)
    numeros = sorted(pontos)
    saida: dict[str, float | None] = dict.fromkeys(
        ("escada", "irregular", "largura_mm", "alarga", "vao_px", "cruzam", "nut")
    )
    if len(numeros) < 2:
        return saida
    eixo = pontos[numeros[-1]] - pontos[numeros[0]]
    if np.linalg.norm(eixo) < 1e-6:
        return saida
    eixo = eixo / np.linalg.norm(eixo)
    normal = np.array([-eixo[1], eixo[0]])
    posicao = {n: float((pontos[n] - pontos[numeros[0]]) @ eixo) for n in numeros}
    espacos = {k: posicao[k + 1] - posicao[k] for k in numeros if k + 1 in posicao}
    larguras = {}
    vaos = []
    for n in numeros:
        p1 = _cruzamento(pontos[n], normal, marcas.corda1)
        p6 = _cruzamento(pontos[n], normal, marcas.corda6)
        if np.isnan(p1).any() or np.isnan(p6).any():
            continue
        larguras[n] = float(np.linalg.norm(p1 - p6))
        vaos.append(float((p6 - p1) @ normal))
    if vaos:
        saida["vao_px"] = min(abs(v) for v in vaos)
        saida["cruzam"] = 1.0 if min(vaos) < 0 < max(vaos) else 0.0
    razoes = [
        espacos[k + 1] / espacos[k]
        for k in espacos
        if k + 1 in espacos and espacos[k] > 0 and espacos[k + 1] > 0
    ]
    if razoes:
        mediana = statistics.median(razoes)
        saida["escada"] = mediana
        saida["irregular"] = max(abs(math.log(r / mediana)) for r in razoes)
    if any(e <= 0 for e in espacos.values()):
        saida["irregular"] = math.inf
    estimadas = [
        (k, larguras[k] * _distancia_fisica(k) / espacos[k])
        for k in sorted(espacos)
        if k in larguras and espacos[k] > 0
    ]
    if estimadas:
        saida["largura_mm"] = statistics.median(v for _, v in estimadas)
    if len(estimadas) >= 2:
        saida["alarga"] = estimadas[-1][1] / estimadas[0][1]
    if 0 in espacos and 1 in espacos and espacos[1] > 0:
        saida["nut"] = espacos[0] / espacos[1]
    return saida


#: Validadores: nome -> (medida, tipo). ``faixa`` tem os dois lados; ``minimo`` e
#: ``maximo`` um só. V4 (cordas) usa limites fixos do pré-registro.
VALIDADORES = {
    "V1_alarga": ("alarga", "minimo"),
    "V2_escada": ("escada", "faixa"),
    "V2_irregular": ("irregular", "maximo"),
    "V3_largura": ("largura_mm", "faixa"),
    "V5_nut": ("nut", "faixa"),
}


def _quantil(valores: list[float], q: float) -> float:
    """Quantil linear de uma lista.

    Args:
        valores: valores finitos.
        q: entre 0 e 1.

    Returns:
        O quantil.
    """
    return float(np.quantile(np.asarray(valores, dtype=float), q))


def faixas_das_marcas(lista: list[dict[str, float | None]]) -> dict[str, dict]:
    """As faixas de cada validador pelas marcas do dono (≥ ``APROVACAO`` aprovadas).

    Args:
        lista: as ``medidas`` de cada quadro do dono.

    Returns:
        ``{validador: {"medida", "tipo", "min", "max", "aprovadas": [n, total]}}``.
    """
    faixas = {}
    for nome, (medida, tipo) in VALIDADORES.items():
        valores = [m[medida] for m in lista if m[medida] is not None]
        valores = [v for v in valores if math.isfinite(v)]
        fora = 1.0 - APROVACAO
        while True:
            faixa = _faixa(valores, medida, tipo, fora)
            aprovadas = sum(1 for m in lista if passa(m, faixa) is not False)
            if aprovadas >= APROVACAO * len(lista) or fora <= 0:
                break
            fora = max(0.0, fora - PASSO_FORA)
        faixa["aprovadas"] = [aprovadas, len(lista)]
        faixas[nome] = faixa
    return faixas


def _faixa(valores: list[float], medida: str, tipo: str, fora: float) -> dict:
    """A faixa de um validador que deixa ``fora`` dos valores de fora.

    Args:
        valores: os valores medidos nas marcas do dono.
        medida: nome da medida.
        tipo: ``faixa``, ``minimo`` ou ``maximo``.
        fora: fração deixada de fora (metade de cada lado na ``faixa``).

    Returns:
        ``{"medida", "tipo", "min", "max"}``.
    """
    minimo = maximo = None
    if tipo == "faixa":
        minimo, maximo = _quantil(valores, fora / 2), _quantil(valores, 1 - fora / 2)
    elif tipo == "minimo":
        minimo = _quantil(valores, fora)
    else:
        maximo = _quantil(valores, 1 - fora)
    return {"medida": medida, "tipo": tipo, "min": minimo, "max": maximo}


def passa(medida_quadro: dict[str, float | None], faixa: dict) -> bool | None:
    """Se uma medida está na faixa do validador.

    Args:
        medida_quadro: ``medidas`` de um quadro.
        faixa: a faixa de um validador.

    Returns:
        True ou False; None sem dado.
    """
    valor = medida_quadro[faixa["medida"]]
    if valor is None:
        return None
    if faixa["min"] is not None and not valor >= faixa["min"]:
        return False
    return not (faixa["max"] is not None and not valor <= faixa["max"])


def validar(marcas: Marcas | None, faixas: dict[str, dict]) -> dict:
    """Aplica os validadores a uma hipótese.

    Uma hipótese passa se tem a escada e a largura medidas (≥ 3 pontos seguidos), as
    cordas não se cruzam, o vão é ≥ ``VAO_MINIMO_PX`` e nenhum validador reprova.

    Args:
        marcas: marcas previstas (None se a cadeia não achou o braço).
        faixas: as faixas do desenvolvimento.

    Returns:
        ``{"passa": bool, "reprovados": [nomes]}``.
    """
    if marcas is None:
        return {"passa": False, "reprovados": ["sem braço"]}
    medida_quadro = medidas(marcas)
    reprovados = [
        nome for nome, faixa in faixas.items() if passa(medida_quadro, faixa) is False
    ]
    if medida_quadro["escada"] is None or medida_quadro["largura_mm"] is None:
        reprovados.append("sem dado")
    if medida_quadro["cruzam"] == 1.0:
        reprovados.append("V4_cruzam")
    if medida_quadro["vao_px"] is not None and medida_quadro["vao_px"] < VAO_MINIMO_PX:
        reprovados.append("V4_vao")
    return {"passa": not reprovados, "reprovados": reprovados}


def faixas() -> dict:
    """As faixas dos validadores nas marcas do dono do desenvolvimento.

    São todos os gabaritos ``braco*.json`` menos os das provas (1043 e 1044).

    Returns:
        As faixas e as fontes; também gravadas em ``ARQUIVO_FAIXAS``.
    """
    pasta = GABARITO_BRACO_M43.parent
    lista = []
    fontes = []
    for caminho in sorted(pasta.glob("braco*.json")):
        if caminho.name in GABARITOS_PROVA:
            continue
        fontes.append(caminho.name)
        for registro in _ler_json(caminho).get("quadros", {}).values():
            marcas = marcas_do_registro(registro)
            if marcas is not None:
                lista.append(medidas(marcas))
    resultado = {"fontes": fontes, "quadros": len(lista), **faixas_das_marcas(lista)}
    gravar_atomico(ARQUIVO_FAIXAS, resultado)
    return resultado


def _casa_local(pontos: dict[int, np.ndarray], n: int) -> float | None:
    """O tamanho da casa em torno do ponto n (distância ao vizinho).

    Args:
        pontos: ``{numero: ponto}``.
        n: número do ponto.

    Returns:
        A distância, ou None sem vizinho.
    """
    for vizinho in (n + 1, n - 1):
        if vizinho in pontos:
            return float(np.linalg.norm(pontos[vizinho] - pontos[n]))
    return None


def concordam(a: Marcas, b: Marcas) -> bool:
    """Se duas hipóteses dão a mesma numeração (cada ponto comum a ≤ ¼ de casa).

    Args:
        a: marcas de uma hipótese.
        b: marcas da outra.

    Returns:
        True com ≥ 3 pontos comuns e todos dentro da tolerância.
    """
    pa, pb = _pontos(a), _pontos(b)
    comuns = sorted(set(pa) & set(pb))
    if len(comuns) < 3:
        return False
    for n in comuns:
        casa = _casa_local(pa, n)
        if casa is None or np.linalg.norm(pa[n] - pb[n]) > TOLERANCIA_CASA * casa:
            return False
    return True


def escolher_hipotese(
    hipoteses: dict[str, dict], faixas_validas: dict[str, dict]
) -> dict:
    """A regra da B num quadro.

    Args:
        hipoteses: ``{nome: entrada de previsto.json}``, na ordem de ``PARES`` × ``MODOS``.
        faixas_validas: as faixas dos validadores.

    Returns:
        ``{"entregue": nome ou None, "validas": n, "grupo": n, "reprovados": {nome:
        [validadores]}}``. ``entregue`` None quer dizer sinalizar.
    """
    validas = {}
    reprovados = {}
    for nome, previsto in hipoteses.items():
        marcas = marcas_do_previsto(previsto)
        resultado = validar(marcas, faixas_validas)
        if resultado["passa"]:
            validas[nome] = marcas
        else:
            reprovados[nome] = resultado["reprovados"]
    melhor, grupo = None, 0
    for nome, marcas in validas.items():
        tamanho = sum(1 for outra in validas.values() if concordam(marcas, outra))
        if tamanho > grupo:
            melhor, grupo = nome, tamanho
    entregue = (
        melhor
        if validas and grupo >= FRACAO_GRUPO * len(validas) and grupo >= MINIMO_GRUPO
        else None
    )
    return {
        "entregue": entregue,
        "candidata": melhor,
        "validas": len(validas),
        "grupo": grupo,
        "reprovados": reprovados,
    }


def _ler_hipoteses(numero: str) -> dict[str, dict]:
    """As hipóteses gravadas pela parte GPU para uma rodada.

    Args:
        numero: rodada do ciclo.

    Returns:
        ``{nome: previsto.json}``, na ordem de ``PARES`` × ``MODOS``.
    """
    pasta = PASTA_HIPOTESES / numero
    return {
        nome_da_hipotese(par, modo): _ler_json(
            pasta / f"{nome_da_hipotese(par, modo)}.json"
        )
        for par in PARES
        for modo in MODOS
    }


def cadeia(
    numero: str, faixas_validas: dict[str, dict], tomada: bool = True
) -> tuple[dict, dict]:
    """A cadeia da 1044 (B e C) numa rodada.

    Args:
        numero: rodada do ciclo.
        faixas_validas: as faixas dos validadores.
        tomada: se True, aplica a parte C (S4b); a 1047 roda sem ela.

    Returns:
        ``(previsto, registro)``: o documento no formato de ``previsto.json`` e o
        registro por quadro (validas, grupo, reprovados, S4).
    """
    docs = _ler_hipoteses(numero)
    referencia = docs[nome_da_hipotese(*REFERENCIA)]
    indice = _ler_json(RODADAS[numero].pasta / "indice.json")
    dimensoes = {q["id"]: (q["largura"], q["altura"]) for q in indice["quadros"]}
    quadros, registro = {}, {}
    for id_q in referencia["ordem"]:
        escolha = escolher_hipotese(
            {nome: doc["quadros"][id_q] for nome, doc in docs.items()}, faixas_validas
        )
        if escolha["entregue"] is None:
            base = escolha["candidata"] or nome_da_hipotese(*REFERENCIA)
            quadro = dict(docs[base]["quadros"][id_q], sinalizado=True)
        else:
            quadro = copy.deepcopy(docs[escolha["entregue"]]["quadros"][id_q])
        quadros[id_q] = quadro
        registro[id_q] = dict(escolha)
    doc = dict(referencia, quadros=quadros)
    if not tomada:
        return doc, registro
    doc = aplicar_consenso(doc, dimensoes)
    for id_q, quadro in doc["quadros"].items():
        sinal = quadro.get("S4")
        s4b = bool(sinal and sinal["referencia"] is not None and sinal["k"] != 0)
        registro[id_q]["S4b"] = s4b
        if s4b:
            quadro["sinalizado"] = True
    return doc, registro


def _sem_linhas(medida: dict) -> dict:
    """A medida sem as linhas quadro a quadro.

    Args:
        medida: saída de ``medir_por_grupo``.

    Returns:
        Cópia sem ``linhas``.
    """
    return {k: v for k, v in medida.items() if k != "linhas"}


def criterios(novo: dict, referencia: dict) -> dict:
    """Os critérios 1, 2 e 3 da 1044.

    Args:
        novo: ``medir_por_grupo`` da cadeia.
        referencia: ``medir_por_grupo`` do par antigo.

    Returns:
        Cada critério com os números e se passa.
    """
    n, r = novo["todos"], referencia["todos"]
    medidos = n["medidos"]
    certos_ref = {
        linha["id"]
        for linha in referencia["linhas"]
        if not linha["sinalizado"] and linha["classe"] == "certo"
    }
    estragados = sum(
        1
        for linha in novo["linhas"]
        if linha["id"] in certos_ref
        and not linha["sinalizado"]
        and linha["classe"] == "falso"
    )
    return {
        "1_seguranca": {
            "falsos_novo_ref": [n["falsos_passam_n"], r["falsos_passam_n"]],
            "passa": n["falsos_passam_n"] <= r["falsos_passam_n"]
            and n["falsos_passam_n"] <= 0.05 * medidos,
        },
        "2_ganho": {
            "certos_novo_ref": [n["entregue_certo"], r["entregue_certo"]],
            "passa": n["entregue_certo"] >= r["entregue_certo"] + 4,
        },
        "3_nao_estragar": {
            "estragados_de": [estragados, len(certos_ref)],
            "passa": estragados <= 1,
        },
    }


#: Rodadas medidas sem a tomada (parte C).
RODADAS_SEM_TOMADA = ("1047",)


def ler_faixas() -> dict[str, dict]:
    """As faixas dos validadores gravadas por ``faixas``.

    Returns:
        ``{validador: faixa}``.
    """
    return {k: v for k, v in _ler_json(ARQUIVO_FAIXAS).items() if k in VALIDADORES}


def medir(numero: str) -> dict:
    """Mede a cadeia da 1044 e o par antigo numa rodada.

    Args:
        numero: rodada do ciclo.

    Returns:
        As medidas, os critérios e o registro por quadro; também gravados em
        ``PASTA_HIPOTESES / numero / "medida.json"``.
    """
    doc, registro = cadeia(
        numero, ler_faixas(), tomada=numero not in RODADAS_SEM_TOMADA
    )
    gabarito = _ler_json(RODADAS[numero].gabarito)
    referencia_doc = _ler_hipoteses(numero)[nome_da_hipotese(*REFERENCIA)]
    novo = medir_por_grupo(doc, gabarito)
    referencia = medir_por_grupo(referencia_doc, gabarito)
    resultado = {
        "cadeia": _sem_linhas(novo),
        "referencia": _sem_linhas(referencia),
        "criterios": criterios(novo, referencia),
        "linhas": {"cadeia": novo["linhas"], "referencia": referencia["linhas"]},
        "registro": registro,
    }
    pasta = PASTA_HIPOTESES / numero
    gravar_atomico(pasta / "previsto_1044.json", doc)
    gravar_atomico(pasta / "medida.json", resultado)
    return resultado


def main() -> int:
    """Ponto de entrada da CLI.

    Returns:
        0 ao terminar.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("faixas", help="faixas dos validadores no desenvolvimento")
    p_medir = sub.add_parser("medir", help="a cadeia contra o gabarito")
    p_medir.add_argument("--rodada", required=True)
    args = parser.parse_args()
    if args.comando == "faixas":
        resultado = faixas()
    else:
        medida = medir(args.rodada)
        resultado = {
            "criterios": medida["criterios"],
            "cadeia": medida["cadeia"]["todos"],
            "referencia": medida["referencia"]["todos"],
        }
    print(json.dumps(resultado, ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

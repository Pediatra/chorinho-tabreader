"""Confiança do detector do braço (rodada 1023): sinais sem rótulo e regra de revisão.

Para cada quadro o detector (decodificador v2 da 1022) produz três sinais que não usam o
rótulo: S1, discordância sob perturbação (4 perturbações extras com semente própria);
S2, encaixe dos trastes (inliers e picos não inliers à direita do nut); S3, força dos
mapas (canais corda 1, corda 6 e nut). Valor alto quer dizer "duvidoso". Um quadro que
não acha o braço conta como sinalizado.

``dev`` aplica o pré-registro 1023 aos 1.052 quadros R do D2 (1022): mede os sinais, grava
o quadro a quadro e escolhe a regra (S1, S2, S3, ou S1 OU S2, com limiar por percentil).
``confirmar`` aplica a regra congelada à M11b (28 quadros, 3 sementes). Só ``dev`` deve
ser rodado nesta fase; ``confirmar`` falha enquanto as constantes da regra forem None.

CLI: ``python -m tab.maos_braco_confianca {dev,confirmar}``. ``dev --limite N`` mede só N
quadros por canal (validação ponta a ponta).
"""

from __future__ import annotations

import argparse
import itertools
import math
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

from .caminhos import MAOS_M11B, MAOS_M21
from .maos_braco_detector import (
    ARQUIVO_D2,
    CANAL_CORDA1,
    CANAL_CORDA6,
    CANAL_NUT,
    DIR_PESOS,
    PASSOS,
    SEMENTE_D2,
    SEMENTES_FINAIS,
    _carregar_pesos,
    _cordas_e_nut,
    _entradas_prova,
    _gravar_json,
    _imagem,
    _ler_json,
    _medir,
    _montar_saida,
    _nao_achou,
    _no_quadro,
    _nome_unidade,
    _numerar_v2,
    _pool_r,
    _trava_gpu,
    canais_g,
    prever_mapas,
)
from .maos_braco_faixa import eixo_da_faixa, matriz_da_faixa, perturbar, recortar
from .maos_braco_tempo import Marcas, erros, marcas_do_registro

#: Rodada 1023: semente das perturbações extras do S1 (``<semente>:<id>:<j>``).
SEMENTE_EXTRAS = "20261023:P"
#: Rodada 1023: número de perturbações extras (j = 1..4).
N_EXTRAS = 4
#: Escala da discordância do S1 (vãos para as cordas, casas para nut e trastes).
ESCALA_DISCORDANCIA = 0.5
#: Quadros por lote (cada quadro vira 1 + N_EXTRAS faixas no modelo).
QUADROS_POR_LOTE = 16
#: Percentis varridos para o limiar de cada sinal.
PERCENTIS = tuple(range(50, 100, 5))
#: Teto de quadros sinalizados (desenvolvimento).
LIMITE_SINALIZADOS = 0.30
#: Teto de falsos não sinalizados, em fração de todos os quadros (desenvolvimento).
LIMITE_FALSOS_DEV = 0.02
#: Confirmação M11b: teto de falsos não sinalizados e de sinalizados (frações).
LIMITE_FALSOS_CONFIRMACAO = 0.05
LIMITE_SINALIZADOS_CONFIRMACAO = 0.50
#: Regras candidatas: cada sinal sozinho, e S1 OU S2 (a ordem desempata).
REGRAS = (("S1",), ("S2",), ("S3",), ("S1", "S2"))
ARQUIVO_DEV = MAOS_M21 / "c1023_dev.json"
ARQUIVO_CONFIRMACAO = MAOS_M21 / "c1023_confirmacao.json"
#: Regra congelada no desenvolvimento, antes de ``confirmar`` (ex.: ``("S1",)``).
#: Enquanto for None, ``confirmar`` falha com erro claro.
REGRA_CONGELADA: tuple[str, ...] | None = ("S1", "S2")
#: Limiar numérico de cada sinal da regra congelada (mesmas chaves de REGRA_CONGELADA).
LIMIARES_CONGELADOS: dict[str, float] | None = {
    "S1": 0.5402071601548553,
    "S2": 0.09523809523809523,
}


def decodificar_com_dados(mapas: np.ndarray) -> tuple[dict, dict]:
    """Decodificador v2 que também devolve os dados usados pelo S2.

    Reaproveita ``_cordas_e_nut`` e ``_numerar_v2`` do detector, e a saída é a mesma de
    ``decodificar_v2``. Além da saída, devolve os inliers, os picos e o x do nut.

    Args:
        mapas: probabilidades ``(4, 192, 1024)``.

    Returns:
        ``(dec, info)``: ``dec`` tem o formato de ``decodificar_v2``; ``info`` tem
        ``achou``, ``inliers`` (número -> x), ``picos`` (x dos picos do canal de trastes)
        e ``x_nut``.
    """
    geo = _cordas_e_nut(mapas)
    if not geo["achou"]:
        return geo, {"achou": False, "inliers": {}, "picos": [], "x_nut": 0.0}
    base = {"picos": geo["picos"], "x_nut": geo["x_nut"]}
    resultado = _numerar_v2(geo["picos"], geo["x_nut"])
    if resultado is None:
        return _nao_achou("menos de 4 inliers de traste"), {
            "achou": False,
            "inliers": {},
            **base,
        }
    dec = _montar_saida(geo, resultado["inliers"], resultado["ts"])
    return dec, {"achou": True, "inliers": resultado["inliers"], **base}


def sinal_s1(principal: Marcas | None, extras: list[Marcas | None]) -> float:
    """S1: discordância da predição principal contra as perturbações extras.

    Para cada extra, mede ``erros(principal, extra)`` e toma o máximo de
    ``perp_cordas``, ``nut_casas`` e ``pior_traste_casas``, cada um dividido por 0,5
    (``ESCALA_DISCORDANCIA``). O S1 é o máximo entre as extras.

    Args:
        principal: marcas da principal no quadro, ou None se ela não achou o braço.
        extras: marcas de cada extra no quadro, ou None se a extra não achou o braço.

    Returns:
        A discordância; ``math.inf`` se a principal ou alguma extra não achou o braço,
        ou se a medida não é possível (vão nulo).
    """
    if principal is None:
        return math.inf
    discordancia = 0.0
    for extra in extras:
        if extra is None:
            return math.inf
        try:
            medida = erros(principal, extra)
        except ValueError:
            return math.inf
        partes = [medida["perp_cordas"] / ESCALA_DISCORDANCIA]
        for chave in ("nut_casas", "pior_traste_casas"):
            if medida[chave] is not None:
                partes.append(medida[chave] / ESCALA_DISCORDANCIA)
        discordancia = max(discordancia, max(partes))
    return discordancia


def sinal_s2(info: dict) -> float:
    """S2: encaixe dos trastes, a partir de ``decodificar_com_dados``.

    Vale ``1 - inliers / maior número inlier``, somado a ``picos não inliers à direita do
    nut / picos à direita do nut``. Sem braço, vale infinito.

    Args:
        info: dados de ``decodificar_com_dados`` (``achou``, ``inliers``, ``picos``,
            ``x_nut``).

    Returns:
        O S2 (0 é encaixe perfeito).
    """
    if not info["achou"] or not info["inliers"]:
        return math.inf
    maior = max(info["inliers"])
    direita = [p for p in info["picos"] if p > info["x_nut"]]
    xs_inliers = {float(x) for x in info["inliers"].values()}
    fora = [p for p in direita if float(p) not in xs_inliers]
    parte_picos = len(fora) / len(direita) if direita else 0.0
    return 1.0 - len(info["inliers"]) / maior + parte_picos


def sinal_s3(mapa: np.ndarray) -> float:
    """S3: força dos mapas, invertida: 1 menos o menor máximo entre corda 1, corda 6 e nut.

    Args:
        mapa: probabilidades ``(4, 192, 1024)`` da faixa principal.

    Returns:
        O S3, em [0, 1]; alto quer dizer mapa fraco em algum dos três canais.
    """
    maximos = [
        float(mapa[canal].max()) for canal in (CANAL_CORDA1, CANAL_CORDA6, CANAL_NUT)
    ]
    return 1.0 - min(maximos)


def _sinais_do_quadro(
    item: dict, mapas: list[np.ndarray], matrizes: list[np.ndarray]
) -> dict:
    """Classe v2 e os três sinais de um quadro, a partir dos mapas do seu bloco.

    Args:
        item: quadro (``id``, ``canal``, ``alvo``, ``matriz``).
        mapas: ``1 + N_EXTRAS`` mapas: o da principal e os das extras, nessa ordem.
        matrizes: afins das ``1 + N_EXTRAS`` faixas, na mesma ordem.

    Returns:
        Dicionário com ``id``, ``canal``, ``achou``, ``classe_v2``, ``falso``, ``S1``,
        ``S2`` e ``S3``.
    """
    dec_principal, info_principal = decodificar_com_dados(mapas[0])
    classe, _ = _medir(dec_principal, matrizes[0], item["alvo"])
    marcas_principal = (
        _no_quadro(dec_principal, matrizes[0]) if dec_principal["achou"] else None
    )
    extras: list[Marcas | None] = []
    for j in range(1, N_EXTRAS + 1):
        dec_extra, _ = decodificar_com_dados(mapas[j])
        extras.append(
            _no_quadro(dec_extra, matrizes[j]) if dec_extra["achou"] else None
        )
    return {
        "id": item["id"],
        "canal": item["canal"],
        "achou": bool(dec_principal["achou"]),
        "classe_v2": classe,
        "falso": classe == "falso",
        "S1": sinal_s1(marcas_principal, extras),
        "S2": sinal_s2(info_principal),
        "S3": sinal_s3(mapas[0]),
    }


def sinais_do_lote(modelo: nn.Module, itens: list[dict]) -> list[dict]:
    """Mede os sinais de um lote de quadros com um modelo já carregado.

    Cada item traz a faixa principal já recortada (``faixa``, ``matriz``), as marcas do
    rótulo (``alvo``) e o caminho da imagem (``caminho``), usado para as extras. As extras
    usam ``random.Random(f"{SEMENTE_EXTRAS}:<id>:<j>")`` com o mesmo ``eixo_da_faixa``
    do rótulo. Os mapas são descartados depois de cada lote.

    Args:
        modelo: rede em modo de avaliação.
        itens: quadros de ``_item_r`` ou ``_item_prova``.

    Returns:
        Uma entrada por item, como em ``_sinais_do_quadro``.
    """
    tamanho = 1 + N_EXTRAS
    faixas: list[np.ndarray] = []
    matrizes: list[np.ndarray] = []
    for item in itens:
        imagem = _imagem(Path(item["caminho"]))
        eixo = eixo_da_faixa(item["alvo"])
        faixas.append(item["faixa"])
        matrizes.append(item["matriz"])
        for j in range(1, N_EXTRAS + 1):
            semente = f"{SEMENTE_EXTRAS}:{item['id']}:{j}"
            matriz = matriz_da_faixa(perturbar(eixo, random.Random(semente)))
            matrizes.append(matriz)
            faixas.append(recortar(imagem, matriz))
    mapas = prever_mapas(modelo, faixas)
    del faixas
    resultados = []
    for i, item in enumerate(itens):
        base = i * tamanho
        resultados.append(
            _sinais_do_quadro(
                item, mapas[base : base + tamanho], matrizes[base : base + tamanho]
            )
        )
    del mapas
    return resultados


def _item_r(entrada: dict) -> dict:
    """Quadro R do D2: faixa principal com ``20261022:D2:<id>`` e o rótulo R.

    Args:
        entrada: entrada de ``_pool_r`` (``caminho``, ``registro``, ``canal``).

    Returns:
        Item para ``sinais_do_lote``.
    """
    caminho = Path(entrada["caminho"])
    alvo = marcas_do_registro(entrada["registro"])
    matriz = matriz_da_faixa(
        perturbar(eixo_da_faixa(alvo), random.Random(f"{SEMENTE_D2}:{caminho.stem}"))
    )
    return {
        "id": caminho.stem,
        "canal": entrada["canal"],
        "alvo": alvo,
        "caminho": caminho,
        "faixa": recortar(_imagem(caminho), matriz),
        "matriz": matriz,
    }


def _item_prova(entrada: dict) -> dict:
    """Quadro da M11b, a partir de ``_entradas_prova`` (perturbação ``20261021:T``).

    Args:
        entrada: entrada de ``_entradas_prova``.

    Returns:
        Item para ``sinais_do_lote``.
    """
    return {
        "id": entrada["id"],
        "canal": entrada["canal"],
        "alvo": entrada["marcas"],
        "caminho": MAOS_M11B / "quadros" / f"{entrada['id']}.png",
        "faixa": entrada["faixa"],
        "matriz": entrada["matriz"],
    }


def _jsonizar(valor: float | None) -> float | None:
    """Número para JSON: infinito e nulo viram None (``null``).

    Args:
        valor: número ou None.

    Returns:
        O número, ou None se ele não é finito.
    """
    if valor is None or not math.isfinite(valor):
        return None
    return float(valor)


def _serializar(quadros: list[dict]) -> list[dict]:
    """Quadros com os sinais prontos para JSON (infinito vira None).

    Args:
        quadros: saída de ``sinais_do_lote``.

    Returns:
        Cópias com ``S1``, ``S2`` e ``S3`` em JSON.
    """
    saida = []
    for q in quadros:
        copia = dict(q)
        for sinal in ("S1", "S2", "S3"):
            copia[sinal] = _jsonizar(q[sinal])
        saida.append(copia)
    return saida


def _limiar(valores: list[float], percentil: float) -> float:
    """Limiar de um sinal: percentil dos valores finitos (infinitos ficam de fora).

    Args:
        valores: valores do sinal, um por quadro.
        percentil: de 0 a 100.

    Returns:
        O limiar, ou infinito se não há valor finito.
    """
    finitos = [v for v in valores if math.isfinite(v)]
    if not finitos:
        return math.inf
    return float(np.percentile(finitos, percentil))


def marcar(
    quadros: list[dict], regra: tuple[str, ...], limiares: dict[str, float]
) -> np.ndarray:
    """Quadros sinalizados pela regra: sem braço, ou algum sinal acima do limiar.

    Args:
        quadros: entradas com ``achou`` e os sinais.
        regra: sinais da regra, por exemplo ``("S1",)`` ou ``("S1", "S2")`` (OU).
        limiares: sinal -> limiar (um por sinal da regra).

    Returns:
        Máscara booleana, um valor por quadro, True para sinalizado.
    """
    marcado = np.array([not q["achou"] for q in quadros], dtype=bool)
    for sinal in regra:
        valores = np.array([q[sinal] for q in quadros], dtype=float)
        marcado |= valores > limiares[sinal]
    return marcado


def avaliar(
    quadros: list[dict],
    regra: tuple[str, ...],
    limiares: dict[str, float],
) -> dict:
    """Resultado de uma regra com limiares fixos: sinalizados e falsos que passam.

    Args:
        quadros: entradas com ``achou``, ``falso`` e os sinais.
        regra: sinais da regra.
        limiares: sinal -> limiar.

    Returns:
        Dicionário com ``regra``, ``limiares``, ``sinalizados``, ``fracao_sinalizada``,
        ``falsos``, ``falsos_nao_sinalizados`` e ``fracao_falsos_nao_sinalizados``.
    """
    n = len(quadros)
    marcado = marcar(quadros, regra, limiares)
    falso = np.array([q["falso"] for q in quadros], dtype=bool)
    sinalizados = int(marcado.sum())
    falsos_nao = int((falso & ~marcado).sum())
    return {
        "regra": "+".join(regra),
        "limiares": {s: _jsonizar(limiares[s]) for s in regra},
        "sinalizados": sinalizados,
        "fracao_sinalizada": sinalizados / n,
        "falsos": int(falso.sum()),
        "falsos_nao_sinalizados": falsos_nao,
        "fracao_falsos_nao_sinalizados": falsos_nao / n,
    }


def escolher_regra(quadros: list[dict]) -> dict:
    """Escolha de regra do desenvolvimento, com a curva de cada regra.

    Para cada regra candidata e cada combinação de percentis (50..95 passo 5; a regra OU
    tem a grade dos dois percentis), mede a fração sinalizada e os falsos que passam.
    Candidatas: fração sinalizada até ``LIMITE_SINALIZADOS``. A escolha é a de menos
    falsos não sinalizados; no empate, a que sinaliza menos; no empate de ambos, a
    primeira na ordem de ``REGRAS`` e dos percentis.

    Args:
        quadros: entradas com ``achou``, ``falso``, ``S1``, ``S2`` e ``S3``.

    Returns:
        Dicionário com ``curvas`` (regra -> lista de avaliações, cada uma com
        ``percentis``), ``escolhida`` (avaliação ou None), e ``passou`` (escolhida com
        falsos não sinalizados até ``LIMITE_FALSOS_DEV``).
    """
    curvas: dict[str, list[dict]] = {}
    candidatas: list[dict] = []
    for regra in REGRAS:
        nome = "+".join(regra)
        curvas[nome] = []
        for percentis in itertools.product(PERCENTIS, repeat=len(regra)):
            limiares = {
                sinal: _limiar([q[sinal] for q in quadros], percentil)
                for sinal, percentil in zip(regra, percentis, strict=True)
            }
            avaliacao = avaliar(quadros, regra, limiares)
            avaliacao["percentis"] = dict(zip(regra, percentis, strict=True))
            curvas[nome].append(avaliacao)
            if avaliacao["fracao_sinalizada"] <= LIMITE_SINALIZADOS:
                candidatas.append(avaliacao)
    escolhida = (
        min(
            candidatas,
            key=lambda e: (e["falsos_nao_sinalizados"], e["sinalizados"]),
        )
        if candidatas
        else None
    )
    passou = (
        escolhida is not None
        and escolhida["fracao_falsos_nao_sinalizados"] <= LIMITE_FALSOS_DEV
    )
    return {"curvas": curvas, "escolhida": escolhida, "passou": passou}


def dev(limite: int | None = None, destino: Path = ARQUIVO_DEV) -> int:
    """Desenvolvimento 1023: sinais dos 1.052 quadros R e escolha da regra.

    Usa o peso ``A3_100_<k>_s1`` do canal k (o canal k não está no treino dele). Grava
    o quadro a quadro, as curvas e a escolha em ``destino``. Confere a classe v2 contra
    o D2 da 1022 (``ARQUIVO_D2``).

    Args:
        limite: se dado, só os N primeiros quadros R de cada canal (validação).
        destino: arquivo do resultado.

    Returns:
        0 ao terminar (a decisão é do dono, pelo campo ``passou``).
    """
    inicio = time.perf_counter()
    pool = _pool_r()
    quadros: list[dict] = []
    por_canal: list[dict] = []
    for k, canal in enumerate(canais_g()):
        entradas = [e for e in pool if e["canal"] == canal]
        if limite is not None:
            entradas = entradas[:limite]
        nome = _nome_unidade("A3", "100", k, 1)
        passos = _ler_json(DIR_PESOS / f"{nome}.json")["passos"]
        with _trava_gpu():
            modelo, _ = _carregar_pesos(nome, passos)
            for ini in range(0, len(entradas), QUADROS_POR_LOTE):
                lote = entradas[ini : ini + QUADROS_POR_LOTE]
                quadros.extend(sinais_do_lote(modelo, [_item_r(e) for e in lote]))
            del modelo
            torch.cuda.empty_cache()
        por_canal.append(
            {"dobra": k, "canal": canal, "peso": nome, "quadros": len(entradas)}
        )
        print(f"{canal}: {len(entradas)} quadros", file=sys.stderr)

    referencia = {q["id"]: q["classe_v2"] for q in _ler_json(ARQUIVO_D2)["quadros"]}
    divergentes = [
        q["id"]
        for q in quadros
        if q["id"] in referencia and referencia[q["id"]] != q["classe_v2"]
    ]
    escolha = escolher_regra(quadros)
    dados = {
        "portao": "C1023_DEV",
        "dados": "1.052 quadros R do D2 da 1022, peso A3_100_<k>_s1, rótulo R",
        "semente_principal": f"{SEMENTE_D2}:<id>",
        "semente_extras": f"{SEMENTE_EXTRAS}:<id>:<j>",
        "extras": N_EXTRAS,
        "limite_por_canal": limite,
        "limite_sinalizados": LIMITE_SINALIZADOS,
        "limite_falsos": LIMITE_FALSOS_DEV,
        "percentis": list(PERCENTIS),
        "quadros_total": len(quadros),
        "falsos_v2": sum(q["falso"] for q in quadros),
        "nao_achou_v2": sum(not q["achou"] for q in quadros),
        "conferencia_d2": {
            "comparados": sum(q["id"] in referencia for q in quadros),
            "divergencias": len(divergentes),
            "ids_divergentes": divergentes[:50],
        },
        "por_canal": por_canal,
        "escolha": escolha["escolhida"],
        "passou": escolha["passou"],
        "curvas": escolha["curvas"],
        "quadros": _serializar(quadros),
        "tempo_s": round(time.perf_counter() - inicio, 1),
    }
    _gravar_json(destino, dados)
    print(_resumo_dev(dados))
    return 0


def _resumo_dev(dados: dict) -> str:
    """Resumo legível do desenvolvimento, para o terminal.

    Args:
        dados: saída de ``dev`` (sem a lista de quadros).

    Returns:
        Texto com quadros, falsos, conferência com o D2, escolha e veredito.
    """
    escolhida = dados["escolha"]
    linhas = [
        f"quadros: {dados['quadros_total']}",
        f"falsos v2: {dados['falsos_v2']}; nao achou: {dados['nao_achou_v2']}",
        "conferência D2: "
        f"{dados['conferencia_d2']['divergencias']} divergências "
        f"de {dados['conferencia_d2']['comparados']}",
        f"tempo: {dados['tempo_s']} s",
    ]
    if escolhida is None:
        linhas.append("escolha: nenhuma regra com até 30 % sinalizados")
    else:
        linhas.append(
            f"escolha: {escolhida['regra']} limiares {escolhida['limiares']} "
            f"sinalizados {escolhida['sinalizados']} "
            f"({100 * escolhida['fracao_sinalizada']:.1f} %), "
            f"falsos não sinalizados {escolhida['falsos_nao_sinalizados']} "
            f"({100 * escolhida['fracao_falsos_nao_sinalizados']:.2f} %)"
        )
    linhas.append(f"passou no desenvolvimento: {dados['passou']}")
    return "\n".join(linhas)


def _constantes_congeladas() -> tuple[tuple[str, ...], dict[str, float]]:
    """Regra e limiares congelados, ou erro claro se ainda não foram preenchidos.

    Returns:
        ``(regra, limiares)``.

    Raises:
        RuntimeError: se ``REGRA_CONGELADA`` ou ``LIMIARES_CONGELADOS`` é None.
        ValueError: se os limiares não correspondem aos sinais da regra.
    """
    if REGRA_CONGELADA is None or LIMIARES_CONGELADOS is None:
        raise RuntimeError(
            "regra da confirmação não congelada: preencha REGRA_CONGELADA e "
            "LIMIARES_CONGELADOS em tab/maos_braco_confianca.py com a escolha do "
            "desenvolvimento (data/saida/maos/m21/c1023_dev.json) antes de rodar "
            "'confirmar'"
        )
    if set(LIMIARES_CONGELADOS) != set(REGRA_CONGELADA):
        raise ValueError(
            "LIMIARES_CONGELADOS não tem as mesmas chaves de REGRA_CONGELADA"
        )
    return REGRA_CONGELADA, LIMIARES_CONGELADOS


def confirmar(destino: Path = ARQUIVO_CONFIRMACAO) -> int:
    """Confirmação M11b com a regra congelada: 28 quadros x 3 sementes (84 medidas).

    Não rodar antes de o desenvolvimento congelar REGRA_CONGELADA e LIMIARES_CONGELADOS.
    Critério: falsos não sinalizados até 5 % das 84 medidas e sinalizados até 50 %.

    Args:
        destino: arquivo do resultado.

    Returns:
        0 ao terminar (a decisão é do dono, pelo campo ``passou``).

    Raises:
        RuntimeError: se a regra ainda não está congelada.
    """
    regra, limiares = _constantes_congeladas()
    inicio = time.perf_counter()
    itens = [_item_prova(e) for e in _entradas_prova()]
    quadros: list[dict] = []
    for semente in SEMENTES_FINAIS:
        nome = f"A3_100_todos_s{semente}"
        with _trava_gpu():
            modelo, _ = _carregar_pesos(nome, PASSOS)
            for ini in range(0, len(itens), QUADROS_POR_LOTE):
                lote = itens[ini : ini + QUADROS_POR_LOTE]
                for resultado in sinais_do_lote(modelo, lote):
                    resultado["semente"] = semente
                    quadros.append(resultado)
            del modelo
            torch.cuda.empty_cache()
    resultado_regra = avaliar(quadros, regra, limiares)
    passou = (
        resultado_regra["fracao_falsos_nao_sinalizados"] <= LIMITE_FALSOS_CONFIRMACAO
        and resultado_regra["fracao_sinalizada"] <= LIMITE_SINALIZADOS_CONFIRMACAO
    )
    marcado = marcar(quadros, regra, limiares)
    dados = {
        "portao": "C1023_CONFIRMACAO_M11B",
        "regra": resultado_regra,
        "limite_falsos": LIMITE_FALSOS_CONFIRMACAO,
        "limite_sinalizados": LIMITE_SINALIZADOS_CONFIRMACAO,
        "medidas": len(quadros),
        "passou": passou,
        "quadros": [
            {**_serializar([q])[0], "sinalizado": bool(m)}
            for q, m in zip(quadros, marcado, strict=True)
        ],
        "tempo_s": round(time.perf_counter() - inicio, 1),
    }
    _gravar_json(destino, dados)
    print(_resumo_confirmacao(dados))
    return 0


def _resumo_confirmacao(dados: dict) -> str:
    """Resumo legível da confirmação, para o terminal.

    Args:
        dados: saída de ``confirmar``.

    Returns:
        Texto com a regra, as medidas e o veredito.
    """
    regra = dados["regra"]
    return "\n".join(
        [
            f"medidas: {dados['medidas']}",
            f"regra {regra['regra']} limiares {regra['limiares']}",
            f"sinalizados {regra['sinalizados']} "
            f"({100 * regra['fracao_sinalizada']:.1f} %), falsos não sinalizados "
            f"{regra['falsos_nao_sinalizados']} "
            f"({100 * regra['fracao_falsos_nao_sinalizados']:.2f} %)",
            f"passou na confirmação: {dados['passou']}",
        ]
    )


def _parser() -> argparse.ArgumentParser:
    """Parser da CLI.

    Returns:
        Parser com os subcomandos ``dev`` e ``confirmar``.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    dev_p = sub.add_parser(
        "dev", help="desenvolvimento 1023: sinais e escolha da regra"
    )
    dev_p.add_argument(
        "--limite", type=int, default=None, help="só N quadros R por canal (validação)"
    )
    sub.add_parser(
        "confirmar", help="confirmação M11b com a regra congelada (não rodar ainda)"
    )
    return parser


def main() -> int:
    """Ponto de entrada da CLI.

    Returns:
        Código de saída do subcomando.
    """
    args = _parser().parse_args()
    if args.comando == "dev":
        return dev(args.limite)
    return confirmar()


if __name__ == "__main__":
    sys.exit(main())

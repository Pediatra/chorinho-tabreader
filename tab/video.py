"""VÍDEO -> JSON v1: lê cada tela de um vídeo inteiro e mede o tempo por exibição.

Cadeia, por tela (``tab.telas``, Fase 3):

1. imagem limpa: o quadro de referência (``quadro_ref_s``) ou a mediana temporal de alguns
   quadros da maior exibição, que apaga o marcador;
2. painel: ``tab.painel.escolher_ou_mascara`` nessa imagem; o ``roi`` dele dá o x no espaço do QUADRO;
3. leitura do ``roi``, por um de dois leitores (``LEITORES``): ``rede`` (padrão), o detector
   de sistema inteiro ``tab.detector_tab`` sobre a grade de ``tab.tabseg``; ou ``glifos``,
   o leitor antigo ``reconhecer_linha`` (tokens com corda, casa e símbolo cru);
4. colunas (um acorde é uma coluna) e compasso, pelas barlines da tela;
5. tempo por exibição (Fase 5): dentro de cada ``[t0, t1]`` da tela, os quadros são lidos
   a ~6 qps pelo ``tab.leitor``, e dois observadores (posição do marcador e cor do algarismo)
   dizem a coluna atual. Escolhe-se, por exibição, o de maior coerência; abaixo do mínimo,
   a exibição sai com ``medido: false`` e o motivo.

Algarismo vai para ``notas``; o resto vai para ``nao_notas`` com a classe e o símbolo cru,
porque símbolo não se descarta. No leitor ``rede``, o X (nota abafada) sai em ``nao_notas``
com classe ``x``, e a técnica que a rede vê sai no campo ``tecnica`` da nota, **sem
validação** (o gabarito não tem técnica por nota). Cada nota sai com ``t_ini`` do observador escolhido na
exibição (``null`` sem tempo medido). Quando a aula **repete** uma passagem dentro de uma
exibição, a nota ganha uma entrada por passagem, com ``exibicao`` e ``passagem``.

Uso:
    python -m tab.video VIDEO --json saida.json [--leitor rede|glifos] [--imagem quadro|mediana]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

from . import ataque_rotulo, detector_tab, leitor
from .caminhos import DETECTOR_PADRAO, MODELO_PADRAO, RAIZ, VIDEO_SIMBOLOS, acervo
from .colunas import agrupar_colunas
from .digito import carregar
from .estado import (
    ESTAVEL_MINIMO,
    Amostra,
    Observacao,
    estados_cor,
    estados_posicao,
    ler_amostras,
    observar,
    passagens_de,
    refinar_inicios,
)
from .painel import (
    PASSO_MAXIMO_PX,
    PASSO_MINIMO_PX,
    escolher_ou_mascara,
    recorte_alto,
)
from .reconhecer import ALGARISMOS, carregar_modelo, reconhecer_linha
from .telas import Tela, telas

#: Identificador do formato, lido por ``tab.avaliar_video``.
ESQUEMA = "chorinho/video@1"

#: Maneiras de obter a imagem limpa de uma tela (T4.1).
IMAGENS = ("quadro", "mediana")

#: Imagem usada por padrão. Escolhida pela medição no ouro (ver ``ESTADO.md``, Fase 4).
IMAGEM_PADRAO = "quadro"

#: Leitores de nota: a rede de sistema inteiro e o classificador de glifos antigo (reserva).
LEITORES = ("rede", "glifos")

#: Leitor usado por padrão. Medido nos 8 gabaritos (validação cruzada por vídeo, 2.689
#: notas): rede 0,974/0,949/0,987 (precisão/revocação/casa) contra 0,962/0,830/0,943.
LEITOR_PADRAO = "rede"

#: Classe da nota abafada (X) no leitor ``rede``. Vai para ``nao_notas``.
CLASSE_ABAFADA = "x"

#: Folga, em passos, em volta da caixa de um glifo para a nota da rede herdar a borda esquerda
#: dele. Sem glifo assim, a borda é estimada a ``BORDA_SEM_GLIFO`` passos à esquerda do centro.
FOLGA_GLIFO_PASSO = 0.15

#: Meia largura típica de um algarismo, em passos (estimativa da borda esquerda).
BORDA_SEM_GLIFO = 0.3

#: Distância máxima, em passos, da borda esquerda do glifo ao centro da nota para a nota
#: herdar essa borda. Um ``12`` tem o centro a ~0,5 passo da borda; num glifo largo (slide
#: ``2/3`` grudado), a segunda nota está a ~1 passo e herdaria a borda da primeira, caindo na
#: mesma coluna (medido no South American: 5 pares repetidos).
BORDA_MAXIMA_PASSO = 0.8

#: Quadros da mediana temporal, espalhados pela maior exibição da tela.
MEDIANA_QUADROS = 7

#: Quadros por segundo lidos dentro de cada exibição (T5.1).
QPS_EXIBICAO = 6.0

#: Taxa usada para ler os quadros nativos do refino quando ``ffprobe`` não informa a taxa.
FPS_PADRAO = 30000 / 1001

#: Amostras seguidas para uma coluna ser aceita como atual (T5.2). Medido no ouro.
ESTAVEL_EXIBICAO = ESTAVEL_MINIMO

#: Trocas de coluna mínimas para uma coerência ter sentido. Abaixo disso o observador
#: não é avaliado (não há o que medir).
TRANSICOES_MINIMAS = 3

#: Fração mínima das amostras da exibição que o observador precisa cobrir.
COBERTURA_MINIMA = 0.3

#: Coerência mínima (fração de trocas que avançam +1 ou +2 colunas) para aceitar o tempo.
#: Medido no ouro (retrato, 22 exibições): a menor coerência de uma exibição escolhida foi
#: 0,955, e todas as escolhas estão certas no ouro. Sem ouro (mr. tabs), as exibições
#: medidas por cor têm 0,50 a 0,87: 0,9 deixa de aceitar essas até haver ouro para elas.
COERENCIA_MINIMA = 0.9

#: Motivo declarado quando a tela não tem exibição medida e nenhum motivo mais preciso.
MOTIVO_TEMPO = "tempo por exibicao nao medido"

#: Ordem de preferência dos observadores quando empatam na coerência.
OBSERVADORES = ("posicao", "cor_acende", "cor")


def mediana_temporal(quadros: list[np.ndarray]) -> np.ndarray:
    """Mediana, pixel a pixel, de quadros do mesmo tamanho.

    O marcador anda, então cada posição dele fica acesa só num pedaço dos quadros, e a
    mediana a apaga. A tinta fixa (algarismo, corda) aparece em todos e fica.

    Args:
        quadros: quadros BGR de mesmas dimensões (ao menos um).

    Returns:
        O quadro mediano, em ``uint8``.

    Raises:
        ValueError: se a lista estiver vazia.
    """
    if not quadros:
        raise ValueError("a mediana temporal precisa de ao menos um quadro")
    return np.median(np.stack(quadros), axis=0).astype(np.uint8)


def tokens_do_quadro(r: dict, x0: int) -> list[dict]:
    """Tokens de uma linha lida, com o x no espaço do QUADRO.

    Args:
        r: resultado de ``reconhecer_linha``; o x vem em pixels do ``roi``.
        x0: deslocamento em x do ``roi`` no quadro (``Candidato.x0``).

    Returns:
        Um dict por token, na ordem de ``r["notas"]``, com ``corda``, ``classe``,
        ``x_quadro`` (borda esquerda), ``x_centro_quadro``, ``confianca``, ``tecnica``,
        e ``simbolo_cru`` e ``casa_recuperada`` quando houver.
    """
    tokens = []
    for n in r.get("notas", []):
        tokens.append(
            {
                "corda": int(n["corda"]),
                "classe": str(n["casa"]),
                "x_quadro": int(x0) + int(n["x"]),
                "x_centro_quadro": round(int(x0) + float(n["x_centro"]), 1),
                "confianca": float(n["confianca"]),
                "tecnica": n.get("tecnica"),
                "simbolo_cru": n.get("simbolo_cru"),
                "casa_recuperada": n.get("casa_recuperada"),
            }
        )
    return tokens


def tokens_da_rede(
    notas: list[dict], glifos: list, x0: int, passo: float
) -> list[dict]:
    """Tokens no formato de ``tokens_do_quadro`` a partir da saída de ``detectar``.

    A rede dá o centro da nota. A borda esquerda (``x_quadro``, usada nas colunas e no
    compasso) vem do glifo da mesma corda cuja caixa, com ``FOLGA_GLIFO_PASSO`` de folga,
    contém o centro e começa a até ``BORDA_MAXIMA_PASSO`` dele; sem glifo assim, é o
    centro menos ``BORDA_SEM_GLIFO`` passos.

    Args:
        notas: saída de ``tab.detector_tab.detectar``; o x vem em pixels do ``roi``.
        glifos: glifos da grade (``grade.glifos``), com ``corda``, ``x0`` e ``x1`` no ``roi``.
        x0: deslocamento em x do ``roi`` no quadro.
        passo: passo entre cordas, em px.

    Returns:
        Um dict por nota, com as chaves de ``tokens_do_quadro``. ``tecnica`` é o texto das
        técnicas da rede unidas por ``+`` (``None`` sem técnica).
    """
    folga = FOLGA_GLIFO_PASSO * passo
    tokens = []
    for n in notas:
        xc = float(n["x"])
        bordas = [
            g.x0
            for g in glifos
            if g.corda == int(n["corda"])
            and g.x0 - folga <= xc <= g.x1 + folga
            and xc - g.x0 <= BORDA_MAXIMA_PASSO * passo
        ]
        borda = min(bordas) if bordas else xc - BORDA_SEM_GLIFO * passo
        tokens.append(
            {
                "corda": int(n["corda"]),
                "classe": str(n["rotulo"]),
                "x_quadro": int(x0) + round(borda),
                "x_centro_quadro": round(int(x0) + xc, 1),
                "confianca": float(n["confianca"]),
                "tecnica": "+".join(n["tecnica"]) or None,
                "simbolo_cru": None,
                "casa_recuperada": None,
            }
        )
        if "tecnica_p" in n:
            tokens[-1]["tecnica_p"] = n["tecnica_p"]
    return tokens


def colunas_do_quadro(tokens: list[dict], passo: float) -> list[int]:
    """Coluna de cada token da tela, numerada de 1 em diante, em ordem de x.

    Uma coluna são os tokens com o mesmo x (um acorde). Todos entram, algarismo ou não:
    a coluna é uma posição do marcador no quadro.

    Args:
        tokens: saída de ``tokens_do_quadro`` para uma tela.
        passo: passo entre cordas da tela, em px.

    Returns:
        A coluna de cada token, na mesma ordem de ``tokens``.
    """
    if not tokens:
        return []
    colunas = agrupar_colunas([t["x_quadro"] for t in tokens], passo)
    saida = [0] * len(tokens)
    for numero, coluna in enumerate(colunas, start=1):
        for i in coluna.indices:
            saida[i] = numero
    return saida


def compasso_de(x_quadro: int, barlines_x: list[int]) -> int:
    """Compasso, a partir de 1, de um x do quadro.

    Mesma regra do ``reconhecer.completar``: a primeira barline é o início da pauta.

    Args:
        x_quadro: x do token no quadro.
        barlines_x: barlines da tela, no quadro, em ordem crescente.

    Returns:
        O número do compasso.
    """
    return 1 + sum(1 for bx in barlines_x[1:] if bx < x_quadro)


def colunas_e_caixas(
    tokens: list[dict],
    colunas: list[int],
    glifos: list,
    x0: int,
    passo: float,
) -> tuple[list[float], list[list[tuple[int, int, int, int]]]]:
    """Centro no quadro e caixas de algarismo de cada coluna, para os observadores.

    O centro é a média do ``x_centro_quadro`` dos tokens da coluna (o marcador passa pelo
    centro). A caixa de um glifo entra na coluna cujo centro está a até meio passo. As caixas
    saem no espaço do quadro em x, e em y relativo ao recorte da faixa (que começa em ``y0``
    do painel, então o y do ``roi`` já é o y do recorte).

    Args:
        tokens: tokens da tela (``tokens_do_quadro``), na ordem de ``colunas``.
        colunas: número da coluna de cada token (``colunas_do_quadro``).
        glifos: glifos do painel (``grade.glifos``), com ``x0, y0, x1, y1`` no ``roi``.
        x0: deslocamento em x do ``roi`` no quadro.
        passo: passo entre cordas, em px.

    Returns:
        ``(centros, caixas)``: ``centros[k]`` é o x da coluna ``k + 1``; ``caixas[k]`` lista
        as caixas ``(x0, y0, x1, y1)`` dos glifos dessa coluna.
    """
    numeros = sorted(set(colunas))
    centros: list[float] = []
    for numero in numeros:
        xs = [
            t["x_centro_quadro"]
            for t, c in zip(tokens, colunas, strict=True)
            if c == numero
        ]
        centros.append(float(np.mean(xs)))
    caixas: list[list[tuple[int, int, int, int]]] = [[] for _ in numeros]
    if not centros:
        return centros, caixas
    for g in glifos:
        xc = x0 + (g.x0 + g.x1) / 2.0
        k = min(range(len(centros)), key=lambda i: abs(centros[i] - xc))
        if abs(centros[k] - xc) <= 0.5 * passo:
            caixas[k].append((x0 + g.x0, g.y0, x0 + g.x1, g.y1))
    return centros, caixas


def escolher_observador(obs: dict[str, Observacao]) -> tuple[str | None, str]:
    """Escolhe, numa exibição, o observador de maior coerência, ou declara por que não há.

    Um observador só conta se tiver trocas suficientes e cobertura suficiente. Entre os
    que contam, vence a maior coerência (empate: a ordem de ``OBSERVADORES``).

    Args:
        obs: observações da exibição, por nome de observador.

    Returns:
        ``(nome, motivo)``: ``nome`` é o observador escolhido (ou ``None``) e ``motivo`` diz
        por que a exibição não foi medida (vazio quando foi).
    """
    resumo = "; ".join(
        f"{n}: cobertura {obs[n].cobertura:.2f}, {obs[n].transicoes} trocas, "
        f"coerencia {obs[n].coerencia:.2f}"
        for n in OBSERVADORES
        if n in obs
    )
    validos = [
        obs[n]
        for n in OBSERVADORES
        if n in obs
        and obs[n].transicoes >= TRANSICOES_MINIMAS
        and obs[n].cobertura >= COBERTURA_MINIMA
    ]
    if not validos:
        return None, f"nenhum observador com trocas e cobertura suficientes ({resumo})"
    melhor = max(validos, key=lambda o: o.coerencia)
    if melhor.coerencia < COERENCIA_MINIMA:
        return None, (f"coerencia abaixo de {COERENCIA_MINIMA} em todos ({resumo})")
    return melhor.observador, ""


def medir_exibicao(
    video: str,
    t0: float,
    t1: float,
    recorte_y: tuple[int, int],
    centros: list[float],
    caixas: list[list[tuple[int, int, int, int]]],
    passo: float,
) -> dict:
    """Mede o tempo de UMA exibição ``[t0, t1]`` (T5.1 a T5.3).

    Args:
        video: caminho do vídeo.
        t0: início da exibição, em segundos.
        t1: fim da exibição, em segundos.
        recorte_y: ``(y0, y1)`` da faixa da tela, no quadro.
        centros: centro no quadro de cada coluna.
        caixas: caixas de algarismo de cada coluna (``colunas_e_caixas``).
        passo: passo entre cordas, em px.

    Returns:
        Dicionário com ``t0``, ``t1``, ``tempo`` (``medido``, ``observador``, ``motivo``,
        ``coerencia``, ``cobertura``), ``observadores`` (o diagnóstico de cada um) e
        ``passagens``: uma lista por passagem, de ``{"coluna", "t_ini"}`` (coluna 1-based).
    """
    amostras = ler_amostras(video, t0, t1, QPS_EXIBICAO, recorte_y, caixas)
    obs = {
        "posicao": observar(
            "posicao",
            amostras,
            estados_posicao(amostras, centros, passo),
            ESTAVEL_EXIBICAO,
        ),
        "cor": observar(
            "cor", amostras, estados_cor(amostras, "destaque"), ESTAVEL_EXIBICAO
        ),
        "cor_acende": observar(
            "cor_acende", amostras, estados_cor(amostras, "acende"), ESTAVEL_EXIBICAO
        ),
    }
    nome, motivo = escolher_observador(obs)
    escolhido = obs[nome] if nome else None
    passagens = []
    if escolhido is not None:
        # o início de cada trecho vai para o quadro nativo da transição (ver refinar_inicios)
        estado_de = {
            "posicao": lambda lidas: estados_posicao(lidas, centros, passo),
            "cor": lambda lidas: estados_cor(lidas, "destaque"),
            "cor_acende": lambda lidas: estados_cor(lidas, "acende"),
        }[nome]
        fps = leitor.info(video)["fps"] or FPS_PADRAO

        def ler_fino(t_a: float, t_b: float) -> list[Amostra]:
            """Leituras dos quadros nativos de ``t_a`` a ``t_b``, com a mesma faixa e caixas."""
            return ler_amostras(video, t_a, t_b, fps, recorte_y, caixas)

        refinar_inicios(escolhido.corridas, amostras, ler_fino, estado_de, fps)
        for p in passagens_de(escolhido.corridas):
            passagens.append(
                [
                    {"coluna": k + 1, "t_ini": round(t, 3)}
                    for k, t in sorted({c.coluna: c.t_ini for c in p}.items())
                ]
            )
    return {
        "t0": round(t0, 3),
        "t1": round(t1, 3),
        "tempo": {
            "medido": nome is not None,
            "observador": nome,
            "motivo": None if nome else motivo,
            "coerencia": round(escolhido.coerencia, 3) if escolhido else None,
            "cobertura": round(escolhido.cobertura, 3) if escolhido else None,
        },
        "observadores": {
            n: {
                "coerencia": round(o.coerencia, 3),
                "cobertura": round(o.cobertura, 3),
                "transicoes": o.transicoes,
                "passagens": len(o.passagens),
            }
            for n, o in obs.items()
        },
        "passagens": passagens,
        "amostras": len(amostras),
    }


def entradas_da_nota(base: dict, exibicoes: list[dict]) -> list[dict]:
    """Uma entrada de nota por passagem medida, ou uma sem tempo se nenhuma foi medida.

    Args:
        base: campos comuns da nota (tela, coluna, corda, x, casa, ...).
        exibicoes: entradas de exibição da tela, com ``tempo`` e ``passagens``.

    Returns:
        Lista de notas: uma por (exibição, passagem) em que a coluna tem onset; senão uma
        única com ``t_ini`` nulo, ``exibicao`` nulo e ``passagem`` 1.
    """
    saida: list[dict] = []
    coluna = base["coluna"]
    for e, ex in enumerate(exibicoes):
        if not ex["tempo"]["medido"]:
            continue
        for p, passagem in enumerate(ex["passagens"], start=1):
            for item in passagem:
                if item["coluna"] == coluna:
                    saida.append(
                        {**base, "passagem": p, "exibicao": e, "t_ini": item["t_ini"]}
                    )
    if not saida:
        saida.append({**base, "passagem": 1, "exibicao": None, "t_ini": None})
    return saida


def montar_v1(
    *,
    video: dict,
    gerado_por: dict,
    telas_v1: list[dict],
    notas: list[dict],
    nao_notas: list[dict],
) -> dict:
    """Monta o JSON v1 a partir do que já foi lido. Função pura.

    Args:
        video: bloco ``video`` (arquivo, canal, duracao_s, codec).
        gerado_por: bloco ``gerado_por`` (modelo, commit, imagem, em).
        telas_v1: uma entrada por tela (id, painel, passo, modo, barlines_x, exibicoes, tempo).
        notas: notas numéricas, com ``casa`` inteiro e ``t_ini`` (``None`` sem tempo).
        nao_notas: tokens que não são algarismo, com ``classe`` e o símbolo cru.

    Returns:
        O dicionário do esquema ``chorinho/video@1``, com ``resumo`` calculado daí.
    """
    instantes = {n["t_ini"] for n in notas if n["t_ini"] is not None}
    return {
        "esquema": ESQUEMA,
        "video": video,
        "gerado_por": gerado_por,
        "telas": telas_v1,
        "notas": notas,
        "nao_notas": nao_notas,
        "resumo": {
            "telas": len(telas_v1),
            "exibicoes": sum(len(t["exibicoes"]) for t in telas_v1),
            "notas": len(notas),
            "notas_com_tempo": sum(1 for n in notas if n["t_ini"] is not None),
            "instantes_distintos": len(instantes),
            "telas_sem_tempo": sum(1 for t in telas_v1 if not t["tempo"]["medido"]),
            "nao_notas": len(nao_notas),
        },
    }


def validar_tempo(dados: dict) -> list[str]:
    """Invariantes do tempo por exibição (T5.5). Devolve as violações, vazio se tudo bate.

    Verifica: ``t_ini`` dentro de uma exibição da própria tela; onsets não decrescentes em
    cada passagem (pela coluna); mesma coluna com o mesmo ``t_ini`` na mesma passagem;
    exibição sem tempo com ``motivo`` não vazio; nota com tempo apontando exibição real.

    Args:
        dados: o JSON v1 (dicionário).

    Returns:
        Lista de textos, um por violação.
    """
    erros: list[str] = []
    telas_por_id = {t["id"]: t for t in dados.get("telas", [])}
    for t in dados.get("telas", []):
        for e, ex in enumerate(t["exibicoes"]):
            tempo = ex.get("tempo")
            if (
                tempo is not None
                and not tempo.get("medido")
                and not tempo.get("motivo")
            ):
                erros.append(f"tela {t['id']} exibicao {e}: medido false sem motivo")
            for p, passagem in enumerate(ex.get("passagens", []), start=1):
                ts = [item["t_ini"] for item in passagem]
                if ts != sorted(ts):
                    erros.append(
                        f"tela {t['id']} exibicao {e} passagem {p}: onsets decrescem"
                    )
    vistos: dict[tuple, float] = {}
    for n in dados.get("notas", []):
        if n["t_ini"] is None:
            continue
        tela = telas_por_id.get(n["tela"])
        if tela is None or n.get("exibicao") is None:
            erros.append(f"nota {n.get('x_quadro')} com t_ini sem exibicao da tela")
            continue
        ex = tela["exibicoes"][n["exibicao"]]
        if not ex["t0"] <= n["t_ini"] <= ex["t1"]:
            erros.append(
                f"tela {n['tela']} nota t_ini {n['t_ini']} fora de [{ex['t0']}, {ex['t1']}]"
            )
        chave = (n["tela"], n["exibicao"], n["passagem"], n["coluna"])
        if chave in vistos and vistos[chave] != n["t_ini"]:
            erros.append(f"coluna {chave} com t_ini diferentes")
        vistos[chave] = n["t_ini"]
    return erros


def imagem_da_tela(video: str, tela: Tela, modo: str) -> np.ndarray | None:
    """Imagem limpa de uma tela, no modo pedido (T4.1).

    Args:
        video: caminho do vídeo.
        tela: tela de ``tab.telas``.
        modo: ``"quadro"`` (o ``quadro_ref_s``) ou ``"mediana"`` (mediana de quadros da
            maior exibição).

    Returns:
        O quadro BGR, ou ``None`` se o vídeo não der quadro no instante.

    Raises:
        ValueError: se ``modo`` não for conhecido.
    """
    if modo not in IMAGENS:
        raise ValueError(f"imagem desconhecida: {modo!r}")
    if modo == "quadro" or not tela.exibicoes:
        return leitor.quadro_em(video, tela.quadro_ref_s)
    k = max(
        range(len(tela.exibicoes)),
        key=lambda i: tela.exibicoes[i][1] - tela.exibicoes[i][0],
    )
    t0, t1 = tela.exibicoes[k]
    instantes = [
        t0 + (t1 - t0) * (i + 1) / (MEDIANA_QUADROS + 1) for i in range(MEDIANA_QUADROS)
    ]
    quadros = [q for t in instantes if (q := leitor.quadro_em(video, t)) is not None]
    return mediana_temporal(quadros) if quadros else None


def ler_tela(
    imagem: np.ndarray | None,
    tela: Tela,
    modelo,
    rotulos,
    dev,
    discriminador,
    dir_simbolos: str,
    video: str | None = None,
    detector=None,
    rotulo_ataque: bool = False,
) -> tuple[dict, list[dict], list[dict]]:
    """Lê uma tela: painel, tokens, colunas, compasso e tempo por exibição.

    Args:
        imagem: imagem limpa da tela (``None`` se o vídeo não deu quadro).
        tela: tela de ``tab.telas``.
        modelo: classificador de glifos carregado.
        rotulos: classes na ordem de saída do modelo.
        dev: dispositivo do modelo.
        discriminador: função "é algarismo?" (``tab.digito.carregar``).
        dir_simbolos: pasta dos recortes crus de símbolo.
        video: caminho do vídeo para medir o tempo; ``None`` deixa todas as exibições sem
            tempo, com o motivo.
        detector: ``DetectorTab`` carregado (leitor ``rede``); ``None`` usa o leitor
            ``glifos`` (``modelo``, ``rotulos``, ``discriminador``).
        rotulo_ataque: grava ``ataque``, ``ataque_motivo`` e ``nivel_rotulo`` "prata" em
            cada nota (``tab.ataque_rotulo``; só com ``detector``).

    Returns:
        ``(entrada da tela, notas, nao_notas)``. Sem painel legível, as listas saem vazias
        e a entrada declara ``leitura`` com o motivo.
    """
    exibicoes = [{"t0": round(t0, 3), "t1": round(t1, 3)} for t0, t1 in tela.exibicoes]
    m = escolher_ou_mascara(imagem) if imagem is not None else None
    if m is None or not PASSO_MINIMO_PX <= m.passo <= PASSO_MAXIMO_PX:
        motivo = "sem painel legivel na imagem limpa"
        entrada = {
            "id": tela.id,
            "painel": list(tela.painel),
            "passo": None,
            "modo": tela.modo,
            "barlines_x": [],
            "exibicoes": [
                {**e, "tempo": {"medido": False, "motivo": motivo}, "passagens": []}
                for e in exibicoes
            ],
            "tempo": {"medido": False, "motivo": motivo},
            "leitura": motivo,
        }
        return entrada, [], []

    altura, largura = m.roi.shape[:2]
    if detector is not None:
        extra = {"com_escores": True} if rotulo_ataque else {}
        # o rótulo de ataque lê com o recorte alto (rodada 0210); o resto, como sempre
        roi, linhas_y = (
            recorte_alto(imagem, m) if rotulo_ataque else (m.roi, m.grade.linhas_y)
        )
        lidas = detector_tab.detectar(detector, roi, linhas_y, m.passo, **extra)
        tokens = tokens_da_rede(lidas, m.grade.glifos, m.x0, m.passo)
        barlines_roi = m.grade.barlines_x
    else:
        r = reconhecer_linha(
            m.roi,
            modelo,
            rotulos,
            dev,
            dir_simbolos=dir_simbolos,
            prefixo="",
            discriminador=discriminador,
        )
        tokens = tokens_do_quadro(r, m.x0)
        barlines_roi = r.get("barlines_x") or []
    colunas = colunas_do_quadro(tokens, m.passo)
    barlines = [m.x0 + int(bx) for bx in barlines_roi]
    painel = [m.x0, m.y0, m.x0 + largura, m.y0 + altura]

    if video is None:
        medidas = [
            {
                **e,
                "tempo": {"medido": False, "motivo": "leitura sem video"},
                "passagens": [],
            }
            for e in exibicoes
        ]
    else:
        centros, caixas = colunas_e_caixas(
            tokens, colunas, m.grade.glifos, m.x0, m.passo
        )
        medidas = [
            medir_exibicao(
                video, e["t0"], e["t1"], (m.y0, m.y0 + altura), centros, caixas, m.passo
            )
            for e in exibicoes
        ]
    medidos = [e["tempo"]["motivo"] for e in medidas if not e["tempo"]["medido"]]
    tempo = (
        {"medido": True, "motivo": None}
        if any(e["tempo"]["medido"] for e in medidas)
        else {"medido": False, "motivo": "; ".join(medidos) or MOTIVO_TEMPO}
    )
    entrada = {
        "id": tela.id,
        "painel": painel,
        "passo": round(m.passo, 2),
        "modo": tela.modo,
        "barlines_x": barlines,
        "exibicoes": medidas,
        "tempo": tempo,
        "leitura": "ok",
    }
    notas: list[dict] = []
    nao_notas: list[dict] = []
    rotulos_ataque = (
        ataque_rotulo.rotular(tokens, m.passo)
        if rotulo_ataque and detector is not None
        else [None] * len(tokens)
    )
    for tk, coluna, rot in zip(tokens, colunas, rotulos_ataque, strict=True):
        comum = {
            "tela": tela.id,
            "coluna": coluna,
            "corda": tk["corda"],
            "x_quadro": tk["x_quadro"],
            "x_centro_quadro": tk["x_centro_quadro"],
        }
        confianca = round(tk["confianca"], 3)
        if tk["classe"] in ALGARISMOS:
            base = {
                **comum,
                "compasso": compasso_de(tk["x_quadro"], barlines),
                "casa": int(tk["classe"]),
                "tecnica": tk["tecnica"] if detector is not None else None,
                "confianca": confianca,
            }
            if rot is not None:
                base["ataque"], base["ataque_motivo"] = rot
                base["nivel_rotulo"] = "prata"
            notas.extend(entradas_da_nota(base, medidas))
            continue
        registro = {**comum, "classe": tk["classe"], "confianca": confianca}
        if tk["simbolo_cru"] is not None:
            registro["simbolo_cru"] = tk["simbolo_cru"]
        if tk["casa_recuperada"] is not None:
            registro["casa_recuperada"] = tk["casa_recuperada"]
        nao_notas.append(registro)
    return entrada, notas, nao_notas


def transcrever_video(
    caminho: str,
    modelo: str | Path = MODELO_PADRAO,
    imagem: str = IMAGEM_PADRAO,
    telas_lidas: list[Tela] | None = None,
    leitor_notas: str = LEITOR_PADRAO,
    detector: str | Path = DETECTOR_PADRAO,
    rotulo_ataque: bool = False,
) -> dict:
    """Lê todas as telas de um vídeo e devolve o JSON v1, com o tempo por exibição.

    Args:
        caminho: caminho do vídeo (sempre lido por ``tab.leitor``).
        modelo: classificador de glifos (leitor ``glifos``).
        imagem: ``"quadro"`` ou ``"mediana"`` (ver ``imagem_da_tela``).
        telas_lidas: telas já medidas por ``tab.telas``; se ``None``, o vídeo é segmentado
            aqui. Serve para medir variantes sem refazer a presença.
        leitor_notas: ``"rede"`` ou ``"glifos"`` (``LEITORES``).
        detector: pesos do ``DetectorTab`` (leitor ``rede``).
        rotulo_ataque: rótulo de ataque por nota com a faixa "não sei" (rodada 0205). Só
            com o leitor ``rede`` e os pesos ``ataque_rotulo.DETECTOR_CALIBRADO``.

    Returns:
        O dicionário do esquema ``chorinho/video@1``.

    Raises:
        ValueError: leitor desconhecido, ou rótulo de ataque com leitor ou pesos para os
            quais os limiares não foram escolhidos.
    """
    if leitor_notas not in LEITORES:
        raise ValueError(f"leitor desconhecido: {leitor_notas!r}")
    if rotulo_ataque and (
        leitor_notas != "rede"
        or Path(detector).resolve() != ataque_rotulo.DETECTOR_CALIBRADO.resolve()
    ):
        raise ValueError(
            "rotulo_ataque exige o leitor rede com os pesos "
            f"{ataque_rotulo.DETECTOR_CALIBRADO}"
        )
    if leitor_notas == "rede":
        rede_tab = detector_tab.carregar(Path(detector))
        rede, rotulos, dev, discriminador = None, None, None, None
        modelo_usado = detector
    else:
        rede_tab = None
        rede, rotulos, dev = carregar_modelo(str(modelo))
        discriminador = carregar()
        modelo_usado = modelo
    dir_simbolos = str(VIDEO_SIMBOLOS / _slug(caminho))
    lista = telas_lidas if telas_lidas is not None else telas(caminho)
    telas_v1: list[dict] = []
    notas: list[dict] = []
    nao_notas: list[dict] = []
    for tela in lista:
        img = imagem_da_tela(caminho, tela, imagem)
        entrada, nts, nns = ler_tela(
            img,
            tela,
            rede,
            rotulos,
            dev,
            discriminador,
            dir_simbolos,
            video=caminho,
            detector=rede_tab,
            rotulo_ataque=rotulo_ataque,
        )
        telas_v1.append(entrada)
        notas.extend(nts)
        nao_notas.extend(nns)
    info = leitor.info(caminho)
    arquivo = _relativo(caminho, acervo())
    partes = arquivo.split("/")
    return montar_v1(
        video={
            "arquivo": arquivo,
            "canal": partes[0] if len(partes) > 1 else None,
            "duracao_s": round(float(info.get("duracao_s") or 0.0), 2),
            "codec": info.get("codec"),
        },
        gerado_por={
            "modelo": _relativo(str(modelo_usado), RAIZ),
            "leitor": leitor_notas,
            "commit": _commit(),
            "imagem": imagem,
            "em": datetime.now().isoformat(timespec="seconds"),
        },
        telas_v1=telas_v1,
        notas=notas,
        nao_notas=nao_notas,
    )


def _slug(caminho: str) -> str:
    """Nome de pasta seguro para o vídeo (usado nos recortes de símbolo).

    Args:
        caminho: caminho do vídeo.

    Returns:
        O nome do arquivo sem extensão, com caracteres especiais trocados por ``_``.
    """
    return re.sub(r"[^\w.-]+", "_", Path(caminho).stem).strip("_") or "video"


def _relativo(caminho: str, base: Path) -> str:
    """Caminho relativo a ``base``, ou só o nome do arquivo se estiver fora dela.

    Args:
        caminho: caminho a relativizar.
        base: pasta de referência.

    Returns:
        O caminho relativo, em barras ``/``.
    """
    try:
        return Path(caminho).resolve().relative_to(base.resolve()).as_posix()
    except OSError, ValueError:
        return Path(caminho).name


def _commit() -> str:
    """Hash curto do HEAD do git, ou ``desconhecido`` se não houver git.

    Returns:
        O hash curto do commit atual.
    """
    try:
        saida = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
    except OSError, subprocess.SubprocessError:
        return "desconhecido"
    return saida.stdout.strip() or "desconhecido"


def _json_seguro(valor: object) -> object:
    """Converte tipos numpy que o ``json`` não serializa.

    Args:
        valor: objeto que o ``json`` não sabe escrever.

    Returns:
        O equivalente nativo do Python.

    Raises:
        TypeError: se o tipo não for conhecido.
    """
    if isinstance(valor, np.generic):
        return valor.item()
    if isinstance(valor, np.ndarray):
        return valor.tolist()
    raise TypeError(f"não serializável: {type(valor).__name__}")


def main() -> int:
    """CLI: ``python -m tab.video VIDEO --json saida.json``.

    Returns:
        ``0`` ao gravar o JSON.
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("video")
    ap.add_argument("--json", required=True, help="onde gravar o JSON v1")
    ap.add_argument("--leitor", choices=LEITORES, default=LEITOR_PADRAO)
    ap.add_argument("--modelo", default=str(MODELO_PADRAO), help="leitor glifos")
    ap.add_argument("--detector", default=str(DETECTOR_PADRAO), help="leitor rede")
    ap.add_argument("--imagem", choices=IMAGENS, default=IMAGEM_PADRAO)
    ap.add_argument(
        "--rotulo-ataque",
        action="store_true",
        help="ataque por nota com a faixa nao_sei (exige --detector calibrado)",
    )
    args = ap.parse_args()
    dados = transcrever_video(
        args.video,
        modelo=args.modelo,
        imagem=args.imagem,
        leitor_notas=args.leitor,
        detector=args.detector,
        rotulo_ataque=args.rotulo_ataque,
    )
    destino = Path(args.json)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(dados, ensure_ascii=False, indent=1, default=_json_seguro),
        encoding="utf-8",
    )
    r = dados["resumo"]
    gerado = dados["gerado_por"]
    print(
        f"modelo {gerado['modelo']} | commit {gerado['commit']} | imagem {gerado['imagem']}"
    )
    print(
        f"{r['telas']} telas, {r['notas']} notas, {r['nao_notas']} nao-notas "
        f"-> {destino}"
    )
    print(
        f"tempo: {r['notas_com_tempo']} notas com t_ini, {r['instantes_distintos']} "
        f"instantes, telas sem tempo {r['telas_sem_tempo']} | invariantes: "
        f"{'ok' if not validar_tempo(dados) else len(validar_tempo(dados)) + ' violacoes'}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

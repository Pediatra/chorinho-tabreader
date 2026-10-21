"""Alinhador tela -> áudio: o instante em que cada coluna da tablatura soa (trilha A2).

Entrada: o produto SEM o marcador (ver ``esconder_marcador``) e o áudio. Saída: por coluna de
cada exibição, ``t_audio`` no instante do ataque, com ``confianca`` e recusa explícita
(``t_audio`` nulo e ``motivo`` preenchido). Um tempo errado afirmado é pior que um tempo
ausente declarado.

O alinhador NÃO lê ``t_ini``, ``passagens``, ``tempo``, ``observadores``, nem ``passagem`` ou
``exibicao`` das notas. Por isso não usa ``agrupar_eventos`` de ``tab.audio_atraso``: ele exige
``t_ini``. Reaproveita de ``tab.audio_onsets``: ``espectrograma``, ``fluxo_espectral``,
``picos`` e ``midi_da_nota``.

Colunas abafadas (v2.1, rasgueado): pilhas de X sem altura (``colunas_abafadas``). Entram na
sequência da tela como ataques sem altura. Casam a um pico de fluxo forte com cosseno fixo
``COS_ABAFADA`` (nunca o cosseno de altura), não contam no cosseno médio nem em
``MIN_COLUNAS_CASADAS``, e a exibição é marcada ``rasgueado`` se ``LIMIAR_RASGUEADO`` ou mais das
suas colunas forem abafadas.

Métodos:

- ``onsets`` (padrão): candidatos = picos do fluxo espectral na janela da exibição; programação
  dinâmica que casa colunas a candidatos com índices crescentes. Pode pular candidatos (custo
  ``CUSTO_PULAR_PICO`` cada) e deixar colunas sem ataque (custo ``CUSTO_SEM_ATAQUE_V1`` cada).
  Termo de andamento ``LAMBDA_ANDAMENTO * |log(dt / (dc * T))|`` entre casamentos consecutivos.
- ``dtw`` (linha de base): DTW com início e fim livres (subsequência) entre os moldes das
  colunas e TODOS os quadros do perfil; o instante da coluna é o 1º quadro casado; depois
  encaixe no pico de fluxo mais próximo a ``RAIO_ENCAIXE_S``, se houver.

PRÉ-PROCESSAMENTO É PARTE DA MEDIÇÃO. As constantes abaixo foram fixadas ANTES de medir no
MVP. Mudar qualquer uma invalida a comparação entre execuções.

Perfil "nova energia" em um instante t, para cada MIDI de ``MIDI_MIN`` a ``MIDI_MAX``:
``max(0, média da magnitude em [t, t+0,15 s] - média em [t-0,10 s, t])``, no bin mais forte
(maior média na janela de depois) dentre os bins a até ``TOLERANCIA_CENTS`` de f0(m); se
nenhum, o bin mais próximo de f0(m). Com N_FFT 4096 a 22 050 Hz o bin tem 5,38 Hz: nas notas
graves nenhum bin cai dentro de 30 cents, então vale o bin mais próximo (limitação medida).

Confiança de uma coluna casada: ``cos1 * min(1, margem / MARGEM_CONFIANCA)``, com ``cos1`` o
cosseno do casamento e ``margem = cos1 - max(0, cos2)``, onde ``cos2`` é o maior cosseno de
OUTRO candidato a até ``RAIO_VIZINHANCA_S`` do escolhido (0 se não houver).

Uso::

    python -m tab.audio_alinhar --produto PRODUTO.json --video VIDEO --saida SAIDA.json \\
        [--metodo onsets|dtw] [--transposicao 0]
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import sys

import numpy as np

from .audio_extrair import garantir, ler
from .audio_onsets import espectrograma, fluxo_espectral, midi_da_nota, picos

#: Métodos aceitos pelo alinhador.
METODOS = ("onsets", "onsets_v1", "dtw")

#: Método usado quando a CLI não recebe ``--metodo``.
METODO_PADRAO = "onsets"

#: Métodos oferecidos na CLI (o dtw foi medido e fracassou; fica só no código).
METODOS_CLI = ("onsets", "onsets_v1")

#: Margem, em segundos, acrescentada de cada lado da exibição (``t0 - m`` a ``t1 + m``).
MARGEM_JANELA_S = 0.5

#: Margem extra da STFT de alturas, além da janela, para cobrir os 0,10 s de antes e 0,15 s de
#: depois de cada instante candidato.
MARGEM_ANALISE_S = 0.8

#: Tamanho da FFT do perfil de alturas, em amostras (5,38 Hz por bin a 22 050 Hz).
N_FFT_ALTURA = 4096

#: Passo da STFT de alturas, em amostras (11,6 ms a 22 050 Hz). Igual ao do fluxo.
PASSO_ALTURA = 256

#: Menor e maior MIDI do perfil (61 posições).
MIDI_MIN = 36
MIDI_MAX = 96

#: Janela de depois e de antes do perfil, em segundos.
JANELA_DEPOIS_S = 0.15
JANELA_ANTES_S = 0.10

#: Meia-largura, em cents, da busca do bin de cada MIDI.
TOLERANCIA_CENTS = 30.0

#: Deslocamentos em semitons e pesos do molde da coluna (fundamental, oitava, 12ª, 2ª oitava).
DESLOCAMENTOS_MOLDE = (0, 12, 19, 24)
PESOS_MOLDE = (1.0, 0.5, 0.33, 0.25)

#: Custo de pular um candidato de fluxo (pico que não é coluna: acorde rolado, ruído, fala).
CUSTO_PULAR_PICO = 0.05

#: [v1] Custo de deixar uma coluna sem ataque (recusa). Um casamento só vence a recusa se seu custo
#: (1 - cosseno, mais andamento) for menor que este valor.
CUSTO_SEM_ATAQUE_V1 = 0.5

#: [v2, método ``onsets``] Custo de uma coluna INTERNA ao trecho sem ataque (pontuação negativa).
CUSTO_SEM_ATAQUE = 0.2

#: [v2] Cosseno-base: casar a coluna c com o candidato j vale ``cos - BASE_COS``; só paga acima de 0,35.
BASE_COS = 0.35

#: [v2] Iteração do período: para quando T varia menos que esta fração.
TOL_T_ITERACAO = 0.02

#: [v2] Número máximo de rodadas do DP na iteração de T.
MAX_ITER_T = 4

#: [v2] Recusa a exibição inteira se menos colunas que isto forem casadas.
MIN_COLUNAS_CASADAS = 4


#: Peso do termo de andamento, em ``|log(razão do intervalo)|``.
LAMBDA_ANDAMENTO = 0.5

#: Quantil do fluxo acima do qual um candidato é "pico forte" para estimar o período T.
QUANTIL_PICO_FORTE = 0.75

#: Intervalos entre picos fortes fora de [min, max] (em s) não entram na mediana de T.
PERIODO_MIN_S = 0.20
PERIODO_MAX_S = 2.00

#: Mínimo de intervalos válidos para estimar T por mediana; abaixo disso usa-se a duração da
#: exibição dividida por N colunas.
MIN_INTERVALOS_PERIODO = 3

#: Raio, em segundos, em que outro candidato conta como vizinho para a margem da confiança.
RAIO_VIZINHANCA_S = 0.30

#: Margem (1 - cosseno) em que a confiança satura em 1.
MARGEM_CONFIANCA = 0.20

#: Cosseno mínimo do casamento de uma coluna; abaixo disso a coluna é recusada.
LIMIAR_COSSENO_COLUNA = 0.30

#: Cosseno médio mínimo da exibição; abaixo disso a exibição inteira é recusada.
LIMIAR_COSSENO_EXIBICAO = 0.40

#: Raio, em segundos, do encaixe do DTW no pico de fluxo mais próximo.
RAIO_ENCAIXE_S = 0.06

#: [v2.1] Cosseno fixo de uma coluna abafada (ataque sem altura) contra um pico de fluxo forte.
#: Não é cosseno de altura: entra só no DP, como ganho ``COS_ABAFADA - BASE_COS``. Fixado antes de
#: medir o efeito no acervo.
COS_ABAFADA = 0.5

#: [v2.1] Regra de coluna abafada (``colunas_abafadas``): cordas distintas e glifos com top-1
#: ``TOP1_ABAFADA`` que a coluna precisa ter. Com 3 cordas a regra pegava dígitos de acorde.
MIN_CORDAS_ABAFADA = 4
MIN_QUINZE_ABAFADA = 4
TOP1_ABAFADA = "15"

#: Classe do X no leitor ``rede`` (decisão 0010): o glifo conta como X sem olhar o top-1.
CLASSE_X = "x"

#: [v2.1] Fração de colunas abafadas a partir da qual a exibição é um rasgueado.
LIMIAR_RASGUEADO = 0.20

#: Número de posições do perfil (MIDI_MIN a MIDI_MAX).
N_POSICOES = MIDI_MAX - MIDI_MIN + 1


def parametros_do_alinhador() -> dict:
    """Constantes do alinhador, para gravar junto da saída.

    Returns:
        Dicionário com todas as constantes de medição deste módulo.
    """
    return {
        "MARGEM_JANELA_S": MARGEM_JANELA_S,
        "MARGEM_ANALISE_S": MARGEM_ANALISE_S,
        "N_FFT_ALTURA": N_FFT_ALTURA,
        "PASSO_ALTURA": PASSO_ALTURA,
        "MIDI_MIN": MIDI_MIN,
        "MIDI_MAX": MIDI_MAX,
        "JANELA_DEPOIS_S": JANELA_DEPOIS_S,
        "JANELA_ANTES_S": JANELA_ANTES_S,
        "TOLERANCIA_CENTS": TOLERANCIA_CENTS,
        "DESLOCAMENTOS_MOLDE": list(DESLOCAMENTOS_MOLDE),
        "PESOS_MOLDE": list(PESOS_MOLDE),
        "CUSTO_PULAR_PICO": CUSTO_PULAR_PICO,
        "CUSTO_SEM_ATAQUE_V1": CUSTO_SEM_ATAQUE_V1,
        "CUSTO_SEM_ATAQUE": CUSTO_SEM_ATAQUE,
        "BASE_COS": BASE_COS,
        "TOL_T_ITERACAO": TOL_T_ITERACAO,
        "MAX_ITER_T": MAX_ITER_T,
        "MIN_COLUNAS_CASADAS": MIN_COLUNAS_CASADAS,
        "LAMBDA_ANDAMENTO": LAMBDA_ANDAMENTO,
        "QUANTIL_PICO_FORTE": QUANTIL_PICO_FORTE,
        "PERIODO_MIN_S": PERIODO_MIN_S,
        "PERIODO_MAX_S": PERIODO_MAX_S,
        "MIN_INTERVALOS_PERIODO": MIN_INTERVALOS_PERIODO,
        "RAIO_VIZINHANCA_S": RAIO_VIZINHANCA_S,
        "MARGEM_CONFIANCA": MARGEM_CONFIANCA,
        "LIMIAR_COSSENO_COLUNA": LIMIAR_COSSENO_COLUNA,
        "LIMIAR_COSSENO_EXIBICAO": LIMIAR_COSSENO_EXIBICAO,
        "RAIO_ENCAIXE_S": RAIO_ENCAIXE_S,
        "COS_ABAFADA": COS_ABAFADA,
        "MIN_CORDAS_ABAFADA": MIN_CORDAS_ABAFADA,
        "MIN_QUINZE_ABAFADA": MIN_QUINZE_ABAFADA,
        "TOP1_ABAFADA": TOP1_ABAFADA,
        "LIMIAR_RASGUEADO": LIMIAR_RASGUEADO,
    }


def colunas_abafadas(produto: dict) -> set[tuple[int, int]]:
    """Colunas abafadas (rasgueado): pilhas de X sem nota, como ``(tela, coluna)``.

    Uma coluna é abafada se tem ao menos ``MIN_CORDAS_ABAFADA`` ``nao_notas`` de classe
    ``tecnica`` ou ``CLASSE_X`` em cordas distintas, nenhuma ``nota`` na mesma tela e coluna,
    e ao menos ``MIN_QUINZE_ABAFADA`` desses glifos marcados como X: classe ``CLASSE_X``
    (leitor ``rede``) ou top-1 ``TOP1_ABAFADA`` no classificador (leitor de glifos, JSONs
    antigos). A regra foi medida em ``data/saida/audio/a4/rasgueado/medicao.txt``.

    Args:
        produto: JSON do produto (``tab.esquema``), com ``notas`` e ``nao_notas``.

    Returns:
        Conjunto de pares ``(tela, coluna)`` abafados; vazio se não houver.
    """
    notas_pos = {(int(n["tela"]), int(n["coluna"])) for n in produto.get("notas", [])}
    grupos: dict[tuple[int, int], list[dict]] = {}
    for nao_nota in produto.get("nao_notas", []):
        if nao_nota.get("classe") not in ("tecnica", CLASSE_X):
            continue
        chave = (int(nao_nota["tela"]), int(nao_nota["coluna"]))
        grupos.setdefault(chave, []).append(nao_nota)
    abafadas: set[tuple[int, int]] = set()
    for chave, glifos in grupos.items():
        if chave in notas_pos:
            continue
        cordas = {int(g["corda"]) for g in glifos}
        quinze = sum(
            1 for g in glifos if g.get("classe") == CLASSE_X or _top1(g) == TOP1_ABAFADA
        )
        if len(cordas) >= MIN_CORDAS_ABAFADA and quinze >= MIN_QUINZE_ABAFADA:
            abafadas.add(chave)
    return abafadas


def _top1(nao_nota: dict) -> str | None:
    """Top-1 do classificador de glifo de um ``nao_notas``.

    Args:
        nao_nota: registro de ``nao_notas`` do produto.

    Returns:
        Rótulo de maior confiança, ou ``None`` se o registro não trouxer ``simbolo_cru``.
    """
    simbolo = nao_nota.get("simbolo_cru") or {}
    top3 = simbolo.get("top3") or [[None]]
    return top3[0][0]


def _cos_abafada(fluxo_picos: np.ndarray) -> np.ndarray:
    """Cosseno de uma coluna abafada contra cada pico da exibição.

    Só pico com fluxo maior ou igual à mediana do fluxo dos picos da exibição vale
    ``COS_ABAFADA``. Os demais valem ``-inf``, o que impede o casamento: a coluna fica sem ataque.

    Args:
        fluxo_picos: fluxo espectral de cada candidato da exibição (não vazio).

    Returns:
        Vetor ``[candidatos]`` com ``COS_ABAFADA`` ou ``-inf``.
    """
    forte = fluxo_picos >= float(np.median(fluxo_picos))
    return np.where(forte, COS_ABAFADA, -np.inf)


def e_rasgueado(n_abafadas: int, n_colunas: int) -> bool:
    """Se a exibição é um rasgueado: fração de colunas abafadas em ``LIMIAR_RASGUEADO`` ou mais.

    Args:
        n_abafadas: colunas abafadas na sequência da exibição.
        n_colunas: total de colunas da sequência da exibição.

    Returns:
        ``True`` se ``n_abafadas / n_colunas >= LIMIAR_RASGUEADO``; ``False`` sem colunas.
    """
    if n_colunas <= 0:
        return False
    return n_abafadas / n_colunas >= LIMIAR_RASGUEADO


def esconder_marcador(produto: dict) -> dict:
    """Cópia do produto só com o que o alinhador pode ver.

    Por tela, guarda ``id``, as exibições (só ``t0`` e ``t1``), as colunas únicas da tela
    (coluna -> lista de pares ``[corda, casa]``, ordenados) e as colunas abafadas (``abafadas``,
    lista de colunas). Descarta tudo o mais, inclusive ``t_ini``, ``passagens``, ``tempo``,
    ``observadores``, ``passagem`` e ``exibicao`` das notas.

    Args:
        produto: JSON do produto (``tab.esquema``), com ``telas`` e ``notas``.

    Returns:
        ``{"telas": [{"id", "exibicoes": [{"t0", "t1"}], "colunas": {coluna: [[corda, casa]]},
        "abafadas": [coluna]}]}``.
    """
    abafadas_por_tela: dict[int, list[int]] = {}
    for tela_ab, coluna_ab in sorted(colunas_abafadas(produto)):
        abafadas_por_tela.setdefault(tela_ab, []).append(coluna_ab)
    colunas_por_tela: dict[int, dict[int, set[tuple[int, int]]]] = {}
    for nota in produto.get("notas", []):
        tela = int(nota["tela"])
        pares = colunas_por_tela.setdefault(tela, {}).setdefault(
            int(nota["coluna"]), set()
        )
        pares.add((int(nota["corda"]), int(nota["casa"])))
    telas = []
    for tela_bruta in produto["telas"]:
        tela = int(tela_bruta["id"])
        colunas = colunas_por_tela.get(tela, {})
        telas.append(
            {
                "id": tela,
                "exibicoes": [
                    {"t0": float(ex["t0"]), "t1": float(ex["t1"])}
                    for ex in tela_bruta["exibicoes"]
                ],
                "colunas": {
                    coluna: [[c, s] for c, s in sorted(pares)]
                    for coluna, pares in sorted(colunas.items())
                },
                "abafadas": sorted(abafadas_por_tela.get(tela, [])),
            }
        )
    return {"telas": telas}


def _bins_da_altura(freqs: np.ndarray, midi: int) -> np.ndarray:
    """Bins do perfil de um MIDI: os a até ``TOLERANCIA_CENTS`` de f0, ou o mais próximo.

    Args:
        freqs: frequências dos bins da STFT de alturas, em Hz.
        midi: número MIDI da posição do perfil.

    Returns:
        Índices dos bins candidatos (não vazio).
    """
    f0 = 440.0 * 2.0 ** ((midi - 69) / 12.0)
    desvio = np.abs(1200.0 * np.log2(np.maximum(freqs, 1e-9) / f0))
    dentro = np.flatnonzero(desvio <= TOLERANCIA_CENTS)
    if dentro.size == 0:
        dentro = np.array([int(np.argmin(np.abs(freqs - f0)))])
    return dentro


def perfis_em_instantes(
    mag: np.ndarray,
    tempos: np.ndarray,
    freqs: np.ndarray,
    instantes: np.ndarray,
    dt: float,
) -> np.ndarray:
    """Perfil "nova energia" (61 posições, norma L2 1) em cada instante.

    Cada instante usa o quadro mais próximo. A média de depois e de antes sai de uma soma
    acumulada da magnitude, então o custo é linear no número de instantes.

    Args:
        mag: magnitude ``[quadros, bins]`` da STFT de alturas.
        tempos: instante de cada quadro, na linha do vídeo.
        freqs: frequências dos bins, em Hz.
        instantes: instantes em que o perfil é pedido, em segundos do vídeo.
        dt: passo entre quadros, em segundos.

    Returns:
        Matriz ``[instantes, N_POSICOES]``; linhas nulas se não houver quadros ou o perfil
        for zero.
    """
    n = len(instantes)
    saida = np.zeros((n, N_POSICOES))
    n_quadros = mag.shape[0]
    if n_quadros == 0 or n == 0:
        return saida
    ks = np.clip(
        np.rint((np.asarray(instantes, dtype=np.float64) - tempos[0]) / dt).astype(int),
        0,
        n_quadros - 1,
    )
    n_depois = max(1, round(JANELA_DEPOIS_S / dt))
    n_antes = max(1, round(JANELA_ANTES_S / dt))
    acumulado = np.zeros((n_quadros + 1, mag.shape[1]))
    acumulado[1:] = np.cumsum(mag, axis=0)
    fim_depois = np.minimum(n_quadros, ks + n_depois)
    ini_antes = np.maximum(0, ks - n_antes)
    media_depois = (acumulado[fim_depois] - acumulado[ks]) / np.maximum(
        1, fim_depois - ks
    )[:, None]
    media_antes = (acumulado[ks] - acumulado[ini_antes]) / np.maximum(
        1, ks - ini_antes
    )[:, None]
    linhas = np.arange(n)
    for pos, midi in enumerate(range(MIDI_MIN, MIDI_MAX + 1)):
        bins = _bins_da_altura(freqs, midi)
        escolhido = bins[np.argmax(media_depois[:, bins], axis=1)]
        energia = media_depois[linhas, escolhido] - media_antes[linhas, escolhido]
        saida[:, pos] = np.maximum(energia, 0.0)
    normas = np.linalg.norm(saida, axis=1, keepdims=True)
    return saida / np.maximum(normas, 1e-12)


def molde_coluna(midis: list[int]) -> np.ndarray:
    """Molde de uma coluna: as alturas esperadas com harmônicos, norma L2 1.

    Para cada MIDI esperado ``m``, soma 1 em ``m``, 0,5 em ``m+12``, 0,33 em ``m+19`` e 0,25 em
    ``m+24``, dentro do intervalo do perfil.

    Args:
        midis: números MIDI das notas da coluna (acorde = várias).

    Returns:
        Vetor ``[N_POSICOES]``; nulo se nenhuma posição couber no intervalo.
    """
    vetor = np.zeros(N_POSICOES)
    for m in midis:
        for deslocamento, peso in zip(DESLOCAMENTOS_MOLDE, PESOS_MOLDE, strict=True):
            mm = m + deslocamento
            if MIDI_MIN <= mm <= MIDI_MAX:
                vetor[mm - MIDI_MIN] += peso
    norma = float(np.linalg.norm(vetor))
    return vetor / norma if norma > 0 else vetor


def alinhar_sequencia(
    custo: np.ndarray, tempos: np.ndarray, periodo: float
) -> tuple[list[int | None], float]:
    """Programação dinâmica: casa cada coluna a um candidato, ou a nenhum.

    Estado ``G[c, j]``: menor custo com a coluna ``c`` casada ao candidato ``j`` (último casado
    até aqui), contando as colunas sem ataque e os candidatos pulados antes dele. Transição de
    ``(c', j')`` para ``(c, j)``: ``CUSTO_SEM_ATAQUE_V1`` por coluna entre elas, ``CUSTO_PULAR_PICO``
    por candidato entre elas, mais o andamento e o custo do casamento.

    Args:
        custo: matriz ``[colunas, candidatos]`` com ``1 - cosseno``.
        tempos: instante de cada candidato, em segundos, em ordem crescente.
        periodo: estimativa do intervalo entre colunas consecutivas, em segundos.

    Returns:
        ``(atribuicao, custo_total)``: a atribuição tem, por coluna, o índice do candidato ou
        ``None`` (recusa). Se nenhum casamento compensar, todas as colunas saem como ``None``.
    """
    n_col, n_cand = custo.shape
    if n_cand == 0:
        return [None] * n_col, float(n_col * CUSTO_SEM_ATAQUE_V1)
    g = np.full((n_col, n_cand), np.inf)
    pred = np.full((n_col, n_cand, 2), -1, dtype=np.int64)
    for c in range(n_col):
        for j in range(n_cand):
            melhor = CUSTO_SEM_ATAQUE_V1 * c + CUSTO_PULAR_PICO * j + custo[c, j]
            arg = (-1, -1)
            if c > 0 and j > 0:
                cs = np.arange(c)
                js = np.arange(j)
                razao = (tempos[j] - tempos[js])[None, :] / (
                    ((c - cs) * periodo)[:, None]
                )
                andamento = LAMBDA_ANDAMENTO * np.abs(np.log(np.maximum(razao, 1e-9)))
                penal = (
                    (CUSTO_SEM_ATAQUE_V1 * (c - cs - 1))[:, None]
                    + (CUSTO_PULAR_PICO * (j - js - 1))[None, :]
                    + andamento
                )
                total = g[:c, :j] + penal + custo[c, j]
                k = int(np.argmin(total))
                ci, ji = divmod(k, j)
                if total[ci, ji] < melhor:
                    melhor = float(total[ci, ji])
                    arg = (ci, ji)
            g[c, j] = melhor
            pred[c, j] = arg
    colunas = np.arange(n_col)[:, None]
    candidatos = np.arange(n_cand)[None, :]
    fim = (
        g
        + CUSTO_SEM_ATAQUE_V1 * (n_col - 1 - colunas)
        + CUSTO_PULAR_PICO * (n_cand - 1 - candidatos)
    )
    k = int(np.argmin(fim))
    c, j = divmod(k, n_cand)
    total_fim = float(fim[c, j])
    sem_nenhum = float(n_col * CUSTO_SEM_ATAQUE_V1 + n_cand * CUSTO_PULAR_PICO)
    if sem_nenhum <= total_fim:
        return [None] * n_col, sem_nenhum
    atribuicao: list[int | None] = [None] * n_col
    while c >= 0:
        atribuicao[c] = int(j)
        pc, pj = (int(v) for v in pred[c, j])
        if pc < 0:
            break
        c, j = pc, pj
    return atribuicao, total_fim


def alinhar_dtw(custo: np.ndarray) -> tuple[np.ndarray, float]:
    """DTW de subsequência: início e fim livres, passos (1,0), (0,1) e (1,1).

    A coluna ``i`` é o primeiro quadro ``k`` do caminho que casa com ela. Início livre: a 1ª
    coluna pode casar com qualquer quadro. Fim livre: o caminho termina no melhor quadro da
    última coluna.

    Args:
        custo: matriz ``[colunas, quadros]`` com ``1 - cosseno``.

    Returns:
        ``(primeiro_quadro, custo_total)``: ``primeiro_quadro[i]`` é o índice do quadro da coluna
        ``i`` (ou ``-1`` se o caminho não passar por ela); ``custo_total`` é o custo acumulado.
    """
    n_col, n_fr = custo.shape
    primeiro = np.full(n_col, -1, dtype=np.int64)
    if n_col == 0 or n_fr == 0:
        return primeiro, float("inf")
    d = np.full((n_col, n_fr), np.inf)
    d[0, :] = custo[0, :]
    for i in range(1, n_col):
        d[i, 0] = custo[i, 0] + d[i - 1, 0]
        for k in range(1, n_fr):
            d[i, k] = custo[i, k] + min(d[i - 1, k], d[i, k - 1], d[i - 1, k - 1])
    k_fim = int(np.argmin(d[-1]))
    total = float(d[-1, k_fim])
    i, k = n_col - 1, k_fim
    while True:
        primeiro[i] = k
        if i == 0:
            break
        opcoes = [(d[i - 1, k], (i - 1, k))]
        if k > 0:
            opcoes.append((d[i, k - 1], (i, k - 1)))
            opcoes.append((d[i - 1, k - 1], (i - 1, k - 1)))
        _, (i, k) = min(opcoes, key=lambda o: o[0])
    return primeiro, total


def estimar_periodo(
    tempos_picos: np.ndarray,
    fluxo_picos: np.ndarray,
    duracao_exibicao: float,
    n_colunas: int,
) -> float:
    """Estimativa do intervalo típico entre colunas consecutivas, em segundos.

    Usa a mediana dos intervalos entre picos FORTES (fluxo no quantil ``QUANTIL_PICO_FORTE``
    ou acima), descartando os menores que ``PERIODO_MIN_S`` (acorde rolado) e os maiores que
    ``PERIODO_MAX_S``. Sem intervalos suficientes, usa ``duracao / N``.

    Args:
        tempos_picos: instantes dos candidatos, em ordem crescente.
        fluxo_picos: fluxo de cada candidato.
        duracao_exibicao: ``t1 - t0`` da exibição, em segundos.
        n_colunas: número de colunas da sequência.

    Returns:
        Período estimado, em segundos (positivo).
    """
    if tempos_picos.size >= 2:
        limiar = float(np.quantile(fluxo_picos, QUANTIL_PICO_FORTE))
        fortes = tempos_picos[fluxo_picos >= limiar]
        intervalos = np.diff(fortes)
        validos = intervalos[
            (intervalos >= PERIODO_MIN_S) & (intervalos <= PERIODO_MAX_S)
        ]
        if validos.size >= MIN_INTERVALOS_PERIODO:
            return float(np.median(validos))
    return max(duracao_exibicao / max(n_colunas, 1), 1e-3)


def confianca(cos1: float, cos_vizinhos: list[float]) -> float:
    """Confiança de um casamento: cosseno do escolhido vezes a margem sobre o vizinho.

    Args:
        cos1: cosseno do casamento escolhido.
        cos_vizinhos: cossenos dos OUTROS candidatos a até ``RAIO_VIZINHANCA_S``.

    Returns:
        ``cos1 * min(1, margem / MARGEM_CONFIANCA)`` em [0, 1], com
        ``margem = cos1 - max(0, maior cosseno dos vizinhos)``.
    """
    cos2 = max([0.0, *cos_vizinhos])
    margem = max(0.0, cos1 - cos2)
    return max(0.0, min(1.0, cos1)) * min(1.0, margem / MARGEM_CONFIANCA)


def _r(valor: float | None, casas: int = 6) -> float | None:
    """Arredonda para o JSON sair estável (sha256 repetível).

    Args:
        valor: número ou ``None``.
        casas: casas decimais.

    Returns:
        ``round(valor, casas)`` como ``float``, ou ``None``.
    """
    if valor is None:
        return None
    return round(float(valor), casas)


def alinhar_trecho(
    cos: np.ndarray, tempos: np.ndarray, periodo: float
) -> tuple[list[int | None], tuple[int, int] | None, float]:
    """Alinhamento LOCAL (v2): maximiza a pontuação e escolhe o trecho contínuo.

    Casar ``c`` com ``j`` vale ``cos[c, j] - BASE_COS``. Prefixo e sufixo de colunas são
    livres (não tocadas), e candidatos fora do trecho também. Dentro do trecho, cada coluna sem
    ataque custa ``CUSTO_SEM_ATAQUE`` e cada candidato pulado custa ``CUSTO_PULAR_PICO``; o
    andamento ``LAMBDA_ANDAMENTO * |log(dt / (dc * T))|`` usa ``dc`` com as colunas puladas.

    Args:
        cos: matriz ``[colunas, candidatos]`` de cossenos.
        tempos: instante de cada candidato, em ordem crescente.
        periodo: estimativa de T, em segundos.

    Returns:
        ``(atribuicao, trecho, pontuacao)``: ``atribuicao`` tem o índice do candidato por coluna
        (``None`` se não casada); ``trecho`` é ``(c_a, c_b)`` em índices de coluna ou ``None``
        se nada casou; ``pontuacao`` é a pontuação máxima (0 se nada casou).
    """
    n_col, n_cand = cos.shape
    atribuicao: list[int | None] = [None] * n_col
    if n_col == 0 or n_cand == 0:
        return atribuicao, None, 0.0
    g = np.zeros((n_col, n_cand))
    pred = np.full((n_col, n_cand, 2), -1, dtype=np.int64)
    for c in range(n_col):
        for j in range(n_cand):
            ganho = float(cos[c, j]) - BASE_COS
            melhor = 0.0
            arg = (-1, -1)
            if c > 0 and j > 0:
                cs = np.arange(c)
                js = np.arange(j)
                razao = (tempos[j] - tempos[js])[None, :] / (
                    ((c - cs) * periodo)[:, None]
                )
                andamento = LAMBDA_ANDAMENTO * np.abs(np.log(np.maximum(razao, 1e-9)))
                pen = (
                    (CUSTO_SEM_ATAQUE * (c - cs - 1))[:, None]
                    + (CUSTO_PULAR_PICO * (j - js - 1))[None, :]
                    + andamento
                )
                cand = g[:c, :j] - pen
                k = int(np.argmax(cand))
                ci, ji = divmod(k, j)
                if cand[ci, ji] > melhor:
                    melhor = float(cand[ci, ji])
                    arg = (ci, ji)
            g[c, j] = melhor + ganho
            pred[c, j] = arg
    k = int(np.argmax(g))
    c, j = divmod(k, n_cand)
    if g[c, j] <= 0.0:
        return atribuicao, None, 0.0
    pontuacao = float(g[c, j])
    fim_trecho = c
    ini_trecho = c
    while c >= 0:
        atribuicao[c] = int(j)
        ini_trecho = c
        pc, pj = (int(v) for v in pred[c, j])
        if pc < 0:
            break
        c, j = pc, pj
    return atribuicao, (ini_trecho, fim_trecho), pontuacao


def periodo_todos_intervalos(
    tempos_picos: np.ndarray, duracao_exibicao: float, n_colunas: int
) -> float:
    """T0 do método v2: mediana dos intervalos entre TODOS os picos da janela.

    Só entram intervalos em ``[PERIODO_MIN_S, PERIODO_MAX_S]``. Com menos de
    ``MIN_INTERVALOS_PERIODO`` deles, usa ``duracao / N``.

    Args:
        tempos_picos: instantes de todos os candidatos, em ordem crescente.
        duracao_exibicao: ``t1 - t0`` da exibição, em segundos.
        n_colunas: número de colunas da sequência.

    Returns:
        T0 em segundos (positivo).
    """
    if tempos_picos.size >= 2:
        intervalos = np.diff(tempos_picos)
        validos = intervalos[
            (intervalos >= PERIODO_MIN_S) & (intervalos <= PERIODO_MAX_S)
        ]
        if validos.size >= MIN_INTERVALOS_PERIODO:
            return float(np.median(validos))
    return max(duracao_exibicao / max(n_colunas, 1), 1e-3)


def periodo_pelos_pares(
    atribuicao: list[int | None], tempos_picos: np.ndarray
) -> float | None:
    """T recalculado: mediana de ``(t_j - t_j') / (c - c')`` nos pares casados consecutivos.

    Args:
        atribuicao: candidato por coluna (``None`` para não casada).
        tempos_picos: instantes dos candidatos.

    Returns:
        T em segundos, ou ``None`` se não houver dois casamentos.
    """
    casados = [(c, j) for c, j in enumerate(atribuicao) if j is not None]
    razoes = [
        (tempos_picos[j2] - tempos_picos[j1]) / (c2 - c1)
        for (c1, j1), (c2, j2) in itertools.pairwise(casados)
    ]
    if not razoes:
        return None
    mediana = float(np.median(razoes))
    return mediana if mediana > 0 else None


def alinhar_trecho_iterativo(
    cos: np.ndarray, tempos: np.ndarray, t0_periodo: float
) -> dict:
    """Iteração de T (v2): DP, recalcula T pelos pares casados, repete até convergir.

    Para quando ``|T_recalculado - T_usado| / T_usado < TOL_T_ITERACAO`` ou após
    ``MAX_ITER_T`` rodadas do DP. A saída é a da última rodada do DP.

    Args:
        cos: matriz ``[colunas, candidatos]`` de cossenos.
        tempos: instantes dos candidatos.
        t0_periodo: T0 (chute inicial), em segundos.

    Returns:
        Dicionário com ``atribuicao``, ``trecho``, ``pontuacao``, ``T0``, ``T_usado``
        (T da última rodada do DP), ``T_recalculado``, ``iteracoes`` e ``convergiu``.
    """
    t_usado = t0_periodo
    iteracoes = 0
    convergiu = False
    atrib: list[int | None] = []
    trecho: tuple[int, int] | None = None
    pontuacao = 0.0
    t_recalc: float | None = None
    t_usado_final = t_usado
    while iteracoes < MAX_ITER_T:
        iteracoes += 1
        t_usado_final = t_usado
        atrib, trecho, pontuacao = alinhar_trecho(cos, tempos, t_usado)
        t_recalc = periodo_pelos_pares(atrib, tempos)
        if t_recalc is None:
            break
        if abs(t_recalc - t_usado) / t_usado < TOL_T_ITERACAO:
            convergiu = True
            break
        t_usado = t_recalc
    return {
        "atribuicao": atrib,
        "trecho": trecho,
        "pontuacao": pontuacao,
        "T0": t0_periodo,
        "T_usado": t_usado_final,
        "T_recalculado": t_recalc,
        "iteracoes": iteracoes,
        "convergiu": convergiu,
    }


def _decidir_onsets_v2(
    tela: int,
    exibicao: int,
    sequencia: list[tuple[int, list[int]]],
    resumo: dict,
    cos_pk: np.ndarray,
    t_pk: np.ndarray,
    duracao: float,
    abafadas: set[int],
) -> tuple[dict, list[dict]]:
    """Decisão do método ``onsets`` (v2): trecho, T iterativo e recusas.

    Colunas abafadas casam com ``COS_ABAFADA`` e ficam fora do cosseno médio e de
    ``MIN_COLUNAS_CASADAS``, que contam só as colunas com altura.

    Args:
        tela: id da tela.
        exibicao: índice da exibição.
        sequencia: ``(coluna, [midis])`` da tela, em ordem crescente (abafada: ``[]``).
        resumo: resumo da exibição (preenchido aqui).
        cos_pk: cossenos ``[colunas, candidatos]``.
        t_pk: instantes dos candidatos.
        duracao: ``t1 - t0`` da exibição, em segundos.
        abafadas: colunas abafadas da tela.

    Returns:
        ``(resumo, registros)``.
    """
    n_col = len(sequencia)
    t0_periodo = periodo_todos_intervalos(t_pk, duracao, n_col)
    res = alinhar_trecho_iterativo(cos_pk, t_pk, t0_periodo)
    atrib = res["atribuicao"]
    trecho = res["trecho"]
    eh_abafada = [coluna in abafadas for coluna, _ in sequencia]
    casados = [c for c in range(n_col) if atrib[c] is not None and not eh_abafada[c]]
    casados_abafadas = [
        c for c in range(n_col) if atrib[c] is not None and eh_abafada[c]
    ]
    cosenos = [float(cos_pk[c, atrib[c]]) for c in casados]
    cos_medio = float(np.mean(cosenos)) if cosenos else 0.0
    resumo.update(
        {
            "T0_s": _r(t0_periodo),
            "T_usado_s": _r(res["T_usado"]),
            "T_recalculado_s": _r(res["T_recalculado"]),
            "T_estimado_s": _r(res["T_usado"]),
            "iteracoes_T": res["iteracoes"],
            "convergiu_T": res["convergiu"],
            "pontuacao_trecho": _r(res["pontuacao"], 4),
            "n_casadas": len(casados),
            "n_abafadas_casadas": len(casados_abafadas),
            "trecho_colunas": (
                [sequencia[trecho[0]][0], sequencia[trecho[1]][0]]
                if trecho is not None
                else None
            ),
            "trecho_tempo": (
                [_r(t_pk[atrib[trecho[0]]]), _r(t_pk[atrib[trecho[1]]])]
                if trecho is not None
                else None
            ),
            "cos_medio": _r(cos_medio, 4),
        }
    )
    motivo_exib = None
    if len(casados) < MIN_COLUNAS_CASADAS:
        motivo_exib = f"poucas colunas casadas: {len(casados)} < {MIN_COLUNAS_CASADAS}"
    elif cos_medio < LIMIAR_COSSENO_EXIBICAO:
        motivo_exib = f"cosseno medio {cos_medio:.3f} < {LIMIAR_COSSENO_EXIBICAO:.2f}"
    recusada = motivo_exib is not None
    resumo.update(
        {
            "recusada_exibicao": recusada,
            "motivo_exibicao": motivo_exib,
            "custo_total_normalizado": None,
            "n_afirmadas": 0,
        }
    )
    registros = []
    for c, (coluna, _) in enumerate(sequencia):
        fora = trecho is None or c < trecho[0] or c > trecho[1]
        j = atrib[c]
        if j is None:
            motivo = "fora_do_trecho" if fora else "sem_ataque_casado"
            registros.append(
                _registro(tela, exibicao, coluna, None, None, motivo, None)
            )
            continue
        if recusada:
            registros.append(
                _registro(tela, exibicao, coluna, None, None, "exibicao_recusada", None)
            )
            continue
        cos1 = float(cos_pk[c, j])
        if cos1 < LIMIAR_COSSENO_COLUNA:
            registros.append(
                _registro(tela, exibicao, coluna, None, None, "cosseno_baixo", cos1)
            )
            continue
        viz = _vizinhos(t_pk, t_pk[j], excluir=j)
        conf = confianca(cos1, [float(cos_pk[c, i]) for i in viz])
        registros.append(
            _registro(tela, exibicao, coluna, float(t_pk[j]), conf, None, cos1)
        )
    resumo["n_afirmadas"] = sum(1 for r in registros if r["t_audio"] is not None)
    return resumo, registros


def _registro(
    tela: int,
    exibicao: int,
    coluna: int,
    t_audio: float | None,
    conf: float | None,
    motivo: str | None,
    cos1: float | None,
) -> dict:
    """Uma linha da saída por coluna.

    Args:
        tela: id da tela.
        exibicao: índice da exibição dentro da tela.
        coluna: coluna da tela.
        t_audio: instante do ataque, ou ``None`` (recusa).
        conf: confiança em [0, 1], ou ``None`` se recusada.
        motivo: texto da recusa, ou ``None`` se afirmada.
        cos1: cosseno do casamento, para a curva e para depuração.

    Returns:
        Dicionário com ``tela``, ``exibicao``, ``coluna``, ``t_audio``, ``confianca``,
        ``motivo`` e ``cos``.
    """
    return {
        "tela": tela,
        "exibicao": exibicao,
        "coluna": coluna,
        "t_audio": _r(t_audio),
        "confianca": _r(conf, 4),
        "motivo": motivo,
        "cos": _r(cos1, 4),
    }


def _alinhar_exibicao(
    tela: int,
    exibicao: int,
    t0: float,
    t1: float,
    sequencia: list[tuple[int, list[int]]],
    amostras: np.ndarray,
    taxa: int,
    t_amostra0: float,
    metodo: str,
    abafadas: set[int],
) -> tuple[dict, list[dict]]:
    """Alinha as colunas de uma exibição ao áudio da janela ``[t0 - m, t1 + m]``.

    Args:
        tela: id da tela.
        exibicao: índice da exibição.
        t0: início da exibição, em segundos do vídeo.
        t1: fim da exibição, em segundos do vídeo.
        sequencia: ``(coluna, [midis])`` em ordem crescente de coluna.
        amostras: áudio ``int16`` mono do vídeo inteiro.
        taxa: taxa do áudio, em Hz.
        t_amostra0: instante, no vídeo, da amostra 0.
        metodo: ``"onsets"`` ou ``"dtw"``.
        abafadas: colunas abafadas da tela (vazio fora do método ``onsets``).

    Returns:
        ``(resumo_da_exibicao, registros_por_coluna)``.
    """
    a = t0 - MARGEM_JANELA_S
    b = t1 + MARGEM_JANELA_S
    mag_on, t_on, _ = espectrograma(amostras, taxa, t_amostra0, t0=a, t1=b)
    fluxo = fluxo_espectral(mag_on)
    idx_pk = np.asarray(picos(fluxo, t_on), dtype=np.int64)
    t_pk = t_on[idx_pk]
    f_pk = fluxo[idx_pk]
    mag_al, t_al, freqs = espectrograma(
        amostras,
        taxa,
        t_amostra0,
        n_fft=N_FFT_ALTURA,
        passo=PASSO_ALTURA,
        t0=a - MARGEM_ANALISE_S,
        t1=b + MARGEM_ANALISE_S,
    )
    dt = PASSO_ALTURA / taxa
    n_col = len(sequencia)
    resumo: dict = {
        "tela": tela,
        "exibicao": exibicao,
        "janela": [_r(a), _r(b)],
        "n_colunas": n_col,
        "n_candidatos": int(t_pk.size),
    }
    if n_col == 0:
        resumo.update(_resumo_recusada("sem_colunas", None, 0.0, 0))
        return resumo, []
    if t_pk.size == 0:
        resumo.update(_resumo_recusada("sem_candidatos", None, 0.0, n_col))
        registros = [
            _registro(tela, exibicao, c, None, None, "sem_candidatos", None)
            for c, _ in sequencia
        ]
        return resumo, registros

    moldes = np.stack([molde_coluna(m) for _, m in sequencia])
    p_pk = perfis_em_instantes(mag_al, t_al, freqs, t_pk, dt)
    cos_pk = moldes @ p_pk.T
    linhas_abafadas = [
        c for c, (coluna, _) in enumerate(sequencia) if coluna in abafadas
    ]
    if linhas_abafadas:
        cos_pk[linhas_abafadas] = _cos_abafada(f_pk)
    if metodo == "onsets":
        return _decidir_onsets_v2(
            tela, exibicao, sequencia, resumo, cos_pk, t_pk, t1 - t0, abafadas
        )
    periodo = estimar_periodo(t_pk, f_pk, t1 - t0, n_col)
    resumo["T_estimado_s"] = _r(periodo)

    escolhas: list[tuple[float, float, list[float]] | None]
    if metodo == "onsets_v1":
        atribuicao, custo_total = alinhar_sequencia(1.0 - cos_pk, t_pk, periodo)
        escolhas = []
        for c, j in enumerate(atribuicao):
            if j is None:
                escolhas.append(None)
                continue
            viz = _vizinhos(t_pk, t_pk[j], excluir=j)
            escolhas.append(
                (
                    float(t_pk[j]),
                    float(cos_pk[c, j]),
                    [float(cos_pk[c, i]) for i in viz],
                )
            )
    else:
        idx_fr = np.flatnonzero((t_al >= a) & (t_al <= b))
        if idx_fr.size == 0:
            resumo.update(_resumo_recusada("sem_quadros", None, 0.0, n_col))
            registros = [
                _registro(tela, exibicao, c, None, None, "sem_quadros", None)
                for c, _ in sequencia
            ]
            return resumo, registros
        p_fr = perfis_em_instantes(mag_al, t_al, freqs, t_al[idx_fr], dt)
        cos_fr = moldes @ p_fr.T
        primeiro, custo_total = alinhar_dtw(1.0 - cos_fr)
        escolhas = []
        for c in range(n_col):
            k = int(primeiro[c])
            if k < 0:
                escolhas.append(None)
                continue
            t_quadro = float(t_al[idx_fr[k]])
            proximos = np.flatnonzero(np.abs(t_pk - t_quadro) <= RAIO_ENCAIXE_S)
            if proximos.size:
                j = int(proximos[np.argmin(np.abs(t_pk[proximos] - t_quadro))])
                viz = _vizinhos(t_pk, t_pk[j], excluir=j)
                escolhas.append(
                    (
                        float(t_pk[j]),
                        float(cos_pk[c, j]),
                        [float(cos_pk[c, i]) for i in viz],
                    )
                )
            else:
                viz = _vizinhos(t_pk, t_quadro, excluir=-1)
                escolhas.append(
                    (
                        t_quadro,
                        float(cos_fr[c, k]),
                        [float(cos_pk[c, i]) for i in viz],
                    )
                )

    cosenos = [e[1] for e in escolhas if e is not None]
    cos_medio = float(np.mean(cosenos)) if cosenos else 0.0
    if not cosenos or cos_medio < LIMIAR_COSSENO_EXIBICAO:
        motivo_exib = (
            f"cosseno medio {cos_medio:.3f} < {LIMIAR_COSSENO_EXIBICAO:.2f}"
            if cosenos
            else "nenhuma coluna casada"
        )
        resumo.update(
            _resumo_recusada("exibicao_recusada", motivo_exib, cos_medio, n_col)
        )
        registros = [
            _registro(tela, exibicao, c, None, None, "exibicao_recusada", None)
            for c, _ in sequencia
        ]
        return resumo, registros

    registros = []
    for (coluna, _), e in zip(sequencia, escolhas, strict=True):
        if e is None:
            registros.append(
                _registro(tela, exibicao, coluna, None, None, "sem_ataque_casado", None)
            )
            continue
        t_audio, cos1, cos_viz = e
        if cos1 < LIMIAR_COSSENO_COLUNA:
            registros.append(
                _registro(tela, exibicao, coluna, None, None, "cosseno_baixo", cos1)
            )
            continue
        conf = confianca(cos1, cos_viz)
        registros.append(_registro(tela, exibicao, coluna, t_audio, conf, None, cos1))
    resumo.update(
        {
            "cos_medio": _r(cos_medio, 4),
            "custo_total_normalizado": _r(custo_total / n_col, 6),
            "recusada_exibicao": False,
            "motivo_exibicao": None,
            "n_afirmadas": sum(1 for r in registros if r["t_audio"] is not None),
        }
    )
    return resumo, registros


def _vizinhos(tempos_picos: np.ndarray, t: float, excluir: int) -> list[int]:
    """Índices dos candidatos a até ``RAIO_VIZINHANCA_S`` de ``t``, sem ``excluir``.

    Args:
        tempos_picos: instantes dos candidatos.
        t: instante de referência, em segundos.
        excluir: índice a deixar de fora (``-1`` para não excluir nenhum).

    Returns:
        Lista de índices (pode ser vazia).
    """
    proximos = np.flatnonzero(np.abs(tempos_picos - t) <= RAIO_VIZINHANCA_S)
    return [int(i) for i in proximos if int(i) != excluir]


def _resumo_recusada(
    motivo: str,
    detalhe: str | None,
    cos_medio: float,
    n_col: int,
) -> dict:
    """Campos de resumo de uma exibição recusada inteira.

    Args:
        motivo: categoria da recusa.
        detalhe: texto com o número que motivou (ou ``None``).
        cos_medio: cosseno médio das colunas casadas.
        n_col: número de colunas.

    Returns:
        Campos ``recusada_exibicao``, ``motivo_exibicao``, ``cos_medio``,
        ``custo_total_normalizado`` e ``n_afirmadas``.
    """
    return {
        "cos_medio": _r(cos_medio, 4),
        "custo_total_normalizado": None,
        "recusada_exibicao": True,
        "motivo_exibicao": f"{motivo}: {detalhe}" if detalhe else motivo,
        "n_afirmadas": 0,
        "n_colunas_recusadas": n_col,
    }


def alinhar(
    oculto: dict,
    amostras: np.ndarray,
    taxa: int,
    t_amostra0: float,
    metodo: str = METODO_PADRAO,
    transposicao: int = 0,
) -> dict:
    """Alinha todas as colunas de todas as exibições ao áudio.

    Args:
        oculto: saída de ``esconder_marcador`` (nada de marcador).
        amostras: áudio ``int16`` mono do vídeo inteiro.
        taxa: taxa do áudio, em Hz.
        t_amostra0: instante, no vídeo, da amostra 0.
        metodo: ``"onsets"`` ou ``"dtw"``.
        transposicao: semitons de capotraste ou afinação diferente (0 para padrão E A D G B E).

    Returns:
        Dicionário com ``metodo``, ``transposicao``, ``parametros``, ``exibicoes`` (um resumo por
        exibição) e ``colunas`` (um registro por coluna de cada exibição).

    Raises:
        ValueError: se ``metodo`` não for ``onsets`` nem ``dtw``.
    """
    if metodo not in METODOS:
        raise ValueError(f"método desconhecido: {metodo}")
    exibicoes: list[dict] = []
    colunas: list[dict] = []
    for tela in oculto["telas"]:
        abafadas = set(tela.get("abafadas", [])) if metodo == "onsets" else set()
        sequencia = [
            (
                int(coluna),
                [
                    midi_da_nota(c, s, transposicao)
                    for c, s in tela["colunas"].get(coluna, [])
                ],
            )
            for coluna in sorted(set(tela["colunas"]) | abafadas)
        ]
        n_ab = sum(1 for coluna, _ in sequencia if coluna in abafadas)
        for idx, ex in enumerate(tela["exibicoes"]):
            resumo, regs = _alinhar_exibicao(
                int(tela["id"]),
                idx,
                float(ex["t0"]),
                float(ex["t1"]),
                sequencia,
                amostras,
                taxa,
                t_amostra0,
                metodo,
                abafadas,
            )
            resumo.setdefault("n_abafadas_casadas", 0)
            resumo["rasgueado"] = e_rasgueado(n_ab, len(sequencia))
            for reg in regs:
                reg["tipo"] = "abafada" if reg["coluna"] in abafadas else "nota"
            exibicoes.append(resumo)
            colunas.extend(regs)
    return {
        "metodo": metodo,
        "transposicao": transposicao,
        "parametros": parametros_do_alinhador(),
        "exibicoes": exibicoes,
        "colunas": colunas,
    }


def main() -> int:
    """Ponto de entrada da CLI: alinha as colunas de um produto a um vídeo.

    Returns:
        Código de saída (0 se deu certo).
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--produto", required=True, help="JSON do produto")
    parser.add_argument(
        "--video", required=True, help="vídeo de origem (somente leitura)"
    )
    parser.add_argument("--saida", required=True, help="JSON de saída")
    parser.add_argument("--metodo", choices=METODOS_CLI, default=METODO_PADRAO)
    parser.add_argument("--transposicao", type=int, default=0, help="semitons")
    args = parser.parse_args()

    with open(args.produto, encoding="utf-8") as f:
        produto = json.load(f)
    oculto = esconder_marcador(produto)
    flac, meta = garantir(os.path.abspath(args.video))
    amostras, taxa = ler(flac)
    saida = alinhar(
        oculto,
        amostras,
        taxa,
        float(meta["t_amostra0"]),
        metodo=args.metodo,
        transposicao=args.transposicao,
    )
    saida["video"] = {
        "arquivo": os.path.abspath(args.video),
        "t_amostra0": _r(float(meta["t_amostra0"])),
        "taxa": taxa,
        "cache": meta["cache"],
    }
    afirmadas = sum(1 for c in saida["colunas"] if c["t_audio"] is not None)
    abafadas_afirmadas = sum(
        1
        for c in saida["colunas"]
        if c["tipo"] == "abafada" and c["t_audio"] is not None
    )
    print(
        f"metodo={args.metodo} exibicoes={len(saida['exibicoes'])} "
        f"colunas={len(saida['colunas'])} afirmadas={afirmadas} "
        f"recusadas={len(saida['colunas']) - afirmadas} "
        f"abafadas_afirmadas={abafadas_afirmadas}"
    )
    os.makedirs(os.path.dirname(os.path.abspath(args.saida)), exist_ok=True)
    texto = json.dumps(saida, ensure_ascii=False, indent=1, sort_keys=True)
    with open(args.saida, "w", encoding="utf-8") as f:
        f.write(texto + "\n")
    print(f"gravado: {args.saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

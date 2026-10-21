"""Mede qual termo do DP do alinhador (metodo onsets v2.1) escolhe o trecho curto.

Nao edita o modulo. Importa as funcoes de ``tab.audio_alinhar`` e, na analise de sensibilidade,
troca duas constantes do modulo SO neste processo, restaurando depois. Roda no container, em /app:

    python data/saida/audio/a4/dp_trecho/medir_dp_trecho.py
"""

from __future__ import annotations

import bisect
import itertools
import json
import os
import sys
from pathlib import Path

import numpy as np

from tab import audio_alinhar as al
from tab.audio_alinhar import alinhar, esconder_marcador
from tab.audio_extrair import garantir, ler
from tab.audio_onsets import espectrograma, fluxo_espectral, midi_da_nota, picos

SAIDA = Path("data/saida/audio/a4/dp_trecho")
FIG = SAIDA / "figuras"

PRODUTOS = {
    "room335": (
        "data/saida/audio/a2/produtos/shin_izumi_room_335.json",
        "data/saida/audio/a2/produtos/alinhado_v21_shin_izumi_room_335.json",
    ),
    "giant": (
        "data/saida/audio/a4/lote1/shin_izumi_giant_steps.json",
        "data/saida/audio/a4/lote1/alinhado_v21_shin_izumi_giant_steps.json",
    ),
    "mvp": (
        "data/saida/conserto_v2/mvp.json",
        "data/saida/audio/a2/alinhado_v21_mvp.json",
    ),
    "iwaki": (
        "data/saida/audio/a2/produtos/iwaki_la_vie_en_rose.json",
        "data/saida/audio/a2/produtos/alinhado_v21_iwaki_la_vie_en_rose.json",
    ),
}

# Recusados. O 6o caso nao estava na lista do pedido: escolhi giant tela 9 (1 casada, trecho [3,3]).
CASOS = [
    {"nome": "room335_t33", "produto": "room335", "tela": 33, "exib": 0, "twin": 35},
    {"nome": "room335_t12", "produto": "room335", "tela": 12, "exib": 0},
    {"nome": "room335_t25", "produto": "room335", "tela": 25, "exib": 0},
    {"nome": "giant_t5", "produto": "giant", "tela": 5, "exib": 0},
    {"nome": "giant_t13", "produto": "giant", "tela": 13, "exib": 0},
    {"nome": "giant_t9", "produto": "giant", "tela": 9, "exib": 0},
]
CONTROLES = [
    {"nome": "mvp_t3_ex0", "produto": "mvp", "tela": 3, "exib": 0},
    {"nome": "mvp_t3_ex1", "produto": "mvp", "tela": 3, "exib": 1},
    {"nome": "iwaki_t3_ex0", "produto": "iwaki", "tela": 3, "exib": 0},
    {"nome": "iwaki_t3_ex1", "produto": "iwaki", "tela": 3, "exib": 1},
]

LAMBDA0 = al.LAMBDA_ANDAMENTO
SEM0 = al.CUSTO_SEM_ATAQUE

SENSIBILIDADE = [
    ("linha_de_base", 1.0, 1.0),
    ("lambda x0,5", 0.5, 1.0),
    ("lambda x0,25", 0.25, 1.0),
    ("lambda x0", 0.0, 1.0),
    ("sem_ataque x0,5", 1.0, 0.5),
]


def _f(x: float | None) -> float | None:
    """Converte para ``float`` simples (JSON) ou ``None``.

    Args:
        x: numero ou ``None``.

    Returns:
        ``float(x)`` ou ``None``.
    """
    return None if x is None else float(x)


def aplicar_constantes(fator_lambda: float, fator_sem: float) -> None:
    """Troca as constantes do modulo ao vivo (so neste processo).

    Args:
        fator_lambda: multiplicador de ``LAMBDA_ANDAMENTO``.
        fator_sem: multiplicador de ``CUSTO_SEM_ATAQUE``.
    """
    al.LAMBDA_ANDAMENTO = LAMBDA0 * fator_lambda
    al.CUSTO_SEM_ATAQUE = SEM0 * fator_sem


def sequencia_da_tela(tela: dict) -> list[tuple[int, list[int]]]:
    """Mesma sequencia de ``alinhar``: colunas com nota ou abafadas, em ordem.

    Args:
        tela: tela do ``esconder_marcador``.

    Returns:
        Lista ``(coluna, [midis])``.
    """
    abafadas = set(tela.get("abafadas", []))
    return [
        (
            int(coluna),
            [midi_da_nota(c, s, 0) for c, s in tela["colunas"].get(coluna, [])],
        )
        for coluna in sorted(set(tela["colunas"]) | abafadas)
    ]


def preparar(tela: dict, idx: int, amostras: np.ndarray, taxa: int, t0_amostra: float) -> dict:
    """Reconstroi, com as funcoes do alinhador, picos, matriz de cossenos e T0.

    Espelha o inicio de ``_alinhar_exibicao`` (linhas 940-986 de tab/audio_alinhar.py).

    Args:
        tela: tela do ``esconder_marcador``.
        idx: indice da exibicao na tela.
        amostras: audio int16 mono do video.
        taxa: taxa do audio, em Hz.
        t0_amostra: instante, no video, da amostra 0.

    Returns:
        Dicionario com a sequencia, a matriz ``cos``, os candidatos e o fluxo.
    """
    ex = tela["exibicoes"][idx]
    t0, t1 = float(ex["t0"]), float(ex["t1"])
    abafadas = set(tela.get("abafadas", []))
    sequencia = sequencia_da_tela(tela)
    a = t0 - al.MARGEM_JANELA_S
    b = t1 + al.MARGEM_JANELA_S
    mag_on, t_on, _ = espectrograma(amostras, taxa, t0_amostra, t0=a, t1=b)
    fluxo = fluxo_espectral(mag_on)
    idx_pk = np.asarray(picos(fluxo, t_on), dtype=np.int64)
    t_pk = t_on[idx_pk]
    f_pk = fluxo[idx_pk]
    mag_al, t_al, freqs = espectrograma(
        amostras,
        taxa,
        t0_amostra,
        n_fft=al.N_FFT_ALTURA,
        passo=al.PASSO_ALTURA,
        t0=a - al.MARGEM_ANALISE_S,
        t1=b + al.MARGEM_ANALISE_S,
    )
    dt = al.PASSO_ALTURA / taxa
    moldes = np.stack([al.molde_coluna(m) for _, m in sequencia])
    p_pk = al.perfis_em_instantes(mag_al, t_al, freqs, t_pk, dt)
    cos = moldes @ p_pk.T
    linhas = [c for c, (col, _) in enumerate(sequencia) if col in abafadas]
    if linhas:
        cos[linhas] = al._cos_abafada(f_pk)
    return {
        "sequencia": sequencia,
        "cols": [col for col, _ in sequencia],
        "cos": cos,
        "t_pk": t_pk,
        "f_pk": f_pk,
        "t_on": t_on,
        "fluxo": fluxo,
        "t0": t0,
        "t1": t1,
        "a": a,
        "b": b,
        "duracao": t1 - t0,
    }


def cadeia_do_aligner(prep: dict) -> dict:
    """Roda a cadeia real do alinhador (T0 + DP iterativo) sobre a matriz preparada.

    Args:
        prep: saida de ``preparar``.

    Returns:
        Saida de ``alinhar_trecho_iterativo`` (atribuicao, trecho, pontuacao, T_usado...).
    """
    n = len(prep["sequencia"])
    t0p = al.periodo_todos_intervalos(prep["t_pk"], prep["duracao"], n)
    return al.alinhar_trecho_iterativo(prep["cos"], prep["t_pk"], t0p)


def decompor(
    cos: np.ndarray,
    tempos: np.ndarray,
    periodo: float,
    atrib: list[int | None],
    span: tuple[int, int],
) -> dict:
    """Decompoe a pontuacao de um caminho, dentro do intervalo de colunas ``span``.

    Mesma convencao do DP: colunas do intervalo sem casamento custam ``CUSTO_SEM_ATAQUE``
    (inclusive as de borda, se o intervalo for forcado); candidatos pulados entre o 1o e o
    ultimo casados custam ``CUSTO_PULAR_PICO``; andamento entre casamentos consecutivos.

    Args:
        cos: matriz ``[colunas, candidatos]``.
        tempos: instante de cada candidato, em segundos.
        periodo: T usado no DP, em segundos.
        atrib: candidato por coluna (``None`` se nao casada).
        span: ``(a, b)`` em indices de coluna, inclusive.

    Returns:
        Dicionario com os quatro termos, a pontuacao, contagens e mediana de |log|.
    """
    a, b = span
    casados = [(c, j) for c, j in enumerate(atrib) if j is not None and a <= c <= b]
    ganho = sum(float(cos[c, j]) - al.BASE_COS for c, j in casados)
    n_sem = max(0, (b - a + 1) - len(casados))
    if casados:
        n_pulados = (casados[-1][1] - casados[0][1] + 1) - len(casados)
    else:
        n_pulados = 0
    logs = []
    tempo = 0.0
    for (c1, j1), (c2, j2) in itertools.pairwise(casados):
        razao = (tempos[j2] - tempos[j1]) / ((c2 - c1) * periodo)
        lr = abs(float(np.log(max(razao, 1e-9))))
        logs.append(lr)
        tempo += al.LAMBDA_ANDAMENTO * lr
    sem = al.CUSTO_SEM_ATAQUE * n_sem
    pulos = al.CUSTO_PULAR_PICO * n_pulados
    return {
        "ganho": float(ganho),
        "sem_ataque": float(sem),
        "pulos": float(pulos),
        "tempo": float(tempo),
        "score": float(ganho - sem - pulos - tempo),
        "n_casadas": len(casados),
        "n_sem_ataque": n_sem,
        "n_pulados": n_pulados,
        "mediana_abs_log": float(np.median(logs)) if logs else None,
    }


def alinhar_forcado(
    cos: np.ndarray, tempos: np.ndarray, periodo: float, a: int, b: int
) -> tuple[list[int | None], float]:
    """Melhor caminho que COBRE o intervalo de colunas ``[a, b]``, com os mesmos custos.

    Diferente de ``alinhar_trecho``: o inicio nao e livre. As colunas de ``[a, b]`` antes do
    1o casamento e depois do ultimo custam ``CUSTO_SEM_ATAQUE`` cada. Colunas fora do intervalo
    nao entram. Le as constantes do modulo no momento da chamada.

    Args:
        cos: matriz ``[colunas, candidatos]``.
        tempos: instante de cada candidato, em ordem crescente.
        periodo: T, em segundos.
        a: primeira coluna (indice, inclusive) do intervalo forcado.
        b: ultima coluna (indice, inclusive) do intervalo forcado.

    Returns:
        ``(atribuicao, pontuacao)``; a atribuicao tem o tamanho de ``cos`` (fora = ``None``).
    """
    n_total, n_cand = cos.shape
    sub = cos[a : b + 1]
    n = sub.shape[0]
    atrib_full: list[int | None] = [None] * n_total
    if n == 0 or n_cand == 0:
        return atrib_full, 0.0
    g = np.full((n, n_cand), -np.inf)
    pred = np.full((n, n_cand, 2), -1, dtype=np.int64)
    for c in range(n):
        for j in range(n_cand):
            ganho = float(sub[c, j]) - al.BASE_COS
            melhor = -al.CUSTO_SEM_ATAQUE * c
            arg = (-1, -1)
            if c > 0 and j > 0:
                cs = np.arange(c)
                js = np.arange(j)
                razao = (tempos[j] - tempos[js])[None, :] / (
                    ((c - cs) * periodo)[:, None]
                )
                andamento = al.LAMBDA_ANDAMENTO * np.abs(
                    np.log(np.maximum(razao, 1e-9))
                )
                pen = (
                    (al.CUSTO_SEM_ATAQUE * (c - cs - 1))[:, None]
                    + (al.CUSTO_PULAR_PICO * (j - js - 1))[None, :]
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
    fim = g - (al.CUSTO_SEM_ATAQUE * (n - 1 - np.arange(n)))[:, None]
    k = int(np.argmax(fim))
    c, j = divmod(k, n_cand)
    pontuacao = float(fim[c, j])
    nenhum = -al.CUSTO_SEM_ATAQUE * n
    if nenhum >= pontuacao:
        return atrib_full, nenhum
    atrib = [None] * n
    while c >= 0:
        atrib[c] = int(j)
        pc, pj = (int(v) for v in pred[c, j])
        if pc < 0:
            break
        c, j = pc, pj
    for i, v in enumerate(atrib):
        atrib_full[a + i] = v
    return atrib_full, pontuacao


def forca_bruta(cos_sub: np.ndarray, tempos: np.ndarray, periodo: float) -> float:
    """Maximo por enumeracao de todos os casamentos crescentes (so para teste do DP).

    Args:
        cos_sub: matriz pequena ``[colunas, candidatos]``.
        tempos: instantes dos candidatos.
        periodo: T, em segundos.

    Returns:
        Melhor pontuacao forcada, incluindo a opcao de nenhum casamento.
    """
    n, m = cos_sub.shape
    melhor = -al.CUSTO_SEM_ATAQUE * n
    for k in range(1, min(n, m) + 1):
        for cols in itertools.combinations(range(n), k):
            for js in itertools.combinations(range(m), k):
                s = sum(cos_sub[c, j] - al.BASE_COS for c, j in zip(cols, js, strict=True))
                s -= al.CUSTO_SEM_ATAQUE * (n - k)
                s -= al.CUSTO_PULAR_PICO * (js[-1] - js[0] + 1 - k)
                for (c1, j1), (c2, j2) in itertools.pairwise(zip(cols, js, strict=True)):
                    razao = (tempos[j2] - tempos[j1]) / ((c2 - c1) * periodo)
                    s -= al.LAMBDA_ANDAMENTO * abs(np.log(max(razao, 1e-9)))
                melhor = max(melhor, float(s))
    return melhor


def teste_dp_forcado() -> int:
    """Confere o DP forcado contra enumeracao em 40 instancias pequenas aleatorias.

    Returns:
        Numero de instancias conferidas (sai com erro se alguma divergir).
    """
    rng = np.random.default_rng(0)
    for _ in range(40):
        n = int(rng.integers(2, 6))
        m = int(rng.integers(2, 6))
        cos = rng.uniform(0.0, 1.0, size=(n, m))
        tempos = np.cumsum(rng.uniform(0.05, 0.6, size=m))
        periodo = float(rng.uniform(0.1, 0.5))
        _, dp = alinhar_forcado(cos, tempos, periodo, 0, n - 1)
        bf = forca_bruta(cos, tempos, periodo)
        assert abs(dp - bf) < 1e-9, (dp, bf)
    return 40


def analisar(prep: dict, spans: dict[str, tuple[int, int]]) -> dict:
    """Chosen (aligner) versus forcado, com a decomposicao dos quatro termos.

    Args:
        prep: saida de ``preparar``.
        spans: nome -> ``(a, b)`` dos intervalos forcados.

    Returns:
        Dicionario com o caminho escolhido, cada forcado e o termo dominante.
    """
    cos, tempos = prep["cos"], prep["t_pk"]
    res = cadeia_do_aligner(prep)
    periodo = res["T_usado"]
    atrib = res["atribuicao"]
    trecho = res["trecho"]
    span_ch = trecho if trecho is not None else (0, -1)
    ch = decompor(cos, tempos, periodo, atrib, span_ch)
    assert abs(ch["score"] - res["pontuacao"]) < 1e-6, (ch["score"], res["pontuacao"])
    saida: dict = {
        "T_usado_s": periodo,
        "chosen": {
            **ch,
            "trecho_colunas": (
                [prep["cols"][trecho[0]], prep["cols"][trecho[1]]] if trecho else None
            ),
        },
        "forcados": {},
        "_atrib": {"chosen": atrib},
    }
    for nome, (a, b) in spans.items():
        atr_f, sc = alinhar_forcado(cos, tempos, periodo, a, b)
        df = decompor(cos, tempos, periodo, atr_f, (a, b))
        assert abs(df["score"] - sc) < 1e-6, (df["score"], sc)
        dif = {
            "ganho": df["ganho"] - ch["ganho"],
            "sem_ataque": -(df["sem_ataque"] - ch["sem_ataque"]),
            "pulos": -(df["pulos"] - ch["pulos"]),
            "tempo": -(df["tempo"] - ch["tempo"]),
        }
        # Contribuicao de cada termo a diferenca (forcado - chosen), com sinal de pontuacao.
        dominante = min(dif, key=dif.get)
        saida["forcados"][nome] = {
            **df,
            "a_col": prep["cols"][a],
            "b_col": prep["cols"][b],
            "forcado_menor_que_chosen": df["score"] < ch["score"],
            "diferenca_por_termo": {k: float(v) for k, v in dif.items()},
            "termo_que_mais_reduz": dominante,
        }
        saida["_atrib"][nome] = atr_f
    return saida


def carregar_audio(video: str) -> tuple[np.ndarray, int, float]:
    """Audio do video pelo mesmo caminho da CLI do alinhador (cache).

    Args:
        video: caminho do video no acervo.

    Returns:
        ``(amostras, taxa, t_amostra0)``.
    """
    flac, meta = garantir(os.path.abspath(video))
    amostras, taxa = ler(flac)
    return amostras, taxa, float(meta["t_amostra0"]), meta.get("cache")


def reproduzir(produto_path: str, alin_path: str, amostras, taxa, t0_amostra) -> dict:
    """Passo 1a: roda ``alinhar`` do modulo na tela inteira e confere com o JSON salvo.

    Args:
        produto_path: JSON do produto.
        alin_path: JSON de alinhamento salvo (v2.1, onsets).
        amostras: audio int16 mono.
        taxa: taxa do audio.
        t0_amostra: instante da amostra 0.

    Returns:
        Contagens de colunas identicas e de exibicoes conferidas.
    """
    with open(produto_path, encoding="utf-8") as f:
        produto = json.load(f)
    with open(alin_path, encoding="utf-8") as f:
        antigo = json.load(f)
    nova = alinhar(esconder_marcador(produto), amostras, taxa, t0_amostra, metodo="onsets")
    chave = lambda r: (r["tela"], r["exibicao"], r["coluna"])  # noqa: E731
    novo_col = {chave(r): r for r in nova["colunas"]}
    campos = ["t_audio", "confianca", "motivo", "cos", "tipo"]
    identicas = 0
    divergentes = []
    for r in antigo["colunas"]:
        n = novo_col.get(chave(r))
        if n is not None and all(n.get(c) == r.get(c) for c in campos):
            identicas += 1
        else:
            divergentes.append(chave(r))
    novo_ex = {(e["tela"], e["exibicao"]): e for e in nova["exibicoes"]}
    ex_ok = 0
    campos_ex = [
        "n_casadas",
        "pontuacao_trecho",
        "trecho_colunas",
        "T_usado_s",
        "cos_medio",
        "recusada_exibicao",
    ]
    for e in antigo["exibicoes"]:
        n = novo_ex.get((e["tela"], e["exibicao"]), {})
        if all(n.get(c) == e.get(c) for c in campos_ex):
            ex_ok += 1
    return {
        "colunas_identicas": identicas,
        "colunas_total": len(antigo["colunas"]),
        "primeiras_divergentes": divergentes[:10],
        "exibicoes_identicas": ex_ok,
        "exibicoes_total": len(antigo["exibicoes"]),
        "parametros_iguais": nova["parametros"] == antigo["parametros"],
    }


def tela_e_idx(produto_oculto: dict, tela_id: int) -> dict:
    """Tela pelo id, no produto oculto.

    Args:
        produto_oculto: saida de ``esconder_marcador``.
        tela_id: id da tela.

    Returns:
        Dicionario da tela.
    """
    for t in produto_oculto["telas"]:
        if int(t["id"]) == tela_id:
            return t
    raise KeyError(tela_id)


def span_por_colunas(cols: list[int], c_ini: int, c_fim: int) -> tuple[int, int]:
    """Converte um intervalo de numeros de coluna em indices da sequencia.

    Args:
        cols: numeros de coluna da sequencia, em ordem crescente.
        c_ini: 1a coluna (numero) do intervalo.
        c_fim: ultima coluna (numero) do intervalo.

    Returns:
        ``(a, b)`` em indices, inclusive.
    """
    a = bisect.bisect_left(cols, c_ini)
    b = bisect.bisect_right(cols, c_fim) - 1
    return a, b


def figura(nome: str, prep: dict, resultado: dict, titulo: str) -> None:
    """Grafico do fluxo, dos picos, do caminho escolhido e dos forcados no eixo do tempo.

    Args:
        nome: nome do arquivo (sem extensao).
        prep: saida de ``preparar``.
        resultado: saida de ``analisar``.
        titulo: titulo do grafico.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cores = {"chosen": "#0072B2", "todas": "#E69F00", "twin35": "#009E73"}
    rotulos = {
        "chosen": "aligner (escolhido)",
        "todas": "forcado: todas as colunas",
        "twin35": "forcado: trecho da tela gemea 35",
    }
    fig, ax = plt.subplots(figsize=(11, 4.6), dpi=130)
    ax.axvspan(prep["t0"], prep["t1"], color="#eeeeee", zorder=0, label="exibicao")
    ax.plot(prep["t_on"], prep["fluxo"], color="#aaaaaa", lw=0.8, zorder=1, label="fluxo espectral")
    ax.scatter(prep["t_pk"], prep["f_pk"], s=9, color="#444444", zorder=2, label="picos (candidatos)")
    niveis = {"chosen": 1.0}
    niv = 0.78
    for nome_v in resultado["forcados"]:
        niveis[nome_v] = niv
        niv -= 0.12
    altura_max = float(np.max(prep["fluxo"])) if prep["fluxo"].size else 1.0
    for variante, nivel in niveis.items():
        atrib = resultado["_atrib"][variante]
        y = nivel * altura_max
        xs, cols = [], []
        for c, j in enumerate(atrib):
            if j is not None:
                xs.append(float(prep["t_pk"][j]))
                cols.append(prep["cols"][c])
        cor = cores.get(variante, "#CC79A7")
        if xs:
            ax.scatter(xs, [y] * len(xs), s=36, color=cor, zorder=4, label=rotulos.get(variante, variante))
            for x, col in zip(xs, cols, strict=True):
                ax.annotate(f"c{col}", (x, y), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=7, color=cor)
        ax.axhline(y, color=cor, lw=0.4, alpha=0.4, zorder=0)
    ax.set_xlabel("instante do video (s)")
    ax.set_ylabel("fluxo espectral (linhas: nivel de cada caminho)")
    ax.set_yticks([])
    ax.set_title(titulo, fontsize=10)
    ax.legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False)
    fig.tight_layout()
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{nome}.png")
    plt.close(fig)


def main() -> int:
    """Roda os passos 0 a 4 e grava ``resultados.json``.

    Returns:
        Codigo de saida (0 se deu certo).
    """
    SAIDA.mkdir(parents=True, exist_ok=True)
    n_teste = teste_dp_forcado()
    print(f"[teste] DP forcado == enumeracao em {n_teste} instancias aleatorias")

    audio: dict[str, tuple] = {}
    produtos_oc: dict[str, dict] = {}
    for chave, (prod, alin) in PRODUTOS.items():
        with open(alin, encoding="utf-8") as f:
            video = json.load(f)["video"]["arquivo"]
        amostras, taxa, t0a, cache = carregar_audio(video)
        audio[chave] = (amostras, taxa, t0a)
        print(f"[audio] {chave}: cache={cache} taxa={taxa}")
        with open(prod, encoding="utf-8") as f:
            produtos_oc[chave] = esconder_marcador(json.load(f))

    # Passo 1a: reproducao da tela inteira contra o JSON salvo.
    passo1a = {}
    for chave, (prod, alin) in PRODUTOS.items():
        r = reproduzir(prod, alin, *audio[chave])
        passo1a[chave] = r
        print(
            f"[1a] {chave}: colunas identicas {r['colunas_identicas']} de {r['colunas_total']}; "
            f"exibicoes identicas {r['exibicoes_identicas']} de {r['exibicoes_total']}; "
            f"parametros iguais={r['parametros_iguais']}"
        )

    prep_cache: dict[str, dict] = {}

    def prep_de(chave_prod: str, tela_id: int, exib: int) -> dict:
        k = f"{chave_prod}:{tela_id}:{exib}"
        if k not in prep_cache:
            tela = tela_e_idx(produtos_oc[chave_prod], tela_id)
            am, tx, t0a = audio[chave_prod]
            prep_cache[k] = preparar(tela, exib, am, tx, t0a)
        return prep_cache[k]

    def spans_de(caso: dict, prep: dict) -> dict[str, tuple[int, int]]:
        spans = {"todas": (0, len(prep["sequencia"]) - 1)}
        if "twin" in caso:
            tela_gemea = tela_e_idx(produtos_oc[caso["produto"]], caso["twin"])
            am, tx, t0a = audio[caso["produto"]]
            prep_g = preparar(tela_gemea, 0, am, tx, t0a)
            res_g = cadeia_do_aligner(prep_g)
            if res_g["trecho"] is not None:
                c_ini = prep_g["cols"][res_g["trecho"][0]]
                c_fim = prep_g["cols"][res_g["trecho"][1]]
                spans["twin35"] = span_por_colunas(prep["cols"], c_ini, c_fim)
        return spans

    # Passo 2: recusados e controles.
    passo2 = []
    casos_prep: dict[str, tuple] = {}
    for caso in CASOS + CONTROLES:
        prep = prep_de(caso["produto"], caso["tela"], caso["exib"])
        spans = spans_de(caso, prep)
        r = analisar(prep, spans)
        casos_prep[caso["nome"]] = (prep, r)
        linha = {
            "caso": caso["nome"],
            "tipo": "recusado" if caso in CASOS else "controle",
            "T_usado_s": r["T_usado_s"],
            "n_colunas": len(prep["sequencia"]),
            "chosen": {k: v for k, v in r["chosen"].items()},
            "forcados": {k: v for k, v in r["forcados"].items()},
        }
        passo2.append(linha)
        ch = r["chosen"]
        print(
            f"[2] {caso['nome']}: T={r['T_usado_s']:.4f} casadas={ch['n_casadas']} "
            f"trecho={ch['trecho_colunas']} score_chosen={ch['score']:.4f} "
            f"(ganho={ch['ganho']:.3f} sem={ch['sem_ataque']:.3f} pulos={ch['pulos']:.3f} "
            f"tempo={ch['tempo']:.3f} mediana|log|={ch['mediana_abs_log']})"
        )
        for nome_f, f in r["forcados"].items():
            print(
                f"    forcado {nome_f} [{f['a_col']}..{f['b_col']}]: score={f['score']:.4f} "
                f"casadas={f['n_casadas']} ganho={f['ganho']:.3f} sem={f['sem_ataque']:.3f} "
                f"pulos={f['pulos']:.3f} tempo={f['tempo']:.3f} "
                f"mediana|log|={f['mediana_abs_log']} menor={f['forcado_menor_que_chosen']} "
                f"termo={f['termo_que_mais_reduz']}"
            )

    # Passo 3: sensibilidade (so constantes do modulo, restauradas no fim).
    passo3 = []
    base_controles: dict[str, dict] = {}
    try:
        for nome_cfg, fl, fs in SENSIBILIDADE:
            aplicar_constantes(fl, fs)
            linha = {"config": nome_cfg, "lambda": al.LAMBDA_ANDAMENTO, "custo_sem": al.CUSTO_SEM_ATAQUE, "recusados": [], "controles": []}
            for caso in CASOS:
                prep, _ = casos_prep[caso["nome"]]
                r = analisar(prep, spans_de(caso, prep))
                ch = r["chosen"]
                linha["recusados"].append(
                    {
                        "caso": caso["nome"],
                        "casadas_chosen": ch["n_casadas"],
                        "aceita_se_>=4": ch["n_casadas"] >= al.MIN_COLUNAS_CASADAS,
                        "score_chosen": ch["score"],
                        "score_forcado_todas": r["forcados"]["todas"]["score"],
                        "forcado_menor": r["forcados"]["todas"]["forcado_menor_que_chosen"],
                        "termo": r["forcados"]["todas"]["termo_que_mais_reduz"],
                    }
                )
            for chave in ("mvp", "iwaki"):
                tela_id = 3
                am, tx, t0a = audio[chave]
                tela = tela_e_idx(produtos_oc[chave], tela_id)
                oc = {"telas": [tela]}
                nova = alinhar(oc, am, tx, t0a, metodo="onsets")
                pontos = {(r_["tela"], r_["exibicao"], r_["coluna"]): r_["t_audio"] for r_ in nova["colunas"]}
                if nome_cfg == "linha_de_base":
                    base_controles[chave] = pontos
                linha.setdefault("_pontos", {})[chave] = pontos
            linha["controles"] = []
            for chave in ("mvp", "iwaki"):
                base = base_controles.get(chave, linha["_pontos"][chave])
                novo = linha["_pontos"][chave]
                y = sum(1 for v in base.values() if v is not None)
                x_mais = 0
                x_nulo = 0
                for k, v in base.items():
                    w = novo.get(k)
                    if v is not None and w is not None and abs(v - w) > 0.030:
                        x_mais += 1
                    elif (v is None) != (w is None):
                        x_nulo += 1
                linha["controles"].append({"controle": chave, "mudou_mais_de_30ms": x_mais, "mudou_nulo_vs_valor": x_nulo, "afirmadas_base": y})
            del linha["_pontos"]
            passo3.append(linha)
            print(f"[3] {nome_cfg}: " + "; ".join(f"{x['caso']} casadas={x['casadas_chosen']} forcado_menor={x['forcado_menor']}" for x in linha["recusados"]))
            print("    controles: " + "; ".join(f"{c['controle']} X={c['mudou_mais_de_30ms']} (nulo/valor {c['mudou_nulo_vs_valor']}) de Y={c['afirmadas_base']}" for c in linha["controles"]))
    finally:
        aplicar_constantes(1.0, 1.0)

    # Passo 4: figuras dos recusados.
    for caso in CASOS:
        prep, r = casos_prep[caso["nome"]]
        titulo = f"{caso['nome']}: escolhido {r['chosen']['n_casadas']} casadas, T={r['T_usado_s']:.3f} s"
        figura(caso["nome"], prep, r, titulo)

    saida = {
        "passo1a_reproducao": passo1a,
        "passo2": passo2,
        "passo3_sensibilidade": passo3,
        "constantes": {"LAMBDA_ANDAMENTO": LAMBDA0, "CUSTO_SEM_ATAQUE": SEM0, "CUSTO_PULAR_PICO": al.CUSTO_PULAR_PICO, "BASE_COS": al.BASE_COS},
    }
    with open(SAIDA / "resultados.json", "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=1)
    print(f"gravado: {SAIDA / 'resultados.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

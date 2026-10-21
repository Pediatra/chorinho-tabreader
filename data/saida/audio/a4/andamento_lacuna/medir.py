"""Mede um termo de andamento que aceita lacunas de multiplos inteiros de T (rodada andamento_lacuna).

Hipotese: andamento = min sobre m em 1..K de [ lambda*|log(dt/(m*dc*T))| + kappa*(m-1) ].
So o termo de andamento de ``alinhar_trecho`` muda; o resto do alinhador (v2.1) e o mesmo.

Nao edita o modulo. Troca ``al.alinhar_trecho`` SO neste processo e restaura no fim.
Roda no container, em /app:

    python data/saida/audio/a4/andamento_lacuna/medir.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

import numpy as np

from tab import audio_alinhar as al
from tab import audio_produto as ap
from tab.audio_alinhar import alinhar, esconder_marcador
from tab.audio_extrair import TAXA_PADRAO, VERSAO_CONVENCAO, caminho_no_cache, ler
from tab.audio_onsets import espectrograma, fluxo_espectral, picos
from tab.caminhos import acervo
from tab.censo import chave_do_arquivo

SAIDA = Path("data/saida/audio/a4/andamento_lacuna")
FIG = SAIDA / "figuras"
CACHE = SAIDA / "cache"
# MEDIR_PARTE="i/n": so calcula o cache dos videos de indice % n == i (execucao paralela).
# Sem a variavel, roda tudo e grava resultados.json a partir do cache.
PARTE = (
    tuple(int(x) for x in os.environ["MEDIR_PARTE"].split("/"))
    if os.environ.get("MEDIR_PARTE")
    else None
)
GOLD = Path("data/gold/audio")
K_MAX = 3
LIMIAR_MUDANCA_S = 0.030
ORIGINAL = al.alinhar_trecho

A2 = "data/saida/audio/a2"
LOTE1 = "data/saida/audio/a4/lote1"
VIDEOS: dict[str, tuple[str, str]] = {
    "mvp": ("data/saida/conserto_v2/mvp.json", f"{A2}/alinhado_v21_mvp.json"),
    "iwaki_la_vie_en_rose": (
        f"{A2}/produtos/iwaki_la_vie_en_rose.json",
        f"{A2}/produtos/alinhado_v21_iwaki_la_vie_en_rose.json",
    ),
    "kimny_from_this_place": (
        f"{A2}/produtos/kimny_from_this_place.json",
        f"{A2}/produtos/alinhado_v21_kimny_from_this_place.json",
    ),
    "shin_izumi_room_335": (
        f"{A2}/produtos/shin_izumi_room_335.json",
        f"{A2}/produtos/alinhado_v21_shin_izumi_room_335.json",
    ),
}
for _nome in [
    "guitarous_sakura",
    "iwaki_fly_me_to_the_moon",
    "iwaki_michelle",
    "kimny_bach_prelude",
    "kimny_gunjo",
    "paolo_those_who_wait",
    "shin_izumi_dream_wish",
    "shin_izumi_giant_steps",
    "transcriptor_charagua",
]:
    VIDEOS[_nome] = (f"{LOTE1}/{_nome}.json", f"{LOTE1}/alinhado_v21_{_nome}.json")

# (nome, video, tela) das 6 exibicoes recusadas da rodada 2014, exibicao 0.
CASOS = [
    ("room335_t33", "shin_izumi_room_335", 33),
    ("room335_t12", "shin_izumi_room_335", 12),
    ("room335_t25", "shin_izumi_room_335", 25),
    ("giant_t5", "shin_izumi_giant_steps", 5),
    ("giant_t13", "shin_izumi_giant_steps", 13),
    ("giant_t9", "shin_izumi_giant_steps", 9),
]

# nome da configuracao -> kappa (None = linha de base, sem patch)
CONFIGS: list[tuple[str, float | None]] = [
    ("base", None),
    ("k0.1", 0.1),
    ("k0.2", 0.2),
    ("k0.4", 0.4),
]

CAMPOS_COL = ["t_audio", "confianca", "motivo", "cos", "tipo"]
CAMPOS_EX = [
    "n_casadas",
    "pontuacao_trecho",
    "trecho_colunas",
    "T_usado_s",
    "cos_medio",
    "recusada_exibicao",
]


def fabrica_lacuna(kappa: float, k_max: int) -> Callable[..., tuple]:
    """Copia de ``al.alinhar_trecho`` com o termo de andamento com lacunas.

    O corpo e o do original, linha a linha; muda so o calculo de ``andamento``, que vira
    ``min over m de [lambda*|log(dt/(m*dc*T))| + kappa*(m-1)]``. Com ``k_max=1`` a conta e
    a do original, na mesma ordem de operacoes.

    Args:
        kappa: preco de cada coluna perdida na leitura (m - 1 colunas).
        k_max: maior m considerado (K).

    Returns:
        Funcao ``alinhar_trecho_lacuna(cos, tempos, periodo)`` com a mesma assinatura e saida.
    """
    ms = np.arange(1, k_max + 1, dtype=np.int64)[:, None, None]
    termo_lacuna = kappa * (ms - 1)

    def alinhar_trecho_lacuna(
        cos: np.ndarray, tempos: np.ndarray, periodo: float
    ) -> tuple[list[int | None], tuple[int, int] | None, float]:
        """Mesma saida de ``al.alinhar_trecho``, com o andamento de lacunas.

        Args:
            cos: matriz ``[colunas, candidatos]`` de cossenos.
            tempos: instante de cada candidato, em ordem crescente.
            periodo: estimativa de T, em segundos.

        Returns:
            ``(atribuicao, trecho, pontuacao)``, como em ``al.alinhar_trecho``.
        """
        n_col, n_cand = cos.shape
        atribuicao: list[int | None] = [None] * n_col
        if n_col == 0 or n_cand == 0:
            return atribuicao, None, 0.0
        g = np.zeros((n_col, n_cand))
        pred = np.full((n_col, n_cand, 2), -1, dtype=np.int64)
        for c in range(n_col):
            for j in range(n_cand):
                ganho = float(cos[c, j]) - al.BASE_COS
                melhor = 0.0
                arg = (-1, -1)
                if c > 0 and j > 0:
                    cs = np.arange(c)
                    js = np.arange(j)
                    dc = c - cs
                    dt = tempos[j] - tempos[js]
                    denom = (ms * dc[None, :, None]) * periodo  # (K, c, 1)
                    razao = dt[None, None, :] / denom  # (K, c, j)
                    lam = al.LAMBDA_ANDAMENTO * np.abs(
                        np.log(np.maximum(razao, 1e-9))
                    )
                    andamento = np.min(lam + termo_lacuna, axis=0)  # (c, j)
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

    return alinhar_trecho_lacuna


def calcular(
    nome: str,
    rotulo: str,
    kappa: float | None,
    k_max: int,
    oculto: dict,
    gravado: dict,
) -> dict:
    """Saida do alinhador para um video e uma configuracao, do cache em disco se existir.

    Args:
        nome: nome do video.
        rotulo: rotulo da configuracao (nome do arquivo de cache).
        kappa: kappa da variante, ou ``None`` para a linha de base.
        k_max: K da variante.
        oculto: saida de ``esconder_marcador`` do produto.
        gravado: alinhado v2.1 gravado (para o audio do cache).

    Returns:
        Saida de ``alinhar``.
    """
    caminho = CACHE / f"{nome}__{rotulo}.json"
    if caminho.is_file():
        return json.loads(caminho.read_text(encoding="utf-8"))
    audio = audio_do_cache(gravado)
    assert audio is not None
    configurar(kappa, k_max)
    try:
        res = rodar(oculto, audio)
    finally:
        configurar(None)
    CACHE.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
    return res


def configurar(kappa: float | None, k_max: int = K_MAX) -> None:
    """Põe a variante (ou o original) em ``al.alinhar_trecho`` e confere que o patch vale.

    Args:
        kappa: kappa da variante, ou ``None`` para o original.
        k_max: K da variante.
    """
    al.alinhar_trecho = ORIGINAL if kappa is None else fabrica_lacuna(kappa, k_max)
    # O alinhador chama alinhar_trecho pelo nome global: o patch precisa valer ali.
    assert al.alinhar_trecho_iterativo.__globals__["alinhar_trecho"] is al.alinhar_trecho


def audio_do_cache(alin: dict) -> tuple[np.ndarray, int, float] | None:
    """Audio do video SO pelo cache (nada de extrair). ``None`` se nao houver cache valido.

    Args:
        alin: alinhado gravado (usa ``video.arquivo``).

    Returns:
        ``(amostras, taxa, t_amostra0)`` ou ``None``.
    """
    video = alin["video"]["arquivo"]
    try:
        chave = chave_do_arquivo(video, str(acervo()))
    except FileNotFoundError:
        return None
    flac = caminho_no_cache(chave)
    meta_arq = flac.with_suffix(".json")
    if not (flac.is_file() and meta_arq.is_file()):
        return None
    meta = json.loads(meta_arq.read_text(encoding="utf-8"))
    if (
        meta.get("chave") != chave
        or meta.get("taxa") != TAXA_PADRAO
        or meta.get("versao_convencao") != VERSAO_CONVENCAO
    ):
        return None
    amostras, taxa = ler(flac)
    return amostras, int(taxa), float(meta["t_amostra0"])


def rodar(oculto: dict, audio: tuple[np.ndarray, int, float]) -> dict:
    """Roda ``alinhar`` (onsets) do modulo com a configuracao que estiver posta.

    Args:
        oculto: saida de ``esconder_marcador``.
        audio: ``(amostras, taxa, t_amostra0)``.

    Returns:
        Saida de ``alinhar``.
    """
    amostras, taxa, t0a = audio
    return alinhar(oculto, amostras, taxa, t0a, metodo="onsets")


def indice(res: dict) -> dict[tuple[int, int, int], dict]:
    """Registros de coluna indexados por (tela, exibicao, coluna).

    Args:
        res: saida de ``alinhar``.

    Returns:
        Dicionario ``(tela, exibicao, coluna) -> registro``.
    """
    return {(r["tela"], r["exibicao"], r["coluna"]): r for r in res["colunas"]}


def comparar_gravado(res: dict, gravado: dict) -> dict[str, Any]:
    """Confere a saida contra o alinhado v2.1 gravado, coluna a coluna.

    Args:
        res: saida de ``alinhar``.
        gravado: JSON do alinhado v2.1 salvo.

    Returns:
        Contagens de colunas e exibicoes identicas e a lista de divergencias.
    """
    novo = indice(res)
    cols_ok = 0
    divergentes: list[str] = []
    for r in gravado["colunas"]:
        k = (r["tela"], r["exibicao"], r["coluna"])
        n = novo.get(k)
        if n is not None and all(n.get(c) == r.get(c) for c in CAMPOS_COL):
            cols_ok += 1
        else:
            divergentes.append(str(k))
    novo_ex = {(e["tela"], e["exibicao"]): e for e in res["exibicoes"]}
    ex_ok = 0
    for e in gravado["exibicoes"]:
        n = novo_ex.get((e["tela"], e["exibicao"]), {})
        if all(n.get(c) == e.get(c) for c in CAMPOS_EX):
            ex_ok += 1
    return {
        "colunas_identicas": cols_ok,
        "colunas_total": len(gravado["colunas"]),
        "exibicoes_identicas": ex_ok,
        "exibicoes_total": len(gravado["exibicoes"]),
        "primeiras_divergentes": divergentes[:10],
    }


def comparar_entre(res: dict, ref: dict) -> dict[str, int]:
    """Compara duas saidas do alinhador: t_audio, motivo e recusa, coluna a coluna.

    Args:
        res: saida a conferir.
        ref: saida de referencia (a linha de base).

    Returns:
        Contagens de colunas e exibicoes iguais.
    """
    a, b = indice(res), indice(ref)
    cols_iguais = sum(
        1
        for k, r in b.items()
        if a.get(k) is not None and all(a[k].get(c) == r.get(c) for c in CAMPOS_COL)
    )
    ex_a = {(e["tela"], e["exibicao"]): e for e in res["exibicoes"]}
    ex_b = {(e["tela"], e["exibicao"]): e for e in ref["exibicoes"]}
    ex_iguais = sum(
        1
        for k, e in ex_b.items()
        if all(ex_a.get(k, {}).get(c) == e.get(c) for c in CAMPOS_EX)
    )
    return {
        "colunas_iguais": cols_iguais,
        "colunas_total": len(b),
        "exibicoes_iguais": ex_iguais,
        "exibicoes_total": len(ex_b),
    }


def alarmes(res: dict) -> int:
    """Conta alarmes de leitura de um alinhamento, com a regra de ``tab.audio_produto``.

    Args:
        res: saida de ``alinhar``.

    Returns:
        Numero de exibicoes com ``alarme_leitura``.
    """
    margem = float(res["parametros"].get("MARGEM_JANELA_S", 0.5))
    n = 0
    for e in res["exibicoes"]:
        fora = ap.trecho_fora_da_pagina(e.get("janela"), e.get("trecho_tempo"), margem)
        if ap.alarme_leitura(
            bool(e["recusada_exibicao"]),
            e.get("cos_medio"),
            bool(e.get("rasgueado", False)),
            fora,
        ):
            n += 1
    return n


def resumo_video(res: dict, base: dict) -> dict[str, int]:
    """Metricas de uma configuracao num video, comparadas com a linha de base.

    Args:
        res: saida da configuracao.
        base: saida da linha de base.

    Returns:
        Contagens: colunas com tempo, colunas totais, exibicoes recusadas, colunas-base com
        tempo (Y), mudadas > 30 ms, nulas, novas (sem tempo na base, com tempo agora), alarmes.
    """
    nb, nv = indice(base), indice(res)
    y = mud = nul = nov = 0
    for k, rb in nb.items():
        rv = nv.get(k)
        if rb["t_audio"] is not None:
            y += 1
            if rv is None or rv["t_audio"] is None:
                nul += 1
            elif abs(rv["t_audio"] - rb["t_audio"]) > LIMIAR_MUDANCA_S:
                mud += 1
        elif rv is not None and rv["t_audio"] is not None:
            nov += 1
    return {
        "colunas_com_tempo": sum(1 for r in res["colunas"] if r["t_audio"] is not None),
        "colunas_total": len(res["colunas"]),
        "recusadas": sum(1 for e in res["exibicoes"] if e["recusada_exibicao"]),
        "exibicoes_total": len(res["exibicoes"]),
        "base_com_tempo": y,
        "mudam_30ms": mud,
        "viram_nulas": nul,
        "novas_com_tempo": nov,
        "alarmes": alarmes(res),
    }


def somar(linhas: list[dict[str, int]]) -> dict[str, int]:
    """Soma as contagens de varios videos.

    Args:
        linhas: lista de resumos por video.

    Returns:
        Resumo total.
    """
    chaves = linhas[0].keys() if linhas else []
    return {c: sum(x[c] for x in linhas) for c in chaves}


def carregar_gold() -> tuple[list[dict], dict[str, str]]:
    """Itens do gabarito do dono que confirmam ou apontam erro do tempo do alinhador.

    Folha 1 e 2: 'certo' confirma (nao-controle), 'errado' aponta erro; tempo = t_clique.
    Folha 3: 'escolheu' alinhador confirma, 'deslocado' aponta erro; tempo = t_alinhador;
    itens marcados invalido/ambiguo ficam de fora.

    Returns:
        ``(itens, excluidos)``: itens com ``folha``, ``id``, ``video``, ``tela``, ``exibicao``,
        ``coluna``, ``tipo`` ('confirma' ou 'errado'), ``t_gold``; e ids excluidos com motivo.
    """
    itens: list[dict] = []
    excluidos: dict[str, str] = {}
    for folha in ("folha1", "folha2", "folha3"):
        dados = json.loads((GOLD / f"{folha}.json").read_text(encoding="utf-8"))
        for it in dados["itens"]:
            if it.get("controle"):
                excluidos[it["id"]] = "controle"
                continue
            if folha == "folha3":
                if it.get("invalido") or it.get("ambiguo"):
                    excluidos[it["id"]] = "invalido/ambiguo"
                    continue
                esc = it.get("escolheu")
                tipo = {"alinhador": "confirma", "deslocado": "errado"}.get(esc)
                t_gold = it.get("t_alinhador")
            else:
                tipo = {"certo": "confirma", "errado": "errado"}.get(it["resposta_dono"])
                t_gold = it.get("t_clique")
            if tipo is None:
                excluidos[it["id"]] = "sem resposta util"
                continue
            itens.append(
                {
                    "folha": folha,
                    "id": it["id"],
                    "video": it["video"],
                    "tela": int(it["tela"]),
                    "exibicao": int(it["exibicao"]),
                    "coluna": int(it["coluna"]),
                    "tipo": tipo,
                    "t_gold": float(t_gold) if t_gold is not None else None,
                }
            )
    return itens, excluidos


def nome_do_video_gold(video_gold: str, arquivo: str) -> bool:
    """Diz se o caminho do acervo gravado no alinhado corresponde ao video do gabarito.

    Args:
        video_gold: caminho relativo ao acervo, como no gabarito.
        arquivo: caminho absoluto gravado no alinhado.

    Returns:
        ``True`` se ``arquivo`` termina em ``/`` + ``video_gold``.
    """
    return arquivo.endswith("/" + video_gold)


def avaliar_gold(
    itens: list[dict],
    arquivos: dict[str, str],
    base_por_video: dict[str, dict],
    res_por_video: dict[str, dict],
) -> dict[str, dict[str, int]]:
    """Conta, por folha e tipo, o que muda na configuracao em relacao ao tempo do gabarito.

    Args:
        itens: saida de ``carregar_gold``.
        arquivos: nome do video -> caminho do video no acervo (``video.arquivo`` do gravado).
        base_por_video: nome do video -> saida da linha de base.
        res_por_video: nome do video -> saida da configuracao.

    Returns:
        Dicionario ``folha:tipo`` -> contagens (n, sem_base, nulos, mudou_30ms, igual,
        sem_video) e, para a base, quantos batem com o tempo do gabarito (<= 1 ms).
    """
    saida: dict[str, dict[str, int]] = {}
    for it in itens:
        chave = f"{it['folha']}:{it['tipo']}"
        acc = saida.setdefault(
            chave,
            {"n": 0, "sem_video": 0, "sem_base": 0, "nulos": 0, "mudou_30ms": 0, "igual": 0,
             "base_bate_gold_1ms": 0},
        )
        acc["n"] += 1
        nome = next(
            (n for n, arq in arquivos.items() if nome_do_video_gold(it["video"], arq)),
            None,
        )
        if nome is None:
            acc["sem_video"] += 1
            continue
        k = (it["tela"], it["exibicao"], it["coluna"])
        rb = indice(base_por_video[nome]).get(k)
        if rb is None or rb["t_audio"] is None:
            acc["sem_base"] += 1
            continue
        if it["t_gold"] is not None and abs(rb["t_audio"] - it["t_gold"]) <= 0.001:
            acc["base_bate_gold_1ms"] += 1
        rv = indice(res_por_video[nome]).get(k)
        if rv is None or rv["t_audio"] is None:
            acc["nulos"] += 1
        elif abs(rv["t_audio"] - rb["t_audio"]) > LIMIAR_MUDANCA_S:
            acc["mudou_30ms"] += 1
        else:
            acc["igual"] += 1
    return saida


def exibicoes_casos(res_por_video: dict[str, dict]) -> dict[str, dict[str, Any]]:
    """Colunas casadas e aceitacao das 6 exibicoes da rodada 2014.

    Args:
        res_por_video: nome do video -> saida da configuracao.

    Returns:
        Nome do caso -> ``{"casadas", "recusada"}``.
    """
    saida: dict[str, dict[str, Any]] = {}
    for nome, video, tela in CASOS:
        ex = next(
            (e for e in res_por_video[video]["exibicoes"] if e["tela"] == tela and e["exibicao"] == 0),
            None,
        )
        if ex is None:
            saida[nome] = {"casadas": None, "recusada": None}
            continue
        saida[nome] = {"casadas": int(ex["n_casadas"]), "recusada": bool(ex["recusada_exibicao"])}
    return saida


def novas_aceitas(base: dict, res_por_video: dict[str, dict]) -> list[dict]:
    """Exibicoes recusadas na base que passam a ser aceitas, com as colunas novas.

    Args:
        base: nome do video -> saida da linha de base.
        res_por_video: nome do video -> saida da configuracao.

    Returns:
        Lista de dicionarios com video, tela, exibicao, colunas_novas, casadas_base,
        casadas_var.
    """
    out: list[dict] = []
    for nome, res in res_por_video.items():
        exb = {(e["tela"], e["exibicao"]): e for e in base[nome]["exibicoes"]}
        for e in res["exibicoes"]:
            eb = exb[(e["tela"], e["exibicao"])]
            if eb["recusada_exibicao"] and not e["recusada_exibicao"]:
                ib = indice(base[nome])
                iv = indice(res)
                cols = [k for k in ib if k[:2] == (e["tela"], e["exibicao"])]
                n_b = sum(1 for k in cols if ib[k]["t_audio"] is not None)
                n_v = sum(1 for k in cols if iv.get(k, {}).get("t_audio") is not None)
                out.append(
                    {
                        "video": nome,
                        "tela": e["tela"],
                        "exibicao": e["exibicao"],
                        "colunas_novas": n_v - n_b,
                        "casadas_base": n_b,
                        "casadas_var": n_v,
                    }
                )
    return out


def figura(
    caminho: Path,
    audio: tuple[np.ndarray, int, float],
    base: dict,
    var: dict,
    nome: str,
    tela: int,
    exib: int,
    titulo: str,
) -> None:
    """Fluxo espectral, picos e colunas casadas (base e variante) de uma exibicao.

    Args:
        caminho: arquivo PNG de saida.
        audio: ``(amostras, taxa, t_amostra0)`` do video.
        base: saida da linha de base.
        var: saida da variante.
        nome: nome do video (so para o titulo).
        tela: id da tela.
        exib: indice da exibicao.
        titulo: titulo do grafico.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    amostras, taxa, t0a = audio
    ex = next(e for e in base["exibicoes"] if e["tela"] == tela and e["exibicao"] == exib)
    a, b = ex["janela"]
    mag_on, t_on, _ = espectrograma(amostras, taxa, t0a, t0=a, t1=b)
    fluxo = fluxo_espectral(mag_on)
    idx = np.asarray(picos(fluxo, t_on), dtype=np.int64)
    t_pk = t_on[idx]
    f_pk = fluxo[idx]
    fig, ax = plt.subplots(figsize=(11, 4.6), dpi=130)
    ax.axvspan(a + al.MARGEM_JANELA_S, b - al.MARGEM_JANELA_S, color="#eeeeee", zorder=0,
               label="exibicao (pagina)")
    ax.plot(t_on, fluxo, color="#aaaaaa", lw=0.8, zorder=1, label="fluxo espectral")
    ax.scatter(t_pk, f_pk, s=9, color="#444444", zorder=2, label="picos (candidatos)")
    altura = float(np.max(fluxo)) if fluxo.size else 1.0
    for rotulo, res, cor, nivel in (
        ("base (v2.1)", base, "#E69F00", 0.85),
        ("variante", var, "#0072B2", 1.0),
    ):
        xs, cols = [], []
        for r in res["colunas"]:
            if r["tela"] == tela and r["exibicao"] == exib and r["t_audio"] is not None:
                xs.append(float(r["t_audio"]))
                cols.append(r["coluna"])
        y = nivel * altura
        if xs:
            ax.scatter(xs, [y] * len(xs), s=36, color=cor, zorder=4, label=rotulo)
            for x, col in zip(xs, cols, strict=True):
                ax.annotate(f"c{col}", (x, y), textcoords="offset points", xytext=(0, 7),
                            ha="center", fontsize=7, color=cor)
        ax.axhline(y, color=cor, lw=0.4, alpha=0.4, zorder=0)
    ax.set_xlim(a, b)
    ax.set_xlabel("instante do video (s)")
    ax.set_ylabel("fluxo espectral")
    ax.set_yticks([])
    ax.set_title(f"{titulo} [{nome} tela {tela} ex {exib}]", fontsize=10)
    ax.legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False)
    fig.tight_layout()
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(caminho)
    plt.close(fig)


def main() -> int:
    """Passo 0 (reproducao), medidas por configuracao, gabarito, casos, alarmes e figuras.

    Returns:
        Codigo de saida: 0 se o passo 0 bateu; 2 se nao bateu (para tudo).
    """
    SAIDA.mkdir(parents=True, exist_ok=True)
    resultado: dict[str, Any] = {"video_sem_cache": [], "K": K_MAX, "limiar_mudanca_s": LIMIAR_MUDANCA_S}
    antigos: dict[str, dict] = {}
    oculto_de: dict[str, dict] = {}
    try:
        # PASSO 0: linha de base contra o gravado, e K=1 contra a linha de base.
        passo0: dict[str, Any] = {}
        falhou: list[str] = []
        for idx, (nome, (prod, alin)) in enumerate(VIDEOS.items()):
            if PARTE is not None and idx % PARTE[1] != PARTE[0]:
                continue
            gravado = json.loads(Path(alin).read_text(encoding="utf-8"))
            audio = audio_do_cache(gravado)
            if audio is None:
                resultado["video_sem_cache"].append(nome)
                print(f"[passo0] {nome}: SEM CACHE, pulado")
                continue
            antigos[nome] = gravado
            oculto_de[nome] = esconder_marcador(json.loads(Path(prod).read_text(encoding="utf-8")))
            base = calcular(nome, "base", None, K_MAX, oculto_de[nome], gravado)
            k1 = calcular(nome, "k1", 0.4, 1, oculto_de[nome], gravado)
            g = comparar_gravado(base, gravado)
            k = comparar_entre(k1, base)
            passo0[nome] = {"vs_gravado": g, "K1_vs_base": k}
            ok = (
                g["colunas_identicas"] == g["colunas_total"]
                and g["exibicoes_identicas"] == g["exibicoes_total"]
                and k["colunas_iguais"] == k["colunas_total"]
                and k["exibicoes_iguais"] == k["exibicoes_total"]
            )
            if not ok:
                falhou.append(nome)
            print(
                f"[passo0] {nome}: base=gravado colunas {g['colunas_identicas']} de "
                f"{g['colunas_total']}, exibicoes {g['exibicoes_identicas']} de "
                f"{g['exibicoes_total']}; K1=base colunas {k['colunas_iguais']} de "
                f"{k['colunas_total']}, exibicoes {k['exibicoes_iguais']} de "
                f"{k['exibicoes_total']}"
            )
            resultado["passo0"] = passo0
        resultado["passo0"] = passo0
        resultado["passo0_falhou"] = falhou
        if falhou:
            print(f"PASSO 0 NAO BATEU em {falhou}: parando.")
            (SAIDA / "resultados.json").write_text(
                json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return 2

        # Medidas: cada configuracao em cada video.
        saidas: dict[str, dict[str, dict]] = {nome_cfg: {} for nome_cfg, _ in CONFIGS}
        for nome in antigos:
            for nome_cfg, kappa in CONFIGS:
                saidas[nome_cfg][nome] = calcular(
                    nome, nome_cfg, kappa, K_MAX, oculto_de[nome], antigos[nome]
                )
            print(f"[medida] {nome} ok", flush=True)
        if PARTE is not None:
            print(f"[parte {PARTE[0]}/{PARTE[1]}] cache pronto para {list(antigos)}", flush=True)
            return 0
        base = saidas["base"]

        por_cfg: dict[str, Any] = {}
        for nome_cfg, kappa in CONFIGS:
            linhas = {n: resumo_video(saidas[nome_cfg][n], base[n]) for n in base}
            itens_gold, _ = carregar_gold()
            por_cfg[nome_cfg] = {
                "kappa": kappa,
                "por_video": linhas,
                "total": somar(list(linhas.values())),
                "gold": avaliar_gold(
                    itens_gold,
                    {n: antigos[n]["video"]["arquivo"] for n in antigos},
                    base,
                    saidas[nome_cfg],
                ),
                "casos_2014": exibicoes_casos(saidas[nome_cfg]),
                "novas_aceitas": novas_aceitas(base, saidas[nome_cfg]) if nome_cfg != "base" else [],
            }
            t = por_cfg[nome_cfg]["total"]
            print(
                f"[cfg] {nome_cfg}: colunas com tempo {t['colunas_com_tempo']} de "
                f"{t['colunas_total']}; recusadas {t['recusadas']} de {t['exibicoes_total']}; "
                f"mudam>30ms {t['mudam_30ms']} de {t['base_com_tempo']}; "
                f"nulas {t['viram_nulas']} de {t['base_com_tempo']}; "
                f"novas {t['novas_com_tempo']}; alarmes {t['alarmes']}"
            )
        resultado["configs"] = por_cfg
        resultado["gold_itens_excluidos"] = carregar_gold()[1]

        # Figuras: a configuracao que aceita mais exibicoes (empate: menos colunas mudadas).
        melhor = None
        for nome_cfg, _ in CONFIGS[1:]:
            c = por_cfg[nome_cfg]
            chave = (len(c["novas_aceitas"]), -c["total"]["mudam_30ms"] - c["total"]["viram_nulas"])
            if melhor is None or chave > melhor[1]:
                melhor = (nome_cfg, chave)
        resultado["melhor_config_regra"] = melhor[0] if melhor else None
        figuras: list[str] = []
        if melhor is not None:
            aceitas = sorted(
                por_cfg[melhor[0]]["novas_aceitas"], key=lambda x: -x["colunas_novas"]
            )[:3]
            for ex in aceitas:
                audio = audio_do_cache(antigos[ex["video"]])
                assert audio is not None
                nome_arq = f"{ex['video']}_t{ex['tela']}_ex{ex['exibicao']}_{melhor[0]}.png"
                caminho = FIG / nome_arq
                figura(
                    caminho,
                    audio,
                    base[ex["video"]],
                    saidas[melhor[0]][ex["video"]],
                    ex["video"],
                    ex["tela"],
                    ex["exibicao"],
                    f"base x {melhor[0]}",
                )
                figuras.append(str(caminho))
                print(f"[fig] {caminho}")
        resultado["figuras"] = figuras
    finally:
        al.alinhar_trecho = ORIGINAL

    (SAIDA / "resultados.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("gravado:", SAIDA / "resultados.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Trajetórias do M7: o detector de mãos nos ataques e nos controles.

Parte que precisa de GPU e do acervo montado. As funções puras (painel, cordas,
deslocamentos, rótulos, sinal x ruído, preditor) ficam em
``tab.maos_direita_cordas``, que não importa o detector.

Etapas (``--etapa``): ``cordas`` (painel e cordas, CPU), ``refinar`` (busca local
das retas, CPU), ``trajetorias`` (ataques, GPU), ``controle`` (instantes de controle,
GPU), ``folha`` (imagens), ``tudo`` (as cinco em ordem).

Uso::

    python -m tab.maos_direita_trajetorias --etapa trajetorias --dispositivo cuda
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .caminhos import MAOS_M7, acervo
from .maos_detector import DetectorMaos
from .maos_direita_cordas import (
    DELTAS_S,
    N_ATAQUES,
    N_FOLHA,
    N_QUADROS_CORDAS,
    NOMES_VIDEOS,
    SEMENTE,
    _gravar,
    _quadro_do_delta,
    _reta_no_quadro,
    achar_cordas,
    achar_painel,
    ataques_sorteados,
    corda_mais_frequente,
    cordas_do_ataque,
    desenhar_cordas,
    desenhar_folha,
    desenhar_quadro_ataque,
    espacamento_das_cordas,
    instantes_de_controle,
    instantes_de_referencia,
    instantes_distintos,
    mao_direita_no_painel,
    mascara_de_caixas,
    polegar_diagnostico,
    preditor_ataque,
    refinar_cordas,
    resumo_deslocamentos,
    rotulo_ataque,
    sinal_ruido,
    texto_deslocamentos,
)
from .maos_padroes_preparar import VIDEOS
from .maos_pontas_notas import mao_para_registro
from .maos_visao_dedos import quadro_bgr


def registrar_ataque(
    det: DetectorMaos,
    video: Path,
    t: float,
    notas: list[dict[str, Any]],
    painel: tuple[int, int, int, int],
) -> dict[str, Any]:
    """Roda o detector nos quadros em volta de um ataque e guarda a mão direita.

    Args:
        det: detector de mãos já carregado.
        video: arquivo de vídeo.
        t: instante do ataque, em segundos.
        notas: notas do produto (para as cordas da tablatura).
        painel: retângulo do painel no quadro.

    Returns:
        ``{t_ini, cordas_tab, quadros}``. Em cada quadro: ``delta``, ``t_quadro``,
        ``maos`` (todas, sem filtro) e ``direita`` (a mão no painel, ou None).
    """
    quadros = []
    for delta in DELTAS_S:
        t_quadro = round(max(t + delta, 0.0), 3)
        achado = det.detectar(quadro_bgr(video, t_quadro), None)
        maos = [mao_para_registro(m) for m in achado["maos"]]
        indice = mao_direita_no_painel(maos, painel)
        quadros.append(
            {
                "delta": delta,
                "t_quadro": t_quadro,
                "maos": maos,
                "direita": None if indice is None else maos[indice],
            }
        )
    return {"t_ini": t, "cordas_tab": cordas_do_ataque(notas, t), "quadros": quadros}


def _entrada_do_video(nome: str) -> tuple[Path, Path]:
    """Vídeo e produto de um dos quatro vídeos do M5.

    Args:
        nome: uma das chaves de ``NOMES_VIDEOS``.

    Returns:
        ``(video, produto)``, com o vídeo no acervo montado.
    """
    entrada = VIDEOS[NOMES_VIDEOS.index(nome)]
    return acervo() / entrada["arquivo"], entrada["produto"]


def etapa_cordas(nome: str) -> dict[str, Any]:
    """Acha painel e cordas de um vídeo e grava ``cordas_<nome>.json`` e ``.jpg``.

    Args:
        nome: chave do vídeo.

    Returns:
        O resultado gravado (ver ``achar_cordas``), com os instantes dos quadros.
    """
    video, produto = _entrada_do_video(nome)
    notas = json.loads(produto.read_text(encoding="utf-8"))["notas"]
    ts = instantes_de_referencia(instantes_distintos(notas), N_QUADROS_CORDAS)
    frames = [quadro_bgr(video, t) for t in ts]
    paineis = [achar_painel(f) for f in frames]
    painel = paineis[0]
    achado = achar_cordas(frames, painel)
    achado.update(
        {
            "video": nome,
            "t_quadros": ts,
            "paineis_por_quadro": [list(p) for p in paineis],
            "painel_estavel": all(p == painel for p in paineis),
        }
    )
    _gravar(MAOS_M7 / f"cordas_{nome}.json", achado)
    x0, y0, x1, y1 = painel
    linhas = achado["cordas"] or [
        {**r, "corda": i + 1} for i, r in enumerate(achado["retas_consolidadas"])
    ]
    rotulo = "numeradas" if achado["cordas"] else "SEM 6 - sem numerar"
    partes = [
        desenhar_cordas(f[y0:y1, x0:x1], linhas, f"{nome} | {rotulo}")
        for f in (frames[0], frames[2], frames[4])
    ]
    cv2.imwrite(
        str(MAOS_M7 / f"cordas_{nome}.jpg"),
        np.hstack(partes),
        [cv2.IMWRITE_JPEG_QUALITY, 88],
    )
    return achado


def etapa_trajetorias(nome: str, dispositivo: str, n_ataques: int) -> dict[str, Any]:
    """Roda o detector em volta de cada ataque sorteado e grava ``trajetorias_<nome>``.

    Args:
        nome: chave do vídeo.
        dispositivo: ``cuda`` ou ``cpu``.
        n_ataques: quantos ataques sorteados.

    Returns:
        O resultado gravado.

    Raises:
        ValueError: se o vídeo não tem as 6 cordas (``cordas_<nome>.json``).
    """
    cordas_json = json.loads(
        (MAOS_M7 / f"cordas_{nome}.json").read_text(encoding="utf-8")
    )
    if not cordas_json["cordas"]:
        raise ValueError(f"{nome}: sem as 6 cordas, não há o que medir")
    painel = tuple(cordas_json["painel"])
    video, produto = _entrada_do_video(nome)
    notas = json.loads(produto.read_text(encoding="utf-8"))["notas"]
    sorteados = ataques_sorteados(instantes_distintos(notas), n_ataques, SEMENTE)
    det = DetectorMaos(dispositivo)
    ataques = []
    for i, t in enumerate(sorteados, start=1):
        ataques.append(registrar_ataque(det, video, t, notas, painel))
        print(f"{nome}: {i}/{len(sorteados)} ataques", flush=True)
    dados = {
        "video": nome,
        "semente": SEMENTE,
        "deltas": list(DELTAS_S),
        "painel": list(painel),
        "cordas": cordas_json["cordas"],
        "deslocamentos_resumo": resumo_deslocamentos(ataques),
        "ataques": ataques,
    }
    print(f"{nome} deslocamentos: {dados['deslocamentos_resumo']}", flush=True)
    _gravar(MAOS_M7 / f"trajetorias_{nome}.json", dados)
    return dados


def etapa_folha(nome: str) -> None:
    """Grava ``folha_<nome>.jpg``: ``N_FOLHA`` ataques, cada um com os 5 quadros.

    Args:
        nome: chave do vídeo (precisa de ``trajetorias_<nome>.json``).
    """
    dados = json.loads(
        (MAOS_M7 / f"trajetorias_{nome}.json").read_text(encoding="utf-8")
    )
    painel = tuple(dados["painel"])
    video, _ = _entrada_do_video(nome)
    ataques = dados["ataques"]
    escolhidos = [
        ataques[i] for i in np.linspace(0, len(ataques) - 1, N_FOLHA).astype(int)
    ]
    linhas = []
    for ataque in escolhidos:
        quadros = []
        for q in ataque["quadros"]:
            recorte = quadro_bgr(video, q["t_quadro"])
            x0, y0, x1, y1 = painel
            quadros.append(
                desenhar_quadro_ataque(recorte[y0:y1, x0:x1], q, painel, 0.5)
            )
        linhas.append(
            (rotulo_ataque(ataque) + "  " + texto_deslocamentos(ataque), quadros)
        )
    cv2.imwrite(
        str(MAOS_M7 / f"folha_{nome}.jpg"),
        desenhar_folha(linhas),
        [cv2.IMWRITE_JPEG_QUALITY, 85],
    )


def etapa_refinar(nome: str) -> dict[str, Any]:
    """Refina as retas de um vídeo pela crista, nos quadros de ataque (CPU).

    Usa os quadros de ``delta = 0`` dos ataques (já gravados) e as caixas das mãos
    desses quadros para excluir a mão. Atualiza ``cordas_<nome>.json``, regera o
    ``cordas_<nome>.jpg`` e grava os recortes ampliados 2x da ponte e da boca.

    Args:
        nome: chave do vídeo (precisa de ``cordas_<nome>.json`` e de
            ``trajetorias_<nome>.json``).

    Returns:
        ``{cordas, espacamento, quadros}`` com as cristas antes e depois.
    """
    cordas_json = json.loads(
        (MAOS_M7 / f"cordas_{nome}.json").read_text(encoding="utf-8")
    )
    traj = json.loads(
        (MAOS_M7 / f"trajetorias_{nome}.json").read_text(encoding="utf-8")
    )
    painel = tuple(cordas_json["painel"])
    x0, y0, x1, y1 = painel
    video, _ = _entrada_do_video(nome)
    cinzas, mascaras, recortes = [], [], []
    for ataque in traj["ataques"]:
        quadro = _quadro_do_delta(ataque, 0.0)
        bgr = quadro_bgr(video, quadro["t_quadro"])
        rec = bgr[y0:y1, x0:x1]
        recortes.append(rec)
        cinzas.append(cv2.cvtColor(rec, cv2.COLOR_BGR2GRAY).astype(np.float32))
        caixas = [
            (
                m["caixa"][0] - x0,
                m["caixa"][1] - y0,
                m["caixa"][2] - x0,
                m["caixa"][3] - y0,
            )
            for m in quadro["maos"]
        ]
        mascaras.append(mascara_de_caixas((y1 - y0, x1 - x0), caixas))
    antes = cordas_json["cordas"]
    refinadas = refinar_cordas(cinzas, mascaras, antes)
    cordas = [{**r, **_reta_no_quadro(r, painel)} for r in refinadas]
    cordas_json["cordas_pre_refino"] = antes
    cordas_json["cordas"] = cordas
    cordas_json["refino"] = {
        "quadros": len(cinzas),
        "espacamento": espacamento_das_cordas(antes),
    }
    _gravar(MAOS_M7 / f"cordas_{nome}.json", cordas_json)
    desenhadas = [
        desenhar_cordas(r, cordas, f"{nome} | refinadas") for r in recortes[:3]
    ]
    cv2.imwrite(
        str(MAOS_M7 / f"cordas_{nome}.jpg"),
        np.hstack(desenhadas),
        [cv2.IMWRITE_JPEG_QUALITY, 88],
    )
    menos_mao = int(np.argmin([m.mean() for m in mascaras]))
    sobreposto = desenhar_cordas(recortes[menos_mao], cordas, nome)
    ponte = sobreposto[250:558, 0:330]
    boca = sobreposto[28:330, 180:460]
    for rotulo, recorte in (("ponte", ponte), ("boca", boca)):
        ampliada = cv2.resize(
            recorte, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC
        )
        cv2.imwrite(str(MAOS_M7 / f"zoom_{rotulo}_{nome}.jpg"), ampliada)
    return {
        "cordas": cordas,
        "espacamento": cordas_json["refino"]["espacamento"],
        "quadros": len(cinzas),
    }


def etapa_controle(nome: str, dispositivo: str, n_controles: int) -> dict[str, Any]:
    """Roda o detector em instantes de controle (GPU) e grava ``trajetorias_controle_<nome>``.

    Args:
        nome: chave do vídeo.
        dispositivo: ``cuda`` ou ``cpu``.
        n_controles: quantos instantes.

    Returns:
        O resultado gravado.
    """
    cordas_json = json.loads(
        (MAOS_M7 / f"cordas_{nome}.json").read_text(encoding="utf-8")
    )
    painel = tuple(cordas_json["painel"])
    video, produto = _entrada_do_video(nome)
    notas = json.loads(produto.read_text(encoding="utf-8"))["notas"]
    instantes = instantes_distintos(notas)
    controles = instantes_de_controle(
        instantes, instantes[0], instantes[-1], n_controles, SEMENTE
    )
    det = DetectorMaos(dispositivo)
    registros = []
    for i, t in enumerate(controles, start=1):
        registros.append(registrar_ataque(det, video, t, notas, painel))
        print(f"{nome}: controle {i}/{len(controles)}", flush=True)
    dados = {
        "video": nome,
        "semente": SEMENTE,
        "painel": list(painel),
        "controles": registros,
    }
    _gravar(MAOS_M7 / f"trajetorias_controle_{nome}.json", dados)
    return dados


def etapa_sinal() -> dict[str, Any]:
    """Compara ataques e controles de todos os vídeos e grava ``sinal_ruido.json``.

    Returns:
        ``{video: sinal_ruido(...)}``.
    """
    saida = {}
    for nome in NOMES_VIDEOS:
        traj = json.loads(
            (MAOS_M7 / f"trajetorias_{nome}.json").read_text(encoding="utf-8")
        )
        ctrl = json.loads(
            (MAOS_M7 / f"trajetorias_controle_{nome}.json").read_text(encoding="utf-8")
        )
        saida[nome] = sinal_ruido(traj["ataques"], ctrl["controles"])
        r = saida[nome]
        print(
            f"{nome} maximo AUC={r['maximo']['auc']} ataque={r['maximo']['ataque']} "
            f"controle={r['maximo']['controle']}",
            flush=True,
        )
        for dedo, v in r["por_dedo"].items():
            print(
                f"   {dedo}: AUC={v['auc']} ataque={v['ataque']} controle={v['controle']}",
                flush=True,
            )
    _gravar(MAOS_M7 / "sinal_ruido.json", saida)
    return saida


def etapa_preditor(nome: str) -> dict[str, Any]:
    """Preditor (ponta que mais se move, em -0,07 s, reta mais próxima) e base, por vídeo.

    Args:
        nome: chave do vídeo.

    Returns:
        Resultado gravado em ``preditor_<nome>.json``.
    """
    cordas_json = json.loads(
        (MAOS_M7 / f"cordas_{nome}.json").read_text(encoding="utf-8")
    )
    traj = json.loads(
        (MAOS_M7 / f"trajetorias_{nome}.json").read_text(encoding="utf-8")
    )
    _, produto = _entrada_do_video(nome)
    notas = json.loads(produto.read_text(encoding="utf-8"))["notas"]
    cordas = cordas_json["cordas"]
    ataques = traj["ataques"]
    previsoes = [
        p for p in (preditor_ataque(a, cordas) for a in ataques) if p is not None
    ]
    base = corda_mais_frequente(notas, [a["t_ini"] for a in ataques])
    acertos_base = sum(base in p["cordas_tab"] for p in previsoes)
    resultado = {
        "video": nome,
        "base_corda": base,
        "avaliados": len(previsoes),
        "acertos_preditor": sum(p["acerto"] for p in previsoes),
        "acertos_base": acertos_base,
        "polegar_diagnostico": polegar_diagnostico(ataques, cordas),
        "previsoes": previsoes,
    }
    _gravar(MAOS_M7 / f"preditor_{nome}.json", resultado)
    print(
        f"{nome}: avaliados={resultado['avaliados']} preditor={resultado['acertos_preditor']} "
        f"base={resultado['acertos_base']} (corda {base}) polegar={resultado['polegar_diagnostico']}",
        flush=True,
    )
    return resultado


def main() -> None:
    """Roda as etapas do M7 e grava as saídas em ``MAOS_M7``."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--etapa",
        choices=[
            "cordas",
            "refinar",
            "trajetorias",
            "controle",
            "sinal",
            "preditor",
            "folha",
            "tudo",
        ],
        default="tudo",
    )
    parser.add_argument("--video", choices=NOMES_VIDEOS, action="append", default=None)
    parser.add_argument("--dispositivo", choices=["cuda", "cpu"], default="cuda")
    parser.add_argument("--ataques", type=int, default=N_ATAQUES)
    args = parser.parse_args()
    nomes = args.video or list(NOMES_VIDEOS)
    if args.etapa == "sinal":
        etapa_sinal()
        return
    for nome in nomes:
        if args.etapa in ("cordas", "tudo"):
            achado = etapa_cordas(nome)
            print(
                f"{nome}: painel={achado['painel']} estavel={achado['painel_estavel']} "
                f"retas/quadro={achado['retas_por_quadro']} "
                f"brutas={achado['cordas_brutas']} numeradas={len(achado['cordas'])}",
                flush=True,
            )
        if args.etapa in ("refinar", "tudo"):
            etapa_refinar(nome)
        if args.etapa in ("trajetorias", "tudo"):
            etapa_trajetorias(nome, args.dispositivo, args.ataques)
        if args.etapa == "controle":
            etapa_controle(nome, args.dispositivo, args.ataques)
        if args.etapa == "preditor":
            etapa_preditor(nome)
        if args.etapa in ("folha", "tudo"):
            etapa_folha(nome)


if __name__ == "__main__":
    main()

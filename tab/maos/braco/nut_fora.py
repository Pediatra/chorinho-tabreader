"""Rodada 1031 (desenvolvimento): numeração com o nut fora, pelos vizinhos e pela junção.

Pré-registro: ``docs/rodadas/1031-nut-fora-por-vizinhos-e-juncao.md`` (commit a56e1366).

Esta parte roda inteiros (2 quadros por segundo) os vídeos dos casos de nut fora que a 1030
não rodou: dois da 1029 e o da M11b. O detector é o do ciclo 1029 (``L3_todos_s3`` +
``A4_100_todos_s1``). Grava ``denso_<nome>.jsonl`` na pasta da 1031, no formato da Parte A
da 1030, mais as dimensões do quadro; e guarda em JPEG os quadros em que o braço foi achado,
para a regra da junção (método J), que trabalha sobre a imagem.

CLI: ``python -m tab.maos_braco_nut_fora videos`` (GPU, com a trava da GPU) e
``python -m tab.maos_braco_nut_fora quadros`` (CPU: guarda os quadros dos vídeos da 1030).
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

import cv2
import numpy as np

from tab.comum.arquivos import nfc as _nfc
from tab.comum.caminhos import (
    GABARITO_BRACO_M11B,
    GABARITO_BRACO_M27,
    GABARITO_BRACO_M29,
    GABARITO_BRACO_M31,
    MAOS_M11B,
    MAOS_M27,
    MAOS_M29,
    MAOS_M30,
    MAOS_M31,
    acervo,
)
from tab.maos.braco.cadeia import ler_trecho
from tab.maos.braco.ciclo import (
    ARQUIVO_INDICE,
    ARQUIVO_SORTEIO,
    _ler_json,
    _peso_existe,
    classe_do_quadro,
    marcas_do_registro,
    nut_suspeito_previsto,
    previsto_do_resultado,
)
from tab.maos.braco.detector import (
    DIR_PESOS,
    PASSOS,
    _carregar_pesos,
    _imagem,
    _trava_gpu,
)
from tab.maos.braco.juncao import metodo_j
from tab.maos.braco.localizador import _carregar_localizador, cadeia, sinalizado
from tab.maos.braco.video import (
    PASSO_S,
    VideoRevisado,
    gravar_jsonl,
    ler_jsonl,
    nome_jsonl,
    processar_video,
    videos_revisados,
)
from tab.maos.braco.vizinhos import metodo_v
from tab.maos.gabarito import gravar_atomico

#: Detector do ciclo 1029 (escolhido na M11b; ``m29/escolha_pesos.json``).
ESTAGIO1_1031 = "L3_todos_s3"
ESTAGIO2_1031 = "A4_100_todos_s1"

#: Vídeos que a 1031 roda inteiros: ``(nome, pasta com sorteio.json, trecho do arquivo)``.
VIDEOS_1031 = (
    ("cuando", MAOS_M29, "cuando te dicen que la guitarra"),
    ("lagrima", MAOS_M29, "lágrima de tárrega"),
    ("valsa", MAOS_M11B, "valsa sem nome"),
    ("marigold", MAOS_M27, "マリーゴールド ソロギター"),
)
#: Número usado nos ids dos quadros densos da 1031 (``v<nn>_<k>``), depois dos 16 da 1030.
PRIMEIRO_NUMERO_1031 = 17

#: Qualidade dos JPEG dos quadros guardados para o método J.
QUALIDADE_JPEG = 90
#: Vídeo da 1030 com casos de nut fora (1027 e 1031), cujos quadros a regra J precisa: o
#: v15 (マリーゴールド, solo). Pelo número, porque o nome tem kana em formas Unicode diferentes.
NUMEROS_1030 = (15,)

#: Medida: rodadas revisadas de cada vídeo dos casos, ``(rodada, gabarito, pasta)``.
RODADAS_DOS_VIDEOS = {
    "marigold": (
        ("1027", GABARITO_BRACO_M27, MAOS_M27),
        ("1031", GABARITO_BRACO_M31, MAOS_M31),
    ),
    "cuando": (("1029", GABARITO_BRACO_M29, MAOS_M29),),
    "lagrima": (("1029", GABARITO_BRACO_M29, MAOS_M29),),
    "valsa": (("M11B", GABARITO_BRACO_M11B, MAOS_M11B),),
}
#: Um quadro revisado recebe o quadro denso a até este tempo (como na 1030).
TOLERANCIA_REVISADO_S = 0.25
#: O traste previsto vale para a referência do dono se estiver a até esta fração do
#: espaço local entre trastes.
TOLERANCIA_REFERENCIA = 0.5
#: Critério do pré-registro.
MIN_ACERTOS = 8
ARQUIVO_MEDIDA = MAOS_M31 / "medida_1031.json"

#: A5 (desenvolvimento): fontes dos 16 casos, ``(rodada, gabarito, pasta com quadros)``.
FONTES_CASOS = (
    ("1027", GABARITO_BRACO_M27, MAOS_M27),
    ("M11B", GABARITO_BRACO_M11B, MAOS_M11B),
    ("1029", GABARITO_BRACO_M29, MAOS_M29),
    ("1031", GABARITO_BRACO_M31, MAOS_M31),
)
#: A5: estágio 2 de comparação (o do ciclo) e os candidatos A5.
ESTAGIOS2_A5 = (
    "A4_100_todos_s1",
    "A5_100_todos_s1",
    "A5_100_todos_s2",
    "A5_100_todos_s3",
)
ARQUIVO_MEDIDA_A5 = MAOS_M31 / "medida_a5.json"


def pasta_quadros(nome: str) -> Path:
    """Pasta dos JPEG do vídeo ``nome``.

    Args:
        nome: nome curto do vídeo (``cuando``, ``v15``…).

    Returns:
        ``<m31>/denso/<nome>``.
    """
    return MAOS_M31 / "denso" / nome


def destino_jsonl(nome: str) -> Path:
    """Arquivo com os quadros densos de um vídeo da 1031.

    Args:
        nome: nome curto do vídeo.

    Returns:
        ``<m31>/denso_<nome>.jsonl``.
    """
    return MAOS_M31 / f"denso_{nome}.jsonl"


def videos_1031() -> list[tuple[str, VideoRevisado]]:
    """Os vídeos da 1031, achados pelo trecho do nome nos sorteios de origem.

    Returns:
        ``(nome, vídeo)`` na ordem de ``VIDEOS_1031``.

    Raises:
        ValueError: se um trecho não acha exatamente um vídeo.
    """
    saida = []
    for posicao, (nome, pasta, trecho) in enumerate(VIDEOS_1031):
        achados = [
            v
            for v in _ler_json(pasta / ARQUIVO_SORTEIO)["videos"]
            if _nfc(trecho) in _nfc(v["arquivo"])
        ]
        if len(achados) != 1:
            raise ValueError(f"{trecho!r}: {len(achados)} vídeos no sorteio")
        video = achados[0]
        duracao = video.get("duracao_s", video.get("duracao"))
        saida.append(
            (
                nome,
                VideoRevisado(
                    numero=PRIMEIRO_NUMERO_1031 + posicao,
                    rodada=pasta.name,
                    arquivo=video["arquivo"],
                    duracao_s=float(duracao),
                ),
            )
        )
    return saida


def guardar_quadros(video: VideoRevisado, registros: list[dict], nome: str) -> dict:
    """Relê o vídeo (CPU) e grava em JPEG os quadros em que o braço foi achado.

    Também devolve as dimensões de cada quadro, que a Parte A não gravava.

    Args:
        video: vídeo a reler.
        registros: registros densos do vídeo, na ordem do tempo.
        nome: nome curto (pasta dos JPEG).

    Returns:
        ``{id: [largura, altura]}`` de todos os quadros lidos.
    """
    pasta = pasta_quadros(nome)
    pasta.mkdir(parents=True, exist_ok=True)
    ids = [r["id"] for r in registros]
    com_braco = {r["id"] for r in registros if r["previsto"]["achou"]}
    dimensoes: dict[str, list[int]] = {}
    fluxo = ler_trecho(acervo() / video.arquivo, 0.0, video.duracao_s, PASSO_S)
    for k, (_, imagem) in enumerate(fluxo):
        if k >= len(ids):
            break
        id_q = ids[k]
        dimensoes[id_q] = [int(imagem.shape[1]), int(imagem.shape[0])]
        if id_q in com_braco:
            cv2.imwrite(
                str(pasta / f"{id_q}.jpg"),
                imagem,
                [cv2.IMWRITE_JPEG_QUALITY, QUALIDADE_JPEG],
            )
    return dimensoes


def rodar_videos() -> None:
    """Roda inteiros os vídeos da 1031 (GPU por vídeo) e guarda os quadros com braço."""
    for nome, video in videos_1031():
        destino = destino_jsonl(nome)
        if destino.exists():
            print(f"pulo {destino.name}: já feito", flush=True)
            continue
        with _trava_gpu():
            loc = _carregar_localizador(ESTAGIO1_1031)
            dois, _ = _carregar_pesos(ESTAGIO2_1031, PASSOS)
            registros = processar_video(video, loc, dois)
        dimensoes = guardar_quadros(video, registros, nome)
        for registro in registros:
            registro["dimensoes"] = dimensoes.get(registro["id"])
        gravar_jsonl(destino, registros)
        print(f"{destino.name}: {len(registros)} quadros", flush=True)


def guardar_quadros_1030() -> None:
    """Guarda os quadros com braço dos vídeos da 1030 que têm casos de nut fora (CPU)."""
    for video in videos_revisados():
        if video.numero not in NUMEROS_1030:
            continue
        nome = f"v{video.numero:02d}"
        registros = ler_jsonl(MAOS_M30 / nome_jsonl(video.numero))
        dimensoes = guardar_quadros(video, registros, nome)
        caminho = MAOS_M31 / f"dimensoes_{nome}.json"
        caminho.write_text(json.dumps(dimensoes), encoding="utf-8")
        print(f"{nome}: {len(dimensoes)} quadros lidos", flush=True)


# ---------------------------------------------------------------------------------
# Medida dos métodos V, J e V+J
# ---------------------------------------------------------------------------------


def nut_suspeito(registro: dict) -> bool:
    """Regra de borda da 1030 (só sinal), num quadro denso.

    Args:
        registro: quadro denso com ``previsto`` e ``dimensoes``.

    Returns:
        True se o braço foi achado e o nut é suspeito de estar fora da imagem.
    """
    dimensoes = registro.get("dimensoes")
    return nut_suspeito_previsto(
        registro["previsto"], tuple(dimensoes) if dimensoes else None
    )


def combinar(v: dict | None, j: dict | None, suspeito: bool) -> dict:
    """Combinação V+J do pré-registro.

    Args:
        v: saída do método V para o quadro (ou None).
        j: saída do método J para o quadro (ou None).
        suspeito: se o nut é suspeito (regra de borda).

    Returns:
        ``{"k", "sinaliza", "motivo"}``: concordam vale; discordam sinaliza; um só decide
        vale ele; nenhum decide sinaliza só com o nut suspeito.
    """
    kv = None if v is None else v["k"]
    kj = None if j is None else j["k"]
    if kv is not None and kj is not None:
        if kv == kj:
            return {"k": kv, "sinaliza": False, "motivo": "concordam"}
        return {"k": None, "sinaliza": True, "motivo": "discordam"}
    if kv is not None:
        return {"k": kv, "sinaliza": False, "motivo": "só V"}
    if kj is not None:
        return {"k": kj, "sinaliza": False, "motivo": "só J"}
    return {"k": None, "sinaliza": suspeito, "motivo": "nenhum decide"}


def aplicar(previsto: dict, k: int | None, sinaliza: bool) -> dict:
    """Previsão com a numeração somada a k e o sinal a mais.

    Args:
        previsto: previsão do detector.
        k: deslocamento (None ou 0 não muda os números).
        sinaliza: se o método manda o quadro para revisão.

    Returns:
        Cópia da previsão.
    """
    saida = copy.deepcopy(previsto)
    if k and saida.get("trastes"):
        for traste in saida["trastes"]:
            traste["numero"] = int(traste["numero"]) + int(k)
    saida["sinalizado"] = bool(saida["sinalizado"]) or sinaliza
    return saida


def numero_na_referencia(previsto: dict, referencia: dict) -> int | None:
    """Número previsto para o traste de referência do dono.

    Args:
        previsto: previsão (com ``trastes``).
        referencia: ``traste_referencia`` do dono (``ponto`` e ``numero``).

    Returns:
        O número do traste previsto mais perto do ponto do dono, se estiver a até
        ``TOLERANCIA_REFERENCIA`` do espaço local; senão None.
    """
    if not previsto.get("achou") or not previsto.get("trastes"):
        return None
    pontos = np.asarray([t["ponto"] for t in previsto["trastes"]], dtype=float)
    alvo = np.asarray(referencia["ponto"], dtype=float)
    distancias = np.linalg.norm(pontos - alvo, axis=1)
    i = int(np.argmin(distancias))
    vizinhos = np.linalg.norm(pontos - pontos[i], axis=1)
    vizinhos = vizinhos[vizinhos > 0]
    if len(vizinhos) == 0:
        return None
    if distancias[i] > TOLERANCIA_REFERENCIA * float(vizinhos.min()):
        return None
    return int(previsto["trastes"][i]["numero"])


def modos_do_video(nome: str, registros: list[dict]) -> tuple[dict, dict]:
    """Roda V e J num vídeo e monta as previsões de cada modo.

    Args:
        nome: nome curto do vídeo (pasta dos JPEG).
        registros: quadros densos.

    Returns:
        ``(modos, info)``: ``modos[modo][id]`` é a previsão do modo (``sozinho``, ``V``,
        ``J`` e ``VJ``), e ``info`` tem o número de junção do vídeo e as saídas por id.
    """
    pasta = pasta_quadros(nome)

    def ler(id_q: str) -> np.ndarray | None:
        return cv2.imread(str(pasta / f"{id_q}.jpg"))

    saida_v = metodo_v(registros)
    saida_j, video_j = metodo_j(registros, ler)
    modos: dict[str, dict[str, dict]] = {"sozinho": {}, "V": {}, "J": {}, "VJ": {}}
    combinados: dict[str, dict] = {}
    for registro in registros:
        id_q = registro["id"]
        previsto = registro["previsto"]
        modos["sozinho"][id_q] = previsto
        if not previsto.get("achou"):
            for modo in ("V", "J", "VJ"):
                modos[modo][id_q] = previsto
            continue
        v, j = saida_v.get(id_q), saida_j.get(id_q)
        for modo, saida in (("V", v), ("J", j)):
            k = None if saida is None else saida["k"]
            modos[modo][id_q] = aplicar(previsto, k, k is None)
        combinado = combinar(v, j, nut_suspeito(registro))
        combinados[id_q] = combinado
        modos["VJ"][id_q] = aplicar(previsto, combinado["k"], combinado["sinaliza"])
    info = {
        "juncao_do_video": video_j,
        "V": saida_v,
        "J": {i: {c: s[c] for c in ("k", "motivo")} for i, s in saida_j.items()},
        "VJ": combinados,
    }
    return modos, info


def classe_do_caso(previsto: dict, registro: dict) -> tuple[str, int | None]:
    """Classe de um caso de nut fora contra a referência do dono.

    Args:
        previsto: previsão do modo.
        registro: resposta do dono (``traste_referencia``).

    Returns:
        ``(classe, numero)``: ``acerto`` (número certo e não sinalizado), ``acerto
        sinalizado``, ``recusa`` (sinalizado e sem número certo) ou ``erro não
        sinalizado``; e o número previsto na referência.
    """
    referencia = registro["traste_referencia"]
    numero = numero_na_referencia(previsto, referencia)
    certo = numero is not None and numero == int(referencia["numero"])
    sinal = bool(previsto["sinalizado"]) or not previsto.get("achou")
    if certo:
        return ("acerto sinalizado" if sinal else "acerto"), numero
    return ("recusa" if sinal else "erro não sinalizado"), numero


def medir() -> dict:
    """Mede os modos nos casos (nut fora com referência) e nos controles.

    Returns:
        O resultado gravado em ``medida_1031.json``.
    """
    casos: list[dict] = []
    controles: list[dict] = []
    videos: dict[str, dict] = {}
    for nome, rodadas in RODADAS_DOS_VIDEOS.items():
        caminho = destino_jsonl(nome)
        if not caminho.exists():
            videos[nome] = {"erro": "vídeo denso não rodado"}
            continue
        registros = ler_jsonl(caminho)
        arquivo = _nfc(registros[0]["previsto"]["arquivo"])
        modos, info = modos_do_video(nome, registros)
        videos[nome] = {
            "arquivo": arquivo,
            "quadros": len(registros),
            "com_braco": sum(1 for r in registros if r["previsto"]["achou"]),
            "juncao_do_video": info["juncao_do_video"],
            "motivos_V": _contar(info["V"]),
            "motivos_J": _contar(info["J"]),
            "motivos_VJ": _contar(info["VJ"]),
        }
        denso = {round(r["t"] / PASSO_S): r for r in registros}
        for rodada, gabarito, pasta in rodadas:
            respostas = _ler_json(gabarito)["quadros"]
            for item in _ler_json(pasta / ARQUIVO_INDICE)["quadros"]:
                if _nfc(item["arquivo"]) != arquivo or item["id"] not in respostas:
                    continue
                registro = respostas[item["id"]]
                if registro.get("braco") in (None, "?"):
                    continue
                rec = denso.get(round(float(item["t"]) / PASSO_S))
                chave = f"{rodada}:{item['id']}"
                if (
                    rec is None
                    or abs(rec["t"] - float(item["t"])) > TOLERANCIA_REVISADO_S
                ):
                    continue
                id_q = rec["id"]
                linha: dict = {"chave": chave, "video": nome, "denso": id_q}
                if registro.get("nut") == "fora" and registro.get("traste_referencia"):
                    linha["dono"] = int(registro["traste_referencia"]["numero"])
                    for modo, previstos in modos.items():
                        classe, numero = classe_do_caso(previstos[id_q], registro)
                        linha[modo] = {"classe": classe, "numero": numero}
                    linha["metodos"] = {m: info[m].get(id_q) for m in ("V", "J", "VJ")}
                    casos.append(linha)
                    continue
                if marcas_do_registro(registro) is None and registro["braco"] != "nao":
                    continue
                for modo, previstos in modos.items():
                    classe, _ = classe_do_quadro(previstos[id_q], registro)
                    linha[modo] = {
                        "classe": classe,
                        "sinalizado": bool(previstos[id_q]["sinalizado"]),
                    }
                controles.append(linha)
    resultado = {
        "rodada": 1031,
        "videos": videos,
        "casos": casos,
        "controles": controles,
        "totais": {
            modo: _totais(casos, controles, modo)
            for modo in ("sozinho", "V", "J", "VJ")
        },
    }
    gravar_atomico(ARQUIVO_MEDIDA, resultado)
    return resultado


def _contar(saidas: dict) -> dict:
    """Quantos quadros por motivo.

    Args:
        saidas: ``{id: {"motivo": ...}}``.

    Returns:
        ``{motivo: n}``.
    """
    contagem: dict[str, int] = {}
    for saida in saidas.values():
        contagem[saida["motivo"]] = contagem.get(saida["motivo"], 0) + 1
    return contagem


def _totais(casos: list[dict], controles: list[dict], modo: str) -> dict:
    """Totais de um modo e o critério do pré-registro.

    Args:
        casos: linhas dos casos.
        controles: linhas dos controles.
        modo: ``sozinho``, ``V``, ``J`` ou ``VJ``.

    Returns:
        Contagem por classe nos casos, certos estragados no controle e se passa.
    """
    classes: dict[str, int] = {}
    for caso in casos:
        classes[caso[modo]["classe"]] = classes.get(caso[modo]["classe"], 0) + 1
    estragados = [
        c["chave"]
        for c in controles
        if c["sozinho"]["classe"] == "certo" and c[modo]["classe"] != "certo"
    ]
    sinalizados = sum(1 for c in controles if c[modo]["sinalizado"])
    erros = classes.get("erro não sinalizado", 0)
    acertos = classes.get("acerto", 0)
    return {
        "casos": len(casos),
        "classes": classes,
        "controles": len(controles),
        "controles_sinalizados": sinalizados,
        "certos_estragados": estragados,
        "passa": erros == 0 and not estragados and acertos >= MIN_ACERTOS,
    }


def casos_nut_fora() -> list[tuple[str, dict, dict, Path]]:
    """Os quadros revisados com nut fora e referência do dono (os casos da 1031).

    Returns:
        ``(chave, item do índice, registro do dono, pasta)``, por fonte.
    """
    saida = []
    for rodada, gabarito, pasta in FONTES_CASOS:
        respostas = _ler_json(gabarito)["quadros"]
        for item in _ler_json(pasta / ARQUIVO_INDICE)["quadros"]:
            registro = respostas.get(item["id"])
            if (
                registro
                and registro.get("braco") == "sim"
                and registro.get("nut") == "fora"
                and registro.get("traste_referencia")
            ):
                saida.append((f"{rodada}:{item['id']}", item, registro, pasta))
    return saida


def medir_a5() -> dict:
    """A5 nos 16 casos: cadeia no quadro revisado com ``L3_todos_s3`` e cada estágio 2.

    Pesos que não existem saem da medida. Só desenvolvimento: os 8 casos da 1027 estão no
    treino do A5.

    Returns:
        O resultado gravado em ``medida_a5.json``.
    """
    casos = casos_nut_fora()
    linhas: dict[str, dict] = {chave: {} for chave, *_ in casos}
    totais: dict[str, dict] = {}
    for estagio2 in ESTAGIOS2_A5:
        if not _peso_existe(estagio2, DIR_PESOS):
            continue
        with _trava_gpu():
            loc = _carregar_localizador(ESTAGIO1_1031)
            dois, _ = _carregar_pesos(estagio2, PASSOS)
            previstos = {}
            for chave, item, _, pasta in casos:
                resultado = cadeia(
                    loc, dois, _imagem(pasta / item["png"]), item["id"], conjunta=True
                )
                previstos[chave] = previsto_do_resultado(
                    item, resultado, sinalizado(resultado)
                )
        contagem: dict[str, int] = {}
        for chave, _, registro, _ in casos:
            classe, numero = classe_do_caso(previstos[chave], registro)
            linhas[chave][estagio2] = {
                "classe": classe,
                "numero": numero,
                "dono": int(registro["traste_referencia"]["numero"]),
                "S1": previstos[chave]["S1"],
                "S2": previstos[chave]["S2"],
            }
            contagem[classe] = contagem.get(classe, 0) + 1
        totais[estagio2] = contagem
    resultado = {"rodada": 1031, "parte": "A5", "casos": linhas, "totais": totais}
    gravar_atomico(ARQUIVO_MEDIDA_A5, resultado)
    return resultado


def main() -> int:
    """Ponto de entrada: ``videos`` (GPU), ``quadros`` ou ``medir`` (CPU).

    Returns:
        0 se tudo rodou.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="parte", required=True)
    sub.add_parser("videos", help="roda inteiros os vídeos da 1031 (GPU)")
    sub.add_parser("quadros", help="guarda os quadros dos vídeos da 1030 (CPU)")
    sub.add_parser("medir", help="mede V, J e V+J nos casos e nos controles (CPU)")
    sub.add_parser("medir-a5", help="mede A4 e A5 nos 16 casos (GPU)")
    args = parser.parse_args()
    if args.parte == "videos":
        rodar_videos()
    elif args.parte == "quadros":
        guardar_quadros_1030()
    elif args.parte == "medir-a5":
        print(json.dumps(medir_a5()["totais"], ensure_ascii=False, indent=1))
    else:
        totais = medir()["totais"]
        print(json.dumps(totais, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

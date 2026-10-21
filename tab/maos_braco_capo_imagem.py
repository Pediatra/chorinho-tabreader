"""Rodada 1038: a casa do capo por vídeo, pela imagem, com voto entre os quadros.

Dois detectores olham o mesmo quadro:

- o **antigo** (``L3_todos_s3`` + ``A4_100_todos_s1``, treinado com o nut verdadeiro) acha o
  nut de verdade quando ele aparece;
- o **novo** (o par da 1037, treinado com a decisão 1010) põe o nut no traste à frente do
  capo.

Com capo na casa c, o nut novo cai sobre o traste c do antigo. O voto de cada quadro é o
número do traste do antigo mais perto do nut novo, se ele estiver a menos de
``TOLERANCIA_CASA`` da largura da casa. O vídeo recebe a casa que a maioria dos quadros
válidos dá. O voto 0 quer dizer "nada visto", e nunca "sem capo": com o nut verdadeiro fora
da imagem, os dois detectores põem o nut no capo.

Pré-registro: ``docs/rodadas/1038-casa-do-capo-pela-imagem.md``.

CLI: ``python -m tab.maos_braco_capo_imagem {amostrar,prever,medir}``.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
import unicodedata

import cv2
import numpy as np

from .caminhos import (
    MAOS_M11B,
    MAOS_M25,
    MAOS_M36,
    MAOS_M37,
    MAOS_M38,
    MAOS_M39,
    acervo,
)
from .maos_braco_capo import ARQUIVO_SAIDA as ARQUIVO_CAPO
from .maos_braco_ciclo import (
    _prever_quadros,
    aplicar_sinal_nut_v2,
    marcas_do_previsto,
    pesos_da_rodada,
)
from .maos_braco_geometria import eixo_do_braco
from .maos_braco_sintetico import duracao_do_video, quadro_em
from .maos_gabarito import gravar_atomico

#: Pastas cujos vídeos ficaram fora do treino da 1037 (medidas e o lote da 1039).
PASTAS_VIDEOS = (MAOS_M11B, MAOS_M25 / "prova", MAOS_M36, MAOS_M39)
#: Quadros por vídeo, espaçados de 0,10 a 0,90 da duração.
QUADROS_POR_VIDEO = 16
FRACAO_INICIO = 0.10
FRACAO_FIM = 0.90
#: O nut novo vale como voto se estiver a menos desta fração da casa de um traste do antigo.
TOLERANCIA_CASA = 0.3
#: Mínimos do voto do vídeo: quadros válidos e fração da maioria.
MINIMO_VALIDOS = 4
MAIORIA = 0.6
#: Rodada de onde vem o par antigo.
RODADA_ANTIGA = "1032"
ARQUIVO_INDICE = MAOS_M38 / "indice.json"
ARQUIVO_ESCOLHA_1037 = MAOS_M37 / "escolha_pesos.json"
ARQUIVO_MEDIDA = MAOS_M38 / "medida.json"


def _nfc(texto: str) -> str:
    """Nome de arquivo em NFC.

    Args:
        texto: nome.

    Returns:
        O nome normalizado.
    """
    return unicodedata.normalize("NFC", texto)


def fracoes(n: int = QUADROS_POR_VIDEO) -> list[float]:
    """Frações da duração dos ``n`` quadros do vídeo.

    Args:
        n: quantos quadros.

    Returns:
        ``n`` frações de ``FRACAO_INICIO`` a ``FRACAO_FIM``.
    """
    passo = (FRACAO_FIM - FRACAO_INICIO) / (n - 1)
    return [round(FRACAO_INICIO + k * passo, 6) for k in range(n)]


def videos_da_amostra() -> list[str]:
    """Vídeos das pastas fora do treino da 1037, em ordem.

    Returns:
        Caminhos relativos ao acervo.
    """
    videos: set[str] = set()
    for pasta in PASTAS_VIDEOS:
        indice = json.loads((pasta / "indice.json").read_text(encoding="utf-8"))
        videos |= {q["arquivo"] for q in indice["quadros"]}
    return sorted(videos)


def amostrar() -> int:
    """Grava os quadros de cada vídeo e o ``indice.json`` da 1038 (lê o acervo).

    Retomável: um quadro já gravado não é lido de novo. Vídeo que não está mais no acervo
    fica em ``faltando_no_acervo``.

    Returns:
        Quantidade de quadros no índice.
    """
    pasta = MAOS_M38 / "quadros"
    pasta.mkdir(parents=True, exist_ok=True)
    itens = []
    faltando = []
    for v, video in enumerate(videos_da_amostra(), start=1):
        if not (acervo() / video).exists():
            faltando.append(video)
            continue
        duracao = duracao_do_video(acervo() / video)
        for k, fracao in enumerate(fracoes(), start=1):
            id_q = f"v{v:02d}_{k:02d}"
            png = f"quadros/{id_q}.png"
            t = round(fracao * duracao, 2)
            if not (MAOS_M38 / png).exists():
                imagem = quadro_em(acervo() / video, t)
                if imagem is None:
                    continue
                cv2.imwrite(str(MAOS_M38 / png), imagem)
            imagem = cv2.imread(str(MAOS_M38 / png))
            itens.append(
                {
                    "id": id_q,
                    "arquivo": video,
                    "t": t,
                    "png": png,
                    "largura": int(imagem.shape[1]),
                    "altura": int(imagem.shape[0]),
                }
            )
    gravar_atomico(ARQUIVO_INDICE, {"faltando_no_acervo": faltando, "quadros": itens})
    return len(itens)


def voto_do_quadro(antigo: dict, novo: dict) -> int | None:
    """O traste do antigo sobre o qual cai o nut do novo.

    Args:
        antigo: previsão do detector antigo (formato de ``previsto.json``).
        novo: previsão do detector novo.

    Returns:
        O número do traste (0 é o nut do antigo), ou None quando um dos dois não achou o
        braço, um deles foi sinalizado, ou o nut novo não cai perto de nenhum traste.
    """
    if not (antigo["achou"] and novo["achou"]):
        return None
    if antigo["sinalizado"] or novo["sinalizado"]:
        return None
    marcas = marcas_do_previsto(antigo)
    if marcas is None or marcas.nut is None or not marcas.trastes:
        return None
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
    x = float(np.dot(np.asarray(novo["nut"], dtype=float) - nut, u))
    numero = min(posicao, key=lambda n: abs(posicao[n] - x))
    vizinhos = [posicao[n] for n in (numero - 1, numero + 1) if n in posicao]
    if not vizinhos:
        return None
    largura = min(abs(posicao[numero] - p) for p in vizinhos)
    if abs(posicao[numero] - x) > TOLERANCIA_CASA * largura:
        return None
    return numero


def casa_do_video(votos: list[int | None]) -> int | None:
    """A casa do capo que a maioria dos quadros válidos dá.

    Args:
        votos: ``voto_do_quadro`` de cada quadro do vídeo.

    Returns:
        A casa (≥ 1) quando há ``MINIMO_VALIDOS`` votos e a maioria tem ``MAIORIA``.
        None quando não há dado ou a maioria é 0 ("nada visto").
    """
    validos = [v for v in votos if v is not None]
    if len(validos) < MINIMO_VALIDOS:
        return None
    casa, quantos = collections.Counter(validos).most_common(1)[0]
    if quantos / len(validos) < MAIORIA or casa == 0:
        return None
    return casa


def classificar_video(afirmada: int | None, verdade: int | None) -> str:
    """Classe do vídeo contra a casa do capo do dono.

    Args:
        afirmada: ``casa_do_video``.
        verdade: casa do dono (0 sem capo), ou None se desconhecida.

    Returns:
        ``acerto``, ``erro``, ``sem_dado`` (capo não afirmado) ou ``sem_verdade``.
    """
    if verdade is None:
        return "sem_verdade"
    if afirmada is None:
        return "sem_dado"
    return "acerto" if afirmada == verdade else "erro"


def verdades() -> dict[str, int]:
    """Casa do capo de cada vídeo pelo dono: a casa, ou 0 nos vídeos sem capo.

    Returns:
        vídeo (NFC) -> casa. Vídeo com capo e casa desconhecida fica de fora.
    """
    dados = json.loads(ARQUIVO_CAPO.read_text(encoding="utf-8"))
    resultado = {_nfc(v): 0 for v in dados["sem_capo"]}
    for video in dados["videos"]:
        if video["casa"] is not None and not video["conflito"]:
            resultado[_nfc(video["arquivo"])] = video["casa"]
    return resultado


def prever() -> int:
    """Roda os dois detectores em todos os quadros (GPU) e grava as previsões.

    Returns:
        0 ao terminar.
    """
    indice = json.loads(ARQUIVO_INDICE.read_text(encoding="utf-8"))
    antigo = pesos_da_rodada(RODADA_ANTIGA)
    escolha = json.loads(ARQUIVO_ESCOLHA_1037.read_text(encoding="utf-8"))
    for rotulo, e1, e2 in (
        ("antigo", antigo.estagio1, antigo.estagio2),
        ("novo", escolha["estagio1"], escolha["estagio2"]),
    ):
        previstos = _prever_quadros(MAOS_M38, indice, e1, e2, False)
        aplicar_sinal_nut_v2(previstos, MAOS_M38, indice)
        gravar_atomico(
            MAOS_M38 / f"previsto_{rotulo}.json",
            {"pesos": [e1, e2], "quadros": previstos},
        )
    return 0


def medir() -> dict:
    """Vota por vídeo e compara com a casa do dono; grava ``medida.json``.

    Returns:
        ``videos`` (um por vídeo) e ``totais`` por classe, nos vídeos com e sem capo.
    """
    indice = json.loads(ARQUIVO_INDICE.read_text(encoding="utf-8"))["quadros"]
    antigo = json.loads((MAOS_M38 / "previsto_antigo.json").read_text("utf-8"))
    novo = json.loads((MAOS_M38 / "previsto_novo.json").read_text("utf-8"))
    casas = verdades()
    por_video: dict[str, list[int | None]] = {}
    for item in indice:
        voto = voto_do_quadro(
            antigo["quadros"][item["id"]], novo["quadros"][item["id"]]
        )
        por_video.setdefault(item["arquivo"], []).append(voto)
    videos = []
    totais: dict[str, dict[str, int]] = {"com_capo": {}, "sem_capo": {}, "?": {}}
    for video, votos in por_video.items():
        afirmada = casa_do_video(votos)
        verdade = casas.get(_nfc(video))
        classe = classificar_video(afirmada, verdade)
        grupo = "?" if verdade is None else ("com_capo" if verdade else "sem_capo")
        totais[grupo][classe] = totais[grupo].get(classe, 0) + 1
        videos.append(
            {
                "arquivo": video,
                "verdade": verdade,
                "afirmada": afirmada,
                "classe": classe,
                "votos": votos,
            }
        )
    resultado = {"videos": videos, "totais": totais}
    gravar_atomico(ARQUIVO_MEDIDA, resultado)
    return resultado


def main() -> int:
    """Ponto de entrada da CLI.

    Returns:
        0 ao terminar.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("amostrar", help="grava 16 quadros por vídeo (lê o acervo)")
    sub.add_parser("prever", help="os dois detectores em todos os quadros (GPU)")
    sub.add_parser("medir", help="voto por vídeo contra a casa do dono")
    args = parser.parse_args()
    if args.comando == "amostrar":
        print(f"{amostrar()} quadros")
    elif args.comando == "prever":
        prever()
    else:
        print(json.dumps(medir()["totais"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

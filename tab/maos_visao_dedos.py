"""Predição dos dedos da mão esquerda pela visão, para o avaliador do M3.

Para cada nota do gabarito pisada (casa 1 a 7), acha no braço o ponto (corda, casa)
com ``tab.maos_braco`` e vê qual ponta de dedo está mais perto dele no quadro do
``t_ini`` da nota. Corda solta (casa 0) é ``"0"``, sem visão.

Três variantes, cada uma gravada como um método do avaliador:

- ``visao_ponta``: o dedo mais perto no quadro em ``t_ini``;
- ``visao_ponta_voto``: maioria entre os quadros em ``t_ini-0,1``, ``t_ini`` e
  ``t_ini+0,1``; empate fica com o quadro central;
- ``visao_ou_regra``: a visão quando a ponta mais perto está a menos de meia largura
  da casa; senão ``regra_posicao_janela_1``. O limiar (meia casa) é geométrico e NÃO
  foi ajustado no gabarito.

A direita fica ``None`` (fora do escopo). Também grava ``detalhes.json`` (uma linha
por nota, com alvo, pontas e distâncias) e ``folha_visao.jpg`` (recorte da câmera do
braço de cada nota pisada, com o alvo e as pontas), para a análise dos erros.

Usa a GPU (detector de mãos do M1). Rode pelo container com ``--device``.

Uso::

    python -m tab.maos_visao_dedos
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .caminhos import GABARITO_DEDOS, MAOS_DEDOS, MAOS_M3, MVP, acervo
from .maos_avaliar_dedos import carregar_json, montar_predicao
from .maos_braco import (
    alvo_da_nota,
    dedo_mais_perto,
    escolher_mao_esquerda,
    meia_largura_casa,
    pontas_da_mao,
    votar,
)
from .maos_detector import DetectorMaos
from .maos_regra_dedos import esquerdas_por_metodo

#: Vídeo do M3 dentro do acervo montado.
VIDEO_PADRAO = acervo() / "sky guitar" / "retrato brasileiro - tab & lesson.mp4"

#: Deslocamento, em segundos, dos quadros do voto (antes e depois do ``t_ini``).
DESLOCAMENTO_VOTO = 0.1

#: Regra de posição usada no ``visao_ou_regra`` quando a visão não decide.
REGRA_FALLBACK = "regra_posicao_janela_1"

#: Câmera do braço no quadro: (x0, y0, x1, y1). Recorte da folha de conferência.
CAMERA_BRACO = (670, 520, 1920, 1080)

#: Escala do recorte na folha.
ESCALA_FOLHA = 0.5


def quadro_bgr(video: Path, instante: float) -> np.ndarray:
    """Um quadro do vídeo no instante dado, em BGR, lido pelo ffmpeg.

    Args:
        video: arquivo de vídeo (AV1 é lido pelo ffmpeg, não pelo OpenCV).
        instante: segundo do quadro.

    Returns:
        Quadro ``uint8`` em BGR.

    Raises:
        RuntimeError: se o ffmpeg não devolve um quadro decodificável.
    """
    bruto = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            f"{max(instante, 0.0):.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-f",
            "image2pipe",
            "-vcodec",
            "png",
            "-",
        ],
        check=True,
        capture_output=True,
    ).stdout
    quadro = cv2.imdecode(np.frombuffer(bruto, dtype=np.uint8), cv2.IMREAD_COLOR)
    if quadro is None:
        raise RuntimeError(f"quadro não decodificado em t={instante:.3f}")
    return quadro


def painel_da_nota(pasta_material: Path, nota_id: str) -> list[int] | None:
    """Caixa do painel da tablatura da nota, do material do M2 (ou ``None``).

    Args:
        pasta_material: pasta ``m2/dedos`` com um ``material.json`` por nota.
        nota_id: id da nota no gabarito (``n06``, ...).

    Returns:
        ``rect_tab`` do material, ou ``None`` se o material não existe.
    """
    caminho = pasta_material / nota_id / "material.json"
    if not caminho.exists():
        return None
    return carregar_json(caminho).get("rect_tab")


def decidir_quadro(
    det: DetectorMaos,
    bgr: np.ndarray,
    rect: list[int] | None,
    alvo: tuple[float, float],
) -> dict[str, Any]:
    """Decisão de um quadro: a ponta de dedo mais perto do alvo, com os detalhes.

    Args:
        det: detector de mãos (GPU).
        bgr: quadro inteiro em BGR.
        rect: caixa do painel da tablatura (ou ``None``).
        alvo: ``(x, y)`` do ponto pisado.

    Returns:
        ``dedo`` (``"1"`` a ``"4"`` ou ``None`` se não há mão esquerda no braço),
        ``distancia``, ``segunda``, ``origem`` (``wholebody`` ou ``mediapipe``),
        ``pontas`` (``dedo -> [x, y]``) e ``n_esquerda`` (quantas mãos esquerdas).
    """
    achado = det.detectar(bgr, rect)
    esquerdas = [m for m in achado["maos"] if m["lado"] == "esquerda"]
    mao = escolher_mao_esquerda(achado["maos"])
    if mao is None:
        return {
            "dedo": None,
            "distancia": None,
            "segunda": None,
            "origem": None,
            "pontas": {},
            "n_esquerda": len(esquerdas),
        }
    pontas = pontas_da_mao(mao)
    dedo, distancia, segunda = dedo_mais_perto(alvo, pontas)
    return {
        "dedo": dedo,
        "distancia": distancia,
        "segunda": segunda if np.isfinite(segunda) else None,
        "origem": mao["origem"],
        "pontas": {int(d): [round(x, 1), round(y, 1)] for d, (x, y) in pontas.items()},
        "n_esquerda": len(esquerdas),
    }


def folha(entradas: list[dict[str, Any]], colunas: int = 4) -> np.ndarray:
    """Folha de conferência: recorte da câmera do braço de cada nota pisada.

    Cada célula tem o alvo (cruz vermelha), as pontas dos dedos 1 a 4 com o número e
    o título ``id gab=X pred=Y``.

    Args:
        entradas: uma por nota, com ``quadro`` (BGR inteiro), ``alvo``, ``pontas``,
            ``titulo``.
        colunas: quantas células por linha.

    Returns:
        Imagem BGR com a grade.
    """
    x0, y0, x1, y1 = CAMERA_BRACO
    cor_dedo = {1: (0, 255, 0), 2: (255, 200, 0), 3: (0, 165, 255), 4: (255, 0, 255)}
    celulas = []
    for e in entradas:
        recorte = e["quadro"][y0:y1, x0:x1]
        recorte = cv2.resize(
            recorte,
            None,
            fx=ESCALA_FOLHA,
            fy=ESCALA_FOLHA,
            interpolation=cv2.INTER_AREA,
        )
        cabecalho = np.zeros((34, recorte.shape[1], 3), dtype=np.uint8)
        cv2.putText(
            cabecalho,
            e["titulo"],
            (6, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        celula = np.vstack([cabecalho, recorte])
        ax, ay = e["alvo"]
        px = int((ax - x0) * ESCALA_FOLHA)
        py = int((ay - y0) * ESCALA_FOLHA) + 34
        cv2.drawMarker(celula, (px, py), (0, 0, 255), cv2.MARKER_CROSS, 18, 2)
        for dedo, (x, y) in e["pontas"].items():
            qx = int((x - x0) * ESCALA_FOLHA)
            qy = int((y - y0) * ESCALA_FOLHA) + 34
            cor = cor_dedo[int(dedo)]
            cv2.circle(celula, (qx, qy), 5, cor, -1)
            cv2.putText(
                celula,
                str(dedo),
                (qx + 6, qy - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                cor,
                2,
                cv2.LINE_AA,
            )
        celulas.append(celula)
    altura = max(c.shape[0] for c in celulas)
    largura = max(c.shape[1] for c in celulas)
    linhas = []
    for i in range(0, len(celulas), colunas):
        linha = []
        for c in celulas[i : i + colunas]:
            pad = np.zeros((altura, largura, 3), dtype=np.uint8)
            pad[: c.shape[0], : c.shape[1]] = c
            linha.append(pad)
        while len(linha) < colunas:
            linha.append(np.zeros((altura, largura, 3), dtype=np.uint8))
        linhas.append(np.hstack(linha))
    return np.vstack(linhas)


def main() -> None:
    """Roda a visão nas notas do gabarito e grava predições, detalhes e a folha."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--video", type=Path, default=VIDEO_PADRAO)
    parser.add_argument("--gabarito", type=Path, default=GABARITO_DEDOS)
    parser.add_argument("--mvp", type=Path, default=MVP)
    parser.add_argument("--braco", type=Path, default=MAOS_M3 / "braco.json")
    parser.add_argument("--material", type=Path, default=MAOS_DEDOS)
    parser.add_argument("--pasta", type=Path, default=MAOS_M3)
    parser.add_argument("--dispositivo", choices=["cuda", "cpu"], default="cuda")
    args = parser.parse_args()

    braco = carregar_json(args.braco)
    cordas = {c["corda"]: {"a": c["a"], "b": c["b"]} for c in braco["cordas"]}
    trastes = {int(k): v for k, v in braco["trastes"].items()}
    mvp = carregar_json(args.mvp)["notas"]
    gabarito = carregar_json(args.gabarito)
    regra = esquerdas_por_metodo(mvp)[REGRA_FALLBACK]

    # Uma nota física por indice_mvp; o id vem da primeira entrada do gabarito.
    por_indice: dict[int, dict[str, Any]] = {}
    for gnota in gabarito["notas"]:
        por_indice.setdefault(gnota["indice_mvp"], gnota)

    det = DetectorMaos(args.dispositivo)
    detalhes: list[dict[str, Any]] = []
    decisoes: dict[str, dict[int, tuple[str | None, str | None]]] = {
        "visao_ponta": {},
        "visao_ponta_voto": {},
        "visao_ou_regra": {},
    }
    entradas_folha: list[dict[str, Any]] = []

    for indice, gnota in sorted(por_indice.items()):
        nota = mvp[indice]
        corda, casa, t = nota["corda"], nota["casa"], nota["t_ini"]
        if casa == 0:
            for variante in decisoes:
                decisoes[variante][indice] = ("0", None)
            continue
        rect = painel_da_nota(args.material, gnota["id"])
        alvo = alvo_da_nota(corda, casa, cordas, trastes)
        quadros = {}
        for nome, instante in (
            ("ant", t - DESLOCAMENTO_VOTO),
            ("meio", t),
            ("dep", t + DESLOCAMENTO_VOTO),
        ):
            bgr = quadro_bgr(args.video, instante)
            quadros[nome] = decidir_quadro(det, bgr, rect, alvo)
            if nome == "meio":
                quadro_central = bgr
        central = quadros["meio"]
        voto = votar(
            [quadros["ant"]["dedo"], central["dedo"], quadros["dep"]["dedo"]],
            padrao=central["dedo"],
        )
        meia = meia_largura_casa(casa, trastes)
        visao = central["dedo"]
        if visao is not None and central["distancia"] < meia:
            ou_regra = visao
        else:
            ou_regra = regra[indice]
        decisoes["visao_ponta"][indice] = (visao, None)
        decisoes["visao_ponta_voto"][indice] = (voto, None)
        decisoes["visao_ou_regra"][indice] = (ou_regra, None)
        detalhes.append(
            {
                "id": gnota["id"],
                "indice_mvp": indice,
                "corda": corda,
                "casa": casa,
                "t_ini": t,
                "gabarito_esquerda": gnota["esquerda"],
                "alvo": [round(alvo[0], 1), round(alvo[1], 1)],
                "meia_largura_casa": round(meia, 1),
                "visao_ponta": visao,
                "distancia": central["distancia"],
                "segunda": central["segunda"],
                "origem_mao": central["origem"],
                "n_esquerda_no_quadro": central["n_esquerda"],
                "pontas": central["pontas"],
                "votos": [quadros[n]["dedo"] for n in ("ant", "meio", "dep")],
                "visao_ponta_voto": voto,
                "visao_ou_regra": ou_regra,
                "regra_fallback": regra[indice],
            }
        )
        if gnota["esquerda"] not in ("0", "?"):
            entradas_folha.append(
                {
                    "quadro": quadro_central,
                    "alvo": alvo,
                    "pontas": {int(d): tuple(p) for d, p in central["pontas"].items()},
                    "titulo": f"{gnota['id']} gab={gnota['esquerda']} pred={visao or '-'}",
                }
            )
        print(
            f"{gnota['id']} c{corda}/k{casa} gab={gnota['esquerda']} visao={visao} "
            f"dist={central['distancia'] and round(central['distancia'], 1)} "
            f"voto={voto} ou_regra={ou_regra}",
            flush=True,
        )

    args.pasta.mkdir(parents=True, exist_ok=True)
    for metodo, dec in decisoes.items():
        pred = montar_predicao(metodo, dec)
        (args.pasta / f"pred_{metodo}.json").write_text(
            json.dumps(pred, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    (args.pasta / "detalhes_visao.json").write_text(
        json.dumps(detalhes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    cv2.imwrite(
        str(args.pasta / "folha_visao.jpg"),
        folha(entradas_folha),
        [cv2.IMWRITE_JPEG_QUALITY, 90],
    )
    print(f"{len(detalhes)} notas com visão; predições em {args.pasta}")


if __name__ == "__main__":
    main()

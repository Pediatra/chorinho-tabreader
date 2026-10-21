"""Censo de mãos (M0): mãos e rostos nos 12 quadros de presença de cada vídeo, pelo cache.

Pergunta do censo: em que canais as mãos do violonista aparecem, e como (rosto no quadro,
só o tronco, close do braço)? Isso decide quais canais servem para a trilha das mãos
antes de escolher o detector definitivo (M1).

Lê SÓ do cache de quadros (``tab.cache``, montado em ``/cache``): o acervo não é aberto.
A lista de vídeos, o instante de cada quadro e a caixa da tablatura vêm do censo de
presença (``data/saida/censo/censo_cache.jsonl``). Canais ``rollout: fora`` são pulados.

Detector do censo: MediaPipe HandLandmarker (mãos, 21 pontos) e YuNet do OpenCV (rosto),
na imagem derivada ``chorinho-maos:dev`` (``data/saida/maos/imagem/Dockerfile``).
Cada quadro passa no detector de mãos inteiro e em 4 blocos com 25 % de sobreposição (o
detector de palma reduz a imagem a 192 px e perde a mão pequena: medido em 24 quadros,
os blocos acham a mão esquerda do close do ``sky guitar`` que o quadro inteiro perde).
As detecções da mesma mão são fundidas por ``tab.maos_tabela.fundir_maos``.

Uso::

    python -m tab.maos_censo --max-por-canal 2 --saida data/saida/maos/piloto.jsonl
    python -m tab.maos_censo --saida data/saida/maos/censo_maos.jsonl
    python -m tab.maos_censo --tabela data/saida/maos/censo_maos.jsonl
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

from .cache import ModoCache, caminho_do_quadro, pasta_do_video
from .caminhos import CANAIS, CENSO_MAOS, CENSO_PRESENCA
from .censo import canais_fora, ler_rollout
from .maos_tabela import (
    dentro_da_tab,
    fundir_maos,
    markdown,
    resumo_do_video,
    tabela_por_canal,
)

#: Censo de presença: lista de vídeos, instantes e caixa da TAB por quadro.

#: Modelos dentro da imagem ``chorinho-maos:dev`` (sha256 no log do build).
MODELO_MAOS = Path("/opt/modelos/hand_landmarker.task")
MODELO_ROSTO = Path("/opt/modelos/face_detection_yunet_2023mar.onnx")

#: Confiança mínima de detecção e presença da mão. Medido no piloto (36 quadros rotulados
#: a olho pelo agente, 2 vídeos por canal): 0,5 acha a mão esquerda em 26/34 e acerta o
#: quadro em 28/36; 0,3 acha 30/34 e acerta 32/36, sem mão inventada fora do violonista.
#: O ganho é a mão do braço vista de costas; o custo é troca de lado (L/R) em ~3 de 25
#: quadros que mudaram. Blocos 3x3 pioram (25/36 e 24/36): ver o rodapé do ESTADO.
CONFIANCA_MAO = 0.3

#: Mãos por chamada do detector (há vídeo com professor e aluno no quadro).
MAX_MAOS = 4

#: Blocos por lado e sobreposição entre blocos vizinhos.
BLOCOS_POR_LADO = 2
SOBREPOSICAO_BLOCOS = 0.25

#: Semente da amostra do piloto (``--max-por-canal``).
SEMENTE = 20261012

#: Score mínimo de rosto (o padrão do YuNet é 0,9; 0,8 aceita rosto de perfil).
CONFIANCA_ROSTO = 0.8

#: Largura em que o quadro entra no detector de rosto.
LARGURA_ROSTO = 960

_detectores: dict[str, object] = {}


def criar_detectores(
    confianca: float = CONFIANCA_MAO, n_blocos: int = BLOCOS_POR_LADO
) -> None:
    """Cria os detectores de mão e de rosto do processo (um par por processo do Pool).

    Args:
        confianca: confiança mínima de detecção, presença e rastreio da mão.
        n_blocos: blocos por lado do quadro (além do quadro inteiro).
    """
    _detectores["n_blocos"] = n_blocos
    _detectores["maos"] = vision.HandLandmarker.create_from_options(
        vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(MODELO_MAOS)),
            num_hands=MAX_MAOS,
            min_hand_detection_confidence=confianca,
            min_hand_presence_confidence=confianca,
            min_tracking_confidence=confianca,
            running_mode=vision.RunningMode.IMAGE,
        )
    )
    _detectores["rosto"] = cv2.FaceDetectorYN.create(
        str(MODELO_ROSTO), "", (LARGURA_ROSTO, LARGURA_ROSTO), CONFIANCA_ROSTO
    )


def _imagem_mp(bgr: np.ndarray) -> mp.Image:
    """Converte um recorte BGR do OpenCV para a imagem RGB contígua do MediaPipe."""
    rgb = np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)


def detectar_maos(bgr: np.ndarray, x0: int, y0: int, origem: str) -> list[dict]:
    """Mãos num recorte, com os pontos já no espaço do quadro inteiro.

    Args:
        bgr: recorte do quadro (BGR).
        x0: deslocamento horizontal do recorte no quadro.
        y0: deslocamento vertical do recorte no quadro.
        origem: ``inteiro`` ou ``bloco``, guardado para auditoria.

    Returns:
        Uma entrada por mão: lado (rótulo do detector), score, caixa, palma em px
        (punho até a base do dedo médio) e os 21 pontos em px inteiros.
    """
    h, w = bgr.shape[:2]
    res = _detectores["maos"].detect(_imagem_mp(bgr))
    maos = []
    for pontos, lado in zip(res.hand_landmarks, res.handedness, strict=True):
        pts = [(x0 + p.x * w, y0 + p.y * h) for p in pontos]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        maos.append(
            {
                "lado": lado[0].category_name[0],
                "score": round(lado[0].score, 3),
                "caixa": [
                    round(min(xs)),
                    round(min(ys)),
                    round(max(xs)),
                    round(max(ys)),
                ],
                "palma_px": round(math.dist(pts[0], pts[9]), 1),
                "origem": origem,
                "pts": [[round(x), round(y)] for x, y in pts],
            }
        )
    return maos


def blocos(
    largura: int, altura: int, n: int = BLOCOS_POR_LADO
) -> list[tuple[int, int, int, int]]:
    """Blocos ``(x0, y0, x1, y1)`` que cobrem o quadro com sobreposição.

    Args:
        largura: largura do quadro.
        altura: altura do quadro.
        n: blocos por lado.

    Returns:
        ``n`` ao quadrado blocos de mesmo tamanho.
    """
    s = SOBREPOSICAO_BLOCOS
    bw, bh = int(largura / (n - (n - 1) * s)), int(altura / (n - (n - 1) * s))
    px, py = int(bw * (1 - s)), int(bh * (1 - s))
    saida = []
    for i in range(n):
        for j in range(n):
            x0, y0 = min(j * px, largura - bw), min(i * py, altura - bh)
            saida.append((x0, y0, x0 + bw, y0 + bh))
    return saida


def detectar_rostos(bgr: np.ndarray, rect: list[int] | None) -> list[dict]:
    """Rostos no quadro (YuNet), fora do painel da tablatura.

    Args:
        bgr: quadro inteiro (BGR).
        rect: caixa do painel da TAB, ou None.

    Returns:
        Uma entrada por rosto: caixa em px do quadro e score.
    """
    h, w = bgr.shape[:2]
    escala = LARGURA_ROSTO / w
    menor = cv2.resize(bgr, (LARGURA_ROSTO, max(1, round(h * escala))))
    det = _detectores["rosto"]
    det.setInputSize((menor.shape[1], menor.shape[0]))
    _, achados = det.detect(menor)
    rostos = []
    for f in achados if achados is not None else []:
        x, y, fw, fh = (float(v) / escala for v in f[:4])
        caixa = [round(x), round(y), round(x + fw), round(y + fh)]
        if not dentro_da_tab(caixa, rect):
            rostos.append({"caixa": caixa, "score": round(float(f[14]), 3)})
    return rostos


def censar_video(registro: dict) -> dict:
    """Mãos e rostos nos quadros de presença de um vídeo (só do cache).

    Args:
        registro: linha do censo de presença (``chave``, ``canal``, ``instantes``).

    Returns:
        Linha do censo de mãos: um registro por quadro lido e a lista dos que faltam.
    """
    modo = ModoCache()
    pasta = pasta_do_video(registro["chave"], modo)
    quadros, faltam = [], []
    altura = largura = None
    for i, inst in enumerate(registro["instantes"]):
        arq = caminho_do_quadro(pasta, f"presenca_{i:02d}", modo.formato)
        bgr = cv2.imread(str(arq))
        if bgr is None:
            faltam.append(i)
            continue
        altura, largura = bgr.shape[:2]
        maos = detectar_maos(bgr, 0, 0, "inteiro")
        for x0, y0, x1, y1 in blocos(largura, altura, _detectores["n_blocos"]):
            maos += detectar_maos(bgr[y0:y1, x0:x1], x0, y0, "bloco")
        maos = fundir_maos(maos)
        for m in maos:
            m["na_tab"] = dentro_da_tab(m["caixa"], inst.get("rect"))
        quadros.append(
            {
                "i": i,
                "t": inst["t"],
                "tab": inst["tab"],
                "rect": inst.get("rect"),
                "maos": maos,
                "rostos": detectar_rostos(bgr, inst.get("rect")),
            }
        )
    return {
        "chave": registro["chave"],
        "arquivo": registro["arquivo"],
        "canal": registro["canal"],
        "altura": altura,
        "largura": largura,
        "quadros": quadros,
        "faltam": faltam,
    }


def videos_do_censo(
    caminho: Path, canais: set[str] | None, max_por_canal: int | None
) -> list[dict]:
    """Vídeos a censar, a partir do censo de presença.

    Args:
        caminho: ``censo_cache.jsonl``.
        canais: só estes canais (pedido explícito: nada é pulado), ou None.
        max_por_canal: amostra por canal (semente ``SEMENTE``), ou None para todos.

    Returns:
        Registros do censo de presença, ordenados por chave dentro do canal.
    """
    fora = canais_fora(ler_rollout(CANAIS))
    por_canal: dict[str, list[dict]] = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        r = json.loads(linha)
        if r.get("erro") or not r.get("instantes"):
            continue
        if canais is not None and r["canal"] not in canais:
            continue
        if canais is None and r["canal"] in fora:
            continue
        por_canal.setdefault(r["canal"], []).append(r)
    rng = random.Random(SEMENTE)
    saida = []
    for canal in sorted(por_canal):
        regs = sorted(por_canal[canal], key=lambda r: r["chave"])
        if max_por_canal is not None and len(regs) > max_por_canal:
            regs = sorted(rng.sample(regs, max_por_canal), key=lambda r: r["chave"])
        saida += regs
    return saida


def ja_feitas(caminho: Path) -> set[str]:
    """Chaves já gravadas na saída (retomada).

    Args:
        caminho: jsonl de saída.

    Returns:
        O conjunto de chaves; vazio se o arquivo não existe.
    """
    if not caminho.exists():
        return set()
    return {
        json.loads(linha)["chave"]
        for linha in caminho.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    }


def imprimir_tabela(caminho: Path) -> None:
    """Imprime a tabela por canal de um jsonl do censo de mãos.

    Args:
        caminho: jsonl de saída do censo de mãos.
    """
    linhas = caminho.read_text(encoding="utf-8").splitlines()
    videos = [resumo_do_video(json.loads(linha)) for linha in linhas if linha.strip()]
    print(markdown(tabela_por_canal(videos)))


def main() -> int:
    """CLI do censo de mãos.

    Returns:
        Código de saída do processo.
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--saida", type=Path, default=CENSO_MAOS)
    ap.add_argument("--censo", type=Path, default=CENSO_PRESENCA)
    ap.add_argument("--canal", action="append", help="só este canal (repetível)")
    ap.add_argument("--max-por-canal", type=int, help="amostra por canal (piloto)")
    ap.add_argument("--processos", type=int, default=6)
    ap.add_argument("--confianca", type=float, default=CONFIANCA_MAO)
    ap.add_argument("--blocos", type=int, default=BLOCOS_POR_LADO, help="por lado")
    ap.add_argument("--tabela", type=Path, help="só imprime a tabela deste jsonl")
    args = ap.parse_args()

    if args.tabela:
        imprimir_tabela(args.tabela)
        return 0

    videos = videos_do_censo(
        args.censo, set(args.canal) if args.canal else None, args.max_por_canal
    )
    feitas = ja_feitas(args.saida)
    pendentes = [v for v in videos if v["chave"] not in feitas]
    print(
        f"{len(videos)} vídeos, {len(videos) - len(pendentes)} já feitos, "
        f"{len(pendentes)} pendentes, {args.processos} processos",
        flush=True,
    )
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    inicio = time.perf_counter()
    with (
        args.saida.open("a", encoding="utf-8") as saida,
        Pool(
            args.processos,
            initializer=criar_detectores,
            initargs=(args.confianca, args.blocos),
        ) as pool,
    ):
        for k, linha in enumerate(pool.imap_unordered(censar_video, pendentes), 1):
            saida.write(json.dumps(linha, ensure_ascii=False) + "\n")
            saida.flush()
            if k % 50 == 0 or k == len(pendentes):
                gasto = time.perf_counter() - inicio
                print(f"{k}/{len(pendentes)} em {gasto:.0f} s", flush=True)
    imprimir_tabela(args.saida)
    return 0


if __name__ == "__main__":
    sys.exit(main())

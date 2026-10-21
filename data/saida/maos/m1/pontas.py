"""Folhas de comparação das pontas dos dedos (M1, rascunho, fora do pacote tab/).

Compara, nas mãos que as três variantes acham, a posição das pontas dos dedos:

- MP: MediaPipe, pontos já gravados no censo ``piloto_c0.3_b2.jsonl`` (não roda de novo);
- WB-BGR: Wholebody com a imagem em BGR na pose (padrão da rtmlib);
- WB-RGB: Wholebody com a imagem convertida para RGB SÓ na pose. O detector de pessoa
  recebe BGR nas duas variantes, então as caixas são as mesmas.

Índices (confirmados em ``rtmlib/visualization/skeleton/coco133.py``): mão esquerda =
91 a 111, direita = 112 a 132; dentro de cada mão, 0 = raiz (punho) e as pontas são
4, 8, 12, 16, 20. Na pose, ``rtmlib/tools/pose_estimation/rtmpose.py`` não troca canais.

Roda dentro do container ``chorinho-maos-rtm:dev``. Grava só em
``data/saida/maos/m1/``.

Uso (dentro do container)::

    python data/saida/maos/m1/pontas.py
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import cv2
import numpy as np
from rtmlib import Wholebody

RAIZ = Path("/app")
ROTULO = RAIZ / "data/saida/maos/rotulo_agente_piloto.json"
CENSO = RAIZ / "data/saida/maos/piloto_c0.3_b2.jsonl"
CACHE_PNG = Path("/cache/png")
SAIDA = RAIZ / "data/saida/maos/m1"

#: Média dos 21 scores de uma mão do Wholebody acima disto = "a mão foi achada".
LIMIAR_ACHOU = 0.3
#: Sobreposição mínima (IoU das caixas de 21 pontos) para casar a mão com o MediaPipe.
IOU_MINIMO = 0.3
#: Margem do recorte, como fração da largura/altura da união das três caixas.
MARGEM = 0.20
#: Altura ampliada de cada recorte, em px.
ALTURA_CROP = 480
MAOS_POR_FOLHA = 5
MAOS_POR_LADO = 10
LADOS = ("esquerda", "direita")
#: Pontas dos dedos (ordem de 21 pontos, igual nos dois detectores).
PONTAS = (4, 8, 12, 16, 20)
NOME_DEDO = {4: "polegar", 8: "indicador", 12: "medio", 16: "anelar", 20: "minimo"}
#: Cores fixas por dedo, em BGR (OpenCV).
COR_DEDO = {
    4: (0, 140, 255),  # polegar: laranja
    8: (0, 255, 255),  # indicador: amarelo
    12: (0, 200, 0),  # médio: verde
    16: (255, 80, 0),  # anelar: azul
    20: (255, 0, 255),  # mínimo: magenta
}
#: Esqueleto da mão (ordem de 21 pontos).
CONEXOES = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17),
)  # fmt: skip
FAIXA_ESQ = slice(91, 112)
FAIXA_DIR = slice(112, 133)
COR_PONTO = (255, 255, 255)
COR_LINHA = (200, 200, 200)
COR_FUNDO = (30, 30, 30)
ESPACO = 12


def caminho_quadro(chave: str, quadro: int) -> Path:
    """Caminho do PNG de um quadro de presença no cache de quadros.

    Args:
        chave: chave de retomada do vídeo no censo do M0.
        quadro: índice do quadro de presença (0 a 11).

    Returns:
        Caminho de ``presenca_<quadro>.png`` dentro da pasta do vídeo.
    """
    digest = hashlib.sha1(chave.encode("utf-8")).hexdigest()[:24]
    return CACHE_PNG / digest / f"presenca_{quadro:02d}.png"


def caixa_de(pts: np.ndarray) -> np.ndarray:
    """Caixa ``xyxy`` que envolve um conjunto de pontos.

    Args:
        pts: pontos ``(N, 2)``.

    Returns:
        Array ``[x0, y0, x1, y1]``.
    """
    return np.array(
        [pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max()],
        dtype=float,
    )


def iou(a: np.ndarray, b: np.ndarray) -> float:
    """Interseção sobre união de duas caixas ``xyxy``.

    Args:
        a: primeira caixa.
        b: segunda caixa.

    Returns:
        IoU entre 0 e 1.
    """
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    uniao = area_a + area_b - inter
    return float(inter / uniao) if uniao > 0 else 0.0


def ponto_inteiro(v: np.ndarray) -> tuple[int, int]:
    """Coordenada arredondada para o cv2.

    Args:
        v: ponto ``(x, y)``.

    Returns:
        Tupla de inteiros.
    """
    return int(round(float(v[0]))), int(round(float(v[1])))


def mao_wb(kp: np.ndarray, sc: np.ndarray) -> dict:
    """Uma mão do Wholebody: pontos, scores, média e caixa.

    Args:
        kp: coordenadas ``(21, 2)``, em px do quadro original.
        sc: scores ``(21,)``.

    Returns:
        Dicionário com ``pts``, ``scores``, ``media`` e ``caixa``.
    """
    return {
        "pts": np.asarray(kp, dtype=float),
        "scores": np.asarray(sc, dtype=float),
        "media": float(np.mean(sc)),
        "caixa": caixa_de(kp),
    }


def rodar_wb(wb: Wholebody, img_bgr: np.ndarray) -> list[dict]:
    """Pessoas e mãos do Wholebody num quadro, em duas cores na pose.

    O detector de pessoa recebe a imagem BGR nas duas variantes. A pose roda uma vez
    com BGR e outra com RGB (só a pose muda). Se o detector não acha pessoa, a lista
    sai vazia, sem a pose sobre o quadro inteiro (o que a rtmlib faria).

    Args:
        wb: instância de ``rtmlib.Wholebody`` com ``to_openpose=False``.
        img_bgr: quadro em BGR (OpenCV).

    Returns:
        Uma entrada por pessoa, com as mãos ``esquerda`` e ``direita`` em
        ``BGR`` e ``RGB``.
    """
    caixas = np.asarray(wb.det_model(img_bgr), dtype=float).reshape(-1, 4)
    if not len(caixas):
        return []
    kp_bgr, sc_bgr = wb.pose_model(img_bgr, bboxes=caixas)
    img_rgb = np.ascontiguousarray(img_bgr[:, :, ::-1])
    kp_rgb, sc_rgb = wb.pose_model(img_rgb, bboxes=caixas)
    pessoas = []
    for k in range(len(caixas)):
        pessoa = {}
        for lado, faixa in (("esquerda", FAIXA_ESQ), ("direita", FAIXA_DIR)):
            pessoa[lado] = {
                "BGR": mao_wb(kp_bgr[k, faixa], sc_bgr[k, faixa]),
                "RGB": mao_wb(kp_rgb[k, faixa], sc_rgb[k, faixa]),
            }
        pessoas.append(pessoa)
    return pessoas


def carregar_censo() -> dict:
    """Censo do MediaPipe indexado pelo caminho relativo do vídeo.

    Returns:
        Dicionário ``arquivo -> registro``.
    """
    censo = {}
    for linha in CENSO.read_text(encoding="utf-8").splitlines():
        reg = json.loads(linha)
        censo[reg["arquivo"]] = reg
    return censo


def maos_mp(censo: dict, arquivo: str, quadro: int) -> list[dict]:
    """Mãos do MediaPipe gravadas no censo para um quadro.

    Args:
        censo: saída de ``carregar_censo``.
        arquivo: caminho relativo do vídeo.
        quadro: índice de presença (campo ``i`` do censo).

    Returns:
        Lista de mãos com ``lado``, ``score`` e ``pts`` ``(21, 2)`` em px.
    """
    for q in censo[arquivo]["quadros"]:
        if q["i"] == quadro:
            return [
                {
                    "lado": m["lado"],
                    "score": float(m["score"]),
                    "pts": np.asarray(m["pts"], dtype=float),
                }
                for m in q["maos"]
            ]
    return []


def carregar_itens(rotulos: list[dict], censo: dict) -> list[dict]:
    """Quadros do rótulo lidos do cache, com as mãos do MediaPipe.

    Args:
        rotulos: lista ``rotulos`` do arquivo de rótulo provisório.
        censo: saída de ``carregar_censo``.

    Returns:
        Um item por quadro, com ``rot``, ``img`` (BGR), ``png``, ``mp_maos`` e
        ``dim_censo``.

    Raises:
        SystemExit: quando um PNG do cache não pode ser lido.
    """
    itens = []
    for rot in rotulos:
        reg = censo[rot["arquivo"]]
        arq = caminho_quadro(reg["chave"], rot["quadro"])
        img = cv2.imread(str(arq))
        if img is None:
            raise SystemExit(f"PNG do quadro nao encontrado ou ilegivel: {arq}")
        itens.append(
            {
                "rot": rot,
                "img": img,
                "png": str(arq),
                "mp_maos": maos_mp(censo, rot["arquivo"], rot["quadro"]),
                "dim_censo": (reg.get("altura"), reg.get("largura")),
            }
        )
    return itens


def candidatos(indice: int, it: dict, pessoas: list[dict]) -> list[dict]:
    """Mãos de um quadro que as três variantes acham e que o rótulo marca como visíveis.

    Para cada lado com rótulo ``1``, escolhe a pessoa com maior média BGR entre as
    que têm a mão acima do limiar nas duas variantes do Wholebody, e exige uma mão do
    MediaPipe com IoU de pelo menos ``IOU_MINIMO``.

    Args:
        indice: posição do quadro em ``itens`` (para recuperar a imagem depois).
        it: item do quadro (``rot``, ``mp_maos``, ...).
        pessoas: saída de ``rodar_wb`` para o quadro.

    Returns:
        Uma entrada por mão aceita.
    """
    rot = it["rot"]
    achadas = []
    for lado in LADOS:
        if rot[lado] != 1:
            continue
        melhor = None
        for k, pessoa in enumerate(pessoas):
            m = pessoa[lado]
            if m["BGR"]["media"] <= LIMIAR_ACHOU or m["RGB"]["media"] <= LIMIAR_ACHOU:
                continue
            if melhor is None or m["BGR"]["media"] > pessoas[melhor][lado]["BGR"]["media"]:
                melhor = k
        if melhor is None:
            continue
        m = pessoas[melhor][lado]
        mp_melhor, iou_melhor = None, 0.0
        for mp in it["mp_maos"]:
            v = iou(m["BGR"]["caixa"], caixa_de(mp["pts"]))
            if v > iou_melhor:
                mp_melhor, iou_melhor = mp, v
        if mp_melhor is None or iou_melhor < IOU_MINIMO:
            continue
        achadas.append(
            {
                "id": f"n{rot['n']:02d}-{lado}",
                "n": rot["n"],
                "canal": rot["canal"],
                "arquivo": rot["arquivo"],
                "quadro": rot["quadro"],
                "lado": lado,
                "item": indice,
                "bgr": m["BGR"],
                "rgb": m["RGB"],
                "mp": mp_melhor,
                "iou_mp": iou_melhor,
            }
        )
    return achadas


def selecionar(cands: list[dict]) -> list[dict]:
    """Escolhe 10 mãos por lado, preferindo canais diferentes, na ordem do ``n``.

    Primeiro passa um candidato por canal (na ordem do ``n``); depois completa com
    os restantes, também na ordem do ``n``. Sem aleatoriedade.

    Args:
        cands: todas as mãos aceitas.

    Returns:
        Lista com as esquerdas (por ``n``) seguidas das direitas (por ``n``).
    """
    escolhidos = []
    for lado in LADOS:
        lista = sorted((c for c in cands if c["lado"] == lado), key=lambda c: c["n"])
        escolha: list[dict] = []
        canais: set[str] = set()
        for c in lista:
            if len(escolha) < MAOS_POR_LADO and c["canal"] not in canais:
                escolha.append(c)
                canais.add(c["canal"])
        ids = {c["id"] for c in escolha}
        for c in lista:
            if len(escolha) >= MAOS_POR_LADO:
                break
            if c["id"] not in ids:
                escolha.append(c)
                ids.add(c["id"])
        escolhidos.extend(sorted(escolha, key=lambda c: c["n"]))
    return escolhidos


def recorte(img: np.ndarray, conjuntos: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray, float]:
    """Recorte da união das caixas, com margem, ampliado para ``ALTURA_CROP``.

    Args:
        img: quadro original em BGR.
        conjuntos: conjuntos de pontos ``(21, 2)`` a englobar.

    Returns:
        ``base`` (imagem ampliada), ``origem`` (canto superior esquerdo do recorte em
        px do quadro) e ``escala`` (px ampliados por px originais).
    """
    caixas = np.array([caixa_de(p) for p in conjuntos])
    x0, y0 = caixas[:, 0].min(), caixas[:, 1].min()
    x1, y1 = caixas[:, 2].max(), caixas[:, 3].max()
    mx, my = MARGEM * (x1 - x0), MARGEM * (y1 - y0)
    ax0 = max(0, int(np.floor(x0 - mx)))
    ay0 = max(0, int(np.floor(y0 - my)))
    ax1 = min(img.shape[1], int(np.ceil(x1 + mx)))
    ay1 = min(img.shape[0], int(np.ceil(y1 + my)))
    escala = ALTURA_CROP / (ay1 - ay0)
    corte = img[ay0:ay1, ax0:ax1]
    largura = max(1, round((ax1 - ax0) * escala))
    base = cv2.resize(corte, (largura, ALTURA_CROP), interpolation=cv2.INTER_CUBIC)
    return base, np.array([ax0, ay0], dtype=float), escala


def desenhar_painel(
    base: np.ndarray,
    pts: np.ndarray,
    scores: np.ndarray | None,
    origem: np.ndarray,
    escala: float,
) -> np.ndarray:
    """Cópia do recorte com o esqueleto, os 21 pontos e as 5 pontas em destaque.

    Pontos com score abaixo de ``LIMIAR_ACHOU`` saem vazados (só contorno). O MediaPipe
    não tem score, então todos saem cheios.

    Args:
        base: recorte ampliado em BGR.
        pts: pontos ``(21, 2)`` em px do quadro original.
        scores: scores ``(21,)`` ou None.
        origem: canto do recorte em px do quadro original.
        escala: fator de ampliação do recorte.

    Returns:
        Painel em BGR, do mesmo tamanho do recorte.
    """
    painel = base.copy()
    p = (np.asarray(pts, dtype=float) - origem) * escala
    for a, b in CONEXOES:
        cv2.line(painel, ponto_inteiro(p[a]), ponto_inteiro(p[b]), COR_LINHA, 2, cv2.LINE_AA)
    for i in range(21):
        if i in PONTAS:
            continue
        oco = scores is not None and scores[i] < LIMIAR_ACHOU
        espessura = 1 if oco else -1
        cv2.circle(painel, ponto_inteiro(p[i]), 4, COR_PONTO, espessura, cv2.LINE_AA)
    for t in PONTAS:
        c = ponto_inteiro(p[t])
        cv2.circle(painel, c, 10, (0, 0, 0), -1, cv2.LINE_AA)
        cv2.circle(painel, c, 7, COR_DEDO[t], -1, cv2.LINE_AA)
        cv2.putText(
            painel, str(t), (c[0] + 9, c[1] - 7), cv2.FONT_HERSHEY_SIMPLEX,
            0.55, (0, 0, 0), 3, cv2.LINE_AA,
        )  # fmt: skip
        cv2.putText(
            painel, str(t), (c[0] + 9, c[1] - 7), cv2.FONT_HERSHEY_SIMPLEX,
            0.55, COR_DEDO[t], 1, cv2.LINE_AA,
        )  # fmt: skip
    return painel


def texto(img: np.ndarray, msg: str, y: int, escala: float) -> None:
    """Texto branco com contorno preto (só ASCII, o cv2 não desenha acento).

    Args:
        img: imagem a escrever (alterada no lugar).
        msg: texto.
        y: linha de base em px.
        escala: escala da fonte do cv2.
    """
    cv2.putText(img, msg, (8, y), cv2.FONT_HERSHEY_SIMPLEX, escala, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(
        img, msg, (8, y), cv2.FONT_HERSHEY_SIMPLEX, escala, (255, 255, 255), 1, cv2.LINE_AA
    )


def emoldurar(painel: np.ndarray, titulo: str, rodape: str) -> np.ndarray:
    """Acrescenta o nome da variante acima e o id abaixo do painel.

    Args:
        painel: painel já desenhado.
        titulo: nome da variante (acima).
        rodape: id ``n``, canal e lado (abaixo).

    Returns:
        Painel com as faixas de texto.
    """
    w = painel.shape[1]
    topo = np.full((48, w, 3), COR_FUNDO, np.uint8)
    base = np.full((50, w, 3), COR_FUNDO, np.uint8)
    texto(topo, titulo, 33, 0.8)
    texto(base, rodape, 34, 0.7)
    return np.vstack([topo, painel, base])


def juntar_linha(paineis: list[np.ndarray]) -> np.ndarray:
    """Três painéis lado a lado, com um espaço entre eles.

    Args:
        paineis: painéis de mesma altura.

    Returns:
        Linha única em BGR.
    """
    espaco = np.full((paineis[0].shape[0], ESPACO, 3), COR_FUNDO, np.uint8)
    partes: list[np.ndarray] = []
    for k, p in enumerate(paineis):
        if k:
            partes.append(espaco)
        partes.append(p)
    return np.hstack(partes)


def montar_folha(linhas: list[np.ndarray]) -> np.ndarray:
    """Empilha as linhas (uma por mão), alinhadas à esquerda.

    Args:
        linhas: linhas de ``juntar_linha``.

    Returns:
        Folha única em BGR.
    """
    largura = max(linha.shape[1] for linha in linhas)
    cheias = []
    for linha in linhas:
        falta = largura - linha.shape[1]
        if falta:
            linha = np.hstack(
                [linha, np.full((linha.shape[0], falta, 3), COR_FUNDO, np.uint8)]
            )
        cheias.append(linha)
    separador = np.full((ESPACO, largura, 3), COR_FUNDO, np.uint8)
    partes: list[np.ndarray] = []
    for k, linha in enumerate(cheias):
        if k:
            partes.append(separador)
        partes.append(linha)
    return np.vstack(partes)


def distancia(a: np.ndarray, b: np.ndarray) -> float:
    """Distância euclidiana entre dois pontos.

    Args:
        a: ponto ``(x, y)``.
        b: ponto ``(x, y)``.

    Returns:
        Distância em px.
    """
    return float(np.linalg.norm(np.asarray(a, dtype=float) - np.asarray(b, dtype=float)))


def medir(c: dict) -> dict:
    """Distâncias entre as pontas, em px e normalizadas pela palma (WB-BGR).

    A palma é a distância do punho (0) à base do dedo médio (9), no WB-BGR.

    Args:
        c: mão aceita (com ``bgr``, ``rgb`` e ``mp``).

    Returns:
        ``palma_px``, ``dedos`` (por dedo: ``px`` e ``norm`` para os três pares) e
        ``mediana`` (por par, mediana dos cinco dedos normalizados).
    """
    bgr, rgb, mp = c["bgr"]["pts"], c["rgb"]["pts"], c["mp"]["pts"]
    palma = distancia(bgr[0], bgr[9])
    dedos = {}
    for t in PONTAS:
        px = {
            "BGR-RGB": distancia(bgr[t], rgb[t]),
            "BGR-MP": distancia(bgr[t], mp[t]),
            "RGB-MP": distancia(rgb[t], mp[t]),
        }
        dedos[NOME_DEDO[t]] = {
            "px": px,
            "norm": {k: v / palma for k, v in px.items()},
        }
    mediana = {
        par: float(np.median([dedos[d]["norm"][par] for d in NOME_DEDO.values()]))
        for par in ("BGR-RGB", "BGR-MP", "RGB-MP")
    }
    return {"palma_px": palma, "dedos": dedos, "mediana": mediana}


def diferenca_global(itens: list[dict]) -> dict:
    """Quanto a cor muda os pontos, em todas as mãos que as duas variantes WB acham.

    Usa todos os 21 pontos de cada mão (não só as pontas) e normaliza pela palma
    do WB-BGR daquela mão.

    Args:
        itens: itens com ``wb`` já preenchido.

    Returns:
        Quantidade de mãos e de pontos, mediana e percentil 90 da distância normalizada,
        e fração dos pontos acima de 0,05 da palma.
    """
    valores = []
    maos = 0
    for it in itens:
        for pessoa in it["wb"]:
            for lado in LADOS:
                m = pessoa[lado]
                if m["BGR"]["media"] <= LIMIAR_ACHOU or m["RGB"]["media"] <= LIMIAR_ACHOU:
                    continue
                maos += 1
                palma = distancia(m["BGR"]["pts"][0], m["BGR"]["pts"][9])
                for a, b in zip(m["BGR"]["pts"], m["RGB"]["pts"]):
                    valores.append(distancia(a, b) / palma)
    v = np.array(valores)
    return {
        "maos": maos,
        "pontos": int(v.size),
        "mediana_norm": float(np.median(v)) if v.size else None,
        "p90_norm": float(np.percentile(v, 90)) if v.size else None,
        "frac_acima_0_05": float(np.mean(v > 0.05)) if v.size else None,
    }


def para_json(obj):
    """Converte arrays e escalares numpy em tipos nativos do JSON.

    Args:
        obj: estrutura com arrays e escalares numpy.

    Returns:
        Estrutura equivalente com listas e floats.
    """
    if isinstance(obj, np.ndarray):
        return [para_json(x) for x in obj.tolist()]
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    if isinstance(obj, dict):
        return {k: para_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [para_json(v) for v in obj]
    return obj


def imprimir_tabela(linhas: list[dict]) -> None:
    """Tabela por mão e medianas gerais no terminal.

    Args:
        linhas: mãos aceitas, cada uma com ``medida`` (saída de ``medir``).
    """
    print(
        "| id | lado | canal | MP lado | IoU MP | palma px | BGR x RGB | BGR x MP | RGB x MP |"
    )
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for c in linhas:
        med = c["medida"]["mediana"]
        print(
            f"| n={c['n']} | {c['lado']} | {c['canal'][:18]} | {c['mp']['lado']} | "
            f"{c['iou_mp']:.2f} | {c['medida']['palma_px']:.1f} | "
            f"{med['BGR-RGB']:.3f} | {med['BGR-MP']:.3f} | {med['RGB-MP']:.3f} |"
        )


def mediana_geral(linhas: list[dict], par: str) -> float | None:
    """Mediana de todos os dedos normalizados de um par, nas mãos dadas.

    Args:
        linhas: mãos aceitas.
        par: ``BGR-RGB``, ``BGR-MP`` ou ``RGB-MP``.

    Returns:
        Mediana (5 valores por mão), ou None sem mãos.
    """
    valores = [
        d["norm"][par] for c in linhas for d in c["medida"]["dedos"].values()
    ]
    return float(np.median(valores)) if valores else None


def main() -> None:
    """Roda o Wholebody (BGR e RGB na pose) nos 36 quadros, escolhe 20 mãos, grava folhas."""
    inicio = time.perf_counter()
    rotulos = json.loads(ROTULO.read_text(encoding="utf-8"))["rotulos"]
    censo = carregar_censo()
    itens = carregar_itens(rotulos, censo)
    print(f"{len(itens)} quadros lidos do cache (BGR, sem conversao de cor).", flush=True)

    fora_png = [
        (it["rot"]["n"], it["dim_censo"], it["img"].shape[:2])
        for it in itens
        if it["dim_censo"] != (it["img"].shape[0], it["img"].shape[1])
    ]
    print(f"quadros cujo tamanho do censo difere do PNG: {len(fora_png)}")
    for n, dc, dp in fora_png:
        print(f"  n={n}: censo {dc}, PNG {dp}")

    wb = Wholebody(backend="onnxruntime", device="cpu", to_openpose=False)
    print(f"modelos carregados em {time.perf_counter() - inicio:.1f} s", flush=True)
    rodar_wb(wb, itens[0]["img"])  # aquecimento, não gravado

    for k, it in enumerate(itens, 1):
        it["wb"] = rodar_wb(wb, it["img"])
        print(
            f"{k:2d}/{len(itens)} n={it['rot']['n']:2d} q={it['rot']['quadro']:2d} "
            f"pessoas_wb={len(it['wb'])} mp={len(it['mp_maos'])}",
            flush=True,
        )

    cands = []
    for indice, it in enumerate(itens):
        cands.extend(candidatos(indice, it, it["wb"]))
    print()
    for lado in LADOS:
        na = [c for c in cands if c["lado"] == lado]
        print(
            f"candidatos {lado}: {len(na)} mãos, {len({c['canal'] for c in na})} canais"
        )
    escolhidas = selecionar(cands)
    print(f"escolhidas: {len(escolhidas)}")

    for c in escolhidas:
        c["medida"] = medir(c)
    imprimir_tabela(escolhidas)
    print()
    for par in ("BGR-RGB", "BGR-MP", "RGB-MP"):
        print(f"mediana geral {par}: {mediana_geral(escolhidas, par):.3f}")
    global_ = diferenca_global(itens)
    print(
        f"cor x pontos, todas as maos achadas pelas duas WB ({global_['maos']} maos, "
        f"{global_['pontos']} pontos): mediana {global_['mediana_norm']:.4f}, "
        f"p90 {global_['p90_norm']:.4f}, acima de 0,05 palma "
        f"{global_['frac_acima_0_05']:.3f}"
    )

    folhas = []
    for k0 in range(0, len(escolhidas), MAOS_POR_FOLHA):
        grupo = escolhidas[k0 : k0 + MAOS_POR_FOLHA]
        linhas = []
        for c in grupo:
            img = itens[c["item"]]["img"]
            base, origem, escala = recorte(
                img, [c["bgr"]["pts"], c["rgb"]["pts"], c["mp"]["pts"]]
            )
            rodape = f"n={c['n']} | {c['canal'].encode('ascii', 'replace').decode()}"
            rodape += f" | {c['lado']}"
            paineis = [
                emoldurar(
                    desenhar_painel(base, c["mp"]["pts"], None, origem, escala),
                    "MP (MediaPipe, censo)",
                    rodape,
                ),
                emoldurar(
                    desenhar_painel(
                        base, c["bgr"]["pts"], c["bgr"]["scores"], origem, escala
                    ),
                    f"WB-BGR  media {c['bgr']['media']:.2f}",
                    rodape,
                ),
                emoldurar(
                    desenhar_painel(
                        base, c["rgb"]["pts"], c["rgb"]["scores"], origem, escala
                    ),
                    f"WB-RGB  media {c['rgb']['media']:.2f}",
                    rodape,
                ),
            ]
            linhas.append(juntar_linha(paineis))
        folhas.append(montar_folha(linhas))
    for k, folha in enumerate(folhas, 1):
        cv2.imwrite(
            str(SAIDA / f"pontas_{k}.jpg"), folha, [cv2.IMWRITE_JPEG_QUALITY, 88]
        )
        print(f"folha {k}: {folha.shape[1]}x{folha.shape[0]} px")

    nao_dentro = 0
    for c in escolhidas:
        h, w = itens[c["item"]]["img"].shape[:2]
        for pts in (c["bgr"]["pts"], c["rgb"]["pts"], c["mp"]["pts"]):
            if (pts[:, 0] < 0).any() or (pts[:, 0] >= w).any() or (pts[:, 1] < 0).any() or (pts[:, 1] >= h).any():
                nao_dentro += 1
                break
    saida = {
        "modelos": {
            "wholebody": "YOLOX-m humanart + RTMW-DW-X-L cocktail14, modo balanced, "
            "to_openpose=False, CPU (onnxruntime)",
            "variantes": {
                "MP": "censo piloto_c0.3_b2.jsonl (MediaPipe, gravado; nao rodado de novo)",
                "WB-BGR": "pose com imagem BGR (padrao rtmlib)",
                "WB-RGB": "pose com imagem convertida para RGB; deteccao de pessoa em BGR",
            },
        },
        "parametros": {
            "limiar_achou": LIMIAR_ACHOU,
            "iou_minimo_mp": IOU_MINIMO,
            "margem_recorte": MARGEM,
            "altura_crop_px": ALTURA_CROP,
            "maos_por_lado": MAOS_POR_LADO,
            "pontas": list(PONTAS),
            "cores_bgr_por_dedo": {NOME_DEDO[t]: COR_DEDO[t] for t in PONTAS},
            "palma": "distancia WB-BGR pts 0 (punho) a 9 (base do dedo medio)",
            "mediana_geral": "mediana dos 5 dedos normalizados de todas as maos escolhidas",
        },
        "indices": {
            "wb_esquerda": "91-111 (raiz 91; pontas 95, 99, 103, 107, 111)",
            "wb_direita": "112-132 (raiz 112; pontas 116, 120, 124, 128, 132)",
            "mp_e_wb_relativo_a_raiz": "0 punho; 4, 8, 12, 16, 20 pontas",
        },
        "selecao": {
            "candidatos_por_lado": {
                lado: sum(c["lado"] == lado for c in cands) for lado in LADOS
            },
            "escolhidas_por_lado": {
                lado: sum(c["lado"] == lado for c in escolhidas) for lado in LADOS
            },
            "canais_por_lado": {
                lado: len({c["canal"] for c in escolhidas if c["lado"] == lado})
                for lado in LADOS
            },
        },
        "medianas_gerais": {
            par: mediana_geral(escolhidas, par)
            for par in ("BGR-RGB", "BGR-MP", "RGB-MP")
        },
        "medianas_gerais_por_lado": {
            lado: {
                par: mediana_geral([c for c in escolhidas if c["lado"] == lado], par)
                for par in ("BGR-RGB", "BGR-MP", "RGB-MP")
            }
            for lado in LADOS
        },
        "cor_vs_pontos_todas_maos": global_,
        "maos_com_ponta_fora_do_quadro": nao_dentro,
        "maos": [
            {
                "id": c["id"],
                "n": c["n"],
                "canal": c["canal"],
                "arquivo": c["arquivo"],
                "quadro": c["quadro"],
                "lado": c["lado"],
                "lado_mp": c["mp"]["lado"],
                "iou_mp": c["iou_mp"],
                "media_bgr": c["bgr"]["media"],
                "media_rgb": c["rgb"]["media"],
                "medida": c["medida"],
                "pts_bgr": c["bgr"]["pts"],
                "scores_bgr": c["bgr"]["scores"],
                "pts_rgb": c["rgb"]["pts"],
                "scores_rgb": c["rgb"]["scores"],
                "pts_mp": c["mp"]["pts"],
            }
            for c in escolhidas
        ],
        "tempo_s": time.perf_counter() - inicio,
    }
    (SAIDA / "pontas.json").write_text(
        json.dumps(para_json(saida), ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"maos com alguma ponta fora do quadro: {nao_dentro}")
    print(f"gravado: {SAIDA / 'pontas.json'}")


if __name__ == "__main__":
    main()

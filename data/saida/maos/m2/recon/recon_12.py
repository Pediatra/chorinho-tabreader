"""Reconhecimento M2: 12 quadros nos instantes das notas, detector M1 na GPU."""

import json
import subprocess
from pathlib import Path

import cv2
import numpy as np

from tab.maos_detector import DetectorMaos

VIDEO = Path("/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4")
RECON = Path("/app/data/saida/maos/m2/recon")
QUADROS = RECON / "quadros"
CENSO = Path("/app/data/saida/maos/censo_maos.jsonl")
CHAVE = "sky guitar/retrato brasileiro - tab & lesson.mp4"
COR = {"esquerda": (0, 255, 0), "direita": (0, 140, 255), "incerto": (255, 0, 255)}


def quadros_do_censo() -> list[dict]:
    """Quadros do censo M0 deste video.

    Returns:
        Lista de quadros (``t``, ``tab``, ``rect``, ``maos``, ``rostos``).
    """
    for linha in CENSO.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        reg = json.loads(linha)
        if reg["arquivo"] == CHAVE:
            return reg["quadros"]
    raise SystemExit("video nao achado no censo")


def rect_mais_proximo(t: float, quadros: list[dict]) -> tuple[list[int] | None, float]:
    """Caixa do painel do quadro do censo mais proximo no tempo.

    Args:
        t: tempo da nota, em segundos.
        quadros: quadros do censo.

    Returns:
        Caixa (ou None) e o tempo do quadro do censo usado.
    """
    q = min(quadros, key=lambda x: abs(x["t"] - t))
    return q["rect"], q["t"]


def extrair(t: float, destino: Path) -> None:
    """Extrai um quadro do video no instante t com ffmpeg.

    Args:
        t: instante, em segundos.
        destino: PNG de saida.
    """
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y", "-i", str(VIDEO),
            "-ss", f"{t:.3f}", "-frames:v", "1", str(destino),
        ],
        check=True,
    )


def iou(a: list, b: list) -> float:
    """Intersecao sobre uniao de duas caixas (x0, y0, x1, y1).

    Args:
        a: caixa A.
        b: caixa B.

    Returns:
        IoU entre 0 e 1.
    """
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    uni = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / uni if uni > 0 else 0.0


def maos_distintas(maos: list[dict]) -> dict[str, int]:
    """Conta maos por lado, fundindo caixas do mesmo lado com IoU maior que 0,5.

    Args:
        maos: maos combinadas (com ``lado`` e ``caixa``).

    Returns:
        Quantas maos distintas por lado (esquerda, direita, incerto).
    """
    contagem = {"esquerda": 0, "direita": 0, "incerto": 0}
    for lado in contagem:
        caixas = [m["caixa"] for m in maos if m["lado"] == lado]
        grupos: list[list] = []
        for c in caixas:
            if not any(iou(c, g[0]) > 0.5 for g in grupos):
                grupos.append([c])
        contagem[lado] = len(grupos)
    return contagem


def score_da_mao(mao: dict) -> float | None:
    """Score de uma mao combinada: media dos pontos do Wholebody, ou None (MediaPipe).

    Args:
        mao: mao de ``combinar``.

    Returns:
        Media do Wholebody ou None.
    """
    return mao["media"]


def desenhar(bgr: np.ndarray, maos: list[dict], rect, cabecalho: str, esc: float) -> np.ndarray:
    """Quadro reduzido com caixas, pontos e cabecalho.

    Args:
        bgr: quadro original.
        maos: maos combinadas.
        rect: caixa do painel (ou None).
        cabecalho: texto do canto superior.
        esc: fator de escala do quadro.

    Returns:
        Imagem da celula (quadro + barra de 40 px).
    """
    img = cv2.resize(bgr, None, fx=esc, fy=esc, interpolation=cv2.INTER_AREA)
    if rect is not None:
        x0, y0, x1, y1 = (int(v * esc) for v in rect)
        cv2.rectangle(img, (x0, y0), (x1, y1), (0, 255, 255), 1)
    for m in maos:
        cor = COR[m["lado"]]
        x0, y0, x1, y1 = (int(v * esc) for v in m["caixa"])
        cv2.rectangle(img, (x0, y0), (x1, y1), cor, 2)
        for x, y in m["pts"]:
            cv2.circle(img, (int(x * esc), int(y * esc)), 2, cor, -1)
    barra = np.zeros((40, img.shape[1], 3), dtype=np.uint8)
    cv2.putText(barra, cabecalho, (6, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([barra, img])


def main() -> None:
    """Roda os 12 quadros, grava o JSON, a folha e os zooms da mao esquerda."""
    amostra = json.loads((RECON / "amostra_12.json").read_text(encoding="utf-8"))
    censo = quadros_do_censo()
    QUADROS.mkdir(parents=True, exist_ok=True)
    det = DetectorMaos("cuda")

    registros: list[dict] = []
    bgrs: list[np.ndarray] = []
    for k, nota in enumerate(amostra["notas"], 1):
        t = nota["tempo"]
        png = QUADROS / f"nota_{k:02d}_t{t:.2f}.png"
        extrair(t, png)
        bgr = cv2.imread(str(png))
        rect, t_censo = rect_mais_proximo(t, censo)
        achado = det.detectar(bgr, rect)
        maos = achado["maos"]
        bgrs.append(bgr)
        wb = [m["media"] for m in maos if m["origem"] == "wholebody"]
        mp = [m["score"] for m in achado["maos_mp"]]
        registros.append(
            {
                "n": k,
                "tempo": t,
                "tela": nota["tela"],
                "corda": nota["corda"],
                "casa": nota["casa"],
                "quadro_png": str(png.relative_to(RECON.parent.parent.parent.parent)),
                "rect_censo": rect,
                "t_censo_usado": t_censo,
                "n_maos": len(maos),
                "maos_distintas_iou": maos_distintas(maos),
                "lados": sorted(m["lado"] for m in maos),
                "maos": [
                    {
                        "lado": m["lado"],
                        "origem": m["origem"],
                        "caixa": m["caixa"],
                        "score_wholebody": score_da_mao(m),
                        "pts": m["pts"],
                    }
                    for m in maos
                ],
                "maos_mediapipe_brutas": [
                    {"lado_mp": m["lado"], "score": m["score"], "caixa": m["caixa"]}
                    for m in achado["maos_mp"]
                ],
                "score_wholebody_medio": float(np.mean(wb)) if wb else None,
                "score_mediapipe_medio": float(np.mean(mp)) if mp else None,
                "afirma": achado["afirma"],
                "pessoas_wb": len(achado["pessoas_wb"]),
            }
        )
        print(
            f"{k:02d} t={t:.2f} c{nota['corda']}/c{nota['casa']} "
            f"maos={[(m['lado'], m['origem']) for m in maos]} "
            f"pessoas_wb={len(achado['pessoas_wb'])}",
            flush=True,
        )

    (RECON / "recon_12.json").write_text(
        json.dumps(registros, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    celulas = []
    for reg, bgr in zip(registros, bgrs, strict=True):
        maos_cel = [
            {"lado": m["lado"], "caixa": m["caixa"], "pts": m["pts"]} for m in reg["maos"]
        ]
        rotulo = f"{reg['n']} {reg['tempo']:.2f}s c{reg['corda']}/c{reg['casa']}"
        celulas.append(desenhar(bgr, maos_cel, reg["rect_censo"], rotulo, 640 / 1920))
    linhas = [np.hstack(celulas[i : i + 3]) for i in range(0, 12, 3)]
    folha = np.vstack(linhas)
    cv2.imwrite(str(RECON / "folha.jpg"), folha, [cv2.IMWRITE_JPEG_QUALITY, 92])

    comEsq = [
        (
            m["score_wholebody"]
            if m["score_wholebody"] is not None
            else next(x["score"] for x in r["maos_mediapipe_brutas"]),
            r["n"],
        )
        for r in registros
        for m in r["maos"]
        if m["lado"] == "esquerda"
    ]
    alvo = sorted({min(comEsq)[1], max(comEsq)[1]}) if comEsq else []
    for n in alvo:
        reg = registros[n - 1]
        bgr = bgrs[n - 1]
        mao = next(m for m in reg["maos"] if m["lado"] == "esquerda")
        x0, y0, x1, y1 = (int(v) for v in mao["caixa"])
        m = 40
        h, w = bgr.shape[:2]
        x0, y0 = max(0, x0 - m), max(0, y0 - m)
        x1, y1 = min(w, x1 + m), min(h, y1 + m)
        recorte = cv2.resize(
            bgr[y0:y1, x0:x1], None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC
        )
        for x, y in mao["pts"]:
            cv2.circle(recorte, (int((x - x0) * 2), int((y - y0) * 2)), 4, (0, 255, 0), -1)
        cv2.imwrite(str(RECON / f"zoom_esq_{n:02d}.jpg"), recorte,
                    [cv2.IMWRITE_JPEG_QUALITY, 92])
    print("zoom esquerda: celulas", alvo)
    print("folha", folha.shape)


if __name__ == "__main__":
    main()

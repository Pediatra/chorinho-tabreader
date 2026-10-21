"""Rascunho M0: o detector de mãos do MediaPipe em quadros do cache, quadro inteiro x blocos.

Desenha as mãos achadas para OLHAR. Saída: data/saida/maos/teste_det/<n>.jpg + resumo.
"""

import hashlib
import json
import random
import sys
import time
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision

CENSO = Path("data/saida/censo/censo_cache.jsonl")
CACHE = Path("/cache/png")
SAIDA = Path("data/saida/maos/teste_det")
FORA = {"violaodecria", "tv cifras"}
CANAIS = ["sky guitar", "robert lunn", "guitar dell ́arte", "cifra club",
          "leonardo ramos", "kenneth acoustic", "iwaki", "shin izumi",
          "kimny's guitar", "pablo romé", "serge kottelat", "transcriptor"]


def pasta(chave: str) -> Path:
    return CACHE / hashlib.sha1(chave.encode("utf-8")).hexdigest()[:24]


def detector(conf: float) -> vision.HandLandmarker:
    op = vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path="/opt/modelos/hand_landmarker.task"),
        num_hands=4, min_hand_detection_confidence=conf,
        min_hand_presence_confidence=conf, min_tracking_confidence=conf,
        running_mode=vision.RunningMode.IMAGE)
    return vision.HandLandmarker.create_from_options(op)


def detectar(det, img_bgr, x0=0, y0=0):
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    res = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)))
    h, w = img_bgr.shape[:2]
    maos = []
    for lms, hd in zip(res.hand_landmarks, res.handedness):
        pts = [(x0 + p.x * w, y0 + p.y * h) for p in lms]
        maos.append({"pts": pts, "lado": hd[0].category_name, "score": hd[0].score})
    return maos


def blocos(img, n=2, sobre=0.25):
    h, w = img.shape[:2]
    bw, bh = int(w / (n - (n - 1) * sobre)), int(h / (n - (n - 1) * sobre))
    passo_x, passo_y = int(bw * (1 - sobre)), int(bh * (1 - sobre))
    for i in range(n):
        for j in range(n):
            x0, y0 = min(j * passo_x, w - bw), min(i * passo_y, h - bh)
            yield x0, y0, img[y0:y0 + bh, x0:x0 + bw]


def desenhar(img, maos, cor):
    for m in maos:
        pts = np.array(m["pts"], np.int32)
        for p in pts:
            cv2.circle(img, tuple(p), 4, cor, -1)
        x, y, w, h = cv2.boundingRect(pts)
        cv2.rectangle(img, (x, y), (x + w, y + h), cor, 2)
        cv2.putText(img, f"{m['lado'][0]} {m['score']:.2f}", (x, y - 5), 0, 0.9, cor, 2)


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    regs = {}
    for linha in CENSO.read_text().splitlines():
        r = json.loads(linha)
        regs.setdefault(r["canal"], []).append(r)
    rng = random.Random(7)
    det = detector(float(sys.argv[1]) if len(sys.argv) > 1 else 0.5)
    tempos = []
    for k, canal in enumerate(CANAIS):
        for r in rng.sample(sorted(regs[canal], key=lambda r: r["chave"]), 2):
            i = rng.randrange(12)
            img = cv2.imread(str(pasta(r["chave"]) / f"presenca_{i:02d}.png"))
            if img is None:
                continue
            t = time.perf_counter()
            inteiro = detectar(det, img)
            t1 = time.perf_counter()
            bl = []
            for x0, y0, sub in blocos(img):
                bl += detectar(det, sub, x0, y0)
            t2 = time.perf_counter()
            tempos.append((t1 - t, t2 - t1))
            vis = img.copy()
            desenhar(vis, bl, (255, 0, 255))
            desenhar(vis, inteiro, (0, 255, 0))
            vis = cv2.resize(vis, (960, round(vis.shape[0] * 960 / vis.shape[1])))
            nome = f"{canal}|{Path(r['arquivo']).stem[:40]}|p{i:02d}"
            cv2.putText(vis, nome, (5, 25), 0, 0.7, (0, 0, 0), 4)
            cv2.putText(vis, nome, (5, 25), 0, 0.7, (0, 255, 255), 2)
            cv2.imwrite(str(SAIDA / f"{k:02d}_{len(tempos):02d}.jpg"), vis)
            print(f"{nome}: inteiro {len(inteiro)} blocos {len(bl)}", flush=True)
    a = np.array(tempos)
    print("tempo medio por quadro: inteiro %.3f s, blocos(4) %.3f s" % tuple(a.mean(0)))


if __name__ == "__main__":
    main()

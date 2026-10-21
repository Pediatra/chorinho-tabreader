"""Amostras cruas em janelas dos instantes errados (so medicao)."""

import sys

sys.path.insert(0, "/app")

from tab import video as V  # noqa: E402

VIDEO = "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4"
JANELAS = [(349.0, 351.5), (497.5, 502.0), (509.5, 513.5), (523.5, 527.5), (586.5, 591.0), (664.5, 673.0), (553.5, 557.5), (478.5, 481.0)]
guarda = []
_orig = V.ler_amostras


def _captura(video, t0, t1, qps, recorte_y, caixas):
    r = _orig(video, t0, t1, qps, recorte_y, caixas)
    guarda.append((t0, t1, r, caixas))
    return r


V.ler_amostras = _captura
dados = V.transcrever_video(VIDEO)
for a, b in JANELAS:
    for t0, t1, r, caixas in guarda:
        if t0 <= a and b <= t1 + 1e-9 or (t0 <= a <= t1):
            print(f"--- janela {a}-{b} na exibicao {t0:.2f}-{t1:.2f}")
            for s in r:
                if a <= s.t <= b:
                    xs = "None" if s.x is None else f"{s.x:7.1f}"
                    cores = " ".join(f"{c:4.1f}" for c in s.cores)
                    print(f"   t={s.t:8.3f} x={xs} cores={cores}")
            break

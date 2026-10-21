"""Localiza onde muda o quadro fora do painel nos pares 134-142 (448,48-448,78 s)."""
import json

import cv2
import numpy as np

from tab import leitor

VIDEO = "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4"
SAIDA = "/app/data/saida/audio/a1b/"
PAINEL = [70, 296, 1854, 446]


def main():
    dims = leitor.dimensoes(VIDEO)
    w, h = dims
    import subprocess
    import re
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "info", "-ss", "444.0", "-copyts", "-i", VIDEO,
           "-to", "453.0", "-vf", "showinfo", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    proc = subprocess.run(cmd, capture_output=True, check=True)
    ptss = [float(v) for v in re.findall(r"pts_time:([0-9.]+)", proc.stderr.decode("utf-8", "replace"))]
    buf = np.frombuffer(proc.stdout, dtype=np.uint8)
    n = buf.size // (w * h)
    q = buf[: n * w * h].reshape(n, h, w)
    ptss = ptss[:n]
    print(f"quadros={n} pts_primeiro={ptss[0]:.4f} pts_ultimo={ptss[-1]:.4f} (esperado 444,0102 e 452,9859)")
    x0, y0, x1, y1 = PAINEL
    mascara = np.ones((h, w), dtype=bool)
    mascara[y0:y1, x0:x1] = False
    print("pares 134..142 (PTS posterior): faixa de linhas (60 px) com maior diferenca fora do painel")
    resultados = []
    for k in range(134, 143):
        d = np.abs(q[k].astype(np.int16) - q[k - 1].astype(np.int16)).astype(np.float64)
        d[~mascara] = 0
        bandas = [(yy, float(d[yy:yy + 60][mascara[yy:yy + 60]].mean()) if mascara[yy:yy+60].any() else 0.0)
                  for yy in range(0, h, 60)]
        topo = sorted(bandas, key=lambda b: -b[1])[:3]
        # fracao da area fora do painel com diferenca > 20 tons
        frac = float((d[mascara] > 20).mean())
        # mesma medida na faixa de partitura (acima do painel) e na faixa de video (abaixo)
        partitura = float(d[:y0].mean())
        video_baixo = float(d[y1:].mean())
        print(f"  k={k} pts={ptss[k]:.4f} fora={float(d[mascara].mean()):.3f} "
              f"partitura(y<{y0})={partitura:.3f} video(y>={y1})={video_baixo:.3f} "
              f"frac>20tons={frac:.4f} top_bandas_y={[(b[0], round(b[1],2)) for b in topo]}")
        resultados.append(dict(k=k, pts=ptss[k], fora=float(d[mascara].mean()), partitura=partitura,
                               video_baixo=video_baixo, frac20=frac,
                               top_bandas=[(b[0], b[1]) for b in topo]))
    for k in (137, 139, 141):
        cv2.imwrite(f"{SAIDA}m4_plato_quadro_{k:03d}_pts{ptss[k]:.3f}.png".replace(".", "p", 0), q[k])
    with open(SAIDA + "m4_plato.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

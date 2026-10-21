"""M4(a): quadros nativos 444-453 s; diferenca media entre consecutivos (dentro/fora do painel)."""
import json
import subprocess

import cv2
import numpy as np

from tab import leitor

VIDEO = "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4"
SAIDA = "/app/data/saida/audio/a1b/"
T0, T1 = 444.0, 453.0
PAINEL = [70, 296, 1854, 446]  # telas[6].painel do mvp.json (x0,y0,x1,y1)


def ler_quadros(dims):
    """Decodifica os quadros cinza de 444 a 453 s e le o PTS de cada um pelo showinfo."""
    import re
    w, h = dims
    cmd = [
        "ffmpeg", "-nostdin", "-loglevel", "info", "-ss", f"{T0:.3f}", "-copyts", "-i", VIDEO,
        "-to", f"{T1:.3f}", "-vf", "showinfo", "-fps_mode", "passthrough",
        "-f", "rawvideo", "-pix_fmt", "gray", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, check=True)
    ptss = [float(v) for v in re.findall(r"pts_time:([0-9.]+)", proc.stderr.decode("utf-8", "replace"))]
    buf = np.frombuffer(proc.stdout, dtype=np.uint8)
    n = buf.size // (w * h)
    quadros = buf[: n * w * h].reshape(n, h, w)
    m = min(n, len(ptss))
    quadros = quadros[:m]
    ptss = ptss[:m]
    print("primeiros pts showinfo:", ptss[:3], "n", len(ptss), "bytes", n)
    manter = [i for i, p in enumerate(ptss) if T0 - 1e-4 <= p < T1]
    return quadros[manter], [ptss[i] for i in manter], (n, len(ptss))


def main():
    dims = leitor.dimensoes(VIDEO)
    quadros, pts, (n_bytes, n_pts) = ler_quadros(dims)
    pts_leitor = leitor.pts_nativos(VIDEO, T0, T1)
    bate = len(pts_leitor) == len(pts) and all(abs(a - b) < 1e-3 for a, b in zip(pts, pts_leitor))
    print(f"dims={dims} quadros_showinfo={n_pts} quadros_bytes={n_bytes} pts_leitor={len(pts_leitor)}"
          f" conferem_com_leitor={bate}")
    print(f"PTS primeiro={pts[0]:.4f} ultimo={pts[-1]:.4f}; passo medio ms="
          f"{1000*(pts[-1]-pts[0])/(len(pts)-1):.3f}")
    m = len(pts)
    x0, y0, x1, y1 = PAINEL
    mascara = np.ones(quadros.shape[1:], dtype=bool)
    mascara[y0:y1, x0:x1] = False
    pares = []
    for k in range(1, m):
        a = quadros[k - 1].astype(np.int16)
        b = quadros[k].astype(np.int16)
        d = np.abs(b - a)
        pares.append(dict(
            k=k, pts=float(pts[k]),
            total=float(d.mean()),
            fora=float(d[mascara].mean()),
            painel=float(d[y0:y1, x0:x1].mean()),
        ))
    fora = np.array([p["fora"] for p in pares])
    mediana = float(np.median(fora))
    top = sorted(pares, key=lambda p: -p["fora"])[:5]
    print(f"mediana fora={mediana:.4f}; mediana painel="
          f"{np.median([p['painel'] for p in pares]):.4f}")
    print("5 maiores 'fora do painel' (PTS do quadro posterior, valor, razao p/ mediana):")
    for p in top:
        print(f"  pts={p['pts']:.4f} fora={p['fora']:.4f} razao={p['fora']/mediana:.2f}"
              f" total={p['total']:.4f} painel={p['painel']:.4f}")
    # Pico isolado: vizinhos do maior
    pico = top[0]
    kpk = pico["k"]
    vizinhos = [round(pares[j - 1]["fora"], 4) for j in (kpk - 2, kpk - 1, kpk + 1, kpk + 2)
                if 1 <= j < m]
    print("vizinhos do maior pico (k-2,k-1,k+1,k+2):", vizinhos)
    # Quadros em torno do pico: indices kpk-2..kpk+1 (quadro k-1 e k sao o par)
    for j in range(kpk - 2, kpk + 2):
        if 0 <= j < m:
            cv2.imwrite(f"{SAIDA}m4_pico_quadro_{j:03d}_pts{pts[j]:.3f}.png", quadros[j])
    # Quadros pedidos: 446, 448, 448.5, 450 (o mais proximo de cada instante)
    for alvo in (446.0, 448.0, 448.5, 450.0):
        j = int(np.argmin(np.abs(np.array(pts[:m]) - alvo)))
        nome = f"m4_t{alvo:.1f}_pts{pts[j]:.3f}".replace(".", "p") + ".png"
        cv2.imwrite(SAIDA + nome, quadros[j])
    # Diagnostico do painel: quadro com retangulo desenhado
    diag = cv2.cvtColor(quadros[kpk], cv2.COLOR_GRAY2BGR)
    cv2.rectangle(diag, (x0, y0), (x1, y1), (0, 0, 255), 3)
    cv2.imwrite(f"{SAIDA}m4_diag_painel_pts{pts[kpk]:.3f}.png", diag)
    saida = dict(
        video=VIDEO, dims=dims, n_pts=len(pts), n_decodificados=len(pts), conferem=bate,
        pts=[float(p) for p in pts], painel=PAINEL,
        mediana_fora=mediana,
        mediana_painel=float(np.median([p["painel"] for p in pares])),
        mediana_total=float(np.median([p["total"] for p in pares])),
        top5_fora=top, pares=pares,
    )
    with open(f"{SAIDA}m4_video.json", "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

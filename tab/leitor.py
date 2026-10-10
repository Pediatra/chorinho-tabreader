"""O ÚNICO jeito de ler vídeo neste projeto (Fase 1 / T1.1 do plano do produto).

Por que existe: 44 % do acervo é **AV1** e o `cv2.VideoCapture` **abre**, informa `FRAME_COUNT` e **não
decodifica** — falha **calada**, indistinguível de "vídeo sem marcador" (medido: `grab()` falhou em 30 de 30
tentativas no `mr. tabs`, `ESTADO.md` T0.3). E o caminho de um processo de `ffmpeg` por amostra foi medido em
**128 s por vídeo AV1** (241 *seeks*, e cada *seek* volta ao *keyframe*).

Duas regras desta casa:

1. **tudo em SEGUNDOS** — nunca índice de quadro (o `mr. tabs` tem 60 fps, outros 23,976);
2. **`cv2.VideoCapture` só aqui** — e só depois de **decodificar de fato um quadro de teste**; `isOpened()`
   não basta.

O que veio de onde (reaproveitar, não reinventar):

- `quadro_em`: a invocação do `varredura._ffmpeg_em` (um quadro por `-frames:v 1` + `image2pipe`);
- `quadros`: a **passada única** do `marcador._amostrar_ffmpeg` (`-ss` antes do `-i`, filtro `fps`, `rawvideo`
  `bgr24` pelo stdout) — é ela que torna o AV1 viável;
- `Leitor`: a classe `varredura.Leitor` promovida (decide **uma vez** por vídeo e cai para `ffmpeg` no meio).

Uso:

    python -m tab.leitor VIDEO [--info] [--quadro-em 245.5] [--janela 245.5 250.5 --qps 6]
"""

import argparse
import json
import subprocess
import sys
from collections.abc import Iterator

import cv2
import numpy as np


def info(caminho: str) -> dict:
    """Informações do primeiro stream de vídeo, numa chamada de ``ffprobe``.

    Args:
        caminho: vídeo.

    Returns:
        ``{"codec", "largura", "altura", "fps", "duracao_s"}``; campos ausentes viram ``None``/``0.0``.
    """
    dados: dict = {
        "codec": None,
        "largura": None,
        "altura": None,
        "fps": None,
        "duracao_s": 0.0,
    }
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=codec_name,width,height,r_frame_rate",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                caminho,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        bruto = json.loads(proc.stdout or "{}")
    except Exception:
        return dados
    fluxos = bruto.get("streams") or []
    if fluxos:
        f = fluxos[0]
        dados["codec"] = f.get("codec_name")
        dados["largura"] = int(f["width"]) if f.get("width") else None
        dados["altura"] = int(f["height"]) if f.get("height") else None
        taxa = (f.get("r_frame_rate") or "").split("/")
        if len(taxa) == 2 and float(taxa[1] or 0) > 0:
            dados["fps"] = float(taxa[0]) / float(taxa[1])
    try:
        dados["duracao_s"] = float((bruto.get("format") or {}).get("duration") or 0.0)
    except TypeError, ValueError:
        dados["duracao_s"] = 0.0
    return dados


def dimensoes(caminho: str) -> tuple[int, int] | None:
    """Largura e altura do primeiro stream de vídeo (``ffprobe``).

    Args:
        caminho: vídeo.

    Returns:
        ``(largura, altura)`` ou ``None`` se o ``ffprobe`` não responder.
    """
    d = info(caminho)
    if d["largura"] and d["altura"]:
        return int(d["largura"]), int(d["altura"])
    return None


def quadro_em(caminho: str, t_s: float) -> np.ndarray | None:
    """Um quadro no instante pedido, por ``ffmpeg`` em software (lê 100 % do acervo).

    Args:
        caminho: vídeo.
        t_s: instante, em segundos.

    Returns:
        O quadro em BGR, ou ``None`` se o ``ffmpeg`` não devolver quadro.
    """
    try:
        proc = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-nostdin",
                "-ss",
                f"{max(0.0, t_s):.3f}",
                "-i",
                caminho,
                "-frames:v",
                "1",
                "-f",
                "image2pipe",
                "-vcodec",
                "png",
                "-",
            ],
            capture_output=True,
            timeout=120,
        )
        if proc.stdout:
            quadro = cv2.imdecode(
                np.frombuffer(proc.stdout, np.uint8), cv2.IMREAD_COLOR
            )
            if quadro is not None and quadro.size:
                return quadro
    except Exception:
        return None
    return None


def quadros(
    caminho: str,
    t0: float,
    t1: float,
    qps: float,
    recorte_y: tuple[int, int] | None = None,
) -> Iterator[tuple[float, np.ndarray]]:
    """``(t, quadro)`` de ``t0`` a ``t1`` a ``qps`` quadros por segundo, numa passada de ``ffmpeg``.

    A janela é decodificada **em uma passada** (o caminho de um processo por amostra foi medido em 128 s por
    vídeo AV1). O instante de cada quadro é ``t0 + k / qps`` — aritmética de **segundos**, nunca de índice de
    quadro.

    Args:
        caminho: vídeo.
        t0: instante inicial, em segundos.
        t1: instante final, em segundos (exclusivo).
        qps: quadros por segundo a amostrar (ex.: 6.0).
        recorte_y: ``(y0, y1)`` a recortar de cada quadro, ou ``None`` para o quadro inteiro.

    Yields:
        ``(t, quadro)`` com o quadro em BGR.
    """
    dims = dimensoes(caminho)
    if dims is None or qps <= 0 or t1 <= t0:
        return
    largura, altura = dims
    y0, y1 = (
        (0, altura)
        if recorte_y is None
        else (max(0, recorte_y[0]), min(altura, recorte_y[1]))
    )
    if y1 <= y0:
        return
    altura_rec = y1 - y0
    tamanho = largura * altura_rec * 3
    filtro = f"fps={qps:.6f}"
    if recorte_y is not None:
        filtro = f"{filtro},crop={largura}:{altura_rec}:0:{y0}"
    proc = subprocess.Popen(
        [
            "ffmpeg",
            "-v",
            "error",
            "-nostdin",
            "-ss",
            f"{max(0.0, t0):.3f}",
            "-i",
            caminho,
            "-t",
            f"{t1 - t0:.3f}",
            "-vf",
            filtro,
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    try:
        k = 0
        assert proc.stdout is not None
        while True:
            bruto = proc.stdout.read(tamanho)
            if not bruto or len(bruto) < tamanho:
                break
            quadro = np.frombuffer(bruto, np.uint8).reshape((altura_rec, largura, 3))
            yield t0 + k / qps, quadro
            k += 1
    finally:
        if proc.stdout is not None:
            proc.stdout.close()
        proc.wait()


class Leitor:
    """Lê quadros de UM vídeo escolhendo, uma vez, o caminho mais rápido que **funcionar**.

    O `cv2` é ~2,4x mais rápido, mas falha em boa parte do acervo (AV1 sem aceleração). Por isso o `cv2` só é
    adotado se ele **decodificar de fato um quadro** — `isOpened()` não basta (`ESTADO.md` T0.3, evidência 4).
    Se ele falhar **no meio** do vídeo, cai para o `ffmpeg` daí em diante.
    """

    def __init__(self, caminho: str) -> None:
        self.caminho = caminho
        self.cap: cv2.VideoCapture | None = None
        self.via = "ffmpeg"
        cap = cv2.VideoCapture(caminho)
        if cap.isOpened():
            ok, quadro = cap.read()
            if ok and quadro is not None and quadro.size:
                self.cap = cap
                self.via = "cv2"
            else:
                cap.release()

    def ler(self, t_s: float) -> np.ndarray | None:
        """Quadro no instante ``t_s`` (segundos), pelo caminho escolhido.

        Args:
            t_s: instante, em segundos.

        Returns:
            O quadro em BGR, ou ``None``.
        """
        if self.cap is not None:
            self.cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t_s) * 1000.0)
            ok, quadro = self.cap.read()
            if ok and quadro is not None and quadro.size:
                return quadro
            self.cap.release()
            self.cap = None
            self.via = "ffmpeg"
        return quadro_em(self.caminho, t_s)

    def fechar(self) -> None:
        """Libera o decodificador, se houver."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None


def main() -> int:
    """CLI de inspeção: ``--info``, ``--quadro-em T`` ou ``--janela T0 T1 --qps Q``."""
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--info", action="store_true")
    ap.add_argument("--quadro-em", type=float)
    ap.add_argument("--janela", nargs=2, type=float)
    ap.add_argument("--qps", type=float, default=6.0)
    args = ap.parse_args()

    if args.info or (args.quadro_em is None and args.janela is None):
        d = info(args.video)
        print(f"info: {json.dumps(d, ensure_ascii=False)}")
    if args.quadro_em is not None:
        q = quadro_em(args.video, args.quadro_em)
        print(f"quadro_em({args.quadro_em}): {'ok' if q is not None else 'None'}")
    if args.janela is not None:
        n = 0
        for t, q in quadros(args.video, args.janela[0], args.janela[1], args.qps):
            n += 1
            if n <= 3:
                print(f"  t={t:.3f} quadro={q.shape}")
        print(
            f"quadros({args.janela[0]}, {args.janela[1]}, qps={args.qps}): {n} quadros"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

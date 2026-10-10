"""Rastreio do cursor de execução (o "marcador que passa sobre a nota").

O usuário descreveu exatamente isto: um marcador vertical que percorre a partitura/
tablatura durante a execução. É ele que dá o TEMPO de cada nota sem precisar de
áudio: x do cursor(t) -> coluna da grade -> (corda, casa) -> t.

Método (determinístico, sem modelo):
  1. Restringe a faixa da partitura (ROI), excluindo o vídeo do braço.
  2. Acha a coluna cromática: pixels com saturação alta numa faixa de matiz.
  3. O cursor é uma banda vertical CONTÍNUA e alta (cobre a ROI quase toda).
  4. x(t) = centro da banda; valida monotonicidade (o cursor não volta).

Uso:
    python -m tab.cursor VIDEO [--roi 0 300] [--passo 1] [--debug dir]
"""

from __future__ import annotations

import argparse
import itertools
import json

import cv2
import numpy as np

from . import leitor


def detectar_cursor(
    frame_bgr: np.ndarray,
    altura_min_frac: float = 0.5,
    largura_max_frac: float = 0.06,
    matizes: tuple[int, int] | None = None,
) -> tuple[int, int, tuple[int, int]] | None:
    """Devolve (x0, x1, (matiz, sat)) da banda do cursor, ou None.

    **Sem suposição de cor.** Aqui havia portão de matiz fixo (85–140, azul), herdado de
    quando o cursor medido era azul (rodada 1). Medido no `asturias` (1044 s) com o portão
    aberto: o marcador do `sky guitar` é **laranja/vermelho, matiz 13–14**, e o portão azul
    **rejeitava o marcador certo** — é a causa da varredura ter achado cursor em 69 de
    3.993 vídeos. O dono do projeto já avisou: *"sempre tem marcador, uma faixa, e não tem
    cor fixa"*.

    O que continua valendo como trava é a **geometria**: banda estreita (<= 6 % da largura)
    e cromática (não preto/branco/cinza da partitura). Quem aceita ou recusa um candidato
    passa a ser o **movimento** (`tab.tempo.resumo`): banda parada ou que aparece em
    lugares sem relação é descartada, por mais colorida que seja.

    Args:
        frame_bgr: quadro (ou recorte do painel).
        altura_min_frac: fração mínima da altura que a banda precisa cobrir.
        largura_max_frac: fração máxima da largura da imagem para a banda.
        matizes: portão de matiz OPCIONAL, para quem já sabe a cor daquele canal.

    Returns:
        ``(x0, x1, (matiz, sat))`` ou None.
    """
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    h, w = frame_bgr.shape[:2]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    # cor de verdade (não preto/branco/cinza da partitura)
    crom = (sat > 60) & (val > 90)
    if crom.sum() < 50:
        return None
    contagem = crom.sum(axis=0)
    # a banda do cursor é a coluna cromática mais "cheia"
    limite = altura_min_frac * h
    cand = contagem > limite
    if not cand.any():
        # banda estreita em imagem baixa: relaxa para o topo da distribuição
        limite = max(3, 0.6 * contagem.max())
        cand = contagem > limite
        if not cand.any():
            return None
    xs = np.flatnonzero(cand)
    # maior grupo contíguo
    grupos, ini = [], xs[0]
    for a, b in itertools.pairwise(xs):
        if b - a > 3:
            grupos.append((ini, a))
            ini = b
    grupos.append((ini, xs[-1]))
    x0, x1 = max(grupos, key=lambda g: (g[1] - g[0], contagem[g[0] : g[1] + 1].sum()))
    faixa = crom[:, x0 : x1 + 1]
    if faixa.sum() == 0:
        return None
    matiz = hsv[:, x0 : x1 + 1, 0][faixa]
    s = hsv[:, x0 : x1 + 1, 1][faixa]
    m_med, s_med = int(np.median(matiz)), int(np.median(s))
    largura = x1 - x0 + 1
    if largura > largura_max_frac * w:  # largo demais: é madeira/objeto, não banda
        return None
    if matizes is not None and not (matizes[0] <= m_med <= matizes[1]):
        return None  # portão de cor OPCIONAL (default: sem suposição de cor)
    return int(x0), int(x1), (m_med, s_med)


def rastrear(
    caminho: str,
    roi: tuple[int, int] | None = None,
    passo: int = 1,
    debug_dir: str | None = None,
) -> dict:
    """Rastreia a faixa do cursor ao longo do vídeo, lendo pelo leitor único.

    A leitura é uma passada de ``ffmpeg`` (``tab.leitor.quadros``), que decodifica AV1; o
    ``cv2.VideoCapture`` abria o AV1 e devolvia 0 amostras calado. O tempo de cada amostra é
    o ``t`` em segundos que o leitor devolve; ``frame`` é só o índice equivalente
    ``round(t * fps)``.

    Args:
        caminho: vídeo.
        roi: ``(y0, y1)`` do painel, ou ``None`` para o quadro inteiro.
        passo: amostra um quadro a cada ``passo`` quadros (``qps = fps / passo``).
        debug_dir: pasta para as 3 primeiras visões de depuração, ou ``None``.

    Returns:
        ``{"resumo", "amostras"}``. Se o vídeo não puder ser lido, o ``resumo`` traz a
        chave ``"erro"`` (e ``amostras`` vazia) em vez de parecer "vídeo sem cursor".
    """
    meta = leitor.info(caminho)
    fps = meta["fps"] or 30.0
    duracao = float(meta["duracao_s"] or 0.0)
    n = round(duracao * fps)
    y0, y1 = roi if roi else (0, 0)
    erro = None
    if not meta["largura"] or not meta["altura"]:
        erro = "ffprobe não leu as dimensões do vídeo"
    elif duracao <= 0:
        erro = "ffprobe não informou a duração do vídeo"

    amostras = []
    lidos = 0
    if erro is None:
        qps = fps / max(1, passo)
        recorte = (y0, y1) if y1 > y0 else None
        for t_s, frame in leitor.quadros(caminho, 0.0, duracao, qps, recorte_y=recorte):
            lidos += 1
            i = round(t_s * fps)
            det = detectar_cursor(frame)
            if det:
                x0, x1, (matiz, s) = det
                amostras.append(
                    {
                        "frame": i,
                        "t": t_s,
                        "x": (x0 + x1) / 2.0,
                        "x0": x0,
                        "x1": x1,
                        "largura": x1 - x0 + 1,
                        "matiz": matiz,
                        "sat": s,
                    }
                )
            if debug_dir and len(amostras) <= 3:
                vis = frame.copy()
                if det:
                    cv2.rectangle(
                        vis, (det[0], 0), (det[1], vis.shape[0] - 1), (0, 0, 255), 2
                    )
                cv2.imwrite(f"{debug_dir}/cursor_f{i:06d}.png", vis)
        if lidos == 0:
            erro = "o leitor não devolveu nenhum quadro (ffmpeg não decodificou)"

    xs = np.array([a["x"] for a in amostras])
    ts = np.array([a["t"] for a in amostras])
    # O cursor NÃO desliza: ele salta de nota em nota e fica parado enquanto a nota
    # dura (medido: x constante por ~1 s, salto de ~1 passo de nota). Por isso a
    # estatística útil é a de SALTOS, não de velocidade.
    saltos = np.array([], dtype=float)
    instantes = np.array([], dtype=float)
    retrocessos = 0
    if len(xs) > 1:
        dx = np.diff(xs)
        mask = np.abs(dx) > 5.0
        saltos = np.abs(dx[mask])
        instantes = ts[1:][mask]
        retrocessos = int((dx < -5.0).sum())
    intervalos = np.diff(instantes) if len(instantes) > 1 else np.array([])
    larguras = [a["largura"] for a in amostras]
    resumo = {
        "fps": fps,
        "frames_totais": n,
        "quadros_lidos": lidos,
        "amostras_com_cursor": len(amostras),
        "cobertura": (len(amostras) / max(1, n / passo)),
        "x_min": float(xs.min()) if len(xs) else None,
        "x_max": float(xs.max()) if len(xs) else None,
        "largura_nucleo_mediana": float(np.median(larguras)) if larguras else None,
        "largura_nucleo_p90": float(np.percentile(larguras, 90)) if larguras else None,
        "matiz_mediana": float(np.median([a["matiz"] for a in amostras]))
        if amostras
        else None,
        "posicoes_x_distintas": len(np.unique(np.round(xs))),
        "n_saltos": len(saltos),
        "salto_mediano_px": float(np.median(saltos)) if len(saltos) else None,
        "retrocessos": retrocessos,
        "intervalo_mediano_entre_saltos_s": float(np.median(intervalos))
        if len(intervalos)
        else None,
    }
    if erro:
        resumo["erro"] = erro
    return {"resumo": resumo, "amostras": amostras}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--roi", type=int, nargs=2, default=[0, 300])
    ap.add_argument("--passo", type=int, default=1)
    ap.add_argument("--debug")
    ap.add_argument("--json")
    args = ap.parse_args()
    r = rastrear(args.video, (args.roi[0], args.roi[1]), args.passo, args.debug)
    print(json.dumps(r["resumo"], indent=1, ensure_ascii=False))
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(r, fh, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

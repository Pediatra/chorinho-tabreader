"""Sonda (medida, nao produto): passada densa por quadros-chave x 12 seeks.

Para cada video da amostra (mesma do `tab.censo --amostra 20`):
(a) 12 seeks (Leitor.ler nos 12 instantes) + painel_do_quadro: tempo e veredito;
(b) intervalo entre quadros-chave (ffprobe, flag K dos pacotes): por codec e canal;
(c) passada densa: ffmpeg -skip_frame nokey (sem seek), painel em TODOS os quadros-chave:
    tempo, contagem (confere com a contagem de K) e trechos com TAB que nenhum dos 12
    instantes com TAB acertou (trecho = quadros-chave seguidos com TAB);
(d) folha dos quadros de cada trecho perdido, para olhar a precisao.
"""

import json
import subprocess
import sys
import time

import numpy as np

from tab import censo, leitor, telas, varredura
from tab.caminhos import SAIDA, acervo
from tab.presenca_aval import folha

PASTA = SAIDA / "cache_medida"
MAX_FOLHA = 40


def quadros_chave(caminho: str) -> list[float]:
    """Instantes (s) dos pacotes com flag K, por ffprobe (sem decodificar)."""
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "packet=pts_time,flags",
            "-of",
            "csv=p=0",
            caminho,
        ],
        capture_output=True,
        text=True,
        timeout=900,
    ).stdout
    kfs: list[float] = []
    for linha in out.splitlines():
        partes = linha.split(",")
        if len(partes) >= 2 and "K" in partes[1]:
            try:
                kfs.append(float(partes[0]))
            except ValueError:
                continue
    return kfs


def decodar_quadros_chave(caminho: str, largura: int, altura: int):
    """Quadros BGR decodificados com -skip_frame nokey, em passagem sequencial."""
    tamanho = largura * altura * 3
    proc = subprocess.Popen(
        [
            "ffmpeg",
            "-v",
            "error",
            "-nostdin",
            "-skip_frame",
            "nokey",
            "-i",
            caminho,
            "-fps_mode",
            "passthrough",
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
        assert proc.stdout is not None
        while True:
            bruto = proc.stdout.read(tamanho)
            if len(bruto) < tamanho:
                break
            yield np.frombuffer(bruto, np.uint8).reshape((altura, largura, 3)).copy()
    finally:
        if proc.stdout is not None:
            proc.stdout.close()
        proc.wait()


def sondar(caminho: str, canal: str) -> tuple[dict, list[tuple[np.ndarray, tuple, str]]]:
    info = leitor.info(caminho)
    dur = float(info["duracao_s"])
    largura, altura = int(info["largura"]), int(info["altura"])
    seek_ts = [round(dur * f, 2) for f in censo.FRACOES_PRESENCA]

    # (a) 12 seeks
    t0 = time.perf_counter()
    lei = leitor.Leitor(caminho)
    seek_tab: list[bool] = []
    try:
        for t in seek_ts:
            q = lei.ler(t)
            seek_tab.append(q is not None and telas.painel_do_quadro(q) is not None)
    finally:
        lei.fechar()
    t_seek = time.perf_counter() - t0
    com_tab_seek = [t for t, ok in zip(seek_ts, seek_tab, strict=True) if ok]

    # (b) quadros-chave e intervalos
    t0 = time.perf_counter()
    kfs = quadros_chave(caminho)
    t_kf = time.perf_counter() - t0
    intervalos = np.diff(kfs) if len(kfs) > 1 else np.array([])

    # (c) passada densa com painel em todos os quadros-chave
    t0 = time.perf_counter()
    t_painel = 0.0
    det: list[tuple[float, tuple | None]] = []
    quadros_guardados: dict[int, np.ndarray] = {}
    n = 0
    for quadro in decodar_quadros_chave(caminho, largura, altura):
        tp = time.perf_counter()
        rect = telas.painel_do_quadro(quadro)
        t_painel += time.perf_counter() - tp
        t_inst = kfs[n] if n < len(kfs) else float("nan")
        det.append((t_inst, tuple(int(v) for v in rect) if rect is not None else None))
        if rect is not None:
            quadros_guardados[n] = quadro
        n += 1
    t_dense_loop = time.perf_counter() - t0
    t_decode = t_dense_loop - t_painel

    # trechos: quadros-chave seguidos com TAB
    trechos: list[dict] = []
    i = 0
    while i < n:
        if det[i][1] is None:
            i += 1
            continue
        j = i
        while j + 1 < n and det[j + 1][1] is not None:
            j += 1
        ini = det[i][0]
        fim = det[j + 1][0] if j + 1 < n else det[j][0]
        acertou = any(ini <= t <= fim for t in com_tab_seek)
        trechos.append(
            {
                "t_ini": round(ini, 2),
                "t_fim": round(fim, 2),
                "n_kf": j - i + 1,
                "rect": det[i][1],
                "acertado_pelos_12": acertou,
                "primeiro_kf": i,
            }
        )
        i = j + 1

    perdidos = [tr for tr in trechos if not tr["acertado_pelos_12"]]
    frames = []
    for tr in perdidos:
        q = quadros_guardados.get(tr["primeiro_kf"])
        if q is not None and len(frames) < MAX_FOLHA:
            frames.append((q, tr["rect"], f"{canal[:14]} t={tr['t_ini']:.0f}s"))

    registro = {
        "arquivo": caminho.split("/")[-1][:60],
        "canal": canal,
        "codec": info["codec"],
        "wh": [largura, altura],
        "dur": round(dur, 1),
        "seek_tab": seek_tab,
        "seek_tempo_s": round(t_seek, 2),
        "kf_n_probe": len(kfs),
        "kf_n_decodificados": n,
        "kf_contagem_bate": len(kfs) == n,
        "kf_intervalo_mediana_s": round(float(np.median(intervalos)), 2)
        if intervalos.size
        else None,
        "kf_intervalo_max_s": round(float(np.max(intervalos)), 2)
        if intervalos.size
        else None,
        "kf_probe_tempo_s": round(t_kf, 2),
        "densa_decode_s": round(t_decode, 2),
        "densa_painel_s": round(t_painel, 2),
        "densa_total_s": round(t_kf + t_dense_loop, 2),
        "trechos_com_tab": len(trechos),
        "trechos_perdidos_pelos_12": len(perdidos),
        "trechos_perdidos": perdidos,
    }
    return registro, frames


def main() -> int:
    raiz = str(acervo())
    por = varredura.canais_e_videos(raiz, None)
    todos = [v for vids in por.values() for v in vids]
    amostra = censo.amostra_espalhada(todos, 20)
    registros: list[dict] = []
    todas_folhas: list = []
    for v in amostra:
        canal = v.split("/")[len(raiz.split("/"))]
        reg, frames = sondar(v, canal)
        registros.append(reg)
        todas_folhas.extend(frames)
        print(
            f"{reg['canal'][:16]:16} {reg['codec']:5} kf={reg['kf_n_probe']:4} "
            f"int_med={reg['kf_intervalo_mediana_s']} int_max={reg['kf_intervalo_max_s']} "
            f"seek={reg['seek_tempo_s']}s densa={reg['densa_total_s']}s "
            f"contagem_ok={reg['kf_contagem_bate']} perdidos={reg['trechos_perdidos_pelos_12']}",
            flush=True,
        )
    PASTA.mkdir(parents=True, exist_ok=True)
    (PASTA / "densa.json").write_text(
        json.dumps(registros, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    if todas_folhas:
        folha(todas_folhas, PASTA / "densa_extra.jpg", colunas=4, largura=640)
        print(f"folha: {PASTA / 'densa_extra.jpg'} ({len(todas_folhas)} quadros)")
    t_s = sum(r["seek_tempo_s"] for r in registros)
    t_d = sum(r["densa_total_s"] for r in registros)
    print(
        json.dumps(
            {
                "videos": len(registros),
                "seek_total_s": round(t_s, 1),
                "densa_total_s": round(t_d, 1),
                "razao_densa_sobre_seek": round(t_d / t_s, 2) if t_s else None,
                "videos_com_trecho_perdido": sum(
                    1 for r in registros if r["trechos_perdidos_pelos_12"]
                ),
                "trechos_perdidos_total": sum(
                    r["trechos_perdidos_pelos_12"] for r in registros
                ),
                "contagem_nao_bate": sum(
                    1 for r in registros if not r["kf_contagem_bate"]
                ),
            },
            indent=1,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

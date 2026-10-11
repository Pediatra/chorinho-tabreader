"""Medida de formato do cache de quadros (T-cache): tamanho e ida-e-volta, sem censo.

Amostra 20 canais (um vídeo por canal, do meio da lista) e mede, para os quadros de presença
(quadro inteiro, nativo, no meio do vídeo) e para os quadros de janela (recorte do painel, 3 qps):
PNG, WebP sem perda e JPEG q95.
"""

import json
import os
import sys
import time

import cv2
import numpy as np

from tab import leitor, telas, varredura
from tab.caminhos import SAIDA, acervo

RAIZ = str(acervo())
SAIDA_JSON = SAIDA / "cache_medida" / "formatos.json"


def codificar(quadro: np.ndarray, formato: str) -> bytes:
    if formato == "png":
        ok, buf = cv2.imencode(".png", quadro)
    elif formato == "webp_sem_perda":
        ok, buf = cv2.imencode(".webp", quadro, [cv2.IMWRITE_WEBP_QUALITY, 101])
    else:
        ok, buf = cv2.imencode(".jpg", quadro, [cv2.IMWRITE_JPEG_QUALITY, 95])
    assert ok
    return buf.tobytes()


def medir(quadros: list[np.ndarray]) -> dict:
    out: dict = {}
    for formato in ("png", "webp_sem_perda", "jpeg_q95"):
        tam = []
        t_enc = []
        t_dec = []
        igual = []
        for q in quadros:
            t = time.time()
            b = codificar(q, formato)
            t_enc.append(time.time() - t)
            tam.append(len(b))
            t = time.time()
            d = cv2.imdecode(np.frombuffer(b, np.uint8), cv2.IMREAD_COLOR)
            t_dec.append(time.time() - t)
            igual.append(bool(d is not None and d.shape == q.shape and np.array_equal(d, q)))
        out[formato] = {
            "bytes_medio": float(np.mean(tam)),
            "bytes_mediana": float(np.median(tam)),
            "bytes_max": int(np.max(tam)),
            "enc_s_medio": float(np.mean(t_enc)),
            "dec_s_medio": float(np.mean(t_dec)),
            "identico_em_todos": all(igual),
            "n": len(quadros),
        }
    return out


def main() -> int:
    por = varredura.canais_e_videos(RAIZ, None)
    presenca: list[np.ndarray] = []
    janela: list[np.ndarray] = []
    registros = []
    for canal, vids in list(por.items())[:20]:
        v = vids[len(vids) // 2]
        info = leitor.info(v)
        dur = float(info["duracao_s"])
        quadro = leitor.quadro_em(v, round(dur * 0.5, 2))
        reg = {
            "canal": canal,
            "codec": info["codec"],
            "wh": [info["largura"], info["altura"]],
            "dur": dur,
            "n_videos_canal": len(vids),
        }
        if quadro is not None:
            presenca.append(quadro)
            rect = telas.painel_do_quadro(quadro)
            reg["rect"] = list(rect) if rect else None
            if rect is not None and len(janela) < 40:
                t0 = round(min(dur * 0.5, dur - 10.0), 2)
                for _t, q in leitor.quadros(v, t0, t0 + 10.0, 3.0):
                    janela.append(telas.recortar(q, tuple(int(x) for x in rect)))
                reg["janela_n"] = len(janela)
        registros.append(reg)
        print(reg, flush=True)
    res = {
        "presenca_quadro_inteiro": medir(presenca),
        "janela_recorte": medir(janela),
        "n_presenca": len(presenca),
        "n_janela": len(janela),
        "raw_presenca_bytes": int(np.mean([q.size for q in presenca])),
        "raw_janela_bytes_medio": int(np.mean([q.size for q in janela])) if janela else 0,
        "videos": registros,
    }
    os.makedirs(SAIDA_JSON.parent, exist_ok=True)
    SAIDA_JSON.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "videos"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Passo 5: sonda de janela. Para 3 exibições recusadas, plota o fluxo espectral e
os picos (candidatos) em [t0-3, t1+3], com t0 e t1 marcados, e mede a fração dos
picos fortes dentro da janela. Roda DENTRO do container.
"""

import json
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from tab.audio_alinhar import MARGEM_JANELA_S
from tab.audio_extrair import garantir, ler
from tab.audio_onsets import espectrograma, fluxo_espectral, picos

VIDEO = (
    "/acervo/shin izumi/【tab】room 335 - larry carlton  - fingerstyle guitar "
    "ソロギター【タブ】.mp4"
)
PRODUTO = "/app/data/saida/audio/a2/produtos/shin_izumi_room_335.json"
SAIDA = "/app/data/saida/audio/a4/shin/figuras"
TELAS = [16, 17, 25]


def main() -> int:
    with open(PRODUTO, encoding="utf-8") as f:
        prod = json.load(f)
    telas = {int(t["id"]): t for t in prod["telas"]}
    flac, meta = garantir(VIDEO)
    amostras, taxa = ler(flac)
    t_am0 = float(meta["t_amostra0"])
    relatorio = {}
    for tela_id in TELAS:
        ex = telas[tela_id]["exibicoes"][0]
        t0, t1 = float(ex["t0"]), float(ex["t1"])
        a, b = t0 - 3.0, t1 + 3.0
        mag, tempos, _ = espectrograma(amostras, taxa, t_am0, t0=a, t1=b)
        fl = fluxo_espectral(mag)
        idx = np.asarray(picos(fl, tempos), dtype=np.int64)
        tp = tempos[idx]
        fp = fl[idx]
        dentro = (tp >= t0) & (tp <= t1)
        # Picos da janela do alinhador (t0-0,5 .. t1+0,5).
        dentro_al = (tp >= t0 - MARGEM_JANELA_S) & (tp <= t1 + MARGEM_JANELA_S)
        topo = np.argsort(fp)[::-1][: max(1, len(fp) // 4)]
        frac_topo_dentro = float(np.mean(dentro[topo])) if len(topo) else None
        relatorio[tela_id] = {
            "t0": t0,
            "t1": t1,
            "n_picos_total": int(len(tp)),
            "n_picos_dentro_t0_t1": int(dentro.sum()),
            "n_picos_dentro_aligner": int(dentro_al.sum()),
            "fracao_picos_fortes_top25pct_dentro": (
                round(frac_topo_dentro, 3) if frac_topo_dentro is not None else None
            ),
            "fluxo_mediana_dentro": round(float(np.median(fl[(tempos >= t0) & (tempos <= t1)])), 4),
            "fluxo_mediana_fora": round(
                float(np.median(np.concatenate([fl[tempos < t0], fl[tempos > t1]]))), 4
            ),
        }
        fig, ax = plt.subplots(figsize=(12, 3.5))
        ax.plot(tempos, fl, lw=0.8, color="#444", label="fluxo espectral")
        ax.plot(tp, fp, "o", ms=3, color="#c33", label="picos (candidatos)")
        ax.axvline(t0, color="#16a", ls="--", label="t0")
        ax.axvline(t1, color="#16a", ls=":", label="t1")
        ax.set_title(f"tela {tela_id} (recusada): janela [{a:.1f}, {b:.1f}] s")
        ax.set_xlabel("tempo do vídeo (s)")
        ax.legend(loc="upper right", fontsize=8)
        fig.tight_layout()
        fig.savefig(f"{SAIDA}/janela_tela{tela_id:02d}.png", dpi=110)
        plt.close(fig)
    with open(f"{SAIDA}/janela_relatorio.json", "w", encoding="utf-8") as f:
        json.dump(relatorio, f, ensure_ascii=False, indent=1)
    print(json.dumps(relatorio, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

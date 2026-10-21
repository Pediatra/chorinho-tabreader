"""Escolhe SAT_CURSOR pela regra da 0152 (C3 corrigido): calibração em 184 s, verificação em 110 s."""

import json
from pathlib import Path

import cv2
import numpy as np

from tab import leitor, rolagem_saltos as rs

SAIDA = Path("/app/data/saida/tab_frentes/fc_rolagem/rodada0152")
VIDEO = "/acervo/kenneth acoustic/location - khalid ｜ fingerstyle guitar ｜ tab + chords + lyrics.mp4"
REC = (855, 1085)
XMAX = 1640


def quadro(t: float) -> np.ndarray:
    """Quadro do kenneth em ``t``, faixa do recorte, até ``XMAX``."""
    return list(leitor.quadros(VIDEO, t, t + 0.1, 10.0, recorte_y=REC))[0][1][:, :XMAX].copy()


def nucleo(q: np.ndarray) -> np.ndarray:
    """Máscara booleana das colunas do núcleo do cursor (>= 100 px de azul, sat >= 5)."""
    hsv = cv2.cvtColor(q, cv2.COLOR_BGR2HSV)
    h, s = hsv[..., 0].astype(int), hsv[..., 1].astype(int)
    azul = (h >= 90) & (h <= 130) & (s >= 5)
    cols = np.flatnonzero(azul.sum(axis=0) >= 100)
    m = np.zeros(q.shape[:2], bool)
    m[:, cols.min() : cols.max() + 1] = True
    return m


def metricas(q: np.ndarray, lim: int, nuc: np.ndarray) -> tuple[float, float]:
    """(i) cobertura dos pixels do cursor (cinza < 240) e (ii) tinta fora do núcleo, por quadro."""
    hsv = cv2.cvtColor(q, cv2.COLOR_BGR2HSV)
    h, s = hsv[..., 0].astype(int), hsv[..., 1].astype(int)
    cinza = cv2.cvtColor(q, cv2.COLOR_BGR2GRAY)
    faixa_h = (h >= 90) & (h <= 130)
    m = faixa_h & (s >= lim)
    ref = nuc & (cinza < 240)
    tinta = cinza < 200
    cob = float((m & ref).sum() / max(ref.sum(), 1))
    fora = float((m & tinta & ~nuc).sum() / max(tinta.sum(), 1))
    return cob, fora


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    qc = quadro(184.0)
    nc = nucleo(qc)
    base = metricas(qc, 80, nc)[1]
    escolhido = None
    tabela = {}
    for lim in range(80, 4, -1):
        cob, fora = metricas(qc, lim, nc)
        tabela[lim] = {"cobertura": round(cob, 4), "tinta_fora": round(fora, 5)}
        if escolhido is None and cob >= 0.95 and fora - base <= 0.005:
            escolhido = lim
    print("calibracao 184.0 nucleo cols", int(np.flatnonzero(nc.any(axis=0)).min()), "..", int(np.flatnonzero(nc.any(axis=0)).max()), "base tinta_fora(80)", round(base, 5))
    for lim in sorted(tabela, reverse=True)[:12]:
        print(f"  sat>={lim:>2} cob={tabela[lim]['cobertura']:.4f} tinta_fora={tabela[lim]['tinta_fora']:.5f}")
    print("ESCOLHIDO (calibracao):", escolhido)
    if escolhido is None:
        raise SystemExit("nenhum limiar cumpre (i) e (ii): parar e registrar")
    qv = quadro(110.0)
    ncv = nucleo(qv)
    cob_v, fora_v = metricas(qv, escolhido, ncv)
    base_v = metricas(qv, 80, ncv)[1]
    print(f"verificacao 110.0 com sat>={escolhido}: cob={cob_v:.4f} tinta_fora={fora_v:.5f} base80={base_v:.5f} acrescimo={fora_v - base_v:.5f}")
    cal_cob, cal_fora = metricas(qc, escolhido, nc)
    print(f"calibracao com sat>={escolhido}: cob={cal_cob:.4f} tinta_fora={cal_fora:.5f} acrescimo={cal_fora - base:.5f}")
    for nome, q, nuc_, lim in (("cal184", qc, nc, escolhido), ("ver110", qv, ncv, escolhido)):
        hsv = cv2.cvtColor(q, cv2.COLOR_BGR2HSV)
        m = (hsv[..., 0].astype(int) >= 90) & (hsv[..., 0].astype(int) <= 130) & (hsv[..., 1].astype(int) >= lim)
        ov = q.copy()
        ov[m] = (0, 0, 255)
        img = np.vstack([q, ov])
        cv2.imwrite(str(SAIDA / f"mascara_cursor_{nome}_sat{lim}.png"), img)
    (SAIDA / "calibracao_cursor_escolha.json").write_text(
        json.dumps({"escolhido": escolhido, "tabela_calibracao": tabela, "base80": base,
                    "verificacao": {"cobertura": cob_v, "tinta_fora": fora_v, "base80": base_v}}, indent=1),
        encoding="utf-8")


if __name__ == "__main__":
    main()

"""T8.2: refaz c01_v1/c01_v2 em instantes com tablatura e extrai quadros do c02 (só saída em t82/)."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

import gerar
from tab import caminhos, detector_tab, leitor

SAIDA = gerar.SAIDA
EXAME = SAIDA / "exame"
ESCOLHA_C01 = {
    "c01_v1": ("cifra club/meu lugar - arlindo cruz (completa) ｜ como tocar no violão.mp4", 817.0),
    "c01_v2": ("cifra club/wicked game - chris isaak (versão única) ｜ como tocar no violão.mp4", 1243.0),
}
VIDEO_C02 = "guitar dell ́arte/none but the lonely heart (tchaikovsky), guitar lesson, sheet and tab.mp4"


def main() -> None:
    """Roda o produto nos dois cifra club e extrai quadros do c02."""
    censo = {r["arquivo"]: r for r in gerar.carregar_censo()}
    modelo = detector_tab.carregar(caminhos.DETECTOR_PADRAO)
    resultados = {}
    for pasta_nome, (video, t) in ESCOLHA_C01.items():
        rec = censo[video]
        pasta = SAIDA / "telas" / pasta_nome
        res = gerar.analisar(rec, t, modelo, pasta)
        resultados[pasta_nome] = {"t": t, **{k: res[k] for k in ("erro", "notas", "painel")}}
        print(pasta_nome, t, res.get("erro", ""), "notas=", len(res["notas"]),
              "painel=", res["painel"], flush=True)
    (EXAME / "c01_resultado.json").write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")

    rec = censo[VIDEO_C02]
    tabs = [i["t"] for i in rec["instantes"] if i.get("tab")]
    print("c02 tab instantes:", tabs, flush=True)
    a, b = min(tabs), max(tabs)
    EXAME.mkdir(parents=True, exist_ok=True)
    for k, t in enumerate(np.linspace(a, b, 8), start=1):
        t = round(float(t), 2)
        quadro = leitor.quadro_em(str(caminhos.acervo() / VIDEO_C02), t)
        nome = f"c02_q{k}_t{t:.0f}.png"
        if quadro is not None:
            cv2.imwrite(str(EXAME / nome), quadro)
        print(nome, quadro is not None, flush=True)


if __name__ == "__main__":
    main()

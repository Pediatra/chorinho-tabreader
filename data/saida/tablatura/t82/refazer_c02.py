"""T8.2: regenera c02_v1 (guitar dell'arte) num instante com tablatura visível (só saída em t82/)."""

from __future__ import annotations

import json

import gerar
from tab import caminhos, detector_tab

VIDEO_C02 = "guitar dell ́arte/none but the lonely heart (tchaikovsky), guitar lesson, sheet and tab.mp4"
T_C02 = 219.02


def main() -> None:
    """Roda o produto no c02_v1 no instante escolhido e imprime o resultado."""
    censo = {r["arquivo"]: r for r in gerar.carregar_censo()}
    rec = censo[VIDEO_C02]
    modelo = detector_tab.carregar(caminhos.DETECTOR_PADRAO)
    pasta = gerar.SAIDA / "telas" / "c02_v1"
    res = gerar.analisar(rec, T_C02, modelo, pasta)
    print("c02_v1", T_C02, res.get("erro", ""), "notas=", len(res["notas"]),
          "painel=", res["painel"], "aviso=", res.get("aviso", ""), flush=True)
    print(json.dumps(res["notas"][:5], ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()

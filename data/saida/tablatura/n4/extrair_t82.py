"""0207: cache das telas da T8.2 para o ajuste fino (como o extrair.py faz com os ouros).

Para cada tela conferida em ``r2/conferir_novos/conferencia_t82.json`` (casas do dono): quadro
no instante do ``t82/ferramenta/indice.json`` -> escolher_ou_mascara -> segmentar. Notas com
casa "x" ficam de fora. Grava ``n4/cache_t82/t82__t<id>.png`` e ``.json``, com o slug "t82".

Uso (container, cwd /app):
    python /app/data/saida/n4/extrair_t82.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "/app")

import cv2  # noqa: E402

from tab import caminhos, leitor  # noqa: E402
from tab.painel import escolher_ou_mascara  # noqa: E402
from tab.tabseg import segmentar  # noqa: E402

CACHE = Path("/app/data/saida/n4/cache_t82")
CONF = caminhos.TAB_ROTULO / "r2" / "conferir_novos" / "conferencia_t82.json"
INDICE = caminhos.SAIDA / "t82" / "ferramenta" / "indice.json"


def main() -> int:
    """Extrai o cache e imprime o total."""
    CACHE.mkdir(parents=True, exist_ok=True)
    indice = {int(r["id"]): r for r in json.loads(INDICE.read_text(encoding="utf-8"))}
    conf = json.loads(CONF.read_text(encoding="utf-8"))
    n_ok = n_notas = 0
    for t in conf["telas"]:
        if not t.get("conferida"):
            continue
        r = indice[int(t["id"])]
        frame = leitor.quadro_em(str(caminhos.acervo() / r["video"]), float(r["t"]))
        cand = escolher_ou_mascara(frame) if frame is not None else None
        grade = segmentar(cand.roi) if cand is not None else None
        if cand is None or grade is None or grade.passo <= 0:
            print(f"  SEM PAINEL/GRADE t82 tela {t['id']}", flush=True)
            continue
        nome = f"t82__t{t['id']}"
        cv2.imwrite(str(CACHE / f"{nome}.png"), cand.roi)
        notas = [
            {
                "corda": int(n["corda"]),
                "casa": int(n["casa"]),
                "x_roi": float(n["x_centro_quadro"]) - float(cand.x0),
            }
            for n in t["notas"]
            if isinstance(n["casa"], int)
        ]
        meta = {
            "slug": "t82",
            "tela": int(t["id"]),
            "quadro_ref_s": float(r["t"]),
            "x0": int(cand.x0),
            "linhas_y": [float(v) for v in grade.linhas_y],
            "passo": float(grade.passo),
            "notas": notas,
            "png": f"{nome}.png",
        }
        (CACHE / f"{nome}.json").write_text(
            json.dumps(meta, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        n_ok += 1
        n_notas += len(notas)
    print(f"t82: telas extraidas={n_ok} notas={n_notas}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

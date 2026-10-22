"""0214: cache das telas da T8.4 para o ajuste fino, já com o recorte alto.

Como o extrair_t83.py mais o cache_alto.py: para cada tela do ouro servido no passe do
modo ataque (``t84/passe_ataque/conferencia_t84_servida.json``, casas do dono e as 2 notas
ditas no chat), relê o quadro no instante do ``t84/ferramenta/indice.json``, refaz o painel
do produto e o recorte alto (``painel.recorte_alto``). A tela só entra se as cordas do
painel batem com as da ferramenta em que o dono conferiu (até 2 px): é nelas que ele
marcou a corda de cada nota. Grava ``n4/cache_t84_alto/t84__t<id>``, com o slug "t84".

Uso (container, cwd /app):
    python /app/data/saida/n4/extrair_t84.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "/app")

import cv2  # noqa: E402

from tab.comum import caminhos, leitor  # noqa: E402
from tab.tablatura.leitura.painel import escolher_ou_mascara, recorte_alto  # noqa: E402

T84 = caminhos.SAIDA / "tablatura" / "t84"
CACHE = Path("/app/data/saida/tablatura/n4/cache_t84_alto")
SERVIDO = T84 / "passe_ataque" / "conferencia_t84_servida.json"
INDICE = T84 / "ferramenta" / "indice.json"
PRE = T84 / "ferramenta" / "pre.json"


def main() -> int:
    """Extrai o cache e imprime o total."""
    CACHE.mkdir(parents=True, exist_ok=True)
    indice = {int(r["id"]): r for r in json.loads(INDICE.read_text(encoding="utf-8"))}
    pre = {int(t["id"]): t for t in json.loads(PRE.read_text(encoding="utf-8"))["telas"]}
    servido = json.loads(SERVIDO.read_text(encoding="utf-8"))
    n_ok = n_notas = 0
    for t in servido["telas"]:
        tid = int(t["id"])
        r = indice[tid]
        frame = leitor.quadro_em(str(caminhos.acervo() / r["video"]), float(r["t"]))
        cand = escolher_ou_mascara(frame) if frame is not None else None
        if cand is None:
            print(f"  SEM PAINEL t84 tela {tid}", flush=True)
            continue
        linhas_q = [float(y) + cand.y0 for y in cand.grade.linhas_y]
        if max(abs(a - b) for a, b in zip(linhas_q, pre[tid]["linhas_y"], strict=True)) > 2:
            print(f"  CORDAS DIFERENTES t84 tela {tid}: {linhas_q} x {pre[tid]['linhas_y']}")
            continue
        roi, linhas = recorte_alto(frame, cand)
        nome = f"t84__t{tid}"
        cv2.imwrite(str(CACHE / f"{nome}.png"), roi)
        notas = [
            {
                "corda": int(n["corda"]),
                "casa": int(n["casa"]),
                "x_roi": float(n["x_centro_quadro"]) - float(cand.x0),
            }
            for n in t["notas"]
            if str(n["casa"]).isdigit()
        ]
        meta = {
            "slug": "t84",
            "tela": tid,
            "quadro_ref_s": float(r["t"]),
            "x0": int(cand.x0),
            "linhas_y": linhas,
            "passo": float(cand.grade.passo),
            "notas": notas,
            "png": f"{nome}.png",
            "recorte": "alto",
        }
        (CACHE / f"{nome}.json").write_text(
            json.dumps(meta, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        n_ok += 1
        n_notas += len(notas)
    print(f"t84: telas extraidas={n_ok} de {len(servido['telas'])} notas={n_notas}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

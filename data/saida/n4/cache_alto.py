"""0211: cópia do cache real com o recorte alto (painel.recorte_alto), sem mexer nas notas.

Para cada tela de ``cache``, ``cache_t82`` e ``cache_t83``: relê o quadro, refaz o painel do
produto e confere que o ``roi`` é o mesmo do cache (mesmo x0, mesmos pixels). Grava em
``<pasta>_alto`` o recorte alto e as ``linhas_y`` deslocadas; notas, x0 e passo não mudam.
Tela cujo ``roi`` não confere é copiada como está (e contada).

Uso (container, cwd /app):
    python /app/data/saida/n4/cache_alto.py
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, "/app/data/saida/n3")
sys.path.insert(0, "/app")

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import medir as M  # noqa: E402
from tab import caminhos, leitor  # noqa: E402
from tab.painel import escolher_ou_mascara, recorte_alto  # noqa: E402

N4 = Path("/app/data/saida/n4")
PASTAS = ("cache", "cache_t82", "cache_t83")


def videos() -> dict[str, dict[int, str] | str]:
    """Vídeo por slug (ouros) ou por tela (t82, t83)."""
    v: dict = dict(M.videos_do_run())
    extra = json.loads((M.OURO / f"{M.EXTRA_SLUG}.json").read_text(encoding="utf-8"))
    v.setdefault(M.EXTRA_SLUG, "/acervo/" + extra["video"])
    for lote in ("t82", "t83"):
        ind = json.loads((caminhos.SAIDA / lote / "ferramenta" / "indice.json").read_text())
        v[lote] = {int(r["id"]): str(caminhos.acervo() / r["video"]) for r in ind}
    return v


def main() -> int:
    """Copia os três caches com o recorte alto e imprime o que conferiu."""
    vids = videos()
    for pasta in PASTAS:
        origem, destino = N4 / pasta, N4 / f"{pasta}_alto"
        destino.mkdir(exist_ok=True)
        ok = sem_conferir = 0
        for caminho in sorted(origem.glob("*.json")):
            meta = json.loads(caminho.read_text(encoding="utf-8"))
            v = vids[meta["slug"]]
            video = v[int(meta["tela"])] if isinstance(v, dict) else v
            frame = leitor.quadro_em(video, float(meta["quadro_ref_s"]))
            cand = escolher_ou_mascara(frame) if frame is not None else None
            antigo = cv2.imread(str(origem / meta["png"]))
            if (
                cand is None
                or int(cand.x0) != int(meta["x0"])
                or cand.roi.shape != antigo.shape
                or not np.array_equal(cand.roi, antigo)
            ):
                shutil.copy(origem / meta["png"], destino / meta["png"])
                shutil.copy(caminho, destino / caminho.name)
                sem_conferir += 1
                print(f"  não conferiu: {pasta}/{caminho.stem}", flush=True)
                continue
            roi, linhas = recorte_alto(frame, cand)
            delta = linhas[0] - float(cand.grade.linhas_y[0])
            meta["linhas_y"] = [float(y) + delta for y in meta["linhas_y"]]
            meta["recorte"] = "alto"
            cv2.imwrite(str(destino / meta["png"]), roi)
            (destino / caminho.name).write_text(
                json.dumps(meta, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            ok += 1
        print(f"{pasta}: alto={ok} copiadas sem conferir={sem_conferir}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

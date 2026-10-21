"""0212: os pesos _ger da leitura comum, recorte antigo x alto, nos 8 ouros (CV por vídeo).

Cada ouro é lido pelos pesos da dobra que não o viu (``detector_tab_v3ft_d<d>_ger``,
``_ger_s2``, ``_ger_s3``), no mesmo quadro e no mesmo painel; só muda o recorte entregue ao
detector. Régua da decisão 0010 (``_metricas_par``). Grava ``diag/recorte_comum.json``.

Uso (container): env PYTHONPATH=/app python /app/data/saida/tab_rotulo/diag/recorte_comum.py
"""

import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/app/data/saida/n3")
sys.path.insert(0, "/app/data/saida/n4")

import medir as M  # noqa: E402
import treinar_ft as T  # noqa: E402
from tab import detector_tab, leitor  # noqa: E402
from tab.avaliar_video import FRACAO_PASSO, NotaPrevista, _metricas_par  # noqa: E402
from tab.gpu import trava_gpu  # noqa: E402
from tab.painel import escolher_ou_mascara, recorte_alto  # noqa: E402
from tab.reconhecer import ALGARISMOS  # noqa: E402
from tab.tabseg import segmentar  # noqa: E402

ARTEFATOS = Path("/app/artefatos")
#: Família de pesos por variável de ambiente (seguimento da 0212: PESOS=atqa, só alto).
PESOS = os.environ.get("PESOS", "ger")
SUFIXOS = (
    {1: "_ger", 2: "_ger_s2", 3: "_ger_s3"}
    if PESOS == "ger"
    else {s: f"_{PESOS}_s{s}" for s in (1, 2, 3)}
)
RECORTES = ("painel", "alto") if PESOS == "ger" else ("alto",)
CAMPOS = ("notas_ouro", "entregues", "casadas", "casa_certa", "inventadas", "perdidas")


def videos() -> dict[str, str]:
    """Vídeo de cada um dos 8 ouros (como ``n4/cache_alto.py``)."""
    v = dict(M.videos_do_run())
    extra = json.loads((M.OURO / f"{M.EXTRA_SLUG}.json").read_text(encoding="utf-8"))
    v.setdefault(M.EXTRA_SLUG, "/acervo/" + extra["video"])
    return v


def main() -> int:
    """Mede, imprime e grava."""
    vids = videos()
    soma = {(s, r): Counter() for s in SUFIXOS for r in RECORTES}
    por_video: dict[str, dict] = {}
    for d, slugs in sorted(T.DOBRAS.items()):
        if d == 0:
            continue
        modelos = {
            s: detector_tab.carregar(
                ARTEFATOS / f"detector_tab_v3ft_d{d}{suf}" / "modelo.pt"
            )
            for s, suf in SUFIXOS.items()
        }
        for slug in slugs:
            ouro = json.loads((M.OURO / f"{slug}.json").read_text(encoding="utf-8"))
            v = {(s, r): Counter() for s in SUFIXOS for r in RECORTES}
            for tela in (t for t in ouro["telas"] if t.get("conferida")):
                frame = leitor.quadro_em(vids[slug], float(tela["quadro_ref_s"]))
                cand = escolher_ou_mascara(frame) if frame is not None else None
                grade = segmentar(cand.roi) if cand is not None else None
                if cand is None or grade is None or grade.passo <= 0:
                    for s in SUFIXOS:
                        for r in RECORTES:
                            v[(s, r)]["notas_ouro"] += len(tela["notas"])
                            v[(s, r)]["perdidas"] += len(tela["notas"])
                    continue
                passo = float(grade.passo)
                alto, linhas_alto = recorte_alto(frame, cand)
                desloc = linhas_alto[0] - float(cand.grade.linhas_y[0])
                entradas = {
                    "painel": (cand.roi, [float(y) for y in grade.linhas_y]),
                    "alto": (alto, [float(y) + desloc for y in grade.linhas_y]),
                }
                for r in RECORTES:
                    roi, ly = entradas[r]
                    for s, m in modelos.items():
                        prev = [
                            NotaPrevista(
                                int(n["corda"]),
                                int(n["rotulo"]),
                                cand.x0 + float(n["x"]),
                                None,
                            )
                            for n in detector_tab.detectar(m, roi, ly, passo)
                            if n["rotulo"] in ALGARISMOS
                        ]
                        mt = _metricas_par(tela["notas"], prev, FRACAO_PASSO * passo)
                        v[(s, r)] += Counter({k: mt[k] for k in CAMPOS})
            for k, c in v.items():
                soma[k] += c
            por_video[slug] = {f"s{s}_{r}": dict(c) for (s, r), c in v.items()}
            print(
                slug,
                " | ".join(
                    f"s{s} {r}: perd {v[(s, r)]['perdidas']} inv {v[(s, r)]['inventadas']}"
                    f" casa err {v[(s, r)]['casadas'] - v[(s, r)]['casa_certa']}"
                    for s in SUFIXOS
                    for r in RECORTES
                ),
                flush=True,
            )
    for (s, r), c in sorted(soma.items()):
        print(
            f"s{s} {r}: ouro {c['notas_ouro']} entregues {c['entregues']} perdidas"
            f" {c['perdidas']} inventadas {c['inventadas']} casa errada"
            f" {c['casadas'] - c['casa_certa']}",
            flush=True,
        )
    Path(f"/app/data/saida/tab_rotulo/diag/recorte_comum{'' if PESOS == 'ger' else '_' + PESOS}.json").write_text(
        json.dumps(
            {
                "soma": {f"s{s}_{r}": dict(c) for (s, r), c in soma.items()},
                "por_video": por_video,
            },
            indent=1,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    with trava_gpu("tablatura", "0212: leitura comum, recorte antigo x alto"):
        codigo = main()
    raise SystemExit(codigo)

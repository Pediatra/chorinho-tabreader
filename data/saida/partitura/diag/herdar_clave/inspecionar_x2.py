"""Diagnostico: por recorte, tem clave, tem key, armadura do video, fifths aplicado (antes e depois)."""
import json
from pathlib import Path
from tab.partitura_omr import _tem_clave, _tem_armadura, _fifths_da_leitura, armadura_do_video
from tab.caminhos import RAIZ

base = RAIZ / "data/saida/partitura/p1/omr/audiveris"
antes = Path(RAIZ / "data/saida/partitura/diag/herdar_clave/x2_margem_herdada_antes")
indice = json.loads((RAIZ / "data/saida/partitura/p1/recortes_margem/indice.json").read_text())
execu = {r["id"]: r for r in json.loads((base / "x2_margem/execucao.json").read_text())}
ha = {r["id"]: r for r in json.loads((antes / "herdada.json").read_text())}
hd = {r["id"]: r for r in json.loads((base / "x2_margem_herdada/herdada.json").read_text())}
textos = {}
por_video = {}
for it in indice:
    r = execu[it["id"]]
    if r["ok"]:
        t = (RAIZ / r["saida"]).read_text(encoding="utf-8")
        textos[it["id"]] = t
        por_video.setdefault(it["video"], []).append(t)
arm = {v: armadura_do_video(ts) for v, ts in por_video.items()}
for it in indice:
    i = it["id"]
    t = textos.get(i)
    if t is None:
        print(i, "sem saida"); continue
    print(i, it["video"][:20], "clef", _tem_clave(t), "key", _tem_armadura(t), "fifths_leit", _fifths_da_leitura(t),
          "video", arm[it["video"]], "antes", ha[i]["fifths_aplicado"], "depois", hd[i]["fifths_aplicado"])

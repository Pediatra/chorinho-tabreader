"""2018: garante o FLAC de cada vídeo da amostra e grava a lista (vídeo -> flac)."""

import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, "/app")
from tab.audio_extrair import garantir  # noqa: E402

R = Path("/app/data/saida/audio/r2018")
videos = []
for g in sorted(glob.glob("/app/data/gold/ouro_video/*.json")):
    if g.endswith("retrato_brasileiro.json"):
        continue
    videos.append(("ouro", Path(g).stem, json.load(open(g))["video"]))
for nome in ("paolo_those_who_wait", "robert_lunn_5_beautiful_easy",
             "transcriptor_charagua", "guitarous_sakura"):
    d = json.load(open(f"/app/data/saida/audio/r2017/produtos/{nome}.json"))
    videos.append(("acordes", nome, d["video"]["arquivo"]))
lista = []
for papel, nome, video in videos:
    flac, meta = garantir("/acervo/" + video)
    lista.append({"papel": papel, "nome": nome, "video": video,
                  "flac": str(flac), "cache": meta["cache"]})
    print(papel, nome, flac.name, meta["cache"], flush=True)
(R / "lista.json").write_text(json.dumps(lista, ensure_ascii=False, indent=1))

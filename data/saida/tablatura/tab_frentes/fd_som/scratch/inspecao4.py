import json
import os
import pathlib

PRINC = pathlib.Path("/app")
indice = json.loads(
    (PRINC / "data/saida/t82/ferramenta/indice.json").read_text(encoding="utf-8")
)
videos = sorted({r["video"] for r in indice})
print("videos T8.2 distintos:", len(videos), "| telas:", len(indice))

# produtos completos (com telas) ja gravados em data/saida, por arquivo de video
achados = {v: [] for v in videos}
for raiz, _, nomes in os.walk(PRINC / "data/saida"):
    for n in nomes:
        if not n.endswith(".json") or n.endswith(".audio.json"):
            continue
        p = pathlib.Path(raiz) / n
        if p.stat().st_size > 20_000_000:
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(d, dict) or "telas" not in d or "video" not in d:
            continue
        arq = d.get("video", {}).get("arquivo") if isinstance(d.get("video"), dict) else None
        if arq in achados:
            achados[arq].append(str(p.relative_to(PRINC)))

for v in videos:
    print("-", v[:90], "| produtos:", achados[v][:3])

# cache de audio: quais videos ja tem FLAC
cache = pathlib.Path("/cache/audio")
print("cache metas:", len(list(cache.glob("*.json"))))
for m in sorted(cache.glob("*.json"))[:1]:
    print("exemplo meta:", m.read_text()[:400])

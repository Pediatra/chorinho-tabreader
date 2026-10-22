"""2021: lista dos 36 vídeos da T8.2 (tablatura) e o FLAC de cada um (lê o HD).

Grava ``lista.tsv`` (nome, vídeo, flac). Retomável: o cache de áudio pula o que já existe.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, "/app")
from tab.audio.extrair import garantir  # noqa: E402
from tab.comum.arquivos import slug  # noqa: E402

R = Path("/app/data/saida/audio/r2021")
plano = json.loads(Path("/app/data/saida/tablatura/t82/plano.json").read_text("utf-8"))
linhas, ausentes = [], []
for t in plano["telas"]:
    video = t["video"]
    nome = slug(Path(video).stem)[:60]
    if not Path("/acervo/" + video).exists():
        ausentes.append(video)
        print("AUSENTE", video, flush=True)
        continue
    flac, meta = garantir("/acervo/" + video)
    linhas.append(f"{nome}\t{video}\t{flac}")
    print(nome, meta["cache"], flush=True)
(R / "ausentes.txt").write_text("\n".join(ausentes) + "\n", encoding="utf-8")
(R / "lista.tsv").write_text("\n".join(linhas) + "\n", encoding="utf-8")

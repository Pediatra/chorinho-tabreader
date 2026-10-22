"""Linha de base: o tab/video.py do HEAD (sem tempo) sobre a arvore atual (so medicao)."""

import json
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "/app/data/saida/fase5/_exp/base")

import video_head  # noqa: E402

dados = video_head.transcrever_video(
    "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4"
)
json.dump(dados, open("/app/data/saida/fase5/base_head_atual.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1, default=str)
print("resumo:", dados["resumo"])

#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset
podman run --rm --security-opt label=disable \
  -v /var/home/gabriel/Projects/chorinho-dataset:/app \
  -v /run/media/gabriel/3014CD4714CD1130/chorinho:/acervo:ro \
  -v /run/media/gabriel/3014CD4714CD1130/chorinho_cache:/cache \
  -w /app -e PYTHONPATH=/app chorinho-audio:dev \
  python -m tab.audio_figuras --atraso data/saida/audio/a1/atraso_mvp.json \
  --video "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4" \
  --pasta data/saida/audio/a1/figuras --clipes data/saida/audio/a1/clipes
echo "figuras exit: $?"

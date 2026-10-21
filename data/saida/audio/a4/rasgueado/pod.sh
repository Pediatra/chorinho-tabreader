#!/bin/sh
# Roda um comando python dentro da imagem do áudio, a partir do host.
R=/var/home/gabriel/Projects/chorinho-dataset
exec podman run --rm --security-opt label=disable -v $R:/app -v /run/media/gabriel/3014CD4714CD1130/chorinho:/acervo:ro -v /run/media/gabriel/3014CD4714CD1130/chorinho_cache:/cache -w /app -e PYTHONPATH=/app -e RUFF_CACHE_DIR=/tmp/rc localhost/chorinho-audio:dev "$@"

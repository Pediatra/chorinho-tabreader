#!/bin/sh
# Roda um comando na imagem base chorinho:dev, com repositório, acervo (ro) e cache.
# Uso: podman_base.sh <comando...>   (CPU: CUDA_VISIBLE_DEVICES vazio)
R=/var/home/gabriel/Projects/chorinho-dataset
HD=/run/media/gabriel/3014CD4714CD1130
exec host-spawn -no-pty podman run --rm --security-opt label=disable \
  --memory 6g --memory-swap 6g --shm-size 1g \
  -v "$R":/app -v "$HD/chorinho":/acervo:ro -v "$HD/chorinho_cache":/cache \
  -w /app -e PYTHONPATH=/app -e CUDA_VISIBLE_DEVICES= \
  "${IMAGEM:-docker.io/library/chorinho:dev}" "$@"

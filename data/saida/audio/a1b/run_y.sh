#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
podman run --rm --security-opt label=disable -v /var/home/gabriel/Projects/chorinho-dataset:/app -v /run/media/gabriel/3014CD4714CD1130/chorinho:/acervo:ro -v /run/media/gabriel/3014CD4714CD1130/chorinho_cache:/cache -w /app -e PYTHONPATH=/app chorinho-audio:dev python data/saida/audio/a1b/y.py

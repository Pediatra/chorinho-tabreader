#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
D="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
mkdir -p data/saida/audio/a0/exp2
$D python /app/data/saida/audio/a0/analisa_sync.py

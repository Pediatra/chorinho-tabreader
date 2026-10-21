#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
D="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
$D sh -c 'python -V; ffmpeg -version | head -1; ffprobe -version | head -1; python -c "import numpy; print(numpy.__version__)"; ls /cache | head; ls /acervo | head -3; which ruff pytest'

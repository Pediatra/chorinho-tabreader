#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho python data/saida/audio/a1b/m4_video.py

#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho sh -c 'for f in g14 g20 g21; do ffmpeg -nostdin -v error -y -ss 2.0 -i data/saida/audio/a2/folha/folha2/$f.mp4 -frames:v 1 data/saida/audio/a2/folha/checagem_folha2/$f.png; done && echo ok'

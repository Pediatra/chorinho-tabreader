#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho sh -c 'ffmpeg -nostdin -v error -y -ss 2.0 -i data/saida/audio/a2/folha/demo/d3.mp4 -frames:v 1 data/saida/audio/a2/folha/demo/quadro_d3_t2s.png && ffmpeg -nostdin -v error -y -ss 2.0 -i data/saida/audio/a2/folha/demo/d4.mp4 -frames:v 1 data/saida/audio/a2/folha/demo/quadro_d4_t2s.png && echo ok'

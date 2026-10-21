#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
D="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
$D python data/saida/audio/a0/custo20.py --saida custo20_passada2.jsonl --resumo custo20_passada2_resumo.txt > data/saida/audio/a0/custo20_run2.log 2>&1
echo "rc=$?" >> data/saida/audio/a0/custo20_run2.log

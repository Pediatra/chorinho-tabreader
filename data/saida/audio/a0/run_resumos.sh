#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
D="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
$D python data/saida/audio/a0/custo20.py --so-resumo --saida custo20.jsonl --resumo custo20_resumo.txt > data/saida/audio/a0/resumo_p1.log 2>&1
$D python data/saida/audio/a0/custo20.py --so-resumo --saida custo20_passada2.jsonl --resumo custo20_passada2_resumo.txt > data/saida/audio/a0/resumo_p2.log 2>&1

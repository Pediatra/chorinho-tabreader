#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho sh -c 'rm -rf data/saida/audio/a2/folha/folha3 data/saida/audio/a2/folha/folha3_chave.json data/saida/audio/a2/folha/folha3_pedidos.json data/saida/audio/a2/folha/folha3_manifesto.json && echo limpo'

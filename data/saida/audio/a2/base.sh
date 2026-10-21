#!/bin/sh
# Roda um comando na imagem BASE (compose + podman). Uso: sh base.sh "comando"
cd /var/home/gabriel/Projects/chorinho-dataset
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
docker compose -f compose.yaml -f compose.podman.yaml run --rm -e RUFF_CACHE_DIR=/tmp/ruffcache chorinho sh -c "$1" 2>&1 | grep -v -E "orphan|Creating|Created|^ Container"

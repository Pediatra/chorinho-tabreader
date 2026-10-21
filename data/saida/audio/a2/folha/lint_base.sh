#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
RUN="docker compose -f compose.yaml -f compose.podman.yaml run --rm -e RUFF_CACHE_DIR=/tmp/ruffcache chorinho"
$RUN sh -c 'ruff check tab/audio_folha.py tests/test_audio_folha.py; echo RC_CHECK=$?; ruff format --check tab/audio_folha.py tests/test_audio_folha.py; echo RC_FORMAT=$?'

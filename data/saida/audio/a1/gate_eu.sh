#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
D="docker compose -f compose.yaml -f compose.podman.yaml run --rm -e RUFF_CACHE_DIR=/tmp/ruffcache chorinho"
$D sh -c 'ruff format tests/test_audio_onsets.py && ruff check . && ruff format --check . && pytest tests/ -q -m "not integration" -p no:cacheprovider 2>&1 | tail -3'

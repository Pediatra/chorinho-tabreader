#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
RUN="docker compose -f compose.yaml -f compose.podman.yaml run --rm -e RUFF_CACHE_DIR=/tmp/ruffcache chorinho"
$RUN sh -c 'echo "== ruff check ."; ruff check . ; echo RC_CHECK=$?; echo "== ruff format --check ."; ruff format --check . ; echo RC_FORMAT=$?; echo "== ruff format (meus)"; ruff format --check tab/audio_folha.py tests/test_audio_folha.py; echo RC_FORMAT_MEUS=$?; echo "== ruff check (meus)"; ruff check tab/audio_folha.py tests/test_audio_folha.py; echo RC_CHECK_MEUS=$?; pytest tests/ -q -m "not integration" -p no:cacheprovider > /tmp/pytest_gate.txt 2>&1; echo RC_PYTEST=$?; tail -4 /tmp/pytest_gate.txt'
echo FIM_GATE

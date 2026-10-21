#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
D="docker compose -f compose.yaml -f compose.podman.yaml run --rm -e RUFF_CACHE_DIR=/tmp/ruffcache chorinho"
O=data/saida/audio/a0
$D ruff format tab/audio_extrair.py tests/test_audio_extrair.py > $O/gate_format_seus.log 2>&1
echo "rc=$?" >> $O/gate_format_seus.log
$D ruff check . > $O/gate_ruff_check.log 2>&1
echo "rc=$?" >> $O/gate_ruff_check.log
$D ruff format --check . > $O/gate_ruff_format.log 2>&1
echo "rc=$?" >> $O/gate_ruff_format.log
$D pytest tests/test_audio_extrair.py -q -m "not integration" -p no:cacheprovider > $O/pytest_a0.log 2>&1
echo "rc=$?" >> $O/pytest_a0.log
$D pytest tests/ -q -m "not integration" -p no:cacheprovider > $O/pytest_tudo.log 2>&1
echo "rc=$?" >> $O/pytest_tudo.log
echo fim >> $O/gate_fim.txt

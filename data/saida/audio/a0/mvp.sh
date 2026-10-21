#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
D="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
O=data/saida/audio/a0
V="/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4"
$D python -m tab.audio_extrair "$V" --json "$O/mvp_extracao.json" > "$O/mvp_1.log" 2>&1
echo "rc=$?" >> "$O/mvp_1.log"
$D python -m tab.audio_extrair "$V" --json "$O/mvp_extracao_2.json" > "$O/mvp_2.log" 2>&1
echo "rc=$?" >> "$O/mvp_2.log"
$D sh -c "PYTHONPATH=/app python /app/data/saida/audio/a0/determinismo.py" > "$O/determinismo.log" 2>&1
echo "rc=$?" >> "$O/determinismo.log"
$D sh -c "PYTHONPATH=/app python /app/data/saida/audio/a0/erros_sync.py" > "$O/erros_sync.log" 2>&1
echo "rc=$?" >> "$O/erros_sync.log"
echo fim > "$O/mvp_fim.txt"

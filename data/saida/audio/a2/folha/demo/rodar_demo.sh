#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
LOG=data/saida/audio/a2/folha/demo/demo.log
RUN="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
: > "$LOG"
t0=$(date +%s)
$RUN python -m tab.audio_folha clipes --pedidos data/saida/audio/a2/folha/demo/pedidos.json --pasta data/saida/audio/a2/folha/demo >> "$LOG" 2>&1
echo "RC_CLIPES=$? TEMPO_S=$(( $(date +%s) - t0 ))" >> "$LOG"
$RUN python -m tab.audio_folha pagina --pasta data/saida/audio/a2/folha/demo >> "$LOG" 2>&1
echo "RC_PAGINA=$?" >> "$LOG"
echo FIM >> "$LOG"

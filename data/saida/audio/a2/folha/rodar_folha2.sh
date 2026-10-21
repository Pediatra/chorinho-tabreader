#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
LOG=data/saida/audio/a2/folha/folha2.log
: > "$LOG"
RUN="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
$RUN python data/saida/audio/a2/folha/montar_folha2.py >> "$LOG" 2>&1
echo "RC_MONTAR=$?" >> "$LOG"
$RUN python -m tab.audio_folha clipes --pedidos data/saida/audio/a2/folha/folha2_pedidos.json --pasta data/saida/audio/a2/folha/folha2 --manifesto data/saida/audio/a2/folha/folha2_manifesto.json >> "$LOG" 2>&1
echo "RC_CLIPES=$?" >> "$LOG"
$RUN python -m tab.audio_folha pagina --pasta data/saida/audio/a2/folha/folha2 --manifesto data/saida/audio/a2/folha/folha2_manifesto.json >> "$LOG" 2>&1
echo "RC_PAGINA=$?" >> "$LOG"
echo FIM >> "$LOG"

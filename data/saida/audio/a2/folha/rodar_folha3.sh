#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
LOG=data/saida/audio/a2/folha/folha3.log
: > "$LOG"
RUN="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
F=data/saida/audio/a2/folha
$RUN python -m tab.audio_folha comparar --gold data/gold/audio/folha1.json data/gold/audio/folha2.json --pedidos $F/folha1_pedidos.json $F/folha2_pedidos.json --semente 2003 --pasta $F/folha3 --chave $F/folha3_chave.json --pedidos-saida $F/folha3_pedidos.json --manifesto $F/folha3_manifesto.json >> "$LOG" 2>&1
echo "RC_COMPARAR=$?" >> "$LOG"
$RUN python -m tab.audio_folha pagina-comparacao --pasta $F/folha3 --manifesto $F/folha3_manifesto.json >> "$LOG" 2>&1
echo "RC_PAGINA=$?" >> "$LOG"
echo FIM >> "$LOG"

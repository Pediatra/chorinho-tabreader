#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
LOG=data/saida/audio/a2/folha/folha4.log
: > "$LOG"
RUN="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
F=data/saida/audio/a2/folha
L=data/saida/audio/a4/lote1
$RUN python -m tab.audio_folha rasgueado --v2 $L/alinhado_transcriptor_campanitas.json --v21 $L/alinhado_v21_transcriptor_campanitas.json --produto $L/transcriptor_campanitas.json --semente 2004 --pasta $F/folha4 --chave $F/folha4_chave.json --pedidos-saida $F/folha4_pedidos.json --manifesto $F/folha4_manifesto.json >> "$LOG" 2>&1
echo "RC_ROTULAR=$?" >> "$LOG"
$RUN python -m tab.audio_folha pagina --pasta $F/folha4 --manifesto $F/folha4_manifesto.json --aviso "Em alguns clipes a caixa marca uma batida abafada (X): a pergunta é se o clique cai junto com a batida." >> "$LOG" 2>&1
echo "RC_PAGINA=$?" >> "$LOG"
echo FIM >> "$LOG"

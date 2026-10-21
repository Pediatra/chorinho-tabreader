#!/bin/sh
# Medicao greensleeves (so mede; nao altera codigo nem git).
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
D="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
O=data/saida/fase8/medida/greensleeves
V="/acervo/pablo romé/greensleeves 💚 guía de estudio 👌 partitura + tab + pdf.mp4"
ST="$O/status.txt"
: > "$ST"
FPS_RAW=$($D sh -c 'ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 "$0"' "$V" 2>/dev/null | tail -n1 | tr -d '\r')
FPS=$(echo "$FPS_RAW" | awk -F/ '{ if (NF==2) printf "%.6f", $1/$2; else printf "%s", $1 }')
echo "fps_raw=$FPS_RAW fps=$FPS" >> "$ST"
$D python -m tab.transcrever "$V" --json "$O/run1.json" > "$O/run1.log" 2>&1
echo "transcrever_run1 rc=$?" >> "$ST"
$D python -m tab.transcrever "$V" --json "$O/run2.json" > "$O/run2.log" 2>&1
echo "transcrever_run2 rc=$?" >> "$ST"
$D python -m tab.avaliar_video --ouro data/gold/ouro_video/greensleeves_guia_de_estudio_partitura_tab_pdf.json --pred "$O/run1.json" --pre data/saida/ouro_video/greensleeves_guia_de_estudio_partitura_tab_pdf/pre.json --fps "$FPS" --json "$O/avaliar_video.json" > "$O/avaliar_video.log" 2>&1
echo "avaliar_video rc=$?" >> "$ST"
echo done >> "$ST"

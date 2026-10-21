#!/bin/sh
# Medicao south_american (so mede; nao altera codigo nem git). CPU: gpu.lock presente.
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
D="docker compose -f compose.yaml -f compose.podman.yaml run --rm -e CUDA_VISIBLE_DEVICES= chorinho"
O=data/saida/fase8/medida/south_american_v2
ST="$O/status.txt"
: > "$ST"
V=$($D sh -c 'ls -d /acervo/guitar\ dell*/south\ american\ music\ \(easy\)* | head -n1' 2>/dev/null | tail -n1 | tr -d '\r')
echo "video=$V" >> "$ST"
FPS_RAW=$($D sh -c 'ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 "$0"' "$V" 2>/dev/null | tail -n1 | tr -d '\r')
FPS=$(echo "$FPS_RAW" | awk -F/ '{ if (NF==2) printf "%.6f", $1/$2; else printf "%s", $1 }')
echo "fps_raw=$FPS_RAW fps=$FPS" >> "$ST"
$D python -m tab.transcrever "$V" --json "$O/run1.json" > "$O/run1.log" 2>&1
echo "transcrever_run1 rc=$?" >> "$ST"
$D python -m tab.avaliar_video --ouro data/gold/ouro_video/south_american_music_easy_guitar_tutorial_with_sheet_and_tab.json --pred "$O/run1.json" --pre data/saida/ouro_video/south_american_music_easy_guitar_tutorial_with_sheet_and_tab/pre.json --fps "$FPS" --json "$O/avaliar_video.json" > "$O/avaliar_video.log" 2>&1
echo "avaliar_video rc=$?" >> "$ST"
echo done >> "$ST"

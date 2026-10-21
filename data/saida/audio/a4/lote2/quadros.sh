#!/bin/sh
# Quadros do lote 2: uma tela recusada (exibicao 0 da tela 1) de cada um dos 2 videos
# com menos colunas com tempo. Recorte = painel do produto. Leitura do acervo apenas.
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
DC="docker compose -f compose.yaml -f compose.podman.yaml run --rm"
mkdir -p data/saida/audio/a4/lote2/quadros
$DC chorinho ffmpeg -loglevel error -y -ss 2.9 -i "/acervo/kenneth acoustic/believer (easy version) - imagine dragons ｜ fingerstyle guitar ｜ tab + chords + lyrics.mp4" -frames:v 1 -vf crop=1340:188:345:875 /app/data/saida/audio/a4/lote2/quadros/kenneth_acoustic_t1.png
$DC chorinho ffmpeg -loglevel error -y -ss 48.4 -i "/acervo/vvxofingerstyletab/sword art online alicization - resister - fingerstyle guitar cover + tab tutorial.mp4" -frames:v 1 -vf crop=1215:227:65:477 /app/data/saida/audio/a4/lote2/quadros/vvxofingerstyletab_sao_t1.png
echo "FIM" > data/saida/audio/a4/lote2/quadros/fim.txt

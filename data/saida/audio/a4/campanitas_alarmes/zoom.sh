#!/bin/sh
# Ampliacao 2x das metades esquerda e direita dos recortes (dentro do container).
set -e
D=/app/data/saida/audio/a4/campanitas_alarmes/quadros
for f in tela17_t101.44 tela38_t245.16 tela13_t74.91 tela30_t192.75; do
  ffmpeg -loglevel error -y -i "$D/$f.png" -vf "crop=960:iw/1:0:0,scale=1920:-1" "$D/${f}_esq.png" 2>/dev/null || true
  W=$(ffprobe -v error -show_entries stream=width -of csv=p=0 "$D/$f.png")
  H=$(ffprobe -v error -show_entries stream=height -of csv=p=0 "$D/$f.png")
  ffmpeg -loglevel error -y -i "$D/$f.png" -vf "crop=960:$H:0:0,scale=1920:-1" "$D/${f}_esq.png"
  ffmpeg -loglevel error -y -i "$D/$f.png" -vf "crop=960:$H:946:0,scale=1920:-1" "$D/${f}_dir.png"
done
ls "$D"

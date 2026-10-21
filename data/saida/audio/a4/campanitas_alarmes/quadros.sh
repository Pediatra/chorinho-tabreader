#!/bin/sh
# Recortes do painel de tablatura em instantes medios das exibicoes (dentro do container).
set -e
V="/acervo/transcriptor/inti illimani - campanitas - ernesto cavour - guitarra - partitura ⧸ tablatura..mp4"
O=/app/data/saida/audio/a4/campanitas_alarmes/quadros
mkdir -p "$O"
# tela t_mid y0 h
corte() {
  ffmpeg -loglevel error -y -ss "$2" -i "$V" -frames:v 1 -vf "crop=1906:$4:0:$3" "$O/tela$1_t$2.png"
}
corte 3 15.12 818 189
corte 38 245.16 519 239
corte 17 101.44 818 189
corte 13 74.91 818 189
corte 20 125.12 532 232
corte 34 223.75 533 231
corte 30 192.75 533 232
ls -la "$O"

#!/bin/sh
# Recortes extras das telas 5, 7, 16 e 47 (instantes medios), dentro do container.
set -e
V="/acervo/transcriptor/inti illimani - campanitas - ernesto cavour - guitarra - partitura ⧸ tablatura..mp4"
O=/app/data/saida/audio/a4/campanitas_alarmes/quadros
corte() {
  ffmpeg -loglevel error -y -ss "$2" -i "$V" -frames:v 1 -vf "crop=1906:$4:0:$3" "$O/tela$1_t$2.png"
}
corte 5 27.75 596 125
corte 7 41.59 818 189
corte 16 94.91 818 189
corte 47 298.5 519 240

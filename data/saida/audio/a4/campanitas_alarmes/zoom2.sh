#!/bin/sh
# Ampliacao de regioes em duvida: tela 13 (x 860-960, a partir do esq 2x) dentro do container.
set -e
D=/app/data/saida/audio/a4/campanitas_alarmes/quadros
ffmpeg -loglevel error -y -i "$D/tela13_t74.91_esq.png" -vf "crop=280:376:1640:0,scale=840:-1" "$D/zoom_tela13_x820.png"

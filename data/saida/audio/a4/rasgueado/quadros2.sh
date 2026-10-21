#!/bin/sh
set -e
OUT=/app/data/saida/audio/a4/rasgueado/quadros
ffmpeg -y -loglevel error -ss 146.688 -i '/acervo/transcriptor/inti illimani - campanitas - ernesto cavour - guitarra - partitura ⧸ tablatura..mp4' -frames:v 1 -vf crop=1906:450:0:300 $OUT/transcriptor_campanitas_t23.png
ffmpeg -y -loglevel error -ss 310.875 -i '/acervo/transcriptor/inti illimani - campanitas - ernesto cavour - guitarra - partitura ⧸ tablatura..mp4' -frames:v 1 -vf crop=1906:450:0:300 $OUT/transcriptor_campanitas_t49.png

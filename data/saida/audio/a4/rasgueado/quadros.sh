#!/bin/sh
set -e
OUT=/app/data/saida/audio/a4/rasgueado/quadros
ffmpeg -y -loglevel error -ss 56.938 -i '/acervo/transcriptor/inti illimani - campanitas - ernesto cavour - guitarra - partitura ⧸ tablatura..mp4' -frames:v 1 -vf crop=1906:460:0:620 $OUT/transcriptor_campanitas_t10.png
ffmpeg -y -loglevel error -ss 94.875 -i '/acervo/kimny'"'"'s guitar/[ tab ] bach - prelude (cello suite no.1, bwv1007) ｜ performed by kimny.mp4' -frames:v 1 -vf crop=1811:460:62:620 $OUT/kimny_bach_prelude_t5.png
ffmpeg -y -loglevel error -ss 156.777 -i '/acervo/shin izumi/【tab】a dream is a wish your heart makes- cinderella - fingerstyle guitar ソロギター【タブ】.mp4' -frames:v 1 -vf crop=1898:153:22:832 $OUT/shin_izumi_dream_wish_t22.png
ffmpeg -y -loglevel error -ss 183.938 -i '/acervo/paolo d'"'"'angelo/those who wait ｜ tommy emmanuel ｜ guitar tab ｜ fingerstyle tutorial.mp4' -frames:v 1 -vf crop=1836:460:84:620 $OUT/paolo_those_who_wait_t12.png
ffmpeg -y -loglevel error -ss 1.969 -i '/acervo/shin izumi/【tab】giant steps - john coltrane - fingerstyle guitar ソロギター【タブ】.mp4' -frames:v 1 -vf crop=1920:152:0:874 $OUT/shin_izumi_giant_steps_t1.png
ffmpeg -y -loglevel error -ss 15.406 -i '/acervo/shin izumi/【tab】giant steps - john coltrane - fingerstyle guitar ソロギター【タブ】.mp4' -frames:v 1 -vf crop=1920:153:0:839 $OUT/shin_izumi_giant_steps_t5.png
ffmpeg -y -loglevel error -ss 41.688 -i '/acervo/shin izumi/【tab】giant steps - john coltrane - fingerstyle guitar ソロギター【タブ】.mp4' -frames:v 1 -vf crop=1920:153:0:837 $OUT/shin_izumi_giant_steps_t13.png
ffmpeg -y -loglevel error -ss 54.938 -i '/acervo/shin izumi/【tab】giant steps - john coltrane - fingerstyle guitar ソロギター【タブ】.mp4' -frames:v 1 -vf crop=1920:153:0:839 $OUT/shin_izumi_giant_steps_t17.png

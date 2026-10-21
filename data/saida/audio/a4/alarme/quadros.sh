mkdir -p data/saida/audio/a4/alarme/quadros
ffmpeg -loglevel error -y -ss 78.97 -i "/acervo/iwaki/fly me to the moon ｜ tab.mp4" -frames:v 1 -vf crop=1669:460:125:620 data/saida/audio/a4/alarme/quadros/iwaki_fly_me_to_the_moon_t10.png
ffmpeg -loglevel error -y -ss 15.41 -i "/acervo/shin izumi/【tab】giant steps - john coltrane - fingerstyle guitar ソロギター【タブ】.mp4" -frames:v 1 -vf crop=1920:153:0:839 data/saida/audio/a4/alarme/quadros/shin_izumi_giant_steps_t5.png

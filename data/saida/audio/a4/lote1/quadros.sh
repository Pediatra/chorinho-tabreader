mkdir -p data/saida/audio/a4/lote1/quadros
ffmpeg -loglevel error -y -ss 30.88 -i "/acervo/ギタロー ⧸ guitarous/sakuraドロップス ソロギター 初心者向け タブ譜.mp4" -frames:v 1 -vf crop=1280:420:0:300 /app/data/saida/audio/a4/lote1/quadros/guitarous_sakura_t3.png
ffmpeg -loglevel error -y -ss 56.94 -i "/acervo/transcriptor/inti illimani - campanitas - ernesto cavour - guitarra - partitura ⧸ tablatura..mp4" -frames:v 1 -vf crop=1906:460:0:620 /app/data/saida/audio/a4/lote1/quadros/transcriptor_campanitas_t10.png

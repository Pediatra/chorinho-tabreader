#!/bin/sh
# roda paginar em cada vídeo do piloto (dentro do container)
while IFS= read -r v; do
  python -m tab.partitura_video paginar --video "$v"
done < data/saida/partitura/diag/piloto_videos.txt

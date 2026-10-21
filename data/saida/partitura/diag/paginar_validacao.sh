#!/bin/sh
# roda paginar nos 3 vídeos com produto, gravando em diag/paginar_validacao/<stem>
# (o produto em data/saida/partitura/video/ não é tocado); saída de paginar em stdout
while IFS="	" read -r stem v; do
  python -m tab.partitura_video paginar --video "$v" --pasta "data/saida/partitura/diag/paginar_validacao/$stem"
done < data/saida/partitura/diag/validacao_videos.txt

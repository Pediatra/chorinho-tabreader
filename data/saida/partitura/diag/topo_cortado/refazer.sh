#!/bin/sh
# paginar + ler --pasta nos vídeos do piloto cujo recorte mudou (rodada 3022)
while IFS= read -r v; do
  python -m tab.partitura_video paginar --video "$v" < /dev/null
done < data/saida/partitura/diag/topo_cortado/videos.txt
for s in agua_de_beber amazing_grace athletic_theme blackbird canon_de_pachelbel o_lafur 無料タブ譜_mela; do
  for p in data/saida/partitura/sem_produto/"$s"*/; do
    python -m tab.partitura_video ler --pasta "$p" < /dev/null
  done
done

#!/bin/sh
# Passo 4: sonda de transposição (roda no container). Saída em a4/shin/alinhado_t{N}.json
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
RUN="podman run --rm --security-opt label=disable -v /var/home/gabriel/Projects/chorinho-dataset:/app -v /run/media/gabriel/3014CD4714CD1130/chorinho:/acervo:ro -v /run/media/gabriel/3014CD4714CD1130/chorinho_cache:/cache -w /app -e PYTHONPATH=/app localhost/chorinho-audio:dev"
VIDEO="/acervo/shin izumi/【tab】room 335 - larry carlton  - fingerstyle guitar ソロギター【タブ】.mp4"
for N in -2 -1 0 1 2; do
  echo "== transposicao $N"
  $RUN python -m tab.audio_alinhar --produto data/saida/audio/a2/produtos/shin_izumi_room_335.json --video "$VIDEO" --saida "data/saida/audio/a4/shin/alinhado_t$N.json" --metodo onsets --transposicao $N
done

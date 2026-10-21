#!/bin/sh
# Regera os chorinho/audio@1 (com alarme_leitura) dos 4 pares do A5 e dos 10 do lote 1.
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
COMMIT=$(git rev-parse HEAD)
RUN="podman run --rm --security-opt label=disable -v $PWD:/app -w /app -e PYTHONPATH=/app localhost/chorinho-audio:dev"
LOG=data/saida/audio/a4/alarme/rodar.log
: > "$LOG"
A2=data/saida/audio/a2; A5=data/saida/audio/a5; L1=data/saida/audio/a4/lote1
run() { echo "== $1" >> "$LOG"; $RUN python -m tab.audio_produto --produto "$2" --alinhado "$3" --saida "$4" --commit "$COMMIT" >> "$LOG" 2>&1; echo "RC=$?" >> "$LOG"; }
run mvp data/saida/conserto_v2/mvp.json $A2/alinhado_v2_r1.json $A5/mvp.audio.json
for a in iwaki_la_vie_en_rose kimny_from_this_place shin_izumi_room_335; do
  run $a $A2/produtos/$a.json $A2/produtos/alinhado_$a.json $A5/$a.audio.json
done
for a in $(python3 -c "import json;print(' '.join(json.load(open('$L1/apelidos.json'))))"); do
  run $a $L1/$a.json $L1/alinhado_$a.json $L1/$a.audio.json
done
echo FIM >> "$LOG"

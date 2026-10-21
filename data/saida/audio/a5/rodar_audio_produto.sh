#!/bin/sh
# Rodada A5: escreve e valida o chorinho/audio@1 dos 4 pares (produto + alinhamento v2).
# Roda no host (git e podman); o Python roda na imagem chorinho-audio:dev.
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
COMMIT=$(git rev-parse HEAD)
A2=data/saida/audio/a2
A5=data/saida/audio/a5
LOG=$A5/rodar_audio_produto.log
: > "$LOG"
RUN="podman run --rm --security-opt label=disable -v $PWD:/app -w /app -e PYTHONPATH=/app localhost/chorinho-audio:dev"
run() {
  nome="$1"; produto="$2"; alinhado="$3"
  echo "== $nome" >> "$LOG"
  $RUN python -m tab.audio_produto --produto "$produto" --alinhado "$alinhado" \
    --saida "$A5/$nome.audio.json" --commit "$COMMIT" >> "$LOG" 2>&1
  echo "RC=$?" >> "$LOG"
}
run mvp data/saida/conserto_v2/mvp.json "$A2/alinhado_v2_r1.json"
run iwaki_la_vie_en_rose "$A2/produtos/iwaki_la_vie_en_rose.json" "$A2/produtos/alinhado_iwaki_la_vie_en_rose.json"
run kimny_from_this_place "$A2/produtos/kimny_from_this_place.json" "$A2/produtos/alinhado_kimny_from_this_place.json"
run shin_izumi_room_335 "$A2/produtos/shin_izumi_room_335.json" "$A2/produtos/alinhado_shin_izumi_room_335.json"
echo FIM >> "$LOG"

#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
LOG=data/saida/audio/a2/produtos/alinhar.log
: > "$LOG"
RUN="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
run() {
  apelido="$1"; video="$2"
  echo "== $apelido" >> "$LOG"
  t0=$(date +%s)
  $RUN python -m tab.audio_alinhar --produto "data/saida/audio/a2/produtos/$apelido.json" --video "$video" --saida "data/saida/audio/a2/produtos/alinhado_$apelido.json" --metodo onsets >> "$LOG" 2>&1
  echo "RC=$? TEMPO_S=$(( $(date +%s) - t0 ))" >> "$LOG"
}
run iwaki_la_vie_en_rose "/acervo/iwaki/la vie en rose - edith piaf ｜ tab.mp4"
run shin_izumi_room_335 "/acervo/shin izumi/【tab】room 335 - larry carlton  - fingerstyle guitar ソロギター【タブ】.mp4"
run kimny_from_this_place "/acervo/kimny's guitar/[ tab ] from this place - pat metheny ｜ fingerstyle guitar cover.mp4"
echo FIM >> "$LOG"

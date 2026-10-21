#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
LOG=data/saida/audio/a2/produtos/parte1.log
: > "$LOG"
RUN="docker compose -f compose.yaml -f compose.podman.yaml run --rm -e CUDA_VISIBLE_DEVICES= chorinho"
run() {
  apelido="$1"; video="$2"
  echo "== $apelido ==" >> "$LOG"
  t0=$(date +%s)
  $RUN python -m tab.video "$video" --json "data/saida/audio/a2/produtos/$apelido.json" >> "$LOG" 2>&1
  rc=$?
  t1=$(date +%s)
  echo "RC_VIDEO=$rc TEMPO_VIDEO_S=$((t1-t0))" >> "$LOG"
  t0=$(date +%s)
  $RUN python -m tab.audio_extrair "$video" >> "$LOG" 2>&1
  rc=$?
  t1=$(date +%s)
  echo "RC_AUDIO=$rc TEMPO_AUDIO_S=$((t1-t0))" >> "$LOG"
}
run iwaki_la_vie_en_rose "/acervo/iwaki/la vie en rose - edith piaf ｜ tab.mp4"
run shin_izumi_room_335 "/acervo/shin izumi/【tab】room 335 - larry carlton  - fingerstyle guitar ソロギター【タブ】.mp4"
run kimny_from_this_place "/acervo/kimny's guitar/[ tab ] from this place - pat metheny ｜ fingerstyle guitar cover.mp4"
echo FIM >> "$LOG"

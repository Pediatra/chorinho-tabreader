#!/bin/sh
# Rodada A4, lote 1: 10 videos com tablatura e SEM marcador na tela.
# Por video, em sequencia: ffprobe (metadados), tab.video (produto, CPU),
# tab.audio_extrair, tab.audio_alinhar (onsets) e tab.audio_produto (arquivo irmao,
# na imagem localhost/chorinho-audio:dev). Falha de um passo: registra e pula
# só os passos que dependem dele; segue para o proximo video.
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
L=data/saida/audio/a4/lote1
LOG=$L/lote1.log
mkdir -p "$L/logs"
: > "$LOG"
COMMIT=$(git rev-parse HEAD)
echo "COMMIT=$COMMIT" >> "$LOG"
DC="docker compose -f compose.yaml -f compose.podman.yaml run --rm"
PODMAN="podman run --rm --security-opt label=disable -v $PWD:/app -w /app -e PYTHONPATH=/app localhost/chorinho-audio:dev"

executar() {
  ap="$1"; nome="$2"; shift 2
  t0=$(date +%s)
  "$@" > "$L/logs/${ap}_${nome}.log" 2>&1
  rc=$?
  echo "[$ap] $nome RC=$rc TEMPO_S=$(( $(date +%s) - t0 ))" >> "$LOG"
  return $rc
}

rodar() {
  ap="$1"; video="$2"
  echo "== $ap  ($(date +%H:%M:%S))" >> "$LOG"
  executar "$ap" meta $DC chorinho ffprobe -v error -of json \
    -show_format -show_entries stream=codec_type,codec_name,width,height "$video"
  prod_ok=0
  if executar "$ap" produto $DC -e CUDA_VISIBLE_DEVICES= chorinho \
      python -m tab.video "$video" --json "$L/$ap.json"; then
    prod_ok=1
  fi
  audio_ok=0
  if executar "$ap" audio $DC chorinho python -m tab.audio_extrair "$video"; then
    audio_ok=1
  fi
  if [ $prod_ok = 1 ] && [ $audio_ok = 1 ]; then
    if executar "$ap" alinhar $DC chorinho python -m tab.audio_alinhar \
        --produto "$L/$ap.json" --video "$video" \
        --saida "$L/alinhado_$ap.json" --metodo onsets; then
      executar "$ap" sibling $PODMAN python -m tab.audio_produto \
        --produto "$L/$ap.json" --alinhado "$L/alinhado_$ap.json" \
        --saida "$L/$ap.audio.json" --commit "$COMMIT"
    else
      echo "[$ap] sibling PULADO (alinhar falhou)" >> "$LOG"
    fi
  else
    echo "[$ap] alinhar e sibling PULADOS (produto ou audio falhou)" >> "$LOG"
  fi
}

rodar iwaki_michelle "/acervo/iwaki/the beatles - michelle｜tab for beginners.mp4"
rodar iwaki_fly_me_to_the_moon "/acervo/iwaki/fly me to the moon ｜ tab.mp4"
rodar kimny_gunjo "/acervo/kimny's guitar/[tab] 群青（合唱曲）- 小田美樹 ｜ fingerstyle guitar cover.mp4"
rodar kimny_bach_prelude "/acervo/kimny's guitar/[ tab ] bach - prelude (cello suite no.1, bwv1007) ｜ performed by kimny.mp4"
rodar shin_izumi_giant_steps "/acervo/shin izumi/【tab】giant steps - john coltrane - fingerstyle guitar ソロギター【タブ】.mp4"
rodar transcriptor_charagua "/acervo/transcriptor/charagua - victor jara -  2＊ guitarra - partitura ⧸ tablatura..mp4"
rodar transcriptor_campanitas "/acervo/transcriptor/inti illimani - campanitas - ernesto cavour - guitarra - partitura ⧸ tablatura..mp4"
rodar guitarous_sakura "/acervo/ギタロー ⧸ guitarous/sakuraドロップス ソロギター 初心者向け タブ譜.mp4"
rodar shin_izumi_dream_wish "/acervo/shin izumi/【tab】a dream is a wish your heart makes- cinderella - fingerstyle guitar ソロギター【タブ】.mp4"
rodar paolo_those_who_wait "/acervo/paolo d'angelo/those who wait ｜ tommy emmanuel ｜ guitar tab ｜ fingerstyle tutorial.mp4"
echo "FIM" >> "$LOG"

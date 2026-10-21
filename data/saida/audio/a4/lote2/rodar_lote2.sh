#!/bin/sh
# Rodada A4, lote 2: 12 videos de canais novos (com marcador na tela).
# Por video, em sequencia: ffprobe (metadados), tab.video (produto, CPU),
# tab.audio_extrair, tab.audio_alinhar (onsets) e tab.audio_produto (arquivo irmao,
# na imagem localhost/chorinho-audio:dev). Falha de um passo: registra e pula
# só os passos que dependem dele; segue para o proximo video.
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
L=data/saida/audio/a4/lote2
LOG=$L/lote2.log
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

rodar leonardo_ramos_tiempo_de_vals "/acervo/leonardo ramos/tiempo de vals (lección nº11) 🎸 julio s. sagreras ｜｜ tutorial para guitarra clásica + tabs.mp4"
rodar robert_lunn_5_beautiful_easy "/acervo/robert lunn/5 beautiful easy guitar pieces (with sheet music & tab) - robert lunn.mp4"
rodar serge_kottelat_sungha_jung_at "/acervo/serge kottelat/sungha jung at age 12 – pirates of the caribbean ｜ guitar transcription with tab & notation.mp4"
rodar kenneth_acoustic_believer_easy_version "/acervo/kenneth acoustic/believer (easy version) - imagine dragons ｜ fingerstyle guitar ｜ tab + chords + lyrics.mp4"
rodar mr_tabs_eric_clapton_tears "/acervo/mr. tabs/eric clapton - tears in heaven - guitar tab ｜ lesson ｜ cover ｜ tutorial.mp4"
rodar guitar_dell_arte_summertime_g_gershwin "/acervo/guitar dell ́arte/summertime (g. gershwin), guitar lesson, sheet and tab.mp4"
rodar sky_guitar_exercise_3_chromatic "/acervo/sky guitar/exercise #3 (chromatic scale) tab.mp4"
rodar tv_on_guitar_mario_wonder_overworld "/acervo/tv on guitar/mario wonder overworld theme tab & std notation ｜ tvonguitar.mp4"
rodar lonelypicker_its_a_heartache "/acervo/lonelypicker/it’s a heartache – bonnie tyler - easy fingerstyle guitar tutorial tab.mp4"
rodar violaodecria_bela_rosa_mc "/acervo/violaodecria/bela rosa - mc livinho (dj perera) kondzilla #violao #auladeviolao #t... [7375869523666291973].mp4"
rodar yunus_guitarist_first_love_nikka "/acervo/yunus guitarist/first love - nikka costa - fingerstyle guitar tutorial tab + chords + lyrics.mp4"
rodar vvxofingerstyletab_sword_art_online "/acervo/vvxofingerstyletab/sword art online alicization - resister - fingerstyle guitar cover + tab tutorial.mp4"
echo "FIM" >> "$LOG"

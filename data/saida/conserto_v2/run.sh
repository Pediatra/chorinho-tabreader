#!/bin/sh
# Rodada de medição do conserto v2 (só mede; não altera código nem git).
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
D="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
O=data/saida/conserto_v2
mkdir -p "$O/piloto"
ST="$O/status.txt"
: > "$ST"

FPS_RAW=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 "/run/media/gabriel/3014CD4714CD1130/chorinho/sky guitar/retrato brasileiro - tab & lesson.mp4")
FPS=$(echo "$FPS_RAW" | awk -F/ '{ if (NF==2) printf "%.6f", $1/$2; else printf "%s", $1 }')
echo "fps_raw=$FPS_RAW fps=$FPS" >> "$ST"

$D python -m tab.transcrever "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4" --json "$O/mvp.json" > "$O/mvp.log" 2>&1
echo "mvp_transcrever rc=$?" >> "$ST"

$D python -m tab.avaliar_video --ouro data/gold/ouro_video/retrato_brasileiro_v2.json --pred "$O/mvp.json" --fps "$FPS" --json "$O/avaliar_video.json" > "$O/avaliar_video.log" 2>&1
echo "avaliar_video rc=$?" >> "$ST"

for s in 1 2 3; do
  $D python -m tab.avaliar --modelo "artefatos/oficial_$s/glifo_sint.pt" > "$O/oficial_$s.log" 2>&1
  echo "oficial_$s rc=$?" >> "$ST"
done

$D sh -c 'ruff check .' > "$O/gate_ruff_check.log" 2>&1
echo "ruff_check rc=$?" >> "$ST"
$D sh -c 'ruff format --check .' > "$O/gate_ruff_format.log" 2>&1
echo "ruff_format rc=$?" >> "$ST"
$D sh -c 'pytest tests/ -q -m "not integration" -p no:cacheprovider' > "$O/gate_pytest.log" 2>&1
echo "pytest rc=$?" >> "$ST"

rm -rf "$O/piloto"; mkdir -p "$O/piloto"
$D python -m tab.censo --piloto 3 --so-cache --saida "$O/piloto/censo.jsonl" --folhas "$O/piloto" > "$O/piloto.log" 2>&1
RC=$?
echo "piloto_so_cache rc=$RC" >> "$ST"
if [ $RC -ne 0 ] || [ ! -s "$O/piloto/censo.jsonl" ]; then
  rm -rf "$O/piloto"; mkdir -p "$O/piloto"
  $D python -m tab.censo --piloto 3 --cache --saida "$O/piloto/censo.jsonl" --folhas "$O/piloto" > "$O/piloto.log" 2>&1
  echo "piloto_cache rc=$?" >> "$ST"
fi
echo FIM >> "$ST"

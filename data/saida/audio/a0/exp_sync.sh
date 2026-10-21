#!/bin/sh
# Experimento exploratorio: mp4 sintetico com clique de audio em t=1.0 s (tempo da fonte).
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
D="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
O=data/saida/audio/a0/exp
mkdir -p $O
GEN='aevalsrc=0.8*sin(2*PI*2000*t)*between(t\,1.0\,1.005):s=44100:d=3'
for OFF in 0 0.5; do
  for CODEC in aac pcm; do
    if [ $CODEC = aac ]; then CA="-c:a aac -b:a 128k"; EXT=mp4; else CA="-c:a pcm_s16le"; EXT=mov; fi
    $D sh -c "ffmpeg -nostdin -v error -y -f lavfi -i testsrc=size=320x240:rate=25 -itsoffset $OFF -f lavfi -i '$GEN' -t 3 -map 0:v -map 1:a -c:v libx264 -pix_fmt yuv420p $CA /tmp/sync_${OFF}_${CODEC}.$EXT && cp /tmp/sync_${OFF}_${CODEC}.$EXT /app/$O/ && ffprobe -v error -show_entries stream=index,codec_name,start_time,sample_rate -show_entries format=start_time,duration -of json /app/$O/sync_${OFF}_${CODEC}.$EXT > /app/$O/probe_${OFF}_${CODEC}.json && ffprobe -v error -select_streams a:0 -show_entries packet=pts_time -read_intervals '%+#2' -of csv=p=0 /app/$O/sync_${OFF}_${CODEC}.$EXT > /app/$O/pkta_${OFF}_${CODEC}.txt && ffprobe -v error -select_streams v:0 -show_entries packet=pts_time -read_intervals '%+#2' -of csv=p=0 /app/$O/sync_${OFF}_${CODEC}.$EXT > /app/$O/pktv_${OFF}_${CODEC}.txt && ffmpeg -nostdin -v error -y -i /app/$O/sync_${OFF}_${CODEC}.$EXT -map 0:a:0 -ac 1 -ar 22050 -f s16le - | python -c 'import sys,numpy as np; a=np.frombuffer(sys.stdin.buffer.read(),dtype=np.int16).astype(float); k=np.argmax(np.abs(a)); print(\"pico_idx\",k,\"pico_s\",k/22050,\"n\",len(a))' > /app/$O/pico_${OFF}_${CODEC}.txt"
  done
done
echo done

#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
D="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
$D sh -c "ffmpeg -nostdin -v error -f lavfi -i 'aevalsrc=0.8*sin(2*PI*2000*t)*between(t\,1.0\,1.005):s=44100:d=3' -ac 1 -f s16le -ar 44100 - | python -c 'import sys,numpy as np; a=np.frombuffer(sys.stdin.buffer.read(),dtype=np.int16).astype(float); k=np.argmax(np.abs(a)); print(\"44100 direto: pico_idx\",k,\"s\",k/44100); w=np.nonzero(np.abs(a)>1000)[0]; print(\"primeira amostra >1000:\",w[0],w[0]/44100, \"ultima:\", w[-1]/44100)'"
$D sh -c "ffmpeg -nostdin -v error -f lavfi -i 'aevalsrc=0.8*sin(2*PI*2000*t)*between(t\,1.0\,1.005):s=44100:d=3' -ac 1 -ar 22050 -f s16le - | python -c 'import sys,numpy as np; a=np.frombuffer(sys.stdin.buffer.read(),dtype=np.int16).astype(float); w=np.nonzero(np.abs(a)>1000)[0]; print(\"22050 reamostrado: primeira >1000:\",w[0],w[0]/22050, \"ultima:\", w[-1]/22050)'"

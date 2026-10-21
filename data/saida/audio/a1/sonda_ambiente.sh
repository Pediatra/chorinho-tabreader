#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset
podman images | head -20
echo ---
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
docker compose -f compose.yaml -f compose.podman.yaml config >/dev/null 2>&1 && echo compose_ok
echo ---
grep -l "retrato" /run/media/gabriel/3014CD4714CD1130/chorinho_cache/audio/*.json 2>/dev/null | head -3
for f in /run/media/gabriel/3014CD4714CD1130/chorinho_cache/audio/*.json; do python3 -c "import json,sys; m=json.load(open(sys.argv[1])); print(m['caminho'], m['taxa'], m['t_amostra0'], m['origem_t_amostra0'], m['n_amostras'])" "$f"; done 2>/dev/null | grep -i retrato

#!/bin/sh
# 6 censos em paralelo, um por grupo de canais (grupos.json); cada um retomável.
cd /var/home/gabriel/Projects/chorinho-dataset
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
for i in 0 1 2 3 4 5; do
  if [ $i = 0 ]; then saida=data/saida/censo/v2/censo_cache_v2.jsonl; else saida=data/saida/censo/v2/par_$i.jsonl; fi
  canais=$(python3 -c "import json;print(' '.join(\"'\"+c.replace(\"'\",\"'\\\\''\")+\"'\" for c in json.load(open('data/saida/censo/v2/grupos.json'))[$i]))")
  eval "docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho python -m tab.censo --cache --janelas-por-canal 30 --canais $canais --saida $saida" > data/saida/censo/v2/par_$i.log 2>&1 &
done
wait
echo FIM_PARALELO

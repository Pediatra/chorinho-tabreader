#!/bin/sh
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
cd /var/home/gabriel/Projects/chorinho-dataset
for par in "base:" "ger:_ger"; do
  nome=${par%%:*}; suf=${par#*:}
  docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho python /app/data/saida/fase8/ger/regua_ger.py /app/data/saida/fase8/ger/$nome $suf > data/saida/fase8/ger/$nome.log 2>&1
done
rm -f data/saida/gpu.lock

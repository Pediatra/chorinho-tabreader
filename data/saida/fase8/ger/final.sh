#!/bin/sh
# Modelo do produto com o gerador novo: dobra 0 (os 8 ouros no treino), semente 1 declarada antes.
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
P=/var/home/gabriel/Projects/chorinho-dataset
cd $P
echo "tablatura, $(date '+%F %T'), ~20 min (modelo final com gerador novo)" > data/saida/gpu.lock
docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho python /app/data/saida/n4/treinar_ft.py --dobra 0 --passos 3000 --semente 1 --nome _s1_ger > data/saida/fase8/ger/treino_final_s1_ger.log 2>&1
rm -f data/saida/gpu.lock

#!/bin/sh
# 0214, emenda de 2026-10-23: o dono revisou os gabaritos (casas e ataque). O cache real do
# treino é refeito a partir deles: ouros, T8.2, T8.3, o recorte alto e a T8.4.
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
cd /var/home/gabriel/Projects/chorinho-dataset
L=data/saida/tablatura/tab_rotulo/r4h
CP="docker compose -f compose.yaml -f compose.podman.yaml run --rm --no-deps -e CUDA_VISIBLE_DEVICES= chorinho"
for s in extrair extrair_t82 extrair_t83 cache_alto extrair_t84; do
  $CP python /app/data/saida/tablatura/n4/$s.py > $L/cache_$s.log 2>&1 || { echo "FALHOU $s"; exit 1; }
  echo "ok $s: $(grep -v 'Container\|orphan' $L/cache_$s.log | tail -3 | tr '\n' ' ')"
done

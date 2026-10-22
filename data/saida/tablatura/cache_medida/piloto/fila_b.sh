#!/bin/sh
# fila B: cache WebP sem perda, frio e quente (regra 9)
cd /var/home/gabriel/Projects/chorinho-dataset
R="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho python -m tab.censo --piloto 3"
D=data/saida/cache_medida/piloto
$R --cache --formato webp --saida $D/webp_frio.jsonl
$R --so-cache --formato webp --saida $D/webp_quente.jsonl
echo FILA_B_FIM

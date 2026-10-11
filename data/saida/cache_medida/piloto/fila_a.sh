#!/bin/sh
# fila A: leitura direta (sem cache), depois cache JPEG frio e quente (regra 9)
cd /var/home/gabriel/Projects/chorinho-dataset
R="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho python -m tab.censo --piloto 3"
D=data/saida/cache_medida/piloto
$R --saida $D/direto.jsonl
$R --cache --formato jpeg95 --saida $D/jpeg_frio.jsonl
$R --so-cache --formato jpeg95 --saida $D/jpeg_quente.jsonl
echo FILA_A_FIM

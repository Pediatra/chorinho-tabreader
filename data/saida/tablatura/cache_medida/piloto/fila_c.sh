#!/bin/sh
# fila C: regra 9 com PNG (cache no HD externo /cache): frio e quente, mesmo piloto 3/canal
cd /var/home/gabriel/Projects/chorinho-dataset
R="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho python -m tab.censo --piloto 3"
D=data/saida/cache_medida/piloto
$R --cache --saida $D/png_frio.jsonl
$R --so-cache --saida $D/png_quente.jsonl
echo FILA_C_FIM

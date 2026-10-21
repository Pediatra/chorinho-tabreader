#!/bin/sh
# Ajuste fino das dobras 2, 3 e 4 com o gerador do worktree haiku-gerador (pausa entre
# cordas, fórmula e TAB cinza), depois a régua nos 6 vídeos dessas dobras.
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
P=/var/home/gabriel/Projects/chorinho-dataset
W=/var/home/gabriel/Projects/chorinho-wt-gerador
echo "tablatura, $(date '+%F %T'), ~60 min (ajuste fino com gerador novo, dobras 2-4)" > $P/data/saida/gpu.lock
cd $W
C="docker compose -f compose.yaml -f compose.podman.yaml run --rm -v $P/artefatos:/app/artefatos -v $P/data/saida/n4:/app/data/saida/n4 chorinho"
for d in 2 3 4; do
  $C python /app/data/saida/n4/treinar_ft.py --dobra $d --passos 3000 --nome _ger > $P/data/saida/fase8/ger_treino_d$d.log 2>&1
done
rm -f $P/data/saida/gpu.lock
touch $P/data/saida/fase8/ger_treino.feito

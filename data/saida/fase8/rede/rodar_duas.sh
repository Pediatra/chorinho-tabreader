#!/bin/sh
# Remede os 8 ouros: A = principal (linhas com fundo claro); B = worktree gym (A + barra grossa).
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
P=/var/home/gabriel/Projects/chorinho-dataset
W=/var/home/gabriel/Projects/chorinho-wt-gym
echo "tablatura, $(date '+%F %T'), ~80 min (fase 8: régua linhas fundo claro + barra grossa)" > $P/data/saida/gpu.lock
C="docker compose -f compose.yaml -f compose.podman.yaml run --rm -v $P/artefatos:/app/artefatos:ro chorinho"
(cd $P && $C python data/saida/fase8/rede/regua.py /app/data/saida/fase8/linhas2 > data/saida/fase8/linhas2.log 2>&1) &
(cd $W && $C python data/saida/fase8/rede/regua.py /app/data/saida/fase8/grossa > $P/data/saida/fase8/grossa.log 2>&1) &
wait
(cd $P && for s in 1 2 3; do $C python -m tab.avaliar --modelo /app/artefatos/oficial_$s/glifo_sint.pt 2>&1 | grep RESULTADO; done > data/saida/fase8/linhas2_avaliar.txt)
rm -f $P/data/saida/gpu.lock

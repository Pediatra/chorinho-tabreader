#!/bin/sh
# Sementes 2 e 3, dobras 2-4: gerador antigo (main) e novo (worktree haiku-gerador); depois a régua.
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
P=/var/home/gabriel/Projects/chorinho-dataset
W=/var/home/gabriel/Projects/chorinho-wt-gerador
echo "tablatura, $(date '+%F %T'), ~3h30 (sementes 2-3, gerador antigo x novo, dobras 2-4)" > $P/data/saida/gpu.lock
CP="docker compose -f compose.yaml -f compose.podman.yaml run --rm"
CW="$CP -v $P/artefatos:/app/artefatos -v $P/data/saida/n4:/app/data/saida/n4"
for s in 2 3; do
  for d in 2 3 4; do
    cd $P && $CP chorinho python /app/data/saida/n4/treinar_ft.py --dobra $d --passos 3000 --semente $s --nome _s$s > $P/data/saida/fase8/ger/treino_base_d${d}_s$s.log 2>&1
    cd $W && $CW chorinho python /app/data/saida/n4/treinar_ft.py --dobra $d --passos 3000 --semente $s --nome _ger_s$s > $P/data/saida/fase8/ger/treino_ger_d${d}_s$s.log 2>&1
  done
done
cd $P
for s in 2 3; do
  for par in "base_s$s:_s$s" "ger_s$s:_ger_s$s"; do
    nome=${par%%:*}; suf=${par#*:}
    $CP chorinho python /app/data/saida/fase8/ger/regua_ger.py /app/data/saida/fase8/ger/$nome $suf > data/saida/fase8/ger/$nome.log 2>&1
  done
done
rm -f $P/data/saida/gpu.lock

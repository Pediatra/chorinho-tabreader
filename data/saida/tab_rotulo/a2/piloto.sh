#!/bin/sh
# 0206 piloto: dobra 0, semente 1, --ataque --arco (partida v3_s1), 3000 passos.
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
cd /var/home/gabriel/Projects/chorinho-dataset
L=data/saida/tab_rotulo/a2
CP="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
while [ -f data/saida/gpu.lock ] && ! grep -q "^tablatura" data/saida/gpu.lock; do sleep 120; done
echo "tablatura, $(date '+%F %T'), ~30 min (0206 piloto do arco)" > data/saida/gpu.lock
$CP python /app/data/saida/n4/treinar_ft.py --passos 3000 --dobra 0 --semente 1 --ataque --arco --nome _arcop_s1 > $L/treino_arcop_d0_s1.log 2>&1 || { echo FALHOU; rm -f data/saida/gpu.lock; exit 1; }
grep "^passo 3000\|^gravado" $L/treino_arcop_d0_s1.log
rm -f data/saida/gpu.lock
echo fim

#!/bin/sh
# R4f (rodada 0209): metade da T8.3 no ajuste fino, teste na outra metade. Dobra 0, 3 sementes.
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
P=/var/home/gabriel/Projects/chorinho-dataset
cd $P
L=data/saida/tab_rotulo/r4f
CP="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
T="python /app/data/saida/n4/treinar_ft.py --passos 3000"
while [ -f data/saida/gpu.lock ] && ! grep -q "^tablatura" data/saida/gpu.lock; do
  echo "$(date '+%T') espera trava: $(cat data/saida/gpu.lock)"; sleep 120; done
livre() { nvidia-smi --query-gpu=memory.total,memory.used --format=csv,noheader,nounits | awk -F', ' '{print $1-$2}'; }
espera_memoria() { while [ "$(livre)" -lt 3000 ]; do echo "$(date '+%T') espera memoria: $(livre) MiB livres"; sleep 120; done; }
echo "tablatura, $(date '+%F %T'), ~2 h (R4f: 6 treinos + medida)" > data/saida/gpu.lock
falha() { echo "FALHOU $1 (ver $L/$1.log)"; rm -f data/saida/gpu.lock; exit 1; }
for s in 1 2 3; do for h in a b; do
  n=treino_atqm${h}_s$s
  if [ -f artefatos/detector_tab_final_atqm${h}_s$s/modelo.pt ]; then echo "ja existe $n"; continue; fi
  espera_memoria
  $CP $T --dobra 0 --semente $s --ataque --t82 --t83-metade $h --nome _atqm${h}_s$s > $L/$n.log 2>&1 || falha $n
  grep -q "^gravado" $L/$n.log || falha $n
  echo "$(date '+%T') ok $n | $(grep '^passo 3000' $L/$n.log)"
done; done
$CP env PYTHONPATH=/app python /app/data/saida/tab_rotulo/r4f/medir_metade.py > $L/medida_metade.log 2>&1 || falha medida_metade
cat $L/medida_metade.log | grep "sim falso"
rm -f data/saida/gpu.lock
echo fim

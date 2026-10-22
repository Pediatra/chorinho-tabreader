#!/bin/sh
# Modelo final do produto: ajuste fino com os 8 gabaritos, sementes 1-3. Lock próprio.
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
N4=data/saida/n4
dk() {
  host-spawn -no-pty -cwd /var/home/gabriel/Projects/chorinho-dataset sh -c "export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock; docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho $*"
}
echo "tablatura, $(date '+%F %T'), ~45 min (detector final s1-s3)" > data/saida/gpu.lock
trap 'rm -f data/saida/gpu.lock' EXIT
for s in 1 2 3; do
  echo "== treino final semente $s $(date +%T)"
  dk python /app/data/saida/n4/treinar_ft.py --dobra 0 --passos 3000 --semente $s --nome _s$s 2>&1 | grep -v "orphan\|Container" > $N4/log_treino_final_s$s.txt
  echo "   fim $(date +%T)"
done
echo "== fim $(date +%T)" 
touch $N4/final.feito

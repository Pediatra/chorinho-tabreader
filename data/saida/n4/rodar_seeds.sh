#!/bin/sh
# n4 seguimento: sementes 2 e 3 da dobra 1, depois avaliação das três. Lock próprio.
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
N4=data/saida/n4
dk() {
  host-spawn -no-pty -cwd /var/home/gabriel/Projects/chorinho-dataset sh -c "export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock; docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho $*"
}
trap 'rm -f data/saida/gpu.lock' EXIT
for s in 2 3; do
  echo "== treino dobra 1 semente $s $(date +%T)"
  dk python /app/data/saida/n4/treinar_ft.py --dobra 1 --passos 3000 --semente $s --nome _s$s 2>&1 | grep -v "orphan\|Container" > $N4/log_treino_d1_s$s.txt
  echo "   fim $(date +%T)"
done
echo "== avaliacao sementes $(date +%T)"
dk python /app/data/saida/n4/avaliar_seeds.py 2>&1 | grep -v "orphan\|Container" > $N4/log_avaliacao_seeds.txt
echo "== fim $(date +%T)"

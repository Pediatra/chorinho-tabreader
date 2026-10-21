#!/bin/sh
# n4: 4 dobras de ajuste fino + avaliação + sintético. Roda no HOST (nohup).
# O lock data/saida/gpu.lock é criado antes e removido ao final (só este pipeline).
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
N4=data/saida/n4
dk() {
  host-spawn -no-pty -cwd /var/home/gabriel/Projects/chorinho-dataset sh -c "export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock; docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho $*"
}
trap 'rm -f data/saida/gpu.lock' EXIT
for d in 1 2 3 4; do
  echo "== treino dobra $d $(date +%T)"
  dk python /app/data/saida/n4/treinar_ft.py --dobra $d --passos 3000 2>&1 | grep -v "orphan\|Container" > $N4/log_treino_d$d.txt
  echo "   fim $(date +%T) status=$?"
done
echo "== avaliacao $(date +%T)"
dk python /app/data/saida/n4/avaliar_n4.py 2>&1 | grep -v "orphan\|Container" > $N4/log_avaliacao.txt
echo "== sintetico $(date +%T)"
dk python -m tab.detector_tab avaliar-sintetico --modelo /app/artefatos/detector_tab_v3_s1/modelo.pt 2>/dev/null > $N4/sint_v3_s1.json
for d in 1 2 3 4; do
  dk python -m tab.detector_tab avaliar-sintetico --modelo /app/artefatos/detector_tab_v3ft_d$d/modelo.pt 2>/dev/null > $N4/sint_ft_d$d.json
done
echo "== fim $(date +%T)"

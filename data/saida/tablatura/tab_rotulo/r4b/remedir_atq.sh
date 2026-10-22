#!/bin/sh
# R4b: remede _atq e _atqg (3 sementes) com o gabarito corrigido (2026-10-18).
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
cd /var/home/gabriel/Projects/chorinho-dataset
CP="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
[ -f data/saida/gpu.lock ] && { echo "gpu.lock ocupado: $(cat data/saida/gpu.lock)"; exit 1; }
echo "tablatura, $(date '+%F %T'), ~30 min (remedir _atq _atqg)" > data/saida/gpu.lock
for v in atq atqg; do for s in 1 2 3; do
  $CP python -m tab.ataque_r4 medir --versao $v --semente $s > data/saida/tab_rotulo/r4a/medida_${v}_s$s.log 2>&1 || { echo FALHOU $s; rm -f data/saida/gpu.lock; exit 1; }
  echo "ok $v s$s"
done; done
rm -f data/saida/gpu.lock
echo fim

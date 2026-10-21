#!/bin/sh
# 0211 fase 1: _atqt e _atqe com o recorte alto, ouros (dobra fora) e T8.2, 3 sementes.
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
cd /var/home/gabriel/Projects/chorinho-dataset
L=data/saida/tab_rotulo/r4g
CP="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
while [ -f data/saida/gpu.lock ] && ! grep -q "^tablatura" data/saida/gpu.lock; do sleep 120; done
echo "tablatura, $(date '+%F %T'), ~30 min (0211 fase 1: medidas)" > data/saida/gpu.lock
for v in atqt atqe; do for s in 1 2 3; do
  $CP python -m tab.ataque_r4 medir --versao $v --semente $s --recorte alto > $L/medida_${v}_s${s}_alto.log 2>&1 || { echo "FALHOU $v $s"; rm -f data/saida/gpu.lock; exit 1; }
  echo "$(date '+%T') ok $v s$s"
done; done
rm -f data/saida/gpu.lock
echo fim

#!/bin/sh
# 0205: remede _atqg e _atqc (3 sementes) com os limiares baixos da faixa "não sei".
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
cd /var/home/gabriel/Projects/chorinho-dataset
CP="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
while [ -f data/saida/gpu.lock ] && ! grep -q "^tablatura" data/saida/gpu.lock; do sleep 120; done
echo "tablatura, $(date '+%F %T'), ~30 min (0205: medidas nao_sei)" > data/saida/gpu.lock
for v in atqg atqc; do for s in 1 2 3; do
  $CP python -m tab.ataque_r4 medir --versao $v --semente $s > data/saida/tab_rotulo/r4a/medida_${v}_s$s.log 2>&1 || { echo FALHOU $v $s; rm -f data/saida/gpu.lock; exit 1; }
  echo "ok $v s$s"
done; done
rm -f data/saida/gpu.lock
echo fim

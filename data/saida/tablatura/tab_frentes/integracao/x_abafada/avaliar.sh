#!/bin/sh
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
P=/var/home/gabriel/Projects/chorinho-dataset
D=data/saida/tab_frentes/integracao/x_abafada
cd $P
echo "tablatura, $(date '+%F %T'), ~1h30 (régua do conserto do X)" > data/saida/gpu.lock
trap 'rm -f $P/data/saida/gpu.lock' EXIT
CP="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
$CP python /app/$D/t82_comparar.py > $D/t82.log 2>&1
for suf in _gerx _gerx_s2 _gerx_s3; do
  $CP python /app/$D/regua_x.py /app/$D/regua$suf $suf > $D/regua$suf.log 2>&1
done
touch $D/avaliar.feito

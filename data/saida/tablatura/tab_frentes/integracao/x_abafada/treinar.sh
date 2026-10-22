#!/bin/sh
# Conserto do X: ajuste fino com --ignorar-x. Dobras 1-3 x sementes 1-3 e o final s1.
# A dobra 4 não muda (sem EOB e Room 335 no treino, nenhuma região de X): fica a _ger.
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
P=/var/home/gabriel/Projects/chorinho-dataset
D=$P/data/saida/tab_frentes/integracao/x_abafada
cd $P
echo "tablatura, $(date '+%F %T'), ~2h30 (conserto do X: 10 ajustes finos)" > data/saida/gpu.lock
trap 'rm -f $P/data/saida/gpu.lock' EXIT
CP="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
T="python /app/data/saida/n4/treinar_ft.py --passos 3000 --ignorar-x"
echo "== final s1 $(date +%T)"
$CP $T --dobra 0 --semente 1 --nome _s1_gerx > $D/treino_final_s1.log 2>&1
for s in 1 2 3; do
  suf=_gerx; [ $s -gt 1 ] && suf=_gerx_s$s
  for d in 1 2 3; do
    echo "== dobra $d semente $s $(date +%T)"
    $CP $T --dobra $d --semente $s --nome $suf > $D/treino_d${d}_s$s.log 2>&1
  done
done
echo "== fim $(date +%T)"
touch $D/treino.feito

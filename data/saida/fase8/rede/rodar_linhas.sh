#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
dk() {
  host-spawn -no-pty -cwd /var/home/gabriel/Projects/chorinho-dataset sh -c "export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock; docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho $*"
}
echo "tablatura, $(date '+%F %T'), ~70 min (fase 8: régua com linhas por contraste local)" > data/saida/gpu.lock
trap 'rm -f data/saida/gpu.lock' EXIT
dk python /app/data/saida/fase8/rede/regua.py /app/data/saida/fase8/linhas > data/saida/fase8/linhas_log.txt 2>&1
for s in 1 2 3; do dk python -m tab.avaliar --modelo /app/artefatos/oficial_$s/glifo_sint.pt 2>&1 | grep RESULTADO; done > data/saida/fase8/linhas_avaliar.txt 2>&1
touch data/saida/fase8/linhas.feito

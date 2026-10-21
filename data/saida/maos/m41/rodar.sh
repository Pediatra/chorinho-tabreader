#!/bin/bash
# Rodada 1041: teste curto, 6 treinos, escolha com piso, critério 3 e previsão da 1039.
cd /var/home/gabriel/Projects/chorinho-dataset
LOG=data/saida/maos/m41/logs
mkdir -p "$LOG"
COMMIT=$(git rev-parse --short HEAD)
rodar() {
  local nome=$1; shift
  echo "$(date '+%F %T') início $nome" >> "$LOG/etapas.txt"
  podman run --rm --shm-size=2g --security-opt label=disable --device nvidia.com/gpu=all \
    -v "$PWD":/app -w /app -e PYTHONPATH=/app -e CHORINHO_COMMIT="$COMMIT" \
    localhost/chorinho-maos:dev python -m tab.maos_braco_retreino_capo3 "$@" > "$LOG/$nome.log" 2>&1
  local codigo=$?
  echo "$(date '+%F %T') fim $nome código $codigo" >> "$LOG/etapas.txt"
  return $codigo
}
rodar smoke smoke || exit 1
for s in 1 2 3; do rodar l5_s$s treinar --estagio l4 --semente $s; done
for s in 1 2 3; do rodar a7_s$s treinar --estagio a6 --semente $s; done
rodar escolher escolher && rodar medir_dev medir-dev && rodar prever_prova prever-prova

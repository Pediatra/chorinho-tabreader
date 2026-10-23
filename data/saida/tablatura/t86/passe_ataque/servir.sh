#!/bin/sh
# T8.6, 2º passe do dono (modo ataque), só no PC do dono: http://127.0.0.1:8128/
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
cd /var/home/gabriel/Projects/chorinho-dataset
T=data/saida/tablatura/t86/passe_ataque
docker compose -f compose.yaml -f compose.podman.yaml run --rm --no-deps -e CUDA_VISIBLE_DEVICES= -p 127.0.0.1:8128:8128 chorinho \
  python -m tab.tablatura.ouro.ouro_video servir --pasta $T/ferramenta --ouro $T/conferencia_t86_servida.json \
  --ataque data/saida/tablatura/tab_rotulo/r2/conferir_t86/ataque_t86.json --porta 8128 --host 0.0.0.0

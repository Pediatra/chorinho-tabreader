#!/bin/sh
# T8.6, 1º passe do dono (casas e regiões de técnica), só no PC do dono: http://127.0.0.1:8127/
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
cd /var/home/gabriel/Projects/chorinho-dataset
T=data/saida/tablatura/t86
docker compose -f compose.yaml -f compose.podman.yaml run --rm --no-deps -e CUDA_VISIBLE_DEVICES= -p 127.0.0.1:8127:8127 chorinho \
  python -m tab.tablatura.ouro.ouro_video servir --pasta $T/ferramenta --ouro $T/ferramenta/conferencia_t86.json --porta 8127 --host 0.0.0.0

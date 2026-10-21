#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho python -c "
import sys
import tab.audio_folha
print('torch carregado:', 'torch' in sys.modules, '| matplotlib:', 'matplotlib' in sys.modules)
"

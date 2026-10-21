#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho python -c "
import tab.audio_folha as af
import tests.test_audio_folha
print('import ok', len(af.D_MS), af.GANHO_MUSICA)
"

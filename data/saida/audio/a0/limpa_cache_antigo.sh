#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
D="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
$D sh -c "rm -f /cache/audio/ba866b765043431d1ca098a8.flac /cache/audio/ba866b765043431d1ca098a8.json; ls -la /cache/audio"

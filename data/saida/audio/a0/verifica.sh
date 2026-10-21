#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
D="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
$D sh -c "ls /cache/audio | wc -l; du -sh /cache/audio; ls -la /cache/audio | grep -c tmp; ls /acervo | head -3"

#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
D="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
$D python -c "
import numpy as np
print('float', type(round(1.5*22050.0)), type(round(np.float64(1.5)*22050.0)), type(round(np.float64(3.0))))
print('np.float64 arg', type(round(np.float64(0.1+0.4)*np.int64(22050))))
"

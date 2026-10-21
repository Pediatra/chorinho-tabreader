#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho python -c "
import cv2
from tab.leitor import quadro_em
V = '/acervo/shin izumi/【tab】room 335 - larry carlton  - fingerstyle guitar ソロギター【タブ】.mp4'
for nome, t in [('ex08_t29', 29.9), ('ex20_t73', 73.6), ('ex31_t115', 115.8), ('ex42_t158', 158.0)]:
    q = quadro_em(V, t)
    cv2.imwrite(f'data/saida/audio/a2/produtos/shin_quadros/{nome}.png', q)
    print(nome, None if q is None else q.shape)
"

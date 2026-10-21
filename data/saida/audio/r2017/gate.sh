#!/bin/sh
# Gate do projeto na imagem base; código de saída = o do primeiro passo que falhar.
D=/var/home/gabriel/Projects/chorinho-dataset/data/saida/audio/r2017
$D/podman_base.sh ruff check --no-cache . || exit 1
$D/podman_base.sh ruff format --no-cache --check . || exit 2
$D/podman_base.sh pytest tests/ -q -p no:cacheprovider || exit 3

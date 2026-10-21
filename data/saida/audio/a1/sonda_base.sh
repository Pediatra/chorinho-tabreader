#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
RUN="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
$RUN python -c "import sys,numpy,PIL,cv2,torch;print(sys.version);print('numpy',numpy.__version__,'PIL',PIL.__version__,'cv2',cv2.__version__,'torch',torch.__version__)"
$RUN ffmpeg -version | head -1
$RUN python -m pip --version
$RUN python -m pip index versions matplotlib 2>&1 | head -3
$RUN python -m pip download --no-deps --only-binary=:all: --python-version 3.14 --platform manylinux2014_x86_64 --platform manylinux_2_17_x86_64 --platform manylinux_2_28_x86_64 -d /tmp/wh matplotlib 2>&1 | tail -3
$RUN python -m pip list 2>/dev/null | grep -i -E "^(pillow|numpy|contourpy|cycler|fonttools|kiwisolver|pyparsing|python-dateutil|packaging|six|matplotlib) "

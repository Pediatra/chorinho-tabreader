#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
RUN="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
$RUN sh -c 'python -m pip install --dry-run --ignore-installed --report /tmp/rep.json matplotlib==3.11.2 >/tmp/dry.log 2>&1; tail -3 /tmp/dry.log; python -c "
import json
r=json.load(open(\"/tmp/rep.json\"))
for i in r[\"install\"]:
    m=i[\"metadata\"]; print(m[\"name\"], m[\"version\"])
"'

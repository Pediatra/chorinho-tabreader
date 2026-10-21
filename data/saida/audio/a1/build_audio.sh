#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset
podman build -t chorinho-audio:dev - < Dockerfile.audio
echo "build exit: $?"

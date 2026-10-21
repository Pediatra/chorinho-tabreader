#!/bin/sh
# Roda o passo 4 dentro do container (paths do container, /app).
set -e
cd /app
PYTHONPATH=/app python data/saida/audio/a4/campanitas_alarmes/passo4_janela.py

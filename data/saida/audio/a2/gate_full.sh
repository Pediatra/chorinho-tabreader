#!/bin/sh
sh /var/home/gabriel/Projects/chorinho-dataset/data/saida/audio/a2/base.sh 'cd /app; echo "== ruff check ."; ruff check . ; echo "exit $?"; echo "== ruff format --check ."; ruff format --check . ; echo "exit $?"; echo "== pytest"; python -m pytest tests/ -q -m "not integration" -p no:cacheprovider 2>&1 | tail -25'

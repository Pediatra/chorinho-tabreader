# Todo comando do projeto roda DENTRO do container (Regra de Ouro do AGENTS.md).
# O host só tem o .venv do editor; ele não executa o pipeline.

COMPOSE ?= docker compose -f compose.yaml -f compose.podman.yaml
RUN     := $(COMPOSE) run --rm chorinho

.PHONY: help build verify-install lint format test test-integration shell avaliar gate

help:
	@grep -E '^[a-z-]+:' Makefile | cut -d: -f1 | grep -v help

build:
	$(COMPOSE) build

verify-install:
	$(RUN) python -c "import torch, cv2, numpy; print('torch', torch.__version__, '| cuda', torch.cuda.is_available(), '| cv2', cv2.__version__)"
	$(RUN) ffmpeg -version | head -1

lint:
	$(RUN) ruff check .
	$(RUN) ruff format --check .

format:
	$(COMPOSE) run --rm -e RUFF_CACHE_DIR=/tmp/ruffcache chorinho ruff check --fix .
	$(COMPOSE) run --rm -e RUFF_CACHE_DIR=/tmp/ruffcache chorinho ruff format .

test:
	$(RUN) pytest tests/ -q

test-integration:
	$(RUN) pytest tests/ -q -m integration

avaliar:
	$(RUN) python -m tab.tablatura.ouro.avaliar

shell:
	$(COMPOSE) run --rm chorinho bash

gate:
	$(COMPOSE) run --rm -e RUFF_CACHE_DIR=/tmp/ruffcache chorinho ruff check .
	$(COMPOSE) run --rm -e RUFF_CACHE_DIR=/tmp/ruffcache chorinho ruff format --check .
	$(COMPOSE) run --rm chorinho pytest tests/ -q -p no:cacheprovider

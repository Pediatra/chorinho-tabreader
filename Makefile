# Todo comando do projeto roda DENTRO do container (Regra de Ouro do AGENTS.md).
# O host só tem o .venv do editor; ele não executa o pipeline.

COMPOSE := docker compose
RUN     := $(COMPOSE) run --rm chorinho

.PHONY: help build verify-install lint format test test-integration shell avaliar

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
	$(RUN) ruff check --fix .
	$(RUN) ruff format .

test:
	$(RUN) pytest tests/ -q

test-integration:
	$(RUN) pytest tests/ -q -m integration

avaliar:
	$(RUN) python -m tab.avaliar

shell:
	$(COMPOSE) run --rm chorinho bash

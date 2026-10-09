FROM python:3.14-slim

# O venv vive em /opt/venv, FORA de /app, para que o bind-mount do código
# (./:/app) não esconda os pacotes instalados.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

# ffmpeg é obrigatório, não opcional: 44% do acervo é AV1 e o OpenCV não
# decodifica — sem o fallback, quase metade dos vídeos passa em branco.
#
# fonts-liberation também não é enfeite: são as fontes do GERADOR SINTÉTICO.
# Fonte é dependência de DADO aqui — trocar de fonte muda a distribuição do
# treino e portanto a métrica. Sem elas o treino quebra (e é para quebrar).
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg fonts-liberation libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv \
    && pip install --no-cache-dir --upgrade pip

# torch do índice CUDA (a GPU é a mesma do host), resto do PyPI.
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cu130 \
        torch torchvision \
    && pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /app

# Sanidade: se este comando falhar, a imagem está quebrada.
RUN python -c "import torch, cv2, numpy; print('torch', torch.__version__, 'cv2', cv2.__version__)"

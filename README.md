# chorinho

Transcreve a **tablatura de violão que aparece na tela** de vídeos-aula para JSON
estruturado, com **corda, casa, coluna, compasso, técnica e o instante do vídeo** em
que cada nota é executada.

## Como rodar

Tudo roda em container. O `.venv` do host serve só para o editor ler o código.

```bash
make build            # constrói a imagem (torch cu130, opencv, ffmpeg, fontes)
make verify-install   # confere CUDA, cv2 e ffmpeg DENTRO do container
make test             # gate: 14 testes
make lint             # ruff check + format

# aferição no gabarito rotulado à mão — é o número oficial
docker compose run --rm chorinho python -m tab.avaliar

# vídeo -> JSON
docker compose run --rm chorinho python -m tab.transcrever \
    "/acervo/sky guitar/ALGUM_VIDEO.mp4" --json data/saida/sky.json

# treinar o classificador de glifos (sintético), com semente fixa
docker compose run --rm chorinho python -m tab.sintetico \
    --n-linhas 320 --epocas 22 --seed 1 --saida artefatos/semente_1
```

O acervo (3.781 vídeos, 190 GB, 13 canais) entra montado em `/acervo`, **somente
leitura**.

## Estado

| | |
| --- | --- |
| número oficial | **0,949** (66/72, 71/72, 68/72) em **72 glifos / 3 canais** / casas 0–7 — `raman korshun` fora (2026-10-09); **não é ganho**, o denominador caiu de 96/4 |
| tablatura | corda, coluna e compasso robustos |
| tempo | **dois mecanismos**: faixa vertical (`sky guitar`, desvio 0,16 s) e cor cumulativa (`cifra club`, 41/41 onsets) |
| técnica/símbolo | gravados, **ainda não aferidos** |
| partitura de 5 linhas | **fora** desta cadeia (exige OMR próprio) |

Leia [`ESTADO.md`](ESTADO.md) para os limites e [`docs/HISTORICO.md`](docs/HISTORICO.md)
para as 65 rodadas de medição (inclusive o que **já falhou** e não deve ser repetido).
Perguntas abertas para o dono do projeto: [`PERGUNTAS.md`](PERGUNTAS.md). Regras de
trabalho: [`AGENTS.md`](AGENTS.md).

## Onde está o quê

| caminho | o que é |
| --- | --- |
| `tab/` | o motor (ver [`tab/README.md`](tab/README.md)) |
| `tab/caminhos.py` | acervo, gabarito, artefatos — caminho não se espalha |
| `tests/` | gate sem GPU e sem acervo |
| `data/gold/gabarito.json` | 72 glifos rotulados à mão, 3 canais (`raman korshun` descartado) |
| `data/saida/` | JSONs gerados (visíveis no host) |
| `artefatos/` | pesos treinados |
| `configs/` | mapa por canal e mapa de símbolos (a criar) |
| `parts/clipes/` | 18 recortes de amostra |

# tab/ — o motor

Pacote único, com uma pasta por trilha (decisão 9001). Todo módulo é CLI: `python -m tab.<modulo>`, **sempre dentro do
container** (`docker compose run --rm chorinho python -m tab.<modulo> ...`).

- Cada trilha tem a sua pasta: `comum/`, `cruzamento/`, `tablatura/`, `maos/`, `audio/` e `partitura/`.
- Os 149 nomes antigos (`tab.avaliar`, `tab.caminhos`…) continuam importando e rodando, por apelido em `tab/_apelidos.py`.
- Código novo usa o nome novo, com import absoluto (`from tab.comum.caminhos import ...`).

## Camadas

| módulo | o que faz |
| --- | --- |
| `comum/caminhos.py` | acervo, gabarito, saída e artefatos em um lugar só (env `CHORINHO_ACERVO`) |
| `tablatura/leitura/tabseg.py` | **geometria**: recorte → grade de 6 cordas, barlines, passo e tokens por corda/coluna |
| `tablatura/leitura/glyphset.py` | inventário de glifos e `normalizar()` (recorte 24×16 usado pelo classificador) |
| `tablatura/leitura/glyph_bench.py` | `GlifoCNN` (~74 mil parâmetros) + treino/aferição contra rótulos prata |
| `tablatura/treino/sintetico.py` | gerador de tablatura sintética + treino + aferição no gabarito real |
| `tablatura/leitura/reconhecer.py` | linha → `(corda, casa, técnica)` + compasso + tempo; portão de forma |
| `tablatura/leitura/cursor.py` | marcador por **faixa vertical**: `x(t)`, saltos, trocas de sistema |
| `tablatura/produto/transcrever.py` | **vídeo → JSON** (painel, grade, marcação, tempo), ponta a ponta |
| `tablatura/leitura/inventario.py` | varre o acervo (família, painel, marcador) — com fallback `ffmpeg` |
| `tablatura/ouro/ouro.py` | recorta glifo isolado do acervo para rotular à mão |
| `tablatura/ouro/avaliar.py` | aferição padronizada no gabarito — **é o número oficial** |
| `tablatura/censo/exp_binarizacao.py` | experimento: compara binarizações sobre as 5 famílias |

## Fluxo

```
vídeo → tablatura/leitura/inventario (acha o painel) → tablatura/leitura/tabseg (grade + tokens)
      → classificador de ~74k params (treinado em sintético: tablatura/treino/sintetico.py)
      → tablatura/leitura/reconhecer (casa + técnica + compasso) + tablatura/leitura/cursor (tempo)
      → tablatura/produto/transcrever (JSON por vídeo) → tablatura/ouro/avaliar (aferição)
```

## Comandos

```bash
# aferição (o número oficial; reporte média de >=3 sementes)
docker compose run --rm chorinho python -m tab.tablatura.ouro.avaliar

# treinar com semente fixa e guardar em artefatos/ (nunca em /tmp)
docker compose run --rm chorinho python -m tab.tablatura.treino.sintetico \
    --n-linhas 320 --epocas 22 --seed 1 --saida artefatos/semente_1

# vídeo -> JSON
docker compose run --rm chorinho python -m tab.tablatura.produto.transcrever VIDEO --json data/saida/x.json

# grade de um recorte, com depuração visual
docker compose run --rm chorinho python -m tab.tablatura.leitura.tabseg IMAGEM \
    --debug data/saida/seg.png --json data/saida/seg.json
```

`data/saida/` e `artefatos/` são visíveis no host; o `/tmp` **do container não é** — não
grave resultado que precise ser inspecionado em `/tmp`.

Números de referência, limites e o que já falhou: [`../docs/estado/`](../docs/estado/) (índice: [`../ESTADO.md`](../ESTADO.md)) e
[`../docs/HISTORICO.md`](../docs/HISTORICO.md).

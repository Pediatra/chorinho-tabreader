# tab/ — o motor

Pacote único, flat. Todo módulo é CLI: `python -m tab.<modulo>`, **sempre dentro do
container** (`docker compose run --rm chorinho python -m tab.<modulo> ...`).

## Camadas

| módulo | o que faz |
| --- | --- |
| `caminhos.py` | acervo, gabarito, saída e artefatos em um lugar só (env `CHORINHO_ACERVO`) |
| `tabseg.py` | **geometria**: recorte → grade de 6 cordas, barlines, passo e tokens por corda/coluna |
| `glyphset.py` | inventário de glifos e `normalizar()` (recorte 24×16 usado pelo classificador) |
| `glyph_bench.py` | `GlifoCNN` (~74 mil parâmetros) + treino/aferição contra rótulos prata |
| `sintetico.py` | gerador de tablatura sintética + treino + aferição no gabarito real |
| `reconhecer.py` | linha → `(corda, casa, técnica)` + compasso + tempo; portão de forma |
| `cursor.py` | marcador por **faixa vertical**: `x(t)`, saltos, trocas de sistema |
| `transcrever.py` | **vídeo → JSON** (painel, grade, marcação, tempo), ponta a ponta |
| `inventario.py` | varre o acervo (família, painel, marcador) — com fallback `ffmpeg` |
| `ouro.py` | recorta glifo isolado do acervo para rotular à mão |
| `avaliar.py` | aferição padronizada no gabarito — **é o número oficial** |
| `exp_binarizacao.py` | experimento: compara binarizações sobre as 5 famílias |

## Fluxo

```
vídeo → inventario (acha o painel) → tabseg (grade + tokens)
      → classificador de ~74k params (treinado em sintético: sintetico.py)
      → reconhecer (casa + técnica + compasso) + cursor (tempo)
      → transcrever (JSON por vídeo) → avaliar (aferição)
```

## Comandos

```bash
# aferição (o número oficial; reporte média de >=3 sementes)
docker compose run --rm chorinho python -m tab.avaliar

# treinar com semente fixa e guardar em artefatos/ (nunca em /tmp)
docker compose run --rm chorinho python -m tab.sintetico \
    --n-linhas 320 --epocas 22 --seed 1 --saida artefatos/semente_1

# vídeo -> JSON
docker compose run --rm chorinho python -m tab.transcrever VIDEO --json data/saida/x.json

# grade de um recorte, com depuração visual
docker compose run --rm chorinho python -m tab.tabseg IMAGEM \
    --debug data/saida/seg.png --json data/saida/seg.json
```

`data/saida/` e `artefatos/` são visíveis no host; o `/tmp` **do container não é** — não
grave resultado que precise ser inspecionado em `/tmp`.

Números de referência, limites e o que já falhou: [`../ESTADO.md`](../ESTADO.md) e
[`../docs/HISTORICO.md`](../docs/HISTORICO.md).

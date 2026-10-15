# 3016 — Páginas de pauta sem o produto da tab

**Data:** 2026-10-15 · **Trilha:** partitura · **Código:** `tab/partitura_video.py`
(`assinatura`, `diferenca`, `agrupar_paginas`, `paginar`), `tests/test_partitura_video.py`

## Por quê

Só 8 vídeos têm produto de tab (`chorinho/video@1`), e 3 deles têm pauta. Pela P0, uns 1.455
vídeos têm pauta. Para ler a partitura deles sem esperar a trilha tablatura, a partitura
precisa achar as páginas sozinha.

## Como

1. Lê o vídeo inteiro numa passada de ffmpeg, a 1 quadro por segundo.
2. Em cada quadro, faz a **assinatura**: a região das pautas reduzida a 256×64, com tinta
   binária.
3. Quadros seguidos com diferença ≤ 0,25 da primeira amostra formam um trecho estável.
   Trecho com menos de 2 amostras é descartado: é virada de página ou fade.
4. Trecho que repete uma página já vista vira nova exibição dela.
5. Para cada página, recorta todas as pautas no meio da exibição mais longa (`P01a`,
   `P01b`...).

Saída em `data/saida/partitura/sem_produto/<slug>/recortes/`. A pasta é separada de
`partitura/video/` para nunca apagar os recortes de um produto.

## Medição: os 3 vídeos onde a resposta é conhecida

| vídeo | telas do produto | páginas achadas | caixa igual à do produto | tempo |
| --- | ---: | ---: | ---: | ---: |
| greensleeves | 4 | 4 | 4/4 | 14 s |
| south american | 3 | 3 | 3/3 | 29 s |
| gymnopédie | 12 | 12 | 12/12 | 24 s |

- Cada tela do produto cai numa página só, e nenhuma página sobra.
- As repetições do greensleeves (cada página aparece 2 vezes) foram juntadas certo.
- As exibições batem com as do produto com diferença de até ~1,5 s.
- Saída em `data/saida/partitura/diag/conferir_paginas.txt`.

O tempo vem do ffmpeg e da detecção. A ~25 s por vídeo, os 1.455 levam ~10 h de CPU, antes
do Audiveris.

## Limites

- **A assinatura não vê as linhas da pauta:** o corte é pela mediana da linha de pixels, e
  numa linha de pauta essa mediana é a própria tinta. Ela vê notas, hastes e números. Duas
  páginas com pauta vazia pareceriam iguais. Não aconteceu nos 3 vídeos.
- Validado só em 3 canais, todos com uma pauta por tela. Página com 2 ou 3 sistemas ainda
  não foi vista.

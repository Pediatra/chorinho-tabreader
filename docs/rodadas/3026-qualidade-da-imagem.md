# 3026 — a qualidade da imagem e a cobertura do Audiveris

Pergunta do dono (2026-10-18), vendo a conferência da D1: imagem melhor dá pauta mais certa,
sobretudo com muitos elementos na tela? Script:
`data/saida/partitura/diag/qualidade_imagem/medir.py` (só lê). Junta os três gabaritos do dono
(P1, sem produto, D1): 59 recortes conferidos.

Medidas por recorte: entrelinha da pauta no quadro original (px, do `indice.json`), fração de
tinta (cinza < 128), fração de cor (HSV), nitidez (variância do Laplaciano), notas por compasso.

## Resultado

| entrelinha | recortes | certos/(certos+faltando) | certos/lidos |
| --- | ---: | ---: | ---: |
| < 11 px | 10 | 0,868 | 0,970 |
| 11 a 13 px | 12 | 0,885 | 0,981 |
| 13 a 16 px | 7 | 0,868 | 0,953 |
| ≥ 16 px | 30 | **0,934** | 0,982 |

- Correlação de Spearman da cobertura por recorte: tinta **−0,29**, entrelinha +0,11, nitidez
  +0,10, cor +0,03, notas por compasso −0,02.
- **A precisão não muda com a imagem** (0,95 a 0,98 em todas as faixas). O que a imagem pior
  faz é o Audiveris deixar nota de fora.
- Leitura que não sai ("No system found"), piloto + D1, 202 recortes: < 11 px 49/66 saem; ≥ 13
  px 119/125. Mas 16 das 17 falhas abaixo de 11 px são de um vídeo só (mela, faixa amarela,
  hoje apagado do acervo); sem ele, 25 de 26 saem.
- 720p contra 1080p: 0,879 contra 0,904 (7 recortes em 720p).

## Leitura

Apoia a hipótese do dono, com tamanho modesto: pauta grande (≥ 16 px) cobre ~5 pontos a mais, e
tela carregada (tinta) é o fator que mais acompanha a perda. n pequeno e confundido com canal:
os canais de pauta pequena são poucos. É correlação, não causa.

Ampliar com interpolação não é a saída: 3x e 4x pioram (rodada 3003).

## Próximo passo proposto (não feito)

Teste causal com o gabarito que já existe: reduzir os recortes de pauta grande (≥ 16 px) para
~11 px, ler de novo com o Audiveris e contar quantas notas certas da leitura original a leitura
reduzida ainda acha. Se cair de ~0,93 para ~0,87, o tamanho causa a perda. Se o tamanho causar,
a frente é aumentar a resolução de verdade (fonte melhor ou super-resolução treinada para
partitura), não interpolar.

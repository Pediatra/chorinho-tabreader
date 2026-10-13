# 2009 — Áudio A4: por que o alinhador recusa metade do shin izumi (o produto perde a corda 1)

Data: 2026-10-13. Vídeo: `shin izumi/【tab】room 335` (sem marcador). Scripts e saídas:
`data/saida/audio/a4/shin/` (tabela por exibição, cosseno por casa, recortes do painel,
sonda de transposição, figuras de janela).

## Pergunta

O alinhador v2 recusa 23 de 42 exibições deste vídeo (114 de 552 colunas com tempo), todas
por "poucas colunas casadas". A causa está no áudio ou no produto?

## Hipóteses e medição

| hipótese | medição | veredito |
| --- | --- | --- |
| casas > 7 mal lidas (classificador validado só em 0–7) derrubam o cosseno | recusadas têm **menos** casa > 7 que aceitas (mediana 0,05 × 0,28); nas aceitas, cos mediano 0,822 (casas ≤ 7) × 0,784 (alguma > 7) | **não é a causa principal** |
| cosseno baixo | cos médio das recusadas 0,829 × aceitas 0,785 | **descartada**: casam bem, mas casam poucas |
| capotraste / afinação | transposição −2/−1/0/+1/+2: recusadas 41/40/**23**/42/42; afirmadas 4/8/**114**/0/0 | **descartada**: afinação padrão é a melhor |
| notas rápidas demais | candidatos por segundo 10,3 × 10,0 (recusadas × aceitas) | **descartada** como diferença entre grupos |
| janela da exibição errada | as telas trocam a cada ~3,8 s em sequência; o som é contínuo antes e depois de cada janela, o que é esperado em página que muda durante a música | **inconclusivo**, sem sinal de deslocamento |
| **o produto perde colunas** | ver abaixo | **apoiada** |

## O produto perde a corda 1

- Notas por corda no produto: shin izumi tem **4 %** na corda 1 (42 de 998). Nos outros
  vídeos, a corda 1 tem 17–27 % (MVP 17 %, iwaki 23 %, kimny 27 %). Este solo é de violão
  e anda pela região aguda, então a corda 1 deveria ter muitas notas.
- Recortes olhados (`quadros/`):
  - **Tela 12**: a imagem tem ~8 colunas; o produto tem 5, todas corretas. Faltam todas
    as notas da corda 1 (5, 0, 8) e as colunas em que a corda 1 está sozinha ou em
    acorde (5/0, 0/7).
  - **Tela 25**: a imagem tem ~24 colunas, 11 notas delas na corda 1 (10 9 8 7 …
    7 10 12 10 9 10 9). O produto tem 15 colunas, e só ~9 batem com a imagem:
    - na corda 1, um só "10" lido como **14**;
    - duas pausas (o glifo de pausa com 7) lidas como notas (3,0)(4,7);
    - leituras inexistentes, como (5,15) e (3,19).
  - Telas 41 e 20 (aceitas): concordância alta nas colunas lidas.
- As notas da corda 1 ficam sobre a linha de cima do painel, encostadas na borda do recorte.
  Hipótese para a trilha tablatura: o painel ou a grade cortam a corda 1 neste canal.
  Não medido por mim.

## Leitura

O alinhador recusa porque a sequência de colunas que recebe tem buracos: colunas tocadas
sem coluna no produto, e colunas que não existem. Com metade das notas faltando, a
programação dinâmica não acha 4 colunas seguidas que casem. O áudio e o método não são o
gargalo deste vídeo; **o gargalo é a leitura**.

## Consequências

1. Pedido à trilha tablatura (repassar pelo dono): no canal `shin izumi`, a corda 1 quase
   não aparece no produto (4 % das notas, contra 17–27 % nos outros), e pausas viram notas
   (tela 25). Recortes em `data/saida/audio/a4/shin/quadros/`.
2. A taxa de recusa do alinhador serve de **alarme de leitura**: exibição recusada com
   cosseno alto e poucas casadas aponta tela com colunas faltando.
3. Nada a mudar no alinhador por causa deste vídeo.

## Limites

A conferência visual foi feita em 2 telas recusadas com contagem e 4 mais por amostra, não
glifo a glifo nas 42. A causa exata (painel, grade ou classificador) é da trilha tablatura.

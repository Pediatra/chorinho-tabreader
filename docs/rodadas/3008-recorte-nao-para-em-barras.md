# 3008 — Recorte da pauta: barras de colcheia não são vizinhas

**Data:** 2026-10-14 · **Trilha:** partitura · **Código:** `tab/partitura_recortes.py`,
`tests/test_partitura_recortes.py`

## Pergunta

O dono apontou que o R21 (guitarous) corta a parte de cima. Por quê?

## Causa

O recorte para no primeiro "vizinho" acima da pauta, que é qualquer estrutura horizontal longa
(pelo menos 50 % da pauta). No R21, o vizinho era o conjunto de barras de semicolcheia em
y = 436, com 23 px de altura e 825 px de largura. Ele limitou o topo em 441, quando a margem
pedia 391. Barras, hastes e notas agudas ficaram de fora.

## Conserto

Estrutura com espessura acima de 1,5 entrelinha não limita mais o recorte
(`FATOR_ESPESSURA_VIZINHA`). As linhas de pauta e de tab têm 2 a 3 px.

Espessuras medidas, em entrelinhas:

| estrutura | espessura | efeito |
| --- | ---: | --- |
| barras do R21 | 2,4 | ignoradas agora |
| barras do R14 | 3,0 | ignoradas agora |
| vizinhos que continuam valendo (R05, R10, R15, R19) | 0,7 a 1,3 | continuam limitando |

## Resultado (recortes com margem 7/7, refeitos em `p1/recortes_teste/`)

- **19 de 21 caixas idênticas.**
- **R21:** o topo vai de 441 para 391. Agora entram as barras e as notas do compasso 4.
- **R14:** o topo vai de 655 para 610. Entram o "♩= 48", o dedilhado (i m a) e as marcas de
  pestana V e III, que antes eram cortados. Conferido no PNG.

## Consequência

- **Gabarito:** `recortes_margem/` não foi trocado. O gabarito do dono usa coordenadas desses
  PNG (cliques de faltando), então trocar R14 e R21 exige refazer a conferência desses dois.
- **Leitura:** a leitura do Audiveris sobre os recortes novos ainda não foi medida.

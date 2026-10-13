# 2015 — Áudio: termo de andamento que aceita colunas perdidas (não adotado)

Data: 2026-10-13. Só medição; nada mudou em `tab/`. Script, log, resultados, alinhamentos e
figuras em `data/saida/audio/a4/andamento_lacuna/`. São 13 vídeos, sem o *campanitas*.

## Hipótese

A rodada 2014 sugeriu: quando a leitura perde uma coluna, duas notas vizinhas ficam a 2T ou 3T
uma da outra. Nesse caso, o termo de andamento do DP (`alinhar_trecho`) as pune. Variante
medida:

  andamento = mín sobre m ∈ {1, 2, 3} de [ λ·|log(dt / (m·dc·T))| + κ·(m − 1) ]

O κ é o preço de cada coluna perdida. Testei κ = 0,1, 0,2 e 0,4; λ e o resto ficam iguais.

## Conferência

A linha de base reproduz o v2.1 gravado: 5342 de 5342 colunas e 214 de 214 exibições. Com
m = 1, a variante dá exatamente a base. Recontei os totais nos alinhamentos gravados.

## Resultado

| config | colunas com tempo | recusadas | colunas da base que mudam > 30 ms | viram nulas | alarmes |
| --- | --- | --- | --- | --- | --- |
| base | 3760 de 5342 | 53 de 214 | — | — | 34 |
| κ = 0,1 | 3897 de 5342 | 50 de 214 | 69 de 3760 | 17 de 3760 | 33 |
| κ = 0,2 | 3814 de 5342 | 52 de 214 | 41 de 3760 | 7 de 3760 | 33 |
| κ = 0,4 | 3760 de 5342 | 53 de 214 | 0 | 0 | 34 |

- **Os 6 casos da rodada 2014** (room 335, telas 12, 25 e 33; giant steps, telas 5, 9 e 13):
  nenhum passa, em nenhum κ. As colunas casadas não mudam.
- **Gabarito do dono** (folhas 1 a 3, 72 itens usados): **0 de 72 mudam**, em todas as
  configurações. A base bate com o gabarito em 72 de 72. Por isso o gabarito não diz se
  as colunas que mudam melhoram ou pioram.
- **κ = 0,1**: aceita 3 exibições a mais (room 335, telas 2 e 34; dream wish, tela 20).
  Em compensação, muda 69 colunas boas e troca um alarme por outro no giant steps.
- **κ = 0,4**: não faz nada. O κ passa do custo de um buraco de 2T, que é λ·log 2 ≈ 0,35.

## Leitura

A variante não resolve o problema que a motivou: os 6 casos continuam recusados. O que ela
ganha (3 exibições, κ = 0,1) custa mudar colunas que ninguém conferiu. **O alinhador fica
como está (v2.1).** Somando esta rodada à 2014, o conserto dessas páginas é a leitura
(decisão 2004), não o custo do DP.

## Limites

Ninguém ouviu as colunas que mudam. O gabarito não cobre nenhuma delas.

# Rodada 23 — ponta a ponta em canais nunca usados

## 1. O que foi feito

Rodei a cadeia completa (painel → grade → tokens → classificador → compasso) em **3 canais que
não estão no gabarito**, para verificar que ela funciona fora do que eu venho ajustando:

| canal | faixa | notas | compassos | cordas usadas | passo |
| --- | --- | --- | --- | --- | --- |
| shin izumi | base | 38 | 7 | 2–6 | 22,0 |
| serge kottelat | base | 91 | 5 | 1–6 | 15,0 |
| cifra club | topo | 58 | 10 | 1–6 | 16,6 |

Artefatos em `saida/exemplo_0.json`, `exemplo_1.json`, `exemplo_2.json`.

## 2. O que isso verifica (e o que não verifica)

**Verifica** que a geometria generaliza: 6 cordas detectadas nos três, notas distribuídas por
múltiplas cordas, compassos numerados e não vazios, passo dentro da faixa medida no inventário
(14,8–36,3 px). Os três têm temas e posições de painel diferentes (dois embaixo, um em cima), e
nenhum deles passou por ajuste meu.

**Não verifica acurácia das casas**: não existe gabarito para estes três canais. O que posso
afirmar é que a **estrutura** está correta e que o **número oficial (0,805)** vale para os 4
canais do gabarito — não para estes. Dizer "funciona nos 12 canais" seria extrapolação.

## 3. Por que isso importa para o goal

O item (e) é "validar e rodar em escala". Rodar em escala exige saber que a cadeia **não
quebra** fora dos canais de ajuste — e é isso que este teste mostra, em três canais com
características diferentes. É o pré-requisito do rollout, não a prova de acurácia.

## 4. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura, 95 % com cursor |
| (b) gabarito verificado | 96 glifos / 4 canais |
| (c) classificador multi-classe | **0,805 (3 sementes)** nos 4 canais do gabarito |
| (d) pipeline ponta a ponta | **verificado em 7 canais** (4 com gabarito + 3 novos) |
| (e) escala nos 3.781 | pré-requisito cumprido; falta o rollout e o gabarito maior |

Próximo passo continua sendo o que limita a medição: **ampliar o gabarito real** (casas 8–24,
mais canais) e tratar a **marca de técnica** como classe própria. Só depois o rollout faz sentido
em escala — rodar 3.781 vídeos com 0,805 medido em 4 canais seria transformar uma medição
estreita em promessa larga.

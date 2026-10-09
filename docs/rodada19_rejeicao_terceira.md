# Rodada 19 — classe de rejeição: terceira tentativa, terceira nula

## 1. O que fiz

Movi o lixo desenhado para os **vãos entre colunas** de notas (a correção que eu mesmo havia
identificado na rodada anterior), para ele ser extraído como token próprio e sobrar sem par.

## 2. Resultado

| | |
| --- | --- |
| classes do modelo | **19 — `junk` continua ausente** |
| total medido | **82/96 = 0,854** (inalterado) |

## 3. Causa provável, medida

Medi os traços verticais desenhados nas linhas sintéticas: **largura de 2 px**. O filtro de
ruído do extrator descarta componente com `w < 0,07 × passo`, ou seja:

| passo da linha | limiar | traço de 2 px |
| --- | --- | --- |
| 16 px | 1,1 px | sobrevive |
| 30 px | 2,1 px | **descartado** |

Então parte do lixo que eu desenho é removida pelo próprio extrator antes de virar token — e o
que sobrevive é pouco demais para criar a classe (o modelo continuou com 19).

O lixo real do `raman korshun` é **duas barras verticais próximas** (o token aparecia com
`partes=2`), provavelmente resto de barline dupla, com 2–3 px cada. O meu é um traço único e
fino — não é a mesma coisa.

## 4. Próximo passo concreto

Desenhar o lixo como **barra dupla** (dois traços de 2–3 px lado a lado, total ~0,3–0,4 passo),
espelhando o caso real — e conferir a contagem de tokens sem par **antes** de treinar, para não
gastar um treino descobrindo que a classe não nasceu.

Essa última parte é a lição das três tentativas: eu deveria ter medido "quantos tokens sem par
o gerador produz" **antes** de treinar. É uma medida de 30 linhas e teria evitado três retreinos.

## 5. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura, 95 % com cursor |
| (b) gabarito verificado | 96 glifos / 4 canais |
| (c) classificador multi-classe | **0,854 real** — 2 canais em 1,00; erros concentrados em 2 canais |
| (d) pipeline ponta a ponta | corda, casa, técnica, tempo, compasso e andamento |
| (e) escala nos 3.781 | pendente |

Erros restantes: `raman korshun` 12 (`junk → 1/5` e `7 → harmonico`) e `paolo d'angelo` 2
(`1 → 4`). Os dois canais MuseScore seguem com **zero erro**. O estado é seguro: o lixo
desenhado não afetou nenhum canal e o modelo segue íntegro.

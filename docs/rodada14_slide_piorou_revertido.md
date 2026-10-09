# Rodada 14 — terceira tentativa no slide: piorou, e foi revertida

## 1. O que tentei

Seguindo o diagnóstico da rodada anterior (o sintético não desenha slide como o real), passei
a desenhar no gerador uma **barra diagonal cruzando o algarismo** — a forma que o canal
`raman korshun` usa — e retreinei.

## 2. Resultado: piorou

| canal | antes | com a barra diagonal |
| --- | --- | --- |
| iwaki | 27/27 = 1,00 | **23/27 = 0,85** |
| sky guitar | 15/15 = 1,00 | **9/15 = 0,60** |
| raman korshun | 12/24 = 0,50 | 11/24 = 0,46 |
| **TOTAL** | **54/66 = 0,818** | **43/66 = 0,652** |

A tentativa **estragou as duas classes que estavam perfeitas**: os erros novos são todos
`1 → 4` e `1 → 5`. A barra diagonal que eu desenho encosta no algarismo, o token fica largo, e
o rótulo continua sendo o algarismo — então o modelo aprendeu que mancha larga com traço
vertical é `1`, e passou a confundir os `1` reais.

Diagnóstico anterior estava **certo no princípio e errado na execução**: o sintético precisa
cobrir a forma real, mas não basta desenhar a forma e manter o rótulo igual. Precisa
**separar a marca do algarismo** (cortar a barra antes de rotular), ou então treinar a marca
como **classe própria** (a taxonomia `tecnica` já existe no JSON) — não jogá-la dentro do
token do algarismo.

## 3. Revertido

Desfiz a mudança do gerador e retreinei: **54/66 = 0,818**, exatamente o estado anterior.
O repositório está no estado bom; a tentativa está registrada aqui para não ser repetida.

Bug menor encontrado no caminho: `avaliar_no_gabarito` em `tools/sintetico.py` assume índices
contíguos no gabarito e quebra agora que existem entradas `junk` (índices não contíguos).
A aferição oficial passou a ser a de `tools/reconhecer.py`, que não tem esse problema.

## 4. Estado do goal (inalterado)

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura, 95 % com cursor |
| (b) gabarito verificado | 66 glifos / 3 canais / 9 classes |
| (c) classificador multi-classe | **0,818 real** — 3 tentativas de correção, 3 falhas, causa já diagnosticada |
| (d) pipeline ponta a ponta | corda, casa, técnica, tempo, compasso e andamento |
| (e) escala nos 3.781 | pendente |

Três tentativas seguidas sem ganho no mesmo ponto. O que resta a fazer está claro e não é
mais tentativa às cegas: **tratar a marca de técnica como classe própria** (separando-a do
algarismo), em vez de deixá-la dentro do token; e depois a **classe de rejeição** para o lixo.
Se essas duas também falharem, o caminho passa a ser ampliar o gabarito real em vez de insistir
no extrator.

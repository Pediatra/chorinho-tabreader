# Rodada 18 — lixo deliberado: colocado no lugar errado

## 1. O que fiz

Desenhei no gerador traços verticais curtos — o lixo que de fato sobrevive ao extrator no canal
`raman korshun` — com rótulo `junk`, para dar ao modelo a classe de rejeição que faltava.
O código está aplicado (`tools/sintetico.py`, linha 89).

## 2. Resultado: a classe não nasceu

| | |
| --- | --- |
| classes do modelo | **19 — "junk" continua ausente** |
| total medido | **82/96 = 0,854** (inalterado) |

Medi por quê, em 30 linhas sintéticas:

| | |
| --- | --- |
| notas desenhadas | 937 |
| tokens extraídos | 888 |
| **tokens sem par (candidatos a lixo)** | **3** |

## 3. A causa, medida

Os traços são sorteados numa posição x qualquer — e **caem dentro do intervalo x de alguma
nota**. Nesse caso o casamento os identifica como sendo *aquela nota*, e eles recebem o rótulo
do algarismo, não `junk`.

Ou seja, o lixo desenhado não vira classe de rejeição: ele **polui o rótulo de notas reais**.
Por sorte em quantidade irrelevante (3 em 937), e o total ficou idêntico — mas o desenho está
no lugar errado.

## 4. Correção para a próxima rodada

O lixo tem de ser desenhado **nos vãos entre colunas de notas**, não em x aleatório: só assim
ele é extraído como token próprio e sobra sem par. É uma mudança de uma linha (escolher x a
partir da lista de colunas, deslocado meia coluna), e é a diferença entre poluir rótulo e criar
classe.

Registro o padrão que já se repetiu três vezes nesta série: **acertar o princípio não basta, o
detalhe de execução decide** — e o detalhe só aparece porque eu meço o efeito em vez de supor
que funcionou.

## 5. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura, 95 % com cursor |
| (b) gabarito verificado | 96 glifos / 4 canais |
| (c) classificador multi-classe | **0,854 real** — 2 canais em 1,00; erros concentrados em 2 canais |
| (d) pipeline ponta a ponta | corda, casa, técnica, tempo, compasso e andamento |
| (e) escala nos 3.781 | pendente |

Erros restantes: `raman korshun` 12 (lixo virando algarismo e `7 → harmonico`) e
`paolo d'angelo` 2 (`1 → 4`). Os dois canais MuseScore seguem com **zero erro**.

# Rodada 25 — cursor: a medição acusou 38 %, mas a medição está suspeita

## 1. O que mediu

Amostra de 2 vídeos por canal (12 canais), quadro a 40 % da duração:

| | resultado |
| --- | --- |
| painel de tablatura localizado | **24/24 = 100 %** |
| cursor detectável (>50 % das amostras numa janela de 10 s) | **9/24 = 38 %** |

Por canal, o cursor saiu 0 % em `paolo d'angelo`, `shin izumi`, `tv on guitar` e `violaodecria`;
50 % na maioria; 100 % em `tv cifras`.

## 2. Por que eu desconfio do número do cursor

**O painel é confiável, o cursor não** — e o motivo é um erro meu de medição:

- o quadro que define o painel é lido em **40 % da duração** do vídeo;
- mas a janela de rastreio do cursor começa num **tempo fixo de 40 segundos**.

Para qualquer vídeo que não dure exatamente 100 s, os dois instantes **não são o mesmo**. Estou
procurando o cursor num trecho diferente daquele onde sei que o painel existe — e ainda assim o
painel foi achado em 24/24 porque a notação é estática, mas o cursor pode não estar naquele
trecho (intro, fala, troca de sistema).

Evidência de que é erro de medição: **o inventário da rodada 3 mediu 95 % de cursor** usando a
mesma função `detectar_cursor`, no mesmo quadro do painel. Dois números meus, medidos com a mesma
ferramenta, discordando por 57 pontos — a diferença está no *quando* eu olho, não na ferramenta.

## 3. O que fica válido desta rodada

- **O painel de tablatura é encontrado em 100 % da amostra** — reforça o 96 % do inventário, agora
  em 24 vídeos dos 12 canais, com a busca em 3 faixas. Esse número não depende do alinhamento.
- O **defeito de medição** está identificado e é de uma linha: usar o mesmo instante
  (`frac × duração`) para definir o painel **e** iniciar a janela do cursor.

## 4. Próximo passo, já corrigido o alinhamento

Refazer a medição do cursor com a janela começando no instante do quadro do painel, e reportar:

1. % de vídeos com cursor detectável **naquele** trecho (o que o produto precisa);
2. quantos segundos o cursor permanece visível (o tempo que dá para transcrever).

Sem isso, não sei dizer se o anexo de tempo cobre 38 % ou 95 % dos vídeos — e essa diferença é a
diferença entre um produto utilizável e um protótipo.

## 5. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura, 95 % com cursor (medição a corrigir) |
| (b) gabarito verificado | 96 glifos / 4 canais |
| (c) classificador multi-classe | **0,805 (3 sementes)** |
| (d) pipeline ponta a ponta | comando único; tempo e compasso com cobertura parcial |
| (e) escala nos 3.781 | pré-requisito cumprido; rollout não iniciado |

Nada foi alterado no código nesta rodada — só medido. O painel está sólido (100 %), e o cursor tem
uma medição a refazer antes de eu afirmar qualquer coisa sobre a cobertura do tempo.

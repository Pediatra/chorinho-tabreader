# Rodada 37 — normalizar por quadro não basta: a cor é de voz, não de nota

## 1. O que foi feito e o que saiu

Normalizei a fração cromática por instante (token menos mediana do quadro) e procurei os
*outliers* — o que deveria ser a nota em execução.

Vídeo `cifra club / 505 - arctic monkeys`, 74 tokens, 8 instantes:

| t | mediana do quadro | outliers + | outliers − |
| --- | --- | --- | --- |
| 0,40 | 0,83 | 0 | **25** |
| 0,42 | 0,33 | **22** | 0 |
| 0,44 | 0,29 | 20 | 0 |
| 0,46 | 0,10 | 25 | 0 |
| 0,48 | 0,63 | 0 | **24** |
| 0,50 | 0,46 | 17 | 0 |
| 0,54 | 0,20 | 19 | 0 |

**17 a 25 tokens "destacados" por instante** — não 1 ou 2. A normalização não isolou a nota.

## 2. Por que — e isso já estava nos meus próprios dados

Na rodada 1, ao levantar os canais de vídeo, a análise registrou:

> "**Per-voice colour: YES** — blue, green and red digits alongside black; coloured TAB digits
> align in x with equally-coloured noteheads above."

Ou seja: nesse estilo de canal **os algarismos já são coloridos por voz** — metade da tablatura
tem cor de propósito. Então "ter cor" não distingue nada: o meu medidor conta cor de voz como se
fosse realce.

O realce da nota atual é uma **categoria de cor diferente** (ou mais clara) sobre um fundo que já é
colorido. Comparar *quantidade* de cor não separa; é preciso comparar **qual** cor.

## 3. A correção certa

Trocar a métrica de **fração cromática** por **categoria de cor por token**:

1. para cada token e cada instante, classificar a cor em um conjunto pequeno e nomeado (preto,
   azul, verde, vermelho, laranja, branco);
2. acompanhar a **categoria** ao longo do tempo, por token;
3. o marcador é o token cuja **categoria muda** — não o que tem cor.

Isso tem a vantagem de já servir para o objetivo declarado do goal, que inclui **voz/cor**: a mesma
classificação que identifica o realce também rotula a voz (azul/verde/vermelho) de cada nota.

## 4. Onde o anexo de tempo está

| tentativa | resultado |
| --- | --- |
| banda vertical (matiz azul, estreita) | funciona só onde existe faixa; **rejeita o `cifra club`** |
| fração cromática absoluta | mede estilo do canal (muita cor de base) |
| fração cromática normalizada por quadro | 17–25 "destacados" por instante — **não isola** |
| **categoria de cor por token (próximo)** | é o que corresponde ao que você descreveu |

Quatro tentativas; as três primeiras erraram por medir **quantidade** de cor onde o sinal é
**identidade** de cor.

## 5. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, técnica) | **0,805** (3 sementes) — não depende de marcador |
| **compasso** | funciona onde a barline é limpa |
| **voz/cor** | mesma máquina do marcador de tempo (categoria de cor) — ainda não implementada |
| **tempo** | corrigido o diagnóstico: o sinal é **categoria de cor que muda**, não quantidade |

## 6. Próximo passo

Implementar a **categoria de cor por token** (6 baldes de matiz) e medir em `cifra club`:
quantos tokens mudam de categoria por instante? Se for 1–3 e a posição avançar ao longo do tempo,
o marcador está encontrado — e o mesmo dado entrega a **voz** de cada nota, que é item do goal.

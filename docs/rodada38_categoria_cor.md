# Rodada 38 — categoria de cor: melhora, mas ainda não isola o marcador

## 1. O que foi feito

Troquei a métrica de **quantidade** de cor por **categoria** de cor por token (vermelho, laranja,
verde, azul, sem-cor), e comparei cada token com a **sua própria base** (a categoria modal daquele
token ao longo do tempo).

## 2. Resultado

`cifra club / 505 - arctic monkeys`, 74 tokens, 8 instantes:

| cor de base (moda por token) | tokens |
| --- | --- |
| vermelho | **48** |
| sem-cor | 26 |

Isso confirma o que você descreveu: **nesse canal a tablatura é majoritariamente vermelha por
estilo**.

Tokens que mudam de categoria em relação à própria base:

| t | 0,40 | 0,44 | 0,48 | 0,52 | 0,56 | 0,60 | 0,64 | 0,68 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mudaram | 12 | 15 | 10 | 13 | 8 | 6 | 13 | 13 |
| colunas | 1,2,3,5,7,15,22 | 4,6,7,16,22 | 7,14,22 | 4,6,7,17,22 | 6,7,22 | 7,15,17,22 | 4,6,7,9,15,16 | 1,2,3,4,5,7,16,22 |

**Melhor que os 17–25 da rodada anterior, mas ainda 6–15 por instante — e sem padrão que avance no
tempo.** As colunas 7 e 22 aparecem em praticamente todos os instantes, o que sugere oscilação
(anti-aliasing ou token parcialmente colorido), não um marcador deslizante.

## 3. Conclusão honesta

**Não encontrei o marcador neste vídeo.** Duas possibilidades, e eu não sei qual é:

1. este vídeo **não** usa realce de cor como marcador (pode ser uma aula "simplificada" com tab
   estática colorida, e o marcador sendo outra coisa — banda, indicação na partitura, ou nada);
2. a região que eu analiso **não é a tablatura** — eu não conferi visualmente, e já errei isso uma
   vez nesta série (analisei o corpo do violão por oito rodadas).

## 4. A lição que se repetiu

Duas rodadas gastas inferindo o mecanismo **sem olhar o quadro**. Na rodada 33 eu descobri, olhando,
que o "cursor" era o violão — e prometi que faria a verificação visual primeiro. Não fiz: parti
direto para duas métricas (fração normalizada, depois categoria) sobre uma região que **não
verifiquei ser a tablatura**.

O passo certo, antes de qualquer métrica nova: **um quadro deste vídeo, com as caixas dos tokens
desenhadas**, para ver (a) se a região é mesmo a tablatura e (b) o que muda quando a música anda.
É uma imagem.

## 5. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, técnica) | **0,805** (3 sementes) |
| **compasso** | funciona onde a barline é limpa |
| **voz/cor** | a categoria de cor funciona e é barata (48 vermelhos / 26 sem-cor medidos) |
| **tempo** | **marcador ainda não identificado**; duas métricas tentadas sem verificação visual |

## 6. Próximo passo, e é um só

**Olhar um quadro do `cifra club` com os tokens desenhados**, avançar 2–3 quadros e ver o que muda.
Com isso, ou o marcador aparece, ou eu descubro que este vídeo não tem marcador — e nos dois casos
paro de construir métricas sobre suposição.

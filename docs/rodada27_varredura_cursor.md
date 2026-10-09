# Rodada 27 — varredura de janelas do cursor implementada (e o que ela achou)

## 1. O que foi implementado

`tools/transcrever.py` agora **varre o vídeo atrás das janelas em que o cursor está ativo**
(`varrer_cursor`), em vez de assumir cursor no vídeo inteiro. O JSON passou a declarar:

- `janelas_com_cursor`: lista de intervalos `[início, fim]` em segundos;
- `segundos_com_cursor`: total transcrevível com tempo.

Antes, quando não havia cursor, o produto devolvia tempo `None` **em silêncio**. Agora ele diz
explicitamente onde há e onde não há — que era a correção identificada na rodada anterior.

## 2. O que a execução mostrou

Vídeo `shin izumi / don't stop me now` (lido via **ffmpeg**):

| campo | valor |
| --- | --- |
| painel | base (passo 21,8 px) |
| notas | 57 |
| barlines | 12 |
| notas por compasso | `{1:6, 5:1, 7:13, 8:1, 9:7, 10:29}` |
| **janelas com cursor** | **[] (nenhuma)** |
| **segundos com cursor** | **0** de 150 s varridos |

Ou seja: neste canal, o `shin izumi`, **não há cursor detectável em 150 segundos**. Isso confirma
a medição da rodada anterior (0 % em `shin izumi`) e **não é falha do código**: a varredura
encontrou o que existe.

## 3. Leitura honesta

- A **geometria** funciona neste canal (57 notas, 6 cordas, painel localizado, confianças altas
  — 0,94 e 1,00 nas primeiras notas);
- o **tempo** não existe para este canal, e agora o JSON **avisa** em vez de omitir;
- o **compasso** segue não confiável aqui (`{1:6, 7:13, 10:29}`), como na rodada anterior —
  barline deste canal é fraca.

Consequência para o goal: o anexo de tempo **não é uma questão de código, é de cobertura por
canal**. Há canais em que o marcador simplesmente não aparece na tela (o professor não usa
playback), e nesses o tempo terá de vir de outra fonte — áudio ou numeração manual.

## 4. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura; cursor intermitente e ausente em parte dos canais |
| (b) gabarito verificado | 96 glifos / 4 canais |
| (c) classificador multi-classe | **0,805 (3 sementes)** |
| (d) pipeline ponta a ponta | comando único com **varredura de janelas** e aviso explícito de trecho sem tempo |
| (e) escala nos 3.781 | pré-requisito cumprido; rollout não iniciado |

## 5. Próximo passo

**Medir a cobertura de tempo no acervo amostrado**: rodar a varredura em 2–3 vídeos por canal e
somar `segundos_com_cursor`. Esse número responde, com dado, qual fração do acervo pode receber
tempo pelo cursor — e qual fração precisa de outra fonte. É a última medição grande que falta
antes de decidir o rollout.

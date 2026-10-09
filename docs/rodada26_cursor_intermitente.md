# Rodada 26 — o cursor é intermitente (e isso reconcilia 95 % com 50 %)

## 1. Medição refeita com alinhamento correto

Janela de rastreio começando **no mesmo instante** do quadro que define o painel (o erro da
rodada anterior), 2 vídeos por canal:

| | resultado |
| --- | --- |
| painel de tablatura | **24/24 = 100 %** |
| cursor detectável (>50 % dos quadros em 12 s) | **12/24 = 50 %** |

Por canal: **0 %** em `paolo d'angelo`, `shin izumi` e `tv on guitar`; **100 %** em
`raman korshun`, `tv cifras` e `violaodecria`; 50 % na maioria.

(Registro um defeito no meu próprio script: a coluna "s visível" saiu 71,7 s de 12 s — a condição
de amostragem por intervalo dispara em quase todo quadro, então o acumulador somou 0,2 s por
quadro. A *fração* de quadros com cursor continua válida, que é o que o veredito usa.)

## 2. Como isso convive com os 95 % do inventário

Não é contradição: **são duas perguntas diferentes.**

| medição | pergunta | resposta |
| --- | --- | --- |
| inventário (rodada 3) | "neste quadro, há cursor?" | 95 % |
| esta rodada | "nestes 12 s contínuos, o cursor está sempre ali?" | 50 % |

A leitura que explica os dois: **o cursor é intermitente.** Ele aparece durante a execução e
desaparece (ou fica parado fora da área) em intros, falas e trechos sem execução. O inventário
olhou um quadro — e teve sorte em 95 % deles; esta medição exigiu **12 segundos contínuos**, o
que é justamente o que o produto precisa.

## 3. Consequência para o produto

O anexo de tempo **não pode assumir cursor no vídeo inteiro**. O caminho correto é:

1. **varrer o vídeo** procurando janelas em que o cursor esteja ativo (o inventário mostra que
   elas existem em quase todo vídeo);
2. transcrever **por janela**, com o tempo medido só ali;
3. marcar no JSON os trechos sem cursor, em vez de silenciosamente omitir o tempo.

Isso também explica por que a execução do `transcrever.py` no `shin izumi` saiu sem tempo: aquele
canal está nos 0 % desta medição. O código devolveu `None` — que é o comportamento certo — mas o
rollout precisa procurar a janela ativa antes.

## 4. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura; cursor **intermitente** (95 % num quadro, 50 % em 12 s contínuos) |
| (b) gabarito verificado | 96 glifos / 4 canais |
| (c) classificador multi-classe | **0,805 (3 sementes)** |
| (d) pipeline ponta a ponta | comando único; **falta a varredura de janela ativa do cursor** |
| (e) escala nos 3.781 | pré-requisito cumprido; rollout não iniciado |

Próximo passo: implementar a **varredura de janelas com cursor ativo** no `transcrever.py` e medir
quantos minutos por vídeo são transcrevíveis. É o que decide a cobertura real do tempo no acervo.

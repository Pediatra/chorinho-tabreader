# Rodada 32 — passagens por sistema: falhou, e o padrão sugere outra causa

## 1. O que foi implementado

`passagens()` no `tools/transcrever.py`: divide x(t) em **passagens** — o cursor entra pela
margem esquerda e sai pela direita — para transcrever por **sistema** em vez de janela arbitrária.

## 2. Resultado: não funcionou

Vídeo `shin izumi / 3 easy songs`, 56 colunas de notas, série de cursor com 247+ amostras:

| | |
| --- | --- |
| passagens detectadas | **57** (é ruído, não sistema) |
| melhor passagem | 0–4 s, x 96–1181 |
| notas dentro da passagem | **2 de 36** |
| instantes distintos | **1** |

Um detector de sistemas que devolve 57 passagens num trecho está quebrado; e a "melhor" passagem
cobre 4 segundos de uma linha que tem 36 notas.

## 3. A hipótese que os números sugerem

Reunindo tudo o que medi em três rodadas:

- o cursor é detectado em **muitos quadros** (247 amostras em 180 s);
- mas produz **pouquíssimas posições distintas** (1 a 8 por vídeo);
- e as poucas posições **não formam varredura** (57 "passagens" sem sentido, x quase constante).

Isso é o comportamento de um **marcador que fica parado sobre a nota atual e salta de tempos em
tempos** — não o de uma banda que varre a pauta. Ou seja: minha detecção pode estar pegando
**o realce colorido da nota que está soando**, e não um cursor de playback.

Se for isso, as consequências são grandes e explicam tudo o que deu errado no tempo:

1. o "cursor" **não percorre a pauta**, então não existe travessia para medir;
2. o tempo teria de vir **do próprio realce**: a nota destacada *é* a nota soando naquele
   instante — o que é ainda melhor, pois dá o instante **por nota** sem interpolação;
3. e explica por que o `skyguitar` (que tem banda azul de verdade) funcionou e os canais de
   lição não.

## 4. Como confirmar (próxima rodada, primeiro item)

**Olhar os quadros** de um vídeo de lição com o realce detectado, marcando a caixa detectada sobre
a imagem, e verificar se é:

- uma **banda vertical** (cursor de execução) → travessia é o método certo; ou
- um **algarismo colorido** (nota soando) → o método é ler qual nota está destacada, por cor.

É uma verificação visual de um quadro, não um experimento longo — e decide o desenho do anexo de
tempo inteiro. Eu deveria ter feito isso na primeira rodada em que o tempo deu errado, em vez de
tentar três métodos de interpolação sobre um sinal que talvez não seja o que eu penso.

## 5. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura; 54 % com "cursor" (a redefinir) |
| (b) gabarito verificado | 96 glifos / 4 canais |
| (c) classificador multi-classe | **0,805 (3 sementes)** |
| (d) pipeline ponta a ponta | **anexo de tempo parado**: o sinal detectado pode não ser um cursor |
| (e) escala nos 3.781 | rollout rodado; tempos não utilizáveis |

## 6. Onde o projeto está, sem maquiagem

Três anexos, três estados diferentes:

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, técnica) | 0,805 medido em 3 sementes; pipeline robusto |
| **compasso** | funciona onde a barline é limpa; frágil nos canais de vídeo |
| **tempo** | **parado**, e possivelmente por eu estar lendo o sinal errado |

O reconhecimento — que era a minha maior preocupação na rodada 1 — está resolvido. O tempo, que eu
declarei "resolvido sem modelo" na rodada 2, é o que resiste.

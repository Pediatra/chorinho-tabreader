# Rodada 46 — o teste de cor não acha o laranja que a imagem mostra

## 1. O que eu esperava e o que saiu

Com a grade lida (**41 tokens, 16 colunas**) e o mecanismo confirmado em imagem (algarismos
brancos → laranja), rodei a série de cor em 13 instantes de 0,440 a 0,500:

| t | tokens laranja |
| --- | --- |
| 0,440 a 0,500 (13 instantes) | **0 em todos** |

**Zero.** Mas o recorte que eu li mostrava algarismos laranja com clareza — inclusive no mesmo
instante (t≈0,45) de onde eu tirei a grade.

## 2. A contradição, explicitada

| evidência | o que diz |
| --- | --- |
| imagem do recorte (rodada 40) | há algarismos **laranja** na tablatura |
| segmentação (rodada 45) | 41 tokens lidos na mesma região e instante |
| **teste de cor (esta rodada)** | **0 tokens laranja** |

Não podem estar os três certos. Como a imagem e a segmentação concordam (e eu vi a imagem), o
suspeito é o **teste de cor** — ou o **instante amostrado**.

Hipóteses, em ordem de probabilidade:

1. **o painel rola** entre os instantes: o recorte fixo (y 620–890) que funcionou em t≈0,45 pode
   apontar para outra parte da página em t=0,50, e aí os tokens lidos não são os algarismos;
2. **minha faixa de matiz/limiares** não pega o laranja real do canal (posso ter assumido um laranja
   "de livro" em vez do laranja daquele vídeo);
3. `ler_quadro` com frações próximas devolve quadros com **layout diferente** (troca de seção).

## 3. O erro de método é o mesmo de sempre

Eu **não desenhei a máscara de laranja sobre o quadro** para conferir. Fiz o teste, deu zero, e a
resposta certa — como nas rodadas 33 e 39 — está numa imagem: pintar os pixels que o teste considera
laranja e olhar se eles caem sobre os algarismos.

É a terceira vez que eu chego nesse ponto e a lição é a mesma: **quando uma medição contradiz o que
eu vi, eu confiro a medição numa imagem antes de teorizar.**

## 4. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, técnica) | **0,805** (3 sementes) nos 4 canais com gabarito |
| **localização do painel** | **resolvida** (uniformidade de fundo) |
| **geometria em painel escuro** | **resolvida** (6 cordas, passo 44,2, 41 tokens) |
| **tempo** | mecanismo confirmado em imagem; **teste de cor ainda não bate** — contradição registrada, causa não isolada |

## 5. Próximo passo (uma imagem, de novo)

1. pegar **um** quadro (t≈0,45), desenhar em verde os pixels classificados como laranja e em cima as
   caixas dos tokens, e **olhar**: o laranja cai nos algarismos ou em outro lugar?
2. se cair nos algarismos e o contador der zero, o erro é de índice/região no código;
3. se não cair, ajustar a faixa de matiz **medindo a cor real** dos algarismos laranja naquele quadro
   (imprimir a mediana de matiz/sat/val dentro de algumas caixas);
4. só então medir o avanço no tempo.

Sem essa conferência, qualquer número que eu reportar sobre tempo neste canal é chute — e eu já
gastei rodadas suficientes aprendendo que conferir a medição numa imagem é mais barato que teorizar
sobre ela.

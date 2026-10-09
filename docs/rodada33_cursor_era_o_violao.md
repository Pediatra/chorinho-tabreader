# Rodada 33 — a imagem mostra: o "cursor" detectado era o VIOLÃO

## 1. A verificação que eu devia ter feito há oito rodadas

Peguei o vídeo que produzia detecções (`guitar dell ́arte / 3 easy songs`), desenhei a caixa
detectada sobre o quadro e olhei.

**A caixa vermelha está sobre o corpo do violão.** A detecção tem **149 px de largura, matiz 16
(laranja) e saturação 85** — o madeirame do violão, não uma banda de cursor.

Para comparar, o cursor real medido na rodada 2 (`skyguitar`): matiz **109** (azul), núcleo de
**15–22 px**.

## 2. O erro que isso revela

Meu detector de cursor procura "coluna com muitos pixels coloridos e saturates". **Madeira de
violão satisfaz isso.** E o erro foi amplificado pelo painel:

- neste vídeo a notação está **embaixo**, mas a busca de painel escolheu a faixa `topo`;
- na faixa `topo` está o **vídeo do violão**;
- o detector então "achou um cursor" no meio da madeira.

## 3. O que isso invalida

| medição | situação |
| --- | --- |
| "54 % dos vídeos têm cursor" (rodada 28) | **não confiável** — parte pode ser violão |
| "247 amostras de cursor" (rodada 31) | **não confiável** — mesma causa |
| "cursor é intermitente" (rodada 26) | **provavelmente falso** — a intermitência pode ser o violão entrando e saindo da faixa |
| tempo por travessia / passagens | construídos sobre um sinal contaminado |
| cursor no `skyguitar` (rodada 2) | **válido** — lá eu vi a banda azul no quadro e validei o tempo com 1 nota/s |

Ou seja: o único canal em que o tempo foi validado de verdade (`skyguitar`) continua válido; **as
medições de cobertura nos canais de vídeo não são.**

## 4. A correção (duas travas, ambas simples)

1. **Rodar o detector de cursor só sobre o painel da notação** — e não sobre a faixa onde o painel
   foi encontrado por acidente. O painel precisa ser validado por conteúdo (a grade de 6 cordas),
   não pela primeira faixa onde algo colorido apareceu;
2. **Exigir assinatura de cursor**: banda **estreita** (≤ 60 px), aproximadamente **vertical**,
   atravessando a altura do painel, e com matiz de banda de playback (azul/pálido). Madeira é
   larga, laranja e não atravessa a pauta como uma régua.

Com essas duas travas, refazer as medições de cobertura — e só então dizer quantos vídeos têm
tempo.

## 5. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, técnica) | **0,805** (3 sementes); pipeline robusto em 7 canais |
| **compasso** | funciona onde a barline é limpa |
| **tempo** | **não medido**: as medições anteriores estavam contaminadas por madeira de violão |

## 6. A lição, dita sem enfeite

Oito rodadas atrás eu declarei o tempo "resolvido sem modelo", validando num canal, e construí
três métodos sobre esse sinal. **Uma olhada de um segundo no quadro teria evitado tudo isso.**
Foi a mesma falha que a variância do treino me mostrou: generalizei de uma amostra sem verificar
o que a amostra era.

O que sobra de sólido: a tablatura (0,805), a geometria (96 % do acervo), o inventário, e o
`skyguitar` — onde o tempo é real e verificado. O resto do tempo precisa ser remedido do zero.

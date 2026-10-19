# 1028 — Um braço só, consenso por vídeo, `r` em perspectiva e retreino com os ciclos

**Data**: 2026-10-18. **Estado**: regras a priori. Este documento ganha commit antes de qualquer
medida. **O dono aprovou o plano** ("a, pode seguir com o plano").

**Decisão do dono sobre o capotraste**: o dataset guarda a **casa real**, contada do nut, e a
posição do capotraste num campo separado. O nut fora da imagem nunca autoriza tratar o
capotraste ou o 1º traste como nut.

**Antecedente** ([1027](1027-ciclo-de-revisao-guitarous.md)): o ciclo funciona num canal novo,
com 2 de 64 falsos passando e 37,5 % sinalizados. Mas há três falhas nomeadas:
- tela dividida com dois violões;
- nut fora da imagem com capotraste (de onde vieram os 2 falsos que passaram);
- um quadro isolado errado, com os vizinhos certos.

## Partes

**P1. A tecla `r` em perspectiva** (só ferramenta).
- `prever_trastes` passa a usar o modelo projetivo do decodificador v2:
  t(n) = (a·s + b)/(c·s + 1), com s = 1 − 2^(−n/12).
- O nut é o ponto de b, e as 2 âncoras do dono fixam a e c.
- Sem nut, o modelo de 3 parâmetros (a, b, c) é ajustado com 3 âncoras. Com 2 âncoras e sem nut,
  a ferramenta recusa com uma mensagem clara.
- **Teste**: nos quadros da 1026 e da 1027 com nut e ≥ 4 trastes marcados pelo dono, a
  previsão a partir das âncoras 5 e 12 é comparada com os trastes do dono.
  - **Passa** com mediana ≤ 0,15 casa e pior caso (p90) ≤ 0,3 casa.
  - A regra antiga é reportada ao lado.

**P2. Um braço só** (decodificação do estágio 1).
- O mapa de presença (> 0,5) é dividido em componentes conexos. A decodificação conjunta da
  emenda 1 da 1025 roda **dentro de cada componente**: os candidatos são só os pontos daquele
  componente, alargado em 3 px.
- Ganha o componente com a maior soma. Se a diferença for < 5 %, ganha o de **cima**; em
  empate de altura, o da **esquerda** (a regra do dono).
- Com um componente só, nada muda.

**P3. Consenso por vídeo** (depois do estágio 2, entre os quadros do mesmo vídeo).
- Dois quadros são da **mesma tomada** quando as cordas 1 e 6 deles estão a ≤ 0,3 da largura do
  braço, uma da outra, e o eixo difere ≤ 3°.
- Dentro de uma tomada, os quadros **não sinalizados** formam a referência.
- Para cada quadro, os trastes dele são comparados com os da referência mais próxima, em casas,
  no espaço do braço.
- Um quadro cuja numeração difere da referência por um deslocamento inteiro k ≠ 0, com cada
  traste a ≤ 0,25 casa depois do deslocamento, recebe o **sinal S4** e é **sinalizado**.
- A correção automática (renumerar pelo k) fica para depois desta rodada. Agora o consenso só
  sinaliza.
- Um quadro sem referência na tomada fica como está.

**P4. Retreino**, com os mesmos hiperparâmetros e 3 sementes cada estágio.
- **Estágio 1** (`L3_todos_s1..3`): R + G + C + as marcas finais da 1026 e da 1027 (cordas e nut;
  com nut "fora", o quadro sai, como no C) + o N da 1025, menos os de 7 cordas.
- **Estágio 2** (`A4_100_todos_s1..3`): a mistura A3 da 1021 (S + R), com os R aumentados pelas
  marcas completas da 1026, da 1027 e do N, menos os de 7 cordas.
  - Os quadros com nut "fora" e `traste_referencia` entram no estágio 2: a faixa é recortada pela
    referência, e o nut do alvo fica ausente.
  - Se o código do estágio 2 não suportar nut ausente, esses quadros saem, e isso fica
    registrado.

## Medidas

**P2 e P3 com os pesos atuais** (L2_s1 e A3_s1), na 1026 e na 1027:
- é o que o ciclo teria entregue com P2 e P3;
- certos entregues, falsos que passam e sinalizados, antes e depois.

Estes quadros não estão no treino dos pesos atuais, então a comparação é limpa.

**P4**: os pesos novos **não** são medidos na 1026 nem na 1027, que agora estão no treino. A
medida deles é o próximo ciclo (1029), num lote novo de um canal fora do treino, com P1–P4
juntos.

| parte | passa se |
| --- | --- |
| P1 | mediana ≤ 0,15 casa e p90 ≤ 0,3 casa |
| P2 + P3 (1027) | falsos que passam ≤ 1 de 64, sem aumentar os falsos que passam na 1026 (0) |
| P2 + P3 (sinalizados) | só registro, porque o S4 aumenta os sinalizados de propósito |

Se P2 ou P3 piorarem algo na 1026 ou na 1027, a parte sai antes do ciclo 1029.

## Riscos declarados antes

- **8 quadros por vídeo, espalhados no tempo**, dão um consenso fraco. Num vídeo inteiro haverá
  centenas de quadros. Aqui a medida subestima o P3.
- **A regra de mesma tomada** foi fixada sem dado. Uma câmera que se move devagar pode quebrar a
  tomada em pedaços, e então o P3 só deixa de agir. Ele não erra por isso.
- **O nut fora da imagem continua sem solução própria** nesta rodada (vem depois, apoiado no
  P3). O P3 pode pegar os casos em que outro quadro da tomada mostra o nut.

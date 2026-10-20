# 1010 — Capotraste como nut do braço

**Data**: 2026-10-20. **Decisão do dono** ("pode mudar"), durante a revisão da
[1036](../rodadas/1036-ciclo-diagnostico-violaodecria.md).

## Contexto

Em 2026-10-18 (1027), o dono decidiu que o dataset guarda a **casa real**, contada do nut,
e a posição do capotraste à parte. O gabarito do braço seguiu a mesma regra: com capo, os
trastes eram contados do nut, e o capo ficava como um ponto (tecla `k`).

Isso pedia ao detector uma coisa que não serve ao casamento com a tab:

- **A tab da tela vem contada a partir do capo**, e é ela que gera o rótulo das mãos
  ([0011](0011-tablatura-vira-rotulo-da-base.md));
- **fisicamente, o capo é o nut**: a corda vibra a partir dele, e o detector vê uma barra
  atravessando as cordas;
- **nos cortes verticais, o nut verdadeiro quase sempre está fora da imagem quando há capo**;
- o "capo tomado por nut" já tinha aparecido na 1032 (q43).

## Opções

1. **Manter**: o detector numera do nut verdadeiro, e o capo é erro a sinalizar.
2. **Capo como nut no braço**: o detector numera a partir do capo. A casa real vira a
   casa relativa mais a casa do capo, um número por vídeo.

## Decisão

**Opção 2.**

- **No gabarito do braço**, com capo:
  - o nut marcado é **o traste logo à frente do capo** (do lado do corpo), onde a corda para
    de vibrar, e não o corpo do capo;
  - os trastes contam a partir dele (o traste 1 é o seguinte);
  - a tecla `k` marca o capo **no corpo dele**, para registrar que ali não é o nut de verdade;
  - a casa do capo vai na observação ("capotraste casa N").
- **No dataset**, nada muda: a casa real continua sendo o que se guarda
  ([1007](1007-formato-da-base-das-maos.md), `violao.capotraste`). Ela é a casa relativa mais
  `violao.capotraste`.
- O custo de mudar é baixo: nenhum gabarito anterior tinha capo marcado com `k`. Os
  capotrastes antigos, como os da [1008](1008-partes-do-violao-no-gabarito-do-braco.md),
  estão só em observação; são 14 quadros (ver Consequências).

## Consequências

- **Na medida**, com capo, o certo é o nut no capo. O detector que acha o nut verdadeiro
  atrás do capo erra, como no q10 da 1036.
- **Quando nut e capo aparecem juntos**, a regra é que a referência é a barra mais perto do
  corpo. O modelo precisa aprender isso com exemplos marcados.
- **A casa do capo é por vídeo, não por quadro.** Ela vem da tela, do título, ou do dono
  uma vez por vídeo. Se o capo muda no meio do vídeo, vale a marca por quadro.
- **Quadros antigos com capo na observação, contados do nut**: são 14. Antes de entrarem
  num treino ou numa escolha de pesos com esta regra, o dono precisa revê-los. Não se
  converte pela observação.

  | gabarito | quadros |
  | --- | --- |
  | `braco.json` (M3b) | q04, q10, q14, q42–q46 |
  | `braco_m11b.json` (usado na escolha de pesos) | q36–q39 |
  | `braco_m32.json` | q11, q43 |

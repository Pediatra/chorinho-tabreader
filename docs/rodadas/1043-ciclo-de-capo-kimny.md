# 1043 — Ciclo de capo: kimny's guitar (a prova lacrada da 1042)

**Data**: 2026-10-22. O pré-registro é commitado antes do sorteio.

**A pergunta**: num canal que o treino nunca viu, o detector da 1042 numera a partir do capo
sem deixar erro passar sem sinal?

**Por que um canal novo**: as marcas da 1039 (shin izumi) entram no treino da 1042, então a
1039 deixa de ser prova. O kimny's guitar não aparece em nenhuma amostra do braço, e é um caso
difícil: violão clássico, imagem em preto e branco, cabeça muitas vezes fora do quadro.

## Lote

1. **Triagem** (`python -m tab.maos.braco.ciclo triar --rodada 1043`): 40 vídeos do canal,
   sorteados entre os 98 livres, com um quadro no meio de cada um (`m43/triagem.jpg`).
2. **Marca de capo visto (feita, 2026-10-22, antes do sorteio)**: capo visível no quadro ou a
   legenda "Capo N flet" na tela em **5 de 40**: n.º 2 (capo 3), 5 (capo 4), 9 (capo 3), 16
   (capo 2) e 18 (capo 1), pela legenda. Ampliação em `m43/triagem_zoom.jpg`. Não é rótulo,
   só a escolha da amostra; quem confirma o capo é o dono.
3. **Sorteio** (`sortear --rodada 1043`, semente 20261043): como há menos de 8 vídeos com
   capo, o lote fica com **os 5, com 8 quadros cada: 40 quadros** (a regra da 1039).

## Detector do pré-preenchimento

- **O par da 1041** (`L5_capo3_s2` + `A7_capo3_s2`), com a regra 1023 e o sinal v2. É o
  melhor no capo até aqui, e poupa trabalho do dono.
- A 1042 **não** preenche o lote: o par dela prevê o lote sem ver o gabarito, e ninguém
  compara a previsão com o gabarito antes da revisão do dono.

## O que o dono faz

O protocolo da 1039: braço `x` (sim) em cada quadro; com capo, o nut no traste à frente do
capo, o `k` no capo e a casa na observação ("capotraste casa N"); nut fora com o traste de
referência; 7 cordas com o botão.

## Medidas

São as do ciclo (`ciclo medir --rodada 1043`) para o par da 1041, e os critérios da 1042 para
o par dela. O critério está no [pré-registro da 1042](1042-retreino-com-a-1039.md).

## Resultado (2026-10-23)

O dono revisou os 40 quadros (39 com capo). O par da 1041 entrega 1 certo, 1 falso que passa e
sinaliza 38; o da 1042, 1 certo, 2 falsos que passam e 37 sinalizados. A medida e os critérios
estão no [resultado da 1042](1042-retreino-com-a-1039.md#resultado-na-prova-1043-revisada-pelo-dono-em-2026-10-23).
A prova fica **gasta para os pares da 1041 e da 1042**. Ela continua sem uso para escolher
qualquer coisa de métodos novos, mas o agente viu os erros dos quadros q01–q10 (folha
`m43/erros_parcial.jpg`), e isso fica declarado.

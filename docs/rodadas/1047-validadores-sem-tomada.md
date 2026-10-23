# 1047 — Confirmar a cadeia da 1044 sem a tomada (validadores + tentativas) num lote lacrado

**Data**: 2026-10-23. O pré-registro é commitado antes do sorteio.

**A pergunta**: os validadores físicos e as 22 tentativas (partes A e B da 1044), **sem** a
tomada (parte C), entregam pelo menos os certos do par antigo, sem os erros calados dele?

**Por que** ([1044](1044-validadores-tentativas-e-tomada.md#resultado-2026-10-23)): na M44, a
cadeia completa zerou os falsos que passam (0 contra 4), mas perdeu 8 certos, 6 deles pela
tomada. Sem a tomada, a conta feita **depois** de ver a prova deu 18 certos e 0 falsos, os
mesmos certos da referência. Por ter sido vista depois, essa conta não decide nada; esta
rodada a confirma num lote novo.

## O que muda em relação à 1044

- **A cadeia é a da 1044, congelada** (commit da 1044 e deste pré-registro): as mesmas
  faixas (`m44/faixas.json`), os mesmos 11 pares × original/espelho, a mesma regra da B (≥ 2/3
  das hipóteses válidas e ≥ 6), **sem a parte C**.
- **O lote é pré-preenchido pela própria cadeia** (`validadores_gpu preencher --rodada 1047`):
  é o que entraria no ciclo. A referência (o par antigo no quadro original) é uma das 22
  hipóteses e é medida nos mesmos quadros.

## Amostra: M47, lacrada

- 40 quadros: **1 vídeo de cada um de 8 canais, 5 quadros por vídeo**, entre os vídeos que não
  estão em nenhum gabarito do braço nem nas amostras de treino. Semente 20261047.
- Os 8 canais são os com menos quadros respondidos no gabarito do braço (contados depois da
  M44) que têm vídeo livre: rostheo guitar (5), guitar dell'arte (8), lonelypicker (9), mr.
  tabs (9), robert lunn (9), paolo d'angelo (11), serge kottelat (11) e iwaki (12, empate com
  leonardo ramos desfeito pela ordem alfabética). O raman korshun está descartado do
  gabarito.
- Ninguém compara a previsão com o gabarito antes de o dono terminar a revisão.

## Medida

Os mesmos critérios da 1044, contra o par antigo nos mesmos quadros:

| critério | o que precisa |
| --- | --- |
| **1. Segurança** | falsos que passam ≤ os da referência, e ≤ 5 % dos medidos |
| **2. Ganho** | entregues certos ≥ os da referência (aqui o pedido é **não perder**: a cadeia entra como segurança, não como ganho) |
| **3. Não estragar** | dos quadros que a referência entrega certos, no máx. 1 sai falso que passa |

- **Emenda declarada antes de medir**: o critério 2 da 1044 pedia referência + 4. Aqui a
  pergunta é outra (a cadeia substitui o par antigo no ciclo sem perder certos), e por isso
  o critério 2 é "≥ referência". Isso fica escrito antes do sorteio.
- Também reportados: falsos que passam e certos por canal, hipóteses válidas por quadro e
  reprovações por validador.

| resultado | o que fazer |
| --- | --- |
| 1, 2 e 3 passam | a cadeia (A + B, sem C) vira a cadeia do ciclo sem capo |
| 1 e 3 passam, 2 falha | entra só como sinal sobre o par antigo (sinaliza o que a cadeia recusa) |
| 1 ou 3 falha | não adotar; olhar por validador |

## Resultado (2026-10-23): passa nos três critérios

M47 revisada pelo dono: 40 quadros, 35 com braço (5 com capo), 5 sem braço
(`m44/hipoteses/1047/medida.json`).

| | certos entregues | falsos que passam | sinalizados |
| --- | --- | --- | --- |
| referência (par antigo) | 18 | 3 | 19 |
| cadeia (A + B, sem a tomada) | **20** | **0** | 20 |

- **Critério 1: passa** (0 contra 3). **Critério 2: passa** (20 ≥ 18). **Critério 3: passa**
  (0 dos 18 certos da referência viraram falso).
- **Por canal** (certos / falsos que passam, cadeia contra referência): rostheo 5/0 e 5/0;
  lonelypicker 2/0 e 0/2; robert lunn 1/0 e 0/0; paolo d'angelo 5/0 e 5/0; serge kottelat
  2/0 e 1/0; iwaki 5/0 e 5/0; mr. tabs 0/0 e 2/1; guitar dell'arte 0/0 nos dois.
- **Resultado: a cadeia (validadores + 22 tentativas, sem a tomada) vira a cadeia do ciclo
  sem capo.** Com capo, ela só sinaliza (1043); o capo espera a 1045.
- Somando as duas provas lacradas (M44 + M47, 76 medidos), sem a tomada: 0 falsos que passam
  contra 7 da referência. (A M44 sem a tomada foi conta depois de ver; a M47 é a confirmação.)

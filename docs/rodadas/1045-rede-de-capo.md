# 1045 — Uma rede que acha o capo na faixa do braço, e o nut pela conta

**Data**: 2026-10-23. O pré-registro é commitado antes de qualquer treino.

**A pergunta**: uma rede pequena, treinada só para achar o capo (um objeto grande, que cruza
as seis cordas), acha o capo em canais que nunca viu? Com o capo achado, o nut sai pela conta
da 1046 (o traste logo antes do capo, do lado do corpo, decisão 1010), em vez de a rede do
braço adivinhar qual traste é o nut.

**Por que**: os retreinos que ensinavam o nut com capo reprovaram canal a canal (1041, 1042);
o detector aberto não localiza o capo (1046: a caixa cobre 75–99 % do quadro). A cadeia da
1047 é segura sem capo, mas com capo só sinaliza (1043: 0 certos de 40).

## A rede

- **Entrada**: a faixa retificada do braço (1024 × 192, a mesma do estágio 2), do nut
  verdadeiro até o corpo. **Saída**: um mapa, com uma crista no segmento entre as cordas 1 e 6
  na posição do capo (o ponto `k` do dono). Quadro sem capo: mapa vazio.
- **Arquitetura**: a U-Net do estágio 2 (ResNet18 ImageNet, já no disco) com 1 canal de saída.
  Nenhum download.
- **No treino**, a faixa sai das marcas do dono com o começo nas pontas das cordas do lado da
  cabeça (com capo, o dono marca as cordas até o nut verdadeiro), com o erro de eixo sorteado
  do `faixa.perturbar` e os aumentos do estágio 2 (cor, desfoque, JPEG, espelho vertical).
- **Na previsão**, a faixa sai das marcas previstas pelo par antigo. O capo é visto quando o
  pico do perfil (média do mapa entre as cordas, por coluna) passa do limiar.
- **3 sementes**, `C1_capo_s{1,2,3}`, mesmo número de passos.

## Dados

| papel | gabaritos | capo | sem capo |
| --- | --- | --- | --- |
| **treino** | todos os `braco*.json` menos os abaixo | ~110 (kenneth, guitarous, violaodecria, vvxo, serge) | o resto com braço `sim` e marcas completas |
| **escolha (dev)** | M39 (shin izumi) e, sem capo, M29 + M44 | 64 | 89 |
| **prova** | 1043 (kimny's guitar) e M47 (8 canais) | 39 + 5 | 1 + 30 |

- Nenhum quadro de um vídeo da escolha ou da prova entra no treino. Os canais kimny's guitar e
  lonelypicker (os capos da prova) não têm capo no treino.
- Risco declarado: nos gabaritos antigos, um quadro com capo sem a marca `k` vira exemplo
  negativo errado (a decisão 1010 mandou rever 14 deles). Os gabaritos sem nenhum `k` (M26,
  M29) são de canais sem capo.

## Escolha (só no dev)

- **Limiar** de cada semente: o menor em que o capo é visto em ≤ 1 dos 89 sem capo do dev.
- **Achado**: o capo previsto a ≤ ½ casa do `k` do dono, ao longo do braço.
- **Semente**: a que mais acha na M39 com o seu limiar; empate, a menor semente.
- **Parada**: se a escolhida acha < 70 % da M39 (45 de 64), a rodada para sem prova.

## A cadeia medida

Para cada quadro, a da 1047 (validadores + 22 tentativas, sem tomada), mais:

1. a rede de capo na faixa do par antigo;
2. capo visto → o nut pela conta da 1046 sobre as marcas do par antigo; o resultado passa
   pelos validadores da 1044 e é **sinalizado** se reprovar, se o par antigo sinalizou, ou se
   o pico está entre o limiar e o limiar + 0,1;
3. capo não visto → a saída da 1047 como está.

## Prova

| critério | onde | o que precisa |
| --- | --- | --- |
| **1. Segurança** | 1043 | falsos que passam ≤ 2 de 40 |
| **2. Ganho** | 1043 | entregues certos ≥ 20 de 40 (a cadeia da 1047 deu 0; o par da 1041, 1) |
| **3. Capo falso** | M47, os 30 sem capo com braço | capo visto em no máx. 1 |
| **4. Não estragar** | M47 | falsos que passam ≤ os da cadeia da 1047 (0) + 1, e certos ≥ os dela − 1 |
| registro | 1043 e M47 | capo achado (≤ ½ casa do `k`), casa do capo pela conta contra a do dono, por vídeo |

- A 1043 foi vista pelo agente (q01–q10) e medida para outros métodos, mas nunca usada para
  escolher nada desta rede. A M47 foi medida na 1047 e não escolhe nada aqui.

| resultado | o que fazer |
| --- | --- |
| 1 a 4 passam | a rede de capo entra na cadeia do ciclo |
| 1, 3 e 4 passam, 2 falha | olhar onde perdeu: capo não visto, ou conta errada perto do capo |
| 1, 3 ou 4 falha | não adotar; olhar por tipo de erro |

## Resultado (2026-10-23)

**Treino** (`artefatos/m21/C1_capo_s{1,2,3}`, 1.500 passos, ~5,5 min cada): perda final 0,154,
0,138 e 0,221.

**Escolha** (`m45/escolha.json`; limiar com ≤ 1 capo falso em 89 sem capo):

| semente | limiar | capos achados na M39 |
| --- | --- | --- |
| **1** | 0,172 | **47 de 64 (73 %)** |
| 2 | 0,191 | 41 de 64 |
| 3 | 0,251 | 28 de 64 |

A semente 1 passa dos 70 % e segue para a prova.

**Prova** (`m45/medida.json`):

| critério | resultado |
| --- | --- |
| 1. Segurança (1043) | **passa**: 1 falso que passa (a 1047, 2) |
| 2. Ganho (1043) | **reprova**: 3 certos entregues (exigido 20; a 1047, 0) |
| 3. Capo falso (M47) | **passa**: 0 em 30 sem capo |
| 4. Não estragar (M47) | **passa**: 20 certos e 0 falsos, iguais à 1047 |

- **Resultado: "1, 3 e 4 passam, 2 falha"**: olhar onde perdeu.
- **Onde perdeu (1043, 39 com capo)**: o capo **não foi visto em 28**; visto em 11, dos quais
  2 sem traste para a conta, 4 reprovados pelos validadores e 5 válidos (3 entregues certos).
  Capo achado a ≤ ½ casa do `k`: 9 de 39. No lonelypicker (M47): 5 de 5.
- **Por vídeo** (folha `m45/diag_kimny.jpg`, depois da medida): em 2 dos 5 vídeos o capo nunca
  é visto (câmera de baixo, capo escuro e coberto pela mão); num vídeo o estágio 1 achou outra
  coisa (q09, faixa sem braço). Quando o capo aparece claro (q13, q25, q27, q29), a rede o
  acende com nota 0,96–0,99.
- **Leitura**: a rede acha o capo visível em canal novo (lonelypicker 5/5, kimny com nota alta
  quando aparece), mas o kimny tem o capo escondido na maior parte dos quadros. O capo não se
  move no vídeo: o que falta é levar o capo visto num quadro aos outros do mesmo vídeo.

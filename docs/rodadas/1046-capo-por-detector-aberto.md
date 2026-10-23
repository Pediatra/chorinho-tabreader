# 1046 — Achar o capo com um detector aberto (Grounding DINO) e pôr o nut pela conta

**Data**: 2026-10-23. O pré-registro é commitado antes de qualquer medida.

**A pergunta**: um detector aberto, sem treino, acha o capo nos nossos vídeos? E, com o capo
achado, o nut com capo sai certo por uma regra fixa, em vez de a rede adivinhar?

**Por que**: os retreinos de capo reprovaram canal a canal (1041 na 1039, 1042 na 1043). Nos
39 quadros com capo da 1043, o par da 1042 pôs o nut no nut verdadeiro em 17 e no capo em 7: a
rede acha bem trastes e cordas, e erra só **qual** traste é o nut. A regra do dono (decisão
1010) é fixa: o nut é o traste logo antes do capo, do lado do corpo.

## O detector

- **Grounding DINO tiny** (`IDEA-Research/grounding-dino-tiny`, revisão `a2bb814d`, Apache-2.0),
  por `transformers==5.19.0` na imagem das mãos (`Dockerfile.maos`), com o aval do dono para o
  download (2026-10-23). Pesos com sha256 `1a2412ef…042f3`. O build confere que torch, numpy e
  cv2 não mudaram.
- Sem treino. A entrada é o quadro inteiro, com um texto.

## A cadeia

1. **Capo**: o Grounding DINO com o texto escolhido no desenvolvimento (abaixo). Entre as
   caixas, fica a de maior nota que cruza o braço previsto (as cordas 1 e 6 do par antigo
   passam pela caixa). Nota abaixo do limiar = "sem capo visto".
2. **Trastes**: o par antigo (`L3_todos_s3` + `A4_100_todos_s1`, treinado com o nut
   verdadeiro).
3. **Nut pela conta**: com capo visto, o nut é o traste do par antigo mais próximo do capo do
   lado do corpo, a no máximo 1 casa do centro da caixa ao longo do eixo; os trastes são
   renumerados a partir dele. Sem traste nessa janela, o quadro é sinalizado.
4. **Sinal**: valem a regra 1023 e o sinal de nut v2 do par antigo. Um quadro com capo visto e
   nota entre o limiar e o limiar + 0,1 é sinalizado (capo duvidoso).

## Escolhas no desenvolvimento (antes da prova)

- **Amostras de desenvolvimento**: a 1039 (64 quadros com capo, shin izumi) e os quadros sem
  capo dos gabaritos revisados (1026–1036, M36, N). Já vistos; servem só para escolher.
- **Texto**: entre "capo", "guitar capo" e "guitar capo . guitar nut . hand", o que acha mais
  capos da 1039 (a caixa contém o `k` do dono).
- **Limiar**: o menor em que o capo aparece em ≤ 2 % dos quadros sem capo do desenvolvimento.
- Se, com esse limiar, o capo não aparece em ≥ 70 % da 1039, a rodada para aqui, sem prova:
  o detector aberto não serve sem treino.

## Prova: a 1043

- 40 quadros do kimny's guitar, 39 com capo, revisados pelo dono. Ela está gasta para os pares
  da 1041 e da 1042, mas é nova para este método. O agente viu os erros de q01–q10 (declarado
  na 1043), e nada da 1046 é escolhido nela.
- Os quadros sem capo da M44 (a prova da 1044), depois da revisão do dono, contam no critério
  do capo falso.

| critério | onde | o que precisa |
| --- | --- | --- |
| **1. Segurança** | a 1043 | falsos que passam ≤ 2 de 40 (5 %) |
| **2. Ganho** | a 1043 | entregues certos ≥ 20 de 40 (o par da 1041 deu 1) |
| **3. Capo falso** | os quadros sem capo da M44 | capo visto em no máx. 1 |
| registro | a 1043 e a 1039 | capo achado (a caixa contém o `k`), casa do capo pela conta contra a do dono, por vídeo |

| resultado | o que fazer |
| --- | --- |
| 1, 2 e 3 passam | o ciclo com capo passa a usar esta cadeia; o retreino de capo (1045) sai da fila |
| 1 e 3 passam, 2 falha | ver onde perdeu: capo não achado, ou traste errado perto do capo |
| 1 ou 3 falha | não adotar; ver os quadros por tipo de erro |

## Riscos declarados antes

- A pestana com o dedo indicador parece um capo. O texto com "hand" e a exigência de a caixa
  cruzar o braço tentam separar os dois; o critério 3 mede.
- Com a mão na frente, o traste logo antes do capo pode não ser achado pelo par antigo.
- O par antigo inverte o braço em alguns vídeos verticais (1041); aí a conta erra junto.

## Resultado (2026-10-23): para no desenvolvimento, sem prova

`m46/escolha.json` (as caixas em `m46/<rodada>/caixas.json`, 7 rodadas, ~22 min de GPU):

| texto | limiar (≤ 2 % dos 192 sem capo) | capos achados na 1039 |
| --- | --- | --- |
| "capo." | 0,499 | **18 de 64** |
| "guitar capo." | 0,853 | 0 de 64 |
| "guitar capo. guitar nut. hand." | 0,675 | 0 de 64 |

- O melhor texto acha 18 de 64 (28 %), abaixo dos 70 % exigidos. **Pela regra, a rodada para
  aqui e a 1043 não é medida.**
- **Por quê** (diagnóstico depois da parada, `m46/diag_dev.py`): a melhor caixa "de capo" tem
  em mediana **75 % a 99 % da largura do quadro**, com ou sem capo. O Grounding DINO tiny não
  localiza o capo: ele encaixa o violão (ou a pessoa) inteiro e chama de "capo". Uma caixa
  contendo o `k` do dono existe nos 64 quadros, mas só porque a caixa cobre o braço todo; os
  18 "achados" são esse mesmo efeito, e não acerto.
- **Conclusão**: sem treino, o detector aberto não serve para o capo. O capo precisa ser uma
  saída aprendida (um canal de capo no estágio 2, com os ~200 pontos `k` do dono e o
  sintético com capo), com o nut pela conta da 1046.

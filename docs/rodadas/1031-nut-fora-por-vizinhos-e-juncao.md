# 1031 — Nut fora da imagem: numeração pelos vizinhos e pela junção braço-corpo

**Data**: 2026-10-19 (pré-registro feito antes da janela autônoma de 2026-10-20). **Estado**:
regras a priori. **As ideias são do dono**:
- "ele aparece em quadros vizinhos, então pode ser criada uma referência e repassada";
- "a casa 12 em violões de nylon está sempre na divisão com o braço e o corpo, e quando é de aço
  é a casa 14".

## Pergunta

Com o nut fora da imagem, o detector toma o 1º traste como nut, e a numeração desloca
exatamente 1 casa, sem sinal. Esse erro foi visto em 4 quadros na 1029 e em 2 na 1027. Uma
referência de outro lugar (o quadro vizinho ou a junção) corrige ou sinaliza esse erro, sem
estragar os quadros certos?

## Casos (desenvolvimento)

**Com nut "fora" e `traste_referencia` do dono**:
- 1027: 8;
- M11b: 1 (q34);
- 1029: 4 (q19, q20, q24 e q46; o q50 ficou de fora, porque o dono não tem confiança);
- 1031: 3 (q13, q14 e q15).
- Total: **16**.

**Controle**: os quadros revisados com o nut visível nos mesmos vídeos. O método não pode
renumerar nenhum deles para errado.

## Métodos (sem treino novo)

**V. Vizinhos.**
- O vídeo inteiro roda a 2 quadros/s. O pré-requisito é rodar inteiros os vídeos da 1029 e da
  M11b que ainda faltam.
- Para cada quadro, procura-se o quadro mais próximo no tempo, a até 30 s, em que o nut é
  **visível com confiança**:
  - a ponta das cordas do lado do nut fica a mais de 5 % da borda;
  - e o quadro não é sinalizado.
- Entre os dois quadros, os trastes são **seguidos quadro a quadro**: cada traste vai para o
  vizinho mais perto, no espaço do braço normalizado pelas cordas.
  - Isso só vale se ≥ 3 trastes casarem a ≤ 0,25 do espaço local em todo o caminho.
  - Se o caminho quebrar, não há decisão.
- A numeração do quadro com o nut é levada até o quadro sem nut, e o deslocamento k é obtido
  como na 1030, só que pelo caminho seguido.

**J. Junção.**
- **Detectar a junção**: é a posição, ao longo do braço, em que a faixa das cordas encontra o
  corpo, ou seja, onde a borda do braço se alarga.
  - O detector é escrito nesta rodada. Ele é uma regra sobre a imagem, sem treino.
- **Aprender o número da junção no próprio vídeo**: nos quadros com o nut visível com confiança
  e com a junção detectada, o traste mais perto da junção recebe o número dado pelo nut.
  - O número do vídeo é a moda desses quadros.
  - Só vale se for 12 ou 14 e se ≥ 70 % dos quadros concordarem.
- **Contagem de trastes com folga**: só entra quando o vídeo nunca mostra o nut.
  - Com ≤ 18 trastes, a junção é a 12; com ≥ 21, é a 14.
  - Com 19 ou 20, não há decisão.
- **No quadro sem nut**: o traste da junção recebe o número do vídeo, e os outros são numerados
  a partir dele.

**Combinação V+J**:
- se os dois decidem e **concordam**, vale o resultado;
- se **discordam**, o quadro é sinalizado;
- se só um decide, vale esse;
- se nenhum decide, o quadro é sinalizado quando o nut é suspeito (a regra de borda da 1030,
  só como sinal).

## Medida e critério

Em cada caso, compara-se o número dado pelo método ao traste de referência do dono:
- **acerto**;
- **recusa** (sinalizado);
- **erro não sinalizado**.

No controle, conta-se quantos quadros certos ficam errados.

| resultado | o que fazer |
| --- | --- |
| 0 erros não sinalizados nos 16 casos, 0 certos estragados no controle e ≥ 8 acertos | o método vai ao ciclo do kenneth acoustic (1032) |
| senão | o ciclo 1032 sai com o detector atual, e os quadros com o nut suspeito vão para revisão como sinal |

## Também nesta janela

- **A5**: o estágio 2 retreinado com os quadros de nut "fora".
  - Hoje o A4 os exclui (`nut_fora_excluido: 8`).
  - A faixa é recortada a partir da referência do dono, e o alvo do nut fica ausente.
  - São 3 sementes, com o resto igual ao A4.
  - A medida é na M11b e nos 16 casos de nut fora, só como desenvolvimento.
- **1032**: o ciclo do kenneth acoustic (escolha do dono). São 8 vídeos e 64 quadros, com o
  protocolo da 1029 e o melhor detector e método desta rodada.

## Riscos declarados antes

- **16 casos** dão a direção, não uma taxa. E 11 deles vêm do guitarous.
- **A junção** é escondida pela mão nas posições altas, e o cutaway deixa a junção ambígua.
  Nesses casos, o método tem de recusar.
- **Os vizinhos** dependem de o vídeo mostrar o nut em algum momento perto do quadro. Num vídeo
  que nunca mostra o nut, só a junção pode ajudar.

## Emenda 1 (2026-10-20, antes de ver o resultado de qualquer método nos casos)

**Vídeos inteiros e detector**:
- Os quatro vídeos dos casos rodam inteiros, a 2 quadros/s, com o **detector do ciclo 1029**
  (`L3_todos_s3` + `A4_100_todos_s1`), que é o que vai à 1032:
  - "cuando te dicen…" e "lágrima" (1029);
  - "valsa sem nome" (M11b, q34);
  - マリーゴールド solo (1027 e 1031).
- O マリーゴールド **roda de novo**. Na Parte A da 1030 (pesos antigos), o braço só foi achado
  em 28 de 248 quadros, e os 8 casos da 1027 ficavam quase todos sem par denso.
  - Esse vídeo está no treino da `L3`/`A4` (marcas da 1027). Isso é desenvolvimento, não prova.
- Código: `tab/maos_braco_nut_fora.py` (`videos`, `medir`), `tab/maos_braco_vizinhos.py` (V) e
  `tab/maos_braco_juncao.py` (J).

**Regra J, fixada no desenvolvimento**:
- O desenvolvimento usou os vídeos da 1030 **sem casos** (v01 a v16, menos o v15), só nos
  quadros com o nut visível com confiança.
- A faixa do braço é retificada. Por fora da escala, de 0,6 a 0,9 largura do eixo, de cada
  lado, lê-se a cor média (Lab) de cada coluna. A junção é o ponto de mudança desse sinal: o
  corte em dois segmentos com a menor soma de quadrados.
  - A busca vai do traste 5 do detector ao último traste.
  - A junção conta como achada com contraste ≥ 3.
  - O traste da junção é o traste previsto mais perto do corte.
- O que o desenvolvimento mostrou (`m31/dev_j.json`):
  - **Vídeos com número consistente**: v02, v05, v06 e v08 dão 12 em 96 a 100 % dos quadros;
    o v07 dá 12 em 72 %; o v09 (aço) dá 14 em 100 %.
  - **Vídeos rejeitados** (moda fora de 12 ou 14, ou concordância < 70 %): v01, v03 e v04 dão
    **13** de forma estável. É um violão clássico; a curva do bojo põe o corte 1 traste
    depois. Os v10, v12 e v13 dão mão ou braço (7 a 11).
  - Nesses vídeos, o J não decide, e isso é recusa.
- **Tentativas descartadas no desenvolvimento**:
  - bandas mais longe (0,65 a 1,4 largura): mesmo 13 nos v01, v03 e v04;
  - busca a partir do traste 9: o v06 caiu de 99 % para 57 %.

**Leitura dos casos, fixada agora**:
- Cada caso recebe o quadro denso a até 0,25 s.
- O número do método é o do traste previsto mais perto do ponto de referência do dono, desde
  que esteja a até 0,5 do espaço local. Se não estiver, é "sem número".
- Classes de um caso, por modo (`sozinho`, `V`, `J`, `VJ`):
  - **acerto**: número certo e quadro não sinalizado;
  - **acerto sinalizado**: número certo, mas o quadro vai à revisão;
  - **recusa**: sinalizado e sem número certo (inclui braço não achado);
  - **erro não sinalizado**: número errado e quadro não sinalizado.
- O critério conta como acerto só o **acerto não sinalizado**, porque é o que o ciclo entrega
  sem revisão.
- Nos modos V e J sozinhos, um quadro sem decisão (k vazio) é sinalizado. No V+J vale a regra
  da combinação.
- **Controle**: os quadros revisados dos mesmos vídeos, sem nut fora e com marcas completas.
  - "Estragado" é o quadro certo no detector sozinho que deixa de ser certo no modo.
  - O critério exige 0 estragados.

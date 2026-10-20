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

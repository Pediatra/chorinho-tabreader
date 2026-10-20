# 1034 — Conferência da numeração pelas marcações do braço (desenvolvimento)

**Data**: 2026-10-20 (janela autônoma). **Estado**: regras a priori, escritas antes de medir.
Esta rodada é **só de desenvolvimento**.

## Por quê

O único falso que ainda passa depois do sinal v2 da [1033](1033-sinal-de-nut-suspeito-v2.md) é o
1027:q56. Nele, o detector toma o 1º traste depois do capo como nut.

No quadro, as marcações do violão de aço ficam **um espaço antes** do esperado:
- a da casa 7 cai entre os trastes 5 e 6 do detector;
- a da casa 12, entre o 10 e o 11.

O padrão das marcações (5, 7, 9, 12, 15 e 17) é uma âncora absoluta, porque o salto de 3 entre a
9 e a 12 fixa a numeração.
- Isso vale mesmo quando o violão tem marcação dupla também na 7, como os do guitarous.
- Violão clássico não tem marcação, e aí a regra não decide.

## Regra (fixada agora)

1. A faixa do braço é a da regra J (`faixa_do_quadro`). Na escala, entre corda1 e corda6, tiram-se
   as cordas e os trastes com aberturas morfológicas: uma linha horizontal e uma vertical,
   ambas de 25 px. O que sobra de claro, que é a marcação, vira um sinal.
2. **Cada espaço entre trastes vizinhos do detector** (n−1, n) recebe a pontuação do máximo
   desse sinal no meio do espaço (60 % do centro). Um espaço tem marcação se a pontuação for
   ≥ 4 vezes a mediana das pontuações dos espaços do quadro e ≥ 20 níveis de cinza.
3. **O padrão** é P = {3, 5, 7, 9, 12, 15, 17}, a casa de cada marcação.
   - Para cada k em {−2, …, 2}, contam-se os espaços marcados n tais que n + k está em P, e
     também os que não estão.
   - O k aceito é o de mais acertos, com 0 erros.
   - Ele exige ≥ 3 marcações, entre elas uma em 12 + k, ou o par 9 + k e 12 + k.
   - Sem isso, não há decisão.
4. **Sinal**: o quadro é sinalizado se o k aceito for diferente de 0.

## Medida e critério

**Dados**: os ciclos 1026, 1027 e 1029 (com o rótulo do dono) e a 1032 (só a contagem de
disparos).

**Contagens**:
- quantos dos 6 falsos que passaram o sinal pega;
- quantos dos 150 certos não sinalizados ele dispara;
- em quantos quadros ele decide.

| resultado | o que fazer |
| --- | --- |
| pega o 1027:q56 e dispara em ≤ 3 % dos certos | proposto para o ciclo seguinte à 1032, junto com o v2 (a 1032 já está com o dono e não muda) |
| senão | fica registrado; nenhum ciclo muda |

## Riscos declarados antes

- A **mão e o reflexo** fazem manchas claras.
- **Kenneth** usa pontos pequenos, alguns quase invisíveis. Muitos quadros vão ficar sem
  decisão, o que é seguro.
- Os 6 falsos já foram vistos: é direção, não prova.

## Resultado (2026-10-20; `m31/medida_1034.json`) — **reprova**

- **Falsos**: o sinal pega 0 de 6. Nenhum deles teve marcação detectada.
- **Certos**: a regra decide em 6 dos 150 certos, todos com k = 0, e não dispara em nenhum.
- **1032**: decide em 16 de 64, sem disparo.
- O 1027:q56 não é pego, e por isso a regra não vai a ciclo.

**Por quê** (diagnóstico depois da medida, `m31/dbg_1034.py`; não muda o resultado):
- No 1027:q56, as marcações **são detectadas** no resíduo. Os espaços 6, 8 e 11 do detector
  pontuam 190, 193 e 212, contra cerca de 20 nos espaços vazios. Isso é exatamente 7, 9 e 12
  com k = +1.
- Mas os espaços sobre o corpo (13 a 19) pontuam de 124 a 176, porque o tampo claro aparece na
  borda da escala.
- Isso sobe a mediana (cerca de 100), e o limiar de 4 × mediana apaga tudo. No 1027:q10, a mão
  faz o mesmo nos espaços 2 a 4.
- **Proposta para uma próxima rodada**, a medir em dados novos (as marcas do dono na 1032) e não
  nestes:
  - limiar pelo quartil inferior;
  - ou exigir uma mancha compacta (a marcação é um disco, e o tampo e a mão são regiões
    largas);
  - e só contar os espaços antes da junção.

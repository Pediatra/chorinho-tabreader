# 1048 — Memória do capo por vídeo: o capo visto num quadro vale para os outros

**Data**: 2026-10-23. O pré-registro é commitado antes do código e do sorteio.

**A pergunta**: o capo não se move durante a música. Levando o capo visto com certeza num quadro
(o quadro-chave) para os outros quadros do mesmo vídeo, a cadeia da 1045 entrega mais quadros
com capo certos, sem erro calado?

**Por que** ([1045](1045-rede-de-capo.md#resultado-2026-10-23)): a rede de capo acende com nota
0,96–0,99 quando o capo aparece, mas no kimny ele está escondido (mão, câmera de baixo) na
maior parte dos quadros: visto em 11 de 39, 3 certos entregues. Em 3 dos 5 vídeos há pelo menos
um quadro com o capo visto com nota alta.

## A cadeia

A da 1045 (a da 1047 + a rede de capo `C1_capo_s1` com o limiar 0,172 + o nut pela conta), mais:

1. **Quadros-chave** de um vídeo: capo visto com nota ≥ `NOTA_CHAVE` e o resultado da conta
   aprovado pelos validadores da 1044.
2. **Levar o capo** a um quadro do mesmo vídeo sem capo visto: pontos ORB casados entre o
   quadro-chave mais próximo no tempo e o alvo, **só dentro do braço** nos dois (a máscara do
   braço das marcas previstas pelo par antigo em cada um; a 1015 mostrou que sem isso os pontos
   caem na tablatura), Lowe 0,8, homografia por RANSAC; o capo-chave vai ao alvo pela
   homografia. Aceita com ≥ `MIN_INLIERS` inliers, reprojeção mediana ≤ 3 px e determinante
   entre 0,5 e 2. Se o quadro-chave mais próximo falha, tenta os outros, do mais próximo ao
   mais distante.
3. Com o capo levado, o nut pela conta da 1046 sobre as marcas do par antigo do alvo; o
   resultado é **sinalizado** se os validadores reprovam ou se o par antigo sinalizou (a mesma
   regra dos capos vistos na 1045).

## Escolha (só no desenvolvimento)

- **Desenvolvimento**: a 1043 (kimny, 5 vídeos) e a M39 (shin izumi, 8 vídeos), já vistas.
- **Grade**: `NOTA_CHAVE` ∈ {0,5; 0,7; 0,9} × `MIN_INLIERS` ∈ {10; 20; 40}.
- **Medida de cada ponto da grade**: capos levados e, entre eles, os que caem a ≤ ½ casa do `k`
  do dono ("levados certos").
- **Regra**: entre os pontos com levados errados ≤ 5 % dos levados, o de mais levados certos;
  empate, o de `MIN_INLIERS` maior, depois o de `NOTA_CHAVE` maior. Se nenhum ponto cumpre os
  5 %, a rodada para sem prova.

## Prova: lote novo M48, lacrado

- **Triagem**: 40 vídeos livres (fora de todo gabarito e treino) do kimny's guitar e do shin
  izumi, sorteados juntos (semente 20261048), um quadro no meio de cada, numa folha. O agente
  marca `capo_visto` (capo visível ou legenda de capo na tela) antes do sorteio; isso escolhe a
  amostra e não é rótulo.
- **Lote**: 8 vídeos entre os marcados, 5 quadros cada (40). Com menos de 8, todos os
  marcados.
- O dono revisa como na 1039 (`x` em cada quadro, nut no traste à frente do capo, `k` no capo).

| critério | o que precisa (na M48, contra a cadeia da 1045 nos mesmos quadros) |
| --- | --- |
| **1. Segurança** | falsos que passam ≤ 5 % dos medidos (no máx. 2 em 40) |
| **2. Ganho** | entregues certos ≥ os da 1045 + 6 (15 % de 40) |
| **3. Não estragar** | dos quadros que a 1045 entrega certos, no máx. 1 sai falso que passa |

- O critério 2 pede um mínimo de certos, para não premiar quem só sinaliza.
- Também reportados: por vídeo, os quadros-chave, os levados e os levados certos.

| resultado | o que fazer |
| --- | --- |
| 1, 2 e 3 passam | a memória entra na cadeia com capo (junto com a rede de capo) |
| 1 e 3 passam, 2 falha | olhar por vídeo: sem quadro-chave, ou rastreio que não acha |
| 1 ou 3 falha | não adotar; olhar os levados errados |

## Riscos declarados antes

- Num vídeo sem nenhum quadro-chave, a memória não faz nada (2 dos 5 vídeos da 1043).
- O braço se move entre instantes distantes do vídeo (os 5 quadros vão de 15 % a 85 % da
  duração); a homografia só no braço cobre isso, mas a mão em cima do braço tira pontos.
- Um quadro-chave errado espalha o erro pelo vídeo; os validadores e o sinal do par antigo
  são a barreira.

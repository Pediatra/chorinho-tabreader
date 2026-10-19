# 1029 — Terceiro ciclo de revisão: pablo romé, com o detector retreinado

**Data**: 2026-10-18 (pré-registro feito antes da janela autônoma de 2026-10-19). **Estado**:
regras a priori. **O dono escolheu o canal** ("pablo romé pode ser?").

**Antecedentes**:
- O ciclo funciona: na [1026](1026-ciclo-de-revisao-sky-guitar.md), 92 % saíram certos sem
  revisão; na [1027](1027-ciclo-de-revisao-guitarous.md), 61 %, com 2 falsos passando por causa
  do nut fora da imagem.
- A [1028](1028-um-braco-consenso-e-retreino.md) retreina os dois estágios com as marcas dos
  ciclos (`L3` e `A4`) e testa o "um braço só" (P2) e o consenso (P3).

## Pergunta

O detector retreinado entrega mais certo, sem revisão e sem deixar falso passar, num canal que
ele viu pouco? O pablo romé só aparece em cerca de 9 quadros do C e em 5 da M11b, que são
desenvolvimento.

## Escolha do detector (fixada agora; feita antes de abrir o lote)

1. **Pesos**: entre as 9 combinações de `L3_todos_s{1,2,3}` com `A4_100_todos_s{1,2,3}`,
   escolher pela **M11b** (desenvolvimento: 28 quadros, cadeia completa do quadro inteiro, com
   a regra 1023).
   - Critério: **menos falsos não sinalizados**.
   - Desempate: mais certos não sinalizados; depois, menos sinalizados; depois, a menor soma de
     sementes.
   - Se um peso não existir (treino falhou), entram só as combinações que existem.
   - Se nenhum L3 ou A4 existir, o ciclo usa os pesos da 1026/1027 (`L2_todos_s1` e
     `A3_100_todos_s1`), e isso fica registrado.
2. **P2 e P3**: entram no ciclo **só se passarem** pelos critérios da 1028. Se não, ficam fora.
3. **Regra de revisão**: a da 1023, congelada.

A M11b já foi muito vista e serve só para escolher os pesos, não como medida de resultado.

## Lote

- **8 vídeos do pablo romé**, sorteados com a semente 20261029, entre os vídeos que não aparecem
  em nenhuma amostra anterior (M3b, R, C, N, M11b, 1026 e 1027).
- **8 quadros por vídeo**, entre 0,15 e 0,85 da duração, num total de 64.
- A ferramenta abre preenchida, com os sinalizados primeiro, os trastes fora da imagem cortados
  e a marca **capo** disponível (tecla `k`).

**O que o dono faz**: o mesmo protocolo da 1027. Se houver capotraste, ele clica `k` em cima do
capo.

**Medidas e critério**: os da 1026 e da 1027 (`maos_braco_ciclo medir`).

**Também reportado**: a comparação com o detector antigo (`L2_s1` + `A3_s1`) nos mesmos 64
quadros, contra as marcas do dono. É a medida do ganho do retreino num canal pouco visto.

| resultado | o que fazer |
| --- | --- |
| falsos que passam ≤ 5 % e sinalizados ≤ 50 % | o ciclo segue; as marcas da 1029 entram no próximo retreino |
| falsos que passam > 5 % | parar e investigar por tipo de erro |
| sinalizados > 50 % | seguro, mas caro: propor a melhora que mais reduz os sinalizados |

## Riscos declarados antes

- **A escolha de pesos na M11b** é feita em 28 quadros de canais já vistos pelo estágio 1 (no
  C). Ela pode não ser a melhor para o pablo romé.
- **O pablo romé** pode ter capotraste e nut fora da imagem, a falha ainda sem solução própria.

## Preparação (2026-10-18, 23h40)

- **Pesos**: nenhum `L3` ou `A4` existe, porque a GPU caiu durante o primeiro treino. Pela regra
  deste pré-registro, o ciclo usa `L2_todos_s1` + `A3_100_todos_s1` (`m29/escolha_pesos.json`).
- **P2 e P3**: desligados. O P2 reprovou na 1028, e o P3 não agiu.
- **Previsão rodada na CPU** (`CHORINHO_MAOS_CPU=1`): 61 de 64 com braço, **6 sinalizados**.
- **Vídeos**: moliendo café, gabriel's oboe, "cuando te dicen…", preludio nº1 (villa-lobos),
  gran vals (tárrega), lágrima (tárrega), dust in the wind e carcassi estudio 7.
- **Ferramenta no ar** para o dono: porta 8103, já preenchida, sinalizados primeiro e com a
  tecla `k` (capo).
- **A comparação "detector antigo × novo"** do pré-registro fica sem efeito enquanto não houver
  pesos novos. Quando a fila de GPU terminar o retreino, os pesos novos são medidos nos mesmos
  64 quadros, contra as marcas do dono (`medir --rodada 1029 --comparar-antigo`).

## Emenda 1 (2026-10-19, 10h20, antes de o dono abrir o lote)

O PC foi reiniciado, e a GPU voltou. O retreino da fila está rodando: `L3_todos_s1..3` já
estão prontos, e os `A4` estão em treino.
- O dono **não respondeu nenhum quadro** do lote (0 de 64), e o servidor da porta 8103 parou com
  o reinício.
- Por isso, o preenchimento feito com os pesos de reserva **é refeito com os pesos novos**, como o
  pré-registro previa, assim que os 3 `A4` existirem: `escolher-pesos --rodada 1029` (na M11b,
  com P2 e P3 desligados) e depois `prever --rodada 1029`.
  - A previsão de reserva fica guardada em `m29/previsto_reserva.json`.
- **Por quê**: revisar sobre o preenchimento antigo induz concordância com o detector antigo, e a
  pergunta desta rodada é sobre o detector novo.
- A ordem da fila muda: este preenchimento vem **antes** da Parte A da 1030. A Parte A só usa os
  pesos antigos e não depende dele.
- Se um `A4` falhar 3 vezes, a escolha usa as combinações que existirem, como já diz o
  pré-registro.

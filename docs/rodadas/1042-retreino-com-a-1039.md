# 1042 — Retreino com as marcas da 1039 (capo nas casas 4 e 5) e veto de inversão

**Data**: 2026-10-22. O pré-registro é commitado antes do treino.

**A pergunta**: com as 64 marcas da 1039 no treino, o detector passa a achar o capo também
nas casas 4 e 5? E a escolha, com um veto de inversão nos vídeos verticais, deixa de pegar o
par que inverte o braço?

**Por que** ([1041](1041-retreino-capo-sobreamostrado.md#resultado-na-prova-1039-2026-10-22-depois-da-revisão-do-dono)):
- na 1039, o par da 1041 acertou o capo nas casas 2 e 3, mas nas casas 4 e 5 pôs o nut no nut
  verdadeiro, e 12 desses passaram sem sinal;
- o treino da 1041 tinha ~13 quadros com capo na casa 4 e 1 na casa 5. A 1039 traz 16 e 8;
- a escolha da 1041 pegou um par que inverte o braço em 7 de 28 quadros verticais da M36.

## Treino (`tab/maos/braco/retreino_1042.py`)

- **A receita da 1041**: as mesmas fontes, exclusões e barreira, 3.000 passos, mistura A3 e
  cada quadro com capo **3 vezes** no sorteio dos dois estágios.
- **Entra a M39** (os 64 quadros da 1039, gabarito do dono) nos dois estágios, como fonte do
  dono, com o mesmo filtro das outras (braço `sim`, marcas completas, nut visível).
- **Barreira nova**: nenhum quadro de um vídeo da 1043 entra no treino.
- **Pesos**: `L6_capo_s{1,2,3}` e `A8_capo_s{1,2,3}`, 3 sementes.
- **Contagem antes do treino** (`contar`, sem GPU), em `m42/contagem.json`.

## Escolha

1. **Piso** (o da 1041): na M11b, entregues certos ≥ os do par antigo − 2.
2. **Veto de inversão (novo)**: na M36 (32 quadros, 28 com o nut do dono), o par não pode
   inverter mais quadros que o par antigo (0 na 1041). Inverter = o nut previsto mais perto da
   ponta das cordas do lado do corpo do que do nut do dono.
3. Entre os que passam, o critério da 1029. Se nenhum passa, a rodada reprova sem medir.
- A M36 passa a ser folha de escolha, e por isso sai do critério 3.

## Medida

| critério | onde | o que precisa |
| --- | --- | --- |
| **1. Segurança** | a 1043 (40 quadros, 5 vídeos com capo do kimny's guitar, nunca vistos), depois da revisão do dono | falsos que passam ≤ 5 % dos medidos (no máx. 2 de 40) |
| **2. Capo** | os quadros da 1043 com `k` do dono | no máx. 1 falso que passa, **e** entregues certos ≥ os do par da 1041 nos mesmos quadros |
| **3. Sem capo** | os quadros sem capo do N (21 quadros; já usado como desenvolvimento na 1041, sem escolha nele) | falsos que passam ≤ os do antigo + 1, **e** entregues certos ≥ os do antigo − 2 |

- Também reportado: o resultado por casa do capo, a calibração (certos entre os sem sinal e
  entre os sinalizados) e as inversões na M36.

| resultado | o que fazer |
| --- | --- |
| 1, 2 e 3 passam | o par novo vira o peso do ciclo, com e sem capo |
| 1 e 2 passam, 3 falha | o novo serve só onde há capo, e depende da 1038 (achar o capo) |
| 1 passa, 2 falha | não adotar; olhar por casa do capo e por canal antes de outro retreino |
| 1 falha | não adotar e investigar por tipo de erro (canal clássico em preto e branco? casa do capo?) |

## Riscos declarados antes

- **A 1043 tem só 5 vídeos**: 1 vídeo ruim pesa 8 quadros. O resultado sai também por vídeo.
- **O canal é preto e branco e clássico**: um erro ali pode ser de domínio, e não de capo. A
  tabela por tipo de erro separa os dois.

## Resultado do treino e do critério 3 (2026-10-22)

- 6 treinos (L6_capo_s1..s3 e A8_capo_s1..s3), todos com código 0 (`data/saida/maos/m42/logs/etapas.txt`).
- **Escolha** (M11b com piso, M36 com veto; referência: o par antigo L3_todos_s3 + A4_100_todos_s1, 14 certos, 0 inversões em 28):
  - os 3 pares com L6_capo_s2 invertem o nut em 6 quadros da M36 (de 29 a 30) e saem pelo veto, apesar de terem os mais certos (15 e 16);
  - os pares com L6_capo_s3 ficam abaixo do piso (5 a 7 certos);
  - passam os 3 pares com L6_capo_s1 (12 a 13 certos, 0 inversões em 26); pelo critério da 1029, o escolhido é **L6_capo_s1 + A8_capo_s2** (1 falso que passa, 12 certos, 18 sinalizados).
- **Critério 3 (N sem capo, 17 quadros com braço): reprova.**
  - Falsos que passam: novo 0, antigo 0 (precisa ≤ 1): passa.
  - Entregues certos: novo 9, antigo 12 (precisa ≥ 10): **falha**. O novo sinaliza 7 de 17, contra 5 do antigo.
  - No N com capo (4 quadros, só informativo): novo 3 certos e 1 falso que passa; antigo 0 certos e 3 falsos.
- Pela tabela pré-registrada, se 1 e 2 passarem na 1043, o par novo vale **só onde há capo** e depende da 1038 (achar o capo). Os critérios 1 e 2 esperam a revisão do dono na 1043 (`previsto_1043.json` já gerado).

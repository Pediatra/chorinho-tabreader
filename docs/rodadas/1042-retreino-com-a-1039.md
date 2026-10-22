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

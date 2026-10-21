# 1041 — Retreino com o capo sobreamostrado, escolha com piso

**Data**: 2026-10-21 (janela autônoma). O pré-registro é commitado antes do treino.

**A pergunta**: sorteando os quadros com capo 3 vezes mais, o detector passa a numerar a partir
do capo sem perder os vídeos sem capo? E a escolha, com piso de certos, deixa de premiar o
modelo que sinaliza tudo?

**Por que** (a 1037, [resultado](1037-retreino-com-capo.md#resultado-2026-10-21-gpu-dividida-com-a-tablatura)):
- a tabela da 1037 manda **sobreamostrar** quando o critério 2 falha;
- os pares sãos da 1037 já melhoravam o capo (de 4 para 1–2 falsos que passam) e perdiam
  pouco sem capo. O melhor deles reprovou por 1 quadro no critério 3;
- o par escolhido invertia o braço. Ele **sinaliza quase tudo**, e o critério da 1029 olha
  primeiro os falsos que passam.

## Treino (`tab/maos_braco_retreino_capo3.py`)

- **A receita da 1037**: as mesmas fontes, exclusões e barreira, 3.000 passos e mistura A3.
- **Sobreamostragem**: cada quadro com capo (`k` do dono; o R herda da chave) entra **3
  vezes** no sorteio dos dois estágios. A contagem, feita antes do treino, está em
  `m41/contagem.json`:

| | quadros distintos | com capo | com as cópias | capo no sorteio |
| --- | --- | --- | --- | --- |
| estágio 1 (L5) | 1.460 | 167 | 1.794 | 28 % (era 11 %) |
| estágio 2 (A7), parte real | 1.270 | 148 | 1.566 | 28 % da parte real; ~14 % do lote, com o S |

- **Barreira nova**: nenhum quadro de um vídeo do lote da 1039 entra no treino. A contagem
  deu **0** em cada estágio: os vídeos da 1039 já estavam fora de todas as fontes.
- **Pesos**: `L5_capo3_s{1,2,3}` e `A7_capo3_s{1,2,3}`, com 3 sementes, como pede a regra.

## Escolha (M11b, os mesmos 33 quadros da 1037)

1. **Piso**: só concorre o par com **entregues certos ≥ os do par antigo − 2**, na mesma folha
   (o antigo deu 14 na 1037, então o piso foi 12).
2. Entre os que passam, vale o critério da 1029: menos falsos que passam; depois mais certos;
   depois menos sinalizados; depois a menor soma de sementes.
3. **Se nenhum par passa o piso**, não há escolha: a rodada reprova sem medir.

## Medida

| critério | onde | o que precisa |
| --- | --- | --- |
| **1. Segurança** | **a 1039** (64 quadros, 8 vídeos com capo do shin izumi, nunca vistos), depois da revisão do dono | falsos que passam ≤ 5 % dos medidos, com o par novo |
| **2. Capo** | os quadros da 1039 com `k` do dono | no máximo 1 falso que passa, **e** entregues certos ≥ os do par antigo nos mesmos quadros |
| **3. Sem capo** | os quadros sem capo da M36 e do N (desenvolvimento, já vistos; ninguém escolhe nada neles) | falsos que passam ≤ os do antigo + 1, **e** entregues certos ≥ os do antigo − 2. É o critério 3 da 1037, sem mudança |

- O par antigo na 1039 é a previsão do próprio ciclo (`m39/previsto.json`). O novo fica em
  `m41/previsto_1039.json`, e **ninguém compara os dois com o gabarito antes da revisão do
  dono**.
- O critério 3 sai hoje (`medir-dev`). Os critérios 1 e 2 saem depois da revisão
  (`medir-prova`).

| resultado | o que fazer |
| --- | --- |
| 1, 2 e 3 passam | o par novo vira o peso do ciclo, e a 1038 roda com ele |
| 1 e 2 passam, 3 falha | o novo serve só onde há capo. Depende da 1038 (achar o capo), e o antigo fica nos outros vídeos |
| 1 passa, 2 falha | não adotar. Sobreamostrar não basta: o próximo passo é mais dado de capo com o nut verdadeiro visível (as marcas da 1036 e da 1039 entram no treino) |
| 1 falha | não adotar e investigar por tipo de erro |

**Também reportado**:
- a tabela da escolha com os 9 pares e quantos passaram o piso;
- quantas sementes do estágio 1 invertem o braço;
- a calibração (2005): certos entre os sem sinal e entre os sinalizados.

## Riscos declarados antes

- **Sobreamostrar repete os mesmos quadros**: são 167 quadros distintos, a maioria de 3 canais
  (kenneth, guitarous e violaodecria). O modelo pode decorar esses vídeos em vez de aprender o
  capo.
- **O piso usa a folha da escolha**, que já foi usada na 1037. Ela continua sendo
  desenvolvimento, e a prova é a 1039.
- **A 1039 depende da revisão do dono.** Até lá, a rodada fica sem os critérios 1 e 2.
- **A tablatura divide a GPU**: o tempo de treino pode mudar, mas o resultado não (semente e
  determinismo por processo).

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

## Resultado parcial (2026-10-21, 16:12–20:19; commit do código `1e79c81c`)

Os 6 treinos terminaram sem erro (`m41/logs/etapas.txt`). O estágio 1 levou ~19 min por
semente e o estágio 2 ~55–60 min.

**Escolha** (M11b, 33 quadros; o par antigo deu 6 falsos que passam, 14 certos e 12
sinalizados, então o piso era 12 certos):

| par | falsos que passam | certos | sinalizados | passa o piso |
| --- | --- | --- | --- | --- |
| L5 s1 + A7 s1 | 6 | 11 | 12 | não |
| L5 s1 + A7 s2 | 2 | 13 | 15 | sim |
| L5 s1 + A7 s3 | 7 | 14 | 11 | sim |
| L5 s2 + A7 s1 | 4 | 11 | 16 | não |
| **L5 s2 + A7 s2** | **1** | **15** | 14 | **sim: escolhido** |
| L5 s2 + A7 s3 | 3 | 13 | 14 | sim |
| L5 s3 + A7 s1 | 5 | 3 | 25 | não |
| L5 s3 + A7 s2 | 1 | 4 | 27 | não |
| L5 s3 + A7 s3 | 6 | 3 | 24 | não |

- **O piso fez o que devia**: a semente 3 do estágio 1 é desta vez a que sinaliza quase tudo
  (3 e 4 certos), e saiu.
- Na folha de escolha, o par escolhido é melhor que o antigo: 1 falso contra 6, e 15 certos
  contra 14.

**Critério 3 (sem capo, na M36 e no N): reprova.**

| sem capo (33 quadros) | par novo | par antigo |
| --- | --- | --- |
| falsos que passam | 0 | 0 |
| entregues certos | **9** | 15 |

- O mínimo era 13 (o antigo − 2).

| com capo (20 quadros, descritivo) | par novo | par antigo |
| --- | --- | --- |
| falsos que passam | 1 (no N) | 4 |
| entregues certos | 4 | 6 |

- **Por quê: o par escolhido inverte o braço em 7 de 28 quadros da M36** (os vídeos verticais
  do violaodecria): o nut sai do lado do corpo. Conta: nut previsto mais perto da ponta do
  corpo do que do nut do dono.
  - O par antigo inverte 0 de 28, e o melhor par da 1037 (L4 s1 + A6 s2), também 0.
  - A folha de escolha (M11b) não tem vídeo vertical, então o piso não pega essa inversão.
- **Calibração (2005)**, certos entre os entregues sem sinal:
  - na M36, 3 de 4 (antigo: 9 de 10);
  - no N, 10 de 11 (antigo: 12 de 15).

**A previsão da 1039** com o par novo está em `m41/previsto_1039.json`: 64 quadros, 33
sinalizados e 1 sem braço. Ninguém a comparou com o gabarito. Os critérios 1 e 2 saem depois
da revisão do dono (`medir-prova`).

**Leitura, pela tabela do pré-registro**:
- com o critério 3 reprovado, o melhor resultado possível agora é a linha "1 e 2 passam, 3
  falha": o par novo serviria só em vídeo com capo, e dependeria da 1038 para achar o capo;
- o par antigo segue no ciclo.

**O que fica para a próxima tentativa**:
1. **a inversão do braço é o defeito comum** da 1037 e da 1041. Uma semente em três inverte
   tudo, e a escolhida aqui inverte nos vídeos verticais;
2. a folha de escolha precisa de vídeos verticais, ou a escolha precisa de uma checagem de
   orientação (o nut do lado da cabeça);
3. o alvo de orientação no treino do estágio 1 é o lugar a investigar antes de mais dado.

## Resultado na prova (1039, 2026-10-22, depois da revisão do dono)

`python -m tab.maos.braco.retreino_capo3 medir-prova` (`m41/medida_prova.json`), 64 quadros,
todos com capo (casas 2 a 5) e braço `sim`:

| | par novo (L5 s2 + A7 s2) | par antigo (L3 s3 + A4 s1) |
| --- | --- | --- |
| entregues certos | **9** de 64 | 0 |
| falsos que passam | **15** de 64 (23 %) | 39 (61 %) |
| sinalizados | 33 | 25 |
| por classe | 11 certos, 17 imprecisos, 35 falsos, 1 sem braço | 64 falsos |

- **Critério 1 (segurança, ≤ 5 %) reprova**: 15 de 64. **Critério 2 (capo) reprova**: 15
  falsos que passam, o limite era 1. A linha da tabela é "1 falha": não adotar e investigar
  por tipo de erro.

**Por tipo de erro** (`m41/erros_1039/diag.py` e `linhas.json`; folha
`m41/erros_1039/folha_tipos.jpg`):
- **o erro depende da casa do capo**:
  - capo na casa 2 ou 3 (5 vídeos, 40 quadros): o par novo põe o nut no capo em 32 de 40, a
    menos de meia casa do dono. 11 são certos (9 entregues sem sinal) e 16 imprecisos (nut
    ~0,2–0,5 casa para o lado da cabeça). Os outros 3 falsos que passam são do totoro (capo
    3): q27 com o nut no nut verdadeiro, q29 e q31 a ~0,5 casa;
  - **capo na casa 4 (2 vídeos, 16 quadros): o nut fica no nut verdadeiro em 14 de 16**, a
    ~7 larguras de pestana para o lado da cabeça, e **12 deles passam sem sinal**. São 12 dos
    15 falsos que passam;
  - capo na casa 5 (1 vídeo, 8 quadros): o mesmo erro, mas os 8 saem sinalizados;
- o par antigo põe o nut no nut verdadeiro em todos os 64, como na 1032.

**Leitura**: a sobreamostragem ensinou o capo onde o treino tinha exemplo (casas 1 a 3). O
treino tem só ~13 quadros com capo na casa 4 e 1 na casa 5, e lá o modelo volta ao nut
verdadeiro **sem sinalizar**. É falta de cobertura, como na regra 9 do `AGENTS.md`. O passo
seguinte é a 1042: as 64 marcas da 1039 (16 na casa 4, 8 na casa 5) entram no treino, e a
prova vai para um lote novo (1043).

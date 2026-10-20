# 1032 — Quarto ciclo de revisão: kenneth acoustic

**Data**: 2026-10-20 (janela autônoma; o pré-registro vem antes de qualquer previsão no lote).
**Estado**: regras a priori. **O canal foi escolhido pelo dono** ("pode ser kenneth acoustic").

**Antecedentes**:
- [1029](1029-ciclo-de-revisao-pablo-rome.md): 54 de 60 entregues certos, mas 4 falsos que
  passam (6,3 %), todos com o nut fora da imagem.
- [1031](1031-nut-fora-por-vizinhos-e-juncao.md): métodos para o nut fora (V, J e A5).

## Lote (já sorteado; `m32/sorteio.json`)

- **8 vídeos do kenneth acoustic**, sorteados com a semente 20261032, entre os 515 do canal.
  Ficam de fora os vídeos de todas as amostras anteriores (M3b, R, C, N, M11b, 1026, 1027 e 1029).
- **8 quadros por vídeo**, de 0,15 a 0,85 da duração, num total de 64.
- **Vídeos**:
  - redbone;
  - canon in d;
  - a thousand miles;
  - apt.;
  - merry go round of life;
  - smooth criminal;
  - bad romance;
  - interstellar.
- **Visto numa folha de 16 quadros** (`m32/amostra.jpg`), antes da previsão:
  - o canal mostra quase sempre o braço inteiro, com a cabeça do violão;
  - muitas vezes usa capotraste, e a casa do capo aparece escrita na tela ("Capo: Fret N").

## Detector (fixado agora)

1. **Pesos**: a escolha da 1029 na M11b, com o mesmo critério e o mesmo desempate.
   - Os candidatos do estágio 2 são `A4_100_todos_s{1,2,3}` e também os `A5_100_todos_s{1,2,3}`
     que existirem quando a escolha rodar. O A5 é o estágio 2 com os quadros de nut fora, da
     1031.
   - Se nenhum A5 existir, a escolha fica entre os A4, como na 1029.
2. **Regra de revisão**: a da 1023, congelada.
3. **Mais o sinal de nut suspeito**: a regra de borda da 1030, que pré-registrei na 1031 para o
   caso de nenhum método passar.
   - Um quadro com braço é sinalizado quando não tem nut, ou quando a ponta das cordas do lado
     do nut fica a até 2 % da borda menor.
   - Na 1030, esse sinal disparou em 30 % dos quadros bons. Ele custa revisão, mas não deixa
     passar falso.
4. **Métodos V e J**: entram só se passarem no critério da 1031.
   - Mesmo assim, eles exigem rodar inteiros os 8 vídeos, cerca de 3 600 quadros, e na GPU
     dividida desta janela isso leva mais de 6 h.
   - Se passarem e não houver tempo, ficam para a revisão seguinte, e isso fica registrado.
5. P2 e P3 ficam desligados, como na 1029.

## O que o dono faz

O protocolo da 1029:
- os sinalizados aparecem primeiro;
- capo com a tecla `k`;
- nut fora com o traste de referência (botão direito no traste e o número);
- 7 cordas com o botão.

## Medidas e critério

Os da 1026, da 1027 e da 1029 (`maos_braco_ciclo medir --rodada 1032`).

| resultado | o que fazer |
| --- | --- |
| falsos que passam ≤ 5 % e sinalizados ≤ 50 % | o ciclo segue; as marcas entram no próximo retreino |
| falsos que passam > 5 % | parar e investigar por tipo de erro |
| sinalizados > 50 % | seguro, mas caro: propor a melhora que mais reduz os sinalizados |

**Também reportado**: quantos quadros o sinal de nut suspeito mandou para revisão, e quantos
deles estavam certos. Essa é a medida do custo do sinal.

## Riscos declarados antes

- **O capotraste é comum neste canal.** O detector já confundiu capo com nut antes. A tecla `k`
  e a regra "casa contada do nut" valem.
- **O braço é longo na imagem e a cabeça aparece.** O nut quase sempre está visível, e por
  isso este lote quase não testa o nut fora.

## Verificação retroativa do sinal de nut suspeito (2026-10-20, antes da previsão da 1032)

A regra é a mesma, sem mudança (`m31/sinal_1029.py`), aplicada às previsões já revisadas:

| ciclo | falsos que passavam | o sinal pega | sinalizados a mais (todos os do sinal) |
| --- | --- | --- | --- |
| 1026 | 0 | — | 0 |
| 1027 | 2 (q51 e q56) | q51 | 5 (q51, q57, q60, q61 e q64) |
| 1029 | 4 (q19, q20, q24 e q46) | q19, q20 e q24 | 6 (os 3 falsos e mais q17, q18 e q23) |

- Com o sinal, a 1029 teria **1 falso que passa em 63 (1,6 %)**, e não 4 (6,3 %). A 1027 teria 1
  em 64.
- O que escapa (1027:q56 e 1029:q46) é o nut previsto no 1º traste longe da borda, que nenhuma
  regra de borda vê.
- São ciclos já vistos, então isso é direção, não prova. A 1032 é a medida.

## Preparação (2026-10-20, 11h45)

- **Pesos** (`m32/escolha_pesos.json`, M11b, 18 combinações: 3 L3 × 3 A4 e 3 A5): **`L3_todos_s3`
  + `A4_100_todos_s1`**, os mesmos da 1029.
  - 0 falsos que passam, 16 entregues certos e 12 sinalizados.
  - O melhor com A5 (`L3_s2` + `A5_s1`) dá 0 falsos e 14 certos. 4 das 9 combinações com A5
    têm 1 falso que passa.
- **Previsão**: 64 de 64 quadros com braço e **1 sinalizado** (q43, S1 = 2,05).
  - O sinal de nut suspeito disparou em **0** quadros: o canal mostra a cabeça do violão.
- **Conferido numa folha de 8 quadros** (`m32/conf1.jpg`): o nut ficou no nut, e o capo (casas
  6, 2, 4, 3, 3 e 1, como diz a tela) não foi tomado como nut.
- **A ferramenta está no ar** na porta 8103, com os quadros já preenchidos.

## Resultado (2026-10-20, noite; `m32/medida.json`) — **o ciclo funciona**

O dono revisou os 64 quadros.

| | 1032 (kenneth) | 1029 (pablo romé) |
| --- | --- | --- |
| entregue certo | **63 de 64 (98,4 %)** | 54 de 60 (90 %) |
| falsos que passam | **0 de 64 (0 %)** | 4 de 63 (6,3 %) |
| sinalizados | 1 (1,6 %) | 5 (8 %) |

- **Critério**: 0 % ≤ 5 % e 1,6 % ≤ 50 %. **O ciclo segue**, e as marcas da 1032 entram no próximo
  retreino.
- **O único erro foi sinalizado**: o q43 (smooth criminal, S1 = 2,05). Segundo o dono, o detector
  "confundiu um capotraste com o nut".
- **O dono também anotou o q11** (canon in d), que está certo e não foi sinalizado: "é o mesmo
  ângulo que ele confundiu o nut com o capotraste, acho que tá faltando um controle maior e
  validação entre os quadros".
  - Fica como proposta: conferir a posição do nut entre quadros da mesma tomada. A 1030 já
    mostrou que o consenso por deslocamento não age, então teria de ser uma regra nova.
- **O sinal de nut suspeito (v2) não disparou**: 0 quadros, o que é coerente com um canal que
  mostra o braço inteiro. O custo dele nesse canal foi zero.
- **O dono não usou a marca de capo** (`capo` vazio nos 64 quadros), embora o canal use capo na
  maioria dos vídeos. A casa do capo aparece escrita na tela ("Capo: Fret N").

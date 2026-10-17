# 1015 — M11a: braço quadro a quadro, rastreado a partir de um quadro de referência

**Data**: 2026-10-16. **Estado**: regras a priori. Este documento ganha commit **antes** de
qualquer medida no teste (q37–q66). Plano: [`plano-dataset-maos.md`](../guias/plano-dataset-maos.md)
§5, M11.

## Pergunta

Partindo de **um** quadro marcado pelo dono por vídeo (o quadro-chave), um rastreador só por
imagem acha o braço nos outros instantes do vídeo? E ele diz "não achei" quando não acha?

## Método

- No quadro-chave, a região do braço é o polígono das cordas 1 e 6 do gabarito, alargado
  de meio vão de corda para cada lado e estendido até a pestana.
- Pontos de interesse nessa região (ORB ou AKAZE, do cv2), casados com o quadro alvo.
- Homografia por RANSAC.
- As marcas do quadro-chave (pestana, trastes, cordas 1 e 6) são levadas ao quadro alvo pela
  homografia.
- "Achei" exige um número mínimo de inliers e um erro de reprojeção máximo. Fora disso, "não
  achei".
- Determinístico, sem treino e sem nada da tablatura.

## Divisão

- **Desenvolvimento** (escolher o detector de pontos e os limiares): os vídeos do sky guitar
  com mais de uma marca. São retrato (q02 → q24, q25), noturno (q16 → q26, q27), lacrimosa
  (q21 → q28, q29) e glimpse (q23 → q30, q31): 8 quadros alvo.
- **Teste** (uma medida só, com tudo congelado): 6 vídeos de 6 canais. O quadro-chave é a marca
  antiga do vídeo, e os alvos são os 5 instantes novos:

  | canal | quadro-chave | alvos |
  | --- | --- | --- |
  | cifra club | q01 | q37–q41 |
  | kenneth acoustic | q04 | q42–q46 |
  | shin izumi | q05 | q47–q51 |
  | leonardo ramos | q06 | q52–q56 |
  | iwaki | q08 | q57–q61 |
  | guitar dell'arte | q13 | q62–q66 |

- Todo o desenvolvimento é do sky guitar. Isso é declarado: o teste mede se o método passa
  para outros canais.

## Métricas (as mesmas da linha de base da B3, `maos-frentes.md` §7)

Por quadro alvo com braço "sim" no gabarito:

- **pestana**: erro em casas;
- **pior traste**: o pior erro entre os trastes 1–12 marcados pelo dono, em casas, medido ao
  longo do eixo do braço e dividido pelo vão local;
- **erro perpendicular**: distância das cordas 1 e 6 previstas às do dono, em vãos de corda.
  O vão de corda é a distância entre as cordas 1 e 6 do dono dividida por 5. Vale o pior dos
  dois extremos de cada corda.

**Linha de base**: a grade fixa, com as marcas do quadro-chave usadas sem mudança. Nos 8
quadros de desenvolvimento, ela tem de reproduzir a tabela da B3: até 2,4 cordas de erro
perpendicular no q28.

## Critérios de aceite (no teste)

Cada quadro alvo é classificado assim:

- **certo**: o rastreador disse "achei", a pestana e o pior traste ficaram a < 1/4 de casa, e
  o erro perpendicular ficou a < 1/4 de vão;
- **falso**: o rastreador disse "achei", mas a pestana ou algum traste passou de 1/2 casa, ou o
  erro perpendicular passou de 1/2 vão;
- entre um e outro: impreciso.

| | critério |
| --- | --- |
| CA1 | a linha de base reproduz a tabela da B3 nos 8 quadros de desenvolvimento |
| CA2 | certos ≥ 95 % dos "achei" no teste |
| CA3 | falsos ≤ 2 % dos quadros alvo com braço "sim" (com 30 quadros, isso quer dizer 0 falsos) |
| CA4 | cobertura ("achei" sobre braço "sim") relatada por canal, com denominador; sem mínimo nesta rodada |
| CA5 | erro perpendicular mediano no teste menor que o da linha de base nos quadros "achei" |
| CA6 | duas execuções idênticas |
| CA7 | gate verde |

- Quadro em que o gabarito diz braço "não": "achei" ali é falso.
- Quadro com braço "parcial": entra só no CA4.
- A amostra é pequena (30 quadros). O resultado é um sinal de ir ou não ir para o rollout do
  braço; ele não fecha a precisão.

**Pare se**, no desenvolvimento, o rastreador não bater a linha de base no erro
perpendicular nos quadros que se mexem (q26, q27 e q28). Nesse caso, olhe os casamentos
desenhados antes de mexer em limiar.

## Linha de base no desenvolvimento (CA1), medida antes do teste

`python -m tab.maos_braco_tempo base` (duas execuções, arquivo idêntico;
`data/saida/maos/m11/base_dev.json`):

| par | pestana (casas) | pior traste (casas) | ⊥ nas cordas (vãos) | B3 (deslocamento do nut) | classe |
| --- | --- | --- | --- | --- | --- |
| q02→q24 | 0,08 | 0,11 | 0,17 | +7 px | certo |
| q02→q25 | 0,02 | 0,03 | 0,13 | +13 px | certo |
| q16→q26 | 0,07 | 0,14 | 1,34 | −26 px | falso |
| q16→q27 | 0,09 | 0,16 | 2,40 | −51 px | falso |
| q21→q28 | 0,05 | 0,07 | 1,98 | +64 px | falso |
| q21→q29 | 0,04 | 0,10 | 0,23 | 0 px | certo |
| q23→q30 | 0,15 | 0,08 | 0,41 | +4 px | impreciso |
| q23→q31 | 0,03 | 0,06 | 0,15 | −4 px | certo |

- **Casas**: reproduz a B3 com diferença de no máximo 0,03 casa.
- **Perpendicular**: a coluna da B3 era o deslocamento **vertical do nut**. Conferi:
  7,1 / 13,2 / −26,5 / −51,2 / 63,7 / 0,0 / 4,2 / −3,8 px. Ela não media as cordas. A
  métrica desta rodada é a que está escrita acima (pior extremo das cordas 1 e 6, em vãos).
  Ela dá números diferentes, mas a conclusão é a mesma: os quadros que se mexem (q26, q27 e
  q28) erram de 1,3 a 2,4 vãos, e os outros ficam abaixo de 0,5.
- **CA1 está cumprido** nas casas e na conclusão. A linha de base do CA5 é esta coluna, e
  não a da B3. Os critérios não mudam.

## Rastreador congelado (desenvolvimento)

`python -m tab.maos_braco_rastreio dev` (`tab/maos_braco_rastreio.py`).

- **Detector**: ORB. O AKAZE não existe no OpenCV 5.0.0 da imagem; não instalei nada.
- **Parâmetros congelados**:
  - `n_orb` = 5000;
  - Lowe = 0,8;
  - `min_inliers` = 15;
  - reprojeção mediana ≤ 3 px;
  - RANSAC com limiar de 3 px e semente 0;
  - determinante do bloco 2×2 entre 0,5 e 2.
- **Busca no quadro alvo**: no quadro inteiro.
- **Varredura** (80 combinações, só nos pares de desenvolvimento):
  - com 500 a 2000 pontos, q27 ou q28 caem em "não achou";
  - com Lowe 0,85, aparece 1 falso;
  - com 5000 pontos e Lowe de 0,70 a 0,80, os três pares que se mexem ficam abaixo da linha
    de base.

| par | inliers | pestana | pior traste | ⊥ (vãos) | base ⊥ | classe |
| --- | --- | --- | --- | --- | --- | --- |
| q02→q24 | 100 | 0,01 | 0,04 | 0,15 | 0,17 | certo |
| q02→q25 | 113 | 0,02 | 0,03 | 0,09 | 0,13 | certo |
| q16→q26 | 141 | 0,01 | 0,02 | 0,14 | 1,34 | certo |
| q16→q27 | 127 | 0,08 | 0,08 | 0,13 | 2,40 | certo |
| q21→q28 | 89 | 0,01 | 0,04 | 0,14 | 1,98 | certo |
| q21→q29 | 111 | 0,03 | 0,03 | 0,07 | 0,23 | certo |
| q23→q30 | 126 | 0,03 | 0,06 | 0,08 | 0,41 | certo |
| q23→q31 | 102 | 0,02 | 0,05 | 0,17 | 0,15 | certo |

- Os parâmetros foram escolhidos nestes 8 pares, então a medida é dentro da amostra e **não
  valida nada**. A regra de parada não disparou.
- Conferi a olho os desenhos dos três pares que se mexem (`data/saida/maos/m11/desenhos/`):
  - as cordas previstas caem sobre as do dono;
  - os casamentos ficam no braço e se movem de forma coerente.
- Duas execuções deram o mesmo JSON (sha256 `27ab99b5…`).
- O teste (q37–q66) roda **uma vez**, com estes parâmetros, quando o dono terminar as marcas.

## Resultado do teste (uma medida, 2026-10-17)

Os dados do teste:
- **Gabarito**: commit `3344910b`, com q37–q66 marcados pelo dono, todos com braço "sim".
  - O q53 tinha ficado sem resposta no campo do braço. O dono respondeu "sim" antes do teste.
- **Comandos**: `python -m tab.maos_braco_rastreio teste` (commit `af0fd992`, parâmetros
  congelados) e `python -m tab.maos_braco_tempo base --teste`.

| par | achou | inliers | pestana | pior traste | ⊥ (vãos) | classe | base ⊥ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| q01→q37 | sim | 207 | 0,02 | 0,07 | 0,21 | certo | 1,07 |
| q01→q38 | sim | 193 | 0,03 | 0,05 | 0,10 | certo | 2,18 |
| q01→q39 | não (degenerada) | 58 | — | — | — | não achou | 7,63 |
| q01→q40 / q41 | não | 4 / 5 | — | — | — | não achou | 3,14 / 3,54 |
| q04→q42–q46 | não | 5–34 | — | — | — | não achou ×5 | 0,11–3,38 |
| q05→q47–q51 | não | 6–10 | — | — | — | não achou ×5 | 0,14–1,24 |
| q06→q52 | sim | 68 | 0,17 | 0,30 | 0,35 | impreciso | 2,75 |
| q06→q53 | sim | 169 | 0,03 | 0,18 | 0,16 | certo | 1,33 |
| q06→q54 | sim | 151 | 0,03 | 0,23 | 0,06 | certo | 1,10 |
| q06→q55 | não (degenerada) | 105 | — | — | — | não achou | 0,49 |
| q06→q56 | sim | 135 | 0,01 | 0,21 | 0,17 | certo | 0,35 |
| q08→q57–q61 | não | 3–7 | — | — | — | não achou ×5 | 0,25–2,96 |
| q13→q62 | sim | 61 | 0,17 | 0,13 | 0,22 | certo | 4,72 |
| q13→q63 | sim | 67 | — (fora) | 0,06 | 0,10 | certo | 3,29 |
| q13→q64 | sim | 139 | 0,01 | 0,07 | 0,12 | certo | 0,46 |
| q13→q65 | sim | 85 | 0,03 | 0,07 | 0,35 | impreciso | 0,56 |
| q13→q66 | sim | 108 | 0,04 | 0,08 | 0,27 | impreciso | 0,68 |

| | critério | resultado | |
| --- | --- | --- | --- |
| CA1 | linha de base reproduz a B3 | casas ≤ 0,03 de diferença (ver acima) | **passa** |
| CA2 | certos ≥ 95 % dos "achei" | 8 de 11 = **72,7 %** (3 imprecisos: 0,27–0,35 vão) | **reprova** |
| CA3 | falsos ≤ 2 % | **0 de 30** | **passa** |
| CA4 | cobertura por canal | cifra club 2/5, kenneth 0/5, shin izumi 0/5, leonardo ramos 4/5, iwaki 0/5, guitar dell'arte 5/5; total **11/30** | relatado |
| CA5 | ⊥ mediano < linha de base nos "achei" | **0,17** contra 1,10 | **passa** |
| CA6 | duas execuções idênticas | `cmp` idêntico | **passa** |
| CA7 | gate | verde | **passa** |

**Veredito: reprova (CA2).** O rastreador não entra no rollout como está.

O que o teste mostra:
- **Ele nunca disse "achei" errado.** Em 30 quadros houve 0 falsos, enquanto a grade fixa faz
  18 falsos, 10 imprecisos e 2 certos. Quando achou, errou 0,17 vão no mediano, contra 1,10 da
  grade fixa nos mesmos quadros.
- **Os imprecisos ficam perto do limite de 1/4 de vão, a 0,27–0,35 vão** (5–8 px num vão de
  cerca de 20 px). Não sabemos quanto o próprio clique do dono varia. Sem essa medida, não dá
  para dizer se 1/4 de vão está acima do ruído do gabarito.
- **A cobertura caiu a zero em 3 canais**: kenneth, shin izumi e iwaki, todos com câmera aberta.
  Os pontos da tela levaram a cota de pontos. Diagnóstico feito **depois** do teste, sem mudar
  nada:

  | quadro | área do braço | pontos ORB no braço (5000 no quadro inteiro) | pontos ORB buscando só no braço |
  | --- | --- | --- | --- |
  | q24 (sky, dev) | 9,3 % | 506 | 4169 |
  | q27 (sky, dev) | 9,4 % | 1100 | 4364 |
  | q37 (cifra club) | 5,0 % | 1227 | 3528 |
  | q42 (kenneth) | 5,2 % | **0** | 2919 |
  | q48 (shin izumi) | 3,2 % | **19** | 3472 |
  | q57 (iwaki) | 2,7 % | **1** | 1654 |

  - Os 5000 pontos do quadro alvo ficam quase todos na tablatura e no texto, que têm alto
    contraste.
  - O braço tem textura de sobra quando buscado sozinho.
  - Nos 8 pares do desenvolvimento (sky guitar, braço em close), isso não aparecia. Era o risco
    declarado: todo o desenvolvimento num canal só.

**Próximo (nova rodada, com critérios escritos antes e quadros de teste novos).** Os 30 quadros
deste teste já foram vistos e não servem mais de teste. Duas mudanças a medir:
1. Buscar os pontos do alvo só numa região: o quadro sem a caixa da tablatura, ou o braço do
   quadro-chave alargado.
2. Medir quanto o dono varia ao remarcar os mesmos quadros sem ver a marca antiga, para saber
   se o limite de 1/4 de vão está acima do ruído do gabarito.

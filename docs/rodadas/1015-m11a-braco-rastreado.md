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

# 1022 — Decodificador de trastes robusto e prova lacrada na M11b

**Data**: 2026-10-18. **Estado**: regras a priori. Este documento ganha commit antes de
qualquer mudança no decodificador.

**Antecedente** ([1021](1021-piloto-detector-do-braco.md)): o A3 com 100 %, semente 1, deu
30/64 certos e 18 falsos nos quadros G, em canal deixado de fora.
- A rede acerta a geometria: cordas com mediana de 0,19 vão e nut com 0,02 casa.
- Os **18 falsos vêm todos da numeração dos trastes**. A regra "por ordem" (emenda 2 da 1021)
  conta um pico a mais ou a menos, e toda a numeração desliza.
- O dono aprovou esta rodada.

## Pergunta

Com um decodificador que atribui os números dos trastes por ajuste robusto (e não por
contagem), o detector da 1021 passa no critério da fase A em **8 canais que nunca viu**?

## O decodificador v2 (a única mudança de método)

O que a v2 recebe e o que muda:
- **Entrada**: os mesmos 4 mapas da 1021, as cordas e o nut.
- **O que muda**: só a numeração dos picos do canal de trastes.
- **Modelo**: t(n) = (a·s(n) + b)/(c·s(n) + 1), com s(n) = 1 − 2^(−n/12) e **b = x do nut**
  (preso). Restam 2 parâmetros: a e c.

Passos:
1. **Hipóteses**: para cada par de picos (p_i < p_j) e cada par de números
   (1 ≤ n_i < n_j ≤ 20), resolva a e c pelo sistema linear a·s − c·t·s = t − b nos dois
   pontos.
   - Descarte a hipótese se o denominador não for positivo em n = 0..20.
   - Descarte também se t(n) não for estritamente crescente.
2. **Inliers**: um pico é inlier do número n quando |p − t(n)| ≤ 0,25 · (t(n+1) − t(n)).
   - Cada número recebe no máximo um pico (o mais próximo), e cada pico no máximo um número.
   - Contam só os números de 1 até o maior n com t(n) dentro da faixa.
3. **Escolha**: a hipótese com mais inliers.
   - Empate: menor soma dos |p − t(n)| normalizados pelo espaço local.
   - Depois, reajuste a e c por mínimos quadrados com todos os inliers (b continua preso).
4. **Saída**:
   - trastes de 1 até o maior número inlier;
   - número inlier usa a posição do pico; número sem pico usa a posição do modelo;
   - picos que não são inliers são descartados;
   - com menos de 4 inliers, a resposta é "não achou".

**Os limiares (0,25 do espaço, 20 trastes, 4 inliers) ficam fixos agora.** Eles só podem
mudar no desenvolvimento abaixo, e nunca depois de abrir a M11b.

## Desenvolvimento (sem os G e sem a M11b)

| portão | o que mede | passa se |
| --- | --- | --- |
| D1, oráculo | Mapas perfeitos dos G pelo decodificador v2. É verificação de código, sem modelo: o mesmo V1 da 1021. | ≥ 95 % certos nos 64 |
| D2, R fora da dobra | Os pesos já treinados `A3_100_<k>_s1` (1021) aplicados aos quadros **R** do canal k, que ficou fora do treino daquela dobra. Os R são outros quadros dos mesmos vídeos, rotulados pelo rastreador, e não os G. | só registro: certos e falsos contra o rótulo R, v1 contra v2 |
| D3, S de validação | O peso A1 do V3 (1021) nos 500 S de validação, com a v1 e com a v2. | só registro |

- Se o D1 falhar, conserte só a implementação, nunca os limiares.
- O D2 e o D3 podem ajustar **um** limiar, o 0,25. Qualquer ajuste é registrado com os números
  antes e depois, e congelado antes da prova.

## Prova (M11b, lacrada até aqui)

**Treino**:
- O A3 da 1021 sem dobra: S + **todos** os R dos 8 canais de `braco.json`.
- 3 sementes, 3.000 passos cada, com o mesmo código de treino da 1021 (nada muda além do
  decodificador).
- Retomável: se a GPU cair, a unidade é refeita.

**Quadros**:
- Os 28 quadros da M11b com braço `sim` e marcas completas: 8 quadros-chave (q01, q41, q11,
  q16, q21, q26, q31 e q36) e 20 alvos (q46–q61, q65, q69, q73 e q74).
- São **8 canais** que não aparecem em S, R nem G.
- A faixa é recortada do gabarito do dono com a mesma perturbação da 1021 (semente
  `20261021:T:<id>`).
- A M11b é aberta **uma vez**, depois do commit do decodificador congelado.

**Critério (média das 3 sementes), o mesmo da fase A da 1021:**

| resultado | o que fazer |
| --- | --- |
| certos ≥ 70 % e falsos ≤ 5 % (no máximo 1 em 28) | **passa**: segue para a fase B (o estágio 1, que acha a faixa sem o gabarito) |
| abaixo disso | reprova. Registrar por canal e por tipo de erro; a próxima decisão é do dono |

Também são reportados:
- a tabela por canal, com denominador;
- as medianas de cordas, nut e pior traste;
- a amplitude entre as sementes.

## Riscos declarados antes

- **28 quadros de 8 canais são poucos.** Com 0 falsos em 28, o limite superior de 95 % da
  taxa de falsos fica em cerca de 10 %.
- **A faixa ainda vem do gabarito**, com erro simulado. Passar aqui não prova o detector
  inteiro. A fase B mede o conjunto.
- **A GPU é dividida com a trilha da tablatura.** Cada treino leva de 30 a 50 min, e o driver já
  caiu uma vez.

## Desenvolvimento: resultado (2026-10-18)

**Treino final**: `A3_100_todos_s1..3` em `artefatos/m21/`, 3.000 passos cada.
- Tempos: 3.343 s, 3.693 s e 4.237 s.
- As 3 sementes terminaram na primeira tentativa, sem queda da GPU.

**D1, oráculo** (`d1_oraculo_v2.json`): a v2 deu **64/64 certos** e passou.
- A v1 no mesmo oráculo deu 62/64, igual ao V1 da 1021.
- Isso confirma que a refatoração não mudou a v1.

**D2, R fora da dobra** (`d2_r_fora.json`): 1.052 quadros, pesos `A3_100_<k>_s1`, rótulo do
rastreador.

| canal (dobra) | quadros | certo v1 → v2 | falso v1 → v2 |
| --- | --- | --- | --- |
| cifra club | 125 | 34 → 35 | 14 → 7 |
| guitar dell'arte | 125 | 99 → 115 | 25 → 8 |
| iwaki | 92 | 49 → 58 | 17 → 3 |
| kenneth acoustic | 90 | 7 → 81 | 82 → 6 |
| leonardo ramos | 118 | 55 → 76 | 47 → 8 |
| robert lunn | 53 | 16 → 24 | 13 → 0 |
| shin izumi | 98 | 32 → 65 | 48 → 0 |
| sky guitar | 351 | 293 → 305 | 20 → 4 |
| **total** | **1.052** | **585 (55,6 %) → 759 (72,1 %)** | **266 (25,3 %) → 36 (3,4 %)** |

- A v2 ganha nas 8 dobras.
- O maior ganho é o kenneth (capotraste), que era a causa nomeada na 1021.
- O rótulo R vem do rastreador, que também erra. Por isso esses números servem para comparar a
  v1 com a v2, não como taxa absoluta.

**Limiar**: `TOLERANCIA_V2 = 0,25`, **mantido e congelado**. Não houve varredura, e o D2 não deu
motivo para mexer.

Interpretações tomadas na implementação, onde o pré-registro não dizia:
- o espaço local de n = 20 usa t(21);
- o denominador positivo é exigido até n = 21;
- só os picos à direita do nut entram na numeração.

**D3, S de validação** (`d3_sval.json`): peso A1 do V3, 500 amostras.

| | certo | impreciso | falso | não achou |
| --- | --- | --- | --- | --- |
| v1 | 283 | 32 | 184 | 1 |
| v2 | **342 (68,4 %)** | 53 | **104 (20,8 %)** | 1 |

- A v1 reproduz exatamente o V3 gravado (283/500), o que confere a medida.
- Os falsos restantes do S ficam altos, porque o S é sintético e tem trastes e mãos mais
  difíceis que o real. É só registro: o S não entra no critério.

**Decodificador congelado** neste commit, antes de abrir a M11b.

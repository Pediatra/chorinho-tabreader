# 1023 — O detector sabe quando erra?

**Data**: 2026-10-18. **Estado**: regras a priori. Este documento ganha commit antes da primeira
medida. **O dono aprovou** ("sim, pode seguir com o teste").

**Antecedente** ([1022](1022-decodificador-robusto-e-m11b.md)): o detector com o decodificador
v2 reprovou na M11b, com 59,5 % de certos e 25 % de falsos.
- 14 dos 21 falsos vêm de um ângulo de câmera que o treino não tem: o ponto de vista do
  violonista.
- O plano combinado com o dono prevê um ciclo de revisão: o detector marca, e o dono corrige
  só os quadros duvidosos. Esse ciclo só se paga se o detector **apontar sozinho** onde erra.

## Pergunta

Sinais internos do detector, que não usam rótulo, separam os falsos dos certos o bastante para
que o dono revise só uma fração dos quadros e quase nenhum falso passe sem revisão?

## Sinais (calculados sem rótulo, para cada quadro)

| | sinal | como se calcula |
| --- | --- | --- |
| S1 | discordância sob perturbação | Recorta a faixa de mais **4** perturbações (semente `20261023:P:<id>:<j>`, j = 1..4, com o mesmo `perturbar` da 1021) e decodifica cada uma com a v2. A predição principal e as 4 extras vão para o quadro. A discordância é o máximo, entre as 4, de max(cordas/0,5 vão; nut/0,5 casa; pior traste/0,5 casa), medidos com `erros()` da principal contra cada extra. Uma extra que não acha o braço vale discordância infinita |
| S2 | encaixe dos trastes | 1 − (inliers ÷ números de 1 até o maior inlier), somado a picos não inliers ÷ picos |
| S3 | força dos mapas | menor máximo entre os canais corda1, corda6 e nut (probabilidade), invertido: 1 − valor |

Valor alto em qualquer sinal quer dizer "duvidoso". "Não achou" conta como sinalizado, e um
quadro sinalizado vai para o dono.

## Desenvolvimento (a regra é escolhida aqui)

- **Dados**: os mesmos do D2 da 1022. São os 1.052 quadros R, cada canal medido pelo peso
  `A3_100_<k>_s1` que não o viu, com a perturbação principal `20261022:D2:<stem>`. O rótulo é o
  R (do rastreador).
- **Regras candidatas**: cada sinal sozinho, e o "OU" de S1 com S2. O limiar de cada sinal é
  escolhido para que **no máximo 30 %** dos quadros sejam sinalizados, varrendo os percentis
  50–95 em passos de 5.
- **Escolha**: a regra com **menos falsos não sinalizados** com até 30 % sinalizados. No
  empate, a que sinaliza menos.
- **Registro**: a curva "fração sinalizada × falsos que passam" de cada regra.

## Confirmação (M11b, aberta na 1022, com a regra congelada)

- A regra e os limiares do desenvolvimento ficam congelados num commit antes da confirmação.
- **Quadros**: os 28 quadros da prova 1022, com os 3 pesos `A3_100_todos_s1..3` e a perturbação
  principal `20261021:T:<id>`. São 84 medidas.
- A M11b já foi vista na 1022, mas **não** é usada para escolher regra nem limiar. Ela continua
  sendo um teste para a regra.

**Critério**:

| | passa se |
| --- | --- |
| desenvolvimento | com ≤ 30 % sinalizados, falsos não sinalizados ≤ 2 % de todos os quadros |
| confirmação M11b | falsos não sinalizados ≤ 5 % das 84 medidas (no máximo 4) **e** sinalizados ≤ 50 % |

| resultado | o que fazer |
| --- | --- |
| passa nos dois | o ciclo de revisão é viável. Propor ao dono a fase do ciclo: o detector roda, e o dono confere os sinalizados |
| passa no desenvolvimento e reprova na M11b | os sinais não generalizam para ângulos novos. Registrar e devolver a decisão ao dono |
| reprova no desenvolvimento | o detector não sabe quando erra. Registrar e devolver a decisão ao dono |

**Também reportados, só como registro**:
- a discordância entre as 3 sementes na M11b, que só existe lá;
- quantos dos 14 falsos do lonelypicker são sinalizados.

## Riscos declarados antes

- **O rótulo R é do rastreador**, e ele também erra. Um "falso" no desenvolvimento pode ser
  erro do R, o que pesa contra a regra.
- **A perturbação ainda parte do gabarito.** S1 mede a estabilidade em torno do eixo certo, e
  na fase B o eixo vem do estágio 1.
- **84 medidas são poucas**: 4 falsos que passam equivalem a 5 %.

## Desenvolvimento: resultado (2026-10-18) — **passa**

`python -m tab.maos_braco_confianca dev` (`c1023_dev.json`, 1.525 s), sobre 1.052 quadros.
- A classe v2 confere com o D2 da 1022 em **1.052 de 1.052** quadros: 36 falsos e 1 não achou.

| regra | percentil | limiar | sinalizados | falsos que passam (de 36) |
| --- | --- | --- | --- | --- |
| S1 | 85 | 0,540 | 166 (15,8 %) | 2 (0,19 %) |
| S2 | 70 | 0,050 | 287 (27,3 %) | 14 (1,33 %) |
| S3 | 75 | 0,126 | 263 (25,0 %) | 8 (0,76 %) |
| **S1 ou S2** | 85 / 90 | 0,5402 / 0,0952 | **228 (21,7 %)** | **1 (0,10 %)** |

- **Regra congelada**: S1 > 0,5402071601548553 **ou** S2 > 0,09523809523809523.
  - "Não achou" e uma extra sem braço contam como sinalizados.
  - As constantes ficam em `tab/maos_braco_confianca.py` neste commit, antes da confirmação.
- O único falso que passa é o `q28_-5` (sky guitar).
- Conferi a escolha refazendo a conta à parte a partir do arquivo: o resultado é o mesmo, 228
  sinalizados e 1 falso que passa.
- A estabilidade sob perturbação (S1) carrega quase tudo sozinha. O S2 só pega 1 falso a mais.

## Confirmação M11b: resultado (2026-10-18) — **passa**

`python -m tab.maos_braco_confianca confirmar` (`c1023_confirmacao.json`), rodado depois do
commit fe114eb4, que congelou a regra.
- São 84 medidas: 28 quadros × 3 pesos.

| classe v2 | sinalizada | não sinalizada |
| --- | --- | --- |
| certo | 7 | 43 |
| impreciso | 5 | 8 |
| falso | **21** | **0** |

- **Sinalizados**: 33 de 84 (39,3 %), dentro do limite de 50 %.
- **Falsos que passam**: 0 de 84, dentro do limite de 4. **Passa.**
- Os 15 quadros do lonelypicker (5 × 3) **foram todos sinalizados**. O detector percebe que não
  conhece aquele ângulo.
- Os 51 quadros não sinalizados são 43 certos e 8 imprecisos, sem nenhum falso. Os imprecisos
  ficam entre 0,25 e 0,5 de erro.
- A fração sinalizada sobe de 21,7 % no desenvolvimento para 39,3 % na M11b, o que é esperado
  em canais novos e ângulos novos.

**Conclusão**: o detector sabe quando erra, no desenvolvimento e na M11b. O ciclo de revisão é
viável: o detector marca, e o dono confere só os sinalizados (cerca de 20 a 40 %). Os quadros
sinalizados e corrigidos são justamente os ângulos que faltam no treino.

**Limite que continua valendo**: a faixa ainda parte do gabarito. Na fase B, o eixo vem do
estágio 1, e os sinais precisam ser medidos de novo.

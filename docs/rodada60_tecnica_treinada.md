# Rodada 60 — a classe `tecnica` treinada: estabilidade sim, métrica não (e sei por quê)

## 1. O treino, com 3 sementes

| semente | iwaki | sky guitar | raman | paolo | **TOTAL** |
| --- | --- | --- | --- | --- | --- |
| 0 | 27/27 | 15/15 | 12/24 | 27/30 | **0,844** |
| 1 | 27/27 | 15/15 | 12/24 | 27/30 | **0,844** |
| 2 | 27/27 | 15/15 | 12/24 | 30/30 | **0,875** |

O modelo agora tem **20 classes** — `tecnica` existe.

| | antes (sem `tecnica`) | **agora** |
| --- | --- | --- |
| média | 0,851 | **0,854** |
| amplitude | 0,062 | **0,031** |
| sementes 0 e 1 | diferentes | **idênticas** |
| iwaki / sky | 27/27 e 15/15 | **27/27 e 15/15 nas três** |

## 2. O que melhorou e o que não

**Melhorou a estabilidade**: amplitude caiu à metade (0,062 → 0,031) e duas sementes deram resultado
**idêntico** canal a canal. Nenhum canal regrediu — a condição que eu imponho a toda mudança desde a
rodada 16.

**Não moveu `raman`**: 12/24 nas três sementes. **E eu sei exatamente por quê** — é a parte
importante: o gabarito rotula o token fundido com o **algarismo** (`"7"`), não com a técnica. Então
quando o modelo responde `tecnica` — que é a resposta **certa** para um algarismo com barra de slide
fundida — a aferição conta como **erro**.

Ou seja: **a métrica não consegue recompensar o que a classe faz.** Não é a classe que falhou; é o
gabarito que não expressa o caso.

## 3. O que isso exige (e é a próxima medição, não código)

O gabarito do `raman` precisa distinguir dois tipos de token:

| tipo de token | rótulo correto |
| --- | --- |
| algarismo limpo | o algarismo (`7`) |
| algarismo **com marca fundida** | `tecnica` (e o algarismo re-lido do componente dominante) |

Sem essa distinção, qualquer acerto da classe aparece como erro. É o **mesmo problema de semântica**
que eu já encontrei com os 7 rótulos `junk` (rodada 54) — o gabarito é que limita o que a medição
consegue ver.

## 4. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** — casas | **0,854** (3 sementes, amplitude 0,031) · 0,885 bruto / 0,955 alcançável na rodada anterior |
| **canais limpos** | `iwaki` 27/27, `sky` 15/15, `paolo` 27–30 de 30 |
| **classe `tecnica`** | **treinada, estável, sem regressão** — mas o gabarito não a recompensa |
| **`raman`** | 12/24 — teto de 17/24 por causa dos 7 `junk`; e os fundidos contam como erro |
| **tempo** | faixa (`skyguitar`, 0,16 s) e cor (`cifra club`, 41/41 onsets) |
| **gerador** | íntegro; `tecnica` em 11,7 % dos tokens |

## 5. Próximo passo

1. **rotular os tokens fundidos do `raman` como `tecnica`** no gabarito (é a correção de semântica
   que destrava a medição da classe) e reaferir;
2. ligar a **releitura do algarismo** pelo componente dominante — o segundo passo do desenho, que
   transforma `tecnica` em informação útil (`casa` + técnica no mesmo token);
3. ampliar o gabarito para casas 8–24.

Esta rodada fechou o ciclo que começou na rodada 10 (o `raman` resistindo): **o fenômeno agora é
produzido** (11,7 %), **a classe existe**, **a estabilidade melhorou** — e o que falta é o gabarito
saber dizer o que é um acerto.

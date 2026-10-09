# Rodada 54 — a métrica estava deprimida por 7 rótulos inalcançáveis

## 1. O que a medição do `raman` revelou

| | |
| --- | --- |
| tokens com ≥2 componentes (marca fundida) | **70 de 94 (74 %)** |
| erros | 11 de 24 |
| **erros com ≥2 componentes** | **9 de 11** |

E os erros se dividem em dois grupos bem diferentes:

| caso | quantos | o que é |
| --- | --- | --- |
| `harmonico`/`1` onde o gabarito diz **`junk`** | **5** | fragmentos — inclusive de **2 px de largura** classificados como `1` |
| `harmonico` onde o gabarito diz **`7`** | 3 | a marca de slide fundida no algarismo |
| outros | 3 | — |

## 2. A trava de largura (correção de segurança)

Apliquei em `reconhecer.compativel`: **um algarismo não pode ter menos de 0,22 passo de largura**.
Um fragmento de 2 px num painel de passo 21,6 nunca é dígito.

Efeito medido (mesmo modelo, regra determinística): **85/96 = 0,885** — o melhor número até agora.
**Mas o total não mudou**, e é importante dizer por quê: os fragmentos de 2 px caíam em posições cujo
gabarito diz `junk`, e o modelo **não tem classe `junk`** — errar por `1` ou por `harmonico` conta
igual. A trava é **correção de segurança**, não ganho de métrica.

## 3. A descoberta sobre a métrica

O gabarito do `raman korshun` tem **7 rótulos `junk` em 24**. Como o modelo atual **não tem** essa
classe (eu a removi na rodada 22, quando ela se mostrou uma troca e não um ganho), esses 7 são
**inalcançáveis por construção**:

| métrica | valor |
| --- | --- |
| acerto bruto (96 rótulos, 7 deles inalcançáveis) | **85/96 = 0,885** |
| **acerto sobre os rótulos alcançáveis** (89) | **85/89 = 0,955** |
| `raman`, excluindo os 7 `junk` | 13/17 = 0,76 |

Ou seja: **o número que descreve o reconhecimento é 0,955**, e 0,885 é o número que inclui uma
tarefa que o sistema, por decisão minha, não tenta fazer. Ambos são verdadeiros — e reportar só o
primeiro (ou só o segundo) seria escolher o mais conveniente.

## 4. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** — casas | **85/96 = 0,885** bruto · **85/89 = 0,955** sobre o alcançável |
| **canais limpos** | `iwaki` 27/27, `sky` 15/15, `paolo` **30/30** |
| **o que resta** | `raman` (13/17 sem junk): marca de técnica fundida no token (70 de 94 tokens!) |
| **tempo** | faixa (`skyguitar`, 0,16 s) e cor (`cifra club`, 41/41 onsets) |
| **técnica** | só existe no sintético; em dado real, **fundida no token** — é o defeito medido |

## 5. Próximo passo, agora com o número certo do problema

O `raman` mostra que **74 % dos tokens têm ≥2 componentes** — a marca de técnica fundida não é
exceção, é a regra nesse canal. A correção certa não é uma regra de forma (duas tentativas
falharam): é **separar a marca do algarismo antes de classificar**, ou treinar a marca como classe
própria com o algarismo re-lido do componente dominante.

E antes de mexer: **medir quantos tokens o sintético produziria com marca fundida** — a lição que eu
já aprendi e vou aplicar desta vez.

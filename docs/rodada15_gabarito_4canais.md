# Rodada 15 — gabarito ampliado e o modo de falha localizado

## 1. Gabarito: 66 → 96 glifos, 3 → 4 canais

Rotulei 30 glifos do canal **paolo d'angelo** (passo 16 px), todos legíveis, casas 0, 1, 2, 3 e 5.
O gabarito passou a **96 glifos em 4 canais**.

## 2. Aferição com o mesmo modelo sintético

| canal | acerto | erros |
| --- | --- | --- |
| iwaki | 27/27 = 1,00 | — |
| sky guitar | 15/15 = 1,00 | — |
| raman korshun | 12/24 = 0,50 | `junk→1`, `junk→8`, `7→15` |
| **paolo d'angelo** (novo) | **23/30 = 0,77** | `1→4` (×3), `3→9` |
| **TOTAL** | **77/96 = 0,802** | 19 |

O total caiu de 0,818 para 0,802 porque a medição ficou mais larga — mesmo padrão da rodada 10,
e de novo é a medição melhorando, não o sistema piorando.

## 3. O modo de falha está localizado, e é o mesmo de sempre

As três falhas `1 → 4` do canal novo não são aleatórias. Olhando os recortes:
**no `paolo d'angelo` a corda passa POR CIMA do algarismo**, enquanto no MuseScore (e no meu
gerador) a corda é **cortada** onde o algarismo entra.

Consequência direta: o algarismo ganha um **traço horizontal** que não deveria ter — e a classe
que o modelo escolhe é justamente `4`, que é o algarismo com barra horizontal. É o mesmo
mecanismo do erro da rodada anterior (`1` virando `4`/`5` quando desenhei a barra de slide por
cima do algarismo): **traço horizontal extra no algarismo ⇒ confusão com classes que têm traço
horizontal.**

Isso fecha o diagnóstico das três tentativas falhas: eu estava tentando consertar na geometria
um problema que é de **cobertura do gerador**. O gerador sempre corta a corda; parte dos canais
desenha a corda por cima.

## 4. Correção, agora específica e barata

No `tools/sintetico.py`, o parâmetro que decide "buraco na corda" hoje é fixo. Ele deve virar
**sorteio** entre:

- **buraco** na corda onde o algarismo entra (MuseScore/Guitar Pro — a maioria);
- **corda por cima** do algarismo (paolo d'angelo, e provavelmente outros).

É uma linha de mudança, com efeito medido esperado nas três falhas `1→4`. Vale mais que
qualquer nova regra no extrator — e é exatamente o que a rodada anterior recomendou, agora com
o caso concreto identificado.

Depois disso: **classe de rejeição** para o lixo (`junk→1`, `junk→8`) e a marca de técnica como
classe própria (`7→15`).

## 5. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura, 95 % com cursor |
| (b) gabarito verificado | **96 glifos / 4 canais** |
| (c) classificador multi-classe | **0,802 real**; dois modos de falha identificados e ambos de cobertura do gerador |
| (d) pipeline ponta a ponta | corda, casa, técnica, tempo, compasso e andamento |
| (e) escala nos 3.781 | pendente |

Os dois canais limpos (MuseScore, tema claro e escuro) seguem em **1,00**. As falhas se
concentram nos canais com renderização fora do padrão MuseScore — que é precisamente o que o
gerador precisa cobrir.

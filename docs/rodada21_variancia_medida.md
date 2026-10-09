# Rodada 21 — variância medida e uma regressão sistemática

## 1. Dívida paga: semente fixa, 3 execuções

`tools/sintetico.py` ganhou `--seed` (fixa `torch`, `numpy` e `random`), e criei
`tools/avaliar.py` para a aferição padronizada. Mesmo código, mesmos dados, 320 linhas, 22
épocas:

| semente | iwaki | sky guitar | raman | paolo | **TOTAL** |
| --- | --- | --- | --- | --- | --- |
| 0 | 23/27 | 9/15 | 19/24 | 24/30 | **0,781** |
| 1 | 23/27 | 9/15 | 18/24 | 27/30 | **0,802** |
| 2 | 24/27 | 9/15 | 18/24 | 29/30 | **0,833** |

**Média 0,805 · amplitude 0,052 · desvio entre execuções de até 5 pontos.**

Isso confirma que minha comparação de execução única estava errada, e **calibra o critério**: a
partir de agora, só é ganho o que passar de ~0,05 — e com repetição.

## 2. O achado que o ruído NÃO explica

`sky guitar` deu **9/15 nas três sementes** — exatamente o mesmo resultado. Isso não é variação:
é **regressão sistemática**.

Referência: a mesma linha mediu **15/15** quando o pipeline estava no estado da rodada 16. Entre
lá e aqui, a mudança que ficou no código é o **rótulo `junk`** no gerador (o gancho que eu deixei
para a classe de rejeição): tokens sem par recebem `junk`, e isso cria uma classe que **puxa os
`1` para lixo** — coerente com o que medi na rodada 18 (`sky` caiu para 0,60 quando a classe
existe).

Ou seja: um gancho "inócuo" que eu deixei no gerador **não era inócuo**. Custa 6 das 15 notas de
uma linha verificada.

## 3. O que fazer (próxima rodada, primeiro item)

1. remover o rótulo `junk` do gerador (voltar a `continue`) e **medir com 3 sementes** — se
   `sky guitar` voltar a ~15/15, a regressão está confirmada e o estado bom é restaurado;
2. só então reavaliar qualquer coisa; a lista de "melhorias" das rodadas 16–18 precisa ser
   **refeita** com repetição, porque foi medida com execução única.

## 4. Balanço honesto das últimas rodadas

| afirmação que eu fiz | situação real |
| --- | --- |
| "corda-por-cima: 0,802 → 0,854" | **não demonstrado** (execução única; amplitude é 0,052) |
| "classe de rejeição: 0,854 → 0,865" | **dentro do ruído** |
| "3 tentativas geométricas falharam" | válido — falharam de forma consistente |
| "lixo sintético não gera tokens sem par" | válido e medido (3 em 937), depois corrigido (91 em 30 linhas) |
| luz sobre a **regressão no `sky guitar`** | **novo e sólido**: 9/15 em 3 sementes seguidas |

## 5. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** |
| (b) gabarito verificado | 96 glifos / 4 canais |
| (c) classificador multi-classe | **0,805 ± 0,026**, com regressão sistemática a corrigir no `sky guitar` |
| (d) pipeline ponta a ponta | corda, casa, técnica, tempo, compasso e andamento |
| (e) escala nos 3.781 | pendente |

O número oficial do sistema passa a ser **0,805 (média de 3 sementes)**, não os valores de
execução única que reportei antes. Nada de código foi deixado quebrado: o estado é reprodutível
com `--seed`.

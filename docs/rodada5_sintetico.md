# Rodada 5 — gerador sintético e o bug de tokenização

## 1. Gerador sintético: funciona

`tools/sintetico.py` desenha linhas de tablatura aleatórias cobrindo as famílias medidas
(fundo claro/escuro, corda sólida/tracejada, passo 14–36 px, 2–5 compassos, 8–26 colunas,
acorde de 1–4 notas, cor de voz, casa 0–24, harmônico `<n>`, ligado, rótulo TAB) e depois
**passa cada linha pelo mesmo extrator** (`tabseg.segmentar`) — de propósito, para que a
distribuição de treino seja idêntica à de inferência, cortes da faixa incluídos.

Rendimento: **12.352 glifos rotulados de 300 linhas**, **19 classes** (0–24 inclui números
de 2 dígitos, mais `harmonico`). Treina em segundos na 3060 Ti.

## 2. O bug que o sintético revelou: falta tokenizar

A acurácia de treino ficou em **0,58**, o que é baixo demais para dado sintético — sinal
de rótulo errado, não de modelo fraco. Medi a causa:

| | |
| --- | --- |
| notas desenhadas (30 linhas) | 959 |
| glifos extraídos | 1.380 |
| glifos casados com uma nota | 1.257 |
| **razão glifos/nota** | **1,44** (o ideal é 1,0) |

Motivo: **um token de vários caracteres é extraído como vários componentes**. `12` vira
dois componentes (`1` e `2`), `<7>` vira três (`<`, `7`, `>`), e cada pedaço acaba
rotulado com o token inteiro (`12`, `harmonico`). A rede recebe a imagem de um `1` com o
rótulo `12` — daí ela não aprender.

Isso não é um detalhe do sintético: é o mesmo fenômeno que aparece no dado real (os canais
têm casa de 2 dígitos, `11`, `12`, `14`, e harmônico escrito `<7>`). Ou seja, o sintético
me mostrou de graça um defeito que eu teria encontrado depois de treinar com dado real
rotulado à mão — e aí teria culpado o gabarito.

## 3. Correção identificada (próxima rodada)

Falta uma etapa de **agrupamento em token** entre extrair e classificar:
componentes na **mesma corda** com **intervalo em x menor que ~0,25 do passo** formam um
token único; a classificação passa a ser do token (número de 1–2 dígitos, `<n>`, algarismo
simples), não do componente solto. O extrator hoje entrega componentes; ele precisa
entregar tokens.

Depois disso: retreinar, aferir contra `gold/gabarito.json` e só então ampliar o gabarito
real (hoje 42 glifos, 4 classes — insuficiente para declarar acurácia).

## 4. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura, 95 % com cursor |
| (b) gabarito verificado | 42 glifos / 2 canais (faltam ~260 e as casas 4–24) |
| (c) classificador multi-classe | gerador sintético **pronto**; falta tokenizar, treinar e aferir |
| (d) pipeline ponta a ponta | grade, corda, coluna e tempo prontos; falta casa, técnica e compasso |
| (e) escala nos 3.781 | pendente |

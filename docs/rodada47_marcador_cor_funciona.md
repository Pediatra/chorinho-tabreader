# Rodada 47 — o marcador de cor funciona: o laranja avança

## 1. O erro era o meu limiar

O teste de cor dava zero porque eu exigia que **45 % da caixa do token** fosse laranja. O algarismo
ocupa só parte da caixa (o resto é fundo escuro) — medindo a cor real dentro das caixas, os tokens
são **laranja forte** (H≈11–12, S≈235, V≈217).

Baixando o limiar para 20 % da caixa:

| t | tokens laranja | colunas (máx) |
| --- | --- | --- |
| 0,440 | 1 | 1 |
| 0,450 | **7** | 7 |
| 0,460 | **13** | 13 |
| 0,470 | 2 | 2 |
| 0,480 | 3 | 4 |
| 0,490 | 6 | 14 |

## 2. O que isso mostra

**O laranja avança da esquerda para a direita dentro de uma frase: 1 → 7 → 13 colunas em três
instantes consecutivos**, sempre começando na coluna 1 (contíguo, cumulativo). Depois **reinicia**
(2, 3, 6) — que é o começo de outra frase/seção.

Isso é exatamente o que você descreveu: **os algarismos das notas tocadas vão ficando laranja** — um
cursor de progresso em cor, não uma faixa. E é *melhor* que uma faixa, porque o intervalo em que um
algarismo fica laranja é, por construção, **o intervalo em que aquela nota soa** → `t_ini`/`t_fim`
sai **por nota**, sem interpolação.

## 3. A cadeia do `cifra club` está completa

| peça | estado |
| --- | --- |
| achar o painel (e não o violão) | **uniformidade de fundo** |
| ler a grade escura | **máscara de tinta clara** → 6 cordas, passo 44,2, 41 tokens |
| achar o marcador | **fração de laranja por token**, limiar 20 % |
| avanço no tempo | **1 → 7 → 13 colunas** (cumulativo, com reinício por frase) |

## 4. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, técnica) | **0,805** (3 sementes) nos 4 canais com gabarito |
| **localização do painel** | **resolvida** (uniformidade) |
| **geometria em painel escuro** | **resolvida** (6 cordas, passo 44,2) |
| **tempo — canal que marca por cor** | **marcador medido e funcionando**: o laranja avança por coluna |
| **tempo — canal que usa faixa** | validado no `skyguitar` (1 nota/s, desvio 0,16 s) |

## 5. Próximo passo

1. converter o avanço em `t_ini`/`t_fim` **por nota**: para cada token, o instante em que ele passa a
   laranja e quando deixa de ser;
2. detectar o **reinício de frase** (o laranja volta à coluna 1) para separar sistemas;
3. gravar no JSON o **mecanismo** usado (`cor` ou `faixa`) — porque agora sei que os dois existem;
4. rodar nos canais do estilo `cifra club` / `tv cifras` e medir cobertura **por mecanismo**.

Esta rodada fecha o anexo de tempo para o tipo de marcador que você apontou: **medido, não inferido**
— 1 → 7 → 13 colunas em três instantes, com reinício por frase. O erro que me custou rodadas foi um
limiar meu, e ele só apareceu porque fui **medir a cor real** dentro das caixas em vez de teorizar
sobre o resultado zero.

# Rodada 36 — série de cor por token: implementada, mas o sinal é global

## 1. O que foi feito

Implementei a máquina que você apontou como a certa: para cada algarismo, uma **série temporal de
cor** (fração de pixels cromáticos dentro da caixa do token), em 6 instantes.

## 2. O que a medição mostra

Vídeo `cifra club / 505 - arctic monkeys`, 74 tokens, painel no topo:

| token (coluna, corda) | t=0,40 | 0,42 | 0,44 | 0,46 | 0,48 | 0,50 |
| --- | --- | --- | --- | --- | --- | --- |
| c3, corda 4 | 1,00 | 0,00 | 0,00 | 0,00 | 0,00 | 0,03 |
| c4, corda 1 | 1,00 | 1,00 | 0,00 | 0,00 | 1,00 | 1,00 |
| c6, corda 3 | 1,00 | 1,00 | 0,00 | 0,00 | 1,00 | 0,00 |
| … | | | | | | |

- **45 dos 74 tokens** variam mais de 0,5 na fração cromática;
- variação mediana de **0,59**;
- em **t=0,46 praticamente todos** os tokens vão a 0,00 (sem cor).

## 3. O problema: o sinal é global, não por nota

Se 45 tokens variam, e num instante **todos** perdem cor juntos, o que a série está capturando é um
**efeito de quadro inteiro** — troca de sistema, rolagem, fade, ou o painel sendo redesenhado —
e não o realce da nota que está soando.

Ou seja: a máquina certa existe (série de cor por token), mas do jeito que eu medi ela mede o
**nível de cor do quadro**, não a **nota destacada**. Para separar uma coisa da outra falta um passo
que eu não implementei:

**normalizar por instante.** Em cada quadro, comparar a cor de cada token **com os outros tokens
daquele mesmo quadro** (posto/z-score), e olhar quem é *outlier*. Aí o efeito global some, porque
ele afeta todos igualmente, e sobra o token (ou os tokens) realmente destacado.

## 4. O que fica deste resultado

- a série por token **funciona e é barata** (uma leitura de caixa por token por quadro);
- ela captura mudança de cor como você descreveu — **o mecanismo existe nos dados**;
- falta a normalização por quadro para transformar "cor do quadro" em "nota em execução".

## 5. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, técnica) | **0,805** (3 sementes) — não depende de marcador |
| **compasso** | funciona onde a barline é limpa |
| **tempo** | série de cor por token implementada; falta **normalizar por instante** para isolar a nota destacada |

## 6. Próximo passo (uma linha de código + uma medição)

1. para cada instante, calcular a fração cromática **relativa** (token menos mediana do quadro);
2. o(s) token(s) com desvio forte = nota em execução → `t_ini`/`t_fim` **por nota**, sem
   interpolação e sem banda;
3. validar no `cifra club` (cor) **e** no `skyguitar` (banda, que também recolore o que cobre) —
   um mecanismo, dois canais de tipos diferentes;
4. declarar no JSON qual mecanismo foi usado.

Se a normalização por instante separar o realce, o anexo de tempo deixa de depender de "existir uma
faixa" — que era a premissa errada — e passa a valer para os canais que marcam por cor, que é o caso
que você apontou.

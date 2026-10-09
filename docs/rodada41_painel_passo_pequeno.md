# Rodada 41 — região corrigida, mas o segmentador não pega este painel

## 1. O que eu fiz

Depois de confirmar em imagem que o painel da tablatura do `a banda — chico buarque` está em
**y ≈ 500–890** (e não na faixa de cima, que é o vídeo do violão), rodei:

1. `segmentar` na região correta → **0 linhas, 0 tokens**;
2. diagnóstico das máscaras nessa região.

## 2. O que o diagnóstico mostrou

Região y 490–900, instante t=0,45:

| máscara | tinta | perfil máx | picos | y dos picos |
| --- | --- | --- | --- | --- |
| otsu | 12,4 % | 0,70 | 4 | 1, 25, 32, 41 |
| contraste k=21 | 13,8 % | 0,81 | 3 | 68, 182, 205 |
| contraste k=31 | 11,0 % | 0,72 | 2 | 68, 205 |

**Há linhas fortes** (perfil de até 0,81 = 81 % da largura coberta), mas o detector acha **2 a 4
picos**, e nenhum progressão de 6 linhas. Ou seja: as cordas deste painel estão **muito próximas**
(os picos aparecem entre y 1 e 41 da região) e a minha cadeia de picos (suavização de 3 + exigência
de máximo local) **não separa** linhas com espaçamento pequeno.

Também é relevante: o painel **não ocupa a largura toda** do quadro (o vídeo tem 2220 px e a tab
ocupa ~x 40–1500). Medir cobertura de linha em relação à largura total **subestima** as cordas.

## 3. O que isso significa

O segmentador foi calibrado com:
- recortes herdados (`parts/`), onde a tab ocupa o quadro inteiro;
- painéis de vídeo de outras famílias, com passo de 12–45 px.

Este painel tem **passo pequeno** (~8–13 px), **cordas tracejadas**, **fundo escuro** e **não
ocupa a largura toda**. São quatro diferenças ao mesmo tempo — e nenhuma delas é de modelo: são
parâmetros de detecção de linha.

## 4. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, técnica) | **0,805** nos 4 canais com gabarito |
| **geometria** | funciona em 5 famílias nos recortes; **falha neste painel** (passo pequeno + largura parcial) |
| **compasso** | funciona onde a barline é limpa |
| **tempo** | mecanismo confirmado (branco → laranja); **bloqueado** até o segmentador pegar este painel |

## 5. Próximo passo, concreto

1. detectar o **extenso do painel** (a faixa escura lisa) antes de procurar as cordas — resolve a
   largura parcial e já funciona como portão de "é painel, não vídeo";
2. reduzir a **suavização** e permitir picos mais próximos (passo a partir de ~6 px);
3. repetir o diagnóstico até sair 6 linhas; só então rodar a série de cor;
4. desenhar a caixa do painel em todo resultado — a trava que impede o erro de região de se repetir.

Nada de código foi deixado quebrado, e o mecanismo do marcador (o que faltava descobrir) já está
confirmado em imagem. O que falta agora é o segmentador aceitar este tipo de painel — um problema
de parâmetros, com diagnóstico já feito.

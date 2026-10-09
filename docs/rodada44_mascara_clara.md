# Rodada 44 — a máscara que faltava: tinta mais CLARA que o fundo

## 1. O diagnóstico fechou

No painel do `cifra club`, a binarização pegava **só os algarismos brancos** (3 % de tinta) e
**perdia as cordas cinzas** — por isso nenhum pico de linha. A causa: `mascaras_candidatas` só tinha
a variante **"tinta mais escura que o fundo local"**, que serve para papel claro. Num painel escuro
a tinta é **mais clara** que o fundo.

## 2. A verificação

Painel recortado (y 620–890, x 30–1520), máscara com `d = cinza − fundo_local`, tinta = `d > delta`:

| delta | tinta | perfil máx | **picos** | y dos picos | espaçamento |
| --- | --- | --- | --- | --- | --- |
| 8 | 5,1 % | 0,44 | **6** | 23, 68, 112, 156, 201, 245 | **44** |
| 12 | 4,6 % | 0,40 | **6** | 24, 67, 112, 156, 200, 245 | **44** |
| 18 | 4,0 % | 0,38 | **6** | 24, 68, 112, 156, 200, 244 | **44** |

**Seis picos, espaçamento 44 px** — e as posições batem exatamente com as faixas de uniformidade da
rodada anterior (cordas em y 643, 688, 732, 776, 820, 864 → relativo ao recorte que começa em 620:
23, 68, 112, 156, 200, 244). **A grade do `cifra club` está lida.**

## 3. As três peças que faltavam, todas agora com medida

| peça | o que era | o que é |
| --- | --- | --- |
| **onde está o painel** | faixas fixas de y (que pegavam o violão) | **uniformidade de fundo**: y 640–865, x até ~1500 |
| **cor das cordas** | só "mais escuro que o fundo" | **"mais claro que o fundo"** (painel escuro) |
| **limiar de pico** | 0,30 (cordas tracejadas ficavam fora) | ~0,25 com a máscara certa → 6 picos |

## 4. O que isso destrava

Com a grade lida neste canal, o caminho para o tempo fica aberto, e a máquina já existe:

1. **tokens** na grade (o extrator por faixa de corda);
2. **série de cor por token** (rodada 37) — branco ↔ laranja, comparando cada token com a **própria
   base**, que é como o marcador deste canal funciona (confirmado em imagem na rodada 40);
3. `t_ini`/`t_fim` por nota, direto do vídeo — sem banda, sem interpolação.

## 5. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, técnica) | **0,805** (3 sementes) nos 4 canais com gabarito |
| **localização do painel** | **resolvida**: uniformidade de fundo |
| **geometria no painel escuro do `cifra club`** | **resolvida**: 6 cordas, passo 44 px (medido) |
| **tempo** | mecanismo confirmado; grade destravada; falta ligar a série de cor na grade e medir |

## 6. Próximo passo

1. adicionar a variante **"tinta clara"** a `mascaras_candidatas` (uma linha) e o **recorte pelo
   painel uniforme** como entrada do segmentador;
2. rerodar `segmentar` no painel do `cifra club` → esperado: 6 linhas, passo 44, tokens nas cordas;
3. rodar a **série de cor por token** e medir o avanço do laranja (monotônico no tempo?);
4. desenhar a caixa do painel em todo resultado.

Esta rodada fechou o bloqueio mais longo da série — e fechou com **6 picos medidos**, não com
argumento.

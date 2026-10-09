# Rodada 45 — a grade do `cifra club` está lida

## 1. A correção ligada no código

Adicionei `_contraste_local_claro` (tinta = pixels **mais claros** que o fundo local) e a variante
correspondente em `mascaras_candidatas`. É a máscara que faltava para painel escuro — a original
pegava só os algarismos brancos e perdia as cordas cinzas.

## 2. O resultado, medido

`segmentar` no painel do `a banda — chico buarque` (y 620–890, x 30–1520):

| | |
| --- | --- |
| linhas | **6** — `[24, 68, 112, 156, 200, 245]` |
| passo | **44,2 px** |
| máscara escolhida | `contraste_claro_k21_d12` |
| tokens | **41**, todos centrados nas cordas |
| por corda | 1:3, 2:13, 3:10, 4:7, 5:4, 6:4 |

**É a primeira vez que este painel é lido corretamente.** Todas as tentativas anteriores davam
0 linhas — e as causas foram três, cada uma medida:

| causa | o que era | correção |
| --- | --- | --- |
| região | faixa fixa de y → pegava o **violão** | uniformidade de fundo |
| máscara | só "tinta mais escura" | **"tinta mais clara"** |
| limiar de pico | 0,30 → cordas tracejadas fora | com a máscara certa, 6 picos |

## 3. O que fica destravado

Com a grade lida **neste canal**, o anexo de tempo tem tudo para ser medido:

1. os **41 tokens** com corda e coluna (feito);
2. a **série de cor por token** (implementada na rodada 37) — branco ↔ laranja, comparando cada
   token com a **própria base**, que é como este canal marca (confirmado em imagem na rodada 40);
3. `t_ini`/`t_fim` por nota, sem banda e sem interpolação.

## 4. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, técnica) | **0,805** (3 sementes) nos 4 canais com gabarito |
| **localização do painel** | **resolvida** (uniformidade de fundo) |
| **geometria em painel escuro** | **resolvida e verificada**: 6 cordas, passo 44,2, 41 tokens |
| **tempo** | mecanismo confirmado; grade lida; falta ligar a série de cor e medir |

## 5. Próximo passo

1. usar a **faixa uniforme** como entrada do segmentador (em vez de y fixo) — feito o método, falta
   ligar no `transcrever.py`;
2. rodar a **série de cor** nos 41 tokens e medir se o laranja **avança monotonicamente**;
3. se avançar: `t_ini`/`t_fim` por nota e **declarar o mecanismo** no JSON;
4. desenhar a caixa do painel em todo resultado.

O bloqueio mais longo desta série (oito rodadas entre o primeiro "o painel não é o que eu penso" e a
grade lida) fechou com **6 linhas medidas**, e o caminho para o tempo agora é mecânico: a ferramenta
de cor existe, a grade existe, o mecanismo está confirmado em imagem.

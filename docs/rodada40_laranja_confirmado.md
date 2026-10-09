# Rodada 40 — confirmado no vídeo que você indicou: os algarismos ficam laranja

## 1. O que as imagens mostram

Vídeo `cifra club/clips/a banda - chico buarque ｜ aula de violão completa.mp4` (2220×1080).

**Layout real (medido nos quadros):**

| faixa | conteúdo |
| --- | --- |
| y 0–490 | vídeo do violão (mãos, braço) |
| **y ~500–890** | **painel da tablatura** (fundo escuro, cordas tracejadas, rótulos e/B/G/D/A/E em laranja) |
| y ~890–1010 | letra da música, com o acorde atual em laranja |

**O marcador, confirmado:** no painel da tablatura os algarismos são **brancos** e vão ficando
**laranja** conforme são tocados. Em `t=0,45` uma região contígua grande está laranja (o trecho já
executado); em `t=0,44` e `t=0,46` a maior parte está branca de novo; em `t=0,47` outro trecho
(E7(9), A7, D6(9)) está branco.

É exatamente o que você disse: **não é uma faixa que passa — é o algarismo mudando de cor**,
branco ↔ laranja.

## 2. Por que eu não tinha visto isso

Porque eu Media **a região errada**. Nas rodadas 36–38 eu analisei a faixa `topo` (y 0–400), que
neste canal é **o vídeo do violão** — e as "cores" que eu medi (48 tokens vermelhos) eram madeira e
cordas. Você avisou antes ("cuidado com esse cursor"), e a imagem da rodada 39 confirmou: as caixas
estavam sobre as **cordas do braço**.

A tablatura está na faixa do **meio** (y ~500–890). O meu detector de painel escolheu `topo` porque
as **6 cordas do violão** formam uma grade de 6 linhas quase perfeita — e o portão de conteúdo
(`glifos_centrados`) não distingue trastes de algarismos.

## 3. O que já está pronto e agora tem onde ser aplicado

A máquina que eu construí nas rodadas 36–38 — **série de cor por token** — é a ferramenta certa para
este marcador. O que faltava era:

1. **a região correta** (y ~500–890, não 0–400); e
2. **a categoria certa**: aqui o contraste é **branco ↔ laranja**, e o fundo já tem laranja de
   propósito (rótulos de corda, nomes de acorde, letra). Então a leitura tem de ser **por token,
   comparada com a própria base daquele token** (exatamente o que implementei na rodada 37), e não
   com o quadro inteiro.

Com a região certa, a métrica que eu já tenho deve funcionar: o token cuja categoria passa de
`branco` para `laranja` é a nota em execução, e o intervalo em que ele permanece laranja é o
`t_ini`/`t_fim` **daquela nota** — sem interpolação, sem faixa.

## 4. O que isso conserta e o que ainda falta

| item | situação |
| --- | --- |
| mecanismo do marcador | **identificado e confirmado em imagem** |
| região do painel neste canal | **medida** (y ~500–890) |
| máquina de tempo | já implementada (série de cor por token) — precisa rodar na região certa |
| portão de painel | **ainda frágil**: aceita as cordas do violão como tablatura; precisa do teste de fundo uniforme |
| medições de cor anteriores no `cifra club` | **inválidas** (mediram o violão) |

## 5. Próximo passo

1. **portão de fundo uniforme** (o painel é escuro liso; o vídeo é textura) — para o detector parar
   de escolher o braço do violão;
2. rodar a **série de cor por token** na região y ~500–890 deste vídeo e verificar se o conjunto
   laranja **avança** de forma monotônica (que é o que você descreveu);
3. se avançar: `t_ini`/`t_fim` por nota, direto do vídeo, e **declarar no JSON o mecanismo** usado;
4. desenhar a caixa da região escolhida em todo resultado, para erro de região nunca mais passar
   despercebido por três rodadas.

## 6. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, técnica) | **0,805** (3 sementes) nos canais com gabarito |
| **compasso** | funciona onde a barline é limpa |
| **voz/cor** | o `cifra club` usa laranja para "já tocado" — detectável pela mesma série de cor |
| **tempo** | mecanismo **confirmado**; falta rodar na região correta e medir o avanço |

Sua indicação do vídeo fechou o diagnóstico: **é cor no algarismo, branco → laranja**. Eu tinha a
ferramenta e estava apontando para o lugar errado.

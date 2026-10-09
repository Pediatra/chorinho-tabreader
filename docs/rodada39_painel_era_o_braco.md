# Rodada 39 — a imagem prova: eu estava analisando o braço do violão

## 1. O que a imagem mostra

Desenhei as caixas dos "tokens" sobre a região que eu venho chamando de painel de tablatura no
`cifra club`, em dois instantes (t=0,44 e t=0,50), e olhei.

**As caixas verdes estão sobre as cordas do braço do violão.** A "grade de 6 linhas" que o meu
detector encontrou são as **6 cordas do instrumento**, e os "tokens" são pedaços de corda, trastes e
marcadores de casa — não algarismos de tablatura.

Na imagem dá para ver exatamente isso: o violão de frente, a mão esquerda no braço, as cordas
atravessando o quadro — e as caixas verdes distribuídas sobre elas, junto com o rótulo
`t=0.44 painel=topo tokens=66`.

## 2. O que isso significa para tudo o que eu medi no `cifra club`

| medição | o que ela realmente mediu |
| --- | --- |
| "painel encontrado" | **as cordas do braço do violão** |
| "66–74 tokens" | pedaços de corda/trastes/marcadores |
| "48 tokens vermelhos, 26 sem-cor" | **madeira e cordas do violão** |
| "6–15 tokenns mudam de categoria" | reflexo/movimento da mão e do braço |
| cobertura de "cursor" | madeira (rodada 33) |

Ou seja: as três métricas de cor que eu construí nas rodadas 36–38 estavam medindo **o violão**.
Nada daquilo descreve a tablatura do `cifra club`.

## 3. A causa raiz (e um agravante)

- **Causa:** o braço de um violão tem **6 cordas paralelas**, ou seja, uma "grade de 6 linhas"
  quase idêntica em geometria a uma tablatura. O meu portão de painel aceita as duas.
- **Agravante:** o `glifos_centrados≥3` que eu usei como trava **não ajuda** — trastes, marcadores de
  casa e pedaços de corda também ficam centrados "nas linhas".

O portão precisa de um sinal que **vídeo não tem e papel tem**: **fundo uniforme**. Um painel de
notação é fundo branco (ou preto) liso; um vídeo é textura, pele, madeira, sombra. Medir a
**variância do fundo** (fora das linhas) separa os dois de forma trivial — e teria evitado isso.

## 4. O padrão que se repetiu duas vezes

| rodada | erro | como descobri |
| --- | --- | --- |
| 33 | "cursor" era o **corpo** do violão | olhando o quadro |
| 39 | "tablatura" era o **braço** do violão | olhando o quadro |

Duas vezes o mesmo erro de fundo — **medir uma região sem confirmar o que ela é**. E nas duas vezes
a resposta estava numa imagem de um segundo. Você avisou antes da segunda ("cuidado com esse
cursor"), e eu ainda gastei duas rodadas em métricas de cor sobre o braço.

## 5. Estado do goal, com o que sobra de confiável

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, técnica) | **0,805** — medido nos 4 canais do gabarito, onde eu **conferi** os recortes |
| **geometria** | 163/163 linhas nos recortes herdados; **nos canais de vídeo, o portão de painel é frágil** |
| **compasso** | funciona onde a barline é limpa |
| **voz/cor** | metodologia existe; medições no `cifra club` **inválidas** (mediram o violão) |
| **tempo** | **não resolvido** — e parte do trabalho feito estava sobre a região errada |

O que continua valendo sem ressalva: o reconhecimento de casa (0,805), os 4 canais do gabarito e o
`skyguitar` do tempo. O resto precisa ser remedido **depois** de um portão de painel que rejeite
vídeo.

## 6. Próximo passo, nesta ordem

1. **portão de fundo uniforme** no painel (variância do fundo baixa) — rejeita braço/corpo do violão
   e aceita papel/tela de notação;
2. reencontrar o painel do `cifra club` **de verdade** — a tablatura está em outra faixa (nas suas
   capturas, o estilo Cifra Club tem a tab em fundo escuro com nomes de acorde em laranja);
3. refazer as medições de cor e de tempo **sobre a região certa**;
4. desenhar a caixa do painel escolhido em **todo** resultado, para que esse erro seja visível na
   hora — não três rodadas depois.

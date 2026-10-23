# 1044 — Validadores físicos, várias tentativas e um violão por tomada (sem retreino)

**Data**: 2026-10-23. O pré-registro é commitado antes de qualquer código ou medida.

**A pergunta**: sem treinar nada, dá para tirar mais do detector que já existe? Três ideias do
dono (conversa de 2026-10-23):

1. **Validadores**: o violão tem regras físicas. Um quadro que as viola (braço invertido,
   trastes amontoados, cordas cruzadas) é erro certo, e hoje pode passar.
2. **Tentar de novo**: quando a resposta é suspeita, tentar com outros pesos e outra entrada,
   e ficar com a que obedece à física.
3. **Memória entre quadros**: dentro de uma tomada o violão é o mesmo objeto. Um quadro que
   acerta ensina o que erra.

**Por que agora**: os retreinos de capo canal a canal reprovaram (1041 na 1039, 1042 na 1043).
A 1043 mostrou que os pares erram todos do mesmo jeito no canal novo, e a 1028/1030 mostrou
que um consenso que só aceita deslocamento inteiro limpo nunca age (os erros não são
limpos). A 1044 ataca o resto dos erros sem gastar treino. **O capo em si não é o alvo**: sem
um localizador de capo, ela só pode sinalizar o capo, não acertá-lo (isso é a 1046).

## O que entra

### A. Validadores (só física; nenhum usa o gabarito do quadro)

Medidos sobre a previsão de um quadro, com o braço levado ao eixo nut → corpo:

| validador | regra | erro que pega |
| --- | --- | --- |
| **V1 orientação** | o braço alarga do nut para o corpo: a distância entre as cordas 1 e 6 do lado do nut é menor que do lado do corpo, corrigida pela perspectiva dos trastes (o espaço entre trastes diminui no mesmo sentido em que o braço alarga) | braço invertido |
| **V2 escada** | os espaços entre trastes vizinhos caem para o corpo; a razão entre vizinhos fica perto de 2^(−1/12) ≈ 0,944, com a folga da perspectiva projetiva (`tab.maos.braco.regra`) | trastes amontoados, traste a mais ou a menos |
| **V3 proporção** | espaço do traste n ÷ largura do braço no traste n dentro da faixa física (escala 630–660 mm, nut 42–48 mm, casa 12 de 52–58 mm) | numeração deslizada, braço achatado |
| **V4 cordas** | as cordas 1 e 6 não se cruzam dentro do braço e o vão entre elas é ≥ 8 px | cordas trocadas ou coladas |
| **V5 nut** | a distância nut → traste 1 cabe na escada do V2 (é o primeiro degrau) | nut no capo ou num traste qualquer |

**Os limiares saem do desenvolvimento por uma regra fixa**: cada validador, aplicado **às
marcas do dono** em todos os gabaritos revisados de desenvolvimento, precisa aprovar ≥ 98 %
delas. O limiar é o mais apertado que cumpre isso. Um validador que reprova marca de dono
mais que isso está errado, e não entra.

### B. Tentativas

- **Hipóteses**: os pares já treinados (o antigo `L3_todos_s3` + `A4_100_todos_s1`, o da 1041
  e os 9 da 1042), cada um no quadro original e no quadro espelhado (a previsão volta pelo
  espelho). São 22 hipóteses por quadro.
- **Agrupamento**: duas hipóteses concordam quando o nut e cada traste em comum ficam a
  ≤ ¼ de casa.
- **Regra**: entrega o grupo maior entre as hipóteses que passam V1–V5, **só se** ele tem
  ≥ 2/3 das que passam e ≥ 6 hipóteses. Senão, **sinaliza**. Discordância é sinal, nunca
  sorteio.
- Os sinais da 1023 (S1, S2, S3) e o sinal de nut v2 continuam valendo sobre a hipótese
  entregue.

### C. Um violão por tomada

- **Tomada**: os quadros do mesmo vídeo com o eixo do braço parecido (a definição da
  `tab.maos.braco.consenso`, 1028).
- **Ajuste**: em cada tomada, um só violão (escala e largura) e a posição dele em cada
  quadro. Os trastes dos quadros entregues pela parte B são medidos em casas contra esse
  violão.
- **Regra**: um quadro cuja numeração discorda da tomada por ≥ ½ casa é **sinalizado** (S4b,
  o "k = None" achado na 1030). Um quadro sinalizado pela B que, no violão da tomada, cai na
  mesma numeração da maioria, **continua sinalizado** nesta rodada: corrigir pela tomada é só
  registro (a 1030 mostrou que a correção precisa de medida própria).

## Amostras

- **Desenvolvimento** (limiares da A, conferência do código): todos os gabaritos de braço
  revisados, **menos** a 1043 e o lote novo abaixo. Já vistos; não decidem nada.
- **Prova 1 — lote novo M44, lacrado**: 40 quadros de **8 canais diferentes, 1 vídeo de cada
  e 5 quadros por vídeo**, entre os vídeos nunca usados em gabarito nem treino. Os 8 canais
  são os com menos quadros no gabarito do braço hoje. Semente 20261044. Ninguém olha as
  previsões antes da revisão do dono (~50 min).
- **Emenda (2026-10-23, antes do sorteio):** três dos 8 canais não têm vídeo livre (fora de
  todo gabarito e treino): yunus guitarist e vvxofingerstyletab têm 1 vídeo cada, e os 40 do
  gabriel cryslian já foram usados. Entram os seguintes pela contagem: iwaki e leonardo ramos
  (16 quadros cada) e cifra club (17; empate com guitar dell'arte, desfeito pela ordem
  alfabética). Os 8: rostheo guitar, serge kottelat, robert lunn, transcriptor, paolo
  d'angelo, iwaki, leonardo ramos e cifra club.
- **Prova 2 — a 1043**: gasta para os pares da 1041 e da 1042, mas nova para o método. O
  agente viu os erros de q01–q10 (declarado no documento da 1043). Só registro: sem um
  localizador de capo, o esperado é sinalizar.

## Medida

A referência é o par antigo sozinho (o que o ciclo usa sem capo), nos mesmos quadros.

| critério | onde | o que precisa |
| --- | --- | --- |
| **1. Segurança** | M44 | falsos que passam ≤ os da referência, e ≤ 5 % dos medidos |
| **2. Ganho (mínimo de certos)** | M44 | entregues certos ≥ os da referência + 4 (10 % de 40) |
| **3. Não estragar** | M44 | dos quadros que a referência entrega certos, no máx. 1 sai falso que passa |
| registro | a 1043 | as mesmas contas, por tipo de erro |

- O critério 2 existe porque a 1042 mostrou que um par que sinaliza tudo passa os critérios
  de segurança com 0 certos.
- Também reportados: quantos quadros cada validador derrubou e de que classe eram, quantas
  hipóteses passaram por quadro, e o S4b sozinho.

| resultado | o que fazer |
| --- | --- |
| 1, 2 e 3 passam | a 1044 vira a cadeia do ciclo (A + B + C) |
| 1 e 3 passam, 2 falha | entra só a parte que não perde certos (os validadores como sinal); olhar por canal |
| 1 ou 3 falha | não adotar; olhar quais hipóteses passaram nos validadores e por quê |

## Riscos declarados antes

- **22 hipóteses que erram juntas** concordam no erro. É o caso do capo no kimny: os pares
  aprenderam a mesma coisa. A B não resolve erro comum a todos; a C também não, se a tomada
  inteira erra (v15 da 1030).
- **5 quadros por vídeo** é pouco para a tomada; muitos quadros podem ficar sem tomada e sem
  o efeito da C.
- **Custo**: 22 hipóteses × ~700 quadros de desenvolvimento é previsão, não treino: ~1 h de
  GPU estimada.

## Depois

- **1045**: retreino com sintético com capo, capo colado em quadro real e aumento em cinza
  (se a 1044 e a 1046 não bastarem).
- **1046**: achar o capo por um detector aberto (Grounding DINO, Apache-2.0, ~690 MB),
  **depende do aval do dono para o download**; com o capo achado, o nut sai pela conta.

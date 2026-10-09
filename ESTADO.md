# ESTADO.md — número oficial, o que está medido e o que falta

Documento de entrada do projeto. **Todo número aqui é média de ≥3 sementes**, nunca
execução única — sem isso o mesmo código já deu 0,729 e 0,854. O histórico completo
das 65 rodadas está em [`docs/HISTORICO.md`](docs/HISTORICO.md).

## Número oficial

**0,889 de acerto no gabarito real** — média de 3 sementes (**0,865 / 0,917 / 0,885**),
amplitude **0,052**, sobre **96 glifos rotulados à mão em 4 canais, casas 0–7**.
**Reprodutível**: cada semente dá o mesmo total em execuções repetidas (medido 2× cada).

```bash
python -m tab.sintetico --n-linhas 320 --epocas 22 --seed S --saida artefatos/oficial_S
python -m tab.avaliar --modelo artefatos/oficial_S/glifo_sint.pt
```

| canal | acerto nas 3 sementes | observação |
| --- | --- | --- |
| iwaki (tema escuro) | **27/27 nas três** | |
| sky guitar | 14–15 de 15 | |
| **raman korshun** (slides, lixo) | **17/24 nas três** | estável; composição abaixo |
| paolo d'angelo | 25–29 de 30 | passo 16 px, o painel mais denso |

### O que a remedição corrigiu

O número anterior (**0,892**) acabou ficando a **0,003** de distância — ou seja, ele
estava certo *por sorte*, dentro de um ruído de até 0,05 que ninguém controlava. O ganho
desta rodada não é o número: é ele **agora ser reprodutível**. Quatro correções:

1. **A mesma semente variava 0,052 no treino** (0,927 / 0,896 / 0,948): o cuDNN usa
   `atomicAdd` e não é determinístico por padrão. Agora
   [`tab.sintetico.fixar_semente`](tab/sintetico.py) desliga isso e duas execuções da
   mesma semente dão perda idêntica até a 4ª casa. Ver
   [`docs/decisoes/0001-determinismo-do-treino.md`](docs/decisoes/0001-determinismo-do-treino.md);
2. **a aferição feita dentro do treino avaliava o modelo em modo `train()`**, com o
   `Dropout(0.15)` ligado: os MESMOS pesos davam **0,812 em `train()` e 0,865 em
   `eval()`**, e o treino reportava 0,771 enquanto o disco dava 0,865. Havia duas
   implementações de aferição e a do treino estava quebrada de três modos (índices
   contíguos, imagem errada para `raman`/`paolo`, modo de treino). Agora é uma só;
3. **`raman` é 17/24 nas três sementes, mas não é "17/17 nos algarismos"**: a composição
   medida é **12/17 algarismos + 5/7 acertos de `junk`**. Os 5 `junk` são acertados pela
   **regra de assinatura** (token estreito recusado), não pelo classificador. Total
   igual, erro diferente — o total sozinho não descreve o sistema;
4. **as 5 falhas de algarismo são todas `7`→`5` ou `7`→`15`** (posições 3, 5, 12, 19 e 26
   do `raman`): o `7` daquele canal carrega o traço de técnica e a confusão é
   sistemática, não aleatória. É o alvo mais concreto para a próxima rodada.

Números medidos antes de 2026-10-08 têm **ruído de até ~0,05 embutido**: ganhos históricos
de +0,038 e +0,046 estão dentro desse ruído e não deveriam ter sido tratados como ganho.

## CORREÇÃO (2026-10-09): o "96,5 % com tablatura" está inflado

Gerando montagem para os canais novos, o detector escolheu **piano**
(`violaodecria`), **cabeça do violão com tarraxas** (`shin izumi`) e **corpo do violão**
(`cifra club`) — e chamou os três de tablatura. Os números por canal daquela varredura
**não são medida de tablatura** até o portão ser corrigido: ver
[`docs/decisoes/0005-portao-de-tablatura-aprendido.md`](docs/decisoes/0005-portao-de-tablatura-aprendido.md).
Quatro discriminadores feitos à mão foram testados e **os quatro falharam** (uniformidade,
fração de algarismos, confiança do classificador, espessura de linha).

## 2026-10-09 — primeira saída COM TEMPO, e a ressalva que vem junto

`tab/pipeline.py` fecha o ciclo por **intervalo**: amostra a duração, agrupa os trechos com
notação, transcreve cada um e grava **um JSON e um MusicXML por intervalo** (decisão 0004).
No `sky guitar` (`(henze) nocturno`, intervalo 110,3–313,3 s):

| | painel errado (`meio`, passo 7,6) | painel certo (`topo`, passo 16) |
| --- | --- | --- |
| notas lidas | 40 | **143** |
| exportadas para MusicXML | 25 | 49 |
| tempo | **não medido** | **medido: 39 instantes distintos**, 117–303 s |

**RESOLVIDO na mesma data** (`painel.candidatos_quadro` + série nas cordas detectadas +
fração exata + pulso entre ataques distintos): no MESMO intervalo, a leitura foi de 49
algarismos com confiança 0,43 para **48 de 48 com confiança 0,97**, casas 0–4, zero
recusadas, e o tempo passou a ser medido de verdade (22 ataques, pulso 4,0 s). A causa
raiz era o painel: as três faixas fixas **cortam** a tablatura, e a faixa inteira punha o
vídeo dentro da série do marcador.

**Antes disso, a leitura não era confiável**: 94 das 143 notas (66 %) são não-algarismo e a
confiança mediana dos algarismos é 0,434 — porque a faixa escolhida contém **partitura e
tablatura**, exatamente a armadilha que o dono do projeto descreveu. Ver
[`docs/decisoes/0007`](docs/decisoes/0007-painel-com-partitura-e-tablatura.md). O tempo é
utilizável e declarado; o **conteúdo** das notas não é, e está declarado como tal.

## 2026-10-09 — o tempo por marcador foi CONFERIDO no vídeo

`data/saida/frames/valida_tempo.png` desenha, em três ataques do `sky guitar`
(`(henze) nocturno`), o marcador (linha vermelha na faixa azul) e as notas atribuídas
àquele ataque (caixas verdes). Nos três, o marcador está **sobre as notas atribuídas** —
o acorde de 3 notas em 136,3 s, duas notas em 206,3 s, uma em 290,8 s.

A conferência revelou um defeito: em vídeo-**aula** o professor para para explicar, os
intervalos vão de 1,0 s a 22,5 s e a **mediana** dava BPM 15. O pulso passou a ser o
intervalo mais frequente entre os curtos: **1,5 s → BPM 40**, plausível para demonstração
lenta. Ver [`docs/decisoes/0006`](docs/decisoes/0006-marcador-sem-suposicao-de-cor.md).

## 2026-10-09 — o canal mais difícil: `shin izumi`

Com a cascata de máscaras na busca do painel, o `shin izumi` (que o dono do projeto chama
de tablatura mais difícil do acervo) passou a ser lido:

| medida | valor |
| --- | --- |
| painel encontrado | **nos 6 instantes** (`y822–850`, passo ~21,4, 62–87 glifos) |
| algarismos | 27 de 87 tokens |
| **confiança mediana dos algarismos** | **0,99** |
| casas lidas | 2, 0, 5, 4, 3, 6 |
| não-algarismos | 60 (`junk` 45, `tecnica` 9, `harmonico` 6) |
| tempo | `sem_marcador` — confere com a descrição do canal (não tem marcador) |

**Os 60 não-algarismos não são falha de leitura**: são os círculos, elipses e riscos que o
dono do projeto descreveu (*"números dentro de bolinhas, vários empilhados formando um
elíptico, vários símbolos que ligam os números"*). É o **vocabulário de símbolos** do canal,
que por decisão do projeto é guardado cru para classificar depois — não é dívida de leitura,
é dívida de classificação.

## 2026-10-09 — a faixa do `sky guitar` existe em 8 de 8; o gargalo virou o MOVIMENTO

Levantamento denso corrigido (recorte do painel, 8 vídeos, janela de 120 s a partir de 0,55):
a banda cromática é detectada em **8 de 8** vídeos, com **89–100 % de cobertura** — e a
matiz é **azul (95–110) em sete deles e laranja (10) em um**. O dono do projeto está certo
("sempre tem marcador") e a decisão 0006 se confirma de novo: **a cor varia até dentro do
mesmo canal**.

O que ainda separa: o **julgamento do movimento** — 3 `desliza`/`salta`, 2 `duvida`,
3 `parado`/`erratico`. Então o número "marcador utilizável = 3 de 8" **subconta**: a faixa
está nos oito, e o que falta é decidir bem se ela anda de forma aproveitável.

Sinal de que o julgamento precisa de conserto: o `(aguado) etude in am` saiu **`parado`**
numa execução e o próprio subagente o havia medido como **`salta`** com escada de patamares
(1226→1322→1452→1585→1717→184→326) em outra. Limiar instável entre execuções é defeito.

## 2026-10-09 — o inventário de símbolos: encanamento certo, coleta poluída

As 17 montagens por canal (`data/saida/simbolos/montagem_<canal>.png`) estão legíveis. Li a
do `mr. tabs` (o canal que o subagente apontou como o único limpo — tablatura pura rolando)
e o vocabulário aparece: **algarismo entre parênteses** `(3) (2) (1) (0)` = nota presa,
**arcos** = ligado, **traço diagonal grosso** = slide, e marca em `x` sobre a nota.

**CORREÇÃO de uma afirmação minha**: eu disse que "a montagem precisa de filtro de lixo",
e isso está errado. O `montar_montagem` **já** ordena não-`junk` primeiro
(`_ordem_de_leitura`) e **corta em `max_itens`** — o cabeçalho da folha diz
`mostrando 48 de 321 hashes`. Os `junk 245` são do **canal**, não do que se vê. O que eu li
já era o melhor conjunto.

O defeito que **sobra** é menor e é outro: entre os 48 melhores há **algarismos comuns**
(`5`, `4`, `6`, `0`, `2`) classificados como `harmonico`/`tecnica` — erro do classificador,
não símbolo. Filtrar isso é melhorar o classificador, não a montagem.

E a descoberta estrutural do subagente segue valendo: **dedup por hash não forma
vocabulário** (3.223 ocorrências → 3.221 hashes distintos, porque escala e anti-aliasing
mudam o PNG a cada ocorrência). Contar hash não agrupa nada; o caminho é agrupar por
**forma** (`tab/glyphset.py`), como já é feito com os glifos.

## 2026-10-09 — o portão de tablatura: números fechados (item 2 do objetivo)

Config vencedora: **recortes reais rotulados apenas (sem sintético) + peso de classe**,
12 épocas. Três sementes, tudo medido:

| medida | resultado |
| --- | --- |
| **conjunto de aceitação** (7 casos fixos) | **6/7, 6/7, 6/7** — média 0,857, **amplitude 0** (determinístico); antes era 3/7 |
| **leave-one-channel-out** (pooled) | 0,812 / 0,753 / 0,721 → **média 0,762**, amplitude 0,091 |
| recall de tablatura (LOCA) | 199/309 = **0,644** |

Por canal deixado de fora (média das 3 sementes): cifra club 1,000 · leonardo 1,000 ·
mr. tabs 0,933 · kimny 0,875 · guitar dell'arte 0,854 · iwaki 0,792 · paolo 0,667 ·
**sky guitar 0,656 (recall de tablatura 0,49)** · **pablo romé 0,452**.

**Balanceamento (o que o objetivo pedia), seed 1, LOCA / aceitação:**

| estratégia | LOCA | aceitação |
| --- | --- | --- |
| sem peso | 0,801 | 5/7 |
| **peso de classe, só real** | **0,812** | **6/7** |
| peso + 300 sintéticos/classe | 0,641 | 6/7 |
| peso + 1500 sintéticos/classe | 0,655 | **7/7** |
| peso + 300 negativos sintéticos | 0,763 | 6/7 |
| real só, 22 épocas | 0,721 | — |

**Duas conclusões que importam:**

1. **Dado sintético DERRUBA a generalização neste portão** (0,812 → 0,641): o positivo
   sintético ajuda a passar o conjunto de aceitação e piora o canal deixado de fora. O
   subagente escolheu pelo LOCA, não pela aceitação — decisão metodológica certa.
2. **O portão NÃO está pronto para entrar no pipeline**: 0,762 no canal deixado de fora e
   **recall de 0,49 no `sky guitar`** (o canal do MVP) significa que ele **rejeita metade
   da tablatura** ali. Falha determinística única: as **tarraxas do `shin izumi`** são
   aceitas com p ≈ 0,95 nas três sementes.

Rótulos: 121 → **289** (103 tablatura / 184 não / 2 dúvida), 9 canais. Novos positivos:
`sky guitar` 96 recortes → **65 tablatura**; `iwaki` 72 → **12 tablatura** (60 não).

## 2026-10-09 — julgamento do movimento consertado: patamares, não passos

O `(aguado) etude in am` dava `parado` num recorte e `salta` noutro, com o quociente de
trocas de sentido em **0,333 contra limiar 0,30** — a série tem 3–4 voltas ao início (uma
por linha de tablatura) e ~35 patamares, e **um patamar a mais virava o veredito**.

Conserto em `tempo.resumo`: o sentido passa a ser julgado **no nível dos patamares** (é o
nível em que o mecanismo opera) e os **saltos de volta ao início da linha** (|dx| >
`SALTO_MAX_PX`) não contam como troca de sentido.

| recorte | antes | depois |
| --- | --- | --- |
| painel (`escolher` + `roi_das_cordas`) | `parado` (0,333) | **`desliza`** — 155 pontos, 39 patamares, **0 trocas**, 20,4 px/s |
| candidato antigo | `salta` (0,294) | **`desliza`** — 151 pontos, 36 patamares, **0 trocas**, 20,9 px/s |

Dois erros meus que os testes pegaram: série **totalmente parada** não é `erratico` (é
`parado`; `erratico` é para a série que só tem saltos grandes), e `not todos` estava errado
porque `todos` é uma **lista de zeros** (truthy) — o certo é `not any(todos)`.

## 2026-10-09 — levantamento de marcador: tabela FINAL (regra e recorte consertados)

`tab.marcador`, 6 canais × 8 vídeos, janela de 120 s a partir de 0,55 da duração,
**recorte do painel** e a regra de monotonicidade corrigida:

| canal | desliza | salta | parado | erratico | sem_marc | dúvida | **utilizável** | banda visível | matiz |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **`sky guitar`** | 3 | 1 | 1 | 2 | 0 | 2 | **4/8** | 9 | 108 |
| `guitar dell'arte` | 2 | 0 | 0 | 2 | 5 | 0 | **2/8** | 2 | 62 |
| `iwaki` | 1 | 0 | 0 | 0 | 7 | 1 | **1/8** | 2 | 102 |
| `cifra club` | 0 | 0 | 0 | 0 | 8 | 0 | 0/8 | 0 | — |
| `shin izumi` | 0 | 0 | 0 | 2 | 6 | 0 | 0/8 | 0 | 8 |
| `violaodecria` | 0 | 0 | 2 | 3 | 3 | 0 | 0/8 | 3 | 12 |

**No mesmo instante, mesma janela e MESMA REGRA, o recorte fixo `[300:750]` dava 9
`erratico` e 0 utilizável no `sky guitar`; o recorte do painel dá 4 utilizáveis.** É a
medida limpa do conserto: o que era método virou 4 vídeos, e o que sobra (`parado`,
`erratico`, `dúvida`) é julgamento sobre a banda certa.

Três canais dão **0 utilizável e isso está certo**, conferido contra a descrição do dono do
projeto: `cifra club` (o marcador é **cor no algarismo**; um detector de faixa não vê, por
construção), `shin izumi` e `violaodecria` (não têm marcador). `iwaki` com 1/8 é a
divergência que fica aberta: o dono diz nenhum, a medição acha um (`desliza`, matiz 102).

## 2026-10-09 — escopo do gabarito: 3 canais / 72 glifos (o `raman korshun` saiu)

O dono do projeto decidiu em 2026-10-09: **`raman korshun` toca guitarra elétrica — ele
baixou errado**, e a amostra sai do escopo. Não é perda nem falha: é escopo, e fica
registrado no próprio gabarito (`descartada`) em vez de parecer vídeo faltando.

| | antes | **agora** |
| --- | --- | --- |
| canais | 4 | **3** |
| glifos | 96 | **72** |
| número oficial | 0,889 | **0,949** |

Por semente: `oficial_1` 66/72 = 0,917 · `oficial_2` 71/72 = 0,986 · `oficial_3` 68/72 =
0,944 → média **0,949**. Por canal: `iwaki` 27/27 · `sky guitar` 14–15/15 · `paolo` 25–29/30.

**O 0,949 NÃO é ganho.** O `raman` era o pior canal (17/24) e a conferência fecha exata:
(66+17)/(72+24) = 83/96 = 0,865, o número histórico da semente 1. O que subiu foi a média
porque o denominador mudou — e está declarado assim para ninguém comemorar número que só
mudou de base.

**Achado no caminho**: a aferição estava **quebrada** e ninguém sabia. `imagem_da_amostra`
devolvia None quando o vídeo não existia e o chamador estourava com `TypeError` — o número
oficial tinha deixado de ser calculável. Conserto: o quadro de cada amostra é **cacheado**
em `data/saida/frames/gold/`, e amostra sem quadro (ou descartada) é **declarada e fica fora
da conta** em vez de derrubar a aferição.

## 2026-10-09 — delimitador: a coleta de símbolos refeita (antes × depois)

A coleta foi refeita com o delimitador **e** com a busca de painel consertada. A coleta
velha (a que o dono do projeto viu, com a clave de sol) está arquivada em
`data/saida/simbolos_antes/`; a nova está em `data/saida/simbolos/`.

| | ANTES | DEPOIS |
| --- | --- | --- |
| recortes guardados | 4.562 | **2.233 (−51 %)** |
| símbolos / tokens | 3.223 / 5.150 (62,6 %) | **2.233 / 4.610 (48,4 %)** |
| **tiras de linha** (alt/larg < 0,15) | 34 | **0** |
| `sky guitar` | 154 símbolos | **41 (16,7 %)** |
| `pablo romé` suspeitos | 14 de 431 | fora da lista |
| `tv cifras` | 12 | fora da lista |
| `tv on guitar` | 64 de 406 | fora da lista |
| `shin izumi` | 28 de 240 | **7 de 222** |

Conferido **no olho** na montagem nova do `sky guitar`
(`data/saida/simbolos/montagem_sky guitar.png`): sumiram a **partitura**, o **braço do
violão**, o **teclado** e a **clave**; o que aparece é conteúdo de tablatura — algarismos
(`9`, `4`, `5`, `6`, `1`), **arcos** de ligadura e o resto de lixo são fragmentos finos de
corda (11 de 41, a classe `junk`).

**Limite conhecido da regra atual**: um **arco** de ligadura e um **pedaço de corda** são
ambos largos e baixos — tamanho não separa os dois. O que separa é a **curvatura** (corda é
reta, arco não). É o próximo refinamento.

A leitura **não degradou**, conferido: os 3 modelos oficiais deram os mesmos números
(0,917 / 0,986 / 0,944).

## 2026-10-09 — REGRA DE CURVATURA: medida e REPROVADA antes de entrar no código

Eu ia separar **arco de ligadura** (símbolo) de **pedaço de corda** (lixo) por **retidão**:
a corda é reta, o arco encurva. Medi 196 recortes largos-e-baixos da coleta nova (desvio do
y médio por coluna, normalizado pela altura) e **olhei a prancha**
(`data/saida/frames/largos_baixos.png`):

| grupo | o que apareceu |
| --- | --- |
| **"retos"** (desvio ≤ 0,08) | **foto borrada** (corpo do violão, gradiente de mão) — e dois **símbolos legítimos**: `transcriptor 0,059` = **`44`** e `mr. tabs 0,074` = **`1⌒`** |
| **"encurvados"** (0,29–0,33) | mancha escura com aresta diagonal = **braço/mão do violão** (lixo) |

**Conclusão: retidão NÃO separa essas classes.** A regra teria jogado `44` e `1⌒` fora e
mantido o braço — e o número da coleta até "melhoraria". Não entrou no código, e fica
registrado aqui para ninguém tentar de novo pelo mesmo caminho.

**O que o lixo restante realmente é**, medido no olho: **fragmento de FOTO borrada** (corpo,
mão, sombra do braço), não fragmento de linha. O critério que falta não é forma, é
**nitidez/contraste** — símbolo de tablatura é traço crisp, foto borrada não é. É a próxima
calibração, e ela tem de ser medida antes de virar regra (foi exatamente isto que salvou o
projeto aqui).

Lição que se soma à nº 6 do `AGENTS.md`: **o gargalo é cobertura de dado, não regra de
visão** — seis regras geométricas medidas neste projeto deram zero ou negativo, e esta
seria a sétima.

## 2026-10-09 — delimitador COMPLETO (tamanho + extensão horizontal): número final

Coleta refeita com o delimitador completo, depois de a trava de extensão horizontal entrar:

| coleta | símbolos | tokens | fração |
| --- | --- | --- | --- |
| original (a que o dono viu, com a clave) | 3.223 | 5.150 | 62,6 % |
| só com as regras de tamanho | 2.233 | 4.610 | 48,4 % |
| **com tamanho + extensão horizontal** | **2.188** | **4.573** | **47,9 %** |

**−32 % de símbolos** contra a original, com a leitura **inalterada** (0,917 / 0,986 / 0,944)
e o gabarito sem perder um glifo sequer. As três coletas ficam em disco para auditoria:
`data/saida/simbolos_antes/` (original), `data/saida/simbolos_tamanho/` (só tamanho) e
`data/saida/simbolos/` (final).

**Regras do delimitador, todas medidas** (em `tab/tabseg.delimitar_tokens`):

1. **y**: o token tem de caber no sistema das 6 cordas (margem de 1 passo) — `fora_do_sistema`;
2. **tamanho**: `largura/passo ≤ 2,0`, `altura/passo ≤ 2,0`, `altura/passo ≥ 0,20`. Medido:
   algarismos ficam em largura/passo 0,12–1,39 e o lixo começa em 2,69 — o lixo é **largo**
   (tira de linha, texto, braço), não alto. Motivos: `alto_demais`, `largo_demais`,
   `baixo_demais`;
3. **x**: o token tem de estar dentro da extensão onde as 6 cordas coexistem (21 % dos tokens
   de uma amostra de 1.694 caíam fora) — `fora_da_extensao`. O rótulo `T A B` já era removido
   por regra anterior, verificada;
4. **relatório**: toda recusa é contada por motivo em `Grade.recusados`, aparece nos avisos
   (`delimite=largo_demais:3,...`) e no `to_json` — nada some em silêncio.

**O que continua sendo dívida, e não foi resolvido aqui**: o lixo residual é **fragmento de
foto borrada** (corpo, mão, sombra do braço), não fragmento de linha. A regra de retidão foi
medida e **reprovada** (jogaria fora `44` e `1⌒`), e o critério que falta é **nitidez**.

## 2026-10-09 — algarismo × símbolo: medido, e o limiar de confiança está DESCARTADO

Primeiro gabarito de **símbolo** do projeto (`data/gold/simbolos.json`): 48 recortes
**sorteados** (seed 7) da coleta final, 8 por canal em 6 canais — de propósito não os
"melhores" da montagem, que já vem ordenada. Lidos no olho, folha em
`data/saida/frames/folha_simbolos_1.png`:

| rótulo | n | % |
| --- | --- | --- |
| lixo (fragmento de linha, cruz barline×corda, foto borrada, fundo) | 27 | 56 % |
| **algarismo** | **16** | **33 %** |
| dúvida | 4 | 8 % |
| símbolo de verdade (`(0)` = nota presa) | 1 | 2 % |

**Um terço do que o modelo chama de "símbolo" é algarismo puro** — a queixa do dono do
projeto, quantificada. E a "cruz" que ele viu tem nome: **cruzamento de barline com corda**
(5 dos 48), material de linha, que as regras de tamanho não pegam porque cabe na caixa.

Recuperados os 48 recortes **na convenção do modelo** (casando o `sha1` do PNG ampliado, que
é a chave do dedup) em `data/gold/simbolos_crops/` — 48/48 casados.

### O limiar de confiança NÃO resolve (medido)

`p_digito` = maior probabilidade entre as classes de algarismo:

| grupo | mín | mediana | máx |
| --- | --- | --- | --- |
| algarismo (16) | 0,17 | **0,94** | 1,00 |
| lixo (27) | 0,11 | **0,42** | **0,92** |

| limiar | algarismos recuperados | lixo/símbolo que passaria |
| --- | --- | --- |
| 0,5 | 13/16 (81 %) | 11/28 |
| 0,6 | 12/16 (75 %) | 5/28 |
| 0,8 | **11/16 (69 %)** | 2/28 |

As distribuições se sobrepõem: **não há limiar que separe**.

### E a causa raiz aparece no top-1

O **lixo** (fragmento de linha, cruz, foto borrada) é classificado como **`7` (11 vezes) e
`1` (8 vezes)** — o modelo **vê algarismo em pedaço de linha**. É daí que vem o falso
símbolo (algarismo chamado de `harmonico`) e o falso algarismo (linha chamada de `7`/`1`).

**Consequência**: o caminho é o **discriminador dedicado "isto é algarismo?"** (opção c),
treinado com os 16 algarismos e os 28 não-algarismos já rotulados — não o limiar.

## 2026-10-09 — o discriminador "isto é algarismo?" funciona: 0,879–0,940 no canal deixado fora

Construído com o que estava rotulado: **116 recortes** = 88 positivos (algarismos: os 72 do
gabarito + 16 do gabarito de símbolos) e **28 negativos** (lixo e símbolo), em **8 canais**.
Rede pequena (2 convoluções + 2 lineares, entrada 32×32), peso de classe, 60 épocas.

**Leave-one-channel-out** (o mesmo protocolo do portão — o que importa é generalizar):

| semente | LOCA | pior canal |
| --- | --- | --- |
| 1 | **102/116 = 0,879** | `sky guitar` 6/15 |
| 2 | **109/116 = 0,940** | `cifra club` 6/8 · `sky guitar` 14/15 |

Por canal (semente 1): `paolo` 30/30 · `iwaki` 32/33 · `mr. tabs` 7/8 · `pablo` 7/8 ·
`shin izumi` 7/7 · `tv on guitar` 7/7 · `cifra club` 6/8 · `sky guitar` 6/15.

**Comparação que decide**: o **limiar de confiança** não separa (as distribuições se
sobrepõem de 0,17 a 0,92, medido), e o **discriminador dedicado** chega a 0,88–0,94 no canal
que ele nunca viu. O caminho (c) venceu por medição, não por preferência.

Ressalva honesta: `sky guitar` varia de 6/15 a 14/15 entre sementes — com 15 amostras, esse
canal é o ponto frágil, e o número dele não deve ser lido como estável.

Falta implementar no pipeline (o próximo passo): usar o discriminador como portão do que
vira símbolo, em vez de "a classe não é algarismo".

## 2026-10-09 — discriminador ligado no pipeline: recupera os algarismos, mas tem preço

`reconhecer_linha` ganhou uma **terceira passada**: quando o classificador chama um token de
símbolo, o discriminador decide se ele é, na verdade, algarismo. Ele entra como **função**
(`discriminador=None` por padrão, comportamento antigo intacto) — não como import, porque
`digito` importa `_recortar` de `reconhecer` e o import direto seria ciclo.

**O ganho, medido** nos 16 algarismos rotulados que estavam guardados como símbolo:

| semente | recuperados | valor certo |
| --- | --- | --- |
| 1 | **16/16** | 13/16 |
| 2 | 14/16 | 11/16 |
| 3 | **16/16** | 13/16 |

Hoje esses 16 são **0 lidos** (todos descartados como símbolo) — é o falso símbolo que o dono
do projeto viu. E o erro é **sistemático e único**: **`11` lido como `14`** (#17, #21, #23).
O discriminador acerta a pergunta ("é algarismo"); quem erra o valor é o classificador.

**O preço, derivado do LOCA** (não medido direto — o script do custo falhou e eu não vou
fingir que medi): LOCA 0,879 = 14 erros em 116. Tirando os ~3 do lado dos algarismos, sobram
**~11 dos 28 não-algarismos passando** num canal nunca visto — **~1/3 de falso positivo**, e
cada um desses vira **nota errada**.

**Consequência de projeto**: ligar o discriminador com limiar 0,5 troca "nota jogada no balde
dos símbolos" por "nota errada inventada" em um terço dos casos de lixo. Nenhum dos dois é
bom. O caminho que os números apontam é **limiar conservador** (ex.: 0,8) ou **veredito
gravado em vez de decisão** — o símbolo continua guardado e o token ganha a marca de
"suspeita de algarismo", para o pipeline não inventar nota e o dono poder conferir depois.

## 2026-10-09 — limiar do discriminador: varrido, e o conservador DOMINA

Varredura no protocolo do canal deixado de fora (2 sementes × 8 canais; 176 algarismos,
56 não-algarismos):

| limiar | algarismos recuperados | lixo virando nota errada |
| --- | --- | --- |
| 0,50 | 162/176 (92 %) | 7/56 (12 %) |
| 0,70 | 162/176 (92 %) | 5/56 (9 %) |
| 0,80 | 160/176 (91 %) | 4/56 (7 %) |
| 0,90 | 156/176 (89 %) | 3/56 (5 %) |
| **0,95** | **154/176 (88 %)** | **1/56 (2 %)** |

**Não há trade-off que justifique o limiar frouxo**: subir de 0,5 para 0,95 custa 4 pontos de
recuperação e corta a nota errada em **6×**. E os dois erros não são simétricos — algarismo
não recuperado **continua guardado como símbolo e declarado**; nota errada **corrompe em
silêncio**. Fixado `LIMIAR_DISCRIMINADOR = 0,95` em `tab/reconhecer.py`, com a tabela no
docstring para ninguém precisar refazer a varredura.

## 2026-10-09 — coleta final com o discriminador ligado (e por que a comparação não é direta)

Coleta completou sem erro: **2.213 símbolos em 4.701 tokens (47,1 %)**, 99/102 quadros com
tablatura.

**RESSALVA que impede ler isso como antes/depois**: a coleta anterior (sem discriminador)
deu 2.188/4.573, e a diferença **não** é efeito do discriminador — a **amostra muda entre
execuções** porque o acervo cresce e o sorteio de 3 vídeos por canal pega outros arquivos
(o subagente de símbolos já havia medido isso: mesma semente, listas diferentes em 5+ canais).
Comparar os dois totais seria apresentar variação de amostra como ganho — exatamente o erro
que este projeto já pagou para aprender a não cometer.

**O efeito do discriminador está medido onde a amostra é fixa**: nos 16 algarismos rotulados
que estavam guardados como símbolo, ele recupera **14–16 de 16** (88 % no limiar 0,95) com o
valor certo em 11–13 — e a varredura mostra que 12 % do lixo viraria nota errada no limiar
0,5 contra **2 %** no 0,95. É esse número que sustenta a decisão, não o total da coleta.

## 2026-10-09 — o dono do projeto auditou o gabarito de símbolos: 48/48 de concordância

Ele leu a mesma folha (`folha_simbolos_1.png`) e mandou os rótulos com a legenda dele. O que
eu havia juntado, ele separou:

| rótulo dele | n | o que eu tinha chamado |
| --- | --- | --- |
| algarismo | **16** | algarismo — **mesmos valores** |
| nada (`&`) | 13 | lixo |
| **tablatura (`§`)** | **12** | lixo — inclui as **5 cruzes** (barline × corda) |
| **partitura (`{}`)** | **4** | dúvida/lixo |
| símbolo | 3 | eu só tinha visto 1 |

**Concordância: 48/48 em "é algarismo?" e 16/16 no algarismo E no valor.** Duas leituras
independentes, nenhuma divergência — é a validação mais forte que este gabarito podia ter.

**Dois achados que a auditoria trouxe e que não são sobre símbolo, são sobre a coleta:**

1. **8 % da amostra (4 de 48) ainda é pedaço de PARTITURA** — o delimitador não a exclui em
   todos os painéis (o `{` é pauta de 5 linhas, não tablatura);
2. **25 % é material de linha da tablatura**, e as **5 cruzes** (barline × corda) estão aí:
   elas cabem na caixa (~1 passo × 1 passo) e escapam das regras de tamanho, como eu já
   havia medido. Agora têm nome e contagem.

**E o `(n)` tem significado oficial** (dono do projeto): algarismo entre parênteses = nota
**não tocada de novo** — nota ligada (tie), nota fantasma/toque suave, ou resultado de
técnica (bend `7b(9)`, hammer-on/pull-off `2h(4)`). Gravado em `configs/simbolos.yaml`.

**Remedição com o gabarito auditado** (120 recortes: 88 algarismos, 32 não-algarismos):

| semente | LOCA | `sky guitar` |
| --- | --- | --- |
| 1 | 106/120 = 0,883 | 6/15 |
| 2 | 114/120 = 0,950 | 13/15 |
| 3 | 100/120 = **0,833** | **0/15** |

Média **0,889**, amplitude **0,117** (pior que os 0,078 de antes). **`sky guitar` vai de 0/15
a 13/15 entre sementes** — o canal do MVP é o ponto frágil, e num canal nunca visto o
discriminador pode não reconhecer NENHUM algarismo dele. O consolo medido: com o limiar 0,95
o modo de falha é "não recuperado" (o algarismo segue guardado como símbolo e declarado), não
"nota errada inventada" — que é exatamente por que a escolha conservadora foi a certa.

## Noite de 2026-10-08/09

O acervo cresceu para **3.993 vídeos / 183 GB / 17 canais** (ainda baixando). O que
mudou, com o número que sustenta cada item:

| o que | resultado medido |
| --- | --- |
| **varredura do acervo novo** | **96,5 % com tablatura** (3.855/3.993), em 69,5 min |
| **`sky guitar` (corrigido pelo dono)** | ele apagou os vídeos especiais **sem tutorial**: restaram **417, todos com tablatura**. A varredura dizia 348/440 |
| **por que eu errei os 14 %** | dos vídeos que o scan de **1 instante** chamou de "sem tablatura", **20 de 20 têm tablatura em algum instante** (7 instantes conferidos). O padrão é nítido: nas frações 0,08/0,22/0,36 do vídeo ela quase nunca está; de **0,50 para o fim** está quase sempre. O instante único do scan caía justamente na primeira metade |
| **cursor no quadro inteiro** | 69 de 3.993 — dois erros somados: o portão exige faixa de ≥50 % da **imagem** (540 px) e o cursor tem a altura do painel (~150 px), **e** o portão de matiz fixo (85–140, azul) rejeitava a faixa **laranja** do `sky guitar` (medido: matiz 13–14) — ver [`docs/decisoes/0006`](docs/decisoes/0006-marcador-sem-suposicao-de-cor.md) |
| **cursor no ROI da faixa** | muda onde o detector olha, mas **não basta**: no mesmo vídeo as detecções eram **artefato** (banda parada em x=0–99 por 5 s na borda do painel e bandas em x≈900–1084, fora do painel, que é 0–594). Aquele vídeo **não tem marcador** |
| **`iwaki` tem marcador? (corrigido pelo dono)** | **não**. Amostra de 6 vídeos × 7 instantes: **0 detecções**. O dono está certo; o canal mostra a partitura/tablatura e vai trocando |
| **escolha do painel** | o critério antigo (glifos centrados) escolhia o **braço do violão**; com uniformidade do fundo (0,888 × 0,842) escolhe a tablatura — `tab/painel.py`, implementação única |
| **recorte em x** | exigir 4+ das 6 cordas na mesma coluna estreita o painel ao retângulo real |
| **efeito do recorte na máscara** | mesmo quadro: recorte de 570 px → máscara `otsu` → **3 algarismos reais**; recorte de 1920 px → `contraste_k31_d25` → 36 tokens, **33 de lixo** |
| **ponta a ponta (`sky guitar`)** | **3 notas, corda 5, casas 0 / 2 / 3**, confiança 0,996 / 0,931 / 0,999 — exatamente o que está no quadro |
| **símbolo cru** | implementado: PNG deduplicado por hash, caixas dos componentes, larguras em passo, top-3 de classes |
| **recuperar a casa de dentro do símbolo** | medido e **reprovado**: 0,889 → 0,687 |
| **MusicXML** | exportador pronto (score-partwise 4.0, clef TAB, `staff-tuning`, `technical`), com a duração inferida **declarada** |

**Tempo por travessia (`tab/tempo.py`) — método sim, evidência não.** Eu havia concluído
que o marcador do `iwaki/henze` desliza (~65 px/s) e que isso dava **8 instantes distintos**.
**O dono do projeto corrigiu, e a medição confirmou:** ao longo dos 342 s daquele arquivo as
detecções estão **espalhadas** (x = 230, 285, 341, 548, 638, 690, 844, 1184, 1491, 1527…),
**sem progressão** — um movimento suave de 4 s dentro disso me enganou. Marcador de execução
anda para **um lado**; `tab/tempo.resumo` agora classifica isso como **`erratico`** e o
pipeline não atribui tempo. O método (inverter uma série monotônica) segue correto e testado;
o que faltava era **provar que existe série**, e isso agora é condição de aceitação.

**O inventário de 1 instante é um PISO, não um retrato.** Medido: a tablatura do `sky guitar`
aparece da metade para o fim, então amostrar a **segunda metade** detecta quase tudo com 1–2
instantes, enquanto amostrar cedo subestima. O "96,5 % com tablatura" do acervo inteiro foi
medido com 1 instante em 0,35 da duração: é **piso**. Para presença, `tab.varredura` agora
aceita `--frac-inicio/--frac-fim`.

**Bloqueio do MVP:** o **tempo por nota**, e o obstáculo real é anterior ao código:
**a presença e a semântica do marcador são POR VÍDEO, não por canal**. No vídeo do
`sky guitar` medido, a série `x(t)` do "cursor" é uma banda PARADA na borda do painel
por 5 s mais bandas fora do painel — não há marcador nenhum ali. O que existe de
confiável para esse caso é **áudio** (autorizado pelo dono do projeto) ou a marcação
manual. O MusicXML sai hoje com duração constante **declarada** — honesto, e é o teto
do que se pode afirmar sem marcador.

## O que o JSON entrega

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, coluna, compasso) | 0,892; corda e coluna robustas |
| **técnica** | classe treinada e estável; **sem ganho de acerto** (o modelo já lê o algarismo com o slide junto) |
| **símbolo cru** | **implementado**: todo token não numérico (e todo token fundido) sai com recorte em PNG deduplicado por hash, caixas dos componentes, larguras em passo e top-3 de classes |
| **tempo** | **dois mecanismos**, um medido em cada caso (abaixo) |
| **partitura** (5 linhas) | **fora** desta cadeia — exige OMR próprio |

### Tempo — o marcador VARIA por canal

| mecanismo | canal verificado | resultado |
| --- | --- | --- |
| **faixa vertical** que passa | `sky guitar` | 1 nota/s, desvio **0,16 s** (corrigível para ~33 ms) |
| **algarismo fica laranja** (cumulativo) | `cifra club` | **41/41 onsets**, 8 instantes distintos, intervalo mediano 1,80 s |
| **sem marcador** | ~46% dos vídeos | tempo teria de vir de áudio ou de marcação manual |

O JSON **declara o mecanismo**. No marcador por cor mede-se o **onset**, não a
duração: `t_fim` é o **próximo onset** — o algarismo continua laranja depois de tocado.

## Geometria — o que destravou canais

- **painel claro**: máscara de tinta escura. **painel escuro** (estilo `cifra club`):
  máscara de tinta **clara** (`contraste_claro_k21_d12`);
- **uniformidade de fundo** para achar o painel **e rejeitar o violão** — o braço tem
  6 cordas e engana o detector (medi: caixa de 149 px, matiz 16, era o corpo do violão);
- 5 famílias de renderização tratadas; passo entre cordas de **14 a 45 px**;
- algarismos de **0,38 passo** (cifra club) a 0,6 passo (sky guitar).

## O que funcionou (medido)

| mudança | efeito |
| --- | --- |
| tokenização (juntar componentes da mesma corda) | 0,70 → 0,85 em canal novo; treino 0,58 → 0,985 |
| tamanho de fonte variável no gerador | 0,805 → 0,851 e estabilidade |
| **rejeição de lixo por assinatura do vídeo** | `raman` 12 → 17/24; média 0,854 → **0,892** |
| extração por faixa de corda | 6.882 → 11.594 glifos (os ~4.700 a mais eram acordes fundidos) |
| fallback `ffmpeg` para AV1 | **140 de 319** quadros só eram legíveis por ele |

## O que foi tentado e falhou (não repetir)

| tentativa | efeito |
| --- | --- |
| regra de altura no extrator | 0 (0,818 → 0,818) |
| regra de orientação no extrator | 0 (0,818 → 0,818) |
| trocar arco por barra no gerador | **−0,166** (revertida) |
| relabelar gabarito por proxy geométrico (`partes>=2`) | **−0,1**, duas vezes (revertida) |
| classe `junk` no treino | troca entre canais, não ganho (0,805 = 0,805) |
| `lim_x` por margem de barline | apagaria **506 glifos (4,3%)** em 60 linhas |
| **recuperar a casa de dentro do símbolo fundido** (`casa_recuperada`) | **−0,20** (0,889 → 0,687), pior nas 3 sementes; `paolo` 25→10 |
| margem simétrica no recorte do classificador | **−0,02** com os MESMOS pesos (0,865 → 0,844): pré-processamento é entrada do modelo |

## Lições metodológicas (custaram rodadas)

1. **Semente fixa + determinismo + ≥3 execuções**, reportando média e amplitude. Sem o
   segundo item o primeiro não significa nada (medido: 0,052 de variação na mesma semente).
2. **Meça a amostra antes de gastar treino.**
3. **Confira o significado do número**: "323 notas com tempo" eram **3 instantes**.
4. **Olhe o quadro antes de teorizar** — duas vezes medi o violão achando que era a tablatura.
5. **Rótulo de gabarito só por leitura visual**, nunca por proxy geométrico.
6. **O gargalo é cobertura do gerador, não regra de visão** — medido 6 vezes.

## Ferramentas e artefatos

| caminho | o que é |
| --- | --- |
| `tab/tabseg.py` | grade: 6 cordas, barlines, tokens, 5 famílias + painel escuro |
| `tab/cursor.py` | marcador por faixa (x(t), saltos, sistemas) |
| `tab/sintetico.py` | gerador sintético + treino (`--seed`) |
| `tab/reconhecer.py` | linha → corda, casa, técnica, compasso, tempo |
| `tab/transcrever.py` | vídeo → JSON (painel, grade, marcador, tempo) |
| `tab/avaliar.py` | aferição padronizada — é o número oficial |
| `tab/inventario.py` | varre o acervo (família, painel, marcador) + fallback ffmpeg |
| `tab/caminhos.py` | acervo, gabarito, artefatos: **caminho em um lugar só** |
| `data/gold/gabarito.json` | 96 glifos rotulados à mão, 4 canais |
| `artefatos/` | pesos treinados (**nunca** em `/tmp`) |
| `configs/` | mapa por canal e mapa de símbolos (**a criar**) |

## Próximo passo

1. **símbolos e técnicas por canal** — hoje o extrator **descarta** o símbolo em volta
   do número. Decisão nova: **guardar o glifo cru** e classificar depois, com mapa por
   canal (`configs/simbolos.yaml`);
2. **ampliar o gabarito** para casas 8–24 e mais canais — é o que limita a medição;
3. **tempo onde não há marcador** (~46% do acervo) via áudio;
4. **rodar em escala** nos 3.781 vídeos, com decisão por vídeo;
5. representar **nota ligada `(6)`** e conferir a semântica de cada símbolo por canal.

## Ressalvas (não prometa além disto)

- 96 glifos, 4 canais, **casas 0–7**; aferição **glifo a glifo**, não da música inteira;
- a **casa** dos canais fora do gabarito (ex.: `cifra club`) **não foi aferida** — há
  corda e tempo, casa não;
- **tab ASCII** (Ultimate Guitar) e **partitura de 5 linhas** exigem leitor próprio;
- a métrica **não** cobre técnica nem símbolo: eles são gravados, não aferidos.

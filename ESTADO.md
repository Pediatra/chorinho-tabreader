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

## 2026-10-09 — segunda folha de símbolos (17 canais): o lixo se confirma, e a cruz é 15%

Folha 2 (`data/saida/frames/folha_simbolos_2.png`), amostra **estratificada por canal** — 48
recortes de 17 canais, sem repetir nenhum da folha 1. Lida por mim na taxonomia auditada pelo
dono. Os dois retratos batem:

| rótulo | folha 1 | folha 2 |
| --- | --- | --- |
| algarismo | 33 % | **42 %** |
| `nada` (&) | 27 % | 29 % |
| `tablatura` (§) | 25 % | 25 % |
| partitura ({}) | 8 % | 0 % |
| símbolo de verdade | 2 % | 2 % |
| **LIXO** | **60 %** | **54 %** |

**O padrão mais acionável: as CRUZES (barline × corda) são 7 de 48 = 15 % da coleta** — e
aparecem em cinco canais (`mr. tabs`, `tv on guitar`, `ギタロー`, `tv cifras`,
`serge kottelat`). É um alvo único, mecânico e frequente: cruzamento de traço fino vertical
com traço fino horizontal, que cabe na caixa e por isso passa pelas regras de tamanho.

**E 42 % continua sendo algarismo guardado como símbolo**: o discriminador existe para isso,
mas o número mostra o tamanho do que ainda escapa.

Verdade acumulada: **96 recortes rotulados** (`data/gold/simbolos.json` + `simbolos_2.json`),
em 17 canais, na taxonomia de 5 classes. É a base para trocar o binário "é algarismo?" por uma
decisão de três vias: é algarismo → vira nota; é lixo (nada/tablatura/partitura) → **não vira
símbolo**; o resto → símbolo de verdade, para mapear por canal.

## 2026-10-09 — classificador de LIXO: medido e REPROVADO (0,665 de média)

Com os 96 recortes rotulados (167 amostras na tarefa, porque o gabarito de algarismo entra
como "útil"), treinei o binário **"isto é lixo?"** (lixo = `nada` + `tablatura` + `partitura`):

| semente | LOCA (17 canais) |
| --- | --- |
| 1 | 104/167 = 0,623 |
| 2 | 113/167 = 0,677 |
| 3 | 116/167 = **0,695** |

**Média 0,665 — reprovado**, contra 0,889 do discriminador de algarismo. E a quebra por canal
mostra o defeito estrutural: `paolo d'angelo` dá **9/33, 4/33, 5/33** — as 33 amostras dele são
quase todas algarismo (classe "útil"), e com o canal fora do treino o modelo chama de lixo
quase tudo. O mesmo em `tv=3/10` e `violaode=0/1`.

**Por que reprova**: a classe "útil" mistura duas coisas que não se parecem — **algarismo** e
**símbolo** —, e a classe "lixo" mistura três. Um binário sobre quatro tipos heterogêneos não
aprende a fronteira; o discriminador de algarismo funciona porque a pergunta dele é estreita.

**O que isso deixa claro**: "parar de pegar lixo" não vai sair de um classificador genérico de
lixo. Vai sair de **alvos mecânicos e frequentes**, medidos um a um — e o primeiro é a **cruz
barline × corda, 15 % da coleta**, com 7 exemplos rotulados para testar a regra contra eles.

## 2026-10-09 — a regra da "cruz": testada contra os rótulos e REPROVADA (0 de 6)

Predicado testado antes de entrar em qualquer lugar (foi assim que a curvatura foi reprovada
também): tinta fina, perfil de linha cheio, perfil de coluna cheio, e **quase nada além das duas
hastes** (`resto/tinta ≤ 0,15`) — a diferença para um algarismo como o `4`, que também tem haste
e barra.

| teste | resultado |
| --- | --- |
| cruzes rotuladas que a regra pega | **0 de 6** |
| algarismos do gabarito que ela mataria | 0 de 72 |

**Segura e inútil.** E o diagnóstico mostrou que o problema é a minha **descrição**, não o
predicado: os recortes medem **4 px de largura × 13–27 px de altura** — não são cruzes, são
**hastes verticais finas** (pedaço de barline). A categoria que eu e o dono marcamos é a mesma
(`§` material de linha); o nome é que estava errado.

**O alvo, então, é mais simples e mais frequente do que eu pensava**: haste vertical fina, com
**perfil de linha constante** (é o que a distingue de um `1`, que tem bandeira/base e portanto
perfil variável). E há um furo conhecido no delimitador que a deixa passar: ele rejeita token
**largo** demais e **baixo** demais, mas **não tem largura mínima** — e pôr largura mínima
mataria o algarismo `1` (medido: `largura/passo` de 0,12 a 1,39 nos algarismos).

Próximo teste: `w/h < 0,35` E desvio do perfil de linha `< 0,05`, medido contra os 48 rótulos
da folha 1 e os 72 algarismos do gabarito.

## 2026-10-09 — primeira vitória real contra o lixo: a HASTE FINA entrou no delimitador

Medida antes de entrar, contra a verdade rotulada:

| grupo | n | a regra chama de haste |
| --- | --- | --- |
| `tablatura` (§ material de linha) | 12 | **4** (todas as descritas como "barra") |
| `algarismo` | 16 | **0** |
| `nada` / `partitura` / `símbolo` | 20 | **0** |
| **gabarito de algarismo** | **72** | **0** |

Precisão perfeita: pega **um terço do material de linha** (~8 % da coleta) e **não mata um
único algarismo**. O que a distingue do `1` é a **constância do perfil**: o `1` tem bandeira ou
base, então a largura de tinta varia ao longo da altura; a haste não varia.

Conferido depois de entrar: os 3 modelos oficiais dão **os mesmos números** (0,917 / 0,986 /
0,944) e a trava de deslocamento **não disparou** — nenhum glifo rotulado saiu de lugar.

É a primeira regra geométrica deste projeto que **passa** no teste contra a verdade — as seis
anteriores deram zero ou negativo, e as duas desta semana (classificador de lixo, regra da
cruz) foram reprovadas. A diferença aqui: o alvo é **estreito** (haste, não cruz), foi
**medido antes**, e a precisão é **zero colateral** em vez de "melhora a média".

## 2026-10-09 — o delimitador medido no acervo: 1.119 recusas em 33 quadros

Efeito real das três travas, medido nos MESMOS quadros da coleta (33 quadros com tablatura,
1.482 tokens mantidos):

| motivo | tokens recusados | % das recusas |
| --- | --- | --- |
| **`fora_da_extensao`** (fora da tablatura, em x) | **885** | **79 %** |
| `largo_demais` (tira de linha, texto corrido) | 161 | 14 % |
| **`haste_fina`** (regra desta semana) | **73** | 7 % |
| **total** | **1.119** | |

**A trava que mais trabalha é a horizontal** (79 % das recusas) — a que eu quase não implementei
por não ter medido antes qual seria o efeito. A haste fina rende 73 tokens (2,8 % do que
entraria), coerente com a previsão por rótulo (4 de 12 peças de linha).

Coleta com a haste: **2.273 símbolos / 4.766 tokens (47,7 %)**. O total SUBIU em relação à
anterior (2.213 / 4.701) e isso **não** é efeito da regra — é **deriva de amostra** (o acervo
cresce e o sorteio de 3 vídeos por canal pega outros arquivos). O efeito da regra está nas 73
recusas acima, não no total.

**Furo registrado, e não escondido**: o `inventario.json` **não agrega** as recusas por motivo —
elas existem no `Grade.recusados` e nos avisos do `segmentar`, mas não chegam ao artefato final.
"nada some em silêncio" ainda não vale no inventário; é dívida declarada.

## 2026-10-09 — segunda regra que passa: NITIDEZ (o `nada` é borrado, não tem traço)

O maior pedaço restante era o `nada` (~29 % da coleta: foto borrada e fundo). A suspeita
registrada era **nitidez**, não forma — e ela se confirma. Variância do laplaciano, nos
rótulos auditados, **nas duas escalas** (o ampliado 4× NEAREST da auditoria infla a variância,
e por isso o limiar tem de ser declarado na escala em que vai ser usado):

| grupo | 1× mín | 1× mediana | 4× mín | 4× mediana |
| --- | --- | --- | --- | --- |
| **`nada`** | **22** | **275** | 4 | 120 |
| `simbolo` | 1608 | 11327 | 430 | 2449 |
| `algarismo` | 2030 | 18928 | 488 | 2810 |
| `tablatura` | 751 | 36109 | 114 | 3235 |

Varredura em 4× (n=96): L=100 pega 44 % do lixo com **0 de 40** úteis mortos; L=200 → 64 %;
**L=400 → 76 % com 0 de 40**; L=800 → 92 %, mas mata **5 de 40** (12 %). Em 1× (n=48), o mínimo
útil é 1608 e a mediana do lixo é 275.

**Escolhido 600 em 1×**: 2,7× abaixo do mínimo útil e bem acima da mediana do lixo. Entrou como
`tabseg.e_sem_nitidez` com o motivo `sem_nitidez`.

**Conferido depois de entrar**: os 3 modelos oficiais dão os mesmos números (0,917 / 0,986 /
0,944) e a trava de deslocamento **não disparou** — nenhum glifo do gabarito tem nitidez abaixo
de 600. É a **segunda regra geométrica que passa** no teste contra a verdade (a primeira foi a
haste fina, na rodada passada), e as duas compartilham o mesmo método: alvo estreito, medição
antes do código, e critério de zero colateral.

## 2026-10-09 — as quatro travas medidas juntas: 43 % do que entraria é recusado

Medido nos mesmos quadros da coleta (50 quadros com tablatura, 2.491 tokens mantidos):

| motivo | tokens recusados | % das recusas |
| --- | --- | --- |
| `fora_da_extensao` (fora da tablatura, em x) | 854 | 45 % |
| **`sem_nitidez`** (regra desta rodada) | **673** | **35 %** |
| `largo_demais` (tira de linha, texto) | 290 | 15 % |
| `haste_fina` (regra da rodada passada) | 93 | 5 % |
| **total** | **1.910** | |

**43 % dos tokens candidatos são recusados** (1.910 de 4.401), e o gabarito não perdeu um glifo.

**Validação cruzada que fecha**: a nitidez recusa **673 de 2.491 = 27 %** dos tokens mantidos, e
a leitura no olho das duas folhas dizia que o `nada` era **29 %** da coleta. Dois caminhos
independentes — uma regra geométrica e uma amostra rotulada à mão — dando o mesmo número. Isso
é o tipo de concordância que dá confiança na regra, e não a média de acerto.

## 2026-10-09 — o inventário passa a declarar o que o delimitador recusou (furo fechado)

O `Grade.recusados` existia desde o delimitador, mas **não chegava ao artefato**: o inventário
dizia quantos símbolos havia sem dizer quanto lixo foi barrado — e o objetivo pede que nada suma
em silêncio. Agora cada quadro grava `recusados`, a agregação soma por canal e o resumo do canal
publica `recusados` (por motivo) e `recusados_total`.

Conferido num canal (`mr. tabs`, 3 vídeos, 2 instantes):

    tokens 635 | símbolos 318
    recusados: {haste_fina: 96, sem_nitidez: 5, largo_demais: 3} -> total 104

E o perfil faz sentido para o canal: `mr. tabs` é tablatura pura rolando (muita haste de
barline: 96) e traço crisp (só 5 de nitidez) — as duas regras novas se comportam como se espera
onde se sabe o que esperar.

## 2026-10-09 — coleta com as QUATRO travas: 37 % barrado, e um sinal ruim aberto

Inventário com extensão + largura + haste + nitidez (17 canais, 3 vídeos × 2 instantes):

| medida | valor |
| --- | --- |
| tokens mantidos | 4.748 |
| símbolos guardados | 2.242 (47,2 %) |
| algarismos classificados | 871 (18 %) |
| **recusados pelo delimitador** | **2.826** |
| **% do que entraria, barrado** | **37 %** |

**O perfil confirma a previsão onde eu sabia o que esperar** — e é isso que dá confiança nas
regras: `mr. tabs` (tablatura pura rolando) tem `haste_fina=96` e só `sem_nitidez=5`; `pablo
romé` e `tv cifras` (vídeo-aula) têm `sem_nitidez=222` e `202`; `sky guitar` tem 9 recusas no
total. Cada regra se comporta como se deve no canal em que se sabe o que esperar.

**SINAL RUIM, REGISTRADO E NÃO EXPLICADO**: `mr. tabs` leu **31 algarismos em 635 tokens
(5 %)** — e é o canal de tablatura pura. Ou o painel está sendo escolhido errado nos instantes
amostrados, ou os tokens estão fundidos (a 3ª passada do discriminador só olha token de **um**
componente), ou a fonte daquele canal engana o classificador de forma específica.

Tentei diagnosticar e **não reproduzi**: o quadro que eu peguei deu `passo 5,8` (painel falso,
abaixo do mínimo de 14). O sinal fica aberto, com as três hipóteses nomeadas — e não vou fechar
o goal fingindo que ele não existe.

## 2026-10-09 — CORREÇÃO minha: o "sinal ruim" do `mr. tabs` era leitura errada de campo

Eu havia registrado que `mr. tabs` lia 5 % de algarismo e chamei isso de sinal ruim. **Errado, e
o erro é meu**: eu li o campo `classes` do inventário como se fosse a distribuição de TODOS os
tokens. Ele conta apenas as classes dos **símbolos guardados**.

Medido nos MESMOS instantes da coleta (3 vídeos × 2 frações, passos 24,4–26,2 — painéis válidos):

| medida | valor |
| --- | --- |
| tokens | 635 |
| **algarismos** | **603 (95 %)** |
| top-1 | `7` 174 · `1` 101 · `0` 94 · `3` 87 · `2` 72 · `5` 43 |
| componentes por token | 1 componente: 443 de 635 |

**`mr. tabs` é o canal mais saudável do acervo, não o doente.** E o que eu li (31) são os
algarismos que aparecem **dentro dos símbolos guardados** — 10 % de 318, coerente com o resto.

Conserto no código: o campo ganhou o nome honesto `classes_dos_simbolos` (com `classes` mantido
por compatibilidade) e um comentário dizendo o que ele conta. O campo não estava errado — o
**nome** é que enganava, e eu caí nele.

## 2026-10-09 — partitura: terceira hipótese REPROVADA, e o diagnóstico muda o alvo

Hipótese: pedaço de partitura teria **linhas horizontais paralelas** dentro do recorte (pauta de
5). Medido nos rótulos da folha 1, contando picos do perfil de linha:

| grupo | nº de linhas por recorte |
| --- | --- |
| **partitura (4)** | **0, 0, 1, 3** — recortes de **8 a 13 px** de altura |
| `algarismo` (16) | 1 a **12** |
| `tablatura` (12) | 0 a 13 |

A regra "≥3 linhas" pega **1 de 4** da partitura e marca **24 de 44** úteis (quase todos
algarismos). **Reprovada**, como o classificador genérico de lixo e a regra da cruz.

**O diagnóstico corrige a minha suposição**: os 4 recortes de partitura **não são pedaços de
pauta** — são **fragmentos minúsculos** (8–13 px) do conteúdo da partitura: cabeça de nota,
haste, acidente. Logo o vazamento **não é padrão de token, é de PAINEL**: algum painel de
partitura está passando no teste de 6 linhas, o mesmo mecanismo do "5 linhas da pauta + borda"
que eu já consertei uma vez (decisão 0007).

Com **4 exemplos rotulados** eu não calibro regra de token, e não vou inventar uma. O caminho
certo é achar DE ONDE vêm esses recortes (casando o hash com o painel de origem) e olhar o
painel — que é o passo que ainda não foi feito.

## 2026-10-09 — a origem dos recortes de partitura: DOIS painéis errados, com prova visual

Casei o hash dos 4 recortes de partitura com o painel de origem e desenhei o token nele
(`data/saida/frames/origem_partitura.png`). O resultado fecha o diagnóstico e corrige a
suposição de que seria "um" mecanismo:

| caso | painel de origem | o que a imagem mostra |
| --- | --- | --- |
| #11 `iwaki` | passo 30,0; linhas 291,323,350,376,401,**441** | **a FOTO DO VIOLÃO** — lacunas 32,27,26,25,**40**: razão **1,6**, o limite exato da minha tolerância |
| #15 `mr. tabs` | passo 26,0; linhas 217..347 | **a PARTITURA** (clave de sol, compassos 4 e 13) — 6 linhas regulares (25,26,27,26,26), mas é pauta + 1 linha; **a tablatura está abaixo do painel** |
| #32 `iwaki` | passo 17,4; linhas 283..370 | corpo do violão **e** pauta na borda de baixo (clave visível) |
| #3 `tv on guitar` | passo 14,2 | tablatura — o token é uma marquinha pequena dentro dela |

**São dois buracos distintos, cada um com conserto próprio:**

1. **foto de violão passando no teste de 6 linhas** (`#11`): a razão das lacunas deu **1,6**, que
   é o limite exato de `espacamento_regular`. Apertar de 1,6 para ~1,3 deve fechar — e é
   medível: **não pode custar um glifo do gabarito**;
2. **pauta de 5 linhas + 1 formando grupo regular** (`#15`): é o mecanismo da decisão 0007 de
   novo, e agora existe um caso concreto para calibrar — com a tablatura visível **abaixo** do
   painel escolhido.

**O que NÃO fazer**: continuar procurando regra no token. Os 4 recortes são fragmentos de 8-13 px
(cabeça de nota, haste), e a informação que separa está no PAINEL, não neles.

## 2026-10-09 — apertar a tolerância de espaçamento: MEDIDO e REPROVADO (custa 21 % dos painéis)

A foto do violão passa no teste de 6 linhas com razão **1,6** (lacunas 32,27,26,25,40) — o limite
exato de `espacamento_regular`. Apertei para 1,3 e medi, nos MESMOS 34 quadros da amostra:

| tolerância | quadros com painel |
| --- | --- |
| **1,6** (atual) | **33/34** |
| 1,3 (proposta) | **26/34** — **7 quadros (21 %) perderiam a notação** |

Consertava **um** caso de lixo e custava **21 % das detecções**. **Reprovado** — e o valor volta a
1,6, agora como constante documentada (com o custo medido escrito ao lado) em vez de argumento
fixo escondido. O caso concreto conferido: `espacamento_regular([291,323,350,376,401,441])` dá
`True` em 1,6 e `False` em 1,3; e os painéis reais do gabarito seguem `True` em 1,3.

Quarta hipótese reprovada neste goal (classificador genérico de lixo, regra da cruz, linhas de
pauta no token, apertar a tolerância) — e as quatro custaram **zero**, porque morreram antes de
virar código. A diferença desta: aqui eu tinha o conserto certo para o caso errado, e o número
do custo foi o que barrou.

## 2026-10-09 — validar o painel pelo CONTEÚDO: quinta hipótese REPROVADA

Ideia: painel de pauta/foto rende tokens que **não** são algarismo, e painel de tablatura rende
algarismos — logo a fração de algarismo separaria os dois. Medido nos 34 quadros da amostra,
com os 3 quadros-fonte ruins identificados por prova visual na rodada passada:

| quadro-fonte (ruim) | fração de "algarismo" |
| --- | --- |
| `iwaki` 0,65 (foto do violão) | **0,97** |
| `iwaki` 0,85 (foto) | 0,65 |
| `mr. tabs` 0,85 (**pauta**) | **0,93** |
| os outros 31 quadros | mediana 0,85 |

Os painéis **ruins** têm fração **alta**: o classificador chama de algarismo os tokens da foto e
da pauta. É o mesmo defeito já medido antes — *"o modelo vê algarismo em pedaço de linha"* — e ele
**inutiliza** este sinal. Nenhum limiar separa (0/3 dos ruins pegos em qualquer L testado).

**Quinta hipótese reprovada neste goal**, e a resposta agora é estrutural, não de tentativa:

> O vazamento de partitura (e o de foto) precisa de um **classificador de PAINEL** — "este recorte
> é uma tablatura?" —, que é exatamente o portão construído num goal anterior e medido como
> **insuficiente** (LOCA 0,762, recall de 0,49 no `sky guitar`). As duas correções baratas foram
> medidas e reprovadas (tolerância custa 21 % dos painéis; conteúdo não separa).

## 2026-10-09 — folha 3 (coleta JÁ com as 4 travas): o lixo caiu de 60 % para 56 %, e as CRUZES ficaram

O dono do projeto perguntou, com razão: *"folha 2 está praticamente igual, mudou em quê?"*.
Resposta honesta: **as folhas 1 e 2 não podiam mostrar mudança** — as duas foram sorteadas
**antes** de a haste fina e a nitidez entrarem. A diferença entre elas é só a amostragem
(aleatória em 6 canais × estratificada em 17, sem repetir recorte), e o retrato igual **é o
achado** (duas amostras independentes concordando).

Medi então a composição **depois** das regras, com a folha 3 (amostra aleatória da coleta
atual, 48 recortes, excluindo os 96 já rotulados):

| rótulo | folha 1 | folha 2 | **folha 3 (4 travas)** |
| --- | --- | --- | --- |
| algarismo | 33 % | 42 % | **40 %** |
| `tablatura` (§) | 25 % | 25 % | **33 %** |
| `nada` (&) | 27 % | 29 % | **23 %** |
| partitura ({}) | 8 % | 0 % | **0 %** |
| símbolo de verdade | 2 % | 2 % | **4 %** |
| **LIXO** | **60 %** | **54 %** | **56 %** |

**O que mudou de verdade**: o `nada` caiu (29 % → 23 %) — é a nitidez trabalhando. **O que não
mudou**: o material de linha continua 33 %, e **as CRUZES (`+`) são 7 dos 48 = 15 %**.

**E isso explica uma reprovação minha**: na rodada em que testei a "regra da cruz", os recortes
que eu tinha rotulado como cruz (folha 1) eram, medidos no quadro, **hastes de 4 px** — não
cruzes. Eu **calibrei a regra contra exemplos descritos errado**, e foi por isso que ela deu
0 de 6. A folha 3 tem **7 cruzes de verdade**, na forma certa para o teste.

## 2026-10-09 — o dono marcou 46 símbolos e me deu o vocabulário e as REGRAS

Ele usou a ferramenta de clicar (`data/saida/paineis/marcar.html`, servida em
`http://127.0.0.1:8099/marcar.html` porque o Firefox é **Flatpak** e não enxerga `file://` do
projeto) e mandou 46 marcas com explicação em 6 tablaturas. A regra dele, explícita:

> **"tudo que eu marquei é símbolo válido e o que eu não marquei não é símbolo válido"**

Isso transforma as 6 tablaturas num conjunto **completamente rotulado** — e é o dado que faltava
para inverter a lógica do coletor:

| | quantidade |
| --- | --- |
| **positivos** (marcados por ele, com o texto dele) | **46** |
| **negativos** (tokens longe de toda marca) | **417** |
| tablaturas rotuladas | 6 (23 a 102 tokens cada) |

**Vocabulário que ele nomeou**: `arco_ligadura` 24 · `arco_slide` (arco **com barra no meio**) 15 ·
`arpejo_vertical` 3 · `fórmula de compasso` 2 · `pausa de colcheia` 2.

**E as regras**, que valem mais que os recortes:

1. **Hammer-on × pull-off pela DIREÇÃO dos números**: `7 → 10` é hammer-on, `10 → 7` é pull-off;
2. **Arco com barra no meio = SLIDE**, e não h/p;
3. **A direção do arco (para cima/baixo) não muda o significado**;
4. **`(9)` = nota presa**: não se toca de novo, deixa soar;
5. **Ligadura de prolongamento** (grupo com notas iguais às que já soam) é diferente de h/p;
6. **Linha vertical sobre N cordas = arpejo** dessas N cordas, de cima para baixo;
7. **Pausa de colcheia** e **fórmula de compasso** são **notação**, não técnica — devem ser
   guardadas separadas do símbolo da nota.

Verdade bruta em `data/gold/simbolos_marcados.json` (com o texto dele marca a marca) e os recortes
em `data/gold/simbolos_marcados/{positivos,negativos}/`.

## 2026-10-09 — o aviso do dono CONFIRMADO por medição: a janela corta o arco apagado

Ele escreveu, em 5 marcas: *"arco de ligadura quase sumindo — cuidado pra não cortar coisa demais"*.
Medi, nos 123 positivos, a fração de tinta que encosta na **borda** do recorte e o contraste total:

| grupo | tinta na borda (mediana) | tinta total (mediana) |
| --- | --- | --- |
| **"quase sumindo" (5, todas em `tv on guitar`)** | **0,17** | **0,115** (apagado) |
| os outros 118 | 0,08 | 0,162 |

**O dobro de tinta na borda e menos contraste no total** — a janela de 1,6 × passo está **cortando**
esses arcos. E a causa é geométrica, não de limiar: um arco de ligadura vai de uma nota até a
outra, então ele é **mais largo** que a janela quadrada.

**Experimento decidido (e ainda não feito)**: refazer positivos e negativos com janela mais larga
(2,4 × 1,6 passo, mantendo o MESMO enquadramento nas duas classes) e comparar o LOCA — em especial
o recall nesses 5, que hoje são os candidatos naturais a falso negativo.

## 2026-10-09 — o aviso do dono CONSERTADO: janela larga, recall 123/123 nas três sementes

Ele avisou ("arco de ligadura quase sumindo — cuidado pra não cortar coisa demais"), eu medi
(tinta na borda 0,17 contra 0,08 dos outros) e **refiz os recortes com janela de 2,4 × 1,6 passo**
em vez de 1,6 × 1,6 — as duas classes com o mesmo enquadramento. O mesmo conjunto, mesmas
sementes:

| semente | janela quadrada 1,6 × 1,6 | **janela larga 2,4 × 1,6** |
| --- | --- | --- |
| 1 | 122/123 (0,99) | **123/123 (1,00)** |
| 2 | 123/123 (1,00) | **123/123 (1,00)** |
| 3 | **118/123 (0,96)** | **123/123 (1,00)** |

**Recall perfeito nas três sementes e a instabilidade da semente 3 desapareceu** — ela era o arco
cortado, não o modelo. Falsos positivos seguem em 2–4 de 1076 (0,2–0,4 %). A observação de olho do
dono virou ganho medido de 4 pontos na pior semente.

## 2026-10-09 — o filtro positivo LIGADO (e um bug meu de contagem, corrigido na hora)

`reconhecer_linha` ganhou `filtro_simbolo`: antes de gravar um símbolo, recorta a **janela do
treino** (2,4 × 1,6 passo, centrada no token) e pergunta ao detector. O coletor passa
`filtro_simbolo=carregar()` (`tab/simbolo.carregar`), e `LIMIAR_SIMBOLO = 0,5` foi para
`tab/caminhos.py` — em `tab.simbolo` fecharia ciclo (`reconhecer → simbolo → digito → reconhecer`,
e o import quebrou de fato: 9 erros de coleta).

**Bug meu, pego na hora**: na primeira versão eu gravava o recusado **na mesma chave**
(`simbolo_cru`), para não perder o metadado — e quem conta símbolo pergunta
`"simbolo_cru" in nota`. O total não se mexeu (540) e eu quase registrei "o filtro não muda nada".
Agora o recusado vai para `simbolo_recusado`, e a contagem separa os dois. *Conferir o que o número
conta* — a mesma lição de sempre, agora cometida por mim em código novo.

**Onde o filtro roda, ele é categórico**: nos 4 candidatos de um quadro do `mr. tabs`, as
probabilidades foram **0,000 a 0,016** — todas recusadas, corretamente. O problema é de
**cobertura**: ele rodou em 4 tokens de um quadro que guardou ~50 (480 símbolos em 981 tokens na
amostra de 2 canais, contra 540 antes). Ou seja: **existe outro caminho que grava símbolo sem
passar pelo filtro** — é o próximo alvo, e é de fiação, não de modelo.

## 2026-10-09 — o detector separa no gabarito e FALHA no pipeline: o que já eliminei

Diagnóstico da rodada, com o filtro ligado. Ele separa perfeito no conjunto rotulado (LOCA
123/123, falso positivo ~1 %) e **aprova janelas de DÍGITO no pipeline** com mediana 0,79–0,93
(`shin izumi` 40/40 aprovados, `mr. tabs` 37/40) — numa tablatura que quase não tem símbolo.

**Causas JÁ ELIMINADAS, cada uma por medição:**

1. **Bug de contagem** (eu gravava o recusado na mesma chave `simbolo_cru`): corrigido, e a
   contagem passou a separar;
2. **Cobertura do filtro**: ele roda em todos os candidatos (39 de 39 com probabilidade
   calculada) — não é filtro que "não passa";
3. **Atalho "não é dígito = é símbolo"**: os negativos do treino eram **87 % algarismos**
   (937 de 1076, top-1 `7` em 741). Rebalanceei com os **139 negativos DIFÍCEIS** (tokens que
   não são algarismo) + 200 algarismos sorteados → 339 negativos. O LOCA segue 123/123 com
   falso positivo ~1 %, **e o comportamento no pipeline não mudou**;
4. **Escala/ampliação do recorte** (regra 9: o recorte é parte da medição): testei a mesma
   janela com e sem a ampliação 4× NEAREST do treino — **idênticos** (0,932 e 0,794 nos dois);
5. **Desalinhamento do recorte**: o filtro interno e o meu teste externo concordam nos valores,
   então os dois estão medindo a mesma coisa.

**O que sobra investigar** (e é o primeiro item da próxima rodada): comparar LADO A LADO um
negativo do treino (janela de dígito, rótulo conhecido) com um candidato do pipeline — se
`preparar` normaliza os dois para 32 × 32 e as probabilidades divergem, a diferença está no
CONTEÚDO da janela (contexto, contraste, o que mais cai dentro dela), não no tamanho. A hipótese
mais provável, ainda não medida: os negativos do treino vêm de **tablaturas marcadas**, todas com
passo e render parecidos, enquanto o pipeline entrega render de canais que o detector nunca viu.

## 2026-10-09 — o dono identificou o falso positivo: BARRA VERTICAL não é símbolo (e virou regra)

Ele olhou o `shin izumi` e disse: *"essas barras que estão embaixo dos números na vertical não
significam nada de importante, pode fazer o leitor desconsiderar"*. Era **exatamente** o que o
detector aprovava lá (mediana 0,87). Medido:

| | largura/altura (mediana) |
| --- | --- |
| barras que o detector aprovava no `shin izumi` (100 em 3 quadros) | **0,118** |
| os **123 símbolos verdadeiros** dele | **1,706** |

**Zero de 123** símbolos têm razão abaixo de 0,35. Regra determinística, **antes do modelo**:
`RAZAO_MINIMA_SIMBOLO = 0,35` em `tab/caminhos.py`, aplicada no `reconhecer_linha`. Efeito na
mesma amostra: `shin izumi` **41 → 6** guardados por quadro; `mr. tabs` **39 → 11**.

Por que a `e_haste_fina` do delimitador não pegava: ela exige **perfil constante** (desvio ≤ 0,06)
e estas barras têm desvio **0,218** — passavam. A regra nova usa só a razão, e só no caminho de
SÍMBOLO (o algarismo `1`, que é estreito, não é afetado porque não é candidato a símbolo).

## 2026-10-09 — coleta com filtro positivo + regra da barra: 2.242 → 934 símbolos, e a precisão medida

Coleta completa (17 canais, 3 vídeos × 2 instantes), arquivando a anterior para a comparação ser
pareada:

| | 4 travas (sem filtro) | **com filtro + regra da barra** |
| --- | --- | --- |
| símbolos guardados | 2.242 | **934** (−58 %) |
| tokens | 4.748 | 4.584 (delimitador não mudou) |
| fração símbolo/token | 47,2 % | **20,4 %** |

**Corte por canal** (o filtro age onde há lixo de render): `ギタロー` −80 %, `mr. tabs` −76 %,
`shin izumi` −75 %, `robert lunn` −73 %, `guitar dell'arte` −68 %, `kimny's` −57 %,
`violaodecria` −45 %, `sky guitar` −37 %, `paolo` −35 %, `transcriptor` −24 %, `iwaki` −13 %,
`serge kottelat` −11 %; **`tv on guitar` −0 %**; e **`tv cifras`, `pablo romé` e `cifra club`
zeraram** (no `cifra club` zero é o CERTO: é vídeo com nome de acorde, não tem tablatura).

**Precisão medida no olho**, amostra aleatória de 48 recortes da coleta nova:

| categoria | 4 travas | **filtro + barra** |
| --- | --- | --- |
| **símbolo de verdade** | 4 % | **27 %** (13 de 48) |
| material de linha / lixo | 56 % | **15 %** |
| **algarismo guardado como símbolo** | 40 % | **58 %** (28 de 48) |

**O lixo de linha caiu de 56 % para 15 % e o símbolo verdadeiro subiu de 4 % para 27 % — 7×.** Mas
o alvo do goal (~99 % de precisão) **não foi atingido**: precisão medida = **27 %**. O que sobrou é
o problema ANTIGO, não o novo: **algarismo entrando como símbolo** (58 %). São tokens cuja classe
top-1 não é algarismo (erro do classificador) ou que têm algarismo + símbolo no mesmo token — e o
recorte centrado no token mostra o algarismo.

Próximo alvo, portanto: o caminho de `alvos`/`simbolo_cru` quando o token É (ou CONTÉM) algarismo.

## 2026-10-09 — recorte do componente: implementado, medido, e NÃO resolveu os 58 %

Diagnóstico primeiro (medido, 51 símbolos guardados em 6 quadros):

| tipo | n |
| --- | --- |
| **dígito COM símbolo no mesmo token** (`partes > 1`) | **47 (92 %)** |
| dígito puro (`partes = 1`) | 4 |

Implementei o conserto óbvio: `_guardar_cru` aceita uma **caixa explícita** e o reconhecedor passa
o **componente que não é algarismo** (medido: recortar o token inteiro mostrava o dígito e escondia
o símbolo). Gate verde, sem erro de execução.

**E a verificação no olho REPROVOU**: amostra aleatória de 48 recortes da coleta nova (5 canais,
3 vídeos × 2 instantes) continua com **28 de 48 algarismos = 58 %** — o mesmo número de antes.

**Por que não resolveu** (dedução a partir do que foi medido): dentro de um token fundido, "o
componente que não é algarismo" pode ser **outro algarismo mal classificado** — num `11` fundido os
dois componentes são dígitos, e o classificador por componente erra um deles, que então é escolhido
como "o símbolo". Ou seja: **o problema não está no RECORTE, está na DECISÃO de quem é candidato**.

**Conserto certo, para a próxima rodada**: o candidato a símbolo tem de ser um **componente cuja
classe seja de símbolo** (`tecnica`, `harmonico`, …) — decidido **no nível do componente**, não do
token. Hoje o caminho guarda quando o token tem componentes extras, e é isso que traz o algarismo.

## 2026-10-09 — decisão por componente: também REPROVADA, e a hipótese que sobra é sobre os DADOS

Implementei a decisão **componente a componente** (cada componente vira candidato, com a janela
centrada nele, e quem decide é o detector). Gate verde, rodou, e o número **não se moveu**: 434
símbolos contra 432, e a verificação no olho deu **~34 de 48 algarismos (71 %)** — pior que os
58 % anteriores, dentro da variação da amostra.

**Duas tentativas, dois números iguais.** Isso não é azar: é sintoma de que o problema não está
no caminho de decisão, e sim em algo comum aos dois — **o recorte do treino**.

**A hipótese que sobra, e ela tem prova material**: quando eu desenhei no quadro o que o filtro
aprovava (`filtro_shin.png`), **os retângulos saíram desalinhados** e eu registrei que
`Grade.glifos` **não é** a lista de tokens interna do `reconhecer_linha`. Ora: os meus negativos de
treino foram recortados **centrados em `Grade.glifos`** (`/tmp/janela.py`, `/tmp/hard.py`, e os
anteriores) — ou seja, **podem estar centrados no objeto errado**, e o modelo nunca aprendeu a
janela de dígito que o pipeline realmente produz. Isso explicaria por que ele separa perfeito no
gabarito (cujos recortes são consistentes com o próprio gabarito) e aprova dígito no pipeline.

**Próximo passo, medível**: regerar os recortes de treino a partir dos **tokens internos** do
`reconhecer_linha` (expondo a caixa de cada token no registro, em vez de usar `Grade.glifos`),
retreinar e comparar. Se a hipótese estiver certa, o dígito para de ser aprovado — e é a primeira
vez que o problema estaria nos DADOS e não no modelo.

## 2026-10-09 — hipótese dos DADOS REFUTADA com prova direta (IoU 1,00): o bloqueio é outro

Expus a caixa do token interno (`caixa_token` no registro) e comparei com a caixa que usei para
recortar o treino (`Grade.glifos[i]`), nos MESMOS quadros em que o filtro falha:

| quadro | deslocamento do centro | IoU mediana | IoU < 0,5 |
| --- | --- | --- | --- |
| `shin izumi` 0,85 | 0,0 px | **1,00** | 0 de 41 |
| `serge kottelat` 0,5 | 0,0 px | **1,00** | 0 de 14 |
| `tv on guitar` 0,5 | 0,0 px | **1,00** | 0 de 19 |

**São o mesmo objeto.** Os recortes de treino estavam centrados certo, e o desalinhamento que eu
vi no `filtro_shin.png` era **bug do meu desenho**, não dos dados.

**Sete causas eliminadas por medição neste goal**, nesta ordem: (1) bug de contagem meu;
(2) cobertura do filtro; (3) atalho "não-dígito = símbolo" nos negativos (87 % eram algarismos;
rebalanceado, sem efeito no pipeline); (4) escala do recorte (1× e 4× idênticos); (5) desalinhamento
do desenho; (6) recorte do componente; (7) decisão por componente. **Nenhuma explica** por que o
detector separa 123/123 no gabarito e aprova dígito no pipeline.

**O que sobra, dito sem rodeio**: os recortes do gabarito vêm de 20 tablaturas marcadas; os do
pipeline vêm de outros vídeos dos mesmos canais. A LOCA por canal não mede isso, porque **todos os
recortes dela saem das mesmas tablaturas**. O buraco é de **cobertura de vídeo/render**, e o único
jeito de fechá-lo é o dono marcar nos quadros onde o detector erra — que é exatamente o caso em que
ele mandou pausar e chamá-lo.

## 2026-10-09 — o dono me corrigiu: eu lia só os significados MAIS FREQUENTES das marcas

Ele perguntou se eu estava lendo o JSON inteiro. **Não estava**: os meus resumos usavam
`most_common(6)`/`most_common(8)`, e por isso eu perdi tipos que apareciam poucas vezes. Ao listar
**todos** os ~60 significados das 241 marcas dele, apareceram coisas que eu nunca tinha citado:

- **`mordente`** — e ele já tinha falado: *"quando um arco cobre três ou mais notas chama-se
  tecnicamente mordente"* (6 marcas; **1 delas já estava no arquivo ANTERIOR**, em `T14_serge`);
- **bend / ligadura de expressão** ("linha curva flutuante por cima do número 10");
- **trémolo** ("3 traços inclinados por baixo");
- **ritornello / barra de repetição dupla**;
- **pausas**: semínima, mínima pontuada, semibreve, colcheia;
- **slide-in** (ascendente) e **slide-out** (descendente);
- **`(4)` = pull-off de nota que já vem ressoando**;
- **"7 pequeno = nota quase instantânea"** (grace note);
- e uma instrução: **"T A B não é símbolo nenhum"** → essa marca entrou como **NEGATIVO**, não
  positivo (o rótulo `T A B` aparece em vários canais e nunca é símbolo);
- e outra: **`T06_tv cifras` = "AULA FILTREI ERRADO, JÁ FOI APAGADO — IGNORE"** — era o vídeo que
  ele apagou e cuja marca não entrou; a explicação estava escrita e eu não tinha lido.

**Regra nova de método**: ler **todos** os significados distintos, nunca só os mais frequentes.
Frequência não é importância — `mordente` tinha 1 marca e mudou o vocabulário.

**Conjunto agora**: 356 positivos (era 123) × 652 negativos (352 difíceis + 300 algarismos),
1008 amostras, 3 arquivos de marcas. LOCA novo:

| semente | símbolos pegos | falso positivo | equilibrada |
| --- | --- | --- | --- |
| 1 | 342/356 (0,96) | 102/652 (16 %) | 0,902 |
| 2 | 346/356 (0,97) | 103/652 (16 %) | 0,907 |
| 3 | 341/356 (0,96) | 32/652 (5 %) | 0,954 |

O recall segue alto, mas o **falso positivo subiu de 0,3–1 % para 5–16 %** — e isso **não é
regressão do modelo: é o conjunto ter ficado honesto**. Antes eu media 123 positivos de 20
tablaturas com negativos fáceis; agora são 356 positivos de 37 tablaturas de vídeos novos, com os
abafados, setas longas, mordentes e trêmolo dele — a distribuição REAL do pipeline. O número piorou
porque a medição melhorou.

## 2026-10-09 — A CAUSA: a coleta amostra vídeos que o dono NUNCA marcou (interseção = 1 de 51)

Depois de retreinar com 3× mais dados (356 positivos, 37 tablaturas) e o número da coleta **não se
mexer** (979 símbolos; algarismo ainda ~58 % na amostra no olho), medi o que faltava medir — a
sobreposição entre os VÍDEOS:

| | |
| --- | --- |
| vídeos das tablaturas marcadas pelo dono | **28** |
| vídeos que a coleta amostra | **51** |
| **interseção** | **1** |
| canais que a coleta cobre e NÃO têm nenhuma tablatura marcada | `cifra club`, `guitar dell'arte`, `violaodecria` |

**É isto.** O detector é treinado em 28 vídeos e aplicado em 51 **quase disjuntos**. A validação por
canal (LOCA) **não podia ver isso**, porque ela deixa um CANAL de fora mas todos os recortes dela
saem dos mesmos 28 vídeos. Todo o mistério do goal — "separa 123/123 no gabarito e aprova dígito no
pipeline" — era isto: **o gabarito e o pipeline não compartilham vídeos.**

Consequência prática, e é o próximo passo: extrair tablaturas **dos vídeos que a própria coleta
amostra** (`sorted(glob)[:3]` por canal) e pedir ao dono para marcar ESSES. Aí treino e teste
passam a falar da mesma distribuição — e aí o número vai dizer algo de verdade.

E os 3 canais sem nenhuma tablatura marcada não têm como ser avaliados de jeito nenhum: é preciso
marcar pelo menos um vídeo de cada.

## 2026-10-09 — tablaturas dos vídeos DA COLETA, prontas para marcar (27, todos os 17 canais)

Consequência direta da causa medida (interseção de vídeos = 1 de 51): extraí tablaturas **dos
vídeos que a própria coleta amostra**, usando os instantes exatos do inventário
(`data/saida/simbolos/inventario.json`, campo `amostra`) — 2 por canal, 34 candidatos, **17 canais**.

**Conferi no olho, folha de contato por folha: 27 de 34 são tablatura de verdade.** Os 7 descartados
foram braço de violão/vídeo (`cifra club` 1, `robert lunn` 1, `tv cifras` 2, `pablo romé` 2) e
**1 partitura** (`serge kottelat`, com "let ring" e cabeças de nota em pauta de 5 linhas).

Ficaram marcáveis, em 15 canais: as duas do `guitar dell'arte`, duas do `violaodecria` e **uma do
`cifra club`** — justamente os três canais que **não tinham nenhuma tablatura marcada** e não podiam
ser avaliados de jeito nenhum.

Ferramenta (verificada, 200 na página e nas imagens):
`http://127.0.0.1:8099/coleta_marcar/marcar.html`

Com isto o par treino/teste passa a falar da **mesma distribuição de vídeos** — que é a condição
para o número da coleta significar algo.

## 2026-10-09 — a coleta passa a DECLARAR se treino e teste falam da mesma distribuição

O inventário ganhou `cobertura_de_marcas`: quantos vídeos amostrados têm tablatura marcada, a
fração, e quais canais não têm **nenhuma**. Existe por causa do erro que custou sete hipóteses
(interseção 1 de 51 entre os vídeos do treino e os da coleta): se o inventário tivesse escrito
"0 de 51", eu teria visto no primeiro dia.

Dois bugs meus, pegos na própria verificação do campo — e os dois são a mesma lição:

1. **`basename` de um lado só**: os índices guardam o vídeo em formatos diferentes (uns só o nome,
   outros com o canal na frente: `cifra club/always - blink-182...`). Comparando cru, deu **0 de 6**
   e o campo diria "nenhuma marca" onde havia 3 — número errado por detalhe de string;
2. **legenda errada**: eu listava em `canais_sem_nenhuma_marca` o canal de **qualquer** vídeo sem
   marca, e o campo dizia "cifra club, mr. tabs" **com 3 de 6 marcados**. Agora só entra canal com
   **zero** marcas entre os amostrados.

Conferido depois de corrigir: `{videos_amostrados: 6, videos_com_tablatura_marcada: 3, fracao: 0,5,
canais_sem_nenhuma_marca: []}`. **Número certo com legenda certa** — porque número certo com
legenda errada é a mesma armadilha que me fez acusar o `mr. tabs` de ler 5 % de algarismo.

## 2026-10-09 — TRÊS bugs meus no mesmo campo, e o número que ele passou a mostrar

O campo `cobertura_de_marcas` levou três correções minhas na mesma rodada, e as três são a mesma
lição — **número certo com legenda errada é a armadilha que já me pegou quatro vezes**:

1. `basename` de um lado só (os índices guardam o vídeo em formatos diferentes) → dizia 0 de 6 onde
   havia 3;
2. listava em `canais_sem_nenhuma_marca` o canal de **qualquer** vídeo sem marca → dizia "cifra
   club, mr. tabs" com 3 de 6 marcados;
3. **deduplicava só os marcados**, então vídeo sem marca contava 2× (os 2 instantes da amostra) →
   `videos_amostrados: 82` para **51** vídeos de verdade.

Corrigido e conferido (`51` vídeos, `20` com tablatura entregue, fração **0,392**, nenhum canal sem
marca). E o mais importante: **esse número era 1 antes de eu extrair as tablaturas dos próprios
vídeos da coleta** — ou seja, o alinhamento treino/teste, que era 1 de 51, já subiu para 20 de 51
**sem o dono marcar nada ainda**, só por eu ter ido buscar os vídeos certos.

## Tentativa de trava de FORMA (sem o dono), medida e NÃO conclusiva

Procurei uma assinatura geométrica que separasse os 356 símbolos dos negativos, como a barra
vertical separou (razão < 0,35):

| feature | POSITIVOS (mediana) | NEGATIVOS (mediana) | separa? |
| --- | --- | --- | --- |
| aspecto w/h | 1,52 | 1,50 | **não** |
| tinta (fração) | 0,173 | 0,327 | parcial (p10 se sobrepõe: 0,133 × 0,107) |
| componentes | 4 | 2 | parcial |

Nenhuma separa sozinha. Uma **combinação** (tinta baixa **e** ≥3 componentes) poderia separar, mas
isso exige varredura que eu **não rodei** — e não vou apresentar como se tivesse.

## 2026-10-09 — o número que resume o goal: precisão 77–91 % no treino, 27 % na coleta

Consolidação dos dois lados da mesma medida (não é medição nova — é juntar o que já estava medido):

| onde | recall | **precisão** |
| --- | --- | --- |
| vídeos **marcados** pelo dono (onde o detector foi treinado) | 0,96–0,97 | **0,77 / 0,77 / 0,91** (sementes 1/2/3) |
| vídeos da **coleta** (que ele não marcou) | — | **0,27** (13 de 48 no olho) |

Precisão = TP/(TP+FP), dos números do último LOCA (342/102, 346/103, 341/32).

**O detector não é ruim: ele é ruim ONDE NÃO FOI TREINADO.** 27 % contra 77–91 % é a distância
entre os 28 vídeos marcados e os 51 que a coleta usa. Isso fecha a explicação do goal inteiro e
mostra que o caminho não é mexer no modelo — é **cobertura de vídeo**, como a lição 6 do projeto
diz desde o começo.

## 2026-10-09 — as marcas nos vídeos DA COLETA: precisão 89–91 % (era 27 %)

O dono mandou **200 marcas em 22 tablaturas (C01–C27)** — e com uma ordem: *"leia tudo, não me
engane novamente"*. Li a lista **inteira**, sem resumo por frequência, e por isso vi coisas que os
resumos esconderiam:

- **`traço a ser ignorado` (24 marcas)** e **`TAB` / `TAB TEXTO` (7)** — ele NOMEOU os negativos.
  Foram para o conjunto como negativos, não positivos;
- **duas reclamações de qualidade, e as duas são ERRO MEU de extração**:
  `C05_iwaki` — *"isso é uma partitura, algo de errado não está certo"* (eu extraí uma PAUTA achando
  que era tablatura) → **excluída**;
  `C14_robert lunn` — *"o recorte dessa tablatura está errado, tá faltando a última linha"* (o meu
  `roi_das_cordas` cortou a 6ª corda) → **excluída**;
- tipos que eu não tinha: **vibrato (`~`)**, **appoggiatura/grace note** (o "14 pequeno"), **notas
  fantasma em parênteses**, **harmônico natural em bloco (oval envolvendo o acorde)**, **harmônico
  com `<>`**, **slide off**, **pausas de semínima** (o "Z"/"3" estilizado), **compasso 5/4**,
  **h → hammer on**, e a **ligadura de sustentação cruzando compasso** (arcos grandes do 67 para o 68).

**Conjunto**: 523 positivos (era 356) × 880 negativos (530 difíceis + 350 fáceis), de 22 tablaturas
dos vídeos da coleta. LOCA:

| semente | símbolos pegos | falso positivo | **precisão** |
| --- | --- | --- | --- |
| 1 | 511/523 (0,98) | 51/880 (6 %) | **0,91** |
| 2 | 504/523 (0,96) | 61/880 (7 %) | **0,89** |
| 3 | 508/523 (0,97) | 51/880 (6 %) | **0,91** |

**89–91 % de precisão nos vídeos que a coleta usa**, contra **27 %** medidos antes — e o recall
segue 0,96–0,98. A distância entre "onde foi treinado" e "onde é usado" era o problema inteiro, e
ela fechou.

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

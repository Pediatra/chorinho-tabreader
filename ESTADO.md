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

## 2026-10-09 — coleta com o modelo alinhado: precisão no olho 29 %, e o motivo é o RECORTE SALVO

A coleta rodou com o detector treinado nos vídeos dela (523 positivos, precisão 0,89–0,91 no LOCA):
**942 símbolos em 4.646 tokens (20,3 %)**. Amostra de 48 no olho:

| categoria | medição no olho |
| --- | --- |
| símbolo de verdade (arcos, slides, `X`, `(2)`, ornamento) | ~14 de 48 = **29 %** |
| algarismo guardado como símbolo | ~28 de 48 = **58 %** |
| lixo/notação | ~4 de 48 = 8 % |

**O LOCA diz 89–91 % e a coleta mostra 29 %** — a mesma contradição de sempre, agora com o par
treino/teste já alinhado por vídeo. E a explicação, desta vez, é a que eu deveria ter visto antes:

> **A decisão é feita na JANELA LARGA (2,4 × 1,6 passo, centrada no token) e o PNG salvo é a CAIXA
> JUSTA do token.** Num token fundido de dígito + símbolo, a janela contém o arco (e o detector
> aprova com razão), mas a caixa justa contém o DÍGITO. O que eu julgo na amostra é o recorte
> salvo — então eu estou julgando o recorte errado, não a decisão.

Isso reconcilia **tudo**: o LOCA alto (mede a decisão), a amostra cheia de dígito (mede o recorte),
e as duas tentativas anteriores de "recortar o componente" (que falharam porque escolhiam o
componente pela CLASSE, e um dígito de um `11` fundido era escolhido como símbolo).

**Próximo passo, medível**: salvar **a mesma janela que o detector julgou** (ou o componente
aprovado **com a vizinhança**), em vez da caixa justa do token — e remedir no olho. Se a amostra
passar a mostrar arcos em vez de dígitos, a precisão da coleta é a do LOCA.

## 2026-10-09 — conserto do recorte salvo: salvar a JANELA JULGADA (e a amostra mudou de cara)

`reconhecer_linha` passou a gravar **a mesma janela que o detector julgou** (2,4 × 1,6 passo
centrada no token ou no componente aprovado), e não a caixa justa do token. Verificação numa
amostra (2 canais re-coletados — a amostra fica **mista**, porque os outros canais ainda têm os
recortes antigos):

- recortes que **carregam o arco com os números em volta** (ex.: arco sobre o `6`, sobre o `4`,
  `(0)` e `(3)` com o arco junto, diagonais de slide) — o símbolo **aparece**;
- antes, o mesmo token produzia um PNG com o **dígito pelado**, e era isso que eu julgava nas
  amostras: eu media o recorte, não a decisão.

Contagem grosseira na amostra mista: ~42 % símbolo, ~42 % dígito-com-contexto, ~16 % material de
linha — contra 29 % / 58 % / 8 % da amostra anterior. **Mista, então é indício e não medida** — a
medida limpa exige re-rodar a coleta inteira com o conserto.

Estado do disco, dito para não confundir depois: a rodada de teste de 2 canais **sobrescreveu**
`mr. tabs` e `serge kottelat` dentro de `data/saida/simbolos/`; os outros canais continuam da coleta
completa anterior. A próxima rodada re-roda tudo.

## 2026-10-09 — coleta LIMPA com a janela julgada: 1.018 símbolos, precisão no olho 27 %

| | valor |
| --- | --- |
| símbolos guardados | **1.018** em 4.691 tokens (21,7 %) |
| **precisão no olho** (48 recortes) | **27 %** (~13 símbolos) |
| algarismo guardado como símbolo | **52 %** (~25) |
| lixo/notação/material de linha | ~21 % (~10) |

**O conserto do recorte NÃO fechou a distância.** Os recortes agora carregam contexto (arcos,
`X` de abafado, `(12)`, ornamento triangular — visíveis na amostra), mas a maioria continua sendo
**dígito**, e a precisão da coleta continua em **27 %**, contra **89–91 %** do LOCA com o MESMO
modelo.

**O que isso significa, dito sem rodeio**: o LOCA mede o conjunto rotulado (523 positivos × 880
negativos de 22 tablaturas) e a coleta mede o que o pipeline salva — e os dois não concordam, mesmo
com treino e teste alinhados por vídeo. **Ainda não sei por quê.** A diferença que sobra está entre
o conjunto de CANDIDATOS do pipeline (`alvos`) e o conjunto de negativos do gabarito (tokens longe
das marcas), e eu não medi essa diferença — é o que falta medir antes de qualquer outra hipótese.

**Não vou fechar o goal com 27 %**, e também não vou apresentar o 89–91 % do LOCA como se fosse a
precisão da coleta: são duas medidas diferentes, e a que importa para o produto é a segunda.

## 2026-10-09 — o que faltava medir: os recortes da coleta são MISTURA (e o modelo aprova negativo)

Comparei as três populações pela mesma feature (tinta = fração de pixels de tinta na janela):

| conjunto | aspecto (mediana) | **tinta (mediana)** | interquartil |
| --- | --- | --- | --- |
| POSITIVOS do gabarito (símbolos) | 1,56 | **0,174** | 0,154–0,197 |
| NEGATIVOS do gabarito | 1,50 | **0,332** | 0,241–0,415 |
| **RECORTES DA COLETA** | 1,58 | **0,232** | 0,195–0,278 |

A coleta fica **entre** os dois: é uma **mistura**, e a mediana é compatível com os ~27 % de símbolo
que eu contei no olho. Conclusão medida: **no pipeline o modelo aprova recortes que se parecem com
os NEGATIVOS do gabarito** — os mesmos que ele rejeita 94 % das vezes no gabarito.

Então o problema **não é o tipo de objeto**: nas duas pontas são janelas de token das MESMAS
tablaturas. É a **decisão** que não se reproduz. E o teste que isola isso é direto e ainda não foi
feito: **pegar UM negativo do gabarito (dígito, que o modelo rejeita) e o MESMO token no pipeline,
e comparar as duas probabilidades**. Se divergirem, há algo diferente no caminho de inferência
(pré-processamento, ROI, conversão de cor) — e não no modelo nem nos dados.

## 2026-10-09 — teste fim a fim: NÃO deu 1 de 256 por bug MEU de coordenada (não registrado como medida)

Tentei o teste que separa as duas leituras (o pipeline acerta nos quadros marcados, ou não?). O
resultado bruto deu **1 acerto em 256 aprovações** — e isso **não é medida, é erro meu**:

> Os tokens vêm com **x relativo à ROI** do painel (`c.roi`), e as **marcas do dono** estão em **x do
> quadro inteiro**, porque a faixa que eu entreguei para ele marcar é `q[y0:y1, :]` — **largura
> total**. Comparar os dois sem somar o deslocamento horizontal da ROI desalinha *tudo*.

**CORREÇÃO, no mesmo dia e antes de qualquer número ir para lugar nenhum**: fui ao código e a minha
explicação estava **errada** — `tab/painel.py` faz `roi = frame[y0:y1, :]` (linhas 115 e 213), ou
seja a ROI também é **largura total** e **não existe deslocamento de x**. Eu inventei a causa sem
conferir, que é precisamente o que eu passei o goal inteiro dizendo que não faria.

**O que fica**: o resultado de **1 acerto em 256 aprovações** está **sem explicação** — não é
offset de x (refutado no código), e o alinhamento de y deveria bater (a faixa e a ROI são o mesmo
recorte `frame[y0:y1, :]`). Não medi o suficiente para dizer o que é, e **não vou chutar de novo**.
O próximo passo é o que eu deveria ter feito primeiro: **desenhar no quadro, lado a lado, os tokens
aprovados e as marcas do dono** — olhar a imagem antes de teorizar (regra 4 do projeto, que eu
quebrei duas vezes seguidas nesta rodada).

## 2026-10-09 — o bug do `1 de 256` era MEU (y somado duas vezes), achado DESENHANDO

Desenhei no mesmo quadro as marcas do dono (círculos azuis) e os tokens aprovados (quadrados
verdes) — `data/saida/frames/marcas_vs_tokens.png` — e **olhei antes de teorizar**. Os dois caem
**nos mesmos lugares** sobre a tablatura, o que provou que a comparação é que estava errada. No
código:

```python
abs(cy - (y0 + m["y"])) < 0.7 * passo  # ERRADO: m["y"] JÁ está na coordenada da FAIXA
```

`m["y"]` já vem na coordenada da faixa (foi nela que ele clicou) e eu **somava o `y0` de novo**.
Depois de corrigir, o número virou `21 de 256` (com tolerância de 0,7 passo) e **`31 de 256`** com
tolerância que associa símbolo (arco, acima) a token (dígito, abaixo): 1,2 passo em x, 2,0 em y.

**TESTE FIM A FIM, contra as marcas dele, nas 18 tablaturas marcadas:**

| medida | valor |
| --- | --- |
| marcas | 189 |
| tokens aprovados | 256 |
| **coincidem** | **31** |
| **precisão fim a fim** | **31/256 = 0,12** |
| **recall fim a fim** | **31/189 = 0,16** |

**É este o número que vale para o produto** — medido contra a verdade dele, não contra o conjunto
que eu construí. E ele diz que o pipeline aprova tokens que **não** são os símbolos marcados, o que
é coerente com os 27 % do olho.

**O que continua sem explicação, e agora com nome**: o LOCA do mesmo modelo dá 0,89–0,91 no conjunto
rotulado, e o fim a fim dá 0,12 contra as marcas. As duas medidas usam o MESMO modelo e os MESMOS
vídeos. A diferença está entre o **conjunto de candidatos do pipeline** e o **conjunto rotulado** —
e é exatamente essa diferença que falta medir, comparando janela a janela, token a token.

**Regra que eu quebrei e que o desenho restaurou**: eu escrevi duas teorias (offset de x; e antes
disso a hipótese da coordenada) sobre uma imagem que eu não tinha aberto. Abrir a imagem achou o bug
em um minuto.

## 2026-10-09 — o modelo é CONSISTENTE, e ele aprova a região do SÍMBOLO (y acima da 1ª corda)

Teste token a token num quadro marcado (`C07_kimny's guitar`, passo 20,6, 93 tokens), comparando a
probabilidade pelo caminho do pipeline e pela minha janela (a que gerou o gabarito):

| | |
| --- | --- |
| aprovados | 18 |
| probabilidade **igual** nas duas janelas | **10** |
| diferente | 8 — **todos por ~0,08** (0,966 contra 0,888), compatível com 1–2 px de diferença no centro do token |

**Não há divergência de caminho de inferência.** O modelo é consistente.

**E a posição dos tokens aprovados diz o essencial**: os de maior confiança estão em **y = 13**, que
é **acima da primeira corda** — a **região dos arcos**. Ele **está aprovando a região do símbolo**,
não o dígito. Isso derruba a minha leitura anterior (de que ele aprovava "dígito"): o token é do
tamanho de um dígito, mas está **onde o símbolo fica**.

**O que sobra sem explicação**: o teste fim a fim contra as marcas dele deu 31 de 256, mesmo com o
modelo aprovando a região certa e sendo consistente. A associação marca↔token é minha e pode estar
errada (uma marca pode cobrir mais de um token, e uma marca no arco cai entre dois dígitos). **Não
concluo que a precisão é 0,12 nem que é 0,90** — o que eu tenho é: o modelo aprova a região certa,
e a minha forma de casar isso com as marcas dele está sob suspeita.

## 2026-10-09 — ENCONTRADO: os meus NEGATIVOS foram recortados do LUGAR ERRADO do quadro

A caixa não aparecia no desenho nem com 3 px de espessura e 1900 px de largura. Isso só tinha uma
explicação, e ela é grave:

```
iwaki: roi=(460, 1669)   roi_das_cordas=(876, 1066)
       linhas_y = [283, 310, 337, 365, 392, 419]   <- espaco da ROI
       glifos y de 298 a 432                        <- espaco da ROI
```

Os glifos e as linhas de corda estão no **espaço da ROI** (460 px de altura), e eu desenhava numa
faixa de **190 px** — as caixas caíam **fora da imagem**.

**E o mesmo erro está na construção do conjunto rotulado:**

| | como eu fiz | certo |
| --- | --- | --- |
| **positivos** (marcas do dono) | `cinza[y0 + marca_y]` — **com** o offset ✓ | ✓ |
| **negativos** (centro do glifo) | `cinza[cy]` — `cy` está no espaço da ROI e eu indexei o **quadro** ✗ | falta somar `y0` |

**Os negativos foram recortados do lugar errado.** Isso explica TUDO o que estava sem explicação:

- **LOCA 0,89–0,91**: os negativos eram pedaços de região errada, quase vazios — **fáceis demais**;
- **fim a fim 0,12**: o modelo **nunca viu um negativo de verdade**;
- e a insistência do "dígito" nas amostras: com negativos falsos, o modelo aprendeu a separar
  "arcos" de "região errada", não "arcos" de "dígitos".

**Achado pela regra 4** (olhar a imagem) — depois de eu escrever duas teorias erradas sobre imagens
que não tinha aberto. É a terceira vez neste goal que abrir a imagem resolve o que a teoria não
resolveu.

**Próximo passo**: corrigir o recorte dos negativos (somar `y0`), regerar o conjunto, retreinar e
medir de novo — LOCA e fim a fim. A expectativa honesta: o LOCA vai **cair** (os negativos deixam de
ser fáceis) e o fim a fim deve **subir**. Se o LOCA cair muito, o número novo é o verdadeiro.

## 2026-10-09 — negativos corrigidos: o LOCA CAIU como previsto (0,77–0,79) e o número é esse

Regerados **todos** os negativos a partir da **ROI** (onde os glifos vivem) — 2.263 recortes: 506
difíceis (não-algarismo) + 1.757 algarismos, rebalanceado para 856. Mesmo conjunto de positivos
(523). Resultado, e eu tinha dito **antes** de medir que o LOCA ia cair:

| semente | símbolos pegos | falso positivo | **precisão** |
| --- | --- | --- | --- |
| 1 | 454/523 (0,87) | 136/856 (16 %) | **0,77** |
| 2 | 460/523 (0,88) | 124/856 (14 %) | **0,79** |
| 3 | 444/523 (0,85) | 118/856 (14 %) | **0,79** |

Antes (negativos furados): 0,89–0,91 de precisão e 0,96–0,98 de recall. **O recall também caiu**
(0,85–0,88). Estes são os números verdadeiros: **precisão 0,77–0,79, recall 0,85–0,88**. O número
piorou porque a medição ficou honesta — e é o que eu quero registrado, não o bonito.

**E a minha segunda previsão estava ERRADA**: eu disse que o fim a fim ia subir. Deu **0,15** (era
0,12). Não subiu.

**Mas o `0,15` ainda NÃO é medida**: o meu teste compara os **tokens (coordenada da ROI)** com as
**marcas (coordenada da FAIXA)**, e a faixa é um recorte **dentro** da ROI (para o `iwaki`, a faixa
começa 256 px abaixo do topo da ROI). O token que eu vi em `y=13` da ROI está em `y=-243` da faixa —
**acima da tablatura**. É o mesmo bug de espaço, agora dentro do meu teste. **Não registro `0,15`
como precisão da coleta.**

## 2026-10-09 — fim a fim com o espaço CERTO: 0,10 — e a pista de onde ele aprova errado

Corrigi o espaço no meu teste (`strip_y = roi_y + (altura_quadro − altura_ROI) − y0`, conferido no
`iwaki`: linhas 283–419 na ROI viram 903–1039 no quadro, e `roi_das_cordas` dá 876–1066 com margem
de exatamente 1 passo nos dois lados) e remedi:

| | |
| --- | --- |
| marcas | 189 |
| aprovados | 201 |
| **coincidem** | **21** |
| **precisão fim a fim** | **0,10** |
| **recall fim a fim** | **0,11** |

**Não melhorou** (era 0,12–0,15 com o espaço errado). Os três consertos — alinhar vídeos, corrigir o
recorte dos negativos, corrigir o espaço — **não fecharam a distância** entre o LOCA (0,77–0,79) e o
fim a fim (0,10).

**A pista, medida**: no `iwaki`, um token aprovado está em ROI `y=13`, que na faixa é **`y=−243`** —
**acima da tablatura**, fora da região das cordas. O modelo aprova regiões **fora** da faixa das
cordas, e essas aprovações não podem casar com marca nenhuma.

**Próximo passo, concreto**: os candidatos do pipeline **não estão restritos à faixa das cordas** —
e símbolo de tablatura vive **dentro** dela. Restringir os candidatos à região que o
`roi_das_cordas` já delimita é uma trava determinística, barata de medir, e ataca exatamente o que
sobrou. Medir antes de adotar: quantos dos 523 positivos do gabarito ficam dentro da faixa (deve ser
quase todos) e quantos dos aprovados de fora sobram.

## 2026-10-09 — trava da FAIXA DAS CORDAS: medida antes de adotar, 523 de 523 dentro, zero colateral

Medi a trava antes de ligar (como a da barra vertical, que mediu 0 de 123 antes de ser aceita):

| | |
| --- | --- |
| símbolos verdadeiros do dono avaliados | **523** |
| **DENTRO da faixa das cordas** (`roi_das_cordas`) | **523 (100 %)** |
| fora | **0** |

**Zero colateral.** E o pipeline aprovava tokens **fora** da faixa — um caso medido: ROI `y=13`, que
na faixa é `y=−243`, acima da tablatura. Ligada como motivo próprio (`recusado_fora_da_faixa`), com a
faixa convertida para coordenada da ROI no coletor. Se a trava recusar, o motivo fica gravado — nada
some em silêncio.

Conversão conferida antes de usar: a ROI é `frame[y_roi0:y_roi1]` e o `roi_das_cordas` devolve a
faixa em coordenada do **quadro**; no `iwaki` as linhas 283–419 da ROI viram 903–1039 no quadro e o
`roi_das_cordas` dá 876–1066 — margem de exatamente 1 passo nos dois lados.

## 2026-10-09 — com a trava da faixa: fim a fim vai de 0,10 para 0,15 (e a distância segue)

| | sem trava | **com a trava da faixa** |
| --- | --- | --- |
| tokens aprovados | 201 | **133** (−68 fora da faixa) |
| **precisão fim a fim** | 0,10 | **0,15** |
| recall fim a fim | 0,11 | 0,11 |

A trava fez **exatamente o que devia** — removeu 68 aprovações fora da faixa das cordas — e a
precisão subiu de 0,10 para 0,15. **Mas não fechou a distância** para os 0,77–0,79 do LOCA.

**O que sobra, e agora com um suspeito único**: a minha **associação marca↔token** no teste fim a
fim é a única peça que eu **nunca validei olhando**. Ela foi feita por proximidade (1,2 passo em x,
2,0 em y) e é onde os dois últimos bugs de espaço apareceram. Duas vezes nesta noite eu escrevi
teoria sobre imagem que não abri e achei o erro em um minuto ao abrir.

**Próximo passo, e é o mesmo que resolveu duas vezes**: desenhar as **marcas** e os **tokens
aprovados com a trava** no MESMO quadro e **olhar** se eles caem juntos. Se caírem, o `0,15` é bug do
meu casamento e o número verdadeiro é outro; se não caírem, o modelo aprova outra coisa — e eu vou
**ver** o quê, em vez de deduzir.

## 2026-10-09 — OLHANDO: o modelo aprova ESPAÇO VAZIO (e isso explica a distância inteira)

Desenhei, no espaço da faixa, as marcas do dono (círculos azuis) e os tokens aprovados com a trava
(quadrados verdes), em caixa grossa. O que a imagem mostra, sem margem para interpretação:

- **as marcas dele estão EXATAMENTE sobre os arcos** — uma a uma, em `0-2`, `5-5`, `3-3`, `7-7`,
  `8-8`. É a validação mais forte possível do trabalho dele;
- **os tokens aprovados estão em ESPAÇO VAZIO**, entre as linhas de corda, longe de qualquer arco.

**O modelo não aprova os símbolos: ele aprova espaço em branco.**

**Por que**, e é dedutível do que já está medido: os positivos do treino são janelas centradas nos
arcos — e um arco é **fino**, então a janela é **quase vazia** (tinta mediana 0,174, contra 0,332 dos
negativos). O modelo aprendeu **"pouca tinta = símbolo"**. No pipeline, qualquer janela quase vazia —
inclusive espaço em branco entre as linhas — recebe 0,85–0,97.

E o LOCA ficava bom porque **os meus negativos eram janelas de dígito** (com tinta): a classe que
faltava nos negativos é a **janela vazia**, e ela **nunca esteve no treino**. Não era o modelo, não
era o recorte, não era a coordenada: era **uma classe de negativo ausente**.

**Próximo passo, medível e barato**: gerar negativos de **janelas vazias** (regiões entre as cordas,
longe de qualquer marca) e retreinar. É o mesmo padrão que funcionou antes — descobrir qual classe
o modelo estava confundindo e pôr a classe no treino (foi assim com os "negativos difíceis").

## 2026-10-09 — a classe da janela vazia no treino: falso positivo cai 30 % e o fim a fim sobe a 0,19

Gerados **539 negativos de janela vazia** (regiões entre as cordas, longe de qualquer marca, tinta
≤ 0,12 — o primeiro limiar que tentei, ≤ 0,05, era **impossível**: uma janela de 1,6 passo numa
tablatura cujas cordas estão a 1 passo **sempre** contém uma linha, e só 31 passaram).

| | sem os vazios | **com os 539 vazios** |
| --- | --- | --- |
| LOCA: precisão | 0,77–0,79 | **0,74–0,76** |
| LOCA: falso positivo | 0,14–0,16 | **0,10–0,11** |
| LOCA: recall | 0,85–0,88 | 0,83–0,86 |
| **fim a fim: precisão** | 0,15 | **0,19** |
| fim a fim: recall | 0,11 | 0,13 |

**A classe que faltava era PARTE do problema** — o falso positivo do detector caiu ~30 % e o fim a
fim subiu de 0,15 para 0,19 — **mas não é o problema todo**: 0,19 contra 0,74–0,76 do LOCA.

**Próximo passo, o que já funcionou quatro vezes nesta noite**: **desenhar e olhar** os 108 aprovados
que ainda não casam com marca nenhuma, e ver o que eles são. Não vou deduzir.

## 2026-10-09 — OLHANDO os 108: ainda é espaço vazio, e agora em pontos específicos

Desenhei os aprovados do `C07`: verde os que casam com marca, **vermelho os que não**. A imagem é
inequívoca: **os 8 vermelhos são espaço vazio entre as linhas**, em dois pares localizados — mesmo com
os 539 negativos de janela vazia no treino.

Ou seja: **a classe nova reduziu o modo de falha (−30 % de falso positivo) mas não acabou com ele.**
O modelo ainda aprova vazio em pontos específicos, e a pergunta que sobra é **o que distingue esses
vazios dos 539 que eu gerei** — se é tamanho, forma, ou uma marca fraca dentro deles (lembrando o
aviso do dono: *"arco de ligadura quase sumindo, cuidado pra não cortar coisa demais"*).

E um efeito colateral registrado: no `C16` (shin izumi) o modelo agora **não aprova nada** — os
negativos vazios o endureceram, e o recall do fim a fim segue baixo (0,13). Trocar falso positivo por
recall não é ganho: é mudança de lugar.

**Próximo passo, medível**: comparar as features (tinta, aspecto, componentes) entre **os vazios que
ele aprova** e **os vazios que eu gerei** — se houver um separador, ele vira negativa dirigida; se não
houver, o modelo está usando um sinal que eu ainda não identifiquei, e aí o caminho é outro.

## 2026-10-09 — zoom de 5×: os aprovados são VAZIO mesmo — e a diferença é a POSIÇÃO na lacuna

Ampliei 5× os 6 aprovados que não casam (recorte generoso de 4 passos de largura em volta de cada um).
**Nenhum tem símbolo apagado**: são vazios, e a hipótese do "arco quase sumindo escondido" está
refutada — embora o aviso do dono continue valendo para o caso geral.

Mas os zooms mostram **uma diferença sistemática**:

| | os que ele APROVA (0,94–0,96) | os meus 539 negativos |
| --- | --- | --- |
| posição na lacuna | **logo acima de uma linha** (assimétrico) | **no meio exato da lacuna** (simétrico) |

E é essa assimetria que um **arco** tem: ele fica **em cima da linha**, não no meio. O modelo parece ter
aprendido **"vazio encostado numa linha = arco"** — e eu só ensinei o caso simétrico, então ele nunca
viu o negativo que precisava.

**Próximo passo, medível**: gerar negativos com **múltiplos deslocamentos** dentro da lacuna (logo
acima de cada linha, logo abaixo, no meio, a 1/4 e a 3/4) em vez de só o ponto médio — e retreinar.
É o mesmo padrão das outras três correções: a classe não estava ausente, estava **incompleta**.

## 2026-10-09 — vazio com deslocamentos múltiplos: hipótese REFUTADA (o fim a fim não se move)

Gerei 480 negativos de janela vazia com **vários deslocamentos** (¼, ½ e ¾ de cada lacuna, mais logo
acima e logo abaixo de cada linha) — a variação assimétrica que a imagem sugeria que faltava:

| | só o ponto médio (539) | **com deslocamentos (480)** |
| --- | --- | --- |
| LOCA precisão | 0,74–0,76 | 0,74–0,76 |
| LOCA falso positivo | 0,10–0,11 | 0,10–0,12 |
| **fim a fim precisão** | 0,19 | **0,18** |
| fim a fim recall | 0,13 | 0,12 |

**Hipótese refutada.** Os vazios assimétricos não eram a causa: o fim a fim não se moveu (0,19 → 0,18,
dentro da variação).

**Cinco consertos já feitos, e o fim a fim segue em ~0,18–0,19**: alinhar os vídeos · corrigir o
recorte dos negativos · corrigir o espaço de coordenada · negativos de janela vazia · negativos de
vazio com deslocamentos. O LOCA está em 0,74–0,76 e o fim a fim em 0,18 — e **a distância entre os
dois é o que continua sem explicação**.

**O que ainda não foi feito**: desenhar os aprovados **com o modelo atual** (a lista mudou: 124
aprovados agora, era 201 no começo). Eu refutei a hipótese do vazio assimétrico com base no que o
modelo *antigo* aprovava. **Olhar de novo, com o modelo de agora**, é o passo que falta — e é o que
resolveu cinco vezes nesta noite.

## 2026-10-09 — OLHANDO (modelo atual, metade direita): ele aprova a FAIXA VAZIA ENTRE AS PAUTAS

A metade esquerda do `C07` eu já tinha visto; a **direita** mostrou o resto. O quadro tem **duas
pautas empilhadas** (a mesma música em duas versões), e os quadrados — **vermelhos e verdes** — estão
**na faixa vazia entre as duas pautas**. As marcas do dono (azuis) estão nos arcos da pauta de cima.

**Consequência dura**: os poucos "casamentos" do teste fim a fim eram **coincidência de x** — um
quadrado na faixa vazia que por acaso alinha com uma marca do arco acima (a minha tolerância de 2
passos em y dá esse crédito). O `0,18` não é subestimação: é **generoso**.

**E explica por que os meus negativos vazios não bastaram**: eu amostrei vazio **dentro de uma pauta**
(entre as 6 cordas). A faixa **entre pautas** é mais larga (2–3 passos), **nunca esteve no treino**, e
é onde ele aprova.

**Próximo passo, concreto**: incluir nos negativos as **faixas vazias largas** — entre pautas e fora
delas — e não só as lacunas internas de uma pauta. É a terceira variação da mesma classe (vazio
simétrico → vazio deslocado → vazio largo entre pautas), e as duas primeiras só moveram o falso
positivo do LOCA, não o fim a fim.

## 2026-10-09 — os DOIS erros de extração que o dono apontou: CORRIGIDOS e conferidos no olho

**C14 (`robert lunn`)** — ele escreveu *"o recorte dessa tablatura está errado tá faltando a última
linha"*. Causa: o `roi_das_cordas` usa margem de **1 passo** em volta das linhas detectadas, e a 6ª
corda ficou fora. Refiz com **0,6 passo extra** em cada lado: faixa de **217 → 255 px**, e as 6 cordas
aparecem (conferido na imagem: a 6ª linha entrou, com `tambora`, `N.H.` e os `x` visíveis).

**C05 (`iwaki`)** — ele escreveu *"isso é uma partitura, algo de errado não está certo"*. Causa: o
detector de painel escolheu uma **pauta de 5 linhas** e eu entreguei como tablatura. Procurei outro
instante daquele vídeo e achei em `frac=0,3`: **passo 27,4, 35 glifos**, e a imagem confirma uma
**tablatura de verdade** (`7`, `9`, `11`, `(12)`, `5`, `2`, `4`, `3`, `0`, `8`).

Os dois recortes corrigidos estão em `data/saida/correcoes/` com uma ferramenta própria
(`marcar.html`) — e o dono pode remarcá-los com o mesmo gesto de sempre.

**Achado de bônus, que me pouparia tempo antes**: o `Candidato` **já tem** os campos `y0`/`y1` — a
origem da ROI no quadro. Eu vinha **deduzindo** esse valor (`altura_do_quadro − altura_da_ROI`) em vez
de ler o campo. A dedução estava certa (conferida no `iwaki` por margem exata), mas era um risco
desnecessário: **o dado estava no objeto**.

## 2026-10-09 — FECHAMENTO: três variações de negativo vazio, e a precisão da coleta fica em 0,17

Última tentativa: negativos amostrados em **todo o painel** (a faixa larga entre pautas, que a imagem
revelou), 422 deles, tinta ≤ 0,10.

| variante de negativo vazio | n | LOCA precisão | **fim a fim precisão** |
| --- | --- | --- | --- |
| nenhuma | 0 | 0,77–0,79 | 0,15 |
| ponto médio da lacuna | 539 | 0,74–0,76 | 0,19 |
| deslocamentos (¼, ½, ¾, junto às linhas) | 480 | 0,74–0,76 | 0,18 |
| **todo o painel (faixa larga)** | **422** | **0,77** | **0,17** |

**Três variações da mesma classe, e a precisão da coleta não sai de ~0,17–0,19.** O LOCA fica em
0,74–0,79. As duas medidas continuam separadas por um fator de ~4, e eu **não consegui fechá-lo**.

**O que eu posso afirmar com os dados na mão**: este detector, com este modelo e este dado,
**não entrega a precisão que o produto precisa**. Ele aprova faixa vazia ampla no pipeline, e ensinar
essa classe ao modelo (três vezes, de três formas) **não mudou o comportamento dele no uso**.

**O que sobrou sem ser testado, e é o caminho se alguém quiser continuar**: os negativos que o modelo
precisa **não são sintéticos** — são **os quadros exatos onde ele erra no pipeline**, e para esses só
existe uma fonte de verdade: **o dono marcar naqueles quadros** (é a instrução dele: pausar e chamar).
Todas as minhas tentativas foram de **inventar** o negativo; a alternativa é **pedir o rótulo**.

## 2026-10-09 — FECHAMENTO DO DETECTOR: os números finais, com o custo declarado

**O caminho novo foi medido e REPROVADO.** O piso de tinta tinha um vão real (vazio: máximo 0,100;
símbolo: p10 0,128), mas travar por ele **piorou o uso**: fim a fim 0,17 → **0,16** e recall 0,11 →
**0,08**. Revertido, e a tentativa fica registrada em `tab/caminhos.PISO_TINTA_SIMBOLO` para ninguém
repeti-la. A tinta continua **gravada** no registro de cada token (`sufixo["tinta"]`), sem travar.

**NÚMEROS FINAIS, medidos:**

| medida | valor |
| --- | --- |
| LOCA no conjunto rotulado (523 marcas suas) | precisão **0,74–0,79**, recall 0,82–0,87 |
| **precisão da coleta**, contra as marcas do dono, no espaço de coordenada correto | **0,17** (recall 0,11) |
| e o 0,17 é **generoso** — os "casamentos" são coincidência de x com a faixa vazia | — |

**CUSTO DECLARADO do que foi adotado** (as três travas que ficaram):

| trava | ganho medido | custo medido |
| --- | --- | --- |
| haste fina (razão < 0,35) | tira material de linha | **0** de 123 símbolos da época |
| faixa das cordas (`roi_das_cordas`) | tira 68 aprovações fora da faixa | **0** de 523 símbolos |
| filtro positivo (janela 2,4 × 1,6) | tira o resíduo do classificador | recall 0,87 no LOCA |

**E o que foi REPROVADO, tudo com número**: classificador genérico de lixo (0,665) · regra da cruz
(0 de 6) · linhas de pauta no token (1 de 4) · apertar a tolerância de espaçamento (custa 21 % dos
painéis) · validar o painel por conteúdo · recortar o componente · decidir por componente · as três
variações de negativo vazio · **o piso de tinta**. Todas medidas antes de adotar, e todas declaradas.

**O que este detector é, com os dados na mão**: ele acerta 0,74–0,79 no conjunto que eu construí e
**0,17 no uso real**. Ele aprova janelas que **não são** os símbolos marcados. **Não entrega a
precisão que o produto precisa** — e o caminho que sobra não é de modelo nem de dado sintético: é
**rótulo do dono nos quadros exatos onde ele erra**.

## 2026-10-09 — LOVO refuta "generalização entre vídeos" e revela a causa REAL: o símbolo não é candidato

Deixando a **tablatura inteira de fora** (vídeo + instante), em vez do canal:

| semente | símbolos pegos | falso positivo | **precisão** |
| --- | --- | --- | --- |
| 1 | 484/523 (0,93) | 125/1278 (10 %) | **0,79** |
| 2 | 463/523 (0,89) | 109/1278 (9 %) | **0,81** |

**O modelo generaliza para vídeo que nunca viu** (0,79–0,81) — praticamente o mesmo que por canal.
A minha hipótese ("não generaliza entre vídeos") está **refutada**, e o `0,77` por canal não era
inflado por isso.

**E aí a aritmética fecha de um jeito que reenquadra o problema inteiro:**

- no gabarito o modelo aprova **612 de 1801** (~34 %);
- no pipeline ele aprova **~126** do que julga (**~35 %**) — **o MESMO comportamento**;
- mas só **21 dos 189 marcadores do dono** casam.

**A conclusão**: as marcas dele estão nos **ARCOS**, e **o arco não é um token**. O pipeline propõe
**dígitos, pedaços de linha e espaço vazio**; o símbolo **não está entre os candidatos**. Os 21
"casamentos" são dígitos que por acaso ficam perto do arco.

**O classificador não é o gargalo — o conjunto de CANDIDATOS é.** Todo o esforço de treinar o filtro
(523 positivos, 1278 negativos, 11 hipóteses) estava a montante do problema: ele aprendeu bem a
separar arco de dígito (0,79–0,81), e o pipeline **nunca lhe oferece o arco para julgar**.

**Próximo passo, medível**: medir, para cada marca do dono, se existe um **token** naquela posição —
e onde o arco se perde (o delimitador? a segmentação? a lista `alvos`?). É uma medição direta e
localiza o conserto no lugar certo pela primeira vez.

## 2026-10-09 — ACHEI a condição que escondia o símbolo (e ela é o mesmo erro de sempre)

A condição que decide quem o filtro julga, em `reconhecer_linha`:

```python
alvos = [
    i for i, tk in enumerate(tokens) if classes[i][0] not in ALGARISMOS or tk.partes > 1
]
```

**"classe top-1 não é algarismo → pode ser símbolo".** É **o mesmo critério errado** que eu passei o
goal inteiro tentando substituir — e ele estava vivo **aqui**, na porta de entrada.

**Medição das 189 marcas do dono** (convertendo faixa → ROI com `c.y0`, o campo que existe):

| onde a marca cai | n |
| --- | --- |
| **token julgado pelo filtro** | **0** |
| token por perto, **nunca oferecido** | **138 (73 %)** |
| **nenhum token** na posição | **51 (27 %)** |

**Nenhuma marca chegava a ser julgada.** E o motivo é direto: o arco, como token, é lido como
**algarismo** pelo classificador de glifos — medido antes: **45 % dos símbolos verdadeiros** são lidos
como dígito. Então o critério "não é dígito → candidato" **excluía justamente o símbolo**.

**Conserto**: `julgar_todos=True` (o coletor oferece **todos** os tokens e deixa quem decide ser o
detector). Efeito medido:

| | antes | **oferecendo todos** |
| --- | --- | --- |
| aprovados | 126 | 149 |
| casam com marca | 21 | **27** |
| **precisão fim a fim** | 0,17 | **0,18** |
| recall fim a fim | 0,11 | **0,14** |

**Ganho pequeno — não é a transformação.** E a leitura mais provável: os "138 com token por perto"
casaram com o **dígito abaixo do arco**, não com o arco. Ou seja, **o arco provavelmente não é um
token** — ele é fino e deve estar se fundindo com a linha, ou sendo descartado na segmentação.

**Próxima medição, direta**: para as 189 marcas, verificar se existe **componente cru** (antes do
delimitador) naquela posição — e, se existe, por qual motivo do `Grade.recusados` ele cai. Isso
separa "o arco se funde com a linha" de "o delimitador o descarta".

## 2026-10-09 — o arco se FUNDE com a linha: a medição que fecha o diagnóstico

Para cada uma das 189 marcas, procurei o **componente cru** (componentes conexas na máscara da ROI,
sem passar pelo delimitador) na posição dela:

| onde a tinta da marca está | n |
| --- | --- |
| **componente existe, mas FORA de qualquer token** | **89 (47 %)** |
| **nenhuma tinta no ponto** | **58 (31 %)** |
| marca fora da ROI | 25 (13 %) |
| componente dentro de um token | 17 (9 %) |

E os exemplos de "componente fora de token" identificam a causa: um mede **1690 × 128 px** — a
**largura inteira do painel, 6 passos de altura**; outro, 88 × 12 (largura 3,4 passos, altura 0,46).

**O arco está ENCOSTADO na linha de corda e no dígito, e os três viram UM componente gigante** — que o
delimitador recusa por tamanho (os motivos estão em `Grade.recusados`). O arco **nunca existe
sozinho** para poder virar token. E os 31 % "sem tinta no ponto" são o arco **fino demais** para a
binarização (limiar `média − 0,5·desvio`) — o mesmo fenômeno do "arco quase sumindo" que o dono avisou.

**Onde o conserto tem de ser**: na **SEGMENTAÇÃO**, não no delimitador e não no classificador. O
caminho clássico e medível é **remover as linhas de corda** antes de procurar componentes (abertura
morfológica com kernel horizontal): assim o arco deixa de estar colado na linha e volta a ser um
componente próprio — e aí ele vira token, é oferecido ao filtro, e o detector (que já acerta 0,79–0,81
em vídeo novo) pode julgá-lo.

## 2026-10-09 — retirada das linhas de corda: implementada, medida e NEUTRA (desligada)

Implementei `_tirar_linhas` (abertura morfológica com kernel horizontal de 2,5 passos, que extrai a
corrida horizontal das cordas sem extrair o arco curvo) e liguei na segmentação dos glifos, com a
hipótese de que o arco, deixando de estar colado na linha, viraria componente próprio.

**Medição, contra a hipótese:**

| | antes | **com a retirada das linhas** |
| --- | --- | --- |
| marcas com componente **fora de token** | 89 | **89** |
| marcas **julgadas** pelo filtro | 0 | **0** |
| marcas **sem token** | 51 | **51** |
| gabarito de algarismo (semente 1) | 0,917 | **0,903** (−1 glifo) |

**Neutra nas marcas e negativa no gabarito.** Pela disciplina do projeto — só fica o que se mede como
benéfico — **desliguei**, e `_tirar_linhas` fica como ferramenta medida e documentada para quem quiser
tentar outro kernel ou outro limiar.

**O que isso ensina**: a fusão do arco com a linha **não é o que decide** a posição das marcas. As 138
marcas "com token por perto" continuam casando com o **dígito**, não com o arco — ou seja, **a medição
de proximidade que eu usei (±1 passo, em x e y) é generosa demais** e está contando o dígito de baixo
como se fosse o arco. É a **quarta vez** que um critério de associação meu se revela o elo fraco.

**Próxima medição**: apertar a associação (ex.: exigir que o token esteja **acima** da linha e a menos
de 0,5 passo em y da marca) e refazer a contagem — para saber quantas marcas têm o **arco** como
componente de fato, em vez de ter um dígito por perto.

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

## 2026-10-09 — retirada das linhas de corda: implementada, medida e NEUTRA (desligada)

`_tirar_linhas` (abertura morfológica com kernel horizontal de 2,5 passos: extrai a corrida
horizontal das cordas e não o arco curvo) foi ligada na segmentação dos glifos, com a hipótese de que
o arco, deixando de estar colado na linha, viraria componente próprio.

| | antes | **com a retirada das linhas** |
| --- | --- | --- |
| marcas com componente **fora de token** | 89 | **89** |
| marcas **julgadas** pelo filtro | 0 | **0** |
| marcas **sem token** | 51 | **51** |
| gabarito (semente 1) | 0,917 | 0,903 (−1 glifo) |

**Neutra nas marcas e negativa no gabarito → desligada.** `_tirar_linhas` fica como ferramenta
medida e documentada.

**E uma observação de integridade**: o gabarito continua dando **0,903 DEPOIS de eu reverter** — ou
seja, a variação de 1 glifo **não é da retirada das linhas**. É o acervo/cache mudando embaixo de nós
(vídeo apagado, quadro recacheado), instabilidade que este projeto já registra. **Não atribuo a
mudança à regra que eu testei** — seria creditar a mim uma variação que não é minha.

**O que a medição ensina**: a fusão do arco com a linha **não é o que decide** a posição das marcas.
As 138 marcas "com token por perto" continuam casando com o **dígito**, não com o arco — o meu critério
de proximidade (±1 passo em x e y) é **generoso demais** e conta o dígito de baixo como se fosse o
arco. É a **quarta vez** que um critério de associação meu se revela o elo fraco.

**Próxima medição**: apertar a associação (token **acima** da linha e a menos de **0,5 passo** em y da
marca) e refazer a contagem — para saber quantas marcas têm o **arco** como componente de fato.

## 2026-10-09 — associação apertada: 5 % dentro de token, 56 % com componente fora — e o alarme refutado

Medição apertada (só o componente que **contém o pixel da marca**, sem buscar vizinho):

| categoria | n |
| --- | --- |
| **dentro_em_token** | **10 (5 %)** |
| sobre_FORA_de_token | 66 |
| abaixo_FORA_de_token | 28 |
| acima_FORA_de_token (o arco) | 12 |
| **marca sem tinta** (±2 px) | **48 (25 %)** |
| **marca fora da ROI** | **25 (13 %)** |

Larguras: larg_larga 88, larg_media 12, larg_curta 16.

**O alarme que eu levantei — "o painel mudou, a minha base está corrompida" — foi REFUTADO por
verificação direta**: comparei a faixa de hoje com a tira que entreguei ao dono e a diferença média de
pixel é **0,0 / 0,8 / 0,3** em três imagens → **é a MESMA**. Não houve deriva de painel.

**As duas anomalias ficaram explicadas**:

1. **25 fora da ROI**: o `roi_das_cordas` devolve faixa com margem de 1 passo que **sai do painel**
   (no `C07`, a faixa começa em 862 e o painel em 870) — marcas nessa margem caem fora;
2. **48 sem tinta**: o meu raio de busca era **±2 px**, estreito demais para um traço de arco de 2 px
   com clique um pouco ao lado.

**O número que importa**: só **10 de 189 marcas (5 %)** têm o componente **dentro** de um token, e
**106 (56 %)** têm componente **fora de qualquer token**. O símbolo é descartado antes de poder ser
julgado — confirma o diagnóstico, agora com associação apertada.

**Próxima medição**: alargar a busca para ±1/3 de passo (para recuperar as 48) e, nas 106 "fora de
token", identificar **por qual motivo** elas caem — ligando cada componente descartado ao seu motivo
no `Grade.recusados` (hoje ele é contado, não individualizado).

## 2026-10-09 — motivos por componente: gigantes (60-86 passos) — com uma RESSALVA declarada

Replicando as condições do delimitador para o componente de cada marca (busca até ⅓ de passo):

| motivo | n |
| --- | --- |
| **`largo_demais`** (> 2,0 passos) | **101** |
| **`alto_demais`** (> 2,0 passos) | **92** |
| `fora_da_extensao` | 42 |
| sem tinta (até ⅓ de passo) | 29 |
| **`passaria_no_delimitador`** | **20** |
| `baixo_demais` | 5 |

Exemplos com `w/passo` de **60,5** e **86,0** (altura 14,7 e 5,3): o componente na posição da marca é a
**linha inteira** — o arco colado nela, recusado por tamanho. Confirma o diagnóstico por motivo.

**RESSALVA, e ela é sobre a minha medição**: eu binarizei a ROI por conta própria
(`média − 0,5·desvio`), e **o pipeline não usa essa máscara** — ele testa várias
(`mascaras_candidatas`) e escolhe a que passa no teste de estrutura, registrando o nome nos `avisos`
(`mascara=<nome>`). Se a máscara que eu usei é mais agressiva, ela **funde mais**, e os "gigantes"
podem ser artefato **da minha binarização**, não do pipeline. **Isso explicaria a retirada das linhas
ter sido neutra**: apliquei na máscara do pipeline e medi na minha.

**Quinta vez** que o elo fraco é um critério meu — a segunda nesta rodada (o primeiro foi o alarme de
deriva de painel, refutado por verificação).

**Próxima medição**: repetir a contagem **usando a máscara que o pipeline escolheu** (ela está nos
`avisos` da grade) — e só então decidir se o conserto é no delimitador, na segmentação ou na
binarização.

## 2026-10-09 — CORREÇÃO DE INTEGRIDADE: a minha "reversão" da rodada 2 NÃO pegou

Ao inspecionar o código para ligar a versão por faixas, descobri que `_tirar_linhas` (a remoção de
linhas por morfologia) **estava ATIVA** — a minha reversão da rodada 2 passou no `assert` mas não
alterou o que eu supunha. Consequência: **as medições das rodadas 3, 4 e 5 foram feitas com a
retirada de linhas ligada**, e eu as apresentei como se estivesse tudo desligado.

**O que isso muda**: os "gigantes de 73 passos de largura" que eu medi na máscara do próprio pipeline
foram medidos **com a morfologia ativa** — ou seja, a remoção por morfologia **não resolve** os
gigantes (o que reforça a leitura de que as linhas vêm quebradas nas máscaras de contraste e a
abertura não as extrai). **O diagnóstico permanece; a atribuição anterior estava errada.**

E o conserto por **faixas** (`_sem_faixas`: apaga `linhas_y ± 0,12 passo`, usando a posição que o
pipeline já conhece) **não chegou a ser ligado**: a inserção da função falhou e a chamada ficou
apontando para um nome inexistente (5 testes quebrados). Revertido para o estado são; a versão por
faixas é o **próximo passo**, a medir.

**Lição registrada**: eu declarei "revertido" com base num `assert` que passou, sem **ler o arquivo
depois** de editar. É a mesma família de erro das outras cinco vezes: eu verifico o que eu quis fazer,
não o que ficou no arquivo.

## 2026-10-09 — apagar as FAIXAS das cordas: implementado (com leitura do arquivo), medido e REPROVADO

`_sem_faixas` (apaga `linhas_y ± 0,12 passo`, usando a posição que o pipeline **já detecta** — mais
robusta que a morfologia, que não basta porque as linhas vêm quebradas nas máscaras de contraste).
Ligado **e conferido por leitura do arquivo** (função na linha 839, chamada na 894) — a disciplina que
eu tinha quebrado na rodada 2.

| | antes | **com as faixas apagadas** |
| --- | --- | --- |
| marcas julgadas | 0 | 0 |
| marcas com token não julgado | 138 | 138 |
| marcas **sem token** | 51 | **54** (pior) |
| gabarito `oficial_2` | 0,986 | **0,931** (−4 glifos) |
| gabarito `oficial_3` | 0,944 | **0,931** |

**Não melhora as marcas e piora o gabarito → desligada** (função fica medida e documentada).

**E o que isso prova é importante**: o componente gigante (mediana de **73 passos**) **não é mantido
pelas linhas de corda** — apagá-las não o divide. Ele é mantido por **outra coisa** que liga a largura
inteira. Candidatos óbvios: as **barlines** (linhas verticais de compasso) ou a própria **máscara de
contraste** deixando a faixa do sistema conectada.

**Próxima medição**: na máscara **do pipeline** (não na minha) e **já com as faixas apagadas**, medir a
largura do componente da marca — e, se continuar gigante, olhar **a imagem** dessa máscara naquele
ponto (regra 4), para ver o que está ligando tudo.

## 2026-10-09 — A CAUSA RAIZ, vista na máscara: o arco NÃO ESTÁ na máscara que o pipeline escolhe

Renderizei a máscara do pipeline na posição das marcas do `C07` (máscara escolhida: **`otsu`**) e
**olhei**:

- **os pontos das marcas estão em PRETO — não há tinta ali.** Os arcos são **finos demais para o
  Otsu**: eles **não existem** na máscara que o pipeline usa;
- o que **está** na máscara são **barras verticais brancas** (uma linha pontilhada, visível nos quatro
  recortes) — e o único componente encontrado foi **uma dessas barras** (4 × 16 px = 0,2 × 0,8 passos);
- essas barras são exatamente **as "barras que não significam nada"** que o dono mandou desconsiderar —
  e a regra `haste_fina` as recusa **corretamente**.

**A causa raiz, então, não é o delimitador nem o classificador: é a SELEÇÃO DA MÁSCARA.** O
`segmentar` percorre `mascaras_candidatas` e fica com a **primeira** que passa no teste de estrutura —
e a `otsu` passa, **perdendo os arcos finos**. As máscaras de contraste (`contraste_k21_d12`,
`contraste_k31_d25`) aparecem nos `avisos` de outras imagens: elas pegam traço fino, mas não foram as
escolhidas neste painel.

**Próximo passo, medível**: extrair os glifos da **UNIÃO** das máscaras (ou da mais sensível), mantendo
a grade (`linhas_y`, `passo`) vinda da escolhida — e medir: (a) quantas marcas passam a ter componente;
(b) o gabarito de algarismo (não pode cair, como caiu nas duas tentativas anteriores).

## 2026-10-09 — união das máscaras para os glifos: gabarito INTACTO, marcas paradas

`_uniao_mascaras`: a máscara dos glifos passa a ser a **união** de todas as candidatas (a grade —
`linhas_y`, `passo` — continua vindo da vencedora). Ligado **e conferido por leitura do arquivo**
(função na 522, chamada na 568).

| | antes | **com a união** |
| --- | --- | --- |
| gabarito `oficial_1` | 0,917 | **0,917** |
| gabarito `oficial_2` | 0,986 | **0,986** |
| gabarito `oficial_3` | 0,944 | **0,944** |
| marcas julgadas | 0 | 0 |
| token não julgado / sem token | 138 / 51 | **137 / 51** |

**Primeira mudança desta série que NÃO custa o gabarito** (morfologia e faixas derrubaram; a união
não). **Mas as marcas não se moveram** — o arco continua não virando token, mesmo com a união.

**Duas leituras possíveis, e a imagem decide**: ou (a) o arco **não está em nenhuma** máscara candidata
(fino demais para todas), ou (b) ele **está e é recusado depois** (por `haste_fina`, tamanho ou
agrupamento). A medição que separa: **renderizar a máscara UNIÃO na posição das marcas e olhar** —
como eu fiz com a `otsu`, que mostrou preto onde a marca está.

**Decisão sobre manter**: a união fica **ligada** por ora — ela é neutra no gabarito e é o princípio
certo (não perder traço fino); se a imagem mostrar que ela também não tem o arco, o conserto passa a
ser **para baixo do limiar** (trabalhar com a imagem crua/nitidez, não com máscara binária).

## 2026-10-09 — crua vs união, lado a lado: no C16 o arco ESTÁ na máscara; a perda é DEPOIS

Renderizei, para cada marca, a **imagem crua** e a **máscara união** com o círculo no ponto (pares
lado a lado) e olhei:

**C16 (`shin izumi`) — as marcas estão em símbolos reais, e a união os contém:**

- par 4: a marca está **em cima de um arco** (arco perfeito ligando dois dígitos) e a união o mostra
  em branco — **o arco ESTÁ na máscara**;
- pares 5 e 6: a marca está num **traço vertical grosso**, presente na união.

**C07 (`kimny's guitar`) — as marcas caem em áreas quase vazias**: a crua mostra as cordas e o círculo
no vazio; na união há mancha preta com um fio de branco. Ali o arco é **quase invisível na imagem**.

**Conclusão que muda o alvo**: a **máscara não é o gargalo** — no C16 ela contém o arco. A perda
acontece **depois**: o componente existe na máscara e **é recusado ou não é agrupado em token**. É
para o **delimitador/agrupamento** que a investigação volta — com a diferença de que agora eu sei que o
dado de entrada está lá.

**Próxima medição**: pegar a marca do C16 que está **em cima do arco** (par 4) e segui-la passo a passo
— o componente cru, o que o delimitador faz com ele (qual motivo de `Grade.recusados`), e o que o
agrupamento faz. Um caso rastreado do começo ao fim vale mais que cem contagens.

**Nota de honestidade**: as duas leituras que eu propus na rodada anterior — "(a) não está em nenhuma
máscara" e "(b) está e é recusado depois" — **a imagem decidiu por (b)**, e para o C07 há um terceiro
caso: **(c) o arco é quase invisível na própria imagem**, e nesses pontos nem a imagem crua o tem
claramente.

## 2026-10-09 — o rastreamento de UM caso, e a combinação que dobra o recall (e quebra o gabarito)

**O caso rastreado** (a marca do `C16` que está em cima do arco): o pixel dela, na **união**, pertence
a um componente de **1822 × 137 px = 85,14 × 6,40 passos** — a união **piora** o gigante (sendo mais
inclusiva, engrossa as linhas e costura tudo). E na `otsu` o arco **não existia**. **As duas máscaras
falham por motivos opostos** — e é isso que explica por que cada tentativa isolada dava neutro.

**Espessura real das linhas** (medida): `C16` otsu 5 px (0,23 passo), `C16` união 3 px, `C07` otsu
3 px, `C07` união 4 px — com p90 de até **15 px** (onde o traço encosta na linha, a corrida vertical
cresce). A minha faixa de ±0,12 passo ≈ ±2,5 px estava na mediana.

**E então a combinação que nunca tinha sido testada** — união (para o arco **existir**) + faixas (para
ele não estar colado):

| | antes | **união + faixas** |
| --- | --- | --- |
| aprovados | 126 | **631** |
| **casam com a marca do dono** | 21 | **78** |
| **recall fim a fim** | 0,11 | **0,41** |
| precisão fim a fim | 0,17 | 0,12 |
| **gabarito de algarismo** | 0,917/0,986/0,944 | **QUEBRA: `total=0`, zero glifos** |

**O recall quase quadruplica** — os símbolos finalmente chegam ao filtro, que era o diagnóstico desde o
começo. **Mas o gabarito quebra**: a segmentação perde **todos** os glifos, e os 631 aprovados vêm
desse destroço. **Não entra assim** — rejeitado e revertido (**conferido por leitura do arquivo**: a
chamada com faixas não existe mais, e o gabarito voltou a 0,917/0,986/0,944).

**O que fica**: a união (neutra no gabarito) e a **direção certa medida** — o caminho é união + uma
faixa que **poupe o dígito**. Próximo passo: faixa mais estreita, ou apagá-la **só onde a linha é
fina**, ou aplicá-la **só no caminho do símbolo** (deixando o caminho do algarismo intacto).

## 2026-10-09 — SEPARAR OS DOIS CAMINHOS: o símbolo acha 149 de 163 marcas, com a forma de arco

A ideia que a assimetria da rodada 10 apontou: o símbolo e o algarismo querem processamentos
**diferentes** da mesma imagem. Medi a metade que importa, **sem tocar no caminho do dígito** (por isso
o gabarito fica intacto por construção): os glifos do **caminho do símbolo** = união das máscaras +
faixas apagadas.

| no caminho do símbolo, na posição das marcas | n |
| --- | --- |
| **tem token** | **149** |
| sem token | 14 |
| fora da ROI | 25 |

E **a forma dos tokens prova**: 2,4 × 1,0 · 2,5 × 1,0 · 2,7 × 0,9 · 3,1 × 1,0 passos — **largos e
baixos**, que é a assinatura de um **arco** (contra o pipeline de hoje: **0 marcas julgadas** e só
**10 de 189** com componente dentro de token).

**Ou seja: o conserto é este** — dar ao filtro de símbolo um caminho de candidatos próprio
(união + faixas), deixando a grade do algarismo (máscara escolhida) **intacta**. O recall de 0,41 que eu
medi na rodada 10 veio de fazer isso **destruindo o dígito**; aqui a mesma cobertura aparece **sem**
tocar no dígito.

**Próximo passo (implementação)**: `reconhecer_linha` passa a julgar os tokens do caminho do símbolo
**além** dos da grade — os primeiros para o filtro de símbolo, os segundos para o algarismo. Medir o
fim a fim e o gabarito juntos: o gabarito **tem de ficar** em 0,917/0,986/0,944 (o caminho do dígito não
muda) e o recall deve subir.

## 2026-10-09 — FECHAMENTO DO GOAL: o diagnóstico está fechado; a ligação dos dois caminhos é o que falta

**A pergunta do goal — ONDE o símbolo (o arco) se perde antes de chegar ao filtro — está RESPONDIDA
com medição e imagem**, e não era em nenhum dos lugares que eu suspeitei primeiro:

| suspeito | veredito |
| --- | --- |
| o classificador de símbolo | **não** — LOCA 0,74–0,79 e leave-one-**vídeo**-out 0,79–0,81 |
| o delimitador | **não** — ele recusa corretamente o que é barra e o que é gigante |
| a lista `alvos` | parcialmente — o critério "não é dígito" **escondia 100 % das marcas** (corrigido: `julgar_todos`) |
| a fusão arco-linha | **não é a causa** — apagar as faixas na `otsu` deu neutro |
| a seleção da máscara | **é parte** — na `otsu` o arco **não existe**; na união ele existe mas vira gigante de 85 passos |
| **a raiz** | **as duas coisas querem processamentos opostos**: o algarismo quer a máscara escolhida (a `otsu`, que não tem o arco); o símbolo quer união + faixas (que afoga o dígito) |

**Medições que sustentam**: das 189 marcas, **0** eram julgadas pelo filtro (o arco não é token); no
caminho do símbolo (união + faixas) **149 de 163** marcas passam a ter token, com a **forma de arco**
(2,4×1,0 · 2,5×1,0 · 2,7×0,9 · 3,1×1,0 passos); e ligar isso **destruindo o dígito** dá recall 0,41 com
**gabarito `total=0`** — logo o caminho é separar, não unificar.

**O QUE FALTA, com receita exata para não se perder** (é a única tarefa aberta):

1. `reconhecer_linha` ganha uma **segunda passada**, depois do laço dos tokens: os candidatos do
   **caminho do símbolo** (`_sem_faixas(_uniao_mascaras(roi), linhas, passo)` → `_glifos_por_faixa` →
   `agrupar_tokens`), julgados **só pelo `filtro_simbolo`** e emitidos como nota com `casa=None` e
   `origem="simbolo"` — **sem** passar pelo classificador de algarismo;
2. a passada atual (grade da máscara escolhida) fica **intacta** — é ela que sustenta o gabarito;
3. critério de aceitação **duplo**: gabarito **0,917 / 0,986 / 0,944** (tem de ficar) **e** recall fim a
   fim acima de **0,41**, medido com `julgar_todos=True`.

**Estado da árvore**: ruff limpo, 120 testes, união ligada (neutra no gabarito), faixas **desligadas**
(quebram o dígito). Nada pela metade.

## 2026-10-09 — SEGUNDA PASSADA LIGADA: gabarito fica (0,917/0,986/0,944) — e o recall sobe pouco

Implementada a segunda passada em `reconhecer_linha` (candidatos do caminho do símbolo julgados
**só** pelo `filtro_simbolo`, emitidos com `casa=None` e `origem="simbolo"`; a passada do algarismo
**intacta**). A união **saiu do `segmentar`** — ela mudava a **pontuação do painel** e derrubou
`test_painel` ("o painel não foi nem candidato"); a segunda passada calcula a sua própria união.

| | pipeline antigo | **caminho do símbolo ligado** |
| --- | --- | --- |
| aprovados | 126 | 149 |
| **casam com a marca do dono** | 21 | **27** |
| precisão fim a fim | 0,17 | 0,18 |
| recall fim a fim | 0,11 | **0,14** |
| **gabarito** | 0,917/0,986/0,944 | **0,917/0,986/0,944** ✓ |

**O gabarito fica** (metade do critério duplo cumprida) e o recall melhora — mas **longe dos 0,41**.
O motivo está medido:

| candidatos do caminho do símbolo | n | mediana da prob | aprovados (>=0,5) |
| --- | --- | --- | --- |
| **na posição da marca (o arco)** | 363 | **0,231** | **117 (32 %)** |
| fora da marca | 1.506 | 0,087 | 176 (12 %) |

**O filtro discrimina na direção certa** (o arco é 2,7× mais aprovado que o resto) **mas em termos
absolutos fica abaixo do limiar** (mediana 0,231 < 0,5). Dos 149 candidatos, ~23 passam. **É a
calibragem da janela que eu recorto para o candidato do caminho do símbolo, não o princípio.**

**Próxima medição**: variar a **centragem/tamanho** da janela do candidato de símbolo (centro da caixa,
borda de cima, janela um pouco maior) e medir a taxa de aprovação **na posição das marcas** — é o que
falta para o recall chegar perto de 0,41 sem custar o gabarito.

## 2026-10-09 — O RECALL ALVO FOI ATINGIDO (0,40) — e a minha medição escondia isso

**Duas descobertas nesta rodada, e a segunda é sobre o meu instrumento.**

**1) A janela do candidato de símbolo tem de ficar na BORDA DE CIMA da caixa.** Medido, na posição das
marcas do dono:

| janela | mediana da prob | aprovados (>=0,5) |
| --- | --- | --- |
| centro da caixa (como estava) | 0,208 | 31 % |
| **borda de CIMA** | **0,833** | **78 %** |
| maior (1,6 x 1,0 passo) | 0,395 | 40 % |
| caixa + margem | 0,448 | 47 % |

Faz sentido visual: **o arco fica em cima da corda** — é ali que o dono marcou. O centro da caixa cai na
corda, não no traço do arco.

**2) A minha medição do fim a fim DESCARTAVA as notas do caminho do símbolo.** O script indexava o
token pelo índice da nota (`i < len(gs)`) — e a segunda passada **acrescenta notas no fim**, onde
`i >= len(gs)`. **Sétima vez que um critério de associação meu é o elo fraco**, e a terceira em que ele
esconde exatamente o efeito que eu estava medindo.

**Com a medição corrigida e a janela no topo:**

| | pipeline antigo | **dois caminhos + janela no topo** |
| --- | --- | --- |
| aprovados | 126 | **1.407** |
| **casam com a marca do dono** | 21 | **76** |
| **recall fim a fim** | 0,11 | **0,40** |
| precisão fim a fim | 0,17 | 0,05 |
| **gabarito** | 0,917/0,986/0,944 | **0,917/0,986/0,944** ✓ |

**O recall alvo (0,41) está atingido (0,40) e o gabarito fica.** O custo é a precisão: a segunda passada
aprova **1.258 falsos**, porque no limiar 0,5 a janela do topo também casa pedaços de linha.

**Próximo passo — o item (3) do goal, agora com número**: **varrer o limiar** da segunda passada. A
medição anterior dá o alvo: os candidatos **na marca** têm p90 **0,979** e os **fora** têm p90 **0,567**
— logo um limiar entre 0,6 e 0,9 deve cortar a maior parte dos falsos **sem** perder os arcos. Medir a
curva (limiar × recall × precisão) e escolher o ponto com o critério declarado.

## 2026-10-09 — varredura do limiar: NÃO é a alavanca (as distribuições se sobrepõem)

`limiar_simbolo2` (parâmetro novo, separado do limiar do caminho do algarismo) e a curva medida:

| limiar | aprovados | batem | falsos | precisão | recall |
| --- | --- | --- | --- | --- | --- |
| **0,50** | 1.407 | 76 | 1.331 | 0,054 | **0,402** |
| 0,60 | 1.139 | 71 | 1.068 | 0,062 | 0,376 |
| 0,70 | 957 | 65 | 892 | 0,068 | 0,344 |
| 0,80 | 781 | 60 | 721 | 0,077 | 0,317 |
| 0,90 | 579 | 54 | 525 | 0,093 | 0,286 |
| 0,95 | 471 | 49 | 422 | 0,104 | 0,259 |

**Não há joelho**: subir o limiar corta falsos **e** verdadeiros juntos (precisão 0,054 → 0,104 com
recall 0,402 → 0,259). A distribuição dos arcos e do lixo **se sobrepõe** neste caminho — mesmo em 0,95
os falsos (422) são 8,6× os verdadeiros (49).

**O que isso diz**: o problema **não é o limiar, é o TAMANHO DO POOL**. A união+faixas gera ~110
candidatos por quadro e o filtro aprova quase todos (a mediana dos que estão na marca subiu para 0,833
com a janela no topo — e a dos outros subiu junto). **Muitos candidatos são "forma de arco" sem ser o
arco**: pedaços de linha, topo de dígito, ruído do contraste local.

**Próxima alavanca, e ela é sobre o CANDIDATO, não sobre o limiar**: filtrar o pool **por forma** antes
do modelo — os arcos medidos são **largos e baixos** (2,4–3,1 × 0,9–1,0 passos), e é isso que a união
dos tokens "com forma de arco" precisa exigir (largura ≥ 1,5 passo **e** altura ≤ 1,5 passo, por
exemplo). Medir antes de adotar: quantos candidatos sobram, quantas marcas continuam cobertas, e o
recall/precisão resultantes.

## 2026-10-09 — filtro de FORMA antes do modelo: melhora precisão E recall (ganho de Pareto)

Regra no caminho do símbolo: só passa candidato **largo e baixo** (largura ≥ 1,5 passo **e** altura
≤ 1,5 passo) — a forma que as marcas do dono mediram (2,4×1,0 a 3,1×1,0 passos).

| | baseline (só 1ª passada) | pool aberto | **com filtro de forma** |
| --- | --- | --- | --- |
| aprovados | 149 | 1.407 | **178** |
| batem | 27 | 76 | **35** |
| **precisão** | 0,180 | 0,054 | **0,197** |
| **recall** | 0,140 | 0,402 | **0,185** |
| **gabarito** | 0,917/0,986/0,944 | idem | **0,917/0,986/0,944** ✓ |

**Ganho de Pareto contra o pipeline anterior**: precisão **e** recall sobem juntos (0,180 → 0,197 e
0,140 → 0,185). E o limiar perdeu importância (0,5 e 0,7 dão o mesmo 178) — o filtro de forma já tirou
o pool de baixa probabilidade.

**O que falta para o critério duplo**: o recall 0,185 está longe de 0,41. Mas agora o trade-off está
**mapeado por duas variáveis** (forma do candidato e limiar), e a curva do limiar com o pool aberto
mostrou que **o caminho passa pela forma, não pelo limiar**.

**Próxima medição**: varrer a **forma** (largura mínima em {1,0; 1,2; 1,5} passo × altura máxima em
{1,0; 1,5; 2,0} passo) e escolher o ponto de operação **com critério declarado** — o recall alvo é
0,41 e a precisão tem de ficar acima do baseline (0,180) para o ganho ser real.

## 2026-10-09 — varredura da FORMA: a largura decide, a altura é inerte, e o ponto fica em 1,5

`forma_simbolo` parametrizada (largura mínima, altura máxima) e a curva medida no limiar 0,5:

| largura mín. | altura máx. | aprovados | batem | precisão | recall |
| --- | --- | --- | --- | --- | --- |
| 1,0 | 1,0 | 263 | 43 | 0,163 | 0,228 |
| 1,0 | 1,5 | 264 | 43 | 0,163 | 0,228 |
| 1,2 | 1,5 | 220 | 39 | 0,177 | 0,206 |
| **1,5** | **1,5** | 178 | 35 | **0,197** | 0,185 |
| 1,2 | 2,0 | 220 | 39 | 0,177 | 0,206 |
| 1,0 | 2,0 | 264 | 43 | 0,163 | 0,228 |

**Dois achados**: a **altura é inerte** (1,0 / 1,5 / 2,0 dão os mesmos números) — só a **largura**
separa; e o trade-off é **monotônico** na largura, sem ponto mágico.

**Aplicando o critério declarado ANTES de medir** (precisão acima de 0,180 **e** recall acima de 0,140):
largura 1,0 dá 0,163 (**abaixo do baseline** — deslocamento, não ganho); 1,2 dá 0,177 (ainda abaixo);
**1,5 dá 0,197 e 0,185 — é o ponto escolhido, e é o que está ligado**.

**E o alvo do goal (recall 0,41) não é alcançável por estas duas alavancas**: o pool aberto chega a
0,402 **com precisão 0,054**, abaixo do baseline — ou seja, "chegar lá" custaria mais do que o pipeline
que já existia. **O limite não é o limiar nem a forma: é a discriminação do modelo na distribuição
deste pool.**

**Terceira alavanca, ainda não testada, e é geométrica e barata**: **o arco fica ENTRE duas cordas**
(e não sobre uma). Exigir que a caixa do candidato **não cruze** uma linha de corda corta pedaço de
linha e dígito — que são justamente os falsos. Medir: quantos candidatos sobram, e recall/precisão.

## 2026-10-09 — terceira alavanca (entre cordas): MEDIDA E REPROVADA; as três alavancas estão esgotadas

| | forma (sem ela) | **com "entre cordas"** |
| --- | --- | --- |
| aprovados | 178 | 154 |
| batem | 35 | **27** |
| precisão | 0,197 | **0,175** |
| recall | 0,185 | **0,143** |

Derruba **os dois lados** (mata 8 verdadeiros e 16 falsos) → **revertida**. O motivo é claro e fica
registrado: **o arco encosta na corda**, então a caixa dele cruza a linha com frequência.

**Estado final do caminho do símbolo, com as três alavancas esgotadas:**

| | precisão | recall |
| --- | --- | --- |
| baseline (só a 1ª passada) | 0,180 | 0,140 |
| **caminho do símbolo + forma 1,5 (LIGADO)** | **0,197** | **0,185** |
| pool aberto (limiar 0,5) | 0,054 | 0,402 |
| + regra entre cordas | 0,175 | 0,143 |

**O alvo do goal (recall 0,41) exige precisão 0,054** — abaixo do baseline. As três alavancas
disponíveis (limiar, forma, posição) estão medidas: o limiar não tem joelho, a forma é monotônica (e a
altura é inerte), e a posição piora os dois lados. **O limite é a discriminação do modelo na
distribuição deste pool** — e mexer no modelo está fora do goal.

## 2026-10-09 — AUDITORIA: a discrepância 30 x 178 NÃO EXISTE (erro meu de leitura) e a tolerância inflava o "149"

O dono mandou auditar antes de mexer no classificador, e a auditoria derrubou **duas conclusões minhas**:

**1) As duas grades são a MESMA.** Comparei a grade do `Candidato` (`c.grade`) com `segmentar(c.roi)`, que é
o que o `reconhecer_linha` usa por dentro: passo, `linhas_y` e número de glifos **idênticos**, e
**535 candidatos por cada caminho** em 8 imagens. Logo a página de auditoria mostra **o que o pipeline
julga** — a suspeita de que ela mostrava outra coisa está **refutada por medição**.

**2) E a "discrepância 30 x 178" era eu lendo errado o meu próprio número**: **178 = 149 da primeira
passada (algarismos) + 29 da segunda passada** — e a segunda passada julga exatamente os **30
candidatos** da página (dos quais ~29 aprovados). **Os dois números sempre foram consistentes.**
Oitava vez que o elo fraco é a minha verificação, não o sistema.

**3) E uma terceira, que corrige um número que eu já tinha apresentado como achado**: o "149 de 163
marcas ganham token" vinha de uma tolerância de **±1 passo EM CADA EIXO** (até ~2 passos de folga).
Com distância real até a marca mais próxima:

| | |
| --- | --- |
| candidatos com forma (18 tablaturas) | **30** |
| **a menos de 1 passo de uma marca do dono** | **19 (63 %)** |
| distância mediana | 0,78 passo |
| p75 | 2,67 passos |
| mais de 6 passos | 3 |

**Portanto o quadro real é**: a segunda passada **só gera 30 candidatos** nas 18 tablaturas, e **19**
deles ficam em cima de uma marca — ou seja, **~170 das 189 marcas não têm candidato nenhum**. É esse o
"fraco" que o dono viu **no olho**, e ele estava certo: **o caminho do símbolo quase não propõe
candidato em cima do arco.**

**Também corrigi a página de auditoria**, a pedido dele: recorte de ±3,2 × ±2,2 passos (o anterior
cortava o símbolo) e **duas caixas com significados diferentes** — **amarela = a janela que o modelo
vê** (é por ela que se classifica), **verde = o candidato bruto**, que costuma ser um **fragmento**
(tira de linha ou dígito) e por isso **não cobre o símbolo**. Ele tinha razão nas duas observações.

**Próximo passo (B do goal)**: por que o caminho do símbolo gera só 30 candidatos onde há 189 marcas —
medir se o arco existe como componente cru na posição da marca **na máscara união+faixas** e, se existe,
por que não sobrevive ao `agrupar_tokens`/filtro de forma.

## 2026-10-09 — OS 170 BURACOS TÊM NOME: o meu filtro de forma é quem os cria

Medição marca a marca (189), com dx e dy **separados**, na máscara união+faixas:

| | n |
| --- | --- |
| **candidato a menos de 1 passo, em x E y** | **139** |
| candidato em x, longe em y | 13 |
| longe nos dois | 10 |
| marca fora da ROI | 25 |
| **sem tinta crua na máscara** | **85** |
| sem candidato nenhum no quadro | 1 |

`dx` mediano **0,30 passo** e `dy` mediano **0,37 passo** — ou seja, **os candidatos estão em cima das
marcas do dono**. E então:

| o candidato mais próximo da marca passa o filtro de forma? | n |
| --- | --- |
| **NÃO passa** | **147** |
| passa | 16 |

**A causa dos buracos não é a geração de candidatos: é o FILTRO DE FORMA** (largura ≥ 1,5 passo) que eu
introduzi para salvar a precisão. Ele aprova **16 de 163**.

**E a premissa da "forma de arco" estava errada pelo mesmo vício de sempre**: os 2,4×1,0 a 3,1×1,0
passos que eu medi como "forma do arco" vieram da medição com **±1 passo de tolerância em cada eixo** —
a mesma que eu já tinha derrubado. Os candidatos que caem **em cima** da marca são **fragmentos
pequenos**, não arcos largos.

**O que sobra para os 85 "sem tinta crua"**: nesses pontos nem a união das máscaras tem tinta — o arco é
fino demais para qualquer limiar, ou o ponto está em região que a união não cobre. São um problema
**diferente**, e ficam registrados como tal.

**Próximo passo, e ele não é apertar nem afrouxar o filtro**: o filtro de forma existe para **limitar
quantas janelas o modelo julga** — mas várias candidatas próximas geram a **MESMA janela** (a janela é
larga, ±1,2 passo, independente do tamanho do candidato). Então o caminho é **deduplicar por janela**
(quantizar o centro) em vez de **descartar por forma**: julga cada janela **uma vez**, sem perder o arco.
Medir: quantas janelas únicas sobram, quantas marcas ficam cobertas e o par recall/precisão.

## 2026-10-09 — dedupe por janela: ligado, medido e INERTE na quantização fina

| | baseline (1ª passada) | filtro de forma | **dedupe 0,5 passo (sem forma)** |
| --- | --- | --- | --- |
| aprovados | 149 | 178 | **1.397** |
| batem | 27 | 35 | **74** |
| precisão | 0,180 | **0,197** | 0,053 |
| recall | 0,140 | 0,185 | **0,392** |
| gabarito | 0,917/0,986/0,944 | idem | **idem ✓** |

**O dedupe sozinho não substitui o filtro**: a 0,5 passo ele deixou **1.397 candidatos** contra 1.407
sem filtro nenhum — **as janelas são distintas nessa escala**. O recall volta (0,392) mas a precisão cai
para 0,053, abaixo do baseline.

**Estado da árvore**: o **filtro de forma foi restaurado** (é o melhor ponto medido: 0,197/0,185) e o
**dedupe ficou ligado** junto dele — inerte hoje, mas é a peça certa para quando a quantização for
grossa.

**Próxima medição**: quantização **grossa** no dedupe (0,8 / 1,2 / 1,6 passo — a janela tem 2,4 passos
de largura, então janelas a menos de 1,2 passo de distância **se sobrepõem** e mostram o mesmo arco).
Medir candidatos, marcas cobertas, precisão e recall, com o baseline 0,180/0,140 na mesa.

## 2026-10-09 — dedupe com quantização GROSSA: também NÃO resolve (a hipótese está morta)

Filtro de forma **desligado** e quantização varrida (a janela tem 2,4 passos de largura):

| quantização | aprovados | batem | precisão | recall |
| --- | --- | --- | --- | --- |
| 0,8 | 1.370 | 75 | 0,055 | 0,397 |
| 1,2 | 1.289 | 73 | 0,057 | 0,386 |
| 1,6 | 1.030 | 70 | 0,068 | 0,370 |
| **2,4** (= a largura da janela) | **835** | 63 | **0,075** | 0,333 |

**Mesmo deduplicando janelas que se sobrepõem 100 %**, a precisão fica em **0,075** — longe do baseline
(0,180). **O dedupe não é a alavanca.** Os candidatos estão genuinamente espalhados: o pool é cheio de
coisa com cara de arco, e é por isso que a precisão só se sustenta **descartando candidatos por forma**.

**Conclusão de (B), medida de ponta a ponta**: o **filtro de forma é um mal necessário** — é a única
alavanca que mantém a precisão no baseline, e **é ele que cria os 170 buracos** (147 dos 163 candidatos
em cima de marcas são descartados por ele). As quatro alavancas testadas — limiar, forma, posição e
dedupe — estão **esgotadas**, e o que sobra é a discriminação do modelo neste pool.

## (C) página de auditoria — FEITO a pedido do dono

- **ordem corrigida**: os candidatos que caem **em cima de uma marca do dono vêm primeiro** (é o que
  valida o modelo); os "sem marca" vão para o fim;
- **filtro** "mostrar só os SEM marca do dono" — a auditoria do falso positivo, isolável num clique;
- recorte de ±3,2 × ±2,2 passos e **duas caixas explicadas**: **amarela = a janela que o modelo vê**
  (classifique por ela), **verde = o candidato bruto** (um fragmento, não o símbolo).

## 2026-10-09 — A AUDITORIA DO DONO: o modelo acertou 30 de 30. O errado é o meu gabarito.

O dono rotulou 149 itens da auditoria (arquivo salvo em `data/gold/auditoria_simbolo_rotulada.json`).
Regra dele, textual: **"tudo que eu marquei que não é símbolo não é símbolo apenas"**.

| o que o modelo fez | o que o dono disse |
| --- | --- |
| **aprovou 29 candidatos** | **29 "é símbolo"** |
| **recusou 1** (prob 0,218) | **"não é símbolo"** |

**30 de 30.** E os dois defeitos estão no gabarito:

1. **9 dos 10 "falsos positivos" eram símbolos que ele não tinha marcado** (C06 ×3 com 0,994–0,996,
   C07_0005, C14_0020, C15 ×3, C22_0026) — o modelo achou, o meu gabarito não tinha;
2. **36 das 119 marcas "sem candidato" NÃO são símbolos** — estavam no gabarito como positivas e o
   modelo foi **penalizado por não encontrá-las**.

**Gabarito corrigido**: `data/gold/marcas_simbolos_5.json` (200 → **164** marcas; 36 removidas pela
regra dele). Fim a fim com ele: precisão **0,183** e recall **0,203** (era 0,197 / 0,185).

**E a precisão quase não se moveu — o que PROVA o defeito da métrica**: ela conta como falso positivo
todo aprovado que não está em cima de uma marca, e os **9 símbolos que ele confirmou** não têm marca.
**A métrica é incapaz de dar crédito ao modelo por achar símbolo que o dono não marcou.**

**Conclusão**: **não há evidência de que o classificador erre** — ele acertou tudo o que foi auditado.
Meter a mão nele agora seria consertar o que está certo para agradar um gabarito incompleto.

## 2026-10-09 — (a) PARAR DE MEDIR ERRADO: três gabaritos, medidos lado a lado

Recuperei as **posições (x, y na faixa)** dos candidatos auditados regerando a auditoria com as
coordenadas gravadas, casei pelo nome do arquivo com os rótulos do dono, e **acrescentei como marcas os
9 candidatos que ele rotulou "sim" e que não tinham marca nenhuma** — é o que a métrica antiga era
incapaz de creditar. Arquivo novo, sem destruir os anteriores: `data/gold/marcas_simbolos_6.json`.

| gabarito | marcas | batem | falsos | precisão | recall |
| --- | --- | --- | --- | --- | --- |
| `_4` (o meu original, com os defeitos) | 189 | 35 | 143 | 0,197 | 0,185 |
| `_5` (36 removidas pela regra do dono) | 153 | 31 | 138 | 0,183 | 0,203 |
| **`_6` (+ os 9 símbolos que ele confirmou)** | **162** | 35 | 143 | **0,197** | **0,216** |

**A referência honesta passa a ser o `_6`**: precisão **0,197** e recall **0,216** — contra o pipeline
anterior ao caminho do símbolo, que era **0,180 / 0,140**. Ou seja, o caminho do símbolo dá **+0,017 de
precisão e +0,076 de recall**, os dois para cima, medidos contra um gabarito corrigido pelo dono.

**E fica registrado o que ainda não está medido**: a precisão de 0,197 conta como falso positivo os
**143 aprovados que não estão em cima de marca nenhuma** — e **nenhum deles foi auditado** (a página só
tinha os 30 que passaram no filtro de forma). O dono confirmou **29 de 29** dos que ele viu. **É por
isso que o passo (c) — auditar o pool aberto — é o único que fecha a pergunta "o modelo erra no pool?"**

Os 9 símbolos que ele confirmou (posições recuperadas): C06 ×3 (x=244, 656, 1458), C07_0005 (x=1557),
C14_0020 (x=1090), C15 ×3 (x=127, 333, 459), C22_0026 (x=933).

## 2026-10-09 — (c) AUDITORIA DO POOL ABERTO montada: 1.869 candidatos, 1.258 aprovados pelo modelo

Regerada a auditoria **sem o filtro de forma** — é o pool que a página anterior escondia:

| | n |
| --- | --- |
| candidatos no pool aberto | **1.869** |
| deles, **aprovados** pelo modelo (prob >= 0,5) | **1.258** |
| recusados | 611 |

**Os 1.258 são exatamente os "1.258 falsos" que eu vinha reportando como erro do modelo** — e nunca
foram auditados. Página nova com **200 itens sorteados** (semente fixa 7: 150 aprovados + 50 recusados),
ordenados por probabilidade decrescente, com as mesmas convenções que o dono já sabe usar: **janela
grande em cima = o que o modelo vê** (classifique por ela), **contexto embaixo** com **caixa amarela =
a janela** e **caixa verde = o candidato bruto**, mais o **círculo vermelho** da marca dele.

**Página**: `data/saida/auditoria_pool/auditoria.html` (servida em
`http://127.0.0.1:8099/auditoria_pool/auditoria.html`). Rótulos: é símbolo / não é símbolo / não sei,
com exportação em JSON.

**É a única medição que fecha a pergunta "o modelo erra no pool?"** — e ela decide se o classificador
precisa de conserto. Sem o olho do dono, qualquer conclusão minha aqui é inferência.

## 2026-10-09 — ferramenta nova: `python -m tab.auditoria` (e o bug que eu peguei nela antes de commitar)

Enquanto os rótulos do pool não chegam, a análise virou **módulo do projeto** (`tab/auditoria.py`), para
o JSON do dono virar número em **um comando**:

    python -m tab.auditoria <rotulada.json> <itens.json>

Ela imprime: aprovados × recusados, a **precisão na amostra com o `n` do lado**, a quebra **por faixa de
probabilidade** (0,5–0,7 / 0,7–0,9 / 0,9–1,0) e a lista do **erro do modelo** (aprovou e o dono disse que
não é símbolo).

**E ela trata as duas armadilhas que me custaram rodadas**: (1) medir contra **rótulos**, não contra
marcas — porque a métrica antiga punia o modelo por achar os 9 símbolos que o dono não marcou; (2)
**imprimir o `n` junto de cada número** — precisão 1,000 em 29 janelas **não** é precisão 1,000 no pool
de 1.869 candidatos.

**Bug meu pego antes de entrar no repositório**: a primeira versão listava como "erro do modelo" um item
que ele havia **recusado** (o C14 de prob 0,218). A lista agora filtra por `aprovado` e imprime **0
erros** na primeira auditoria — consistente com o 29/29.

Conferido com os rótulos da primeira auditoria: **29/29 = 1,000** nos aprovados (5 na faixa 0,7–0,9 e 24
na 0,9–1,0, todos "sim"), e **0 símbolos perdidos** entre os recusados.

## 2026-10-09 — (b) adiantado pelo lado seguro: metade dos buracos tem TINTA, então a perda é no delimitador/agrupamento

Medição nos buracos que o dono confirmou como símbolo (rótulos da auditoria; 78 medidos com posição):

| | |
| --- | --- |
| **a máscara união+faixas tem tinta na posição da marca** | **43 de 83 (52 %)** |
| contraste (fundo − pixel mais escuro) | 239 nos buracos × 229 nas não-símbolos → **não separa nada** |

**O que vale**: **metade dos buracos tem tinta na máscara** e mesmo assim o pipeline **não propõe
candidato** ali. Logo, nesses casos a perda **não é a máscara** (que era a minha hipótese) — é o
**delimitador** (regras de tamanho/extensão/haste/nitidez) ou o **agrupamento em token** (a caixa do
token não cobre a marca).

**O que NÃO vale, e fica registrado como inconclusivo**: a minha medida de "contraste". A janela de
±1,2 × ±0,8 passo em volta da marca **inclui o dígito de baixo**, que é preto — então os dois grupos dão
"escuro" e o número não discrimina. **Décima vez que um critério meu mede a coisa errada.**

**Próxima medição (ainda sem tocar no pipeline)**: para os 43 buracos com tinta, seguir o componente
cru — tamanho em passos, posição em relação à corda — e dizer **por qual motivo** ele não virou token
(`largo_demais` / `alto_demais` / `fora_da_extensao` / `haste_fina` / `sem_nitidez`), como eu fiz na
rodada dos motivos.

## 2026-10-09 — CORREÇÃO: no pixel exato os buracos NÃO têm tinta — a perda é a máscara, não o delimitador

A rodada anterior disse "52 % dos buracos têm tinta". **Era artefato da janela**: eu procurei tinta num
quadrado de **±0,4 passo (±8 px)** em volta da marca. Com o **pixel exato**:

| nos 78 buracos confirmados como símbolo | n |
| --- | --- |
| **SEM tinta no pixel exato da marca** | **55** |
| marca fora da ROI | 17 |
| **não virou token** | **5** |
| virou token (mas a marca não caiu nele) | 2 |

Dos 5 que chegaram ao delimitador: `fora_da_extensao` 5, `largo_demais` 1, passaria 1. Tamanho do
componente quando existe: w mediano **1,86 passo**, h mediano **0,72**.

**Conclusão corrigida**: em **55 de 78** buracos **não há tinta nenhuma na máscara união+faixas** na
posição da marca — o arco **não é capturado**. A perda, na maioria, **é a MÁSCARA/LIMIAR**, não o
delimitador (a hipótese da rodada anterior está **derrubada**). O delimitador perde apenas ~5.

**Décima primeira vez que um critério meu (agora o TAMANHO DA JANELA de busca) mede a coisa errada** — e
é a segunda vez seguida no mesmo item, com a janela como culpada.

**Próxima medição (ainda sem tocar no pipeline)**: medir, nesses 55 pontos, **qual limiar** capturaria o
arco — comparar a distribuição dos tons no ponto com o fundo local — e **qual seria o custo** (quantos
pixels a mais entrariam na máscara no painel inteiro). Só com o custo na mão vale mudar o limiar.

## 2026-10-09 — (b): 39 % dos buracos TÊM sinal (5× a taxa-base) e são consertáveis por limiar local

Nos buracos confirmados como símbolo eu medi o quanto o pixel é mais escuro que o **fundo local** (mediana
de um anel de 1,5 passo, excluindo o miolo), contra um **controle** de pontos aleatórios do mesmo painel:

| | mediana | p75 | p90 | "escuro" (>=40 níveis) |
| --- | --- | --- | --- | --- |
| **BURACOS** (o dono diz que é símbolo) | 2 | **135** | **223** | **39 %** |
| CONTROLE (pontos do painel) | 0 | 1 | 11 | **8 %** |

**39 % contra 8 % de taxa-base: 5×.** Nesses pontos o arco **está nos pixels** e **abaixo do limiar da
máscara** — são consertáveis por **contraste local** (não por limiar global, que foi o que eu tentei).

Os outros **~60 %** não têm nada no pixel exato: ou o clique caiu alguns pixels ao lado do traço, ou não
há sinal capturável. **Não se consertam mexendo no limiar**, e ficam registrados como tal.

**Próxima medição, e ela é a última antes de qualquer mudança de código**: aplicar um limiar de
**contraste local** na máscara do símbolo e medir **as duas coisas juntas** — quantos dos 39 % passam a
ter candidato **e quanto de tinta falsa entra no painel inteiro** (o custo). Foi a falta dessa segunda
metade que me fez inundar o pipeline quando liguei o caminho do símbolo.

## 2026-10-09 — contraste local: recupera 39 % dos buracos, custa menos — e é NEUTRO no fim a fim

Medi as **duas metades** antes de mexer no código (era a promessa):

| | recupera nos buracos | tinta no painel | componentes |
| --- | --- | --- | --- |
| máscara atual (união + faixas) | — | 17,6 % | 179 (C02) / 160 (C04) |
| **contraste local (K=40)** | **24 de 62 (39 %)** | **10,7 %** | **105 / 52** |

**O contraste local é mais BARATO** (menos tinta, menos componentes) e recupera 39 % dos buracos — o medo
de inundar o pipeline estava **errado**. MAS, ligado no caminho do símbolo:

| | referência `_6` | contraste local |
| --- | --- | --- |
| precisão | 0,197 | **0,200** |
| recall | 0,216 | **0,210** |

**+0,003 num eixo, −0,006 no outro: NÃO É GANHO → desligado** (o código fica comentado com a medição).
O gabarito de algarismo fica intacto (0,917 / 0,986 / 0,944).

**O que isso ensina**: recuperar a tinta **não basta** — o componente recuperado **ainda não vira
candidato perto da marca**. A perda tem uma **segunda etapa** que eu ainda não localizei: entre ter tinta
e ter candidato na posição, algo descarta ou desloca. É a próxima pergunta, e agora ela está **estreitada**
(a tinta existe; o candidato não aparece).

## 2026-10-09 — o rastreamento do componente: os "buracos" NÃO são buracos, são o MEU FILTRO DE FORMA

Segui o componente nos buracos que o dono confirmou como símbolo:

| | n |
| --- | --- |
| nem tinta crua (contraste local ou união) | 37 |
| **TEM tinta** | **25** |
| **glifo sobreviveu perto da marca** | **24** |
| **e o TOKEN cobre a marca** | **21** |
| mas nenhum token cobre a marca | 3 |
| nenhum glifo sobreviveu | 1 |

**De 25 buracos com tinta, 21 têm um TOKEN cobrindo a marca.** O candidato **existe**; o delimitador
**não** o descarta; o token **está na posição**. **O que falta é só o meu FILTRO DE FORMA**, que o
exclui — a mesma causa já medida (147 de 163) e que o meu script de auditoria rotulou como "sem
candidato" porque **só contava os candidatos que passavam no filtro**.

**Décima segunda vez que um critério meu é o elo fraco** — e desta vez o erro foi **de vocabulário mais
que de número**: eu chamei de "buraco do pipeline" o que é "candidato descartado pela minha regra".

**E é por isso que (b) NÃO se decide sem (c)**: tirar o filtro de forma inunda o pipeline (1.407
aprovados) — mas isso só é ruim **se os 1.258 forem lixo**. A auditoria do dono já mostrou que **9 de 10
"falsos positivos" eram símbolos verdadeiros**. **Se o modelo estiver certo no pool, o "inundar" não é
inundar: é o recall que eu queria.** A ordem que o dono aprovou — (c) antes de (b) — está certa, e agora
eu sei exatamente por quê.

## 2026-10-09 — a tabela da decisão, na régua honesta (`_6`), com a precisão declarada como PISO

As duas opções que o dono vai escolher, medidas contra o **gabarito corrigido `_6`** (162 marcas) — e o
gabarito de algarismo intacto em todas (0,917 / 0,986 / 0,944):

| opção | aprovados | batem | precisão | recall |
| --- | --- | --- | --- | --- |
| **com o filtro de forma (1,5)** — o que está LIGADO | 178 | 35 | **0,197** | 0,216 |
| filtro frouxo (1,0) | 261 | 43 | 0,165 | 0,265 |
| **sem o filtro** | 1.397 | 62 | 0,044 | **0,383** |

**A ressalva que muda a leitura**: a coluna da precisão mede *"está em cima de uma marca do dono?"* — e a
auditoria dele provou que **essa régua perde símbolos** (9 de 10 "falsos positivos" eram símbolos que ele
não tinha marcado). Portanto:

**A precisão desta tabela é um PISO, não o valor real.** O 0,044 da opção "sem filtro" é o **pior caso**;
o valor verdadeiro é **maior** — e **quanto maior, mais atraente fica a opção "sem filtro"** (recall
0,383, quase o alvo 0,41).

**É exatamente essa a pergunta que a auditoria do pool responde** — e ela não é acadêmica: ela decide
entre **0,197/0,216** (conservador) e um ponto perto de **0,41 de recall** com precisão **desconhecida
hoje, mas maior que 0,044**.

## 2026-10-09 — MULTI-CORDA: 1 %, não 75 % — e a imagem mostra o que é (slides, dígitos fundidos, chaves cortadas)

Medição em 9 painéis (máscara `otsu`, componentes conexas):

| | n |
| --- | --- |
| componentes | 842 |
| "cruzam linha de corda" | 628 (**75 %**) |
| **multi-corda de verdade** (altura >= 1,8 passo **e** largura <= 6 passos) | **7 (1 %)** |

**O 75 % era inflado por DÍGITO APOIADO NA CORDA** — um algarismo encostado na linha tem pixel acima e
abaixo dela, então "cruza" no meu critério frouxo (**13ª vez** que um critério meu mede a coisa errada).
Com o critério honesto (mais alto que qualquer dígito e não tira de linha), sobra **1 %**.

**E a imagem dos 7 é o produto da rodada** (`data/saida/multicorda/folha_0.png` e os recortes
individuais):

| o que é | n | leitura |
| --- | --- | --- |
| **dois dígitos empilhados FUNDIDOS** (`0/2`, `0/2`, `5/7`; 0,7 × 2,0 passos) | 3 | é **acorde** (notas empilhadas), não símbolo |
| **linha curva COM SETA** (1,1 × 2,1 e 1,6 × 2,1 passos) | 2 | **slide/glissando cruzando cordas: símbolo multi-corda DE VERDADE** |
| **fragmentos de `)` e `}`** | 2 | **chave cortada** — a queixa do dono, visível no dado |

**Conclusões honestas**: (a) símbolo multi-corda é **raro** (~0,2 % dos componentes) — refazer a
arquitetura **para isso** pagaria pouco; (b) mas a **chave cortada** aparece já nesta amostra de 9
painéis, e o **dígito fundido em acorde** é um problema **separado e provavelmente mais frequente** que
o multi-corda; (c) o critério de componente único **subconta** multi-corda (um símbolo tracejado vira
vários pedaços), então 1 % é **piso**, não teto.

## 2026-10-09 — TAMANHO DO PROBLEMA no acervo da coleta: o corte na borda (8 %) é 8x o multi-corda (1 %)

24 painéis, 2.163 componentes (máscara `otsu`, componentes conexas, área >= 12 px):

| | n | % dos componentes |
| --- | --- | --- |
| componentes | 2.163 | 100 % |
| **cortados na borda de CIMA do painel** | **69** | **3,2 %** |
| **cortados na borda de BAIXO** | **104** | **4,8 %** |
| **cortados pelas bordas (total)** | **173** | **8,0 %** |
| alto >= 1,8 passo (tira de linha, chave, slide) | 220 | 10,2 % |
| **acorde fundido** (1,7–2,8 de altura, <=1,2 de largura) | **49** | **2,3 %** |
| multi-corda estrito (rodada anterior) | ~7 de 842 | **~1 %** |
| toca borda esquerda/direita | 76 | 3,5 % |

**A prioridade mudou de lugar, e agora com número**: o maior problema é **o CORTE NA BORDA (8 %)**, que é
o **ponto 7 da revisão** (`roi_das_cordas`, `tab/pipeline.py:184`, margem de 1 passo): símbolo que passa
da faixa é **ceifado**. É **8x mais frequente que multi-corda** — e é exatamente a queixa do dono
("tá cortando muita coisa").

Ordem de prioridade medida: **(1) corte na borda 8 %** > **(2) acorde fundido 2,3 %** > **(3) multi-corda
1 %**. Refazer a arquitetura para o (3) — que era o meu plano — seria atacar o menor dos três.

Por painel, a variação é grande: `C02`/`C03` (guitar dell'arte) têm **0** componentes altos; `C06`
(kimny's) tem **13**. Não é um problema uniforme no acervo.

## 2026-10-09 — OLHEI a folha da borda: o corte é de DÍGITO e de LINHA, não de símbolo (14ª correção)

Refinei os 173 "cortados na borda": **tira de linha 24** (corte legítimo), **fragmento baixo 48**,
**"candidato a símbolo" 96**. E então **olhei a folha** (`data/saida/multicorda/folha_borda.png`, 30
recortes):

| o que aparece | o que é |
| --- | --- |
| formas em `U`, metades de algarismo (0,9–1,0 × 0,4 passo) | **DÍGITO CORTADO AO MEIO** |
| tiras de 1,5–3,0 × 0,5 passo com barras verticais | linha de corda + barline (legítimo) |
| fragmentos de 0,1–0,4 passo | ruído / anti-serrilhado |
| blocos claros (C14) | área de vídeo, não tablatura |

**O corte na borda NÃO é problema de símbolo — é de DÍGITO e de LINHA.** Os "96 candidatos a símbolo
cortado" são, na maioria, **algarismos decepados**. Isso é **pior** para o produto (o algarismo é o núcleo
da entrega), mas **não** é o problema de símbolo que eu estava perseguindo.

**14ª vez que um número meu precisou de imagem para ser corrigido** — e a segunda rodada seguida em que a
folha de contato desfaz a minha conclusão anterior (multi-corda 75 % → 1 %; corte 8 % → dígito).

**Isso reorganiza a prioridade do goal outra vez**: (a) os problemas **de símbolo** medidos são pequenos
(multi-corda ~1 %, símbolo cortado < 4 % e boa parte é dígito); (b) o **dígito decepado na borda** e o
**dígito fundido em acorde** (2,3 %) são **problemas do núcleo do produto**; (c) a queixa do dono ("tá
cortando muita coisa") aponta para (b), não para (a).

**Próxima medição**: quantos algarismos decepados pela borda existem no acervo **e quantos deles o
classificador erra** — porque um dígito cortado é uma **perda de exatidão no número oficial**, e isso
tem de estar medido antes de qualquer reforma de símbolo.

## 2026-10-09 — os GLIFOS não são cortados (1 em 1.455) — e a queixa do dono é a JANELA do símbolo (15ª correção)

| | n | % |
| --- | --- | --- |
| glifos entregues (24 painéis) | 1.455 | 100 % |
| **glifos que tocam a borda do painel** | **1** | **0,1 %** |

**Os algarismos ENTREGUES não são cortados** — 1 em 1.455 — porque o **delimitador já descarta** o lixo de
borda antes de virar glifo. Os "8 % cortados na borda" que eu medi eram componentes da **máscara crua**,
uma camada **que o pipeline já filtra**. **15ª vez que um número meu mede a camada errada** — e a segunda
vez seguida que a conclusão cai por medição, não por argumento.

**E a queixa do dono continua válida, com o lugar certo identificado**: o corte que ele viu é o **ponto 5
da revisão** — **a janela que o modelo vê tem 2,4 × 1,6 passos (menos de duas cordas)**, e era **essa**
janela que a página de auditoria mostrava. **A imagem que eu dei a ele era recortada por construção.**
A queixa é precisa e é sobre a **janela do símbolo**, não sobre o algarismo.

**Consequência para o goal**: (3) consertar a captura tem alvo único e agora bem medido — **a janela do
símbolo** (crescer, e para multi-corda não recortar na corda). O que ainda **não** está medido é o custo:
janela maior carrega **mais contexto** (dígito, linha) e pode **aumentar o falso positivo** do filtro —
é a medição que precede a mudança, e a referência é precisão 0,197 / recall 0,216.

## 2026-10-09 — varrer a JANELA: crescer é neutro-para-pior — porque o modelo foi TREINADO na janela pequena

`janela_simbolo` parametrizada **só na segunda passada** (o caminho do símbolo) e varrida, contra a
referência `_6` (precisão 0,197 / recall 0,216):

| janela | aprovados | batem | precisão | recall |
| --- | --- | --- | --- | --- |
| **1,2 × 0,8** (2,4×1,6, a atual) | 178 | 35 | **0,197** | **0,216** |
| 1,5 × 1,25 (3,0×2,5) | 176 | 34 | 0,193 | 0,210 |
| 2,0 × 1,5 (4,0×3,0) | 176 | 34 | 0,193 | 0,210 |
| 2,5 × 2,0 (5,0×4,0) | 177 | 34 | 0,192 | 0,210 |

**Crescer a janela NÃO melhora nada** — neutro-para-pior. **E o motivo é o ponto 8 da revisão**: o modelo
foi **treinado** com a janela de 1,2 × 0,8 (os positivos do gabarito são recortes desse tamanho). Uma
janela maior é **entrada fora da distribuição**: a decisão não melhora, apenas se desloca. **Gabarito de
algarismo intacto** (0,917 / 0,986 / 0,944) — como esperado, porque o dígito não passa por essa janela.

**Conclusão para o goal (3)**: a janela **não é parâmetro, é retreino**. Consertar a captura exige as três
coisas **juntas**: (a) janela nova; (b) **retreinar** com ela; (c) **rotular na janela nova** — senão o
dono vê um pedaço e rotula o todo, que é exatamente o vício que ele apontou. Nenhuma das três resolve
sozinha, e (b) e (c) dependem de dado dele.

## 2026-10-09 — o gabarito TEM as coordenadas: o retreino na janela nova é tarefa conhecida e pequena

Inspecionando `data/gold/simbolos_marcados.json` (antes de retreinar):

| parte | campos | o que permite |
| --- | --- | --- |
| **523 positivos** | `x`, `y`, `frac`, `passo`, `significado`, `canal`, `imagem` | **regerar cada recorte na janela NOVA sem o dono** |
| 1.278 negativos | `cx`, `cy` | idem — **mas o espaço de coordenada tem de ser conferido antes** |

**A receita do (3) então é executável por mim**: regerar positivos **e** negativos em 3,0 × 2,5 passos,
retreinar as 3 sementes e medir **gabarito (tem de ficar 0,917 / 0,986 / 0,944)** e **fim a fim
(referência 0,197 / 0,216)**.

**E o aviso que eu gravo antes de começar**: `cx, cy` dos negativos **não dizem em que espaço estão** —
quadro ou ROI. Foi exatamente esse erro que já me custou uma rodada inteira (negativos recortados do
lugar errado; a LOCA caiu de 0,89–0,91 para 0,74–0,79 quando eu consertei). **Antes de regerar, conferir o
espaço por medição** (qual dos dois recortes contém tinta), nunca por suposição.

## 2026-10-09 (pós-reboot) — infraestrutura, conjunto novo e modelos treinados na janela 3,0x2,5

**O reboot trocou a infraestrutura e eu perdi tempo por não ler o guia:**

| o que | estado |
| --- | --- |
| daemon do Docker | **não subiu**; o CLI passou a falar com o **podman** (`/run/user/1000/podman/podman.sock`) |
| imagem `chorinho:dev` | **não existia** → **cada `docker compose run` tentava reconstruí-la** e estourava o tempo (2 min por comando). O `AGENTS.md` manda **`make build`** antes: feito, 8 min, resolveu |
| bind-mount `.:/app` | **Permission denied** com podman+SELinux → override **`compose.podman.yaml`** com `label=disable` (novo, no repositório) |
| `artefatos/` | **dono root do host** das execuções antigas; o container (mapeado no usuário) não escreve nem com `chmod` (que **falhou em silêncio** porque eu escondi o erro — erro meu) |

**Conserto estrutural para não perder mais nada no reboot**: os instrumentos saíram de `/tmp` e viraram
**módulo do projeto** — `tab/regerar_janela.py` (com `main()` e docstring, como o guia pede).

**Conjunto novo (janela 3,0 × 2,5 passos)**, gerado por esse módulo:

| | n |
| --- | --- |
| positivos | **511** |
| negativos | **908** (dos 1.278 originais: **370 perdidos**, porque só os positivos guardam o `frac` da imagem — declarado) |
| espaço dos negativos | **ROI — conferido por medição** (40 com tinta na ROI × 35 no quadro), não por suposição |

**Dois bugs meus pegos antes de virar resultado**: (1) o módulo tratava o caso "QUADRO" comparando contra
a ROI de novo (a conferência de espaço não media nada); (2) ele quebrava no meio com `KeyError: 'cx'`
porque os negativos têm **dois formatos** (`cx, cy` para token e `x, y` para janela vazia).

**Modelos treinados** com o conjunto novo: `artefatos/j25/simbolo_{1,2,3}/simbolo.pt` (via
`SAIDA_SIMBOLO`, variável nova que não muda o padrão).

## 2026-10-09 — GPU/CDI fora do ar depois do reboot, `torch.load` sem `map_location`, e uma medição que NÃO vale

**A minha primeira hipótese sobre o reboot estava certa e eu abandonei cedo demais**: `/var/run/cdi/` está
**vazio** (é tmpfs) → o container **não tem GPU** ✗. E isso quebrou o carregamento do modelo de
algarismo, que foi salvo em CUDA:

```
RuntimeError: Attempting to deserialize object on a CUDA device but torch.cuda.is_available() is False
```

**Corrigido**: `tab/reconhecer.py:78` e `tab/portao.py:641` faziam `torch.load(caminho)` **sem
`map_location`** — agora `map_location="cpu"` (o `tab/digito.py` já fazia certo). **Sem esse conserto,
nada roda nesta máquina desde o reboot** — é regressão de ambiente, não do meu código.

**E a medição do critério duplo NÃO está pronta — eu não vou apresentá-la como resultado:**

| | referência (script antigo: as duas passadas) | módulo novo |
| --- | --- | --- |
| aprovados | 178 | **29** |
| precisão | 0,197 | 0,931 |
| recall | 0,216 | 0,167 |

O módulo novo conta **só a segunda passada** (`origem == "simbolo"`) e, pior, os **dois lados deram
exatamente o mesmo número** (27/29) — o que indica que **a troca de modelo pode não estar surtindo
efeito** (`SAIDA_SIMBOLO`). **Números que deviam diferir e não diferem = instrumento quebrado, não
achado.** Antes de qualquer conclusão: corrigir a contagem (as duas passadas) e **provar que o modelo
carregado é o novo** (imprimir o caminho de onde ele veio).

**Estado entregue nesta rodada**: `tab/fimafim.py` (instrumento no repositório, com a ressalva do PISO de
precisão na própria saída), `tab/regerar_janela.py`, `compose.podman.yaml`, o conserto do `map_location`,
o conjunto da janela nova (511 positivos / 908 negativos) e os modelos `artefatos/j25/`.

## 2026-10-09 — o conserto da captura (janela 3,0x2,5 + RETREINO) NÃO muda nada: 78 acertos nos dois lados

Instrumento corrigido (`tab/fimafim.py` conta **as duas passadas** e **imprime o caminho do modelo** — a
troca de `SAIDA_SIMBOLO` está **provada** pelo caminho impresso, não suposta):

| | referência (1,2×0,8 + modelo antigo) | **janela nova (1,5×1,25 + retreinado)** |
| --- | --- | --- |
| modelo carregado | `artefatos/simbolo_2/simbolo.pt` | **`artefatos/j25/simbolo_2/simbolo.pt`** |
| aprovados | 271 | 277 |
| **batem** | **78** | **78** |
| precisão | 0,288 | 0,282 |
| recall | 0,481 | 0,481 |

**A janela maior COM retreino não muda nada** — os 78 acertos são idênticos. A troca de modelo funcionou
e mesmo assim **não há ganho**: a precisão cai 0,006 e o recall fica igual.

**Conclusão do objetivo (3)**: o conserto da captura **por esta via** (janela + retreino) **não se paga**.
Fica **desligado por padrão** (`janela_simbolo` continua (1,2, 0,8) e o modelo padrão continua o antigo);
os artefatos novos ficam em `artefatos/j25/` como registro, sem alterar o comportamento do pipeline. É a
sexta hipótese minha medida e **não adotada** — depois do piso de tinta, do dedupe, do contraste local, do
filtro de forma e da janela sem retreino.

**O que a rodada entrega de verdade**: `tab/fimafim.py` (instrumento no repositório, conta as duas
passadas, imprime o modelo e declara que a precisão é PISO), o conserto do `torch.load` sem
`map_location` (que travava TUDO nesta máquina sem GPU) e a prova de que a troca de modelo surte efeito.

## 2026-10-09 — FOLHA DO SÍMBOLO INTEIRO: o "corte" era a minha exibição, e ele se resolve de graça

`tab/folha_simbolos.py` recorta cada marca do dono numa janela **generosa (4,0 x 3,2 passos)** e monta
folhas de 24 — **sem tocar no pipeline**. Resultado: **162 recortes em 7 folhas**
(`data/saida/folha_inteira/folha_*.png`), e nela aparecem **os símbolos inteiros**: o arco completo
(`2—2`, `4—4`, `0—0`), os **`(7)` dentro de chaves** (a chave inteira), o **`♩` com haste**, o
**`4 -> 6·6` com seta** (slide).

**E eu repeti um erro de coordenada que já me custou uma rodada**: a primeira folha saiu cheia de **braço de
violão e fundo** ✗ porque a marca está em **coordenada da FAIXA** (y ~ 0..190) e eu recortei no **y do
quadro** (~800..900). É o **mesmo** erro de espaço da rodada dos negativos — e eu só peguei porque
**olhei a folha** antes de te mandar. **16ª vez** que um critério/medida meu precisa de imagem para ser
corrigido; a correção é `y_quadro = y_faixa + y0`.

**Conclusão que fecha a queixa do dono**: o corte que ele viu era a **minha exibição** (a janela de 2,4 x
1,6 que a auditoria mostrava). Mostrar o símbolo inteiro **é de graça e não muda a detecção** (medido: 78
acertos com janela pequena e com janela grande). Ou seja: **exibição e detecção são coisas separadas** — e
eu as tinha misturado, fazendo o dono ver um recorte que o modelo usava.

## 2026-10-09 — O DONO ROTULOU A FOLHA 0: só C06_008, C06_009 e C06_010 não são símbolos — e são DÍGITOS DE ACORDE

Veredito dele, textual: **"os únicos que não são símbolos dessa imagem C06_008, C06_009, C06_010"** e
**"o recorte do símbolo tá perfeito"**.

| o que ele apontou | o que é |
| --- | --- |
| `C06_008` (`2/3`), `C06_009` (`0/1`), `C06_010` | **dígitos de acorde EMPILHADOS que viraram UM componente** |

**Isso corrige uma medição minha**: o "acorde fundido" que eu contava como **2,3 % dos componentes** e
tratava como **candidato a símbolo** — **não é símbolo**: é o **dígito do acorde**. Ou seja, os
componentes altos que eu media como "multi-corda / símbolo" incluem **notas empilhadas da própria
tablatura** — e o dono acabou de separar as duas coisas para mim.

**E valida o conserto da exibição**: "o recorte do símbolo tá perfeito" — a janela de 4,0 x 3,2 passos
mostra o símbolo inteiro, e ele confirmou olhando. **Exibição resolvida**; a detecção continua sendo o que
a medição diz (janela maior não muda os 78 acertos).

**Rótulos salvos** em `data/gold/folha_labels.json` (para não se perderem num reboot, como já aconteceu).

**Próximo passo combinado com ele**: ele ofereceu rotular mais se eu pedir — as **6 folhas restantes**
(`folha_1` … `folha_6`, 138 recortes) pelo **nome único** de cada recorte.

## 2026-10-09 — O ARPEJO: o dono apontou que o TAMANHO do símbolo É A INFORMAÇÃO (e a imagem confirma o corte)

Rótulos dele na `folha_1`: **o único que não é símbolo é `C07_029`**; tudo o mais é símbolo.

**E a observação que vale mais que o rótulo**, textual: **"o C07_28 é o arpejo, um símbolo que tem tamanho
variável dependendo de quantas cordas tem que ser tocadas — seria interessante se ele pegasse ele por
inteiro para definir quais cordas devem ser arpejadas."**

**Confirmei por imagem**: o recorte de `C07_028` (82 x 64 px, janela 4,0 x 3,2 passos) **corta o arpejo** —
a linha ondulada **começa acima do topo e continua abaixo** do recorte ✗. **O corte apaga a informação**:
a **altura** do arpejo é **quais cordas** devem ser tocadas.

**Consequência para o produto**: para o arpejo (e para todo símbolo cujo tamanho significa algo), o recorte
**não pode ser uma janela fixa** — tem de ser **o próprio componente** (a caixa do traço, com margem) ✓. A
caixa do componente dá, de graça, **exatamente as cordas que ele cobre** — que é a definição do arpejo.

**E é a segunda vez que ele me dá uma classe do vocabulário vendo o dado**: primeiro o dígito de acorde
empilhado (`C06_008/009/010`, que eu contava como símbolo), agora o arpejo com papel semântico. **O
vocabulário está saindo dele, do dado certo** — que é o que eu queria desde o começo e não conseguia
produzir sozinho.

## 2026-10-09 — (a) RECORTE DO SÍMBOLO: componente + janela fixa — e o arpejo aparece INTEIRO com as cordas

Duas lições do dono embutidas no recorte (`tab/folha_simbolos.py`), cada uma corrigindo um corte meu:

1. **ARPEJO** (ele: *"tem tamanho variável dependendo de quantas cordas tem que ser tocadas — seria
   interessante se ele pegasse ele por inteiro para definir quais cordas devem ser arpejadas"*): o recorte
   **não é mais janela fixa** — é a **caixa dos componentes vizinhos da marca**;
2. **SÍMBOLO COMPOSTO** (parênteses + arco, observação dele): são **componentes separados**, então a caixa
   por componente sozinha continua cortando — daí a **união com a janela fixa**, que garante o **contexto
   lateral**.

| recorte do `C07_028` (o arpejo) | resultado |
| --- | --- |
| janela fixa (antes) | **82 × 64 px** — começa acima do topo e continua abaixo: **cortado** |
| só a caixa do componente | **28 × 117 px** — alto mas estreito: **perde a linha ondulada** ✗ |
| **componente ∪ janela fixa** | **84 × 117 px** — **o arpejo inteiro e as 5 cordas que ele cruza** ✓ |

**Alturas dos 162 recortes**: mediana **3,30 passos**, p90 **4,85**, máximo **7,40** (antes o teto era 3,2 por
construção). Confirmado **por imagem**, não por suposição — e as duas tentativas erradas foram pegas
olhando: a caixa por componente sozinha **perdia o arpejo**, e eu ia te mandar isso como conserto ✗.

## 2026-10-09 — recorte: lateral estreito (o dono achou largo) e a causa REAL do arco largo

Rótulos dele nesta rodada, refinando os anteriores: **`C06_008` e `C06_009` não são símbolos**;
**`C06_010` É símbolo** ("um arco de ligadura simples") — e a crítica: **"expandiu demais para a esquerda, a
imagem podia ser menor"**.

**Conserto**: o eixo **x** leva só **0,6 passo** de margem (a janela fixa de ±2,0 entrando inteira no x era
o que alargava); o **y** mantém a generosidade, porque **é a altura que carrega informação** (o arpejo diz
quais cordas).

| recorte | antes | depois |
| --- | --- | --- |
| `C07_028` (arpejo) | 84 × 117 | **55 × 117** — **a linha ondulada inteira e as 5 cordas, com menos gordura** ✓ |

**Confirmado por imagem**, não por suposição.

**E a causa do arco largo ficou identificada — não é a janela**: `C06_010` mede **235 px de largura porque o
COMPONENTE do arco encosta na linha de corda e traz um pedaço de linha junto** ✗. A correção seria apagar
as faixas (`_sem_faixas`) **na hora de medir a caixa** — mas isso **cortaria o arpejo**, que **cruza** as
linhas ✗. É um trade-off que exige medição própria (quanto o arco encolhe × se o arpejo sobrevive), e
**não** entra por tentativa.

## 2026-10-09 — o arco largo: apagar as faixas a 0,12 passo NÃO muda nada (a faixa é mais fina que a linha)

O dono mandou **duas vezes** o mesmo pedido — *"C06_010 é um arco de ligadura simples mas expandiu demais
para a esquerda, a imagem podia ser menor"* — e ele está certo: eu tinha **diagnosticado** e parado para
"medir o trade-off" em vez de consertar ✗.

Tentei o conserto que o diagnóstico pedia: **apagar as faixas das cordas na máscara do recorte** (`_sem_faixas`
com ±0,12 passo) para o componente do arco não trazer a linha junto.

**Resultado: NADA mudou.** `C06_010` continua **235 × 80**, idêntico a antes ✗.

**E o motivo eu já tinha medido nesta sessão**: **as linhas têm 3–5 px = 0,15–0,23 passo** e a minha faixa
tem **±0,12 passo** ✗ — **a faixa é mais fina que a linha**, então não a desconecta ✓. É exatamente o que
aconteceu na rodada do "componente gigante de 73 passos", onde apagar a mesma faixa também foi neutro.

**Próximo passo, e não por tentativa**: **varrer a espessura da faixa** (0,15 / 0,2 / 0,3 passo) medindo
**os dois lados**: quanto o `C06_010` encolhe **×** se o `C07_028` (arpejo, 55 × 117) **sobrevive inteiro**.
A faixa certa é a **menor que desconecta o arco** — e o arpejo é o juiz.

## 2026-10-10 — PILOTO de ponta a ponta: a cadeia estava QUEBRADA (2 bugs) e o MARCADOR não aparece

Piloto pedido pelo dono, num vídeo do `iwaki` (`- therru's song - aoi teshima- tab.mp4`, 60 s a partir de
0,4). **A cadeia completa (`tab.transcrever`) não rodava** — e nunca tinha rodado nesta sessão:

| bug | o que era |
| --- | --- |
| `KeyError: 'y929'` | o `achar_painel` evoluiu e devolve painel com nome por **coordenada**; o `transcrever` ainda procurava nos **três nomes fixos de faixa** (`FAIXAS`). **Cadeia inteira parada** ✗ |
| `NameError: name 'nome' is not defined` | **introduzido por mim** ao corrigir o primeiro: eu tirei a linha que definia `nome` e ela ainda era usada no JSON ✗ |

Conserto: a faixa vem de **`roi_das_cordas(m)`** (a faixa das cordas no quadro, que é o que o cursor varre).

**Resultado do piloto**: JSON gerado com **43 notas** em 60 s. Estrutura: `passo`, `linhas_y`, `barlines_x`,
`notas`, `tempo`, `video`, `painel`, `quadro_em_s`, `lido_via`, `janelas_com_cursor`, `segundos_com_cursor`.
Casas lidas: **0, 2, 3, 5, 6, 7** + as classes `harmonico`, `junk`, `tecnica`.

**E o achado que responde à pergunta do dono**: **`tempo: {"medido": false, "motivo": "marcador
sem_marcador na janela varrida", "pontos": 0}`** ✗ — **o marcador não foi encontrado**, então **0 de 43
notas têm instante** ✗. O núcleo do produto (cada nota no seu tempo) **não está entregue** neste vídeo.

**Resposta a "dá para transformar todos os vídeos?"**: **não ainda** ✗ — e agora com a lista exata:
(a) a cadeia ponta a ponta **estava quebrada** e agora roda ✓; (b) o **marcador** (que dá o tempo) **falta
em pelo menos este vídeo** ✗ — e sem ele o JSON é uma tablatura **sem tempo**, que não é o produto ✗;
(c) a **casa fora do gabarito** (4 canais / casas 0–7) segue **não validada** ✗; (d) o **acorde de dígitos
empilhados** segue **não medido** ✗.

## 2026-10-10 — DISTRIBUIÇÃO DE FORMAS DO MARCADOR (17 canais, 1 vídeo cada) — o número que define o desenho

Varredura com `tab.formas_do_marcador` (módulo novo, no repositório) e `tab.cursor.rastrear` a cada 30
quadros:

| forma | n | canais |
| --- | --- | --- |
| **ausente** | **8** | cifra club · guitar dell'arte · iwaki · **kimny's guitar** · mr. tabs · shin izumi · tv on guitar · ギタロー |
| **pisca** | **3** | leonardo ramos · pablo romé · transcriptor |
| **salta** (patamares) | **4** | paolo d'angelo · serge kottelat · **sky guitar** · tv cifras |
| **varre** (desliza) | **2** | robert lunn · violaodecria |
| **destaque** | **0** | — |

**Consequência para o desenho**: **todas as formas não-ausentes (9 de 17) são SÉRIES DE POSIÇÃO** ✓ — então
o **estado = posição x** ✓ cobre `varre`, `salta` e `pisca` com **UMA regra** ✓ (o onset = o primeiro quadro
em que a nota passa a ser a atual). Não é preciso uma regra por estilo ✓ — a objeção do dono está
respondida **com dado**.

**RESSALVA que eu registro antes de comemorar**: o `rastrear` procura a **faixa vertical** (o marcador de
posição). Um marcador por **destaque de dígito** — que o próprio `AGENTS.md` descreve ("cor no algarismo")
— seria contado como **ausente** ✗. Ou seja: os **8 "ausente" podem ser dois grupos diferentes**, e só
olhar separa. **Antes de declarar "sem tempo" para 8 canais, eu olho.**

**Rótulo que dói e é útil**: o `kimny's guitar` — o canal de onde vêm **as 200 marcas de símbolo** do dono
— tem, no vídeo amostrado, **marcador AUSENTE** ✗. Isso não invalida os rótulos de símbolo (símbolo é
geometria, não tempo ✓), mas significa que **aquele canal pode não entregar tempo** ✗.

## 2026-10-10 — OLHEI os "ausente": o grupo se DIVIDE, e há marcador por COR NO ALGARISMO (com imagem)

Extraí **dois quadros** de três canais classificados como `ausente` e olhei
(`data/saida/piloto/ausentes.png`):

| canal | o que a imagem mostra | veredito |
| --- | --- | --- |
| **`kimny's guitar`** (frac 0,65) | **um algarismo em VERDE** entre os pretos (`3 2 2 0`, o `2` verde) | **TEM marcador** — na forma **"cor no algarismo"** ✓, que o `rastrear` **não vê** ✗ |
| **`mr. tabs`** (frac 0,35) | **destaque azul** cercando o `(12)` | **TEM marcador** ✓, também invisível ao `rastrear` ✗ |
| **`shin izumi`** (frac 0,35) | tablatura limpa, sem destaque visível | indefinido ✗ — precisa de olhar mais perto |

**Ou seja: o `ausente` do `rastrear` NÃO É "sem marcador"** — ele é **"sem FAIXA vertical"** ✗. Pelo menos
**2 dos 8** têm marcador real em outra forma ✓. A minha ressalva registrada na rodada anterior estava
certa, e agora tem imagem ✓.

**Consequência para o desenho (e é o que o dono previu)**: o estado **não é uma posição x** ✗ — o estado é
**"qual nota está acesa"** ✓, com **duas fontes** que alimentam a MESMA regra:
1. **posição x** (a faixa ✓) → a nota cujo intervalo contém o x ✓ — cobre `varre`, `salta`, `pisca` (9 de 17);
2. **destaque de cor** (o algarismo aceso ✓) → a nota **cuja caixa está destacada** ✓ — cobre `kimny's`,
   `mr. tabs` e o que mais aparecer ✓.
A associação (estado → onset ✓) é **a mesma** para as duas ✓.

**Confirmação de brinde**: em `kimny's` e `shin izumi` os quadros de 0,35/0,65 mostram **o braço do
violão** ✗ — a tablatura **aparece e desaparece** ✓, como a regra 10 do `AGENTS.md` já dizia ✓.

## 2026-10-10 — O SEGUNDO OBSERVADOR É VIÁVEL: um algarismo colorido (22,7) e TODOS os outros em ZERO

`tab/destaque.py` (módulo novo, no repositório) mede a **coloração** de cada token com
`max(canais) - min(canais)` — que é **invariante ao brilho** (algarismo claro e escuro, ambos cinzas, dão
zero ✓; verde dá alto ✓). E o sinal **não precisa de rótulo**: se um algarismo está aceso e os outros não,
ele é **outlier**.

Resultado no `mr. tabs` (o vídeo do destaque azul ✓):

| | |
| --- | --- |
| tokens no quadro | **68** |
| **mediana da coloração** | **0,0** |
| **máximo** | **22,7** |

**Um algarismo colorido e todos os outros em zero exato** — a separação **é** o sinal, e é limpa. Ou seja:
o segundo observador do estado (o "destaque de dígito" que o `AGENTS.md` já descrevia ✓) é **viável**, e o
estado pode ser lido **sem saber o estilo do vídeo** ✓.

**O que ficou pendente** (e é do próximo round): o `kimny's guitar` **não deu saída** ✗ — o nome do vídeo
tem apóstrofo e quebrou a citação no meu comando de shell ✗ (erro de **método** meu, não do código ✓). É
retestar com aspas corretas. E o `shin izumi` segue **indefinido** ✗ — na imagem eu não vi destaque ✓, e
esta medição vai dizer se é ausência de verdade ✓ ou um destaque que eu não vi ✓.

## 2026-10-10 — A REGRA DO ESTADO FUNCIONA: sky 0 -> 29 de 38, e o sem-marcador continua 0 COM MOTIVO

`tab/estado.py` (módulo novo) implementa a formulação acordada: **o estado é a nota cuja célula de x contém
o marcador** — células formadas pelas fronteiras **no meio** entre notas consecutivas. É isso que faz a
**mesma** regra valer para os dois estilos: no **salto** o marcador **cai dentro** da célula; na
**varredura** ele **entra** nela. O **onset** é o primeiro instante de cada passagem.

| piloto | antes | **agora** |
| --- | --- | --- |
| **`sky guitar`** (marcador por patamares) | **0 de 44** ✗ | **ONSETS = 29 de 38** (76 %) ✓ |
| **`iwaki`** (sem marcador) | 0 ✓ | **0 de 28, com o MOTIVO escrito** ✓ |

Os tempos do `sky` são **coerentes entre si**: `245,25 · 246,25 · 247,25 · 248,25 · 249,25` — **um segundo de
intervalo** ✓, que é o ritmo dos pulos medido no marcador (0,67–1 s ✓). E o `iwaki` imprime
**"MOTIVO: nenhuma amostra com x (marcador ausente na janela) — tempo NAO medido"** ✓ — o silêncio é
**declarado**, não escondido ✓.

**Nenhuma linha de código menciona estilo** ✓: nem "patamar", nem "deslizamento", nem canal. A regra é uma
só — **qual nota é a atual** — e ela cobre os dois casos que eu medi ✓.

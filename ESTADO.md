# ESTADO.md — número oficial, o que está medido e o que falta

Documento de entrada do projeto. **Todo número aqui é média de ≥3 sementes**, nunca
execução única — sem isso o mesmo código já deu 0,729 e 0,854. O histórico completo
das 65 rodadas está em [`docs/HISTORICO.md`](docs/HISTORICO.md).

## Atualizar o censo do acervo (comando único)

O acervo cresce. Para censar só o que é novo, rode:

```bash
docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho \
    python -m tab.censo --cache --janelas-por-canal 30 \
    --saida data/saida/censo/censo_cache.jsonl
```

- Vídeo já censado (chave `caminho|tamanho|mtime`) não é refeito. Vídeo novo em canal
  existente, ou canal novo, é censado.
- Canais com `rollout: fora` em `configs/canais.yaml` (hoje `violaodecria` e `tv cifras`,
  decisão 0009) são **pulados**. `--incluir-fora` os censa. Com `--canal`/`--canais`, o
  pedido explícito vale e nada é pulado.
- Canal sem entrada no yaml entra e aparece no log como `canal novo`. **Hoje o yaml cadastra
  7 dos 21 canais do acervo**, então 14 aparecem como novos em toda execução até o perfil de
  cada um ser escrito.
- Estratificação (`--janelas-por-canal 30`): vídeo novo ganha janela se cair na amostra
  espalhada do canal atual. Canal com até 30 vídeos dá janela a todos; acima disso o vídeo
  novo ganha janela só se cair na amostra recalculada (os extremos sempre caem). Vídeo já
  censado não é refeito, então mantém o que ganhou na época.
- Ao fim, o resumo diz quantos vídeos novos foram censados, por canal, e quantos canais são
  novos. Medido sem processar nada: 2.799 vídeos ativos, 1 pendente no instante da checagem.

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
| contar notas que **receberam algum tempo** sem gabarito de tempo | número inflado: "sky 40/44" **não é** tempo certo — não existe gabarito de tempo (T0.3) |
| associar a série do marcador do **vídeo inteiro** às notas de **um** quadro | onsets de **outra página**: no `sky2.json` a nota da coluna 2 recebeu **266,1 s**, quando a tela mostrava o compasso 5 (T0.3) |
| misturar `x` da **ROI recortada** com `x` do **quadro** | coluna errada: no `retrato brasileiro` o recorte começa em **x0 = 70 px** e o marcador de 245,5 s caiu na **coluna 3** em vez da 1 (T0.3) |
| `cv2.VideoCapture` fora do leitor | **falha calada em 44 %** do acervo (AV1): **abre**, informa `FRAME_COUNT` e **não decodifica** — `rastrear` devolve 0 amostras, indistinguível de "sem marcador" (T0.3) |
| pareamento da tela do legado por instantes, com exibição = vídeo inteiro | escolheu a tela com mais instantes (5), não a página lida; instante fora da janela contava como erro. Corrigido: pareamento por conteúdo e exibição = `janela_s` |
| fundir componentes da mesma corda com vão <= 0,39 passo (limiar entre algarismos e notas) | **não separa**: algarismos de dois dígitos vão 0,23 a 0,32 passo, e notas diferentes vizinhas chegam a 0,32 e 0,37 (mesmo vão de 7 px do `13` da pág. 8). Página 5 perde 3 notas, casa certa 39 → 37 (revertida; ver `docs/rodadas/0005-casa-dois-algarismos-vao.md`) |
| `--escala larga` (algarismo de 1,0 a 1,4 passo em metade das linhas do gerador) para o `0` perdido nas cordas internas | **0,940** (64/68/71 = 203/216), contra 0,949 dos `oficial_*`: semente 1 cai 2, semente 2 cai 3. Altura ficou mais perto do real (mediana 0,75 contra 0,93), mas dobrou os glifos partidos em 2 componentes (0,30 contra 0,00 no real). Não adotado (ver `docs/rodadas/0009-zero-nas-cordas-internas.md`) |
| `_glifos_por_faixa` só descartar componente em coluna de barline se for fino (w <= 0,25 passo), para recuperar os algarismos que o sakura perde em barline falsa | **pior em tudo**: inventadas MVP 0 → 113, South American 1 → 133, EOB 471 → 588; métrica oficial quebra (contagem muda). Pedaços de barline real passam a virar `1`/`0` (revertida; `data/saida/barline_fina/`) |
| separar barline real × falsa por geometria da coluna (cobertura, trecho contínuo, tinta acima/abaixo do sistema) | **não separa**: 14 falsas × 335 reais em 41 quadros; a melhor regra (abaixo > 0,4 passo ou cobre < 0,85) pega as 14 mas marca **36 reais** como falsas; barline real do retrato desce ~0,46 passo. Falsas concentradas no sakura (8 de 11 colunas); nos ouros, 6 de 338 (`data/saida/barline_coluna/`) |
| salto > 40 px tratado como troca de página, sem conferir sobreposição (C1, rodada 0150) | **errado**: `mr. tabs` e `kenneth` rolam em saltos com sobreposição; a triagem contou 66 rolantes como "não rola" (correção na 0150) |
| mediana do erro como critério de aceite da rolagem (C1, rodada 0153) | **esconde erro grosso**: mediana 0,32 px passa, mas 6 de 13 definidos erram mais de 5 px. Exigir pior caso |
| medir o salto só entre quadros parados (C1, rodadas 0152 e 0153) | **perde a animação** e cria aliasing de período: erros de 690, 779 e 1557 px no `mr. tabs` (compassos alternados de ~340 e 439 px) |
| ajuste fino que trata tudo que não é nota do ouro como fundo (integração, n4 `treinar_ft.py`) | **apaga o X**: no End of Beginning o produto dá ~1 X para 76 regiões marcadas; o modelo da dobra que não viu o vídeo dava 93 |
| abrir a ferramenta do ouro (`tab.ouro_video servir`) com estado desatualizado | **desfaz edições feitas fora dela**: sobe por cima do estado. Corrigido em `bc431c0f`: não sobe se o ouro diverge |
| **braço, nut fora: numerar pelos quadros vizinhos (V) ou pela junção braço-corpo (J)** | **reprova** (1031): 0 e 1 acerto em 16; a regra "nut visível" é enganada pelo próprio erro (o detector põe o nut no 1º traste longe da borda), e a junção por cor pula entre quadros (k = 4 e k = 1 no mesmo vídeo de 12 s) |
| **braço, estágio 2 retreinado com os 8 quadros de nut fora (A5)** | ganho pequeno e instável entre sementes (2 a 4 erros que passam, contra 4 do A4, fora do treino); não ganha na M11b (1031) |
| **braço, conferir a numeração pelas marcações com limiar 4 × mediana** | **0/6** (1034): o tampo claro e a mão sobem a mediana e apagam as marcações, que eram detectadas |
| **braço, marcações com mancha compacta e limiar 4 × Q25** | seguro (510 decisões sem rótulo, 0 disparo), mas **não decide no 1027:q56** (1035): não ajustar de novo nos mesmos 6 falsos |

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
| caixa de presença pela **uniformidade do fundo** na reserva (critério atual) | erra os 9 erros de caixa: 5 braço e 4 pauta, todos com TAB na faixa base; a TAB densa tem mais tinta e perde para o braço liso (Fase 7.1, rodada 0007) |
| caixa pela **fração de papel branco** na reserva (C1) | precisão de caixa **0,976** (123/126) com o gabarito de 7.1 + rótulos visuais do agente (aceite 0,98): não adotado; as 3 caixas erradas são sobre a pauta (VN18, VN20, FP38); MVP sem regressão (Fase 7.1, rodada 0007) |
| separar pauta de TAB pelo **preenchimento médio** dos tokens | sobrepõe: TAB 0,46 a 0,91 contra pauta 0,49 a 0,59 (Fase 7.1) |
| separar pauta de TAB pelo **`tab.digito`** (P de algarismo por token) | marca as cabeças de nota da pauta como algarismo, p≈1,0 nas 4 pautas (Fase 7.1) |
| regra "5 linhas fortes + 1 fraca = pauta" **sozinha**, sobre o recorte re-segmentado do `refinar` | não pega a VN18: no recorte estreitado as 6 linhas da pauta são todas fortes (espaçamento 14); a caixa continuava na pauta (Fase 7.1 C1b) |
| `refinar` que re-segmenta o recorte sem conferir as cordas em y | a re-segmentação troca a TAB pelas linhas da pauta (VN18, FP38); só vale se as cordas em y forem as do candidato (Fase 7.1 C1b) |
| casa de dois algarismos fora da classe do modelo também no glifo de dois componentes (`_casa_das_partes` sem o caminho do par) | um `3` lido como `2`+`0` virou `20`; `oficial_3` caiu 68 → 67/72 (amostra paolo 3). **Revertido**: a casa fora do modelo vale só para o par geométrico de dois tokens isolados (rodada 0008) |

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

## 2026-10-10 — OS DOIS OBSERVADORES FUNCIONAM, com a MESMA regra

| vídeo | observador | antes | **agora** |
| --- | --- | --- | --- |
| `sky guitar` | posição x (patamares) | 0 de 44 ✗ | **29 de 38** ✓ |
| **`mr. tabs`** | **destaque de cor** (azul) | 0 ✗ | **10 de 19** ✓ — destaque achado em **30 de 30** amostras ✓ |
| `iwaki` | nenhum | 0 ✓ | **0 de 28, com o MOTIVO** ✓ |

**E os dois observadores usam a MESMA regra**: o estado é "qual nota está acesa" — na posição, a nota cuja
célula de x contém o marcador; na cor, a nota cuja célula de x contém o **token colorido** ✓. Nenhuma linha
menciona estilo ✓.

**Três erros meus pegos nesta rodada, todos de método**:
1. o nome do vídeo que eu **chutei** ✗ (o real tem 60 caracteres com `｜` ✓) — o mesmo tipo de descuido dos patches;
2. usei **`cv2.VideoCapture`** ✗ → **44 % do acervo é AV1 e o OpenCV não decodifica** ✓ → `frames_totais = 0`
   e o laço **nunca rodou** ✓. O projeto tem `ler_quadro` (com ffmpeg ✓) exatamente para isso — **regra que
   eu violei** e que está no `AGENTS.md`;
3. peguei o destaque nos **`caixa_token` das notas** ✗ — que só existem quando o filtro de símbolo roda ✓ —
   e por isso o denominador deu **ZERO** ✗. O destaque está no **token da grade** ✓.

## 2026-10-10 — LINHA DE BASE LIMPA: o gabarito de algarismo está intacto ANTES da integração

Medido **antes** de ligar a regra do estado no `transcrever` (para o efeito ser **atribuível**, e não
misturado com o que já existia):

| semente | resultado |
| --- | --- |
| `oficial_1` | **66/72 = 0,917** ✓ |
| `oficial_2` | **71/72 = 0,986** ✓ |
| `oficial_3` | **68/72 = 0,944** ✓ |

**Exatamente a referência** ✓. Nada do que eu mexi nesta sessão (símbolo, recorte, janela, marcador) tocou
a cadeia do algarismo ✓ — e agora isso está **provado**, não suposto.

E o estado reproduz: `ONSETS = 29 de 38` no `sky` ✓.

**O QUE EU NÃO FIZ NESTA RODADA, e por quê**: a integração no `transcrever` ✗. É a mudança mais delicada do
goal (mexe na cadeia do tempo que já existe ✓) e o meu contexto está no fim ✗ — **patch às pressas é
exatamente o erro que eu cometi 4 vezes hoje** ✓ (dois deles quebraram funções em silêncio ✗). **Prefiro
entregar a rodada com a linha de base limpa e a integração planejada a entregar um patch duvidoso.**

**PLANO DA INTEGRAÇÃO (para o próximo round, com contexto fresco)** — **aditivo**, sem remover nada:
1. no `transcrever`, quando a cadeia atual (velocidade ✓) devolver `medido: false` ✗, montar o **estado** a
   partir da **mesma** série do `rastrear` ✓ mais o `x` das notas ✓;
2. aplicar a **regra única** (`nota_do_x` ✓) → **onsets** ✓ → preencher `tempo` de cada nota ✓;
3. se **nenhum** dos dois observadores achar nada → manter **`medido: false` COM o motivo** ✓ (nunca zero
   silencioso ✗), incluindo o motivo do observador de cor ✓;
4. medir: `sky` (29/38 ✓), `mr. tabs` (10/19 ✓), `iwaki` (0 e **com motivo** ✓) → e **o gabarito de novo**,
   que tem de continuar **0,917 / 0,986 / 0,944** ✓ (a régua desta rodada ✓).

## 2026-10-10 — DESCOBERTA QUE MUDA A INTEGRAÇÃO: a regra dos patamares JÁ EXISTIA

Lendo a região do tempo no `transcrever` **antes** de tocar (a lição dos 4 patches falhados ✓), achei o que
eu não sabia:

```python
if veredito["veredito"] in {"desliza", "salta"}:
    if veredito["veredito"] == "desliza":
        onsets = atribuir_tempos([n["x"] for n in r["notas"]], serie)
    else:
        onsets = tempos_por_patamar([n["x"] for n in r["notas"]], serie)   # <- JÁ EXISTE
else:
    ... "medido": False ...
```

**O código já trata "salta" com `tempos_por_patamar`.** O problema do `sky` **não é falta de regra** ✗ — é
que o **veredito** (`resumo`) classifica a série dele como **`"lento"`** ✗, cai no `else` ✓ e devolve zero
tempos ✗.

**Consequência, e ela é boa**: a minha regra do estado **não é uma regra nova** ✓ — é a **generalização das
duas que já existem** (`atribuir_tempos` para "desliza" ✓ + `tempos_por_patamar` para "salta" ✓), que hoje
são **dois caminhos separados** ✗ e por isso **deixam de fora tudo que o veredito não reconhece** ✗ (o
`sky` é o caso vivo ✓).

**Onde a integração deve entrar** (e não é onde eu ia mexer ✗): em vez de **acrescentar** mais um ramo ✗, a
regra única **substitui o `if/else` do veredito** ✓ — uma passagem só, com o estado ✓, o que também
**apaga** a bifurcação por estilo ✓. Isso é uma **limpeza**, não um remendo ✓ — e é por isso que ela merece
contexto fresco ✓, não o meu fim de sessão ✗.

## 2026-10-10 — A REGRA ÚNICA EM CINCO VÍDEOS: 96 % no `salta`, e DUAS FORMAS AINDA SEM EXPLICAÇÃO

Rodei a **mesma** regra (observador de posição ✓) em um vídeo de cada forma medida:

| canal | forma | passo 30 | **passo 5** |
| --- | --- | --- | --- |
| `sky guitar` | salta | 29 de 38 | — |
| **`serge kottelat`** | **salta** | 34 de 49 | **47 de 49 = 96 %** ✓✓ |
| `robert lunn` | varre | 4 de 18 | **4 de 18** ✗ |
| `leonardo ramos` | pisca | 1 de 45 | **1 de 45** ✗ |

**O que está PROVADO**: a regra funciona **muito bem no `salta`** ✓ (76 % no `sky` ✓, **96 %** no `serge` ✓) —
e a **amostragem importa** ✓ (34 → 47 ✓): amostrar a cada 1 s perdia patamares ✓. **Uma regra, dois canais,
duas séries diferentes ✓.**

**O que NÃO está explicado, e eu não vou fingir que está** ✗:
1. **`varre` = 4 de 18** ✗ — e **não é aliasing** ✗: com `passo=5` ele tem **242 amostras, todas com x** ✓ e o
   número **não mudou** ✓. Hipótese a testar: na **janela** varrida o marcador está **parado** (a forma
   "varre" veio do vídeo inteiro ✓), ou o `x` das notas e o `x` do marcador **não se alinham** ✗;
2. **`pisca` = 1 de 45** ✗ com **1 única amostra com x** ✗ em 60 s — o `rastrear` achou o marcador **uma vez**
   ✗. Antes de qualquer teoria: **olhar** o vídeo e **despejar a série** ✓ (a regra 4 do `AGENTS.md`: olhe o
   quadro antes de teorizar ✓).

**Registrado com os números, incluindo os que não fecharam** ✓ — é a regra 11 do projeto ✓.

## 2026-10-10 — OS DOIS CASOS SEM EXPLICAÇÃO: a série explica, e NENHUM é a regra

Despejei a série (regra 4 do `AGENTS.md`: olhe antes de teorizar ✓) — e as duas causas apareceram:

**1. `robert lunn` ("varre" ✗) — NÃO É DESLIZAMENTO, é patamar outra vez**
Série: **101 amostras, 11 posições distintas** de x (173 → 974 ✓), e o padrão é `x=684` por ~6 amostras ✓
e **salto** para `264` ✓. Ou seja: **o marcador pula**, e o meu **classificador** que chamou o vídeo de
"varre" usou `saltos < 20` ✗ com 10 saltos no vídeo ✓ — **o erro é do classificador, não da regra** ✗.
E os 4 onsets de 18 têm causa própria, que é uma limitação **real**:

> **A regra compara o `x` das notas LIDO NUM QUADRO (0,4 ✓) com uma série de marcador de VÁRIOS MINUTOS** ✗.
> Numa tablatura que **rola**, as notas **mudam de x** ao longo do vídeo ✗ → os dois `x` não se correspondem
> ✗. Funciona onde a janela é curta e a tablatura é estável ✓ (`sky` 76 % ✓, `serge` 96 % ✓).

**2. `leonardo ramos` ("pisca" ✗) — a janela do MEU INSTRUMENTO caiu num trecho morto**
Série: **1 amostra, `t = 2,4 s`** ✗ (`cobertura 0,006` ✓). O `tab.estado` escolhe a janela pelo **`t` da
primeira amostra** ✗ → varreu **2,4–62,4 s** ✓ — e nesse trecho o marcador aparece **uma vez** ✓. **Erro do
meu instrumento** ✗, não do acervo nem da regra ✓ (o `AGENTS.md` já diz: o cursor é **intermitente** ✓).

**Consequência para a integração**: (a) o observador precisa de **notas por quadro** (não de um quadro só ✓)
para tablatura que rola ✗; (b) a **escolha da janela** não pode ser "o `t` da primeira amostra" ✗ — tem de
ser onde o marcador **está ativo** ✓ (o código já tem essa preocupação na outra cadeia ✓, com as
`janelas_com_cursor` ✓).

## 2026-10-10 — o "pisca" da minha distribuição está ERRADO: é quase-ausência, não forma

Consertei o meu próprio instrumento (a janela que caía em trecho morto ✓, cedendo à série inteira quando
tem pouca coisa ✓ — declarando em vez de esconder ✓):

| | antes | depois |
| --- | --- | --- |
| `leonardo ramos` | 1 de 45 ✗ | **1 de 45** ✗ — o fallback **não** disparou ✓ |
| `serge kottelat` | 47 de 49 | **47 de 49** ✓ — **não piorou** ✓ |

**E a razão de não disparar é o achado**: o `leonardo ramos` tem **1 amostra com marcador no VÍDEO
INTEIRO** ✗ (não 5 ✓). Ou seja: **ele não é "piscante"** ✗ — é **praticamente ausência** ✓, e o meu
classificador (`cobertura < 0,5 e distintas <= 3` ✗) o jogou no balde **"pisca"** ✗.

**Consequência, e ela corrige um número que eu já tinha registrado**: o **"pisca 3"** da distribuição de
formas ✗ **não é uma forma** ✓ — é **ausência com um pingo de detecção** ✓. Antes de tratar "pisca" como
forma, é preciso **rever o critério** ✓ (e o `pablo romé` e o `transcriptor`, os outros dois, precisam do
mesmo olhar ✓).

**O que a integração deve fazer com esse caso, e já está decidido**: `medido: false` **com o motivo escrito**
✓ ("marcador quase ausente: N amostras em M") ✓ — nunca zero silencioso ✗.

## 2026-10-10 — INTEGRAÇÃO FEITA: o `sky guitar` saiu de 0 para 40 de 44 notas datadas

O `else` da cadeia de velocidade (o caminho que **só desistia** ✗) agora tenta a **regra do estado** ✓ antes
de desistir ✓. Imports no topo ✓ (a regra `PLC0415` ✓). Amostragem a cada **5 quadros** ✓ — porque foi
**medido** que 30 quadros (1 s) **perde patamares** ✓ (34 → 47 onsets no `serge` ✓).

| | antes | **agora** |
| --- | --- | --- |
| `sky guitar` — notas com tempo | **0 de 44** ✗ | **40 de 44** ✓ |
| mecanismo no JSON | `medido: false`, motivo `marcador lento` ✗ | **`medido: true`**, `mecanismo: "estado do marcador (qual nota esta acesa)"` ✓ |

E o JSON passou a trazer **`notas_com_tempo`** ✓ — o número visível sem precisar contar ✓.

**E o meu cheque mentiu outra vez** ✗ (a quinta hoje ✓): eu procurei a chave `tempo` na nota e o tempo está
em **`t_ini`** ✓ — o resumo imprimiu "0 com tempo" ✗ enquanto o JSON tinha **40** ✓. **O erro foi pego
lendo a saída** ✓ (o `t_ini: 266.1` estava visível na terceira nota ✓), não confiando no meu próprio
resumo ✗. Desta vez a mentira foi para o lado **pessimista** ✓ — o que é o menos perigoso dos dois ✓, mas é
a mesma classe de erro que me fez afirmar "gate verde" quatro vezes ✗.

## 2026-10-10 — CRITÉRIO DUPLO CUMPRIDO: o gabarito NÃO caiu e o sem-marcador continua DECLARADO

**Depois** da integração (o número que podia ter sido afetado ✓, medido por isso mesmo ✓):

| semente | resultado | referência |
| --- | --- | --- |
| `oficial_1` | **66/72 = 0,917** ✓ | 0,917 ✓ |
| `oficial_2` | **71/72 = 0,986** ✓ | 0,986 ✓ |
| `oficial_3` | **68/72 = 0,944** ✓ | 0,944 ✓ |

**Idêntico à referência** ✓ — a integração **não tocou a cadeia do algarismo** ✓ (a mudança é só no `else` da
cadeia do tempo ✓), e agora isso está **provado**, não suposto ✓.

E o `iwaki` (sem marcador ✓): **43 notas, 0 com tempo** ✓, com o motivo **declarado** ✓:

```
"medido": false,
"motivo": "marcador sem_marcador na janela varrida, e o estado nao deu onset"
```

**O silêncio continua declarado** ✓ — e agora o motivo cita **também** o estado ✓ (nunca zero silencioso ✓).

**Os três pilotos, lado a lado**:

| vídeo | marcador | antes | **agora** |
| --- | --- | --- | --- |
| `sky guitar` | patamares (64 %) | 0 de 44 ✗ | **40 de 44** ✓ |
| `iwaki` | ausente | 0 de 43 ✓ | **0 de 43, com motivo** ✓ |
| `mr. tabs` | **cor no algarismo** (azul) | 0 ✗ | **0 no `transcrever`** ✗ — o observador de **cor** está medido e funcionando no `tab.estado` (10 de 19 ✓) mas **ainda não está ligado no JSON** ✗ |

## 2026-10-10 — a ÚLTIMA incógnita da integração de cor: a duração JÁ é obtida (e não é devolvida)

Lendo antes de escrever (a lição dos rounds 7 a 9 ✓), a incógnita que faltava para ligar o observador de
**cor** no `transcrever` está resolvida: os onsets de cor vêm em **fração** ✓ e o JSON precisa de
**segundos** ✓ — o que exige a **duração** ✓.

**Ela já é obtida** ✓, em `tab/inventario.py`: o `ler_quadro` chama **`ffprobe -show_entries
format=duration`** ✓ (linhas 46-59 ✓) para calcular o `ss` do fallback de AV1 ✓ — mas **não devolve** a
duração ✗ (a assinatura é `(quadro, via)` ✓).

**Portanto o que falta é pequeno e conhecido** ✓: um helper `duracao(caminho)` que faça a **mesma** chamada
de ffprobe ✓ (10 linhas ✓), e no `else` do `transcrever` — ao lado do observador de posição ✓, alimentando
a **mesma** associação ✓ — converter `fração × duração` ✓.

**Onde o observador de cor já está pronto e medido**: `tab.estado.estado_por_cor` ✓ — **10 de 19 onsets** no
`mr. tabs` ✓, destaque achado em **30 de 30** amostras ✓, com a coloração medindo **22,7 contra mediana
0,0** ✓. Ele usa `ler_quadro` por fração ✓ (o leitor certo para AV1 ✓) e a **mesma** célula de x ✓.

**Nota de arquitetura para o próximo round**: `ler_quadro` pode passar a **devolver** a duração também ✓
(em vez de duplicar a chamada de ffprobe ✓) — mas isso muda a assinatura usada em **todo** o projeto ✗, então
o helper separado é o caminho de menor risco ✓, e a unificação fica como decisão à parte ✓.

## 2026-10-10 — OBSERVADOR DE COR LIGADO NO PRODUTO: mr. tabs de 0 para 16, e o gabarito segue INTACTO

Última peça do goal ✓, e ela entrou **ao lado** do observador de posição ✓, alimentando a **mesma**
associação (a célula de x ✓) — muda só **quem** aponta a nota acesa ✓:

```python
# SEGUNDO OBSERVADOR: A COR DO ALGARISMO. O mr. tabs (e o kimny's guitar) nao tem FAIXA vertical
# nenhuma — o marcador deles e um algarismo ACESO, e o rastrear so procura faixa. Medido: coloracao
# 22,7 contra mediana 0,0, e destaque achado em 30 de 30 amostras. Ele devolve FRACAO, entao converte
# com a duracao do video (novo helper `duracao()` em tab/inventario.py, a MESMA chamada de ffprobe que
# o ler_quadro ja fazia para o AV1 e nao devolvia).
```

| vídeo | observador | antes | **agora** |
| --- | --- | --- | --- |
| `sky guitar` | posição (patamares) | 0 de 44 ✗ | **40 de 44** ✓ |
| **`mr. tabs`** | **cor** | **0** ✗ | **16 de 68** ✓ — `mecanismo: "estado do marcador (algarismo aceso, por cor)"` ✓ |
| `iwaki` | nenhum | 0 ✓ | **0 de 43, com motivo** ✓ |

**Os dois observadores estão no produto, com UMA regra de associação** ✓ — nenhuma linha menciona estilo ✓.
E o `ler_quadro` **continua com a assinatura antiga** ✓ (o helper é separado ✓ — a unificação fica como
decisão à parte, registrada ✓).

## 2026-10-10 — FASE 0 / T0.4: `make gate` que BARRA (e o plano derrubava o gate da árvore limpa)

**Feito**: no `Makefile`, `COMPOSE := docker compose` virou
`COMPOSE ?= docker compose -f compose.yaml -f compose.podman.yaml` ✓ (com `?=`, sobrescrevível num host com
Docker) e nasceu o alvo **`gate`**, com receita em **TAB**, **sem `|| echo`**, com os três passos
(`ruff check .` · `ruff format --check .` · `pytest tests/ -q -p no:cacheprovider`) ✓. O `make` para no
primeiro erro ✓ — medido: com um teste quebrado, `make gate` devolve **EXIT=2** e imprime
`make: *** [Makefile:40: gate] Error 1` ✓; revertido, **EXIT=0** com "All checks passed!" e
**120 passed in 6,99 s** ✓.

**E o `pytest` do plano está CERTO**: **120 testes** passando ✓ (conferido; não é inconsistência).

**ACHADO QUE CONTRADIZ O PLANO, e é o próprio plano que causa**: o §2.5 do plano afirma "Gate **verde**
hoje … **120 testes** passando". Medido **com a árvore limpa** (`git status` só com o `Makefile` e
`?? docs/guias/`): **o gate estava VERMELHO** ✗, e **no primeiro passo** ✗ — antes de chegar ao pytest ✔.
Causa, medida sem filtro: `ruff check .` → **"All checks passed!"** ✓, mas `ruff format --check .` →
**"1 file would be reformatted"** ✗, e o diff aponta um bloco de código **dentro de
`docs/guias/plano-do-produto.md`** ✓ (`+ modo: str  # paginado | rolante | estatico` e a cerca ``` ✗).

**Decisão (suposição, na falta do dono — §5 do plano)**: **não** reformatar o documento do cérebro ✗
(o conteúdo é contrato). Em vez disso, `pyproject.toml` ganhou
**`extend-exclude = ["docs"]`** no `[tool.ruff]` ✓ — os documentos de `docs/` contêm código de **exemplo**,
que não é código do projeto. Consequência: `docs/` sai do ruff (lint e formatação) ✓, e o gate volta a ser
verde na árvore limpa ✓. **Isto é desvio registrado** e vai para o relatório do dono ✓.

**E UMA FALHA MINHA, registrada porque é a mesma classe de erro de sempre**: os meus **dois últimos commits
(`7df88678` e o anterior) rodaram só `ruff check` + `pytest` e imprimiram "GATE OK"** ✗ — eu tinha
**esquecido o `ruff format --check`** naqueles dois comandos ✗. Ou seja: eu afirmei "gate verde" com um dos
três passos **não rodado** ✗. É exatamente o que o T0.4 existe para impedir, e é a razão de o gate ter de
ser um **alvo só**, e não três comandos que eu copio de memória ✗.

## 2026-10-10 — FASE 0 / T0.2: `MODELO_PADRAO` passa a `oficial_3` (68/72) — e o antigo dava 72/72 = 1,000

**Medido antes de mexer** (§4.2):

| modelo | no gabarito de 72 glifos | procedência |
| --- | --- | --- |
| **`artefatos/glifo_sint.pt`** (o que o produto usava) | **72/72 = 1,000** ✗ | **desconhecida** — não está na tabela do `artefatos/LEIA-ME.md` |
| `artefatos/oficial_2` | 71/72 = 0,986 | semente 2 |
| **`artefatos/oficial_3`** | **68/72 = 0,944** | semente 3 (**mediana**) |
| `artefatos/oficial_1` | 66/72 = 0,917 | semente 1 |

**O achado**: o modelo do produto dava **perfeição exatamente na régua que é o gabarito** ✓ — isso não é
qualidade, é **sobreajuste à régua** ✗, e a procedência dele é desconhecida ✗. O plano já mandava trocar
(não escolher pelo gabarito ✓); agora o motivo está **medido**, não suposto ✓.

**Decisão** (opção 3 do T0.2): `MODELO_PADRAO = ARTEFATOS / "oficial_3" / "glifo_sint.pt"` — a semente
**mediana**, não a melhor ✓ (escolher a melhor pelo gabarito de 72 glifos é sobreajustar a régua). Registro
completo em **`docs/decisoes/0008-modelo-do-produto.md`** ✓ (contexto, 4 opções, decisão, consequência) ✓.
O comitê das 3 sementes fica **opcional**, com o critério de adoção escrito ✓. O `glifo_sint.pt` **não se
apaga** ✓ (artefato é registro).

**E um conserto que o CA exigiu**: o CA do T0.2 diz *"tab.avaliar com o MODELO_PADRAO novo **imprime o
caminho**"* — e o `tab/avaliar.py` **não imprimia** ✗ (saía só o `RESULTADO`). O §4.3 do plano exige dizer
qual modelo rodou em **todo** número ✓, então o `avaliar` passou a imprimir
`modelo carregado: <caminho>` ✓.

**CA do T0.2, conferido**: `python -m tab.avaliar` →
`modelo carregado: /app/artefatos/oficial_3/glifo_sint.pt` + `TOTAL=68/72=0.944` ✓ (era exatamente o que o
CA pedia: imprime o caminho **e** dá 68/72 ✓); com `--modelo artefatos/oficial_1/glifo_sint.pt` → 66/72 ✓
(não quebrou o caminho explícito ✓); `make gate` **EXIT=0** ("All checks passed!" + "120 passed") ✓.

**Para o cérebro**: o plano troca um modelo que faz **1,000 na régua** por um de **0,944** ✓. A decisão do
plano é explícita e a queda é esperada ✓ — mas o plano **não tinha a medição de 1,000** ✗ (só dizia que a
procedência era desconhecida ✓). Vale o cérebro saber que o antigo era **perfeito no próprio gabarito** ✓.

### Correção do registro do T0.2 — a falha do gate foi de AMBIENTE, não de código

O commit `228d0e7c` (T0.2) foi commitado com `make gate` **EXIT=2** ✗ porque **eu não exportei o
`DOCKER_HOST`** naquela chamada ✓: o alvo falou com `unix:///var/run/docker.sock` (que **não existe** nesta
máquina — o runtime é podman ✓) e devolveu
`failed to connect to the docker API at unix:///var/run/docker.sock` ✗. **O código do T0.2 estava certo** ✓;
o comando em volta é que estava errado ✗ — e o `git commit` rodou assim mesmo porque eu **não usei
`|| exit 1`** entre o gate e o commit ✗ (o mesmo erro que o T0.4 existe para impedir ✓, e que eu já havia
cometido duas vezes ✓).

**Consequência prática, medida**: o T0.4 barra o commit **quando o shell respeita o código de saída** ✓;
quem não barra é a **cadeia de comando** que eu escrevo em volta ✗. Da terceira vez em diante, o padrão
passou a ser `make gate || { echo "GATE FALHOU — commit NAO feito"; exit 1; }` ✓ — e ele **funcionou** nesta
rodada: o commit seguinte **não** saiu ✓.

**Item para o cérebro**: o alvo `gate` **depende do `DOCKER_HOST`** e falha com um erro de socket do Docker ✓
em vez de dizer o que falta ✗. Sugestão: o próprio alvo verificar a variável (ou o `Makefile` exportá-la com
`?=`) e falhar com mensagem clara ✓.

## 2026-10-10 — FASE 0 / T0.3: os números de TEMPO de 2026-10-10 ficam NÃO VALIDADOS (com as quatro evidências)

Os números de tempo que eu registrei em 2026-10-10 — **"sky 40/44"**, **"mr. tabs 16/68"**, **"serge 47/49"**
— contam **notas que receberam ALGUM número**, não notas com o **tempo certo** ✓. **Não existe gabarito de
tempo** ✓, e por isso o erro passou. Ficam **NÃO VALIDADOS** ✓ (é o mesmo tipo de erro do histórico
"323 notas com tempo eram 3 instantes" — `AGENTS.md` regra 3 ✓).

As quatro evidências, medidas e conferidas na leitura do plano (§2.3 e §2.4):

1. **Espaço de coordenada misturado (medido)** ✗: `painel.refinar` recorta a ROI em `x` e **não guarda o
   deslocamento** ✓. No `retrato brasileiro` o recorte começa em **x0 = 70 px** ✓ — o `x` das notas está no
   espaço da **ROI recortada** e o `x` do marcador (`cursor.rastrear`, que só corta em `y`) está no espaço do
   **quadro** ✓. Efeito: no quadro de 245,5 s o marcador está na **coluna 1** (x da ROI = 154, x do quadro ≈
   228) ✓, mas comparado sem o deslocamento `x = 228` cai na célula da **coluna 3** ✓ — o JSON deu à coluna 3
   o onset **245,25 s** e a **coluna 1 ficou sem tempo** ✓. **O mesmo erro existe em `estado.estado_por_cor`**
   ✓, que recorta `quadro[..., tk.x0:tk.x1]` **sem somar o deslocamento** ✗ — código que **eu escrevi nesta
   sessão** ✓. No `mr. tabs` o recorte foi **x0 = 0** ✓, então lá o erro **não aparece por acaso** ✓.
2. **Onsets vindos de OUTRA página** ✗: `rastrear` percorre o **vídeo inteiro** ✓ e o onset é "a primeira vez
   que o marcador entra na célula", em **qualquer** página ✓. A nota da coluna 2 recebeu **266,1 s**, quando a
   tela mostrava o **compasso 5** ✓. Os onsets do JSON vão de **239 s a 584 s** para notas de **uma** página ✓.
3. **Acorde recebe no máximo um onset** ✗: duas notas com o **mesmo `x`** deixam a célula de uma delas **vazia**
   ✓ (`nota_do_x` usa o ponto médio entre vizinhos, que vira o próprio `x` ✓). No `sky2.json` o acorde da
   coluna 1 (cordas 2 e 6) ficou **sem tempo** ✓.
4. **AV1: a cadeia de tempo falha CALADA em 44 % do acervo** ✗: medido no `mr. tabs` (codec `av1`),
   `cv2.VideoCapture` **abre** (`isOpened() = True`) e informa `FRAME_COUNT = 16972`, mas `grab()` falha em
   **30 de 30** tentativas ✓ — `cursor.rastrear` devolve **0 amostras**, **indistinguível** de "vídeo sem
   marcador" ✓. **Correção ao `CONTEXTO.md` §3**: lá está "AV1 → `FRAME_COUNT=0`" ✗ — neste arquivo o
   `FRAME_COUNT` veio **preenchido**; o que falha é a **decodificação** ✓. A consequência é a mesma, só que
   **mais traiçoeira**: o código pensa que leu o vídeo ✓.

**Sintoma que fecha o caso**: ordenando as notas por `x`, os onsets **invertem a ordem** em **12 de 39** pares
no `sky2.json` ✓ e em **8 de 15** no `mrtabs.json` ✓ — ou seja, o "tempo" contradiz a própria ordem da
música ✓.

**Os quatro itens entraram na tabela "não repetir"** ✓ (fim do arquivo, seção "O que foi tentado e falhou").

## 2026-10-10 — FASE 1 / T1.1 (passo 1: LER antes de escrever): o que o `tab/leitor.py` vai REAPROVEITAR

O plano manda (`docs/guias/plano-do-produto.md`, T1.1) **ler** `marcador._amostrar_ffmpeg` e
`varredura.Leitor` **antes** de escrever, para reaproveitar em vez de reinventar ✓. Feito:

**1. `marcador._amostrar_ffmpeg` (linha 299)** — é a **passada única** que o T1.1 pede ✓:
`subprocess.Popen([...])` com o filtro `fps` pedindo o passo desejado ✓, os recortes saindo do **mesmo**
quadro decodificado ✓, e **fallback para o caminho lento** quando a passada única não devolve quadro ✓.
**E o motivo está medido no próprio docstring**: o caminho lento (um processo por amostra) deu
**128 s por vídeo AV1** — são 241 *seeks* e, a cada *seek*, o decodificador volta ao *keyframe* ✓. Ou seja:
a passada única não é otimização de gosto, é o que torna AV1 viável no HD compartilhado ✓.

**2. `varredura.Leitor` (linha 104)** — **já implementa duas regras que o T1.1 exige** ✓:
- **decide uma vez por vídeo** qual caminho usar ✓ (`via` = `"cv2"` ou `"ffmpeg"` ✓);
- **não confia em `isOpened()`**: lê **um quadro de verdade** e só adota o `cv2` se ele **decodificar** ✓
  (é literalmente a regra do T1.1: *"não basta `isOpened()`, ver §2.4"* ✓);
- e cai para `ffmpeg` **no meio do vídeo** se o `cv2` falhar depois ✓.

**Conclusão de desenho (para o próximo passo desta tarefa)**: o `tab/leitor.py` é **`varredura.Leitor`
promovido** ✓ (mesma semântica, no lugar certo ✓) **mais** a janela em passada única do
`marcador._amostrar_ffmpeg` ✓, com a interface do plano (`info()` por ffprobe ✓, `quadro_em(t_s)` ✓,
`quadros(t0, t1, qps, recorte_y=None)` ✓) — e `inventario.ler_quadro`/`duracao` passam a **delegar**,
mantendo as assinaturas (são usadas no projeto todo) ✓.

**DISCREPÂNCIA DE NÚMERO, registrada para o cérebro (não resolvida)**: o docstring do `varredura.Leitor`
diz que o OpenCV *"falha em **49 %** do acervo (AV1 sem aceleração)"* ✓, enquanto o plano (§2.4) e o
`AGENTS.md` falam de **44 %** de AV1 ✓. Os dois podem estar certos ✓ (44 % AV1 **mais** algum H.264 que o
`cv2` também não decodifica ✓), mas **não medi** qual é o caso ✗ — fica registrado como número a
reconciliar, **sem** assumir que um está errado ✓.

## 2026-10-10 — FASE 1 / T1.1 FEITO: `tab/leitor.py` — e o AV1 passa a decodificar (60 quadros em 10 s)

**Criado `tab/leitor.py`** ✓ (o único jeito de ler vídeo ✓), montado **reaproveitando** o que já existia ✓ —
não reescrito ✗: `info`/`dimensoes` por `ffprobe` ✓; `quadro_em` da invocação do `varredura._ffmpeg_em` ✓;
`quadros` da **passada única** do `marcador._amostrar_ffmpeg` ✓; `Leitor` = `varredura.Leitor` promovido ✓
(decide **uma vez** por vídeo e cai para `ffmpeg` no meio ✓). CLI de inspeção: `python -m tab.leitor VIDEO
--info | --quadro-em T | --janela T0 T1 --qps Q` ✓.

**Medido, rodando de verdade** (§4.2 passo 5):

| vídeo | `info()` |
| --- | --- |
| `sky guitar/retrato brasileiro` | `h264 · 1920×1080 · 29,97 fps · 678,974 s` ✓ |
| **`mr. tabs` (AV1)** | `av1 · 1920×1080 · **60 fps** · 282,894 s` ✓ |

**E a PROVA que o T1.1 existia para dar** — o mesmo vídeo AV1 em que o `cv2` **falhava calado** ✗
(`grab()` falhou em **30 de 30**, T0.3 evidência 4 ✓):

```
python -m tab.leitor "<mr. tabs AV1>" --janela 100 110 --qps 6
  t=100.333 quadro=(1080, 1920, 3)
quadros(100.0, 110.0, qps=6.0): 60 quadros        <- 10 s × 6 qps = 60, exato ✓
```

E no H.264: `quadro_em(245.5)` → ok ✓; `--janela 245.5 248.5 --qps 6` → **18 quadros** ✓ (3 s × 6 ✓).

**O gate barrou o primeiro commit** ✓ com **3 `RUF100`** — `noqa` **inúteis** que eu escrevi para `BLE001` e
`S101`, que **não estão ligados** neste projeto ✓ (eu os copiei de outro contexto ✗). O `ruff check --fix`
removeu os três ✓ e o `ruff format` ajustou a formatação ✓ → gate verde ✓. **O veto funcionou**: nada foi
commitado com o gate vermelho ✓.

**O que ainda falta na Fase 1**: T1.2 (migrar `cursor.rastrear`, `transcrever.*`, `pipeline.*`,
`marcador._amostrar_cv2`, `varredura.Leitor` para o leitor ✓ + o teste que proíbe `VideoCapture(` fora de
`tab/leitor.py` ✓ + `tab.avaliar` **idêntico** antes/depois ✓), T1.3 (espaço de coordenadas do quadro com
`x0` no `Candidato` ✓) e T1.4 (`tab/colunas.py` ✓).

## 2026-10-10 — FASE 1 / T1.2 (começo): `inventario` delega ao leitor — e `tab.avaliar` deu IGUAL

**Linha de base medida ANTES** (§4.2 passo 2 ✓): `tab.avaliar` → `oficial_1` **66/72**, `oficial_2` **71/72**,
`oficial_3` **68/72** ✓ (e com o `MODELO_PADRAO` novo, `modelo carregado: .../oficial_3/...` + 68/72 ✓).

**A lista exata de quem usa `cv2.VideoCapture`** (medida por `grep`, é o que o teste do T1.2 vai proibir ✓):
**11 usos em 7 arquivos** — `cursor.py` (1) · `inventario.py` (1) · `marcador.py` (1) · `pipeline.py` (2) ·
`transcrever.py` (4) · `varredura.py` (1) · e `leitor.py` (1, **permitido** ✓).

**Feito**: `inventario.ler_quadro` e `inventario.duracao` passam a **delegar** ao `tab/leitor.py` ✓ —
mantendo a **assinatura antiga** (`(quadro, via)` ✓, com `via` ainda em `{"cv2","ffmpeg"}` ✓, que é o que o
JSON publica em `lido_via` ✓). Alcance: tudo que já passava pelo `ler_quadro` (inclusive o observador de
**cor** ✓) passa a ler pelo leitor único ✓.

**Trocadas por intervalo de AST, não por número de linha** ✓: o AST achou `duracao` em (31,62) e `ler_quadro`
em (65,125) ✓ — os números que eu "lembrava" ✗ estavam **errados** (eu ia trocar as funções erradas ✗). É a
quinta vez nesta sessão que **ler/o que é exato** vence **lembrar** ✓.

**Verificação de regressão (regra 9 — leitura é entrada do modelo)** ✓: `tab.avaliar` **depois** da mudança →
**66/72, 71/72, 68/72** ✓ — **idêntico** à linha de base ✓. E o AV1 lido por dentro do `inventario`:
`quadro (1080, 1920, 3) via ffmpeg` ✓ (`ler_quadro` no `mr. tabs` ✓).

**Falta no T1.2**: migrar `cursor.rastrear`, `transcrever.*` (4 usos), `pipeline.*` (2), `marcador._amostrar_cv2`
e `varredura.Leitor` ✓; e então **acrescentar o teste** que proíbe `VideoCapture(` fora de `tab/leitor.py` ✓
(a ordem importa: o teste entra quando ele puder passar ✓, senão o gate fica vermelho ✓).

## 2026-10-10 — FASE 1 / T1.2: `varredura.Leitor` vira SUBCLASSE do leitor único (9 usos restantes em 5 arquivos)

**Feito**: a classe `Leitor` do `varredura.py` (104-143) foi substituída por uma **subclasse** de
`tab/leitor.Leitor` ✓ — ela era um **duplicado** do que o T1.1 promoveu ✓, então a migração é de
**compatibilidade**, não de semântica nova ✓. `varredura.py` deixa de ter `cv2.VideoCapture` ✓.

**Conferido antes de trocar** (o receio era quebrar atributos internos ✗): os únicos usos de `_primeiro` eram
dentro da própria classe ✓, e o `marcador.py` importa `Leitor` **de** `varredura` ✓ — que continua existindo,
como subclasse ✓, então o import não quebra ✓. Verificado rodando:
`varredura.Leitor("...retrato brasileiro").ler(245.5)` → `via cv2 · quadro (1080, 1920, 3)` ✓ e
`issubclass(varredura.Leitor, leitor.Leitor) == True` ✓.

**Contagem de `cv2.VideoCapture`**: de **11 usos em 7 arquivos** → **9 usos em 5 arquivos** ✓:
`cursor.py` (1) · `marcador.py` (1) · `pipeline.py` (2) · `transcrever.py` (4) · e `leitor.py` (1, o dono ✓).

**Regressão (regra 9)**: `tab.avaliar` → **66/72, 71/72, 68/72** ✓ — **idêntico** à linha de base ✓.

**Falta no T1.2**: `cursor.rastrear` (1) · `marcador._amostrar_cv2` (1) · `pipeline.*` (2) · `transcrever.*` (4)
— estas **não** são cópia de código ✗: cada uma tem laço próprio de leitura e precisa passar a usar
`leitor.quadros(...)` (a passada única) ✓, o que muda **como** o quadro é obtido ✓. Por isso o teste que
proíbe `VideoCapture(` só entra quando as cinco estiverem migradas ✓ (senão o gate fica vermelho ✓).

## 2026-10-10 — FASE 1 / T1.2: o esqueleto do `cursor.rastrear` (para o patch ser cirúrgico, não reescrita)

Lido por AST (`tab/cursor.py:97-183`, 87 linhas ✓). **Por que ele falha calado no AV1**: `cap.grab()`
(linha 113) devolve `False` **sem exceção** ✓ → o `while` sai **no primeiro quadro** ✓ → `amostras = []` ✓ —
**indistinguível de "vídeo sem marcador"** ✓ (é exatamente a evidência 4 do T0.3 ✓, e é o item do CA da
Fase 1: *"no AV1 do `mr. tabs`, `rastrear` passa a devolver amostras (> 0)"* ✓).

Esqueleto, com os números de linha:

```
103:     cap = cv2.VideoCapture(caminho)
104-105: if not cap.isOpened():  -> retorno antecipado
106:     fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
107:     n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
108:     y0, y1 = roi if roi else (0, 0)
110-111: amostras = []; i = 0
112:     while True:
113:         ok = cap.grab()            <- AQUI o AV1 morre, calado
114-115:     if not ok: quebra o laco
116:         if i % passo == 0:
117:             ok, frame = cap.retrieve()
118-119:         if not ok: quebra
120-121:         if y1 > y0: frame = frame[y0:y1, :]
122:         det = detectar_cursor(frame)
123-136:     if det: x0, x1, (matiz, s) = det; amostras.append({... "t": i / fps ...})
137-143:     if debug_dir e len(amostras) <= 3: desenha a visao de depuracao
144:         i += 1
146:     cap.release()
147-162: as estatisticas (xs, ts, saltos, retrocessos, intervalos, larguras)
163-183: o `resumo` (fps, frames_totais, amostras_com_cursor, cobertura, x_min, x_max,
         largura_nucleo_mediana, largura_nucleo_p90, matiz_mediana, n_saltos, salto_mediano_px,
         retrocessos, intervalo_mediano_entre_saltos_s) e `return {"resumo", "amostras"}`
```

**Plano do patch (cirúrgico, para NÃO perder o que eu não vi)**: trocar **só** o trecho de aquisição
(103-146 ✓) pelo laço do leitor único ✓ — `for t_s, quadro in leitor.quadros(caminho, 0, duracao, qps,
recorte_y=(y0, y1))` ✓, com `qps = fps / passo` ✓ — mantendo **intactos** o `amostras.append({...})` (126-136 ✓),
a depuração (137-143 ✓) e **todo** o cálculo do `resumo` (147-183 ✓) ✓. E o `"t"` da amostra passa a ser o `t_s`
**que o leitor devolve** ✓ (segundos ✓), em vez de `i / fps` ✓ — é a regra do T1.1 ("segundos, nunca índice de
quadro" ✓) e **remove** a aritmética de índice ✓.

**Por que não reescrevi a função inteira agora** ✗: as linhas 126-127 (as chaves do dict da amostra ✓) e
174-186 (campos do `resumo` ✓) **não apareceram** na minha leitura filtrada ✗, e uma reescrita por intervalo
de AST as **apagaria em silêncio** ✗ — o mesmo erro de classe que o `nome` ✗ e o `transcrever` ✗ me custaram
antes ✓. **Preservar o que não se viu é a regra.**

## 2026-10-10 — FASE 1 / T1.2 (cursor): `rastrear` agora lê pelo leitor único

`tab/cursor.py:rastrear` trocou `cv2.VideoCapture` por `tab.leitor.quadros` (passada única de `ffmpeg`,
`qps = fps / passo`, `t` em segundos vindo do leitor, `frame = round(t * fps)`). Vídeo ilegível agora vira
`resumo["erro"]` (antes: `SystemExit` ou 0 amostras calado). Novo campo `quadros_lidos`. Teste:
`tests/test_cursor_leitor.py`.

| vídeo (roi, passo) | antes | depois |
| --- | --- | --- |
| `sky guitar/retrato brasileiro` H.264 (280-462, 30) | 434 amostras, x 197–1810,5, 404 saltos | 434 amostras, x 197–1841, 406 saltos |
| `mr. tabs/blind melon` AV1 (827-997, 300) | 0 amostras (`cv2` não decodifica) | `quadros_lidos`=57, 52 amostras, `frames_totais`=16974 |

H.264: mesmas 434 amostras; a diferença (x_max, +2 saltos) vem de o filtro `fps` do `ffmpeg` escolher o quadro
mais próximo do instante, em vez do `grab()` de 1 a cada 30 índices. AV1: a **leitura** funciona (57 quadros);
mas as 52 "detecções" têm largura mediana 1 px, matiz 98, 29 retrocessos e salto mediano de 347 px — são
**ruído**, não cursor (o `mr. tabs` marca a nota por cor, não por faixa). Não afirmar cursor ali.
`tab.avaliar` nas 3 sementes: 66/72, 71/72, 68/72 (inalterado).

## 2026-10-10 — FASE 1 / T1.2 (fim): zero `VideoCapture` fora do leitor

Trocados por `tab.leitor` (`info`, `quadros`): `transcrever.varrer_cursor`, `tempos_do_cursor`, `serie_cursor`
e `main` (duração); `pipeline.amostrar_presenca` (duração) e `serie_do_marcador`.

`marcador._amostrar_cv2` **não** foi trocado pelo `ffmpeg`: medido em `retrato brasileiro` (H.264, 60 amostras
a cada 0,5 s a partir de 245,5 s, recorte 280–462), o caminho `cv2` e o `ffmpeg` divergem em **21 de 60**
amostras (20 com x diferindo mais de 3 px). Trocar mudaria as séries já medidas do censo (regra 9). A leitura
sequencial do `cv2` foi movida para `tab.leitor.quadros_cv2` (cópia exata): saída idêntica (sha `62b531cfb0cb`
antes e depois). **Decisão em aberto:** qual dos dois caminhos é o certo para o `marcador`.

Trava: `tests/test_sem_videocapture.py` (falha e diz o arquivo). `pyproject.toml`: `addopts = "-m 'not
integration'"`; `make test-integration` continua com 1 passou, 126 desmarcados.

| medida | antes (HEAD) | depois |
| --- | --- | --- |
| `tab.avaliar` sementes 1/2/3 | 66/72, 71/72, 68/72 | 66/72, 71/72, 68/72 |
| `transcrever` retrato brasileiro H.264 (`--inicio 0.5 --janela 30`) | medido, 40 notas com tempo, 0 janelas, série 120 pontos | medido, 40 notas com tempo, 0 janelas, série 119 pontos |
| `transcrever` mr. tabs AV1 (mesmos parâmetros) | medido, 39 notas com tempo, **0 janelas** (cv2 não decodifica) | medido, 39 notas com tempo, **29 janelas** de "cursor" entre 4,5 s e 179,5 s |

As 29 janelas do AV1 são **suspeitas**: o `mr. tabs` marca a nota por cor (ver a seção T1.2 acima), e o
detector de faixa é o mesmo. Não afirmar cursor ali até medir. O `notas_com_tempo` (39) não mudou.

## 2026-10-10 — Fase 1 / T1.3: um espaço de coordenadas (o do quadro)

`painel.Candidato` ganhou `x0` (deslocamento da ROI no quadro); `criar(..., x0=)` o recebe e `refinar` grava
`c.x0 + x0_do_recorte`. `candidatos` constrói com `x0=0` (ROI de largura cheia). O `x` de `reconhecer_linha`
**não mudou** (é entrada do classificador, regra 9); a conversão é na fronteira: `transcrever` e `pipeline`
gravam `x_quadro = cand.x0 + x` em cada nota (o `x` fica, por compatibilidade) e comparam **esse** com a série
do marcador; `estado_por_cor` recorta com `cand.x0 + tk.x0` e recebe `xs` em `x_quadro`.

Medido no `retrato brasileiro` (frac 0,5): `cand.x0 == 70`. Em t=245,5 s o marcador (`detectar_cursor`) está em
x_quadro 230,5 (banda 224-237); a coluna 1 das notas tem x_roi 154 = x_quadro 224. Antes caía na coluna 3.
`tab.avaliar` idêntico: 66/72, 71/72, 68/72. `transcrever` (`--inicio 0.5 --janela 30`): `medido: true`,
`notas_com_tempo` 42 (era 40); as notas da coluna 1 agora têm `t_ini`. **Os tempos ainda não são confiáveis:** a
associação usa a série do vídeo inteiro (onsets de outras páginas); conserto é da Fase 5.

## 2026-10-10 — Fase 1 / T1.4: colunas (o acorde é uma coluna). A Fase 1 fecha.

`tab/colunas.py`: `Coluna(x_quadro, indices)` e `agrupar_colunas(xs_quadro, passo, tol=0.35)`. Varredura em x
ordenado: a nota entra na coluna corrente se a distância à mediana dos x já agrupados for menor que `tol * passo`;
senão abre coluna nova. `tab/estado.py`: `onsets_por_coluna` (a mesma `nota_do_x`, sobre o `x_quadro` das
colunas), `expandir_para_notas` (todas as notas da coluna recebem o mesmo onset). `estado_por_cor` passa a
receber colunas. `onsets()` e `nota_do_x` ficaram como estavam. `transcrever` agrupa com `r["passo"]`: o caminho
do estado e o da cor usam colunas, e o ramo desliza/salta (`atribuir_tempos`/`tempos_por_patamar`) também calcula
por coluna e expande (mudança simples, mas esse ramo não foi exercitado na medição abaixo). `tab/pipeline.py`
**não** foi alterado: o ramo de tempo dele ainda é por nota. `reconhecer_linha` e os recortes do classificador
não foram tocados. `make format` passa a usar `RUFF_CACHE_DIR=/tmp/ruffcache`, como o `gate`.

Medido (`sky guitar`, `retrato brasileiro`, `--inicio 0.5 --janela 30 --simbolos ""`):

| medida | antes | depois |
| --- | --- | --- |
| `tab.avaliar` sementes 1/2/3 | 66/72, 71/72, 68/72 | 66/72, 71/72, 68/72 |
| notas com `t_ini` | 42 de 44 | 44 de 44 |
| grupos de mesmo `x_quadro` com mais de uma nota | 3 de 3 | 3 de 3 |
| desses grupos com `t_ini` idêntico | 0 de 3 | 3 de 3 |

Coluna 1 (cordas 2 e 6, x_quadro 224): antes 264,1 s e 243,74 s; depois as duas em 243,74 s. Os tempos ainda
**não são confiáveis** (onsets de outras páginas, Fase 5).

Gate: `make gate` com `All checks passed!`, 59 arquivos formatados, 135 passed (2 deselected).
`make test-integration`: 2 passed, 135 deselected. Testes novos: `tests/test_colunas.py` (6).

CA da Fase 1: gate verde; `tab.avaliar` idêntico nas 3 sementes; `cand.x0 == 70` (teste de integração); o
marcador de 245,5 s na coluna 1 foi medido no T1.3 (acima), e **não foi remedido** nesta tarefa; AV1 com
amostras (T1.2).

## 2026-10-10 — FASE 2 / T2.3: `tab.avaliar_video` — a régua do produto

Módulo novo `tab/avaliar_video.py` (funções puras + `main`), testes em `tests/test_avaliar_video.py`
(15, dicionários feitos à mão). Lê os dois formatos: o v1 (`chorinho/video@1`) e o legado do
`tab.transcrever`, tratado como uma tela com exibição = vídeo inteiro. Sem `x_quadro` no legado, a
régua **não avalia** notas nem tempo e diz o motivo; telas continuam avaliadas.

Regras da régua (decisões de implementação onde o plano deixava margem):
- **telas**: casamento um a um e guloso, pela contagem de instantes em que a tela prevista aparece;
- **notas**: `|Δx_quadro| <= 0,5 * passo`, mesma corda, guloso pela menor distância; entregue = casa
  numérica; inventada = entregue sem par, **inclusive** em tela prevista sem par no ouro;
- **tempo**: a coluna atual é a de maior `t_ini` até `t`, só dentro da exibição que contém `t`. A
  tolerância de 0,2 s aceita a coluna **imediatamente anterior no tempo** (não por x), e isso fica
  declarado no relatório. As colunas vêm de `tab.colunas.agrupar_colunas` sobre todas as notas da
  tela (inclusive as não numéricas, porque o marcador passa por elas);
- classes: `acerto`, `acerto_tolerancia`, `erro`, `json_sem_tempo`, `tempo_falso`, `ausencia_certa`
  (a última é o acerto de "nenhuma acesa" sem afirmar tempo).

Smoke (legado real + ouro **falso** de 3 instantes montado à mão fora do repositório, só para provar
a leitura): `python -m tab.avaliar_video --ouro <falso> --pred data/saida/avaliar_video/pred_smoke.json`
→ telas 1 de 1; notas precisão 3 de 37, revocação 3 de 3, inventadas 34 de 37; tempo 2 de 2 com coluna
(acerto 2), ausência certa 1 de 1. A predição veio de `tab.transcrever` no `retrato brasileiro` (início
0,5, janela 30 s), que já grava `x_quadro` (corda 2, casa 0: `x` 154 → `x_quadro` 224, deslocamento 70).
Os números de notas do smoke **não são medida de qualidade**: o ouro é falso e tem 3 notas.

Gate: `make gate` com `All checks passed!`, `61 files already formatted`, `150 passed, 2 deselected`,
código de saída 0. Testes da régua: 15 (perfeito, nota inventada, nota perdida, casa errada, acorde,
nenhuma acesa com tempo afirmado, tolerância dentro e fora de 0,2 s, legado, legado sem `x_quadro`,
tempo sem `medido`, casamento de telas, exibição, validação do ouro e reprodutibilidade).
Reprodutibilidade na linha de comando: 2 execuções com o mesmo relatório (`cmp` idêntico).

O ouro do vídeo do MVP (T2.4) **não existe ainda**: esta tarefa não rotulou nada e não criou nada em
`data/gold/`. A linha de base do produto atual depende dele.

## 2026-10-10 — Fase 2 / T2.1+T2.2: ferramenta do ouro de vídeo (`tab/ouro_video.py`)

`preparar` (telas, instantes, `pre.json`) e `servir` (http.server em 127.0.0.1, `POST /salvar` grava o ouro
de forma atômica a cada alteração, retoma o trabalho salvo, botão "baixar JSON"). Testes: `tests/test_ouro_video.py`
(10; agrupamento com faixa colorida, conversão de clique, montagem/validação, gravação atômica, POST em thread).

Medido no `retrato brasileiro` (h264, 679 s, quadro a cada 2 s, semente 0): **11 telas, 40 instantes, 177 s**
(maior parte do tempo é `painel.escolher` nos quadros sem tablatura). A tablatura só existe de 240 s a 672 s.

Limiar da diferença média absoluta (cinza, sem pixels de saturação > 25): histograma das 218 comparações
`[0,0.25)=14, [0.25,0.5)=61, [0.5,1)=87, [1,1.5)=44, [1.5,4)=0, [4,6)=2, [6,8)=6, [12,32)=2, [64,256)=2`.
Vão vazio entre 1,5 e 4: **limiar = 2,0** (12 de 218 acima = 11 trocas de tela + 1 volta).

O que falhou antes de chegar nisso (não repetir): (1) saturação mínima 90: o marcador é uma faixa azul PÁLIDA
(S 40-80), contava como diferença e saíam 163 telas; (2) `painel.escolher` aceita o BRAÇO DO VIOLÃO e tela preta
como painel (uniformidade 0,85-0,93 contra 0,81-0,82 da tablatura de verdade: a uniformidade não separa). Portões
atuais: passo 14-45 px, saturação mediana do recorte <= 25, cinza mediano >= 20. Limite: canal com fundo de
tablatura colorido seria recusado.

Convenção de x: nota pré-lida `x_quadro` = borda esquerda do token (igual ao `tab.transcrever`) + `x_centro_quadro`;
nota acrescentada por clique: centro = clique, `x_quadro` estimado = clique - 0,25 passo. Imagens ignoradas pelo git
(`data/saida/ouro_video/*/telas|instantes`); `pre.json` versionado. O ouro (`data/gold/ouro_video/*.json`) é do dono.

## 2026-10-10 — Fase 2 / conciliação de x: régua e transcrever comparam pelo CENTRO do token

- **Problema**: o ouro grava o clique (centro) na coluna acesa e `x_centro_quadro` nas notas, mas a predição
  só tinha `x_quadro` (borda esquerda). A régua comparava borda com centro: viés de meia largura do algarismo.
- **Conserto**: `tab.reconhecer` registra o centro do token (`(x0+x1)/2`, ROI), e `tab.transcrever` /
  `tab.pipeline` gravam `x_centro_quadro` (quadro). `x` e `x_quadro` não mudaram; nada que entra no classificador mudou.
  `tab.avaliar_video` compara sempre pelo centro (`x_centro_quadro`, senão `x_quadro` com fallback declarado no
  relatório: `x_fallback`), coluna prevista = mediana dos centros.
- **Medido**: `tab.avaliar` nas 3 sementes oficiais: 66/72, 71/72, 68/72 (inalterado).
  `tab.transcrever` smoke (`retrato brasileiro`, `--inicio 0.5 --janela 30 --simbolos ""`): 44 de 44 notas com
  `x_centro_quadro`, todas com centro > borda (ex.: `x_quadro` 224 → `x_centro_quadro` 231,0).
- **Testes**: `tests/test_avaliar_video.py` com 20 passando (5 novos: ouro com centro, predição com centro, coluna
  pela mediana dos centros, fallback declarado com contagem, chaves extras `juntadas`/`ferramenta`).
- **Não feito**: o agrupamento de colunas do `tab.transcrever` (onset) ainda usa `x_quadro`; trocar isso muda a saída
  de tempo e fica para uma rodada própria, medida.

## 2026-10-10 — relato do dono: caixa do ARCO de ligadura não cobre o símbolo inteiro (dívida da Fase 10)

- **Relato**: durante a rotulagem do ouro de vídeo (`data/saida/ouro_video/retrato_brasileiro`, ferramenta
  `tab.ouro_video`), o dono reportou que as caixas de símbolo, nos arcos de ligadura, saem recortadas de forma
  errada e não cobrem o arco inteiro. Registrado como relato, sem medida de recorte nesta rodada.
- **Não afeta o ouro do MVP**: o ouro mede só nota (corda + casa) e tempo; símbolo é só exibição e não entra no
  gabarito nem na régua (`tab.avaliar_video`).
- **Risco correlato a vigiar**: arco cuja caixa engole um algarismo faz a nota sumir do recorte. O dono foi
  orientado a acrescentar essa nota por clique no ouro.
- **Liga com**: `CONTEXTO.md` §13.3 ("arcos precisam de janela larga") e o item 1 da Fase 10 em
  `docs/guias/plano-do-produto.md` (significado de símbolo/técnica, arco de ligadura incluído).
- **Dívida**: a caixa do arco precisa de janela larga, medida no quadro, antes de qualquer campo `tecnica` depender dela.

## 2026-10-10 — LINHA DE BASE do produto contra o ouro de vídeo (corrigida: fase 2, correção da régua)

**Os números da primeira linha de base estão INVÁLIDOS: pareamento por instantes escolheu outra página.**
Com o legado tratado como uma tela de exibição = vídeo inteiro, a régua pareava a tela prevista com a tela do
ouro que mais aparece nos instantes (tela 5), não com a página que foi lida (quadro em 271 s), e instante fora
da janela transcrita contava como `erro`. Esses números ficam só como registro:

- ~~A (padrão): telas 1 de 11; precisão 9 de 43; revocação 9 de 397; tempo 1 de 40 (erro 39)~~ **inválido**
- ~~B (meio, sem símbolos): telas 1 de 11; precisão 5 de 37; revocação 5 de 397; tempo 0 de 40 (erro 40)~~ **inválido**

**Números novos** (régua corrigida; pareamento pelo critério do coordenador: tela do `pre.json` que
contém o quadro lido, depois instante do ouro mais próximo do quadro lido, por último conteúdo):

- **Mudança de código** (nada commitado ainda, ver abaixo): `tab/transcrever.py` grava `quadro_lido_s` (o
  quadro em que o painel foi lido) e `janela_s` (o intervalo que o tempo cobre); `tab/avaliar_video.py`, no
  legado, escolhe a tela pelo critério acima (`escolher_tela_legado`) e declara `pareamento:` na saída. A
  régua lê `data/saida/ouro_video/<slug>/pre.json` por padrão (`--pre` para outro caminho).
- **Predição A** (`--inicio 0.4`, padrão, `--simbolos ""`): `quadro_lido_s` 271,6 s, `janela_s` [239,2; 673,8].
  Pareada: **ouro tela 1** (`pre.json` t_ini 240, t_fim 306: contém 271,6 s; **sanidade OK**). Telas 1 de 11.
  Notas: precisão 5 de 43 entregues = 0,116; revocação 5 de 397 do ouro = 0,013; inventadas 38 de 43; perdidas
  392 de 397; acerto de casa 1 de 5 casadas = 0,200. Tempo: 1 de 40 com o estado certo (acerto 1, erro 39, json
  sem tempo 0). Régua 2x: idênticas.
  - Antes, pelo critério de conteúdo, a régua pareava a tela 5 (9 de 43). Esse número sai do critério novo.
- **Predição B** (`--inicio 0.5 --janela 30 --simbolos ""`): `quadro_lido_s` 339,5 s, `janela_s` [237,6; 669,5].
  Pareada: **ouro tela 3** (`pre.json` t_ini 328, t_fim 390: contém 339,5 s; sanidade OK). Telas 1 de 11. Notas:
  precisão 35 de 37 entregues = 0,946; revocação 35 de 397 do ouro = 0,088; inventadas 2 de 37; perdidas 362 de
  397; acerto de casa 35 de 35 casadas = 1,000. Tempo: 0 de 40 com o estado certo (erro 39, json sem tempo 1).
  Régua 2x: idênticas.
- **Tempo**: erro em 39 de 40 nas duas predições. Não é efeito da janela: em A o número não mudou; em B o único
  instante fora da janela passou de `erro` para `json_sem_tempo`. A causa do erro de tempo **não foi investigada**.
- **Limites da `janela_s`**: é o primeiro e o último quadro em que o marcador foi detectado (série de estado),
  não a varredura inteira. `quadro_em_s` continua sendo o `t0` (já trocado pela janela do cursor); o quadro lido é
  `quadro_lido_s`. Nas duas predições são iguais porque não houve janela de cursor.
- **Decisão do coordenador**: o legado lê um quadro, então a tela certa é a que estava na tela em
  `quadro_lido_s`. Critério implementado na ordem acima. O conteúdo ficou só como último recurso.
- **RESSALVA (pareamento por intervalo)**: a tela do ouro junta várias páginas (a tela 1, 240–306 s, cobre 4 páginas,
  segundo a Fase 3). Então o pareamento por `[t_ini, t_fim]` pode cair na tela "certa" do ouro com conteúdo de outra
  página. Os números de nota destas linhas de base **só valem quando `quadro_lido_s` está na mesma página do
  `quadro_ref_s` da tela pareada**. Isso NÃO foi verificado: A lê 271,6 s e a tela 1 tem `quadro_ref_s` 302 s;
  B lê 339,5 s e a tela 3 tem `quadro_ref_s` 328 s.
- **Commit**: não feito; aguarda o gate do repositório (`tab/telas.py` e `tests/test_telas.py` do outro
  agente). Nos meus arquivos, 34 de 34 testes passam (`tests/test_avaliar_video.py` e
  `tests/test_transcrever_janela.py`), e o ruff passa neles.
- Predições em `data/saida/avaliar_video/base_transcrever.json` e `base_meio30s.json`, relatórios
  `*_relatorio.json`. Não commitadas.

## 2026-10-10 — FASE 3: `tab/telas.py` (telas = páginas de tablatura no tempo)

- **Comando**: `python -m tab.telas VIDEO --json saida.json [--folha PASTA] [--ouro data/gold/ouro_video/<slug>.json]`
  (no container; `--ouro` mede o CA contra o ouro e não o altera). Medições em `data/saida/telas/{mvp,serge,cifra}.json`
  e imagens de conferência em `data/saida/telas/{mvp,serge,cifra}/` (`folha.png` + `tela_NN.png` do `quadro_ref_s`).
- **Cadeia**: presença a cada 5 s com `painel.escolher` + portões (passo 14-45, saturação mediana <= 25, cinza mediano
  >= 20), bordas refinadas por busca binária até 1 s; amostras a 2 qps no trecho (uma passada do `tab.leitor`);
  assinatura de tinta; troca/repetição por `1 − IoU`; rolagem só detectada (`phaseCorrelate`), declarada em `modo`;
  a troca entre duas amostras é afinada para 0,1 s (busca binária com `quadro_em`).
- **Medido no `retrato brasileiro`** (h264, 679 s; trecho 239,4-673,8 s; 869 amostras; 14 telas, 23 exibições, 160 s):
  histograma de `1 − IoU` entre amostras consecutivas (868 pares): `[0,0.02)=846, [0.02,0.5)=0, [0.5,0.6)=1, [0.6,0.8)=16,
  [0.8,1)=5`. Repetição (distância da página nova à tela mais parecida, 22 comparações): `[0,0.02)=9, [0.02,0.5)=0,
  [0.5,0.6)=1, [0.6,0.8)=11, [0.8,1)=1`. **Vale vazio de 0,02 a 0,5 nos dois histogramas.**
- **`serge kottelat` (`chloe (joe pass style)…`, av1, 91 s; trecho 0-79,4 s; 159 amostras; 8 telas)**: consecutivas
  `[0,0.02)=144, [0.02,0.05)=6, [0.15,0.2)=1 (o fade do início), [0.8,1)=7`; repetição `[0.8,1)=7`. Mesmo vale.
- **`cifra club` (`a banda - chico buarque…`, av1, 211 s)**: **sem tablatura** (a cifra é de acordes). O detector deu
  presença em 199,4-203,1 s: é o **banner de patrocinadores** do vídeo (imagem aberta: EAGLE/Acústico/DATALINK/SHURE),
  falso positivo do `painel.escolher` num trecho de 3,75 s. Não corrigido (portão da presença, dívida). Uma varredura de
  9 vídeos do canal a cada 30 s achou **0** quadros com painel: o canal não tem tablatura legível por esta cadeia.
- **Limiar**: `LIMIAR_TROCA = LIMIAR_MESMA = 0,3` (meio do vale vazio; constantes comentadas em `tab/telas.py`).
- **CA contra o ouro (`retrato_brasileiro.json`, 40 instantes, 11 telas)**: **18 de 40 instantes (0,45) na tela
  certa. NÃO cumpre os 98 %.** Revocação de telas **11 de 11** (cada tela do ouro tem prevista no seu `quadro_ref_s`).
  Previstas 14; **7** sem tela do ouro correspondente (7 de 11 = 64 %, longe de <= 10 %). Os 22 instantes errados têm
  uma só causa, medida: **7 das 11 telas do ouro cobrem mais de uma página** (a ferramenta do ouro agrupava por
  diferença média em cinza <= 2,0, que não vê a troca entre páginas de mesmo leiaute). Por intervalo `t_ini`-`t_fim` do
  `pre.json`: ouro 1 (240-306) = 4 páginas previstas; ouro 3 (328-390) = 3; ouro 4 = 2; ouro 5 (428-488) = 3; ouro 6
  (490-510) = 2; ouro 7 (512-572) = 3; ouro 9 = 2; as telas 2, 8, 10 e 11 do ouro = 1. As imagens (`mvp/tela_02.png`,
  `tela_03.png`, `tela_04.png`) mostram as 3 páginas distintas dentro da tela 1 do ouro (compassos 1-4, 5-8 e 9-12;
  quadros 255 s, 276 s e 302 s). O ouro **não foi editado**. A medição vale sem erro do produto só se o dono aceitar
  que as páginas previstas são páginas diferentes; senão, reabrir as telas do ouro com o `ouro_video` e separar as
  7 páginas extras. **Decisão do dono**: separar o ouro (e rotular as páginas que faltam) ou aceitar a segmentação por página.
- **Telas do ouro que o produto junta** (`ouro.ouro_juntadas_pelo_produto` em `data/saida/telas/mvp.json`): ouro 2+3+4
  -> prevista 5, ouro 5+7 -> prevista 7, ouro 6+8 -> prevista 10. Duas causas: (a) a página 308-328 s é a mesma
  em 391-407 s (repetição legítima: mesma tela, 2 exibições) e o ouro a separou em telas 2 e 4; (b) o `quadro_ref_s`
  do ouro 3 é 328,0 s, e a troca de página está em 328,4 s: a prevista em 328,0 é a página anterior.
- **Achado para o `tab.leitor` (Fase 1, não corrigido)**: em torno dessa troca, `leitor.quadros(v, 326, 330,5, 4 qps)`
  vira entre 328,25 e 328,5 s e `leitor.quadro_em(v, t)` vira entre 328,5 e 328,75 s: **as duas leituras diferem em
  ~0,25 s** no mesmo vídeo (h264, 29,97 fps). A troca afinada por `quadro_em` pode estar até 0,25 s depois da vista pelas
  amostras. Isso importa para o tempo da Fase 5 (onset do marcador) e para a conferência por instante do ouro.
- **Não repetir (falhou antes de chegar nisso)**:
  1. `S > 25` do HSV como "marcador": em pixel escuro um desvio de 2 níveis dá S > 25, e **64-68 % dos pixels de tinta
     da tablatura** passavam por "coloridos" (a assinatura apagava os algarismos; o teste com mp4v sintético falhou
     por isso). Trocado por **croma `max − min` > 15** (faixa do marcador: croma mediano 34, p10 16; fundo: mediana 3).
  2. Tinta com as cordas: entre páginas de mesmo leiaute o `1 − IoU` dava 0,03-0,12, igual ao ruído (as cordas são a
     mesma tinta em toda página). Tirar as corridas horizontais >= 40 px separa: 0,5-1,0 contra <= 0,05.
  3. Comparar sem máscara de "tinta conhecida": a faixa que anda dava 0,10-0,15 entre quadros da MESMA página (`serge`).
  4. Restringir a assinatura à faixa das 6 cordas (para juntar páginas com a mesma tablatura e compassos diferentes):
     **não mudou nada** (A em 245 s e A' em 287 s têm o mesmo desenho, mas o leiaute desloca 5-15 px; continuam
     telas distintas). Descartado por simplicidade.
- **Testes** (gate): `tests/test_telas.py` (vídeo sintético A, B, A com faixa colorida andando: 2 telas, A com 2
  exibições, faixa sem troca; assinatura sem marcador e em tema escuro; IoU; corte de páginas e transição; rolagem;
  voto; busca binária; ouro).
- **Limites**: `modo` é por vídeo; rolagem só detectada (T8.4 faz o resto). Um painel com a mesma tinta em duas páginas
  (música que repete exatamente) vira a MESMA tela. Presença é amostrada a 5 s: tablatura com menos de 5 s pode passar.

## 2026-10-10 — FASE 2: ouro v2 (páginas pelo `tab.telas`, notas do dono herdadas do v1)

- **Comando**: `python -m tab.ouro_video completar VIDEO --ouro-v1 data/gold/ouro_video/retrato_brasileiro.json --ouro-v2 data/gold/ouro_video/retrato_brasileiro_v2.json --saida data/saida/ouro_video/retrato_brasileiro_v2 [--telas-json data/saida/telas/mvp.json]`
  (recusa sobrescrever um v2 existente; o v1 só é lido). `fundir_ouro` é pura e testada.
- **Regra**: tela v1 com `quadro_ref_s` dentro de uma exibição da página dá as notas (origem `ouro_v1 (dono)`, conferida);
  várias telas v1 na mesma página: usa a de `quadro_ref_s` mais próximo do da página e COMPARA as outras (conflito é
  relatado, a página fica `conferida: false`); página sem v1: notas do modelo, `modelo — a rotular`. Instantes: `t`,
  coluna e obs do dono; `tela` pelo tempo; `tela_confirmada: false`.
- **MVP**: 14 páginas; 7 herdadas (4, 5, 7, 10, 12, 13, 14; 255 notas); 7 a rotular (1, 2, 3, 6, 8, 9, 11; 271 notas do
  modelo); 22 de 40 instantes reatribuídos; 2 conflitos, ambos na página 5 (v1 telas 2, 3 e 4 caem nela; usada a 4):
  as notas das telas 2/3 divergem das da 4 (corda/x), a conferir pelo dono.
- **Página** (`servir`): aba Telas com filtro "só a rotular" e destaque das herdadas; aba Instantes com a imagem do instante
  ao lado da página atribuída (com a coluna marcada) e botões "é esta página" / "outra página". Compatível com o v1.

## 2026-10-10 — FASE 3 (conserto): transição/oclusão não vira página; `quadro_ref_s` no meio da maior exibição

- **Defeito (visto pelo coordenador)**: a tela 1 (239,4-245,25 s) era a página dos compassos 1-4 com as mãos do vídeo
  por cima do lado direito (imagem aberta), e virou página própria; e `quadro_ref_s` caía logo depois de uma troca
  (tela 2: 328,9 em exibição que começa em 328,4; tela 6: 407,4 em 406,75).
- **Medido antes de fixar**: no trecho 239,4-250 s, contra a página seguinte, o 1 − IoU total é 0,63, mas o
  **prefixo esquerdo (280 das 446 colunas = 63 %)** dá 0,008-0,011. Páginas diferentes divergem já no primeiro compasso
  (prefixo comum só a clave). Fixado: `LIMIAR_OCLUSAO = 0,1` acumulado por coluna, `FRACAO_OCLUSAO = 0,4` da largura,
  pela esquerda ou pela direita, com >= 150 px de tinta (`convergem`).
- **Regra** (`absorver_transicoes`): o trecho é anexado ao vizinho mais parecido se tem < 3 amostras (1,5 s: fade/wipe)
  ou se converge com um vizinho maior-ou-igual (o MENOR é o anexado; a página que fica mantém a tinta limpa).
  `quadro_ref_s` (`quadro_de_referencia`): amostra de menos marcador na metade central da MAIOR exibição.
- **Antes -> depois no MVP (14 -> 13 telas)**: a antiga tela 1 (239,4-245,25) entrou na antiga tela 2, que agora é a
  tela 1 com exibições (239,375-265,875) e (328,375-349,375). As outras 12 telas têm **as mesmas exibições**, só com
  id -1 (antigas 3..14 = novas 2..13). Histogramas de 1 − IoU iguais (846 em [0,0.02); vale vazio de 0,02 a 0,5).
  `quadro_ref_s` antes -> depois: 328,9 -> 257,9 (tela 1), 275,4 -> 275,4, 288,9 -> 300,4, 391,9 -> 322,4,
  407,4 -> 419,9, 511,4 -> 521,9, 532,4 -> 458,9, 469,9 -> 479,9, 574,4 -> 578,9, 589,9 -> 599,9, 612,9 -> 620,9,
  631,9 -> 645,4, 672,9 -> 659,9. Serge: 8 -> 8 telas, exibições iguais.
- **CA contra o ouro**: 18 de 40 (igual; o limite é o ouro com telas que cobrem várias páginas); telas do ouro com
  prevista 11 de 11; previstas 13, 6 sem tela do ouro.
- Testes novos: transição curta anexada ao vizinho, oclusão anexada à página limpa, páginas diferentes continuam
  duas, `quadro_ref_s` longe da fronteira.
- **Regerado com o `tab.telas` consertado (ded676ec)**: 13 páginas; **9 herdadas** (1, 3, 4, 5, 6, 9, 11, 12, 13; 328 notas),
  **4 a rotular** (2, 7, 8, 10; 166 notas do modelo); 22 de 40 instantes reatribuídos; **0 conflitos**. Achado: o
  `quadro_ref_s` do v1 vem de `leitor.quadros` e pode estar até **0,75 s** do tempo do `tab.telas` (tela v1 4: ref 406,0
  mostra a página que começa em 406,75; tela v1 3: ref 328,0 mostra a página seguinte). Mapear só pelo tempo errava o
  conjunto de notas (os "conflitos" da antiga página 5 eram isto: as telas v1 2/3/4 são 3 páginas diferentes). Agora
  `pagina_do_quadro_ref` considera as páginas a até 1,5 s e fica com a cujas notas do modelo mais concordam com as do dono
  (35/0, 39/1, 33/0...); o desempate vai em `fusao.telas_v1_na_borda` do `pre.json`.

## 2026-10-10 — ouro v2 e medições com ele

- **Ouro v2 fechado pelo dono** (`data/gold/ouro_video/retrato_brasileiro_v2.json`, commit `76d301b7`, só esse arquivo):
  13 páginas, 493 notas, 40 de 40 instantes com `tela_confirmada: true`. Páginas com `conferida: true` (notas do
  dono): 1, 3, 4, 5, 6, 9, 11, 12, 13. **Páginas com `conferida: false`: 2, 7, 8, 10**. O dono trabalhou nelas mas não
  clicou no botão de conferência, então as notas dessas quatro são do modelo e **não estão validadas**. Os 14 instantes
  que caem nessas páginas estão confirmados (o dono confirmou a página do instante), mas não as notas. O arquivo não foi
  alterado nesta rodada.
- **CA da Fase 3 contra o v2** (meta do plano: ≥ 98 %), `python -m tab.telas "/acervo/sky guitar/retrato brasileiro -
  tab & lesson.mp4" --json data/saida/telas/v2_ca.json --ouro data/gold/ouro_video/retrato_brasileiro_v2.json`
  (2 execuções, 137 s e 180 s; `ouro` e `telas` idênticos):
  - instantes na tela certa: **40 de 40 = 1,000**;
  - revocação de telas (telas do ouro com prevista): **13 de 13 = 1,000**;
  - previstas a mais (super-segmentação): **0 de 13 = 0 %** (meta ≤ 10 %);
  - erros: 0; ouro juntado pelo produto: nenhum.
  - **Ressalva de circularidade**: as páginas do v2 vieram do próprio `tab.telas` (commit `ded676ec`), e a tela de cada
    instante foi reatribuída pelo tempo a partir dessas exibições. O dono confirmou cada instante na página sugerida. O
    40/40 mede concordância com o que o dono confirmou, não acerto independente da segmentação: há viés de confirmação.
    Um número independente exige instantes rotulados sem a página sugerida.
- **Régua com o v2**: predições regeradas agora (`tab.transcrever`, mesmos comandos de antes), 45 e 44 notas, com
  corda, casa e `x_quadro` idênticos aos das predições anteriores. Cada régua rodada 2× (`cmp` idêntico nas duas):
  - `python -m tab.avaliar_video --ouro data/gold/ouro_video/retrato_brasileiro_v2.json --pred data/saida/avaliar_video/<pred>.json
    --pre data/saida/ouro_video/retrato_brasileiro_v2/pre.json --json data/saida/avaliar_video/<pred>_v2_r1.json`

  | predição | pareamento | precisão | revocação | inventadas | acerto de casa | tempo |
  | --- | --- | --- | --- | --- | --- | --- |
  | padrão (`--simbolos ""`, início 0,4) | tela do pre em 271,6 s | 4 de 43 = 0,093 | 4 de 493 = 0,008 | 39 de 43 | 1 de 4 = 0,250 | 1 de 40 (erro 39) |
  | meio (`--inicio 0.5 --janela 30 --simbolos ""`) | tela do pre em 339,5 s | 35 de 37 = 0,946 | 35 de 493 = 0,071 | 2 de 37 | 35 de 35 = 1,000 | 0 de 40 (erro 39, json sem tempo 1) |

  Telas: 1 de 13 (o legado tem uma tela só). Com o v1 (397 notas) a linha de base era 5 de 43 e 35 de 37; a queda na
  revocação é o denominador maior (493 contra 397 do v1; a origem das 96 notas a mais não foi auditada). O tempo continua
  errado em 39 de 40 nas duas predições, como antes (causa ainda não investigada).
- **Comandos das predições**: `python -m tab.transcrever "<vídeo>" --simbolos "" --json data/saida/avaliar_video/base_transcrever.json`
  e `python -m tab.transcrever "<vídeo>" --inicio 0.5 --janela 30 --simbolos "" --json data/saida/avaliar_video/base_meio30s.json`.
- Artefatos não commitados: `data/saida/telas/v2_ca.json`, `data/saida/telas/v2_ca_r2.json`, `data/saida/avaliar_video/*_v2_r{1,2}.json`.
- **Atualização (2026-10-10)**: páginas 2, 7, 8 e 10 marcadas `conferida: true` por declaração escrita do dono ('conferi tudo minuciosamente'); a bullet acima sobre `conferida: false` está superada. Nenhuma nota, instante ou outro campo alterado.
- **Tela 10 do v2 (2026-10-10, dono)**: removidas 2 notas da corda 1 (casa 7 em x≈503,5 e casa 2 em x≈543) que eram o arco de ligadura, lidas como algarismo; 493 -> 491 notas. Autorizado pelo dono ('em baixo do arco estava 1 e 0'); as notas `1` e `0` da corda 2 sob o arco ficam.

## 2026-10-10 — Fase 4: casa de dois algarismos. Limiar de fusão por vão NÃO separa (revertido)

Defeito (relato do dono no ouro v2): `10`, `12`, `13`, `14` saem como dois tokens. Medido em `data/saida/fase4_digitos/`
(`medir_vaos.py`, `ler_paginas.py`, `comparar_paginas.py`). Detalhe em `docs/rodadas/0005-casa-dois-algarismos-vao.md`.

- Vão entre os dois algarismos de cada número de dois dígitos do ouro (5 casos): **0,231 a 0,324 passo** (mediana 0,275).
- Vão entre notas diferentes vizinhas na mesma corda: **0,324 a 0,37** quando inclui os pares sem nota casada no ouro
  (a primeira medição, de 0,463, tinha excluído esses pares).
- Não há limiar de vão que separe as duas classes. O `2`→`7` (corda 1, pág. 5) e o `1`→`3` do `13` (pág. 8) têm o mesmo vão de 7 px.
- Implementado e revertido (gap 0,25 → 0,39): pág. 12 `10` passou a sair certo, mas pág. 5 perdeu 3 notas (casa certa 39 → 37)
  e pág. 8 leu `13` como `12`. Por página: 481/493 → 479/493 com o mesmo `avaliar` 66/71/68 (sem trava de contagem disparada).
- Defeito separado, anterior ao limiar: o token fundido de dois dígitos é rotulado `tecnica` pelo classificador (`12` da pág. 8
  e da pág. 12), então a nota vai para `nao_nota` e some de `notas`. Medido: o `12` da pág. 8 já é fundido no limiar de 0,25.
- Régua `tab.avaliar_video` com `--inicio 0,5 --janela 30` cobre só a tela 1 (sem `12`). Com quadros das páginas 8 e 12,
  o pareamento legado escolhe a tela 5 para o quadro da página 8 (intervalos de tempo das telas 5 a 8 se sobrepõem e
  `pareamento` pega a primeira). Defeito da régua, não do modelo; não corrigido aqui.
- Próximo passo (não implementado): decidir a fusão de vizinhos pelo classificador do token fundido, e não só pelo vão.

## 2026-10-10 — Fase 4: casa de dois algarismos pela forma (aceita, 481 -> 484)

Detalhe e medições em `docs/rodadas/0006-casa-dois-algarismos-forma.md`. Dados em `data/saida/fase4_digitos/`.

- **Causa do `12` virar `tecnica`** (pág. 8): o token fundido tem `partes_digito = 1` (o `2` não tem haste), e `compativel`
  exige dois componentes com haste para dois dígitos. O classificador dava `12` com 0,888.
- **Regra nova**: a casa de dois dígitos sai da leitura das partes (`_casa_das_partes`): cada parte é dígito, a concatenação
  é classe do modelo entre 10 e 24, e o token dá a ela pelo menos 0,80. Pares de dígitos com vão em (0,25; 0,40] passo
  são fundidos só quando essa regra aceita (`_fundir_pares_de_digitos`). `compativel` não mudou.
- **Medido nas 13 páginas do ouro v2 (pareamento direto)**: base 481/493, dois-dígitos 1 de 5, inventadas 21.
  Só classificação: 482, 2 de 5. Classificação mais fusão (escolhida): **484/493, 4 de 5, inventadas 19**; nenhuma página piora.
  Único dois-dígitos que resta errado: `13` (pág. 8), que o modelo não tem como ler.
- `tab.avaliar` oficial_1/2/3 = 66/72, 71/72, 68/72, sem "CONTAGEM MUDOU" (tokens por canal iguais).
- `tab/ouro_video.py::ler_notas` passou a usar a caixa do token exposta pela nota (`caixa`); sem isso o token fundido
  saía com centro errado e o `10` da pág. 12 sumia no pareamento.
- Testes: `tests/test_casa_dois_digitos.py` (decisão e fusão no gate; ponta a ponta com o modelo real em `integration`,
  porque `artefatos/` não é versionado). `pytest tests/` = 231 passed, 3 deselected.
- `make gate` = 0 ("All checks passed!", `pytest tests/` = 232 passed, 3 deselected).
- Limites: classes de dois dígitos do modelo são só `10, 12, 14, 15, 17, 19, 21, 24`; fonte 0,55 do passo ainda sai
  `tecnica` ou `junk` em alguns passos pequenos (16 a 18).
- **Não repetir**: critério "fundido maior que o maior isolado" (reprova o `12` da pág. 8: 0,888 contra 0,943);
  aceitar a casa só pelo vão.
- **Defeito separado, não corrigido**: no `reconhecer_linha` o bloco do discriminador de algarismo roda antes de `classes`
  ser preenchido; pela ordem do código, `alvos_d` é sempre vazio e o discriminador não atua. Medir o efeito de corrigir é a próxima rodada.

## 2026-10-10 — Fase 7.0: precisão do detector de presença no `portao.json` (só medição, detector intacto)

- **O que foi medido**: o critério de presença que o produto usa, `tab.telas.painel_do_quadro` (que chama
  `painel.escolher` + portões de passo, saturação e cinza), no **quadro inteiro** de cada caso do `data/gold/portao.json`
  (`tab.leitor.quadro_em` no instante `instante_frac × duração`). Os 289 casos têm vídeo e instante; nenhum é só recorte.
  `duvida` excluído (2). Lidos: 287; sem quadro: 0.
- **Comando**: `python -m tab.presenca_aval` (no container). Saída: `data/saida/presenca/resultado.json`,
  `fp_presenca_{1..4}.png` (41 quadros FP), `vp_presenca_1.png` (10 VP espalhados), `tipos_fp_quadros.json` (minha
  classificação das 41 FP, quadro a quadro). Teste puro em `tests/test_presenca_aval.py` (no gate, 232 passando).
- **Por recorte** (287 casos, 1 linha por recorte): VP 97, **FP 139**, VN 45, FN 6. Precisão **0,411**, revocação **0,942**.
- **Por quadro** (144 quadros únicos; um quadro tem 1 ou 2 recortes, e o detector responde por quadro inteiro):
  VP 77, **FP 41**, VN 20, FN 6. Precisão **0,653**, revocação **0,928**. Este é o número que vale para "há tablatura
  neste quadro".
- **Por canal, por quadro** (VP / FP / VN / FN; precisão):
  `sky guitar` 43/1/1/3 (0,977) · `iwaki` 16/22/3/2 (0,421) · `kimny's guitar` 5/3/0/0 (0,625) · `leonardo ramos`
  6/0/1/1 (1,000) · `mr. tabs` 7/1/0/0 (0,875) · `pablo romé` 0/6/1/0 (0,000) · `paolo d'angelo` 0/3/3/0 (0,000) ·
  `guitar dell'arte` 0/5/3/0 (0,000) · `cifra club` 0/0/8/0 (sem FP).
- **Portão aprendido** (`artefatos/portao_real_1`, o `tab.portao` com seed 1, limiar 0,5), **só para comparar; NÃO é o
  usado pelo produto**, e foi treinado nestes mesmos casos (número dentro da amostra, otimista): por quadro VP 77,
  FP 35, VN 26, FN 6, precisão 0,688, revocação 0,928 (iwaki 18 FP). Por recorte FP 127, precisão 0,433.
- **Classificação das 41 FP (olhei cada folha; a caixa do detector desenhada na imagem)**:
  - **32 com tablatura real dentro da caixa** (TAB com números sobre as cordas, ou partitura com pauta de TAB embaixo,
    que a caixa cobre): o detector acertou no quadro; o `portao.json` rotulou `nao_tablatura` os **outros** recortes do
    mesmo quadro (topo/meio/base que o dono olhou). Isto é divergência de rótulo por recorte, não erro de presença.
    Pendente de confirmação do dono; se ele confirmar, a precisão por quadro vai para 109/118 = **0,924** (sem mudar
    o detector).
  - **5 braço do violão** (a caixa cobre o braço, sem TAB): `guitar dell'arte` t=181,92 e 242,0; `kimny's guitar`
    t=112,9 e 147,64; `mr. tabs` t=220,92. **Erro de verdade do detector.**
  - **4 partitura de 5 linhas sem TAB dentro da caixa**: `iwaki` t=38,82, 53,71, 85,41 e 118,16. **Erro de verdade.**
  - Tarraxa, piano, banner, tela preta e fade: **0** no conjunto.
- **Os 10 VP** (`vp_presenca_1.png`): todos com TAB real dentro da caixa (inclusive `mr. tabs` t=348,34 em guitarra elétrica).
- **Leitura**: o FP de **verdade** do critério atual é pequeno no conjunto (9 de 41 quadros), e vem de braço e de pauta
  sem TAB. A maior parte do "erro" medido contra o `portao.json` é o rótulo ser por recorte: o gabarito não cobre o
  quadro inteiro. Isto muda o que se pode afirmar: o `portao.json` **não** serve como medida de presença por quadro sem
  o dono rotular o quadro inteiro (ou dizer que a faixa 'nao' não cobre a TAB do quadro).
- **Limites**: medido só nos instantes 0,25 a 0,9 de cada vídeo (os do gabarito); não é varredura de vídeo inteiro (a
  Fase 7 mede o acervo).
- **Não repetir**: montar folha de FP por *caso* (139 células, 480 px) é ilegível e conta cada quadro duas vezes; a folha
  é por quadro (`fps_quadros`).

## 2026-10-10 — Fase 7.1: gabarito de caixa por quadro (dono) e candidato de reserva C1 NÃO adotado (aceite 0,976 < 0,98)

- **Gabarito versionado**: `data/gold/presenca_quadros.json`, 144 quadros lidos pelo dono (9 de 41 FP
  marcados como não tablatura). `tablatura_no_quadro` em 124 quadros; caixa em 118 (109 sobre TAB).
  Os 4 iwaki FP30/31/37/38 têm a TAB de 6 cordas embaixo da pauta, então entraram como "TAB no quadro".
- **Métrica nova** (`python -m tab.presenca_aval`): **precisão de caixa** (caixas sobre TAB / caixas) e
  **revocação de caixa** (quadros com TAB que receberam caixa sobre TAB / quadros com TAB). Presença por
  quadro só como referência. Teste no gate (`tests/test_presenca_aval.py`, 9 testes), com um teste do contrato
  do gabarito (os 9 códigos do dono).
- **Medido no código atual**: caixas 117, corretas 108 → **precisão de caixa 0,923**; revocação 108/124 =
  **0,871**. Presença por quadro: precisão 1,000 (todo quadro com caixa tem TAB em algum lugar), revocação
  0,944. Regressão a investigar: FP12 perdeu a caixa desde a 7.0 (código posterior, não medido a causa).
- **Causa dos 9 erros**: todos caem na reserva `escolher_rapido`, que escolhe a faixa de maior uniformidade
  (a tinta da TAB penaliza a uniformidade). A TAB está na faixa `base` nos 9.
- **Candidato C1** (reserva ordenada por fração de papel branco, medido em memória, `tab/painel.py`
  intacto): **precisão de caixa 0,952** (120/126) sob o rótulo do dono; revocação 0,968. Se os VN15..20
  tiverem TAB, sobe a 0,992. **Aceite (≥0,98) não atingido com o rótulo do dono → não adotado**, sem commit
  de `painel.py`. Checagens do MVP não rodadas (dependem do aceite).
- **Decisões pendentes do dono** (ver a rodada 0007): (1) VN15, VN17, VN18, VN19 e VN20
  mostram TAB visível embaixo; o `portao.json` os rotulou `nao_tablatura` por recorte. Confirmar o rótulo
  decide se o C1 passa. (2) FP38: a caixa cobre só a pauta (conferido na imagem). (3) regressão do FP12.
- **Decisão do dono (2026-10-10, olhando os quadros), aplicada no gabarito** (commit `05ec67b1`):
  VN15, VN17, VN18, VN19 e VN20 têm TAB no quadro (`tablatura_no_quadro=true`); `quadros.tablatura_no_quadro`
  124 → **129**; `suspeitas_rotulo_nao` esvaziada. FP38 confirmado: caixa sobre a pauta (`caixa_sobre_tablatura=false`).
  Com o rótulo novo, **HEAD**: precisão de caixa **0,923** (108/117), revocação **0,837** (108/129); presença
  VP 117 FP 0 VN 15 FN 12.
- **C1 medido com o gabarito novo** (`tab/painel.py`, reserva `escolher_rapido` por fração de papel branco,
  `papel_branco`, cinza > 200): o detector desenha 20 caixas que o gabarito não tinha no quadro. Cada uma foi
  rotulada por **leitura visual do agente** (não do dono; ficam em `caixas_revistas` só para a medição,
  listadas em `data/saida/c1/presenca_quadros_com_revistas_c1.json`): 17 cobrem TAB, 3 cobrem só a pauta
  (VN18, VN20, FP38). Resultado: **caixa 123/126 = 0,976** (aceite ≥ 0,98: **NÃO atingido**); revocação
  123/129 = 0,953; presença VP 126 FP 0 VN 15 FN 3. Por canal, o erro está todo no `iwaki` (40/43).
- **Checagens do MVP, C1 vs HEAD** (rodadas em `data/saida/c1/{head,c1}/`, script `data/saida/c1/run.sh`):
  - `tab.telas` retrato: 13/13 telas, 40/40 instantes (igual).
  - `tab.video` + `tab.avaliar_video`: precisão 485/486 = 0,998, revocação 485/491 = 0,988, casa 482/485 = 0,994
    (igual); tempo **33/40**, tempo falso **0** (igual).
  - `tab.avaliar` sementes 1/2/3: 66/72, 71/72, 68/72 (igual).
  - gate verde com o C1 (ruff check, ruff format --check, pytest 274 passam com 2 testes de `papel_branco`).
  O C1 não regride o MVP, mas **não foi adotado** porque o aceite de caixa falhou. Código revertido
  (`tab/painel.py` e `tests/test_painel.py` no HEAD).
- **Pendência para o dono**: confirmar os 20 rótulos visuais do agente em `caixas_revistas` (17 TAB, 3 pauta).
  Se o dono confirmar, o C1 fica a 0,976 e não passa; o que faltaria é separar as 3 caixas da pauta no iwaki
  (VN18, VN20, FP38), não o critério de reserva.
- **Dúvida aberta**: FP12 perdeu a caixa desde a 7.0. Com C1 a caixa de FP12 volta; a causa no código atual
  continua não investigada.
- **Não repetir**: ver as 4 linhas novas na tabela "O que foi tentado e falhou".
- Rodada: `docs/rodadas/0007-presenca-caixa-por-quadro.md`. Medições e scripts de diagnóstico em
  `data/saida/presenca_7_1/` (não versionados).

## 2026-10-10 — Fase 7.1 (C1b): C1 ADOTADO com regra de pauta (5 x 6 linhas) e `refinar` que mantém as cordas

- **Supera a entrada anterior**: o C1 (reserva por papel branco) foi a base; agora ele entra com duas
  regras em `tab/painel.py`. Commit deste item (ver a mensagem).
- **Causa dos 3 erros da pauta** (olhado nos quadros, `data/saida/c1b/crop_*.png`): na faixa `base`, o
  `segmentar` acha 5 linhas fortes da pauta mais 1 fraca (viga, força ~0,38 contra ~0,86). No `refinar`,
  o recorte estreitado em x era re-segmentado e passava a dar as linhas da pauta (6 fortes), e a caixa
  saía sobre a partitura. VN18 e FP38 sofriam disso; VN20 caía direto na `base` pauta.
- **Regra 1** (`e_pauta`, dentro de `criar`): grupo de 6 linhas com exatamente 5 fortes (força >= 0,5 da
  mais forte) é pauta, não TAB. A reserva segue para a faixa vizinha (a TAB, com 6 fortes).
- **Regra 2** (`refinar`): o recorte só estreita em x. Se a re-segmentação der cordas com outro y
  (`mesmas_linhas`, tolerância 2 px), fica com o candidato original.
- **Medido (gabarito commitado + 4 caixas novas rotuladas à parte, `data/saida/c1b/gold_visual.json`)**:
  caixa **125/126 = 0,992** (aceite 0,98: **passa**); revocação de caixa 124/129 = 0,961 (C1 era 123/129 = 0,953).
  Presença: VP 125 FP 1 VN 14 FN 4. Caixa de HEAD: 108/117 = 0,923.
- **Caixas novas sem rótulo do dono** (rótulo visual do agente, em `data/saida/c1b/folha_novas.jpg`):
  VN18 e FP38 sobre a TAB (certas); **VN14** sobre TAB visível (certa visualmente, mas o gabarito diz
  `tablatura_no_quadro=false`: suspeita de rótulo do quadro, a decidir pelo dono); **FP02 errada**: caixa
  nova `[0,0,1920,106]` no topo, sobre a faixa preta e as cordas do violão do vídeo. É a 1ª FP de caixa
  nova que o HEAD não tinha (o HEAD não desenhava nada no FP02). Não separada: as 6 linhas do topo são
  fortes (0,61-0,65) e regulares, igual às cordas do vídeo.
- **MVP, HEAD limpo vs HEAD + este painel** (cópia do `git archive HEAD` no scratchpad, sem os arquivos
  de outros agentes): telas 13/13 e 40/40 (igual); notas 485/486, 485/491, casa 482/485 (igual); tempo
  33/40, erro 5, json sem tempo 2 (**igual**); `tab.avaliar` 66/72, 71/72, 68/72 (igual).
- **Atenção**: a árvore de trabalho com o trabalho em andamento da Fase 5 (`tab/video.py`, `tab/leitor.py`,
  `tab/estado.py`) dá tempo 37/40, o que **não** vem deste painel (medido). Não confundir os dois.
- **Gate**: na cópia HEAD + painel: `ruff check .` ok, `ruff format --check .` ok, `pytest tests/` 276
  passando. Testes novos em `tests/test_painel.py`: papel branco separa TAB do braço; 5 fortes + 1 fraca
  é pauta; 6 fortes não é; `mesmas_linhas` tolera só desvio pequeno.
- **Limites e pendências para o dono**: (1) confirmar a VN14 (TAB visível, gabarito diz sem TAB); (2)
  FP02, caixa nova no topo, não separada; (3) o gabarito commitado ainda não tem os 4 rótulos novos
  (ficaram em arquivo à parte, como pedido); (4) FP12 voltou a ter caixa sobre a TAB (medido); a causa
  de ele ter perdido a caixa entre a 7.0 e a 7.1 continua sem investigação. (5) VN20 deixou de ter caixa (era
  a caixa da pauta): tinha TAB no quadro, então a revocação cai nesse quadro.

- **Medição oficial com o gabarito completo** (`python -m tab.presenca_aval`, sem `--gold`, rótulos
  só do dono): 21 caixas revistas em `data/gold/presenca_quadros.json` (FP02, FP03, FP38, VN14, VN18, FP09 e
  as 15 caixas da folha 15a/b; FP11 marcada `parcial`, cobre só metade da TAB).
  - **Precisão de caixa 124/126 = 0,984** (aceite ≥ 0,98: passa). **Revocação de caixa 124/130 = 0,954**.
  - Presença por quadro (referência): VP 126, FP 0, VN 14, FN 4; precisão 1,000, revocação 0,969.
  - Por canal (caixas corretas/caixas): iwaki 42/42; sky guitar 46/46; kimny's guitar 8/8; pablo romé 6/6;
    leonardo ramos 6/6; paolo d'angelo 5/5; mr. tabs 7/8 (erra FP11, parcial); guitar dell'arte 4/5 (erra
    FP02, caixa no topo sobre o braço); cifra club sem caixa.
  - Os 2 erros: FP02 (caixa no topo) e FP11 (parcial). Os números desta rodada usam rótulo do dono; não se
    comparam com o 0,992 da rodada r3, que usava rótulos visuais do agente.
- Commit do gabarito: `1423c59f` (decisões do dono até a 1ª leva). Esta medição fecha o gabarito.

## 2026-10-10 — Fase 4: `tab/video.py` (todas as telas, JSON v1) e a régua que pareia tela sem instante

- **Comando**: `python -m tab.video "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4" --json data/saida/fase4/oficial_v1.json`
  (imagem `quadro`, modelo `artefatos/oficial_3/glifo_sint.pt`, CPU: a GPU segue indisponível no container). Saída medida:
  13 telas, 22 exibições, 506 notas, 27 não-notas. `gerado_por.commit` sai `desconhecido` (o container não tem git).
- **Régua corrigida** (`python -m tab.avaliar_video --ouro data/gold/ouro_video/retrato_brasileiro_v2.json --pred data/saida/fase4/oficial_v1.json`), 2 execuções, JSON idêntico:
  - telas: 13 de 13 pareadas (12 por instantes, 1 por `quadro_ref_s`);
  - precisão 487 de 506 = 0,962; revocação 487 de 493 = 0,988; inventadas 19; perdidas 6;
  - acerto de casa 484 de 487 casadas = 0,994; tempo 0 de 40 (Fase 5).
- **CA da Fase 4**: casa+corda nas casadas 0,994 (meta 0,99): **bate**. Revocação 0,988 (meta 0,98): **bate**.
  Inventadas 19 (meta 0): **não bate**.
- **Defeito da régua, corrigido**: a tela 9 do ouro v2 não tem nenhum instante, então `casar_telas` nunca a pareava. Efeito antes: 36 notas perdidas e 37 inventadas falsas (revocação por instantes 0,915 contra 0,988 agora). `casar_sem_instante` pareia pela exibição prevista que contém o `quadro_ref_s` (sem reusar tela já casada), e `telas.criterio` declara o critério por tela. Testes em `tests/test_avaliar_video.py`.
- **Imagem limpa (T4.1, regra 9)**: medido com o mesmo pareamento por `quadro_ref_s`. `quadro`: 481 de 486 casadas com casa certa (0,9897), 7 perdidas. `mediana` (7 quadros da maior exibição): 487 de 493 (0,9878), 0 perdidas. Fica `quadro` (maior acerto de casa). A mediana recupera as perdidas do marcador, mas troca uma casa certa por errada; seu teste (`tests/test_video.py`) segue no gate.
- **Erros por causa** (medidos com a imagem `quadro` antes da fusão de dois algarismos; ver `data/saida/fase4/erros/grade.png`):
  1. **Arco de ligadura lido como algarismo**: cerca de 18 das inventadas. Verificado a olho em T3 x491, T1 x550 e T5 x711; os outros casos seguem o mesmo padrão, não conferidos um a um. Próxima alavanca: o filtro de símbolo (`tab.simbolo`), que `transcrever` não usa.
  2. **Dois algarismos** (13, 10, 12): era o principal erro de casa; a fusão pela forma (`4d844220`) já atacou esse grupo.
  3. **Marcador colorido ou faixa azul sobre o algarismo**: 6 perdidas e 1 casa (T4 c5, 6 lido como 5). A mediana resolve, mas perde no critério de casa.
  4. **Classificador**: T11 c6, 0 lido como 2. Não verificado visualmente.
- **Não repetir**: pareamento só por instantes deixa de fora uma tela do ouro sem instante e inventa notas; a regua tem que cair no `quadro_ref_s`. Trocar a imagem por mediana para ganhar revocação custa casa (0,9897 → 0,9878).
- **Limites**: tempo por exibição ainda não existe (Fase 5); a régua de tempo segue marcando 0 de 40. Os números dependem da fusão de dois algarismos do `reconhecer` (commit `4d844220`).

## 2026-10-10 — GPU no podman: `devices: nvidia.com/gpu=all` (CDI por device)

- O `gpus: all` do `compose.yaml` não chega ao podman: o container dava `torch.cuda.is_available() == False`. Agora `compose.podman.yaml` declara `devices: - nvidia.com/gpu=all`, e o mesmo comando dá `True NVIDIA GeForce RTX 3060 Ti`.
- Armadilha: `/var/run/cdi/` é tmpfs e some no reboot. Regenerar com `sudo nvidia-ctk cdi generate --output=/var/run/cdi/nvidia.yaml`.

## 2026-10-10 — Gerador: casas 11,13,16,18,20,22,23 (cobertura do sintético; NÃO adotado)

- **Achado**: `tab/sintetico.py` sorteava 18 casas distintas (0–10, 12, 14, 15, 17, 19, 21, 24). As casas 11, 13, 16, 18, 20, 22 e 23 nunca eram desenhadas, então o modelo não tinha essas classes (o `13` do ouro v2 não podia sair certo).
- **Mudança**: a lista virou `CASAS_SORTEAVEIS` (0–24, cada casa nova uma vez; as baixas seguem com mais peso). Teste `tests/test_casas_sinteticas.py` (cobre 0–24, mantém as antigas, casas 0–5 ≥ 35%).
- **Distribuição de classes (320 linhas, `montar(seed=1)`)**: antes 6.663 glifos, 20 classes; depois 6.948 glifos, 27 classes. As 7 novas ficam entre 1,96% e 2,33% dos tokens. Casas 0–5: 40,4% → 32,3% dos tokens (continuam as mais comuns; 0 segue no topo, 7,8%).
- **Treino**: GPU (RTX 3060 Ti, via `devices` do compose). Comando oficial, sementes 1, 2, 3 → `artefatos/casas24_{1,2,3}`. Em CPU, 1 época ≈ 0,7 s, mas os pesos de CPU não são comparáveis aos oficiais de GPU, então o treino foi refeito em GPU.
- **Régua `tab.avaliar` (72 glifos, casas 0–7)**: 70/72, 69/72, 70/72 = média **0,968** (amplitude 0,014). Oficiais no mesmo código: 66, 71, 68 = média 0,949 (amplitude 0,069). Diferença dentro do ruído dos oficiais, e a régua não tem as casas novas: **não é ganho medido**.
- **Ouro de vídeo v2 (`comparar_paginas.py`, 493 notas, leitor com o modelo passado por argumento)**:

  | modelo | casas certas (de 493) | inventadas | dois-dígitos certos (de 5) |
  | --- | --- | --- | --- |
  | `casas24_1` | 473 | 24 | 3 |
  | `casas24_2` | 473 | 31 | 3 |
  | `casas24_3` | 480 | 24 | 3 |
  | média casas24 | **475,3** | **26,3** | 3 |
  | `oficial_1` | 470 | 20 | 4 |
  | `oficial_2` | 478 | 26 | 4 |
  | `oficial_3` | 484 | 19 | 4 |
  | média oficial | 477,3 | 21,7 | 4 |

- **Leitura**: o ouro de vídeo **não melhora**; piora ligeiramente nas inventadas (26,3 contra 21,7) e perde um dois-dígitos (o `10` da pág. 12 sai `0` nas 3 sementes). O `13` da pág. 8 continua lido como `1`, mesmo com a classe presente: a fusão de dois algarismos (`_casa_das_partes`, limiar 0,80) não alcança a classe nova. Provável causa: a probabilidade do `10` e do `13` se divide com as novas casas 11 e 13. Não medido.
- **Decisão**: **não troquei o `MODELO_PADRAO`** (continua `artefatos/oficial_3`). Adoção fica para o coordenador, com estes números. Se for adotar, o caminho é corrigir a regressão do `10` antes (medir `p(10)` no token da pág. 12 com e sem as classes novas).
- **Não repetir**: aumentar a cobertura de casas com peso igual a 1 não basta para melhorar a casa de dois algarismos no vídeo; o efeito aparece como troca de probabilidade entre classes vizinhas.
- Gerador: lista oficial de casas volta a ser o padrao; 0-24 so com --casas todas (reprodutibilidade). Padrao = `CASAS_OFICIAIS` (a lista de antes de f76e73ca); `casas24_*` precisam de `--casas todas`.

## 2026-10-10 — Fase 4: arco de ligadura não vira nota (inventadas 21 -> 1; casa e revocação mantidas)

- **Causa das inventadas (olhado, `data/saida/fase4_arco/folha_inventadas.png`)**: das 19 inventadas da
  predição com o ouro de 493 notas, **17 são arcos de ligadura** lidos como algarismo (t1 x4, t3 x6, t5 x3,
  t7 x2, t9 x2); 1 é a faixa cinza do marcador (t7 c2 x1053, altura 0,23 passo); 1 é o `1` do `13` (t8 c3
  x1241; o `13` não é classe do modelo, ver 0006). Os 2 arcos do t10 c1 (x497, x536) batiam com notas `7` e
  `2` do ouro que **não existem no quadro** (`data/saida/fase4_arco/ctx_t10_503.png`): o ouro foi corrigido
  pelo dono no commit `75d714a7` (493 -> 491 notas).
- **Regra (`tab/reconhecer.py`, `ALTURA_MINIMA_ALGARISMO = 0.5`)**: token que o classificador leu como
  algarismo e tem altura < 0,5 passo vira classe `simbolo` (vai para `nao_notas` com o glifo cru, em
  `simbolo_cru`). Sem recuperação de casa de dentro de token baixo. Medido no ouro: arcos 0,23–0,37 passo;
  menor algarismo certo 0,642; p05 0,872. Zero colateral no ouro.
- **Discriminador (defeito confirmado)**: roda antes de `classes` ser preenchido. **Medido e NÃO adotado**:
  movê-lo para depois do loop recupera 4 notas (revocação 0,988 -> 0,996), mas a casa cai de 482/485 para
  482/489 (0,986): 7 casas erradas. Reprova o critério de casa. Fica como está.
- **Números (ouro oficial, 491 notas; `tab.avaliar_video`, predição do snapshot do HEAD)**:

  | variante | entregues | precisão | revocação | inventadas | casa nas casadas |
  | --- | --- | --- | --- | --- | --- |
  | base (HEAD) | 506 | 485/506 = 0,958 | 485/491 = 0,988 | 21 | 482/485 = 0,994 |
  | E1 (só discriminador) | 510 | 489/510 = 0,959 | 489/491 = 0,996 | 21 | 482/489 = 0,986 |
  | **E2 (só altura) — escolhida** | 486 | 485/486 = 0,998 | 485/491 = 0,988 | **1** | 482/485 = 0,994 |
  | E3 (altura + discriminador) | 490 | 489/490 = 0,998 | 489/491 = 0,996 | 1 | 482/489 = 0,986 |

  Com o ouro de 493 notas (antes do commit `75d714a7`), E2 dá revocação 485/493 = 0,984 (base 0,988): as
  2 notas do t10 que o dono retirou passam a contar como perdidas.
- **Oficial (glifo, `tab.avaliar`)**: 66/72, 71/72, 68/72, sem "CONTAGEM MUDOU".
- **Levantamento de alturas (sem nota fora do quadro)**: sky guitar 0 algarismo verdadeiro abaixo de 0,5;
  kimny's guitar: 577 tokens "algarismo" abaixo de 0,5, e na amostra de 40 **nenhum** é algarismo (textura
  de fundo e faixas diagonais: o painel detectado nesse vídeo é lixo); violaodecria: 11 tokens, 4 baixos,
  formas em U sem cara de algarismo. **cifra club e tv cifras: `telas()` não detecta tela nenhuma**, então a
  regra não atinge esses vídeos pelo `tab.video`; não medidos. O limiar relativo à mediana **não foi
  necessário** (nenhum canal com algarismo real abaixo de 0,5 apareceu).
- **Testes**: `tests/test_arco_ligadura.py` (5, sintéticos, classificador falso que lê tudo como `7`): arco
  vira `simbolo`, algarismo normal continua nota, discriminador não devolve arco a algarismo. Gate: `ruff
  check` passa; `pytest tests/` 268 passam; `ruff format --check` falha só em `tab/video.py` (Fase 5, de
  outro agente, não é deste commit).
- **Não repetir**: discriminador movido para depois do loop: troca 4 notas por 7 casas erradas (E1/E3).
- **Limites**: 17 arcos sintéticos de um só vídeo. A altura é a feature que separa aqui; em canal de fonte
  pequena pode não separar (o comentário do gerador cita algarismo de 0,38 passo), e cifra club/tv cifras
  não foram medidos.

## 2026-10-10 — FASE 5 / T5.1–T5.5: tempo por exibição. Estado 33 de 40, tempo falso 0. CA de estado (≥ 38/40) NÃO cumprida; D2 em impasse

- **Comando**: `python -m tab.video "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4" --json data/saida/fase5/mvp.json`
  e `python -m tab.avaliar_video --ouro data/gold/ouro_video/retrato_brasileiro_v2.json --pred data/saida/fase5/mvp.json`
  (2 execuções, saída idêntica). Imagem `quadro`, modelo `artefatos/oficial_3/glifo_sint.pt`, commit do código `desconhecido` no container.
- **Implementação** (`tab/estado.py`, parte nova; `tab/video.py`): cada exibição `[t0,t1]` é lida UMA vez por `tab.leitor.quadros`
  a 6 qps, no recorte da faixa. Três observadores saem da mesma leitura: `posicao` (`detectar_cursor`, largura ≥ 3 px),
  `cor` (algarismo que se destaca: ≥ 5,0 e ≥ 3× a mediana) e `cor_acende` (coluna que subiu de cor desde a amostra anterior, estado
  segue a última que acendeu). Estado = coluna atual; trecho aceito só com ≥ 2 amostras seguidas; passagem termina quando o estado
  volta para trás; onset = 1ª amostra do trecho em cada passagem. Coerência = trocas +1/+2 ÷ trocas. Escolhe o de maior coerência
  com ≥ 3 trocas e cobertura ≥ 0,3; abaixo de **0,9** → `medido: false` com o motivo (números de cada observador).
- **Medido no retrato** (13 telas, 22 exibições, 750 entradas de nota = 486 notas distintas, 618 instantes):
  - **33 de 40 instantes** com o estado certo (acerto 33, tolerância 0, erro 5, json sem tempo 2, **tempo falso 0**); todas as 22 exibições medidas.
  - Observadores isolados contra os mesmos 40 instantes: `posicao` 31/40, `cor` 35/40, `cor_acende` 34/40, escolhido 33/40.
  - Coerência escolhida por exibição: mínimo **0,955**, todas as escolhas certas no ouro (o limiar de 0,9 fica abaixo disso).
- **Leitor × ouro (deslocamento medido, só na régua, em 12 qps)**: δ aplicado aos onsets: −0,4 → 27/40; −0,3 → 33; **−0,2 → 36**; −0,1 → 35;
  0 → 34; +0,1 → 30; +0,2 → 28; +0,3 → 20; +0,4 → 13. Ou seja, o leitor está ~0,15 s atrasado em relação aos rótulos do ouro.
  Não corrigi isso no produto (seria ajustar a saída ao gabarito); fica declarado.
- **Resolução e estabilidade (medido)**: 6 qps / estab. 1 → 32/40; **6 qps / estab. 2 → 33/40 (escolhido, plano)**; 12 qps / estab. 2 → 34/40
  (33 + 1 de tolerância). Em trechos rápidos o marcador fica **uma amostra** por coluna (~0,17 s), então a estabilidade 2 descarta essas
  colunas (`json sem tempo`); mesmo assim 2 é melhor que 1.
- **Causas dos erros (diagnóstico por instante, observador escolhido)**: t=350 (início da exibição: a coluna 246 ainda não tem
  onset; sem coluna afirmada, `json sem tempo`); t=480 (escolhido `posicao` errado, `cor` certo: a escolha por coerência errou
  aqui); t=500 (atraso de ~0,2 s do leitor: no quadro de 500,04 s o marcador ainda não aparece); t=672 (o marcador some de 668 a
  673 s e os três observadores ficam parados; a régua lê o último onset como estado atual, então conta como erro). Em 12 qps o
  diagnóstico dá 34/40 e acrescenta t=408 (uma coluna de diferença, os três observadores). A folha em
  `data/saida/fase5/conferencia/` mostra a coluna do JSON sobre a faixa do marcador em t=260, 462, 538 e 628 (olhada); em t=350
  o JSON não afirma coluna.
- **Sanidade**:
  - `iwaki/10cm ⧸ spring snow ⧸ tab.mp4` (sem marcador): **0 de 22 exibições medidas**; todas com `motivo` ("nenhum observador com trocas e cobertura suficientes ...").
  - `mr. tabs/blind melon … lead only` (AV1): **0 de 46 exibições medidas** com coerência 0,9. `posicao` tem **0 trocas** em todas as telas: o ruído
    de faixa de 1 px não vira tempo de posição. `cor`/`cor_acende` têm coerência 0,50–0,87 e sem ouro para o mr. tabs não as aceito. Com 0,5 essas
    passariam (22 instantes com tempo afirmado, sem conferência).
- **D2 — IMPASSE (números)**: o JSON traz **uma entrada por passagem e exibição** (decisão D2). A régua de notas conta entradas, então:
  - `video.py` HEAD (sem tempo) sobre a árvore atual: precisão **485/486 = 0,998**, revocação 485/491, inventadas **1**, casa 482/485;
  - este código: precisão **485/750 = 0,647**, inventadas **265**, revocação 485/491 (o mesmo número de notas, mais entradas);
  - deduplicar por (tela, corda, x) na régua dá 485/486 (notas idênticas), mas o tempo cai para **22 de 40** se a entrada escolhida for a
    primeira: o tempo precisa das entradas por passagem. **Decisão necessária**: a régua de notas deve contar notas distintas e a de tempo deve usar
    todas as entradas (mudança em `tab/avaliar_video.py`, fora do escopo desta tarefa). Não forcei.
- **CA da Fase 5**: estado ≥ 0,95 → **NÃO** (33/40 = 0,825); tempo falso 0 → **sim**; invariantes (`tab.video.validar_tempo`, testes) → **sim**
  (saída real: `invariantes: ok`); folha de conferência com 6 instantes, olhada → **sim**; métricas de nota da Fase 4 não caírem → **NÃO**, por D2 (acima).
- **Linha de base mudou durante a tarefa** (não é regressão de código meu): `45c839b2` (arco de ligadura não vira nota: inventadas 19 → 1) e
  `75d714a7` (ouro v2, tela 10: 493 → 491 notas). Os números de nota acima são todos sobre a árvore atual.
- **Testes**: `tests/test_tempo_exibicao.py` (20 testes: corridas e estabilidade, passagens, coerência, observadores de cor, escolha do
  observador com motivo, centros e caixas, entradas por passagem, invariantes T5.5). Gate: `ruff check .` ok; `pytest -m "not integration"` 268 passed.
- **Não repetir**: (a) estabilidade 2 com marcador de 1 amostra por coluna não cumpre 0,95; (b) ajuste de δ para o ouro não é ganho de produto;
  (c) deduplicar notas sem preservar o tempo derruba o tempo para 22/40.
- **Não feito**: documento de rodada (`docs/rodadas/`), e o observador de símbolo não tem tempo (`nao_notas` sem `t_ini`).

## 2026-10-10 — FASE 5 (continuação): a causa do atraso era do QUADRO, não do carimbo. Estado 33 → 37 de 40, tempo falso 0

- **Pergunta**: o leitor estava ~0,15 s atrasado em relação ao ouro (a régua fechava com δ = −0,2 s, 36/40). Era carimbo de tempo?
- **Carimbo: NÃO era.** Medido com `ffprobe` e `-copyts` no `retrato brasileiro` (H.264, 30000/1001, `start_time 0`): a passada de `fps` do `quadros()` entrega o quadro mais próximo do instante `t0 + k/qps`, com erro < 1/60 s. Em 245,5 s o quadro de origem é o de 245,512 s.
- **Causa REAL (bug de quadro, `tab/leitor.py::quadros`)**: com recorte de altura ímpar em yuv420p, o `crop` sai com **uma linha a menos** (148, não 149). O `read(tamanho)` assume 149 linhas e desalinha o quadro seguinte; o erro **cresce a cada quadro**. Medido no vídeo sintético do teste (e no retrato): diferença contra `quadro_em` = 4,9 / 2,0 / 6,7 / … / 18,1 nos primeiros quadros; com `format=bgr24` antes do `crop`, **0,0 em todos**. Por isso o `estado` lia faixas deslocadas (e as caixas dos algarismos, no observador de cor).
- **Segunda causa (observador de posição)**: a faixa do marcador do `retrato` tem **saturação mediana 38** (62 em um quadro); o fundo da partitura, 3. O corte `sat > 60` do `detectar_cursor` perdia a faixa clara em vários quadros, e a régua lia a coluna anterior (t = 394, 480, 512 s: a faixa está no quadro de seek, `data/saida/fase5b/quadro_t4_394.00.png`, `quadro_t8_480.00.png`).
- **Terceira causa (carimbo do ONSET, a que o "0,15 s" de fato era)**: o trecho começa na 1ª **amostra de 6 qps** que já mostra a coluna nova, então o início fica até 1/6 s depois da transição. Medido nos 37 rótulos: a coluna rotulada aparece no quadro nativo em +0,00 a −0,6 s do rótulo (ex.: 500,035 s, 288,002 s, 350,002 s). **Conserto**: `tab/estado.py::refinar_inicios` relê os quadros nativos entre a amostra anterior e a atual e põe o início no **PTS do primeiro quadro** em que a coluna aparece.
- **Mudanças** (um commit): (1) `tab/leitor.py`: `format=bgr24` antes do `crop`; (2) `tab/cursor.py`: `detectar_cursor(..., sat_min=60)` (padrão inalterado); (3) `tab/estado.py`: `SATURACAO_MARCADOR = 20` para o observador de posição, `refinar_inicios`; (4) `tab/video.py::medir_exibicao`: usa o refino e monta as passagens dos trechos refinados.
- **Números (ouro `retrato_brasileiro_v2`, `tab.avaliar_video`)**:

  | variante | estado | tempo falso | notas: precisão | revocação | casa |
  | --- | --- | --- | --- | --- | --- |
  | HEAD `89154a8c` | **33/40** (acerto 33, erro 5, sem tempo 2) | 0 | 485/486 | 485/491 | 482/485 |
  | só `format=bgr24` (leitor) | 32/40 | 0 | 485/486 | 485/491 | 482/485 |
  | só refino de onset | 34/40 | 0 | 485/486 | 485/491 | 482/485 |
  | refino + `sat_min=20` (sem bgr) | 37/40 | 0 | 485/486 | 485/491 | 482/485 |
  | **candidato: bgr + refino + sat 20** | **37/40** (acerto 37, erro 3, sem tempo 0) | **0** | **485/486** | **485/491** | **482/485** |

  O conserto do quadro sozinho **piora** 33 → 32 (os quadros desalinhados acertavam por acaso); só junto com o refino e a saturação ele ganha. Por isso a mudança é um commit só.
- **Aceite**: estado **37/40 — CA (≥ 38/40) NÃO cumprida**. Demais itens: tempo falso 0 ✓; notas sem queda ✓ (485/486, 485/491, casa 482/485); `tab.telas` retrato **13/13 e 40/40** ✓; `tab.avaliar` **66/72, 71/72, 68/72** ✓ (`oficial_1/2/3`); sanidade `iwaki`: **0 notas com `t_ini`**, 20 telas sem tempo ✓; `mr. tabs` (AV1): **0 notas com `t_ini`**, 46 telas sem tempo ✓; testes novos: 4 (`tests/test_leitor.py::test_recorte_de_altura_impar_bate_com_seek`, que **falha no HEAD** e passa aqui; 3 em `tests/test_tempo_exibicao.py`: refino até o quadro nativo, trecho sem janela anterior, faixa clara com `sat_min`).
- **Gate**: candidato = HEAD + estes 6 arquivos (cópia exportada em `data/saida/fase5b/mine/`): `ruff check .` ✓, `ruff format --check .` ✓ (69 arquivos), `pytest tests/ -m "not integration"` **276 passed**. A árvore de trabalho do dia tem `tab/painel.py` e `tests/test_painel.py` modificados por outro agente (Fase 7.1, ainda não commitados) que falham no lint (B905, formatação); **não são deste commit**.
- **Causas restantes (medidas, não corrigidas)**:
  - **t = 350 e 500 s**: o rótulo é **no máximo 1 quadro antes** do primeiro quadro em que a coluna aparece (350,000 vs 350,002 s; 500,000 vs 500,036 s). Com `json_atual ≤ t` e tolerância 0, só se resolveria arredondando o tempo para trás: isso é ajuste ao gabarito e **não foi feito**. Limite de precisão desta métrica.
  - **t = 672 s**: o marcador some de 668 a 673 s, e a coluna 1760 (rótulo) **não tem nota no JSON** (perdida na leitura de notas). Não é tempo.
  - **Marcador ausente**: quando o marcador some entre duas colunas, a régua mantém a coluna anterior como estado atual. Isso **afirma** estado sem marcador. O ouro não tem instante "ausente" neste vídeo, então o tempo falso fica 0, mas a regra é frágil. Conserto honesto exige **fim de exibição por coluna** (schema) — fica como próximo passo.
- **Não repetir**: (a) corrigir só o `format=bgr24` no leitor derruba o estado para 32; (b) desalinhamento do quadro não aparece na métrica de notas (que usa `quadro_em`), só no tempo; (c) o teste de recorte precisa de janela de ≥ 10 quadros e limite 0,5 (com limite 1,0 passa no HEAD).
- **Artefatos**: `data/saida/fase5b/` (scripts de medição, `rodada_*.log`, JSONs; `mine/` é a cópia candidata). Não commitados.

## 2026-10-10 — FASE 5 (fechamento do estado): régua aceita o rótulo até 1 quadro antes da coluna. Estado 37 → 39 de 40, tempo falso 0

- **Decisão do dono (2026-10-10, por escrito)**: na régua de tempo, um instante do ouro conta como
  estado certo quando o rótulo cai **até 1 quadro nativo antes** do primeiro quadro que mostra a
  coluna. Não é tolerância para outros erros: coluna errada continua erro, e nada além disso foi
  afrouxado. Usar o fps real do vídeo.
- **Implementação (`tab/avaliar_video.py`)**:
  - nova classe `acerto_quadro` (entra em `estado_certo`, junto de `acerto` e `acerto_tolerancia`);
    `CERTAS_TEMPO` lista as três. A `acerto_tolerancia` antiga (0,2 s, coluna imediatamente
    anterior) **não mudou**;
  - `coluna_que_chega`: o início de cada coluna vai para a **grade de quadros nativos**,
    `round(t_ini * fps) / fps`, e a coluna que chega é a de menor início com
    `t < início <= t + 1/fps`, só na exibição de `t`. Só então a coluna do ouro é comparada;
  - fps: `avaliar(..., fps=)`; o `main` lê do arquivo no acervo por `ffprobe` (`--fps` substitui).
    Sem fps, a regra fica **desligada** e o relatório diz isso (`fps desconhecido`).
- **Por que a grade**: o `t_ini` é um instante de amostragem (`t0 + k/qps`, `refinar_inicios`), não
  o PTS do quadro. Medido com `ffprobe` no `retrato brasileiro` (30000/1001, `start_time 0`): o PTS é
  `k × 1001/30000`. O `t_ini` da coluna 19 em 500 s é 500,042; o primeiro PTS que a mostra é
  500,0334 (quadro 14986), a 0,033 s do rótulo (500,000). Sem alinhar à grade, o erro de 0,042 s
  (acima de 1 quadro, 0,0334 s) deixaria o instante de fora. **Ponto para o dono confirmar**: o
  alinhamento arredonda o início ao quadro mais próximo, dentro de meio quadro; é a definição de
  "primeiro quadro", não uma folga em segundos.
- **Números (ouro `retrato_brasileiro_v2`, predição `fase5b/bgr_refino_sat20.json`, fps 29,97003)**:

  | medida | dcae69d3 (antes) | agora |
  | --- | --- | --- |
  | estado certo | 37 de 40 (acerto 37, erro 3) | **39 de 40** (acerto 37, 1 quadro antes 2, erro 1) |
  | tempo falso | 0 | **0** |
  | notas: precisão | 485/486 | 485/486 |
  | notas: revocação | 485/491 | 485/491 |
  | casa | 482/485 | 482/485 |

  Os dois que passam: t = 350 (rótulo 350,000; início 350,008, na grade 350,0167) e t = 500
  (rótulo 500,000; início 500,042, na grade 500,0334). **t = 672 continua erro**: o marcador some de
  668 a 673 s e a coluna 1760 do ouro não tem nota no JSON (perdida na leitura, não é tempo).
- **Testes** (`tests/test_avaliar_video.py`, 43 no arquivo): rótulo 1 quadro antes passa; 2 quadros
  antes não passa; 1 quadro antes com coluna errada não passa; fps desconhecido desliga a regra;
  início fora da grade cai no quadro nativo.
- **Gate**: `ruff check .` ✓ (`All checks passed!`), `ruff format --check .` ✓ (74 arquivos), `pytest tests/`
  **285 passed, 3 deselected**. Reprodução: `tab.avaliar_video` com o mesmo relatório.
- **CA da Fase 5 (plano, T5 "CA")**: estado certo ≥ 0,95: **cumprida** (39 de 40 = 0,975); tempo
  falso 0: **cumprida**; invariantes no gate: cumpridas nos testes existentes. **Não cumprida**:
  imagem de conferência de 6 instantes em `data/saida/conferencia/` (ainda não feita; olhar antes de
  dar a Fase 5 como fechada).
- **Não repetir**: (a) 0,2 s de tolerância para a coluna anterior não resolve o rótulo antes do
  onset (é outro caso); (b) comparar o rótulo com o `t_ini` cru, sem a grade, reprova 500 s por
  0,0086 s; (c) não aumentar a régua para 2 quadros nem arredondar o rótulo para trás.

## 2026-10-10 — FASE 6: a folha estava certa, o JSON estava 2 a 3 quadros cedo. Conserto no tempo: folha 30 de 30

- **Pergunta**: a folha ou o JSON mentia? **Resposta medida: o JSON.** O quadro desenhado (`quadro_em`) bate com o PTS
  do quadro nativo (seek preciso, ffmpeg) e com o leitor, em todos os 12 instantes. O JSON é que dava o início da coluna
  antes do quadro em que ela aparece. Não é a hipótese (a) (folha errada), nem a (c) (instante colado na transição): a
  transição real estava 74 a 115 ms (2 a 3 quadros) depois do `t_ini` do JSON.
- **Causa (medida)**: o tempo vinha de rótulos de grade calculada (`t0 + k/qps`), não do PTS do quadro lido. Em
  `retrato brasileiro` (30000/1001, `start_time 0`) o amostrador de 6 qps rotulou 449,708 com o conteúdo do quadro
  de 449,783 (coluna 3, quando o quadro de 449,716 ainda mostra a coluna 2). O refino (`refinar_inicios`) só olhava
  até `t_ini + 1 quadro`, e a transição estava fora dessa janela: o erro não podia ser corrigido depois.
- **Números medidos no JSON antigo (`mvp_antes`, `contar.py`, PTS exato)**: 12 instantes da semente 0: itens 4, 5 e 11
  com a faixa na coluna anterior (transições em 449,783; 486,987; 590,657 contra `t_ini` 449,708; 486,875; 590,542).
  Na folha de 30 (semente 1): **22 de 30**. Quase todos os erros são de uma coluna adiantada.
- **Conserto (um commit, 4 arquivos)**:
  1. `tab/leitor.py::quadros_pts`: rotula cada quadro com o PTS que o vídeo declara (`ffprobe`), para cada instante da
     grade o quadro nativo mais próximo, e nunca repete quadro. `quadros` fica intacto (telas, cursor, transcrever,
     ouro e pipeline continuam com a grade antiga, que não foi medida como errada fora do tempo).
  2. `tab/estado.py::ler_amostras` passa a ler por `quadros_pts` (o tempo e o refino herdam o PTS).
  3. `tab/conferir.py`: a folha desenha o quadro de PTS mais próximo de `t` (`quadro_em(t - ½ quadro)`), e não `t + ½`.
     É a checagem mais estrita: com `t` no PTS do primeiro quadro, o quadro de `t + ½` já seria o seguinte.
- **Validação do leitor**: `quadros_pts` na janela 449,2–450,0 s: rótulo = PTS real e quadro igual ao `quadro_em` no
  PTS em **22 de 22**; 3 testes novos em `tests/test_leitor.py` (rótulo = PTS com grade fora do quadro; sem repetição
  com 6 qps em vídeo de 10 fps; `ler_amostras` herda o PTS).
- **Números finais (JSON `data/saida/produto/mvp.json`, código final)**:

  | medida | antes | depois |
  | --- | --- | --- |
  | folha de 30 (semente 1), coluna = faixa | 22 de 30 | **30 de 30** (aceite ≥ 29) |
  | folha de 12 (semente 0), coluna = faixa | 9 de 12 (erram 4, 5 e 11) | **12 de 12** |
  | régua: estado certo (40) | 39 (acerto 37, 1 quadro antes 2, erro 1) | **38** (acerto 37, 1 quadro antes 1, erro 2) |
  | régua: tempo falso | 0 | **0** |
  | notas: precisão | 485/486 | 485/485 |
  | notas: revocação | 485/491 | 485/491 |
  | notas: casa | 482/485 | 483/485 |
  | `tab.avaliar` (oficial_1/2/3) | 66, 71, 68 de 72 | **66, 71, 68 de 72** |

- **O ESTADO NÃO FECHOU o aceite de estado (≥ 39/40): 38/40.** A causa é um instante do ouro, não o código:
  **t = 500 s** (tela 5, coluna x 1061,9 = coluna 19). Medido com PTS exato: o marcador está na coluna 16 (x 982,5)
  até o quadro de **500,0000**, e chega à coluna 19 no quadro de **500,0662** (2 quadros depois do rótulo, não 1).
  O JSON antigo dava 500,042, que estava 1 quadro cedo e passava pela tolerância "1 quadro antes". Com o JSON certo
  (500,066) o rótulo fica 2 quadros antes e reprova. Não afrouxei a régua para 2 quadros (isso é ajuste ao gabarito, e a
  regra é decisão do dono). **Decisão pendente do dono**: o rótulo de t = 500 s está 2 quadros antes do primeiro quadro
  que mostra a coluna. Se o rótulo estiver certo e o vídeo errado, algo no quadro é diferente do que medi; se o rótulo
  for leitura de pouco mais de 1 quadro, a régua precisa de outra decisão explícita. t = 350 s continua "1 quadro antes";
  t = 672 s continua erro (a coluna 1760 não tem nota no JSON, não é tempo).
- **Notas: a mudança de 485/486 para 485/485 e de casa 482 para 483 NÃO vem desta correção.** A correção não toca o
  caminho das notas (`tab/video.py` usa o `estado` só para o tempo). A diferença está em casas de dois dígitos
  (ex.: `13` no lugar de `1` na tela 8, corda 3), e o `tab/reconhecer.py` com esse ajuste é um diff **não commitado de
  outro agente**. O `mvp_antes` foi gerado antes desse diff. Fica declarado como dívida de comparação: a linha de base
  de nota é a do `reconhecer` daquele dia.
- **Gate**: `ruff check .` ✓ (`All checks passed!`, exit 0); `ruff format --check .` ✓ (77 arquivos); `pytest tests/ -q
  -p no:cacheprovider` **317 passed, 3 deselected** (integração), exit 0.
- **Artefatos**: `data/saida/produto/mvp.json` (regenerado), `data/saida/produto/conferencia_mvp.png` (12, semente 0),
  `data/saida/fase6_conf/conferencia_30_semente1.png` (30, semente 1), `data/saida/produto/avaliacao_mvp.json`.
  Diagnóstico (scripts `vizinhos.py`, `medir.py`, `janela.py`, `rotulo.py`, `contar.py`, `validar_pts.py`) em
  `data/saida/fase6_diag/`.
- **Não repetir**: (a) rótulo de quadro pela grade `t0 + k/qps` para tempo; (b) janela de refino só até `t_ini + 1
  quadro`; (c) afrouxar a régua de 1 para 2 quadros para passar 39/40; (d) atribuir a mudança de nota ao tempo.
- **Não feito**: o aceite de estado 39/40 depende da decisão do dono sobre t = 500 s; `docs/rodadas/0004-mvp-video-inteiro.md`
  e a aprovação do dono (CA-10) continuam pendentes.

## 2026-10-10 — Fase 4: casa 13 (par de algarismos sem classe no modelo). Inventadas 1 → 0

Detalhe e tabelas em `docs/rodadas/0008-casa-13-par-de-algarismos.md`. Linha de base: HEAD `b5841c27` (medida em árvore limpa).

- **Causa**: o `13` da tela 8, corda 3 (vão 0,324 passo) era `1` + `3` separados. `_casa_das_partes` exigia a concatenação
  como classe do modelo, e o oficial não tem `13`. O vão não separa (notas distintas vizinhas vão até 0,37).
- **Regra nova** (`tab/reconhecer.py`): casa fora do modelo sai do **par geométrico** de dois tokens isolados quando a
  concatenação está em 10–24 e cada parte tem confiança ≥ `LIMIAR_PARTE_DIGITO` = 0,5. Par com casa possível que não passa
  na leitura segura vai para `nao_notas` com o símbolo cru (não vira nota, não é descartado).
- **Números (ouro v2, `tab.avaliar_video`, árvore limpa em `b5841c27`)**: precisão **485/486 → 485/485** (inventadas 1 → 0);
  revocação 485/491 (igual); casa **482/485 → 483/485**; tempo 39/40 com falso 0 (igual); `tab.telas` 13/13 e 40/40;
  `tab.avaliar` oficial_1/2/3 = **66, 71, 68** (igual ao HEAD). Diferença de notas: só a tela 8, corda 3 (`1`+`3` → `13`).
- **Amostra a amostra dos glifos**: idêntica ao HEAD depois da correção (ver "não repetir").
- **Gate** (árvore limpa = `b5841c27` + os dois arquivos): `ruff check .` e `ruff format --check .` ✓; `pytest tests/` 315 passed, 1 skipped, 3 deselected.
- **Limites**: medido em um vídeo com 6 candidatos a dois dígitos; sem negativos reais de notas distintas com concatenação 10–24 no ouro;
  a regra de "inseguro" muda também pares com casa conhecida e token < 0,80 (antes eram duas notas), sem efeito no ouro nem no gabarito de glifos.
- **Não repetir**: (a) aplicar a casa fora do modelo ao glifo de dois componentes (um `3` virou `20`, −1 no `oficial_3`);
  (b) limiar de vão para separar `13` de notas distintas (ver a Fase 4 acima; não separa).

## 2026-10-10 — MVP APROVADO pelo dono em 2026-10-10

- Frase do dono no chat: "esse mvp ja ta aprovadissimo, só vou passando uns errinhos que to vendo manualmente".
- Pacote: commit `0a3fdcda` (rodada 0004, `docs/rodadas/0004-mvp-video-inteiro.md`) e MusicXML corrigido `c15cd72e`. `transcrever` do vídeo inteiro em 611 s; régua 485/485, 0 inventadas, 485/491, casa 483/485, estado 39/40, tempo falso 0; `tab.avaliar` 66/71/68; gate verde (317 testes).
- Erros apontados pelo dono após a aprovação (em aberto): 6 lido como 5 no compasso 15 (tela 4, corda 5); os dois 0 do acorde 3/0/0/3 da tela 2 perdidos; mordente 2⌒3⌒2 sem interpretação de técnica (cru em `nao_notas`); tempo falso na moldura verde da ilustração de mãos (tela 1, 239,4 s, em conserto).

## 2026-10-10 — Fase 5: marcador falso da moldura verde REJEITADO por aparência (faixa translúcida)

- **Causa (medida)**: `detectar_cursor` (sat 20) achava a moldura verde da ilustração de mãos (x 1206–1217, 12 px, H 49, S 118) como marcador entre ~239 e 244 s do `retrato brasileiro`, e a nota tela 1 col 20 ganhava `t_ini` 239,406. O marcador real tem 44–48 px, H ~109, S ~36.
- **Regra (`tab/estado.py::faixa_translucida`)**: o marcador é tinta translúcida sobre o papel, então cordas e notas aparecem por dentro. Fração de pixels do miolo da faixa mais escuros que a mediana em 40 → exige ≥ 0,02 (`TINTA_MINIMA_FAIXA`). Medido: marcador real do retrato 0,094–0,122 (40 quadros de 245–265 s); moldura sólida 0,000.
- **Números**: `tab.avaliar_video` (ouro `retrato_brasileiro_v2`, `data/saida/fase5_moldura/mvp.json`): notas precisão 485/485, revocação 485/491, inventadas 0, casa 483/485; tempo **39/40** estado certo, tempo falso 0. Tela 1 col 20 agora `t_ini` 257,357. `tab.avaliar` oficial_1/2/3 = 66/72, 71/72, 68/72.
- **Folha `tab.conferir --n 30 --semente 1`**: coluna == faixa em **30/30** (contagem visual, olhando recortes ampliados de 6 em 6, `data/saida/fase5_moldura/zoom_1..5.png`; não é medida automática).
- **Canal com faixa opaca/laranja (asturias)**: 158 detecções com w ≥ 3 em 522–939 s; a faixa laranja (H 12–14, S 91–120, x ~308) mede 0,19–0,45 de tinta, todas aceitas. `mario wonder` (60–300 s): 0 detecções. `configs/canais.yaml` não tem outro canal com faixa sólida. Cifra club usa cor por algarismo, não faixa, então a regra não se aplica.
- **Sanidade**: iwaki 0 notas com `t_ini`. **mr. tabs (AV1): 7 notas com `t_ini` na tela 34 (192–194 s), causa não confirmada, sem ouro; conferir na Fase 8.** Antes desta mudança eram 0. A regra só rejeita x, então o efeito vem de o observador `posicao` mudar; a causa exata não foi testada. A figura `data/saida/fase5_moldura/mrtabs_192_194.png` não serve como prova: a detecção rodou no quadro inteiro e não pegou a faixa, e o JSON não guarda x das colunas.
- **Não repetir**: (a) confiar em `detectar_cursor` sem o miolo da faixa; (b) pensar que a regra só poda — ela muda o observador escolhido; (c) "0 notas com t_ini" no mr. tabs como sinal de sucesso: era por ausência de sinal, e agora há 7.
- **Não feito**: a regra está medida só em retrato brasileiro e asturias; falta medir outros canais com marcador sólido (ex.: os de cor) antes de generalizar.

## 2026-10-10 — Fase 7.1: piloto do censo e painel escuro (teto de passo 45 → 55 px)

**Piloto** (3 vídeos por canal, semente 20261010, 4 instantes por vídeo, contagem pelo olho sobre a folha `data/saida/censo/piloto/folha_<canal>.jpg`):

| | VP | FP | VN | FN | precisão | revocação |
| --- | --- | --- | --- | --- | --- | --- |
| antes (`piloto/`) | 139 | 4 | 53 | 24 | 0,972 | 0,853 |
| depois (`piloto_depois/`) | 141 | 4 | 57 | 18 | 0,972 | 0,887 |

- Efeito **do conserto** nos vídeos comuns: FN → VP em 2 instantes (cifra club `ó vinde adoremos` t=1341, violaodecria `sei que tu me odeia` t=47), zero piora. O +4 VN / −4 FN de `robert lunn` **não é efeito do conserto**: o acervo cresceu e a amostra desse canal trocou de vídeos (os 4 FN antigos saíram da amostra e não foram remedidos).
- **Cifra club**: o painel escuro **não** era rejeitado pelo portão de cor (cinza mediano 26, saturação 0). O bloqueio era o **passo**: as cordas da TAB estão a 52 px e `PASSO_MAXIMO_PX` era 45. O `escolher` achava a faixa do vídeo (topo, uniformidade 0,89), e a faixa da TAB (base, uniformidade 0,97) saía pelo teto. Subido para 55 px (abaixo dos 59 px do texto de acorde do violaodecria).
- A leitura da TAB escura **funciona** (`segmentar` acha 6 cordas e 10 glifos, máscara `contraste_claro`), mas a caixa desse quadro cobre a pauta e a TAB juntas.

**Gabarito de caixa** (`tab.presenca_aval`): com o teto 55, o caso FN05 (sky guitar, t=117,15) ganha caixa **nova** que o gabarito ainda não tem. Medido com rótulo **provisório do agente** (cópia em `piloto/gold_provisorio.json`, NÃO o gabarito do dono): caixa **125/127 = 0,984** (era 124/126), revocação **125/130 = 0,962** (era 124/130). Falta o dono rotular o FN05 em `caixas_revistas`.

**MVP**: `tab.video` retrato → notas 485/485, revocação 485/491, inventadas 0, casa 483/485; tempo 39/40, falso 0; `tab.telas --ouro` 13/13 telas e 40/40 instantes; `tab.avaliar` oficial_1/2/3 = 66/72, 71/72, 68/72.

**Não repetir / limites**: o piloto é de 3 vídeos por canal (amostra pequena); o teto de passo vale para **todos** os canais; `robert lunn black diamond` (4 FN antes, TAB visível) não entrou na amostra refeita e segue sem remedição; TAB em texto ASCII (violaodecria) conta como tablatura no olho.

## 2026-10-11 — Fase 7.1: FN05 rotulado pelo dono e caixa aparada à TAB (aceite de caixa 0,984)

- **Gabarito**: FN05 (sky guitar, t=117,15) tinha a caixa antiga `[62,710,1850,1080]`, que cobria a TAB e a pauta, e foi registrada como `grande_demais=true` (dono, 2026-10-10). Em 2026-10-11 o dono olhou a caixa nova `[62,891,1850,1064]` (`data/saida/fn05/folha_novas.jpg`) e marcou `caixa_sobre_tablatura=true`.
- **Conserto** (`tab/painel.py`, `aparar_pauta`, chamado por `tab/telas.painel_do_quadro`): se a caixa tem 6 linhas fortes regulares (passo 14 a 55) com 5 linhas fortes acima, ela é aparada para ir de 1 passo acima da TAB a 1 passo abaixo. Só estreita; caixa sem pauta em cima fica como estava. Entre os 144 quadros do gabarito, só o FN05 muda de forma.
- **Medição oficial** (`python -m tab.presenca_aval`): caixa **125/127 = 0,984** (era 124/127 = 0,976); revocação de caixa **125/130 = 0,962** (era 124/130 = 0,954); presença VP 127 FP 0 VN 14 FN 3. Erros de caixa restantes: FP02 e FP11 (ver o gabarito).
- **MVP** (medido na cópia com o mesmo código): `tab.telas` retrato 13/13 telas e 40/40 instantes; `tab.avaliar` 66/72, 71/72, 68/72 (iguais ao HEAD); `tab.video` + `tab.avaliar_video`: precisão 485/485, revocação 485/491, inventadas 0, casa 483/485, tempo 39/40, tempo falso 0.
- **Gate**: ruff check e ruff format --check ok; pytest 348 passed (sem integration).
- **Não resolvido**: no FN05 o candidato vem da reserva `escolher_rapido` (faixa `base`) com a grade misturada (linha 786 da pauta mais cordas da TAB, passo 50,6 contra ~24,6 reais). O conserto só corrige a caixa, não a leitura desse quadro.

## 2026-10-11 — Fase 7.1 (cifra club): TAB escura pelo caminho aditivo, e gabarito do dono sobre VN05/VN06/VN12/VN16

- **Causa (medida)**: na TAB escura do `cifra club` (fundo cinza 26, cordas cinza-claras a 0,29-0,31 de tinta), o `escolher` do HEAD não achava as cordas: `candidatos_quadro` juntava os picos de todas as máscaras (quebrando a janela de 6), e `segmentar` procura cordas a fração 0,30. Além disso o portão de cor só olhava o candidato escolhido. Linha de base em 30 instantes rotulados a olho pelo agente: TAB 5/15, falso positivo 0/15.
- **Conserto** (`tab/painel.py`, `tab/telas.py`): aditivo. `painel_do_quadro` roda o caminho do HEAD (`_painel_do_quadro_claro`, sem mudança) e só se ele devolver None entra `_painel_escuro`: grupos de 6 cordas achados só na máscara `contraste_claro`, aceitos com fundo escuro (cinza mediano ≤ 50) e cordas mais claras que o fundo (contraste ≥ 12), depois `_grade_do_grupo` + `criar`. Painel claro nunca chega ao caminho escuro se o do HEAD o achou.
- **Gabarito** (decisão do dono, 2026-10-11, `data/saida/cifra/vn_suspeitos.jpg`): VN05, VN06, VN12 e VN16 têm TAB. Commit `d3b17d38` (gabarito e teste de contrato).
- **Medição oficial** (`python -m tab.presenca_aval`, gabarito novo): caixa **127/129 = 0,984**; revocação de caixa **127/134 = 0,948** (o denominador cresceu de 130 para 134 com VN12 e VN16, que a caixa não cobre; antes 125/130 = 0,962); presença VP 129 FP 0 VN 10 FN 5. Das 144 caixas do gabarito, 142 são idênticas às do HEAD (inclui FN05).
- **Piloto 3/canal** (`tab.censo` do HEAD, semente 20261010, 59 vídeos, 0 erro): nos 39 vídeos em comum com `piloto_depois`, perda (TAB→sem TAB) 0 em todos os canais e ganho 2, ambos `cifra club`. A amostra mudou um pouco (o acervo cresceu: 16 saíram, 20 entraram).
- **MVP** (`tab.telas` retrato, `tab.video` + `tab.avaliar_video`): telas 13/13, instantes 40/40; notas precisão 485/485, revocação 485/491, inventadas 0, casa 483/485; tempo 39/40, tempo falso 0.
- **`tab.avaliar` oficial 1/2/3**: 66/72, 71/72, 68/72 (iguais ao HEAD).
- **Gate**: ruff check e ruff format --check ok; pytest 363 passed (inclui `tests/test_painel_escuro.py`, 4 testes).
- **Não repetir / limites**: o conserto acerta a TAB escura, não a regra de cordas de outro canal. O limiar de fundo (50) e o de contraste (12) foram medidos nos 15 rotulados e nas 144 caixas do gabarito, não num conjunto separado. A TAB escura com cordas sobre vídeo escuro não entrou no `criar` nos quadros medidos, mas não há teste de regressão sobre um acervo grande além do piloto. Rotulagem visual do agente (30 instantes) não é do dono.

## 2026-10-11 — Cache de quadros do censo (T-cache): medido, e a passada densa fica como pendência

- **O que é**: `tab/cache.py` grava em PNG (sem perda) os quadros de presença que o `tab.censo --cache` lê, em `/run/media/gabriel/3014CD4714CD1130/chorinho_cache` (montado em `/cache` no container, leitura-escrita; `/acervo` segue somente leitura). Fora do git (`data/cache/` no `.gitignore`).
- **Equivalência (regra 9)**: piloto 3/canal (59 vídeos) lendo direto do vídeo (`direto`), gravando no cache (`png_frio`) e lendo SÓ do cache (`png_quente`): **59/59 registros idênticos** em todos os campos de decisão (`data/saida/cache_medida/piloto/*.jsonl`).
- **Formato** (`data/saida/cache_medida/formatos.json`, 20 quadros de presença): PNG ~1,34 MB por quadro, identico em todos; WebP sem perda ~0,54 MB mas codifica ~19x mais devagar (0,64 s contra 0,034 s); JPEG q95 ~0,35 MB e **não** é idêntico (reprovado). Adotado: PNG.
- **Passada densa (sonda, 4 vídeos, `data/saida/cache_medida/densa_probe.log`)**: ler por quadros-chave custa 2–5x os 12 seeks (84 contra 21,5 s; 64 contra 21; 78 contra 14; 16,5 contra 8,6 s). Achou 5 trechos com TAB que os 12 instantes perderam num vídeo do `guitar dell'arte`.
- **Decisão do coordenador**: passada densa **NÃO adotada no censo agora** (custo acima de 1,5x). Pendência registrada: passada densa só nos vídeos com `tablatura=false` de canais que têm TAB, depois do censo.
- **Gate** (`make lint` e `make test` equivalentes, no container via podman): `ruff check .` All checks passed; `ruff format --check .` 83 files already formatted; `pytest tests/ -m 'not integration'` 363 passed, 3 deselected.
- **Não repetir / limites**: a sonda densa mediu 4 vídeos, não o acervo. O cache não substitui a medição de equivalência em canais novos; qualquer mudança de recorte ou de decodificação invalida o cache (regra 9).

## 2026-10-11 — violaodecria e tv cifras FORA da Fase 8 (decisão do dono)

- Decisão do dono (2026-10-11, no chat): `violaodecria` (TAB em texto ASCII, contagem inflada) e `tv cifras` (51/537 com TAB no censo parcial) saem do gabarito da Fase 8 e da primeira transcrição em massa. Ver `docs/decisoes/0009-canais-fora-da-fase-8.md`; `configs/canais.yaml` marca `rollout: fora`. O ouro final sai do censo completo; sobram 7 canais, no mínimo do T8.1.

## 2026-10-11 — Fase 7 (T7.1–T7.3): censo completo, tabela por canal, D7 e conferência de 30

**Censo** (`data/saida/censo/censo_cache.jsonl`, 3.813 linhas, 0 erros, sem chave repetida). Fora da tabela: `violaodecria` (478) e `tv cifras` (537), cortados por decisão 0009; ficam só nesta nota. Ativos: **2.798 vídeos, 19 canais**, 269,2 h de vídeo. Por canal, "forma" e "marcador" usam só os vídeos com janela medida (amostra de 30 por canal; n entre parênteses). "TAB estimada" = duração × fração média de instantes com TAB.

| canal | vídeos | com TAB (vídeo) | fração média com TAB | forma (n com janela) | marcador (n com janela) | AV1 | TAB estimada (h) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| sky guitar | 417 | 416 (100 %) | 0,62 | 30: pag 93 % / rol 0 % / fixo 7 % | 30: faixa 100 % / cor 0 % / sem 0 % | 38 % | 25,0 |
| robert lunn | 369 | 344 (93 %) | 0,76 | 27: pag 96 % / rol 0 % / fixo 4 % | 27: faixa 96 % / cor 4 % / sem 0 % | 36 % | 14,7 |
| guitar dell'arte | 361 | 353 (98 %) | 0,48 | 29: pag 55 % / rol 38 % / fixo 7 % | 29: faixa 83 % / cor 17 % / sem 0 % | 41 % | 16,4 |
| cifra club | 341 | 197 (58 %) | 0,28 | 18: pag 89 % / rol 0 % / fixo 11 % | 18: faixa 100 % / cor 0 % / sem 0 % | 96 % | 29,2 |
| leonardo ramos | 298 | 289 (97 %) | 0,86 | 29: pag 48 % / rol 48 % / fixo 3 % | 29: faixa 97 % / cor 0 % / sem 3 % | 23 % | 12,2 |
| kenneth acoustic | 294 | 286 (97 %) | 0,47 | 28: pag 50 % / rol 50 % / fixo 0 % | 28: faixa 100 % / cor 0 % / sem 0 % | 65 % | 8,8 |
| iwaki | 164 | 162 (99 %) | 0,94 | 30: pag 93 % / rol 3 % / fixo 3 % | 30: faixa 7 % / cor 10 % / sem 83 % | 49 % | 7,8 |
| shin izumi | 149 | 148 (99 %) | 0,98 | 30: pag 100 % / rol 0 % / fixo 0 % | 30: faixa 0 % / cor 3 % / sem 97 % | 56 % | 6,0 |
| pablo romé | 123 | 102 (83 %) | 0,37 | 25: pag 92 % / rol 0 % / fixo 8 % | 25: faixa 60 % / cor 36 % / sem 4 % | 14 % | 8,8 |
| kimny's guitar | 108 | 108 (100 %) | 0,93 | 30: pag 97 % / rol 0 % / fixo 3 % | 30: faixa 0 % / cor 3 % / sem 97 % | 26 % | 5,8 |
| ギタロー ⧸ guitarous | 55 | 46 (84 %) | 0,67 | 26: pag 81 % / rol 15 % / fixo 4 % | 26: faixa 85 % / cor 8 % / sem 8 % | 2 % | 1,3 |
| serge kottelat | 38 | 35 (92 %) | 0,84 | 28: pag 100 % / rol 0 % / fixo 0 % | 28: faixa 100 % / cor 0 % / sem 0 % | 79 % | 1,7 |
| transcriptor | 35 | 34 (97 %) | 0,77 | 30: pag 97 % / rol 0 % / fixo 3 % | 30: faixa 17 % / cor 13 % / sem 70 % | 3 % | 2,7 |
| mr. tabs | 22 | 22 (100 %) | 0,91 | 22: pag 18 % / rol 82 % / fixo 0 % | 22: faixa 59 % / cor 41 % / sem 0 % | 91 % | 1,4 |
| paolo d'angelo | 14 | 13 (93 %) | 0,79 | 13: pag 92 % / rol 8 % / fixo 0 % | 13: faixa 85 % / cor 8 % / sem 8 % | 43 % | 0,6 |
| tv on guitar | 5 | 5 (100 %) | 0,97 | 5: pag 60 % / rol 40 % / fixo 0 % | 5: faixa 100 % / cor 0 % / sem 0 % | 100 % | 0,2 |
| lonelypicker | 3 | 3 (100 %) | 0,92 | 3: pag 100 % | 3: faixa 67 % / cor 33 % | 0 % | 0,1 |
| vvxofingerstyletab | 1 | 1 (100 %) | 0,83 | 1: pag 100 % | 1: faixa 100 % | 0 % | 0,03 |
| yunus guitarist | 1 | 1 (100 %) | 1,00 | 1: pag 100 % | 1: faixa 100 % | 0 % | 0,06 |
| **TOTAL** | **2.798** | **2.565 (92 %)** | **0,64** | **405: pag 80 % / rol 16 % / fixo 3 %** | **405: faixa 64 % / cor 9 % / sem 27 %** | **47 %** | **142,8** |

Leitura: a tabela é de **presença por 12 instantes** (fração média) e de **janela** (forma e marcador); o TOTAL de forma/marcador vale só para os 405 vídeos com janela, não para o acervo. `cifra club` aparece com 58 % de TAB: é o número do censo, não revisado aqui. Canais com n < 10 (`lonelypicker`, `vvxofingerstyletab`, `yunus guitarist`, `tv on guitar`) não servem para proporção.

**D7 (rolagem), respondida com o número do censo**: 65 dos 405 vídeos com janela medida têm forma **rolante** (16 %), em 8 canais (`leonardo ramos` 14, `kenneth acoustic` 14, `mr. tabs` 18, `guitar dell'arte` 11, `ギタロー` 4, `iwaki` 1, `paolo d'angelo` 1, `tv on guitar` 2). Estimativa para o acervo ativo, taxa medida por canal × TAB do canal: ~450 de 2.798 vídeos (16 %). Como o limiar do plano é ≥ 10 %, **D7 = sim**: T8.4 entra no escopo. Ressalva: a classificação "rolante" não foi conferida (ver abaixo; a folha de 30 não sorteou nenhum vídeo rolante).

**T7.3 conferência de 30** (semente 20261011; estratificado: 1 por canal com ≥ 10 vídeos, o resto proporcional; 15 canais, 21 com TAB e 9 sem). Folhas: `data/saida/censo/conferencia_30_1.jpg`, `_2.jpg`, `_3.jpg` (10 vídeos cada); manifesto `data/saida/censo/conferencia_30.json`. Contagem do agente, olhando as folhas: **concorda em 26, discorda em 3, dúvida em 1**; concordância ~87 %, abaixo dos 90 % do CA.
- Discorda: **14** (`leonardo ramos`, "pajas blancas"): censo SEM; a TAB com números aparece nos dois quadros.
- Discorda: **21** (`robert lunn`, "cavatina"): censo SEM; há pauta com números de TAB sobreposta no quadro.
- Discorda: **27** (`sky guitar`, "el condor pasa"): censo SEM; o 2º quadro (121 s) tem TAB.
- Dúvida: **10** (`kenneth acoustic`, "ain't no sunshine"): folha vertical com números pequenos; não consegui afirmar.
- Os demais 26 concordam com a presença. Marcador e forma só foram olhados onde a folha mostra (faixa/cor visíveis em alguns); a rolagem não foi testada.
- Pelo plano (T7.3), concordância < 90 % exige conserto do classificador de presença antes de seguir. **Não feito nesta rodada**: a conferência oficial é do dono.

**Não repetir / limites**: a tabela usa só a presença do censo (12 instantes, janela em até 3). O censo ainda não lê TAB em vídeo vertical (caso 10) e pode perder TAB que aparece só nas bordas de 12 instantes (regra 10). Rolagem e marcador não estão validados.

## Mãos — 2026-10-12 — M0: censo de mãos (2.798 vídeos, 12 quadros cada)

Rodada completa: [`docs/rodadas/1001-censo-de-maos.md`](docs/rodadas/1001-censo-de-maos.md). Imagem: [decisão 1001](docs/decisoes/1001-imagem-derivada-maos.md).

**Medido**: MediaPipe (mãos) e YuNet (rosto) em 33.576 quadros (12 por vídeo, 0 faltando) de 2.798 vídeos de 19 canais, em 2.907 s com 6 processos, só CPU. 57.484 mãos detectadas; 419 (0,7 %) descartadas pela regra da TAB. Configuração adotada no piloto (36 vídeos, 2 por canal): confiança 0,3 e blocos 2×2, com 32 de 36 quadros certos (provisório, agente). Determinismo: 36 de 36 vídeos.

Tabela por canal, copiada de `data/saida/maos/censo_maos.log`. Legenda das colunas na rodada.

| canal | vídeos | quadros | alguma mão | 2+ mãos | 2+ mãos nos quadros com TAB | vídeos que servem | L | R | L e R | > 2 mãos | rosto / sem rosto / sem mão | palma / altura |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sky guitar | 417 | 5004 | 97 % | 94 % | 95 % (2936/3086) | 416 (100 %) | 94 % | 96 % | 93 % | 2 % | 0 % / 97 % / 3 % | 0.142 |
| robert lunn | 369 | 4428 | 85 % | 42 % | 41 % (1374/3370) | 161 (44 %) | 52 % | 67 % | 34 % | 1 % | 7 % / 78 % / 15 % | 0.131 |
| guitar dell ́arte | 361 | 4332 | 91 % | 66 % | 70 % (1447/2066) | 316 (88 %) | 78 % | 77 % | 64 % | 1 % | 3 % / 88 % / 9 % | 0.172 |
| cifra club | 341 | 4092 | 97 % | 72 % | 81 % (917/1126) | 308 (90 %) | 78 % | 81 % | 63 % | 3 % | 16 % / 81 % / 3 % | 0.114 |
| leonardo ramos | 298 | 3576 | 94 % | 84 % | 88 % (2722/3079) | 296 (99 %) | 86 % | 91 % | 82 % | 1 % | 1 % / 94 % / 6 % | 0.134 |
| kenneth acoustic | 294 | 3528 | 99 % | 88 % | 89 % (1486/1672) | 290 (99 %) | 96 % | 90 % | 87 % | 0 % | 0 % / 99 % / 1 % | 0.118 |
| iwaki | 164 | 1968 | 100 % | 97 % | 97 % (1803/1853) | 164 (100 %) | 96 % | 97 % | 93 % | 1 % | 1 % / 99 % / 0 % | 0.109 |
| shin izumi | 149 | 1788 | 100 % | 97 % | 98 % (1725/1761) | 147 (99 %) | 89 % | 96 % | 85 % | 3 % | 1 % / 98 % / 0 % | 0.080 |
| pablo romé | 123 | 1476 | 94 % | 82 % | 93 % (508/547) | 115 (93 %) | 87 % | 86 % | 79 % | 4 % | 54 % / 44 % / 3 % | 0.093 |
| kimny's guitar | 108 | 1296 | 68 % | 17 % | 18 % (210/1200) | 13 (12 %) | 27 % | 56 % | 15 % | 0 % | 0 % / 68 % / 32 % | 0.159 |
| ギタロー ⧸ guitarous | 55 | 660 | 96 % | 91 % | 94 % (417/445) | 50 (91 %) | 90 % | 92 % | 86 % | 12 % | 0 % / 95 % / 4 % | 0.138 |
| serge kottelat | 38 | 456 | 76 % | 57 % | 61 % (235/384) | 24 (63 %) | 59 % | 67 % | 51 % | 3 % | 60 % / 21 % / 19 % | 0.056 |
| transcriptor | 35 | 420 | 74 % | 64 % | 66 % (214/323) | 23 (66 %) | 68 % | 69 % | 63 % | 2 % | 14 % / 61 % / 25 % | 0.106 |
| mr. tabs | 22 | 264 | 95 % | 76 % | 77 % (186/241) | 20 (91 %) | 77 % | 93 % | 74 % | 3 % | 1 % / 94 % / 5 % | 0.123 |
| paolo d'angelo | 14 | 168 | 98 % | 82 % | 82 % (108/132) | 14 (100 %) | 80 % | 97 % | 79 % | 2 % | 1 % / 97 % / 2 % | 0.165 |
| tv on guitar | 5 | 60 | 97 % | 85 % | 88 % (51/58) | 5 (100 %) | 85 % | 97 % | 85 % | 2 % | 0 % / 97 % / 3 % | 0.104 |
| lonelypicker | 3 | 36 | 64 % | 56 % | 55 % (18/33) | 2 (67 %) | 47 % | 61 % | 44 % | 0 % | 0 % / 64 % / 36 % | 0.090 |
| vvxofingerstyletab | 1 | 12 | 83 % | 75 % | 90 % (9/10) | 1 (100 %) | 83 % | 75 % | 75 % | 0 % | 0 % / 83 % / 17 % | 0.160 |
| yunus guitarist | 1 | 12 | 100 % | 100 % | 100 % (12/12) | 1 (100 %) | 100 % | 100 % | 100 % | 0 % | 0 % / 100 % / 0 % | 0.125 |
| **TOTAL** | 2798 | 33576 | 93 % | 75 % | 77 % (16378/21398) | 2366 (85 %) | 80 % | 84 % | 70 % | 2 % | 7 % / 86 % / 7 % | 0.128 |

**Leitura** (do coordenador; não é medida nova):
- mãos em 93 % dos quadros e rosto em 7 %: enquadramento típico de tronco cortado ou close do braço. Pesa a favor de detector específico de mão;
- palma mediana 0,128 da altura do quadro; o menor é `serge kottelat`, 0,056;
- número baixo não é canal sem mão: `kimny's guitar` (17 % com 2+ mãos) é preto e branco escuro; `robert lunn` (42 %) mistura close, corpo inteiro e partitura;
- a tabela é um piso: os erros observados são de perder mão.

**Conferência de 30** (semente 20261013, excluindo o piloto):
- provisório (agente): cerca de 25 de 30 (83 %) com esquerda e direita certas. Critério de 90 %: **não fechado**;
- dono (2026-10-12): confirmou o erro do 04 (mão esquerda em close, não achada). Pendentes: 03, 06, 12 e 17;
- dono (2026-10-12): seguir para o M1 com o censo neste estado.

**Não repetir**:
- pose do MediaPipe para dizer "tem rosto": inventa rosto em close de mãos (5 de 12 no `sky guitar`);
- blocos 3×3 na fusão por score: pioram (25/36 contra 28/36; 24/36 contra 32/36);
- rótulo L/R do MediaPipe para a mão do braço visto de costas: troca o lado;
- regra "mão com centro dentro da caixa da TAB é desenho": apaga mão real quando a caixa da TAB está errada. Auditoria pendente.

**Pendências**: auditoria da regra da TAB (419 mãos); confirmação do dono nos quadros 03, 06, 12 e 17; para a trilha tablatura (via dono), o braço do violão marcado como TAB em closes do `guitar dell'arte` e do `leonardo ramos`.

## Mãos — 2026-10-12 — M1: detector de mãos (Wholebody GPU + MediaPipe)

Rodada: [`docs/rodadas/1002-escolha-do-detector.md`](docs/rodadas/1002-escolha-do-detector.md). Decisão: [1002](docs/decisoes/1002-detector-de-maos.md). Imagem: `chorinho-maos:dev` ([decisão 1001](docs/decisoes/1001-imagem-derivada-maos.md)).

**Decisão do dono (2026-10-12)**: detector = RTMPose Wholebody (RTMW-DW-X-L, **na GPU**) como base, com MediaPipe como complemento. Mão do Wholebody com média dos 21 scores acima de 0,4; complemento só com mão do MediaPipe fora da TAB e com sobreposição menor que 0,3 com toda mão aceita.

**Medido** (validação fora do ajuste, 90 quadros; rótulo **provisório (agente)**; o limiar 0,4 foi escolhido nesses mesmos 90):

| detector | quadro certo | mão esquerda | mão direita | falsas |
| --- | --- | --- | --- | --- |
| MediaPipe (censo M0) | 72/90 | 70/86 | 75/79 | 1 |
| Wholebody 0,5 | 81/90 | 79/86 | 77/79 | 3 |
| Wholebody 0,4 | 84/90 | 84/86 | 78/79 | 3 |
| Wholebody 0,4 + MediaPipe (**adotado**) | 86/90 | 86/86 | 78/79 | 3 |

- Só nos 60 novos: MediaPipe 47/60; Wholebody 0,4, 58/60; combinação, 59/60.
- Erros que sobram (4): C03 (mão direita borrada, não achada); C04, C17, N09 (close de uma mão só, com falsa mão direita).
- Piloto (36 quadros, ajustado no MediaPipe): Wholebody 0,5 deu 36/36 em CPU, 0,53 s por quadro. O censo do piloto, com a imagem nova, segue 36/36.
- GPU: 0,20 a 0,22 s por quadro, com o MediaPipe incluído; duas execuções byte a byte iguais. A validação de 90 rodou na GPU (a trava CUDA impede CPU). Não misturar com números de CPU.
- Reavaliação offline da combinação atual (`data/saida/maos/m1/reavaliar_sem_honestidade.py`): 86/90, reproduzido.

**Regra de honestidade REPROVADA**: "esquerda e direita da mesma pessoa, com sobreposição ≥ 0,5, viram `incerto`". A regra não ganhou nenhum quadro (C04 e N09 trocaram a mão direita falsa por perder também a esquerda verdadeira, que virou `incerto`) e perdeu 2 (C08, N25): **84/90 contra 86/90**. Removida. Não ajustar nos mesmos 90 quadros.

**Não repetir**:
- Chamar o `Wholebody` com detector vazio: a pose roda no quadro inteiro e inventa pessoa e mão;
- `onnxruntime-gpu` sem o `LD_LIBRARY_PATH` do torch cai em CPU calado (a trava `_travar_cuda` aborta);
- `rtmlib` com dependências puxa `opencv-contrib-python` sobre o cv2 da base: instalar com `--no-deps`;
- regra de honestidade por sobreposição (reprovada, acima);
- Wholebody sozinho com limiar 0,5 nos 90 quadros: 81/90 (0,4 deu 84/90).

**Pendências**:
1. Gabarito de pontas e de dedo para o M2 (dono);
2. falsa mão direita em close de uma mão só (3 de 90): sem regra;
3. rótulo da validação é do agente (provisório); confirmação do dono ou conjunto novo com rótulo do dono **a medir**;
4. limiar 0,4 fora do ajuste: escolhido nos mesmos 90 quadros; número fora do ajuste **a medir**;
5. tempo em vídeo inteiro e no acervo (2.798 vídeos) **a medir**.

**Artefatos**: `docs/rodadas/1002-escolha-do-detector.md`; `docs/decisoes/1002-detector-de-maos.md`; código `tab/maos_detector.py`, `tab/maos_combinar.py`, `Dockerfile.maos`; validação `data/saida/maos/m1/detector_validacao.jsonl` e `rotulo_agente_validacao.json`.

## Tablatura — 2026-10-12 — censo: painel por máscara (TAB de fundo rosa, transparente, escuro)

Caminho **aditivo** em `tab/painel.py` (`candidatos_por_mascara`) e `tab/telas.py` (`_painel_por_mascara`): só roda quando os caminhos claro e escuro do HEAD não acham nada; `escolher` intacto. Gabarito de presença: VN09/10/11 passam a `tablatura_no_quadro=true` e entram 7 `caixas_revistas` (decisão do dono, 2026-10-12, registrada em `como_foi_rotulado`).

**Medido**:
- presença (gabarito do dono): precisão de caixa **134/136 = 0,985** (erros FP02, FP11, já conhecidos), revocação **134/137 = 0,978** (antes 0,948); presença por quadro VP 136, FP 0, VN 7, FN 1 (FN02);
- MVP sem mudança: 485/485, 485/491, casa 483/485, tempo 39/40, tempo falso 0; oficial 66/71/68 (0,949);
- piloto (`--piloto 3`, 38 vídeos em comum com o piloto antigo): **11 SEM→TAB, 0 TAB→SEM**; olhado à mão, presença certa nos 11, caixa certa em 9 (#05 kimny's guitar: caixa no braço do violão; #10 transcriptor: caixa na partitura, TAB logo abaixo).

**Pendências**: caixa no braço do violão (caso 4 da conferência e #05 acima); caixa na partitura em vez da TAB (#10); FP08; casos 10/14/21/27 a reconferir no censo refeito por `--so-cache`.

**Artefatos**: `data/saida/conserto_v2/` (MVP, oficiais, piloto, `piloto_mudaram.jpg`).

## 2026-10-12 — Mãos — M2: gabarito de dedos do dono

Rodada completa: [`docs/rodadas/1003-gabarito-de-dedos.md`](docs/rodadas/1003-gabarito-de-dedos.md). Gabarito: `data/gold/maos/dedos_retrato_brasileiro.json` (formato 3). Vídeo: `sky guitar/retrato brasileiro - tab & lesson.mp4` (MVP).

**Medido (rotulado pelo dono, 2026-10-12)**: 40 ataques e 56 notas (amostra de 40 sorteios, semente 20261012, estratificada no tempo). Esquerda: 1 = 14, 0 = 13, 2 = 10, 3 = 8, 4 = 8, ? = 3. Direita: p = 17, a = 16, m = 10, i = 10, ? = 3. Pestana: sim 6, não 33, ? 1.

**Confiabilidade**: esquerda alta; **direita PARCIAL** (parte inferida pelo dono; só indicativo). `n19` excluída (o dono disse que a casa 3 da corda 3 não está sendo apertada); `a22` duplica `a21`.

**Lição**: três defeitos da ferramenta foram achados pelo dono no uso (marcava a coluna inteira; perguntava uma nota só do acorde; pestana não preenchia o dedo nem avançava). Testar a ferramenta com acorde e pestana antes de entregar.

**Commits**: `9ba059ce` (ferramenta), `423b9011`, `b4461d45`, `7be3a880`, `561028ca` (correções), `9fa22548` (gabarito rotulado).

## 2026-10-12 — Mãos — M3: nota → dedo (esquerda)

Rodada completa: [`docs/rodadas/1004-dedo-por-visao.md`](docs/rodadas/1004-dedo-por-visao.md). Gabarito: [rodada 1003](docs/rodadas/1003-gabarito-de-dedos.md).

**Medido**: 53 notas na conta, 40 pisadas, mesmo gabarito para todos os métodos (sem conjunto separado). Acerto total (pisadas entre parênteses):

- `regra_posicao_janela_1` (só tablatura, base): 36/53 (23/40)
- `visao_ponta`: 42/53 (29/40)
- `visao_ponta_voto`: 43/53 (30/40)
- `visao_ou_regra`: 44/53 (31/40)

Calibração do braço (`data/saida/maos/m3/braco.json`): 6 cordas, rms 0,37 a 0,58 px; trastes 0 a 14 (13 de 14 achados); razão 0,949 contra 0,944 teórica; câmera fixa, deriva máxima 4,0 px.

**Ordem das cordas**: a primeira versão (brilho ao contrário) acertou 32/53. O erro apareceu num diagnóstico contra o gabarito. A correção vem da geometria (câmera frontal, mão por baixo do braço) e é conferida pelo brilho (90 a 176 da corda 1 à 6). Ela foi feita depois de ver o gabarito.

**Ressalvas**: um vídeo só; tudo escolhido no mesmo gabarito; câmera de braço frontal e fixa é caso favorável; direita fora de escopo.

**Commits**: `4183fe1e` (avaliador e linha de base), `18ff0890` (visão; gate 562 testes passando).

**Não repetir**:
- (a) brilho para ordenar cordas de NÁILON: os bordões revestidos são os mais claros, não as primas;
- (b) "um dedo por casa" como modelo único da esquerda: teto baixo (9 de 17 erros são formas de acorde);
- (c) entregar ferramenta de rótulo sem testar com acorde e pestana.

## 2026-10-12 — Mãos — M3: abrangência da visão (um vídeo só)

A calibração do braço usa **coordenadas fixas do retrato brasileiro** (não acha a câmera do braço). Medido sem rótulo em 30 vídeos sorteados: calibra em 2/20 do `sky guitar` e 0/10 de outros canais (conferido na imagem; 0 falso sucesso). Os 44/53 da rodada [1004](docs/rodadas/1004-dedo-por-visao.md) valem só para este vídeo. Próximo: achar a região do braço a partir da mão esquerda detectada.

**Não repetir**: revisar método de visão sem procurar coordenada fixa no código.

## 2026-10-12 — Mãos — M3: região do braço pelas pontas da mão (reprovada)

Região do braço derivada das pontas da mão esquerda, sem coordenada fixa: MVP igual (53/53 decisões idênticas), abrangência **0/30** (antes 2/30). A região cai em partitura, corpo ou mão. Código revertido; diff em `data/saida/maos/m3/abrangencia_v2/regiao_pelas_pontas.patch`. Detalhes na rodada [1004](docs/rodadas/1004-dedo-por-visao.md). Próximo: gabarito do braço (M3b, decisão [1003](docs/decisoes/1003-fases-das-maos.md)).

**Não repetir**: achar o braço só pela posição da mão (a mão pode estar sobre partitura ou corpo no quadro).

## 2026-10-12 — Mãos — M3b: gabarito do braço e geometria (dono)

Gabarito do braço do dono: 20 quadros, 8 canais (`data/gold/maos/braco.json`, rodada [1005](docs/rodadas/1005-gabarito-do-braco.md)). **Regra das 12 notas + ângulo da câmera (ideia do dono), medida nas marcações**: com nut + trastes 5 e 12 e modelo projetivo 1D, 96,0 % de 327 trastes previstos a < 1/4 de casa (afim: 65,4 %). **Detector por segmentos de reta (LSD) reprovado**: teste por canal (3 canais, 8 quadros) achou o braço em 1/8, trastes com número certo 1/147; a tablatura vira braço.

**Não repetir**: procurar o braço como "família de retas paralelas" no quadro inteiro (a tablatura e a pauta têm a mesma assinatura).

## Tablatura — 2026-10-12 — censo v2 (com painel por máscara), refeito do cache

`python -m tab.censo --cache --janelas-por-canal 30`, em 6 processos paralelos por grupo de canais (`data/saida/censo/v2/paralelo.sh`; ~20 s/vídeo em série, só 1 núcleo usado). Sobreviveu a um reinício do PC retomando pela chave. Saída única: `data/saida/censo/v2/censo_v2_completo.jsonl` (2.998 vídeos ativos, 0 com erro; 1.162 linhas de erro `Errno 107` do acervo desmontado no reinício foram refeitas e descartadas).

**Medido** (canais ativos):

| | censo antigo | censo v2 |
| --- | --- | --- |
| vídeos | 2.798 | 2.998 (+199 kenneth, +1 leonardo, novos no acervo) |
| com TAB | 2.565 (91,7%) | 2.814 (93,9%) |
| "sem TAB" | 233 | 184 |
| horas-equivalentes de TAB | 142,8 | 171,3 |

- Em 2.798 vídeos comuns: **TAB→SEM 0** (vídeo e instante); SEM→TAB 51 vídeos, 3.287 instantes (kenneth 1.588, dell'arte 686, robert lunn 398, leonardo 212, …).
- Precisão dos instantes novos (leitura visual, rótulo provisório, não do dono): amostra espalhada 36/40; **cifra club 4/16** (8 no braço, 3 em legenda, 1 no painel de batida); guitar dell'arte 38/40 (2 no braço); kenneth 20/20.
- Largura da caixa não separa erro de acerto: kenneth tem 377 instantes novos com caixa < 0,5 da largura e acertou 20/20.

**Pendências**: falso positivo no braço do violão pelo caminho da máscara (cifra club sobretudo; os 6 vídeos de cifra club que viraram TAB são suspeitos, exceto "you know i'm no good"); folhas para virar gabarito, se o dono confirmar: `data/saida/censo/v2/cifra_todos.jpg`, `dellarte_amostra_*.jpg`, `kenneth_amostra.jpg`, `mudaram_sem_para_tab_*.jpg`.

## 2026-10-12 — Mãos — M3c: braço calibrado pela música

Rodada [1006](docs/rodadas/1006-braco-calibrado-pela-musica.md). Homografia do braço ajustada por RANSAC só com (corda, casa, instante) do produto e as pontas da mão esquerda, sem linha da imagem. MVP: inliers 465/526; contra a calibração feita à mão, 0,119 casa de erro mediano (p90 0,241; corda 1 sistemática); dedo **40/53 (27/40)** com a calibração excluindo os instantes do gabarito (42/53 com todos; à mão: 42/53). H instável entre sementes (mediana 4–6 px). Próximo: estabilizar e medir fora do MVP contra o gabarito do braço.

## 2026-10-12 — Mãos — M3c: braço pela música estabilizado (adotado)

Rodada [1007](docs/rodadas/1007-braco-pela-musica-estabilizado.md). Consenso de 10 sementes + refino por reprojeção: grade estável (mediana 0,027 px entre execuções; 1,07 px sem os instantes do gabarito). **Dedo 42/53 (29/40) sem os instantes do gabarito**, igual à calibração feita à mão. Contra o gabarito do dono (q02): trastes 14/14 a < 1/4 de casa (0,032 casa), nut 0,036 casa; cordas ainda erram (0,11 do vão na corda 1). Correção das cordas pela imagem (janela por corda): não adotada, frágil.

**Não repetir**: procurar cada corda numa janela própria (as primas têm contraste fraco e a janela corta o pico); atribuir as 6 juntas por espaçamento.

## Tablatura — 2026-10-13 — Fase 8 (T8.1): ouro v2 inicial de 7 vídeos novos

Escolha aprovada pelo dono (2026-10-12), 1 vídeo por canal, pelo censo v2 (`data/saida/fase8/candidatos.json`, folhas `folha_<canal>.jpg`); cifra club fora (falso positivo de presença), rolantes (leonardo ramos, mr. tabs) esperam o formato da T8.4.

`python -m tab.ouro_video completar VIDEO --ouro-v2 data/gold/ouro_video/<slug>.json --saida data/saida/ouro_video/<slug>/` agora aceita vídeo **sem ouro v1**: páginas do `tab.telas` com as notas do modelo (todas `conferida: false`), 40 instantes sorteados dentro da presença (semente 0, grade 2 s) com a página **sugerida** pelo tempo (`pagina_sugerida: true`: viés de confirmação registrado), tela de borda a borda (o painel do `tab.telas` vinha parcial em 2 de 7), painel refeito só na faixa do `tab.telas` quando o quadro inteiro escolhe o braço do violão, página sem painel descartada e listada. `servir --host` para expor a porta do container. O caminho v1→v2 não mudou.

| vídeo | páginas | notas do modelo | instantes |
| --- | --- | --- | --- |
| guitar dell'arte, South American Music | 7 (1 descartada; 5 são o braço do violão, falso positivo do `tab.telas`) | 168 | 40 |
| robert lunn, Gymnopédie no.1 | 12 | 179 | 40 |
| iwaki, La Vie en Rose | 8 | 423 | 40 |
| kenneth acoustic, End of Beginning | 22 | 624 | 40 |
| shin izumi, Room 335 | 42 | 998 | 40 |
| pablo romé, Greensleeves | 4 | 90 | 40 |
| kimny's guitar, From This Place | 5 | 389 | 40 |

Gate: ruff ok, 620 testes (fora 2 arquivos não rastreados da trilha mãos, um deles com 1 falha da outra sessão). **Pendências**: rotulagem do dono (~2.870 notas no total; shin izumi sozinho tem 998); casas > 7 não aferidas (gymnopédie, room 335, from this place); iwaki/shin izumi/kimny sem marcador: instantes quase todos "nenhuma acesa".

## Áudio — 2026-10-13 — A0: áudio em cache e sincronia (rodada 2001)

- `tab/audio_extrair.py`: FLAC mono 16 bits 22 050 Hz em `/cache/audio/`, chave do censo; `indice_de`/`instante_de` convertem o PTS do vídeo em amostra.
- **`t_amostra0` = 1º frame de áudio decodificado**, não o `start_time`: com Opus o `start_time` erra **~7 ms** (pré-salto). Teste sintético de clique: erro ≤ 1,1 ms em PCM/AAC/Opus, áudio deslocado 0 e 0,5 s.
- 20 vídeos (2 por canal, 10 canais): **20 de 20** extraídos, **Opus em 20 de 20**, deslocamento áudio−vídeo **0 ms em 20 de 20**, nenhum buraco que mude a duração; 1,7 s por vídeo (mediana), 82 MB de FLAC por hora. Projeção (estimativa): ~2,2 h de HD e ~24 GB para 2.998 vídeos.
- **Não repetir**: usar o `start_time` do stream de áudio como instante da amostra 0 (−7 ms em todo o acervo Opus).

## Áudio — 2026-10-13 — A1: atraso marcador → som no MVP (rodada 2002)

- `tab/audio_onsets.py` (STFT 2048/256 a 22 050 Hz, fluxo espectral) e `tab/audio_atraso.py`: 636 eventos de coluna do MVP, ataque mais próximo em janela de meia-distância (teto ±0,30 s), 2 passadas.
- **O marcador vem ANTES do som**: Δ = t_som − t_marcador, fluxo, passada 2: ataque em **636 de 636**, mediana **139 ms**, p10 60, p90 268. Sem capotraste (transposição pela música: k = 0).
- **Degrau, não deriva**: mediana por exibição 79–125 ms até ~448 s (10 exibições) e 164–277 ms depois (12 exibições), inclusive na 2ª exibição de telas já vistas. Causa não medida.
- Viés do detector no sintético: −28 ms (pico antes do ataque); o fluxo nas alturas não separa 1 semitom com N_FFT 2048 (razão 0,98). Os dois testes ficam `xfail` estrito com o número.
- **Não repetir**: usar `t_marcador + atraso fixo` como verdade de tempo do som neste vídeo (degrau de ~110 ms e dispersão de 60–100 ms).

## Tablatura — 2026-10-13 — Fase 8: primeiro vídeo fora do sky guitar (pablo romé, Greensleeves) e régua de tempo

Ouro do dono: 4 páginas, 106 notas, 40 instantes (commit `9f5a62c8`). Medida (`data/saida/fase8/medida/`; 2 execuções do `transcrever` idênticas):
- notas: precisão **88/90**, revocação **88/106**, casa **88/88**, telas 4/4. As 18 perdidas são glifos lidos como símbolo (`nao_notas`): 14 são o algarismo **1** saindo como `harmonico` com casa recuperada 4; 2 inventadas na borda direita (casa 8, fora de 0–7);
- tempo: **1/40 com a régua antiga, 20/40 com a nova**; tempo falso 0. MVP sem mudança (39/40; 38 cliques movidos para o x exato da coluna, todos já dentro da tolerância antiga).

**Régua** (`tab/avaliar_video.py::coluna_do_ouro`): neste canal o marcador é um cursor fino **antes** da coluna, e o dono clica no cursor (~17 px à esquerda do centro dos algarismos, passo 24; tolerância era 0,5 passo). O clique agora vai para a coluna de notas do ouro mais próxima, se a até 1 passo; relatório traz `colunas_ajustadas` (Greensleeves 27 de 40). Não muda nenhum rótulo.

**Pendências (T8.3)**: o `1` deste canal lido como harmônico; 17 erros de tempo + 3 sem tempo (primeiras colunas de cada sistema; coluna cujo único token numérico não tem `t_ini`).

## Áudio — 2026-10-13 — A1b: o "degrau" de 448 s não é degrau (rodada 2003)

- **Corrige a seção A1 acima**: não há degrau único. Descartados por medição: troca de observador, andamento diferente (razão som/marcador **1,0017** em 614 intervalos), pausa só na troca 6→7 (a mediana das 21 trocas é −36 ms) e corte de edição (o único pico de imagem em 444–453 s é a troca de página; o áudio não tem descontinuidade).
- O Δ é quase constante dentro de cada página, mas o nível **vagueia** de 60 a 324 ms ao longo do vídeo (13 mudanças > 50 ms, 7 para cima e 6 para baixo), e nota a nota a diferença de intervalos tem **desvio padrão 90 ms**: o marcador anda na grade do software; o violonista toca com rubato.
- Escuta do dono: o clique no ataque detectado cai junto com as notas.
- **Não repetir**: régua de tempo do som como `t_marcador + atraso` (A3 do contexto). O marcador dá a coluna e a janela (±0,3 s); o tempo fino vem do áudio, e a verdade de som tem de ser conferida pelo dono.

## 2026-10-13 — Mãos — M3c: braço pela música fora do MVP (rodada 1008)

- Só q02 e q16 do gabarito do braço são medíveis: q06 e q11 têm 0 notas com tempo no produto; o q07 é de outra câmera (abertura).
- **q16**: estável (0,17 px) e errado: trastes **10/15** dentro de 1/4 de casa, nut **0,49** de casa, corda 1 a **0,35** do vão 1–6. Grade comprimida no sentido das cordas: a ponta do dedo fica ~1 passo para a corda 6 em relação ao contato (q02: ~0,3).
- **Não repetir**: recuo constante da ponta sobre o DIP. Escolhido no q02 = 0 (qualquer recuo piora o nut); o q16 melhoraria em 0,4–0,6. Os quadros discordam.

## Áudio — 2026-10-13 — A2: alinhador sem marcador, v1 e v2 (rodada 2004)

- `tab/audio_alinhar.py`: casa as colunas de cada exibição a picos de ataque por programação dinâmica (alturas esperadas × "nova energia" + andamento), com o marcador escondido.
- **v2** (trecho contínuo com início e fim livres + andamento iterativo), MVP, régua = ataques do A1: **591 de 636** a ≤ 50 ms (fluxo ou alturas), **3 falsos de 636 (0,47 %)**, 7 recusas; trecho igual ao da régua em 19 de 22 exibições. v1 (página inteira): 10 falsos.
- Cada exibição do MVP toca um **trecho contínuo** da página (repetições e casas de volta); forçar a página inteira gerava 7 dos 10 falsos da v1.
- **Não repetir**: DTW de passo padrão sobre o perfil de alturas (14 de 636 a ≤ 100 ms); alinhar a página inteira em cada exibição.

## Áudio — 2026-10-13 — folha 1: primeiro gabarito de tempo do som, por escuta (rodada 2005)

- `data/gold/audio/folha1.json` (26 clipes, aprovado pelo dono): MVP com régua concordante **4 de 4** certos; os **3 "falsos" pela régua do A1 estavam certos** (erro da régua); colunas que o marcador nunca acende: 2 de 4 erradas (tela 2, cols 17–18); sem marcador (iwaki, kimny, shin izumi): **8 certos, 1 errado, 3 não sei em 12**.
- A régua do A3 passa a ser o gabarito de escuta. Próximo conserto: coluna sem ataque (ligadura/ornamento) não pode receber tempo.
- **Não repetir**: controle errado deslocado para onde há coluna recusada vizinha (o clique caiu numa nota real; f03).

## Áudio — 2026-10-13 — colunas que o marcador não acende são ornamentos; v3 reprovada (rodada 2006)

- No MVP, as 10 colunas com nota que o marcador nunca acende são **notas pequenas de ornamento sob arco** (mordente 2–3–2, deslize), vistas nos recortes. Às vezes soam com ataque (f21 certo), às vezes não (f20, f26 errados).
- Regra por proxy (corda 1 + nota única + ≤ 1,75 passo): 6 de 10 ornamentos e 0 de 400 colunas acesas no MVP, mas no gabarito do dono **recusa 2 "certos"** (f06, f21) e não resolve o f11. **Reprovada e desfeita.**
- Pedido à trilha tablatura: marcar ornamento (tamanho do glifo) e arco no produto (`docs/decisoes/2002-ornamento-no-produto.md`).
- **Não repetir**: adivinhar ornamento por geometria de coluna (corda/nota única/distância).

## Áudio — 2026-10-13 — folha 2: vídeos sem marcador; a escuta separa coluna, não ms (rodada 2007)

- `data/gold/audio/folha2.json` (30 clipes, aprovado pelo dono): afirmadas do alinhador v2 nos 3 vídeos sem marcador, **23 de 27 certos, 0 errados, 4 não sei**.
- **Controles não detectados: 0 de 3** (clique a 226–244 ms das notas, sem ataque a < 80 ms, ouvido "certo"). Com a folha 1: 1 de 4. "Certo" em folha de clique único = **coluna certa**, não ±50 ms (vale também para a folha 1).
- A5 proposto: `docs/decisoes/2003-tempo-do-audio-no-produto.md`. Arquivo irmão `chorinho/audio@1` por (tela, exibição, coluna), com recusas e motivo e `afericao.nivel = "coluna"`; sem mexer no `chorinho/video@1`.
- **Não repetir**: tratar "certo" de folha de clique único como precisão de tempo. Próximo formato: comparação A/B com deslocamentos de 50/100/200 ms.
- **Adendo (q21–q23, sky guitar, marcados pelo dono)**: q21 14/14 trastes, nut 0,30, cordas 0,14/0,06; q23 9/14, nut 0,05, cordas 0,06/0,15; q22 instável (85 px entre conjuntos) porque as notas ficam quase todas nas casas 2 e 4. Robustez: nota com casa > 14 é pulada e contada; semente com H inválida é descartada. **Não repetir**: confiar na calibração pela música sem conferir a cobertura de casas e a estabilidade entre conjuntos.

## Partitura — 2026-10-13 — P0: quantos vídeos têm pauta (rodada 3001)

- Amostra de 436 vídeos (até 30 por canal, semente 0) × 12 quadros do cache, com o detector geométrico `tab/partitura_pauta.py`, conferida nas folhas de miniaturas `data/saida/partitura/p0/folhas/`.
- **≈ 1.455 dos 2.998 vídeos ativos têm pauta (49 %)**; 220/436 na amostra, já descontados 2 vídeos falsos e somado 1 perdido. Canais: sky guitar, robert lunn, guitar dell'arte, iwaki, pablo romé, serge kottelat, transcriptor, paolo d'angelo, tv on guitar (quase todos os vídeos); guitarous 4/30; os demais 0.
- **Pauta sem tab praticamente não existe** (5 vídeos na amostra, e era tab não marcada pelo censo). A partitura vem junto da tablatura.
- Conferência: positivos 66/68 certos; nos negativos, 15/110 quadros têm pauta visível, mas só 1 vídeo muda de classe.
- Adendo (rodada 6, detector refinado para a Gymnopédie e barras de colcheia): 21 quadros ganhos, 0 perdidos, mesmo número de vídeos.
- **Não repetir**: (1) limite de espessura medido na sequência inteira de linhas de pixel: a 6ª linha borrada da tab e a chave ao lado da pauta engrossam a sequência (a 1ª rodada deu 2.188 vídeos, inflada por tab lida como pauta); medir no núcleo (≥ 50 % do pico). (2) máscara de polaridade clara sem teste de crista: acha o fundo branco entre as linhas da tab como "linhas". (3) subir o limite de espessura sem exigir espessura parecida: barra de colcheia (5 a 6 px) vira 6ª linha falsa.

## Partitura — 2026-10-13 — P1: qual biblioteca lê a pauta (rodada 3002)

- 21 recortes reais de pauta; R01–R12 medidos contra a tab do gabarito convertida em altura (546 notas, 3 vídeos). CPU, sem treino.
- **Audiveris com ampliação 2x: 479/546 notas certas (87,7 %), 4 inventadas**, saída em 20/21 recortes, 13 s por recorte. homr: 467/546, 23 inventadas, 21/21, 8,5 s. Audiveris sem ampliar: 388/546. oemer: falha (0/2, 8 min cada).
- Greensleeves 106/106 nas duas. No south american, 14 erros do Audiveris são fá# lido como fá em recortes sem clave e sem armadura na tela (a partitura rola): herdar clave e armadura do vídeo.
- **Base para a P2: Audiveris x2**; homr como segunda opinião. A medida é de altura, não de ritmo.
- **Não repetir**: (1) comparar MusicXML do Audiveris sem aplicar `clef-octave-change` (clave de sol com 8): a altura sai uma oitava abaixo (R05 dava 8/85, é 73/85). (2) oemer neste acervo: falha em todos os recortes testados, ~8 min e 5,6 GB cada.

## Partitura — 2026-10-14 — comparativo: variantes do Audiveris e SMT sem treino (rodada 3003)

- R01–R12 (546 notas da tab), mesma régua: **Audiveris x2 com margem 7/7: 491/546, 3 inventadas, 70/83 compassos cheios** (x2 com margem 4/6: 479, 67/83). homr: 467, 23 inventadas, 44/78.
- Ampliar 3x/4x piora (417/270); binarizar quebra 4 recortes (196); colar clave e armadura do início do sistema não ajuda (466).
- SMT sem treino (4 dos 7 pesos públicos rodaram; 3 sem pesos ou com acesso fechado): o melhor acerta 20/546, os outros 0. São pesos de piano, fora do domínio; o SMT só entra treinado (P2).
- Ferramenta de conferência (`tab.partitura_gabarito servir`, porta 8099) pronta; o dono ainda não gravou nada em `data/gold/partitura/`.
- **Não repetir**: (1) ampliar além de 2x para o Audiveris. (2) binarizar por Otsu antes do Audiveris. (3) pesos antoniorv6/SMT com o código `master`: o decoder carrega aleatório e só avisa ("newly initialized"); usar o commit d25acd4.

## Partitura — 2026-10-14 — gabarito do dono: o que o Audiveris erra (rodada 3004)

- O dono conferiu os 21 recortes (`data/gold/partitura/leitura_p1.json`). Dos 873 símbolos lidos, **852 estão certos (97,6 %)**: 7 com figura errada, 4 com altura errada e 10 que não existem. Há **78 notas faltando**.
- O ritmo do que é lido está certo em ~99 % dos símbolos. O gargalo é a cobertura (notas que faltam) e a armadura que não aparece no recorte (R06).
- Recomendação: não treinar o SMT agora. Primeiro juntar homr + Audiveris, completar pela tab e herdar a armadura. A decisão é do dono.
- **Não repetir**: tratar a altura do gabarito como altura soada. O dono confere contra o desenho: sem armadura na tela, um F#4 sai como F4 "certo".

## Partitura — 2026-10-14 — homr completando o Audiveris (rodada 3005)

- A união cega das leituras recupera **31 das 74** notas faltando, mas acrescenta 164 notas (~133 sem clique do dono). Na tab de R01–R12: certas 491→520, **inventadas 3→43**.
- 43 das 74 faltando não aparecem em nenhuma das duas leituras. Filtrar pela tab zeraria as inventadas, mas isso é pareamento (P3): só com aviso do dono.
- **Não repetir**: juntar homr e Audiveris sem filtro, seja completando acordes (14/102 casam), seja com eventos só do homr (17/62).

## Partitura — 2026-10-14 — P3 liberada: homr confirmado pela tab (rodada 3006)

- O dono liberou a P3 em 2026-10-14. Primeiro passo: a nota do homr só entra se a tab tem a mesma altura no evento casado. Resultado em R01–R12: **certas 491→523/546 (95,8 %), inventadas continuam 3**.
- 23 notas continuam sem leitura nenhuma: a altura vem da tab, mas a figura não tem fonte. A figura das 32 recuperadas vem do homr e não foi conferida.
- R20: a segunda metade não foi lida, e o dono não marcou faltando. O gabarito do R20 vale só para os símbolos lidos.
- Armadura herdada (rodada 3007): aplicando a armadura do R05 à leitura sem clave, R06 sobe de 79 para 81/88 e R07 de 88 para 89/96 (R07 sem altura errada). Falta tirar a armadura automaticamente do quadro do vídeo onde a clave aparece.
- Recorte (rodada 3008): conjunto de barras de colcheia, mais grosso que 1,5 entrelinha, deixa de contar como vizinho. Com isso, R21 e R14 deixam de cortar a parte de cima; as outras 19 caixas não mudam. `recortes_margem/` foi mantido, porque o gabarito usa as coordenadas dele.

## Partitura — 2026-10-14 — armadura do vídeo automática (rodada 3009)

- `python -m tab.partitura_omr herdar`: a armadura vem da maioria das leituras do mesmo vídeo que têm clave e é aplicada às leituras sem clave. R01–R12: **491 → 494/546**, inventadas continuam 3.
- No R06, as 5 alturas que sobram são bemóis inventados pelo Audiveris (compassos 7 e 11). O dono marcou essas notas como certas na conferência: rever o R06 na próxima rodada de conferência, sem mexer no gabarito por conta própria.

## Partitura — 2026-10-14 — P3: pareamento partitura × tab (rodada 3010)

- `python -m tab.partitura_pareamento`: o pareamento por sequência põe **325 de 326 pares no mesmo x do quadro** (mediana de 0,5 a 2,7 px, R01–R12).
- O tempo da partitura é o `t_ini` da coluna pareada. Hoje ele sai vazio: nem o gabarito de tab nem a saída `fase8/medida` desses vídeos têm `t_ini` por nota. Depende da trilha tablatura.

## Partitura — 2026-10-14 — saída única da partitura (rodada 3011)

- `python -m tab.partitura_pareamento` agora faz leitura com armadura do vídeo + notas do homr confirmadas pela tab + pareamento. R01–R12: **526/546 certas (96,3 %)**. As notas erradas continuam 14 (as inventadas sobem de 3 para 8 só por troca de categoria). São 336 de 337 pares no mesmo x.

## Partitura — 2026-10-15 — troca de altura desmentida pela tab (rodada 3012)

- Quando o homr completa um evento com nota que a tab confirma, a nota do Audiveris que a tab desmente sai para `trocadas`. R01–R12: certas seguem **526/546**, notas erradas caem de **14 para 8** (inventadas 8 → 3). 5 das 6 trocas são os bemóis inventados do R06.

## Partitura — 2026-10-15 — harmônico não é troca (rodada 3013)

- A troca do R11 (3012) era um harmônico artificial: a pauta desenha a nota presa e a tab escreve o som, uma oitava acima. Nota igual à da tab em outra oitava não é mais trocada. R01–R12: **526/546 certas**, 9 notas erradas (uma é o próprio harmônico), 5 trocas (os bemóis do R06).

## Partitura — 2026-10-15 — pareada com o produto, em todas as telas (rodada 3014)

- `tab.partitura_video` (`recortar`, `ler`, `parear`) gera `<stem>.partitura.json` (`chorinho/partitura@1`) para cada produto: 19/19 telas com pauta nos 3 vídeos. Nas 12 telas da P1, pareada com o produto: **527/546** (era 526 com o gabarito). Nas 7 telas novas do gymnopédie: 196/221. Gym tela 10: a tab do produto tem as cordas deslocadas de uma e o x denuncia (0 de 14 conferidos), um erro da trilha tablatura.

## Partitura — 2026-10-15 — armadura, compassos e x de reserva (rodada 3015)

- O `<stem>.partitura.json` ganha `fifths`, `fifths_origem` e `compassos` por pauta, e `metodo` (`altura` ou `x`) em cada par. Quando o x desmente o par pela altura, o evento pega a coluna livre mais próxima a até uma entrelinha: Gym tela 10 vai de 0 para 10 de 14 pares conferidos; total 433 de 438. Notas certas iguais (723/767). Gym tela 12 tem `fifths` 1, provavelmente errado; `fracao` só na primeira pauta de cada vídeo.

## Partitura — 2026-10-18 — documento final por vídeo com a nota que a tab tem (rodadas 3026, 3027)

- **Tamanho da pauta causa a perda** (3026): 30 pautas grandes reduzidas a 11 px caem de 925/925 para 855/925 notas certas achadas (0,924). Mediana de 15 quadros na pauta pequena não recupera nada (1376 → 1323 certas, extras 73 → 116). Só resolução de verdade ajuda.
- **P4** (3027): `tab.partitura_video parear` completa a pauta com a nota da tab que a pauta não leu (`origem` `tab_completada`, figura `null`) e marca `pauta_pequena` (< 16 px) e `leitura_ok` por pauta. A nota não entra se houver pausa na mesma voz, se estiver no cabeçalho ou se houver conflito de oitava. Nos 3 vídeos: 66 candidatas, 50 entram, 16 ficam fora. 442 eventos existentes idênticos.
- **Contra a tab do gabarito do dono**: fora da tela 10 da Gymnopédie, 12 de 22 completadas estão certas; na tela 10, 2 de 28. A completada vale o que vale a tab do produto naquele ponto, e as duas fontes erram nos mesmos lugares. Tratar como sugestão.

## Partitura — 2026-10-18 — onda 1 das frentes fechada (rodadas 3101–3103, 3110, 3160–3162, 3170–3172, 3026)

- **D1, gabarito sorteado** (40 vídeos, 13 canais; 35 conferidos pelo dono, `leitura_d1.json`): **certos/lidos 0,962**, **certos/(certos+faltando) 0,906**, 0 altura errada; 5 de 40 recortes sem leitura do Audiveris. Confirma o P1 (0,976 e 0,916): o Audiveris quase não inventa; falta cobertura. guitar dell'arte e pablo romé são os piores (0,84). Ver 3162.
- **F0, régua**: as marcas do Audiveris (`abnormal`, duração do compasso) avisam em 14 de 49 compassos com nota faltando (29 %); `expected="1"` do `.omr` é falta de fórmula, não duração (decisão: tratar como sem duração esperada daqui para frente). Troca pelo homr em R01–R12: 3 consertadas, 0 quebradas. Tempo pelo par: 217/438 eventos; as 4 inversões são da partitura. Ver 3101–3103.
- **E1, completar pela tab**: 56 notas completadas; o dono avaliou os trechos como "praticamente tudo errada" sem marcar nota a nota, e a olhada da sessão achou 19/21 figuras batendo (conflito não resolvido; desenho da conferência provavelmente enganou). **Decisão: nota completada entra com altura e instante da tab e figura `null`.** Nos produtos, 14 de 37 completadas herdam erro da tab. Ver 3170–3172.
- **A1, imagem limpa**: nenhuma variante passa de 25/36 (meta 30/36); a moldura recupera 2 e quebra 1. Não adotada. Ver 3110.
- **Qualidade da imagem** (59 recortes dos três gabaritos): pauta ≥ 16 px cobre 0,934, menor que isso 0,87–0,89; precisão igual em todas as faixas; tela carregada (tinta) acompanha a perda (Spearman −0,29). Correlação, não causa; teste causal proposto (reduzir pauta grande e reler). Ver 3026.
- Ferramenta de conferência: imagem dos recortes da frente D, id com acento, e `paginar` com pauta na borda de baixo do quadro corrigidos.
- **Não repetir**: (1) agente de frente numa pasta copiada sem git, container e ffmpeg (travou a onda); a worktree com `host-spawn` resolve. (2) sorteio "proporcional" lido só nos canais pequenos (kimny's guitar com 22 de 40 vagas e ~4 vídeos com pauta). (3) conferência de "só a figura" desenhando só as notas a julgar.

## Partitura — 2026-10-15 — homr troca o compasso em vídeo sem produto (rodada 3025)

- Regra adotada: no compasso em que o homr lê ≥ 2× as notas do Audiveris, entra o compasso do homr, com as notas marcadas `homr_sem_confirmacao` (`trocar_compassos_pelo_homr`). A leitura do Audiveris fica guardada. `ler --pasta` agora roda o homr também (160/162 ok). Nos 11 vídeos do piloto: **30 compassos trocados em 17 recortes** (11 no amores hallaras, 10 no blackbird). No athletic P01a, a troca recupera 25, inventa 8 e **perde 2** notas certas do Audiveris. Conferência do dono na porta 8097, gabarito `data/gold/partitura/compassos_homr.json`. Ver `docs/rodadas/3025-homr-troca-compasso-sem-produto.md`.

## Partitura — 2026-10-15 — o homr nas notas que faltam, sem tablatura (rodada 3024)

- Regra por compasso: aceitar o homr onde ele tem pelo menos 2× as notas do Audiveris. Resultado: 25/40 recuperadas e 8 inventadas sem produto; 5/50 e 2 no gabarito antigo (14 recortes comparáveis). É o caso de voz inteira perdida (athletic, R08, R19). Nota solta em acorde não se resolve assim. Proposta para o dono: trocar o compasso, marcando a nota como "sem confirmação". Ver `docs/rodadas/3024-homr-nas-notas-que-faltam.md`.

## Partitura — 2026-10-15 — gabarito do dono sem produto: Audiveris em 3 recortes (rodada 3023)

- Dos símbolos lidos, **98,9%** estão certos (176/178): 0 altura errada, 0 figura errada, 2 inexistentes. A cobertura é **81,5%** (40 notas faltando, 31 delas no athletic P01a, onde o Audiveris descartou a voz de cima dos compassos 3–4). Clave e armadura certas nos 3. A ferramenta agora grava o `--itens` servido em `fonte_itens`. Ver `docs/rodadas/3023-gabarito-sem-produto.md`.

## Partitura — 2026-10-15 — fileira de vigas não corta mais o topo do recorte (rodada 3022)

- Estrutura horizontal só limita o recorte se cobrir pelo menos 60% da sua extensão (`COBERTURA_MIN_VIZINHA`). Vigas cobrem 24–32%, linha de pestana ~55%, linha de verdade 94–100%. Caixas mudam em 40/162 recortes sem produto, 0/19 de produto e 1/21 do gabarito (R16, que não foi refeito). Nos 40 recortes, os eventos foram de 668 para 742, com o mesmo Audiveris ok (30). Ver `docs/rodadas/3022-viga-nao-corta-o-recorte.md`.

## Partitura — 2026-10-15 — piloto sem produto: 11 vídeos lidos (rodada 3021)

- `ler --pasta` nos 11 vídeos do piloto: Audiveris ok em **143/162** recortes, 3.641 eventos. As 19 falhas são "No system found". A faixa amarela do cursor explica a maioria: com faixa, 12/36 falham (33%); sem faixa, 7/126 (6%). O mela concentra 16 falhas. A regra de armadura da 3020 não mudou nada nos 8 novos. Ver `docs/rodadas/3021-piloto-sem-produto-11-videos.md`.

## Partitura — 2026-10-15 — armadura do vídeo também para leitura com clave e sem armadura (rodada 3020)

- `herdar_condicao` aplica a armadura do vídeo quando a leitura não tem clave **ou** não tem `<key>`. Gabarito R01–R21 idêntico; 3 produtos sem mudança; canon P06a None→2 (5 notas F→F#). Ver `docs/rodadas/3020-armadura-herdada-com-clave.md`.

## Partitura — 2026-10-15 — `ler --pasta`: partitura de vídeo sem produto (rodada 3019)

- `python -m tab.partitura_video ler --pasta <sem_produto/slug>` (imagem `chorinho-partitura:dev`) roda só o Audiveris nos recortes do `paginar` e grava `<slug>.partitura.json`: pautas com página, exibições, armadura, compassos e eventos, **sem par e sem tempo em segundos** (o tempo só vem da tab).
- Piloto: agua 10/10 (403 eventos), athletic 7/8 (301), canon 6/6 (112); ~18 s por recorte em CPU.
- Qualidade **não medida** (sem gabarito). Visto: canon P01a leu 5 de 16 notas; canon P06a perdeu a armadura de 2♯. Ver `docs/rodadas/3019-ler-pasta-sem-produto.md`.

## Partitura — 2026-10-15 — pauta com uma linha apagada ganha a 5ª linha (rodada 3018)

- Linha cinza e borrada some na abertura e sobram 4. O detector agora completa a 5ª linha no meio ou na borda, se ela for crista no cinza; 6 linhas = tablatura, descartada.
- Censo (436 vídeos, mesma amostra da 3001): **18 quadros ganharam pauta, 0 perderam**, 9 ganharam mais uma pauta. Dos 27, 25 são pautas reais, 1 é tablatura que o `paginar` descarta, 1 é falso (leonardo ramos).
- Validação 4/4, 3/3, 12/12, caixas idênticas. Piloto: mela 30→41 recortes; free tab 14→12 páginas (sem página partida), 23 recortes.
- O `paginar` também passa a ler o quadro com mais pautas de cada página. Ver `docs/rodadas/3018-quinta-linha-que-falta.md`.

## Partitura — 2026-10-15 — paginar resiste a destaque colorido e tira a tablatura (rodada 3017)

- Tinta passou a ser contraste com o fundo local (top-hat). Quando só o destaque amarelo ou rosa anda, a diferença caiu de até 0,74 para ≤ 0,06; troca real de página fica em 0,49–0,55.
- A tablatura confundida com pauta é descartada pela 6ª linha, medida no 2º pior de 10 trechos da largura: tablaturas ≥ 0,88, pautas reais ≤ 0,65 (antes as vigas tiravam 7 pautas reais).
- Validação: 4/4, 3/3 e 12/12, caixas idênticas às do produto.
- Piloto de 11 vídeos: canon 16→6 e beam 21→6 páginas em relação à 1ª tentativa; nenhuma pauta real descartada.
- **Ainda perde pauta sob destaque em página corrida** (mela, free tab): é o próximo passo. Faixa que rola fica como limite. Ver `docs/rodadas/3017-paginas-com-destaque-e-tab.md`.

## Partitura — 2026-10-15 — páginas de pauta sem o produto da tab (rodada 3016)

- `python -m tab.partitura_video paginar --video` acha as páginas de pauta direto do vídeo (1 quadro/s, assinatura da região das pautas, trechos estáveis, repetições juntadas). Nos 3 vídeos com produto: **19 de 19 telas** achadas, caixas idênticas às do produto, sem página sobrando, ~25 s por vídeo. Saída em `data/saida/partitura/sem_produto/`.

## Tablatura — 2026-10-13 — painel: o braço do violão deixa de ganhar da TAB

Defeito: no `south american music` (guitar dell'arte) o `escolher` devolvia a faixa fixa do
**braço** (6 "linhas" das cordas diagonais cortadas na horizontal) e o `tab.video` relia cada
página com essa caixa: **0 de 269** notas. Propriedade medida: `cordas_continuas` (grupos de
linhas de pixels com corrida contínua de tinta ≥ 50 % da largura, buracos até 1 passo
fechados). TAB do gabarito de presença: mínimo **6** (128 de 134 dão exatamente 6); braço
escolhido no South American: máximo **3** (17 de 24 dão 0). Limiar 4. O portão entra só
depois do `escolher` (se a faixa escolhida falha, procura TAB nos outros candidatos e por
máscara; sem alternativa, `None`); `tab.video.ler_tela` usa `escolher_ou_mascara`.

| medida | antes | depois |
| --- | --- | --- |
| South American (`tab.avaliar_video`) | 0/269 | precisão 254/255, revocação 254/269, casa 245/254, tempo 37/40 (falso 0) |
| MVP | 485/485, 485/491, 483/485, 39/40 | idêntico |
| Greensleeves | 88/90, 88/106, 88/88, 20/40 | idêntico |
| `tab.avaliar` (3 sementes) | 66, 71, 68 /72 | idêntico |
| gabarito de presença (`painel_do_quadro`, 144 quadros) | 134/136, 134/137 | idêntico; 1 caixa mudou (FP02 dell'arte: do braço para a TAB, sem rótulo) |

**Não resolve**: braço **horizontal** com cordas contínuas (cifra club, n ≥ 5) e as 12 + 2
caixas erradas do censo, que vêm das vias escura e por máscara do `telas.py`. O portão nessas
vias derrubava 3 TAB translúcidas de linha fina (pablo romé #20/#21, robert lunn #26: n = 1) e
foi revertido. Saídas: `data/saida/painel_braco/`, `data/saida/fase8/medida/*_v2/`,
`data/saida/mvp_v2/`.

## Áudio — 2026-10-13 — folha 3 A/B: o tempo do áudio está a ~100 ms (rodada 2008)

- `data/gold/audio/folha3.json` (40 pares, aprovado pelo dono): o dono escolheu o clique do alinhador contra um deslocado em **10 de 10** com 200 ms (2 "não sei") e **9 de 11** com 100 ms; com 50 ms, **7 de 12 "não sei"**. Não há tendência de cedo ou tarde.
- `chorinho/audio@1` (`tab/audio_produto.py`, commit `b6da3b38`): arquivo irmão por (tela, exibição, coluna), validado nos 4 produtos (MVP 645/699 colunas com tempo; iwaki 245/273; kimny 158/222; shin izumi 114/552). Aferição agora `nivel = "ms"`, `resolucao_escuta_ms = 100`.
- **Não repetir**: deslocamento (controle ou par A/B) que cai a menos de |d| + 50 ms de uma coluna vizinha, afirmada ou não. No shin izumi, p21 e p24 caíram em outra nota.
- Abaixo de ~50 ms, o ouvido não separa: a medição tem de ser com áudio sintético.

## Áudio — 2026-10-13 — A4: o shin izumi falha porque o produto perde a corda 1 (rodada 2009)

- 23 de 42 exibições recusadas, todas por "poucas colunas casadas", mas com cosseno **alto** (0,83). Descartados por medição: casas > 7 (as recusadas têm menos), afinação (transposição 0 é a melhor: 114 afirmadas, contra 0–8 nas outras) e densidade de notas (10 candidatos/s nos dois grupos).
- Causa apoiada: o produto do shin izumi tem só **4 % das notas na corda 1** (42 de 998), contra 17–27 % nos outros vídeos. Nos recortes, as telas 12 e 25 perdem as notas da corda 1, e na 25 pausas viram notas. Pedido à trilha tablatura (via dono).
- Exibição recusada com cosseno alto é **alarme de leitura** (colunas faltando).

## 2026-10-13 — Mãos — M3c: correção do braço pela imagem em pente (rodada 1009, reprovada)

- Pente de 6 cordas (3 faixas) + trastes pela regra de 12 notas sob projetiva 1D, sobre a mediana da cena. Constantes fixadas antes; dev q02/q16, teste q21/q23.
- Piora: q16 trastes 10/15 → 2/15 e cordas 0,35 → 0,65; q21 cordas 0,14 → 0,42; q23 trastes 9/14 → 0/14 e nut 0,05 → 0,66. Cada metade (só cordas, só trastes) acerta num quadro e erra em outro.
- **Não repetir**: busca global de pente por perfil de linhas claras no layout do sky guitar sem critério de "não achou" (pega a borda do braço e o painel da mão direita).

## Tablatura — 2026-10-13 — gerador: fonte serifada fina (robert lunn), candidato `fina3`

O Gymnopédie (robert lunn) usa serifa fina tipo Times; o modelo oficial leu 186 de 392 notas
e errou a casa em 108 (`0` lido como `8`, `4`/`2` como `tecnica`/`harmonico`). Presets novos em
`tab.sintetico --fontes` (padrão `padrao` = sequência de sorteios idêntica, pesos `oficial_*`
reproduzem). Treino `--n-linhas 320 --epocas 22 --seed S`, saída `artefatos/serif3_S`;
medições em `data/saida/serif/t1..t3` (`fina3`: + LiberationSerif-Regular com peso 2, corda por
cima quase sempre, fonte fina grande 1,0–1,4 passo).

| `fina3` semente | oficial /72 | MVP casa | Greensleeves revoc. / casa | Gymnopédie revoc. / casa |
| --- | --- | --- | --- | --- |
| 1 | 63 (0,875) | 464/471, revoc. 471/491 | 106/106, 105/106 | 275/392, 259/275 (0,942) |
| 2 | 70 (0,972) | 483/488, revoc. 488/491 | 106/106, 106/106 | 254/392, 238/254 (0,937) |
| 3 | 69 (0,958) | 481/488, revoc. 488/491 | 101/106, 101/101 | 266/392, 247/266 (0,929) |
| oficial (ref.) | 66, 71, 68 (0,949) | 483/485, revoc. 485/491 | 88/106, 88/88 | 186 lidas, 78 casas certas |

Média oficial 0,935 (amplitude 0,097) contra 0,949: **não promovido** (`MODELO_PADRAO` igual).
Critério do Gymnopédie (casa ≥ 0,95) não alcançado (0,93–0,94), mas a casa saiu de ~0,42 e a
revocação de 0,47 para 0,65–0,70. Ainda falha: `4` lido como `harmonico` e notas não
tokenizadas (revocação). Presets `fina`, `fina2`, `fina4` (com desfoque) medidos e piores
(`data/saida/serif/g2_*`, `g4_*`). Uso: `serif3_2` só para PRÉ-PREENCHER o ouro (o dono corrige).

## Áudio — 2026-10-13 — A4: alinhador em 10 vídeos sem marcador (rodada 2010)

- 10 de 10 rodaram sem erro (37 min): **2799 de 4531 colunas com tempo (62 %)**, 64 de 184 exibições recusadas. **6 de 10 bons** (77–97 % das colunas: iwaki ×2, kimny ×2, shin izumi *dream is a wish*, paolo d'angelo).
- Falhas olhadas no recorte: **guitarous sakura 0 de 62**, porque o produto lê tudo uma corda abaixo (pedido à trilha tablatura); **transcriptor campanitas 201 de 935**, por ser rasgueado com batidas abafadas "X" (limite do método, a leitura está certa). Giant steps e charagua não olhados.
- **Recusa da calibração pela música** (`tab/maos_braco_fora.py::avaliar_confianca`, campo `confianca` no medicao.json): ≥ 5 casas com ≥ 5 notas, vão ≥ 5 casas, estabilidade entre conjuntos ≤ 2 px. Recusa o q22 (três motivos); aceita q02, q16, q21, q23. **O q16 passa e é ruim** (nut 0,49, 10/15): o critério pega instabilidade e pouca cobertura, não o viés da ponta do dedo. Limiares escolhidos depois de ver o q22, ainda não validados.

## Áudio — 2026-10-13 — alarme de leitura no arquivo de áudio (rodada 2011)

- `chorinho/audio@1` ganha, por exibição, `cos_medio`, `n_casadas` e `alarme_leitura`: recusada com cos ≥ 0,7. Nos 14 vídeos: 0–2 alarmes nos 9 bons; 7–21 nos 4 fracos.
- Das telas com alarme olhadas na imagem, **5 de 6 têm leitura com falhas**: colunas faltando, cordas deslocadas, números de dois algarismos e acordes em elipse. A sexta é rasgueado com leitura certa.

## Áudio — 2026-10-13 — rasgueado: colunas abafadas no alinhador v2.1 (rodada 2012)

- Coluna abafada = ≥ 4 `nao_notas` `tecnica` em cordas distintas, sem nota e com ≥ 4 de top-1 "15". Campanitas: 122. Nos 9 vídeos bons: 0. Recortes confirmam pilhas de X.
- v2.1: as abafadas entram como ataque sem altura. Nos 9 bons a saída é **idêntica à v2 (4131 de 4131 colunas)**. Campanitas: notas com tempo 201 → **268 de 935**, alarmes 21 → 17, 12 exibições marcadas `rasgueado` (alarme desligado). Não conferido de ouvido.
- **Não repetir**: regra de 3 cordas `tecnica` para X (pega acordes de números e ornamentos em 3 vídeos bons).

## Áudio — 2026-10-13 — campanitas: os 17 alarmes restantes; pedidos consolidados à tablatura (rodada 2013, decisão 2004)

- Causas: 3 de 17 do método (setas de rasgueado sem X), 3 de 17 de leitura, 2 de 17 outras (painel na partitura; uma sem causa), 9 de 17 não olhadas. **14 de 17 têm página gêmea aceita**, e 38 × 20 têm sequências idênticas no produto: o alinhador casa 1 coluna numa passagem e 5 na outra. Hipótese: o alinhador escolhe trecho mínimo quando há mais ataques que colunas. Não provado.
- `docs/decisoes/2004-pedidos-de-leitura-a-trilha-tablatura.md`: 9 pedidos de leitura com evidência e as telas com alarme por vídeo, para o dono repassar.

## Tablatura — 2026-10-13 — régua de tempo: cursor em trânsito vale a última coluna passada (decisão do dono)

Diagnóstico do Greensleeves (`data/saida/tempo_gs/`, folha `folha.png`): dos 17 erros + 3 sem
tempo, **10** eram o cursor fino do pablo romé **entre duas colunas** (a régua levava o clique
para a mais próxima, às vezes a seguinte; o produto dava a última passada); **7** eram coluna
que o produto não leu (o "1" lido como harmônico; o candidato `serif3_*` lê); **3** são a 1ª
coluna de uma exibição, sem tempo (onset atrasado; defeito real, aberto). Decisão do dono: entre
duas colunas vale **a última que o cursor passou** (a nota que soa). `coluna_do_ouro`: a última
coluna à esquerda do clique, salvo se a próxima está a até 0,75 passo à direita **e** mais perto
(cursor chegando, ~17 px antes). A versão "até 0,75 passo, sem comparar" piorava o South
American em t=98 (colunas a 20 px) e foi corrigida antes do commit.

| vídeo | régua antiga | régua nova |
| --- | --- | --- |
| MVP (oficial) | 39/40 | **40/40** |
| Greensleeves (oficial) | 20/40 | **29/40** |
| Greensleeves (`serif3_1/2/3`) | 23, 24, 23 /40 | **33, 33, 32 /40** |
| South American (v2) | 37/40 | 37/40 |

Tempo falso continua 0 em todos. Scripts: `data/saida/fase8/medida/regua_a/`.

## Áudio — 2026-10-13 — campanitas descartado pelo dono

- O dono tirou o transcriptor *campanitas* (Ernesto Cavour) do dataset, por não atender aos padrões dele. A folha 4 não entra no gabarito. As rodadas 2012 e 2013 ficam como registro; o v2.1 não muda os outros 13 vídeos.

## Áudio — 2026-10-13 — por que o alinhador fica com trecho curto (rodada 2014)

- Medição sem mudar código, em 6 exibições recusadas (room 335 e giant steps) e 4 boas. O DP perde o caminho que cobre a página por causa do termo de andamento (3 casos) ou do custo de coluna sem ataque (3). Afrouxar λ aceita até 5 de 6, mas muda 10 a 15 de 112 colunas boas em mais de 30 ms. **Alinhador fica como está**; a causa é leitura com colunas faltando (decisão 2004).
- Achado: 8 dos 42 alarmes de leitura vêm de trecho escolhido todo na margem de 0,5 s fora da página (casou a página vizinha). Proposta: o alarme ignorar esses casos. Ainda não feito.

## Áudio — 2026-10-13 — alarme de leitura ignora trecho fora da página (rodada 2014)

- `tab.audio_produto`: nova chave `fora_da_pagina` por exibição (trecho escolhido inteiro na margem de 0,5 s). O alarme não dispara nesses casos. Nos 13 vídeos: alarmes **42 → 34**, colunas iguais 5342 de 5342. Lista de telas da decisão 2004 atualizada.

## Áudio — 2026-10-13 — andamento com lacunas: não adotado (rodada 2015)

- Variante do termo de andamento que aceita buracos de 2T e 3T (κ por coluna perdida). Em nenhum κ os 6 casos da rodada 2014 passam. Com κ = 0,1, 3 exibições a mais passam, mas 69 de 3760 colunas boas mudam em mais de 30 ms; nenhum dos 72 itens do gabarito muda. **Alinhador fica v2.1**; o conserto é a leitura (decisão 2004).

## Tablatura — 2026-10-13 — marcador pulado: limiar de tinta 0,02 → 0,01

Causa das colunas puladas do Greensleeves (t = 62, 82, 114): o cursor fino do pablo romé mostra
pouca tinta por dentro (p1 0,0087, p5 0,0115, mediana 0,0276; 291 de 1.238 amostras abaixo de
0,02) e `faixa_translucida` o recusava. MVP (mediana 0,106) e South American (0,129) ficam longe;
a moldura sólida do MVP mede 0,0 exato. Medido com `serif3_2`, mesmo leitor do produto:

| vídeo | 0,02 | 0,01 | 0,005 |
| --- | --- | --- | --- |
| MVP | 40/40 | 40/40 | 40/40 |
| Greensleeves | 33/40 | **38/40** | 38/40 |
| South American | 37/40 | 37/40 | 37/40 |

Nenhum instante piora; no Greensleeves 6 mudam para acerto (62, 82, 114, e 92/130, que eram a
"1ª coluna sem tempo"). MVP e South American saem com JSON idêntico. Greensleeves ganha 12 notas
fora das páginas do ouro (203 → 215), não pontuadas. Adotado 0,01 (o mais conservador dos dois
que empatam). Scripts: `data/saida/limiar_tinta/`.

## Áudio — 2026-10-13 — lote 2: 12 canais novos (rodada 2016)

- 12 de 12 vídeos rodaram sem erro; **2292 de 4587 colunas com tempo (50 %)**. 5 vídeos bons (74–98 %), 5 no meio, 2 falham por causa da entrada: kenneth acoustic é padrão de ritmo sem casa; vvxofingerstyletab tem 1 tela de 90 s (troca de página não detectada).
- Som × marcador (3 canais com `t_ini`): tirado o atraso fixo do canal (−115 a +178 ms), 77–95 % das colunas ficam a ≤ 100 ms. O produto leu marcador em só 3 de 12 canais marcados. Pedidos 10–12 na decisão 2004.

## Tablatura — 2026-10-14 — detector neural de sistema (N1–N4): medido nos 8 ouros

Troca o recorte por regras (`_glifos_por_faixa` + barline + classificador de glifo) por
uma rede que vê o sistema inteiro (`tab.detector_tab`, 555 mil parâmetros, treinada com
`tab.sintetico_sistema`). A geometria (painel, cordas, passo) continua a do produto.
Medição no mesmo quadro de cada tela conferida dos 8 ouros (63 telas, 2.689 notas):

| leitura | precisão | revocação | casa |
| --- | --- | --- | --- |
| produto (`oficial_3`) | 0,962 | 0,830 | 0,943 |
| v3 só sintético (3 sementes, média) | 0,977 | 0,950 | 0,977 |
| v3 + ajuste fino com ouros, validação cruzada por vídeo (4 dobras) | 0,974 | 0,949 | **0,987** |

- Room 335 corda 1: 8/28 → 28/28; Gymnopédie revocação 0,43 → 0,93; Greensleeves 0,83 → 1,00.
- O que custou caro e foi consertado pelo GERADOR, não por regra: arpejo Guitar Pro, "TAB"/fórmula
  grandes e pausas lidos como nota (74 inventadas → 10); "1" fino de sans regular lido como "4"
  (78 casos; fontes de treino 2 → 6; o ajuste fino zerou o resto).
- Régua: a nota acrescentada por clique guarda o clique como centro, e no "10" o dono clica no "1"
  (50 notas de dois algarismos com centro < 8 px da borda). `casar_notas` usa 0,8 passo para casa
  de dois algarismos (`FOLGA_DOIS_ALGARISMOS`); números do produto não mudam.
- Única piora contra o produto (ajuste fino, 3 sementes): retrato e la vie, 1-2 notas em ~450.
- Viés a favor do produto: os ouros v2 foram pré-preenchidos por ele (posições herdadas).
- Fora do produto até decisão do dono; trocar o leitor muda o X do rasgueado ("15") de que o áudio depende.
Scripts e tabelas: `data/saida/n3/`, `data/saida/n4/`.

## Tablatura — 2026-10-14 — produto troca de leitor: `rede` é o padrão (decisão 0010)

- **Aprovado pelo dono** ("trocar é a escolha certa"). `tab.video` e `tab.transcrever` ganham
  `--leitor rede|glifos`, e o padrão é `rede`. O leitor de glifos fica de reserva.
- **Modelo**: `artefatos/detector_tab_final_s{1,2,3}/`, ajuste fino a partir de `v3_s1` com os 8
  ouros (63 telas) e o sintético, 3000 passos. O comando está no `config.json`
  (`data/saida/n4/treinar_ft.py --dobra 0`). Perda final nas sementes 1/2/3: 0,0541, 0,0541 e
  0,0543. O produto usa a **s1**, declarada antes de medir.
- **Régua de tempo nos 3 vídeos com marcador**, mesmo HEAD. A rede usa o modelo da dobra que
  NÃO viu o vídeo (`data/saida/troca/`):

  | vídeo | leitor | precisão | revocação | casa | tempo |
  | --- | --- | --- | --- | --- | --- |
  | MVP (retrato) | glifos | 1,000 | 0,988 | 0,996 | 40/40 |
  | MVP (retrato) | rede | 0,998 | 0,994 | 0,996 | 40/40 |
  | Greensleeves | glifos | 0,978 | 0,830 | 1,000 | 34/40 |
  | Greensleeves | rede | 0,991 | 1,000 | 1,000 | 38/40 |
  | South American | glifos | 0,996 | 0,944 | 0,965 | 37/40 |
  | South American | rede | 1,000 | 1,000 | 1,000 | 38/40 |

  - Tempo falso: 0 em todos.
  - Esquema: 0 erros nos 3 JSONs da rede.
  - O MVP passa a ter **1 nota inventada** (CA-3 pede 0 no MVP). É a mesma nota da validação
    cruzada.
- **Bug achado e corrigido antes do commit**: nota da rede herdava a borda esquerda de um glifo
  largo (slide `2/3` grudado). Duas notas caíam na mesma coluna e geravam 5 erros de esquema no
  South American. Agora a borda só é herdada se o glifo começa a até 0,8 passo do centro
  (`BORDA_MAXIMA_PASSO`), com teste.
- **Consequências** (decisão 0010):
  - o X sai em `nao_notas` como classe `x`; a trilha áudio foi avisada pelo texto da decisão;
  - `tecnica` da nota vem preenchida pela rede, **sem validação**;
  - o leitor `rede` não grava `simbolo_cru`. É dívida: quem precisar do recorte cru usa
    `--leitor glifos`.

## Tablatura — 2026-10-15 — fase 8: linhas sob faixa de destaque, e régua com ouro parcial

- **Linhas sob a faixa amarela** (`tabseg.extensao_das_linhas`). No End of Beginning (kenneth
  acoustic, t=52 s) a faixa amarela do compasso tocado apagava as cordas no Otsu. O painel
  começava em x=1011, e a tablatura começa em x≈12. Agora a linha conta também pelo contraste
  local, mas **só onde o fundo local é claro** (`FUNDO_CLARO_MINIMO = 150`).
  - A primeira versão, sem a exigência de fundo claro, piorou a Gymnopédie. O papel fica
    sobre vídeo escuro, o painel crescia para fora do papel e, em 163,4–163,6 s, a escolha caía
    no braço ou em nada. A tela 13 ficava sem passo, e a régua recusava o vídeo inteiro.
  - Fundo medido na linha da corda: papel 255, faixa amarela 241, vídeo escuro ≤ 75.
  - 2 testes sintéticos. Cada um falha na versão que não tem o seu conserto (controle negativo
    feito).
- **Régua com ouro parcial** (`tab.avaliar_video`). Em EOB e Room 335 o ouro confere só
  algumas páginas. As notas entregues em tela sem página conferida contavam como
  "inventadas" (464 e 900). Agora ficam fora da conta, e o relatório diz quantas.
- **8 ouros, leitor `rede`, modelo da dobra que não viu o vídeo** (`data/saida/fase8/linhas2/`):

  | vídeo | precisão | revocação | casa | antes (revocação) |
  | --- | --- | --- | --- | --- |
  | retrato | 0,998 | 0,994 | 0,996 | igual |
  | La Vie | 1,000 | 0,995 | 0,998 | igual |
  | Greensleeves | 1,000 | 1,000 | 1,000 | igual |
  | Gymnopédie | 0,951 | 0,931 | 0,932 | 0,934 (1 nota) |
  | South American | 1,000 | 1,000 | 1,000 | igual |
  | From This Place | 0,979 | 0,990 | 0,995 | igual |
  | End of Beginning | 0,981 | **1,000** | 0,997 | **0,670** |
  | Room 335 | 0,922 | 0,991 | 0,991 | igual |

  - Esquema: 0 erros nos 8.
  - CA-8: 66/71/68 de 72, sem mudança.
  - O tempo do EOB continua 0/12 ("json sem tempo"): o marcador do kenneth não é lido. Pendente.
- **Inventadas de Room 335 e From This Place, olhadas uma a uma**:
  - Room 335: 25 de 27 são leitura errada (pausa com forma de "7", rótulo "TAB", setas de
    palheta). 1 é nota que falta no ouro (tela 4, corda 3, um "1"), para o dono decidir.
  - From This Place: 4 são a fórmula de compasso 3/4 em cinza. As outras ficam em volta de
    algarismos pequenos de ligado ("h") e de "harm. 12".
  - O gerador não tem essa pausa nem o 3/4 cinza. É lacuna de cobertura (regra 6).
- **Barra grossa não é corda** (`painel.descartar_grossas`). Na Gymnopédie, tela 10 (t=136,5 s),
  o painel ficava uma corda abaixo. A barra preta de 10 px da borda do vídeo formava, com 5
  cordas reais, um grupo de 6 linhas regular que ganhava por uniformidade (0,827 contra 0,820).
  Agora um grupo com linha grossa (≥ 6 px e ≥ 2× a mediana, medida na extensão das próprias
  linhas) sai quando existe grupo limpo com 5 das suas 6 linhas.
  - Nas 63 telas conferidas dos 8 ouros, só a tela 10 mudou.
  - Gymnopédie: precisão 0,951 → **0,997**, revocação 0,931 → **0,997**, casa 0,932 → 0,957.
    Os outros 7 vídeos ficaram iguais (`data/saida/fase8/grossa/`, no worktree haiku-gym).
  - 3 testes sintéticos; o controle negativo falha sem a regra.
  - A casa da Gymnopédie (0,957) é a pior dos 8. Ainda não olhei quais casas erram.
- **Painel escuro do cifra club** (`painel._candidato_do_grupo` + `tabseg.extensao_das_linhas_claras`).
  O cifra club desenha a TAB em fundo quase preto, com tracejado claro, letras e/B/G/D/A/E em
  bolinhas laranja à esquerda e diagramas de acorde à direita. O grupo de 6 cordas era achado,
  mas `extensao_das_linhas` só vê linha em fundo claro e estreitava o recorte a ~60 px, e a
  escolha recusava. Agora, com faixa de mediana ≤ `FUNDO_ESCURO_MAXIMO`, a extensão é a do
  tracejado claro, começando depois das bolinhas e com buraco máximo de 60 px. Os buracos do
  tracejado têm 17–26 px (46 px num caso), e o intervalo até o diagrama tem 96–113 px.
  - Em 8 quadros de cifra club, de 8 vídeos, o painel certo foi de 0 para 6. Os 2 restantes
    (a grande família t=52, acenda o farol t=43) ainda escolhem o braço do violão antes do
    ramo escuro. Pendente.
  - Nos 6 quadros, as notas lidas batem com as reais contadas à mão (154). Falsas nas letras
    e no diagrama: 33 → 0. A versão intermediária, com a largura cheia, lia essas 33.
  - O bend escrito "6b7"/"b9r8" sai como mais de uma nota. Técnica não validada.
  - Não-regressão do painel: 63 telas dos 8 ouros e 20 telas claras de outros canais com as
    mesmas linhas e a mesma caixa.
  - 2 testes sintéticos; o controle negativo, com a largura cheia, falha.
  - A régua completa dos 8 ouros não foi rodada de novo: o ramo só age em faixa escura, e os
    painéis dos ouros saíram idênticos.
- **Braço do violão contra a TAB escura** (`painel.escolher_ou_mascara`). Em 3 de 14 quadros de
  cifra club, `escolher` aceitava o braço: as cordas dele passam no teste de linhas contínuas.
  O que separa é a **deriva** das cordas, isto é, quanto sobem ou descem de uma borda à outra,
  em passos:
  - TAB: 0,003–0,060 em 97 telas (63 dos ouros, 20 claras, 6 de cifra club);
  - braço: 0,104, 0,336 e 0,389.
  - Com deriva acima de `DERIVA_BRACO_PASSOS = 0,08`, a escolha procura antes uma TAB escura,
    já recortada pelo tracejado (`candidatos_escuros_estreitos`). Se não achar, fica com a
    escolha antiga. A margem é estreita (0,060 contra 0,104).
  - Cifra club: caixa certa em 14 de 14 quadros (antes, 11). As outras 94 telas ficaram
    idênticas.
  - Lidos pela rede, os 3 quadros trocados têm 60 notas reais: 59 certas, 1 perdida (o
    primeiro 7 de um "7/9"), 0 falsas.
  - 2 testes; o controle negativo falha.
- **Ouro da Gymnopédie corrigido pelo dono** (2026-10-15). Cinco notas estavam como 8 e a
  imagem mostra 0: tela 1 corda 5 (x 1191), tela 2 corda 5 (x 1404), tela 3 corda 6 (x 1690),
  tela 8 corda 5 (x 1216) e tela 11 corda 3 (x 542). Com o mesmo JSON previsto, a casa da
  Gymnopédie vai de 0,957 para **0,969**; precisão e revocação não mudam (0,997).
- **Ouro do Room 335: nota que faltava, incluída pelo dono** (2026-10-15). Tela 4, corda 3,
  casa 1, na coluna x 1260 (2-1-2-0 nas cordas 2 a 5; conferido no recorte do quadro t=14 s).
  Com o mesmo JSON previsto, a precisão vai de 0,922 para **0,925** (320 de 346).
- **Gerador: pausa entre cordas e cinza** (`tab/sintetico_sistema.py`). Desenha a pausa que
  fica entre duas cordas (`P_PAUSA_ENTRE = 0,3`, forma copiada dos recortes reais do Room 335)
  e, às vezes, a fórmula de compasso e a TAB inteira em cinza (`P_FORMULA_CINZA`,
  `P_TAB_CINZA` = 0,15). Eram as notas inventadas que sobravam no Room 335 e no From This
  Place. Ajuste fino das dobras 2–4 (`data/saida/n4/treinar_ft.py`), 3 sementes por gerador,
  régua nos 6 vídeos dessas dobras, mesmo código e mesmo ouro (`data/saida/fase8/ger/`):

  | gerador | precisão (s1, s2, s3) | revocação | casa | inventadas |
  | --- | --- | --- | --- | --- |
  | antigo | 0,977 0,973 0,970 | 0,996 0,996 0,995 | 0,990 0,990 0,988 | 41 50 55 |
  | novo | 0,981 0,980 0,978 | 0,994 0,994 0,996 | 0,990 0,988 0,987 | 35 36 40 |

  - A precisão melhora nas 3 sementes, sem sobreposição (pior novo 0,978 > melhor antigo
    0,977), e a amplitude cai de 0,008 para 0,003. Room 335: 0,904–0,925 → 0,928–0,936.
  - Revocação e casa ficam dentro da amplitude. Gymnopédie, casa: 0,962–0,969 → 0,954–0,972.
  - **O produto passa a usar o gerador novo**: `detector_tab_final_s1_ger` (dobra 0, os 8
    ouros + sintético, semente 1 declarada antes, cache refeito com os ouros corrigidos). Nas
    35 telas da T8.2, que nenhum dos dois modelos viu, relidas pelos dois com o mesmo código
    (`data/saida/fase8/ger/t82_comparar.py`):

    | modelo | casa | precisão | revocação | inventadas | perdidas |
    | --- | --- | --- | --- | --- | --- |
    | `final_s1` (antigo) | 1549/1556 = 0,996 | 0,996 | 0,989 | 7 | 17 |
    | `final_s1_ger` (novo) | 1551/1557 = 0,996 | 0,994 | 0,990 | 9 | 16 |

    Fora do ouro é empate: 15 erros do antigo somem e 12 novos aparecem, a maioria de
    algarismo duplo (10, 12, 14) perdido. O antigo reproduz exatamente o número da T8.2,
    então a releitura confere. A troca vale pelo ganho nas dobras, sem perda fora delas.
- **T8.2: casa fora do ouro, conferida pelo dono** (2026-10-15). 36 telas, 2 vídeos por canal
  dos 18 canais fora do ouro (sorteio com semente 0, `data/saida/t82/gerar.py`), lidas pelo
  produto (rede `detector_tab_final_s1`). O dono conferiu 35 na ferramenta do ouro
  (`tab.ouro_video servir` com material de `data/saida/t82/material_ferramenta.py`; respostas
  em `data/saida/t82/ferramenta/conferencia_t82.json`, fora de data/gold). A tela 33 ficou de
  fora: a ferramenta abria o editor longe do clique em imagem muito larga.
  - 1.563 notas lidas: 1.549 certas, 7 com casa errada, 7 falsas e 17 faltando. Casa certa
    em 1.549 de 1.556 casadas (0,996); precisão 0,996; revocação 1.556 de 1.573 (0,989).
  - Causas (31 erros, olhados um a um em `data/saida/t82/erros/`): número de dois
    algarismos 12 (10, 11 e 12 perdidos ou lidos pela metade), nota encostada em haste,
    arco ou barline 7, fundo ou cor 4, símbolo lido como nota 3, "1" de perna comprida lido
    como 4 3, nota fora do recorte 2.
  - Frequência não explica os dois algarismos: o gerador sintético já sorteia cerca de 33%
    de casas com dois algarismos (`P_CASA_ALTA = 0,15` para 13–24, mais 10–12 entre 0–12).
    A causa está no aspecto (espaço entre os algarismos, fonte, corda tocando o número), e
    ainda não foi medida. O "1" de perna comprida é outra fonte que o gerador não tem.

## 2026-10-15 — Mãos — M8: corda sem a mão direita (rodada 1013)

Rodada: [`docs/rodadas/1013-m8-corda-sem-a-mao-direita.md`](docs/rodadas/1013-m8-corda-sem-a-mao-direita.md). Código `tab/maos_corda_sem_direita.py`; saída `data/saida/maos/m8/`. 4 vídeos do sky guitar, 2.437 notas (2.280 ambíguas pela altura), altura e gabarito tirados da tablatura do produto.

| degrau | acurácia de corda | erros |
| --- | --- | --- |
| D0 casa mais baixa | 0,860 | 341 |
| D1 decodificador (polifonia + continuidade, Viterbi), sem câmera | 0,883 | 285 |
| D2 + janela da mão esquerda pela câmera (só gabarito do braço) | 0,883 | 285 |
| D3 + janela dos vizinhos ± 2 (teto otimista, sem vazar) | 0,912 | 214 |

- Corda solta 690/690 em todos os degraus. Deixando um vídeo de fora: D1 0,888, D2 0,891, D3 0,915.
- D2 = D1 porque a câmera casa com o quadro do gabarito em 96/1.470 ataques com nota presa (6,5 %): a mão dentro do modelo derruba o NCC, e a câmera muda de plano. Onde existe, a janela contém a casa certa (93–100 %), mas tem 4,3–5,8 casas.
- D3: 130 erros com a casa certa dentro da janela (ambiguidade dentro da região da mão) e 66 de posição.
- Próximo: frentes de pesquisa em [`docs/pesquisa/maos-frentes.md`](docs/pesquisa/maos-frentes.md) (rastreio do braço, janela por dedo, timbre, custo aprendido).
- **Não repetir**: casar a câmera pelo braço com a mão dentro do modelo; janela da mão inteira [floor(min) − 1, ceil(max) + 1] para desempatar corda.

## 2026-10-16 — Mãos — Frentes da pesquisa: ondas 1 e 2 (rodadas 1101–1170)

Plano: [`docs/pesquisa/maos-frentes.md`](docs/pesquisa/maos-frentes.md) (seções 4.1 e 4.2). Cada frente rodou numa worktree com critérios congelados (CA1–CA7) e regras escritas antes da medida. **Nenhuma passou.** Os documentos das rodadas estão em `docs/rodadas/`. O código das frentes ficou só nos branches `maos/f0-residuo`, `maos/a3-custo-aprendido`, `maos/b1-janela-dedo`, `maos/c1-inarmonicidade` e `maos/d1-ligados`.

| rodada | frente | resultado contra o D1 do M8 (285 erros; ambíguas 1.995/2.280) |
| --- | --- | --- |
| 1101 | 0 — resíduo | "outros" 97/285 (34 %), acima do limite de 30 % |
| 1110 | A3 — custo aprendido (perceptron) | ambíguas −1,36 pp, 0 consertadas, 31 quebradas |
| 1111 | A1 — transição com `dt` | consertadas 9, quebradas 22 |
| 1112 | A2 — Minimax / L_p | consertadas 7, quebradas 40 |
| 1130 | B1 — janela por célula do dedo | contém 92,3 % e 94,1 % (piso 95 %) |
| 1131 | B1b — D2 com grade fixa, pontas no som | 243 erros (+1,84 pp, saldo 42); reprova no CA3: lacrimosa −0,72 pp |
| 1150 | C1 — β separa cordas | inconclusiva: 0 pares com 8 notas por lado; inclinação log β × casa 0,94 do esperado |
| 1151 | C1b — β com máscara de parciais | parou no controle sintético sobreposto (161 kb/s: 99/117) |
| 1170 | D1 — ligados na mesma corda | sem efeito: só 0,6 % dos intervalos ≤ 0,5 s |

- **Único sinal positivo: a janela da mão esquerda com a grade fixa do quadro do dono, sem o teste de câmera.** Diagnóstico do revisor (`data/saida/maos/m8/d2_fixo.py`): 285 → 242 erros, cobertura 99 %, +1,9 pp nas ambíguas, saldo 43. Com as pontas no som (1131), 243. Reprova no CA3 nas duas versões, cada vez por um vídeo diferente: glimpse −0,63 pp com as pontas no `t_ini`, lacrimosa −0,72 pp com as pontas no som (3 a 4 notas). Próximo passo: confirmação fora da amostra (rodada 1014), em vídeos novos do sky guitar com o mesmo método e os mesmos limiares.
- Corrige o "não repetir" da 1013: a janela da mão inteira **desempata**, desde que cubra o vídeo (grade fixa). O problema da 1013 era a cobertura de 6,5 %. O que sobra são 207 erros com a casa certa dentro da janela.
- Frentes fechadas: A (o decodificador só com a sequência de notas não melhora), D (sem nota onde atuar) e C (sem amostra nos 4 vídeos).
- **Não repetir** (detalhes nas rodadas):
  - perceptron com φ somado por sequência e η = 0,1;
  - Minimax como estimador do que foi tocado;
  - escolher `p` ou a escala de `dt` com 3 vídeos de treino;
  - célula de 10–20 % do vão do traste como janela;
  - excluir a nota inteira por "ainda soa" de 2 s (derruba ~95 % das medidas);
  - "ainda soa" com o `t_ini` de ataques seguidos e janela de 0,5 s;
  - ligado restrito à corda anterior sem limite de casa;
  - "sem ataque no áudio" como rótulo de ligado (0/8);
  - trocar `t_ini` por `t_audio` sem separar os 170 ataques sem casamento.

## 2026-10-16 — Mãos — M9: confirmação fora da amostra da janela fixa (rodada 1014)

[`docs/rodadas/1014-m9-confirmacao-janela-fixa.md`](docs/rodadas/1014-m9-confirmacao-janela-fixa.md). Regras e CA3 (opção b, do dono) gravados antes da medida; quadros q32–q36 marcados pelo dono.

- **Reprovou.** 6 vídeos novos do sky guitar: 153 → 146 erros, +0,57 pp nas ambíguas (mínimo +1,0), saldo 7 (mínimo 20); ganho só em 2 dos 4 vídeos grandes. Nos 4 de trabalho o ganho segue 285 → 242. **A janela fixa não entra no produto; a referência continua o D1 do M8.**
- Diagnóstico: o erro que sobra é quase todo **"previu corda solta onde a nota é presa"** (118/242 nos de trabalho, 122/146 nos novos; 101/102 no no surprises). A janela da mão esquerda não atua nesse erro porque a corda solta não depende da posição da mão.
- Hipótese pós-hoc, não testada: penalizar a solta quando a janela contém a alternativa presa. Só com regras novas e vídeos não olhados.
- **Não repetir**: tratar o ganho da janela fixa nos 4 vídeos de trabalho como efeito geral (não se repetiu fora da amostra).

## Tablatura — 2026-10-16 — onda 1 das frentes (F0, C1, D1)

Três frentes fechadas nesta onda. O aceite de nenhuma foi atingido: A1 não abre, C1 sai, D2 não abre.

### F0 — régua de técnica (rodadas 0101–0104)

- **Folga 0,5**, fixa, como manda o plano (§5.2). A medida com 1,0 foi descartada por contradizer o plano; continua registrada na 0101 só para comparação.
- [`0101`](docs/rodadas/0101-regua-de-tecnica.md): o legato (h, p, mordente, prolongamento; 139 marcas) é achado em **25 de 139**, com classe certa em **4**. Slide: 20 de 46 certas. Harmônico: 4 de 4 (não decide, menos de 10 marcas). Arpejo (0 de 21) e rasgueado (0 de 15) não têm saída na rede. Das perdas, **179 de 201** são "nada marcado".
- [`0102`](docs/rodadas/0102-topo-cortado.md) (F0.2, topo cortado): **não conclusiva**. A medida conta texto acima da tab (10 de 12 folhas legíveis eram letra ou nome de acorde) e erra a polaridade em fundo escuro. Não há limiar novo; a frente fecha assim.
- [`0103`](docs/rodadas/0103-cabeca-do-ligado.md) (F0.3, cabeça do ligado): o ajuste fino **não apagou o ligado**. Com escore ≥ 0,5 nas 139 regiões, v3_s1 marca 14 e o produto 13. O escore existe, mas é fraco (mediana 0,1 nos dois modelos).
- [`0104`](docs/rodadas/0104-corda-vizinha-e-sementes.md) (corda vizinha, variante de diagnóstico): nas 229 marcas, +4 certas, todas de slide (28 → 32). No legato continuam 4 certas de 139. A variante não entra na régua oficial.
- **Conclusão.** A rede não acha o ligado, e não é por limiar nem por ajuste fino. **A1 não abre.** O caminho é A2 (detector de arco) ou B (estilo do arco no gerador). **B1 abre primeiro**: o dono aprovou a dependência do AlphaTab em 2026-10-16.

### C1 — rolagem (rodadas 0150–0153)

- [`0150`](docs/rodadas/0150-rolagem-censo-nao-rola.md): a primeira leitura, "não rolam", estava errada. Os rolantes do censo rolam **em saltos com sobreposição**. A triagem chamou de troca de página todo passo acima de 40 px, e isso foi o erro.
- [`0151`](docs/rodadas/0151-rolagem-saltos-definicoes.md): definições, máscaras e limiares dos saltos, antes da medida.
- [`0152`](docs/rodadas/0152-rolagem-consenso-e-remedida.md):
  - **kenneth "location" passou**: 19 válidos de 20 (1 indefinido); erro mediano do consenso 0,06 px, máximo 0,26 px; nenhum salto válido com erro > 5 px.
  - **mr. tabs "no rain" falhou**: 3 de 20 com erro > 5 px (690, 779 e 1557 px). É alias de período de dois compassos (~779 px), e a regra de consenso não pega, porque os dois métodos erram igual.
- [`0153`](docs/rodadas/0153-rolagem-palpite-pelo-cursor.md): nem o palpite pelo cursor resolveu. Mediana 0,32 px passa, mas 6 de 13 definidos erram mais de 5 px. A premissa de que o compasso do cursor vai ao início da linha não vale: em 155,9 s ele fica em 1061,5 px. A rodada parou no mr. tabs; kenneth e leonardo não foram medidos.
- **C1 sai desta onda.** Ideia anotada para depois: verificar se o salto é animado e somar os passos quadro a quadro (não medido).

### D1 — som confere a casa (rodada 0170)

- [`0170`](docs/rodadas/0170-som-confere-a-casa.md): **parada**. Precisão nos 4 ouros em L\* = 1,25 dB: **1/9 = 0,111** (abaixo de 0,3). Revocação dos erros medidos: 1/4.
- **80 de 84** erros de casa + inventadas não têm instante de som. São colunas sem alinhamento, já cobertas pelo alarme por exibição da rodada 2011. A falha é de cobertura e de baseline, não de resolução de altura: **D2 não abre**.
- Dois casos levados ao dono:
  - Retrato v2, tela 11, corda 6: era erro do ouro (0 → 2), corrigido.
  - Room 335, tela 27: o ouro estava certo (5 ligado ao 9 na corda 5). O arco desenhado sobre a corda 6 faz o produto errar a corda.

### Integração: o ajuste fino apagava o X

- O ajuste fino (`data/saida/n4/treinar_ft.py`) ensinava o detector a apagar o X abafado: tudo que não é nota do ouro virava fundo. No End of Beginning o produto dava ~1 X para 76 regiões marcadas; o modelo da dobra que não viu o vídeo dava 93.
- **Conserto parcial** com `--ignorar-x` (região de X não conta como fundo): **38 de 76** no EOB e **5 de 9** regiões no kenneth (T8.2). Notas sem piora: dobras, casa certa 1745 contra 1744 na semente 1, 1737 contra 1738 na semente 2.
- **Próximo passo:** ensinar o X como nota, a partir de palpites conferidos pelo dono. O produto (`DETECTOR_PADRAO`) não mudou.

### Ouro

- Correções do dono no Retrato v2 e Room 335 (commit `3e7d4d74`). CA1 das dobras passou a ouro 1771, entregues 1799, casadas 1761, casa 1744, 38 inventadas, 10 perdidas. A 0170 tinha 1774 / 1799 / 1764 / 1747 / 35 / 10 antes dessa correção.
- `tab.ouro_video servir` desfazia edições feitas fora dela. Agora não sobe se o ouro diverge do estado (commit `bc431c0f`).
- **Gymnopédie diverge** (10 linhas): precisa de acerto antes de ser aberto.

Tabela "não repetir" atualizada acima (5 linhas novas).

## 2026-10-16 — Mãos — nova direção: base de treino das mãos (decisão 1006)

Decisão do dono: a trilha das mãos **grava as mãos de cada nota** (base de treino) e não tenta mais adivinhar a corda pela mão. A tablatura da tela é o rótulo; as mãos, o braço e o som são a entrada. Plano: [`docs/guias/plano-dataset-maos.md`](docs/guias/plano-dataset-maos.md); decisão: [`1006`](docs/decisoes/1006-maos-viram-base-de-treino.md).

- Fases: M10 esquema e regras → M11 braço quadro a quadro (a peça que falta) → M12 mãos quadro a quadro → M13 tempo do som (trilha do áudio) → M14 associação e auditoria do dono (≤ 2 associações falsas em 100 eventos ouro, proposta) → M15 piloto de 20 vídeos do sky guitar e rollout → M16 modelo, depois.
- Regras centrais: nada da entrada é calculado com o gabarito; associação pelo `t_audio`, não pelo marcador (o som vem 165–275 ms depois); caixa da tablatura guardada para mascarar; cru + confiança + nível (ouro/prata/recusado), nunca exclusão calada.
- O D1 do M8 (88 % da corda do professor) fica como linha de base do modelo futuro.
- **Não repetir**: reabrir as ondas de regra para adivinhar a corda pela mão.

## 2026-10-17 — Mãos — M11a: braço rastreado do quadro-chave (rodada 1015): reprova no CA2

- O dono marcou q37–q66 (teste, 6 canais) e as partes do violão em todos os 66 quadros (decisão [1008](docs/decisoes/1008-partes-do-violao-no-gabarito-do-braco.md)).
- O rastreador (`tab.maos_braco_rastreio`: ORB 5000, Lowe 0,8, RANSAC, "não achei" por inliers, reprojeção e determinante) foi congelado no sky guitar e medido uma vez:
  - **0 falsos em 30** (a grade fixa tem 18);
  - ⊥ mediano de **0,17 vão** contra 1,10 da grade fixa;
  - mas só **8 de 11 "achei" certos** (CA2 pede 95 %) e cobertura de **11/30**.
- Causa da cobertura zero em kenneth, shin izumi e iwaki (câmera aberta): os 5000 pontos do alvo vão para a tablatura. No braço caem 0, 19 e 1 pontos; buscando só no braço, são 2919, 3472 e 1654.
- Próximo:
  - nova rodada com a busca restrita a uma região e quadros de teste novos;
  - medir a variação do próprio dono ao remarcar, porque os imprecisos ficaram em 0,27–0,35 vão, perto do limite de 0,25.
- **Não repetir**: ajustar o rastreador num canal só, com o braço em close, e esperar que ele passe em câmera aberta.

## Áudio — 2026-10-20 — regressão do alinhador com o leitor `rede` (rodada 2017)

- 15 vídeos com número antigo, produto gerado de novo (leitor `rede`, CPU) e alinhador v2.1 sem mudança. Determinismo do produto conferido (2 execuções iguais).
- 14 vídeos bons: colunas com tempo **4707/5666 (0,831) → 5337/6220 (0,858)**; *room 335* 114/552 → 357/603. Colunas presentes nos dois: **4516 de 4648 (97,2 %) a ≤ 30 ms**. Som × marcador: queda máxima 1,6 pp. Gabarito de escuta: 37 de 40 pontos certos mantidos, 1 recusado, 2 fora (104 e 116 ms).
- **Critério 1 reprovado em 2 de 14** (*michelle* −2,9 pp, *bach prelude* −2,6 pp), e as causas são de leitura, vistas no quadro: o acorde final que o `rede` passa a ler encurta o trecho no *ritardando* (limite da rodada 2014); o `rede` junta "2·3" em "23" (casa errada); o `rede` perde "10" na corda 1 do *room 335* e lê ornamento como coluna. Pedidos 13 e 14 na decisão 2004.
- **Não repetir**: comparar fração de colunas com tempo entre leitores sem olhar o denominador: a leitura nova muda as colunas (acorde final, algarismos juntados), e a fração cai sem o alinhador mudar.

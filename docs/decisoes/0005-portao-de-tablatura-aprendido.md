# 0005 — O portão "isto é tablatura?" tem de ser aprendido (regra à mão não separa)

**Data:** 2026-10-09 · **Status:** aceita · **Origem:** montagens dos canais novos

## O achado

Gerando montagem para os canais novos, o detector escolheu, em 3 de 4:

| canal/vídeo | o que ele escolheu | o que era |
| --- | --- | --- |
| `cifra club` — livre estou (frozen) | corpo do violão + "Refrão Final" | **não é tablatura** |
| `guitar dell'arte` — etude in e minor | pauta com `m i m` e uma diagonal | a **partitura** |
| `shin izumi` — change the world | **cabeça do violão com tarraxas** | não é tablatura |
| `violaodecria` — cartel do 900 | **teclado de piano** | não é tablatura (o vídeo é de teclado) |

Consequência direta: o **"96,5 % com tablatura"** da varredura da noite está **inflado** —
o mesmo detector aceitou piano, tarraxas e corpo de violão. Aquele número é piso para
presença, mas **não** é medida de tablatura.

## Quatro discriminadores testados — e os quatro falharam

Medidos nos quadros originais (não na montagem), com a verdade conferida no olho:

| caso | verdade | uniformidade | fração de algarismos (conf ≥0,5) | espessura da linha ÷ passo |
| --- | --- | --- | --- | --- |
| `sky4_t88` | **TAB** | 0,883 | **1,00** | — |
| `sky4_t120` | **TAB** | 0,874 | **0,23** | — |
| `asturias_t417` | **TAB** | 0,876 | **0,90** | — |
| `cifra club` (corpo) | não | **0,974** | 0,00 | 0,53 |
| `guitar dell'arte` (partitura) | não | 0,959 | 0,37 | 5,27 |
| `shin izumi` (tarraxas) | não | 0,925 | 0,28 | 6,38 |
| `violaodecria` (piano) | não | 0,856 | 0,20 | **0,14** |

1. **glifos centrados** (critério antigo): escolhia o braço do violão — já substituído;
2. **uniformidade do fundo**: separa o braço (0,842) da tablatura (0,888), mas **não**
   separa piano (0,856) nem tarraxas (0,925) nem corpo (0,974, o mais "liso" de todos);
3. **fração de algarismos / confiança do classificador**: tablatura real dá 0,23
   (`sky4_t120`) e a cabeça do violão dá 0,28 — **não separa**;
4. **espessura das linhas**: a tecla preta do piano dá linha **fina** (0,14 do passo),
   igual à corda. **não separa**.

A lição é a que o projeto já aprendeu seis vezes em outra roupa: **regra geométrica à mão
não cobre a variedade do acervo**. Aqui a variedade é o *contexto* (o que está na tela),
não a forma do algarismo.

## Decisão

O portão **"este recorte é uma pauta de tablatura?"** passa a ser um **classificador
binário pequeno**, sobre o recorte do painel — não uma regra. Era a recomendação que já
estava no `tab/README.md` antigo e nunca foi feita.

- **entrada**: o recorte do painel (cinza, redimensionado para tamanho fixo), preservando
  a estrutura horizontal (linhas + glifos);
- **positivos**: pauta **sintética** (o gerador já sabe desenhar: claro/escuro, linha
  sólida/tracejada, passo 14–36, acorde, rótulo `TAB`) **mais** os painéis reais
  confirmados dos canais do gabarito;
- **negativos**: negativos **sintéticos** (barras largas tipo tecla, madeira com veio,
  cordas em diagonal tipo cabeça/braço, pauta de 5 linhas sem tablatura) **mais** os
  negativos reais que esta rodada achou (piano, tarraxas, corpo);
- **portão**: só entra no pipeline o recorte com probabilidade de tablatura acima do
  limiar; abaixo disso o resultado é `sem_notacao`, e o vídeo/trecho é declarado como tal
  em vez de virar leitura inventada.

## Por que isto responde à pergunta do dono do projeto

Ele perguntou se dá para fazer "um modelo global e unificado" ou se é canal a canal. A
resposta medida é: **o que é global é aprendido** (identidade do algarismo **e** o portão
de contexto, ambos por modelo pequeno); **o que é por canal é tabela** (símbolo →
técnica). O que **não** se deve fazer é resolver contexto com regra à mão — foi o que
esta rodada mostrou falhando quatro vezes seguidas.

## Consequências e o que fica pendente

- a varredura precisa **reprocessar com o portão**: os números por canal só valem depois
  disso, e o custo do portão é uma passada do modelo por painel (barato);
- o gabarito **não** deve ser ampliado antes do portão: rotular glifo de piano não é
  gabarito de tablatura;
- os negativos reais achados aqui viram **casos de teste** permanentes
  (`data/saida/frames/ouro_novos.png` e os quadros em `data/saida/frames/`).

## Primeira tentativa de treino: 3 de 7 (e o que ela ensinou)

Implementado `tab/portao.py` com positivos e negativos **sintéticos**, o primeiro treino
deu acurácia de treino **1,0000 já na 3ª época** e **0 de 3** nos painéis reais — sinal de
tarefa trivial e sem transferência.

Causa identificada: o positivo sintético era um **desenho limpo** e o recorte real é
**quadro de vídeo** (compressão, borda, conteúdo em volta). O classificador de glifos
transfere porque o sintético passa pelo **mesmo extrator**; o portão recebia pixels crus.

Corrigido o alinhamento (a cena passa a ser colada numa faixa de um quadro sintético e o
recorte da faixa é o que entra na rede), o resultado ficou **3 de 7**:

| caso | verdade | p(tablatura) | |
| --- | --- | --- | --- |
| `sky4_t88` | tablatura | 1,000 | ok |
| `sky4_t120` | **tablatura** | **0,000** | **erro** |
| `asturias_t417` | tablatura | 1,000 | ok |
| `violaodecria` (piano) | não | **0,995** | **erro** |
| `shin izumi` (tarraxas) | não | 0,149 | ok |
| `cifra club` (corpo) | não | **1,000** | **erro** |
| `guitar dell'arte` (partitura) | não | **1,000** | **erro** |

**A lição**: o negativo sintético é um **desenho** (tecla, madeira, mancha); o negativo
real é **fotografia de objeto**. Nenhuma quantidade de desenho sintético cobre a
distribuição de "frame de vídeo que não é tablatura". O mesmo vale para o positivo: uma
tablatura real com `m i m` (digitação) acima e passo 20 foi rejeitada.

## Decisão revisada

O portão continua sendo um classificador pequeno, mas **o rótulo do negativo tem de vir de
frame real, lido no olho** — como o gabarito. Plano:

1. gerar ~120 recortes candidatos de painel de dezenas de vídeos, de canais variados
   (o melhor candidato de cada vídeo **e** a segunda faixa, que costuma ser o braço/corpo);
2. eu leio as montagens e rotulo cada recorte (`tablatura` / `nao_tablatura` / `duvida`),
   **gravando os PNGs para o dono auditar** — regra nº 5 do `AGENTS.md`;
3. treinar com os recortes reais rotulados **mais** os sintéticos alinhados (aumento de
   dado), com os 7 casos desta tabela mantidos **fora** do treino, como conjunto de
   aceitação;
4. só entra no pipeline o que passar no conjunto de aceitação **e** na validação.

## Segunda tentativa: recortes REAIS rotulados no olho → 18/23, mas não generaliza

Coletei 121 recortes de painel de 8 canais (o melhor candidato de cada vídeo **e** a
segunda faixa, que costuma ser o braço/corpo), montei folhas de 32 com índice e rotulei
**lendo uma a uma** — os PNGs ficam em `data/saida/frames/folha_A/B/C.png` e os rótulos em
`data/gold/portao.json` (**119 rotulados**: 26 tablatura, 93 não, 2 em dúvida).

O que a leitura mostrou: a folha A (cifra club) tinha **1 tablatura em 32** (o resto era
corpo/braço e os painéis de letra e acorde); a folha B (eruditos) tinha **16 em 32**; a
folha C (cifra club/outros) tinha **13 em 32** com nomes de acorde acima da TAB. Ou seja:
o detector propõe muito negativo, e é isso que dá para minar.

Treinando com os 119 reais (96 treino / 23 validação, estratificado) **mais 1.800
sintéticos alinhados** como aumento:

- **validação real: 18/23 (78%)** — melhor que o sintético puro;
- **mas o conjunto de aceitação piorou para 3/7**: agora ele **rejeita as três tablaturas
  conhecidas** (`sky4_t88` 0,003; `sky4_t120` 0,000; `asturias` 0,000) e aceita a partitura
  (0,61).

Três causas, todas de **dado**, não de capacidade do modelo:

1. **classe desbalanceada** (26 positivos × 93 negativos): a perda é dominada pelo negativo;
2. **viés de canal**: os positivos rotulados vieram de cifra club, eruditos, iwaki, kimny,
   leonardo, mr. tabs, pablo romé, paolo — **`sky guitar` quase não aparece**, e é
   justamente o canal do MVP. O modelo aprendeu "partitura+TAB dos eruditos" como cara de
   tablatura e estranhou uma TAB limpa de 3 algarismos;
3. **validação sorteada aleatoriamente mede a coisa errada**: o que importa é generalizar
   para **canal que não entrou no treino**. A validação tem de ser **por canal**.

## Próximo passo do portão (revisado de novo)

1. rotular **mais positivos por canal**, sobretudo `sky guitar` e `iwaki` (os dois do MVP
   ainda não representados), com o mesmo método: folha com índice, leitura no olho, PNG
   para auditoria;
2. balancear as classes no treino (peso ou reamostragem) e medir a **validação deixando um
   canal inteiro de fora**;
3. só adotar o portão quando ele acertar o conjunto de aceitação **e** o canal deixado de
   fora. Enquanto isso, o pipeline **declara** que não tem portão confiável em vez de
   aceitar piano.

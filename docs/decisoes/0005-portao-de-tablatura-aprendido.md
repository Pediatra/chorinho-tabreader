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

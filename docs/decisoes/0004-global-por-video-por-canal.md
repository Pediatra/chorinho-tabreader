# 0004 — O que é global e o que é por canal (e por que não há modelo por canal)

**Data:** 2026-10-09 · **Status:** aceita · **Pergunta do dono do projeto:** *"tem como
fazer uma solução e modelo que pegue tudo de maneira global e unificada, ou será
necessário ir em cada canal e adequar o código?"*

## Resposta curta

**Global, com decisão por vídeo e configuração por canal.** Não é um modelo por canal, e
também não é um modelo único que "entende tudo": é um **pipeline global** cujas decisões
são tomadas **por vídeo** (onde está a notação, quando ela aparece, qual o marcador) e
cuja **única camada por canal é uma tabela de dados** (símbolo → técnica), não código nem
pesos.

A medição desta noite sustenta a divisão. Cada linha abaixo é medida, com o número.

| camada | varia por | evidência medida |
| --- | --- | --- |
| leitura do quadro | arquivo | `cv2` lê 51 % do acervo (0,17 s); `ffmpeg` lê 100 % (0,40 s) |
| **onde está o painel** | **vídeo/trecho** | `topo`/`meio`/`base`; no `sky guitar` #4 o painel é `meio` com x=[51,621] |
| **quando a notação aparece** | **vídeo** | no `sky guitar` ela aparece da metade para o fim: 20 de 20 vídeos "sem tablatura" têm tablatura em algum instante |
| família de renderização (claro/escuro, linha sólida/tracejada) | canal ↔ vídeo | 5 famílias; `cifra club` é tinta **clara** sobre fundo escuro |
| grade de cordas (6 linhas) | **global** | 163/163 linhas; a armadilha é o braço do violão, que tem 6 cordas iguais |
| **identidade do algarismo** | **global** | 0,889 no gabarito de 4 canais treinando **só em sintético**; o alfabeto é comum (o cluster de forma mais frequente aparece em 11 canais) |
| **símbolo de técnica** | **canal** | `(6)` ligada, `<7>` harmônico, `/` slide, `h`/`p`; 172 recortes crus já guardados |
| **marcador de tempo** | **vídeo** | faixa que **desliza** (medido: 65 px/s), faixa que **salta**, **cor** no algarismo (41/41 onsets), **nenhum** (`iwaki`: 0 em 42 detecções) |

Repare no padrão: **o que varia é contexto (onde/quando/qual), não o alfabeto.** Por isso
a identidade do símbolo gráfico é global e o resto é decisão local.

## O pipeline, em três etapas globais

### Etapa A — onde e quando existe notação (determinística, sem modelo)

Varredura por instantes: fundo uniforme → grade de 6 cordas → estreitamento ao retângulo →
**intervalos de presença**. Saída por vídeo:

```
{ video, intervalos: [ {t0, t1, painel{x0,y0,x1,y1}, familia, mascara, passo} ] }
```

Custo medido: **0,9 s por vídeo por instante** (depois da otimização de 13×), com medidas
baratas (linhas, fundo) em todas as faixas e `segmentar` só até a primeira que serve.

### Etapa B — qual é o marcador, se houver (detector global, veredito por trecho)

Para cada intervalo, decidir entre quatro mecanismos e **declarar** o escolhido:

| mecanismo | como se mede | estado |
| --- | --- | --- |
| faixa vertical que **desliza** | x(t) monótona → inverter: a nota começa quando cruza o x dela | implementado (`tab/tempo.py`, 10 testes) |
| faixa que **salta** (patamar) | início de cada patamar | a fazer |
| **cor** no algarismo (cumulativo) | onset = instante em que a cor muda, por token | medido na rodada 47–50 (41/41 onsets) |
| **nenhum** | declara ausência e **não inventa** | implementado (hoje é o caso de `iwaki`) |

E há um quinto caminho, que a correção do dono do projeto abriu: quando **não há marcador**
e a partitura/tablatura **vai trocando**, o instante da **troca** é o único sinal de tempo
que existe na imagem. Ele dá **um instante por sistema**, não por nota — grosseiro e
honesto. Para onset por nota sem marcador, a fonte viável é **áudio** (autorizado), com o
alinhamento ainda a resolver.

### Etapa C — o que a notação diz (modelo global)

- geometria e tokenização: global, em produção;
- **um** classificador de glifos (~74 mil parâmetros), treinado **só em sintético**:
  global, 0,889 no gabarito;
- **captura** de símbolo cru: global (todo token não numérico vira recorte PNG
  deduplicado, com caixas e larguras);
- **significado** do símbolo: **por canal**, numa tabela `configs/simbolos.yaml`.

## Por que NÃO um modelo por canal

1. **O alfabeto é comum** — medido: o cluster de forma mais frequente do acervo reúne
   glifos de **11 canais diferentes**;
2. **quando um canal falha, a causa medida foi cobertura do gerador, não capacidade do
   modelo** — 6 vezes: três regras geométricas deram 0, uma deu −0,166, e as duas mudanças
   de **dado** deram +0,05. A ação certa é acrescentar a forma ao gerador sintético;
3. **o modelo é minúsculo** (74 mil parâmetros): o custo não é treinar, é **rotular**. Um
   modelo por canal multiplicaria o custo de rótulo — que é o recurso escasso — sem atacar
   a causa;
4. **o que realmente muda entre canais é vocabulário e desenho de símbolo**, e isso é
   tabela, não peso.

## Por que NÃO um modelo único que "pega tudo"

O que varia é **contexto espaço-temporal** — onde está o painel, quando ele aparece, qual
o marcador. Isso não é reconhecimento de forma: é **medição geométrica e temporal**, e
medição determinística é auditável. Enfiá-la num modelo maior trocaria um número
verificável por uma caixa-preta — exatamente o que o `GOT-OCR2.0` (580 M, **0 de 15**
algarismos) já mostrou que não paga.

## O que isso significa em trabalho

| # | trabalho | escopo | custo medido/estimado |
| --- | --- | --- | --- |
| 1 | varredura corrigida (2 instantes na metade final) | global | ~2 h para 3.993 vídeos |
| 2 | veredito de marcador por intervalo (4 mecanismos) | global | faixa: pronto; cor: existe; troca: a implementar (diferença de quadro, barato) |
| 3 | **ampliar o gabarito** (casas 8–24, canais prioritários e eruditos) | global | ~1 noite de leitura minha, com PNG por montagem para o dono auditar |
| 4 | retreinar (3 sementes, determinístico) e remedir | global | ~10 min de GPU por semente |
| 5 | `configs/simbolos.yaml` (símbolo → técnica **por canal**) | canal | leio os 172+ recortes crus e o dono confirma |
| 6 | afinação (texto na tela) e capotraste | vídeo | a implementar |
| 7 | tempo por áudio nos sem marcador | global | a implementar (alinhamento é o problema) |

O caminho "canal a canal" **não** é o plano: o que existe por canal é a **tabela** do item
5 e, no máximo, uma **dica de configuração** (família de máscara preferida, se o detector
hesitar). O resto é global, com decisão por vídeo.

## Consequência para o formato de saída

O JSON passa a ser **por intervalo de notação**, não por vídeo: um vídeo pode mostrar
trechos diferentes, e cada trecho declara o próprio painel, máscara, marcador e passo. O
MusicXML sai por intervalo. Cada nota carrega a **procedência** de tudo que é inferido
(duração, afinação assumida, mecanismo de tempo) — nada inferido se apresenta como medido.

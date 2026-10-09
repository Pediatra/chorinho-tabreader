# 0007 — O painel pode conter partitura E tablatura: ler as duas é ler errado

**Data:** 2026-10-09 · **Status:** aceita · **Origem:** dono do projeto, confirmada por
medição

## O que o dono do projeto avisou (e estava certo)

Sobre `sky guitar`, `guitar dell'arte` e `iwaki`, ele disse a mesma coisa nos três:

> *"Olhando só para a tablatura não tem como se confundir, mas **se pegar todos os números
> pode acabar pegando alguns números que ficam na partitura e achar que são da tablatura**."*

## O que a medição mostrou

Primeira execução ponta a ponta **com tempo** (`sky guitar`, `(henze) nocturno`, intervalo
110,3–313,3 s), o mesmo trecho que produziu 39 instantes distintos cobrindo 117–303 s:

| medida | valor |
| --- | --- |
| notas lidas | 143 |
| notas **não-algarismo** | **94 (66 %)** — `harmonico` 39, `junk` 33, `tecnica` 22 |
| notas com casa numérica | 49 |
| confiança **mediana** dos algarismos | **0,434** |
| notas exportadas para MusicXML | 49 |

O painel escolhido é a faixa `topo`, de **largura total**, com `passo 16 px` e 107–135
glifos. Nessa faixa convivem **a pauta de 5 linhas e a tablatura de 6** — e o detector de
linhas encontra "6 linhas" numa mistura das duas. As bolinhas de nota e os números de
digitação da partitura entram como token, e o classificador faz o que pode: chama de
`junk`/`harmonico`/`tecnica` dois terços do que recebe.

Ou seja: **o estreitamento em x não basta**. Ele resolveu o braço do violão ao lado; não
resolve partitura **acima** da tablatura, que é o caso mais comum nos canais eruditos.

## Decisão

A leitura da tablatura passa a exigir que os tokens venham do **sistema de 6 linhas da
TABLATURA**, não de uma faixa que contém outra pauta. Caminhos, em ordem de preferência:

1. **separar os sistemas**: achar os grupos de linhas na faixa e exigir que o grupo
   escolhido tenha 6 linhas com espaçamento na faixa medida (14–45 px) e que os tokens
   estejam **dentro** desse grupo — a partitura tem 5 linhas e espaçamento menor;
2. **usar o portão aprendido** (`tab/portao.py`) para decidir "isto é tablatura?" no
   recorte, que é justamente o que ele existe para fazer (ver decisão 0005);
3. **usar a dica de canal** (`configs/canais.yaml`): o dono do projeto disse que nos
   canais eruditos a tablatura fica **abaixo** da partitura — quando as duas aparecem, a
   de baixo é a tablatura.

Enquanto isso não estiver resolvido, **o número de notas lidas não é confiável**: 143
notas com 66 % de não-algarismo não é leitura de tablatura, é leitura de uma faixa que
contém tablatura.

## O que NÃO muda

- o **tempo** desta execução é utilizável e declarado: 39 instantes distintos entre 117,3 s
  e 303,3 s, intervalo mediano de 4,0 s, máximo de 22,5 s; duração **inferida** e rotulada
  como inferida; pulso 1,5 s → BPM 40 derivado;
- a **estrutura** por intervalo está certa: 6 amostras com notação viraram 1 intervalo
  contíguo de 110,3 a 313,3 s, com o painel, o passo e o mecanismo de tempo declarados;
- o erro é de **recorte de conteúdo**, não de arquitetura.

## Medição seguinte: as FAIXAS FIXAS cortam o painel

Consertadas duas causas (borda do quadro entrando como corda e grupo de linhas com
espaçamento irregular — lacunas 16, 16, 15, 17, **140** px), a leitura mal melhorou
(49 → 56 algarismos, confiança mediana 0,43 → 0,45). Olhando **onde** as linhas ficam:

| instante | faixa escolhida | linhas detectadas (relativas à faixa) | o que é |
| --- | --- | --- | --- |
| 228,1 s (antes) | `topo` (0–400) | `[1, 138, 154, 170, 185, 202]` | 5 da partitura + **borda** |
| 228,1 s (depois) | `topo` (0–400) | `[138, 154, 170, 185, 202, 342]` | 5 da partitura + **1 da tablatura** |
| 228,1 s (com regularidade) | `meio` (300–750) | `[278, 288, 303, 313, 325, 336]` | grupo de 10–15 px: a **região do vídeo** |

A causa é estrutural: **as três faixas fixas não são o painel**. No `(henze) nocturno` a
partitura ocupa o `topo` inteiro e a tablatura **começa em y≈342 e continua abaixo de
400** — ou seja, a tablatura é **cortada pela fronteira entre `topo` e `meio`**: 1 linha
cai no `topo`, as outras 5 no `meio`. Nenhuma faixa contém as 6 linhas da tablatura.

Contra o que o dono do projeto descreveu — *"a tablatura varia entre topo e base, e **não
muda de lugar durante o vídeo**"* —, procurar o painel em **três faixas fixas** é a
modelagem errada. O certo é procurar o painel **no quadro inteiro**: achar o grupo de 6
linhas **igualmente espaçadas** em qualquer posição vertical, com o passo na faixa medida
(14–45 px), e só então recortar. A faixa vira **resultado** da busca, não entrada dela.

Custo: a busca no quadro inteiro examina as mesmas linhas que hoje (o perfil de tinta é
uma conta só, sobre o quadro todo) — o que muda é o conjunto de grupos de 6 considerados.
O `tab/varredura` mede **onde** há painel por instante; a mudança aqui é **como** o
enquadramento é derivado.

## RESOLVIDO (mesma data) — e o número antes/depois

Implementada a busca no quadro inteiro (`painel.candidatos_quadro`), a série do marcador
passou a ser montada nas **cordas detectadas** em vez da faixa inteira, a fração da amostra
passou a ser exata e o pulso passou a ser medido entre **ataques distintos**. Mesmo vídeo,
mesmo intervalo (110,3–313,3 s do `sky guitar` / `(henze) nocturno`):

| medida | faixas fixas | **quadro inteiro** |
| --- | --- | --- |
| notas lidas | 143 | 48 |
| algarismos | 49 (34 %) | **48 (100 %)** |
| não-algarismos | 94 (66 %) | **0** |
| confiança mediana | 0,43 | **0,97** |
| casas lidas | 0, 7, 15, 19, 24… | **0, 1, 2, 3, 4** |
| tempo | "medido" na região errada | **medido: 22 ataques, pulso 4,0 s** |

O relatório do MusicXML declara `tempo_medido: true`, `pulso_s: 4.0`, `bpm 15` derivado e
duração **inferida**. Zero notas recusadas.

## A regra nova REPROVAVA tablatura legítima: o `shin izumi` provou

A busca no quadro inteiro trouxe um efeito colateral medido. Em `shin izumi`, 6 vídeos, os
dois critérios **no mesmo quadro**: regra velha (três faixas) dizia `tab` em **6 de 6**;
regra nova dizia `tab_painel` em **1 de 6**.

Fui olhar (`data/saida/frames/shin_diverge.png`, três vídeos, quadro em 0,70 da duração):
**a tablatura está lá, embaixo, nos três** — painel `T A B` com casas (`0 2 0 2 0 0`,
`0 2 0 4 0 5`, `2 2 2 2`) e os diagramas de acorde acima. Ou seja: **a regra velha estava
certa ali e a nova estava errada**. A descrição do dono do projeto (tablatura em todos os
vídeos do canal, embaixo) confere com a imagem.

**Causa**: a busca no quadro inteiro montava o perfil de tinta com `binarizar` (Otsu
**global**), que perde linha fina em quadro de iluminação forte — justamente o caso do
`shin izumi` (parede clara, pessoa iluminada). O `segmentar`, que lê o recorte, já usava a
**cascata** de máscaras (Otsu + contraste local). Medido: sem a cascata, 3 de 4 vídeos do
canal não davam **nenhum** grupo de 6 linhas, nem com limiar frouxo de 15 %.

**Conserto**: `candidatos_quadro` soma os picos de **todas as máscaras da cascata**
(`mascaras_candidatas`), com dois limiares de fração de tinta por máscara. Depois dele,
3 de 4 vídeos do `shin izumi` acham a tablatura (passo ~21 px) onde antes só 1 achava — e o
caso da partitura segue correto: no `sky guitar` (`(henze)`) os cinco instantes continuam
concordando em `y318`, rejeitando a pauta de 5 linhas.

Custo: `escolher` passou de **119 ms** para **295 ms** por quadro (medido), ainda abaixo do
custo de ler o quadro (AV1: ~400 ms).

**Lição registrada**: a regra nova não substitui a velha por decreto. Quando as duas
divergem, a divergência é o dado — e quem decide é o quadro, olhado.

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

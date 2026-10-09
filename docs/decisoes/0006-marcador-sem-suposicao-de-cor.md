# 0006 — O marcador não tem cor fixa: o portão de matiz estava errado

**Data:** 2026-10-09 · **Status:** aceita · **Origem:** descrição do dono do projeto,
confirmada por medição

## O que o dono do projeto disse

- `sky guitar`: *"sempre tem marcador, uma faixa, e **não tem cor fixa**"*;
- `guitar dell'arte`: faixa **azul**, mas há vídeos sem marcador;
- `iwaki` e `shin izumi`: **sem marcador**;
- `cifra club`: marcador por **cor no algarismo**, não faixa;
- `violaodecria`: **0 vídeos com marcador**.

## O que a medição mostrou

`tab/cursor.detectar_cursor` tem portão de **matiz fixo (85–140)**, herdado de quando o
cursor medido era azul (`skyguitar`, rodada 1: matiz 109). Medido agora no `asturias`
(1044 s), com o portão **aberto** para qualquer matiz:

| instante | portão fechado (85–140) | portão aberto |
| --- | --- | --- |
| 208,8 s | — | — |
| 365,3 s | — | — |
| **521,9 s** | — | **x=312, matiz 13, sat 101** |
| 678,5 s | — | — |
| **835,0 s** | — | **x=308, matiz 14, sat 123** |
| **939,4 s** | — | **x=308, matiz 13, sat 112** |

A faixa existe, é **laranja/vermelha (matiz 13–14)**, e aparece só na **segunda metade** do
vídeo — exatamente como o dono do projeto descreveu: a primeira parte é a execução sem
tablatura, a segunda é a execução lenta com partitura e tablatura.

**O portão de matiz estava rejeitando o marcador certo.** Isso explica a varredura ter
dado cursor em 69 de 3.993 vídeos: o detector exigia azul.

## Decisão

O detector de marcador **não pode supor cor**. Passa a:

1. procurar **banda vertical estreita** no recorte do painel, sem portão de matiz —
   exigindo apenas contraste/saturação contra o fundo e a geometria (estreita: ≤6 % da
   largura; alta: ≥50 % da altura do painel);
2. montar a série `x(t)`;
3. **aceitar como marcador só se a série tiver sentido único** (`desliza`, ou `salta` com
   patamares) — `tab/tempo.resumo`, que já rejeita `parado` e `erratico`.

Ou seja: a cor deixa de ser critério e **o movimento passa a ser o critério**. Isso é
melhor em três frentes: cobre canal de cor variável (o dono do projeto já avisou que ela
varia), não depende de constante calibrada à mão por canal, e o que sobra de falso
positivo (elemento colorido e parado, como o do `sky guitar` #4) cai no veredito
`parado`/`erratico` em vez de virar tempo.

## Consequências

- a varredura por instante mede **presença de painel**, não de marcador — a decisão sobre
  marcador só vale com a série no tempo, e é isso que o `tab/tempo.py` faz;
- `cursor.py` mantém o portão de matiz como **opção** (há canal azul), mas o padrão passa a
  ser sem portão de cor;
- o custo sobe: montar a série custa uma varredura de 0,25 s por amostra sobre o vídeo, o
  que só se paga no trecho de notação — não no vídeo inteiro.

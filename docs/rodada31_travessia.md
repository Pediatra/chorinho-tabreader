# Rodada 31 — tempo por travessia: melhora, mas ainda não resolve

## 1. O que foi implementado

- `serie_cursor`: série x(t) do cursor **sem exigir patamar** (o cursor que desliza nunca para);
- `tempos_por_travessia`: o instante da nota passa a ser **quando x(t) cruza o x da coluna**,
  interpolado entre amostras;
- `completar` corrigido: tolera `t_fim` nulo (antes estourava `TypeError`).

## 2. Comparação medida (vídeo `shin izumi / 3 easy songs`, janela com cursor, 247 amostras)

| método | notas | instantes distintos |
| --- | --- | --- |
| patamar (o que eu tinha) | 36 | **3** |
| **travessia (novo)** | 36 | **5** |

Melhora, mas **5 instantes para 36 notas ainda não é um tempo por nota**.

## 3. Por que ainda não basta (e não é bug do método)

A janela medida tem **4 segundos de cursor** (0–4 s) enquanto a linha tem 36 notas espalhadas por
toda a largura. Em 4 segundos o cursor percorre apenas **uma fração da pauta** — logo só algumas
colunas são de fato atravessadas.

Ou seja: o problema deixou de ser *como* ler o cursor e passou a ser **qual trecho transcrever**.
Transcrever uma janela curta de um sistema longo dá tempo para poucas notas — corretamente.

## 4. A correção que falta

Transcrever **por sistema**, não por janela arbitrária:

1. acompanhar o cursor até ele completar **uma passagem inteira** da largura da pauta;
2. aí cada coluna da linha tem a sua travessia;
3. o tempo passa a valer **por sistema** (que é como a música é lida), e o JSON ganha o intervalo
   do sistema em vez de um recorte de 25 s.

Isso também resolve o defeito de escolher trecho por acaso: o sistema é a unidade natural.

## 5. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura; 54 % com cursor |
| (b) gabarito verificado | 96 glifos / 4 canais |
| (c) classificador multi-classe | **0,805 (3 sementes)** |
| (d) pipeline ponta a ponta | tempo por travessia implementado; **falta transcrever por sistema** |
| (e) escala nos 3.781 | rollout rodado; tempos ainda não utilizáveis |

## 6. Balanço da série de tempo

| rodada | o que fiz | resultado |
| --- | --- | --- |
| 24 | tempo por patamar no vídeo | 0 tempo (cursor glida) |
| 27 | varredura de janelas com cursor | cobertura medida: 54 % dos vídeos |
| 30 | contagem de instantes distintos | **tempos não utilizáveis** (3 para 134 notas) |
| 31 | travessia em vez de patamar | 3 → 5 instantes; **falta a unidade "sistema"** |

Três correções, cada uma revelando a seguinte. O tempo é, de longe, o anexo mais difícil dos três
— mais que o reconhecimento de casa, que já está em 0,805.

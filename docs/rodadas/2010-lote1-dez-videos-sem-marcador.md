# 2010 — Áudio A4: alinhador em 10 vídeos sem marcador (lote 1)

Data: 2026-10-13. Lista, produtos, alinhamentos, `.audio.json` e log em
`data/saida/audio/a4/lote1/` (`lista.json`, `apelidos.json`, `rodar_lote1.sh`, `lote1.log`).
Leitura do HD aprovada pelo dono.

## Escolha

Do censo (`data/saida/censo/censo_cache.jsonl`), vídeos com `tablatura` e
`marcador = "sem_marcador"`, `frac_tablatura ≥ 0,8` e duração de 60 a 360 s; fora os 3 já
usados. Sorteio por canal com semente 2009 (shin izumi, 2º vídeo: semente 2010):

- iwaki, kimny's guitar, shin izumi e transcriptor: 2 vídeos cada;
- guitarous e paolo d'angelo: 1 cada.

Leonardo Ramos e Pablo Romé não tinham vídeo que passasse no filtro.

Cadeia por vídeo: `tab.video` (CPU) → `tab.audio_extrair` → `tab.audio_alinhar` (v2) →
`tab.audio_produto`. **10 de 10 sem erro**, 37 min no total. A leitura da tablatura levou de
75 a 572 s; as outras três etapas, < 10 s.

## Resultado

| vídeo | notas | corda 1 | exibições recusadas | colunas com tempo | cos mediano (aceitas) | alarme* |
| --- | --- | --- | --- | --- | --- | --- |
| iwaki michelle | 157 | 4 % | 0/5 | **116/120** | 0,72 | 0 |
| iwaki fly me to the moon | 498 | 18 % | 1/17 | **346/372** | 0,79 | 1 |
| kimny 群青 | 1195 | 22 % | 1/15 | **531/650** | 0,76 | 0 |
| kimny bach prelude | 750 | 25 % | 0/9 | **550/690** | 0,77 | 0 |
| shin izumi dream is a wish | 454 | 8 % | 2/22 | **205/274** | 0,81 | 2 |
| paolo d'angelo those who wait | 1037 | 14 % | 0/16 | **651/831** | 0,79 | 0 |
| shin izumi giant steps | 354 | 13 % | 10/20 | 75/263 | 0,70 | 9 |
| transcriptor charagua | 362 | 33 % | 4/18 | 124/334 | 0,56 | 2 |
| transcriptor campanitas | 2416 | 14 % | 36/52 | 201/935 | 0,66 | 21 |
| guitarous sakura | 94 | 3 % | 10/10 | **0/62** | — | 7 |
| **total** | | | **64/184** | **2799/4531 (62 %)** | | |

\* exibições recusadas com cos médio ≥ 0,7 (alarme de leitura, rodada 2009).

- **6 de 10 vídeos bons**: 77 a 97 % das colunas com tempo, ≤ 2 exibições recusadas.
- **4 de 10 fracos**. Olhei 2 deles na imagem:
  - **guitarous sakura (0 de 62)**: o produto lê **todas as notas uma corda abaixo**. O "0"
    da 2ª linha vira (3,0), o "2" da 3ª vira (4,2), e a coluna com nota na 1ª linha some.
    Com as cordas trocadas, as alturas esperadas não existem no áudio. É erro de leitura (grade de
    cordas deslocada), da trilha tablatura. Recorte: `quadros/guitarous_sakura_t3.png`.
    Lateral: a nota atual tem um **fundo cinza** (o "3" no recorte). Parece ser um
    marcador, apesar de o censo dizer `sem_marcador`.
  - **transcriptor campanitas (201 de 935)**: o produto lê os acordes certos (7-8-9-9-7).
    A música é **rasgueado**: o mesmo acorde repetido, com batidas abafadas ("X") entre
    eles. Cada "X" é um ataque forte no áudio sem coluna no produto, e acordes vizinhos
    iguais não se distinguem pela altura. É limite do método (alinhador de notas, não de
    batida), não erro de leitura. Recorte: `quadros/transcriptor_campanitas_t10.png`.
  - shin izumi giant steps e transcriptor charagua: **não olhados**. O alarme (9 de 10
    recusadas no giant steps) aponta para leitura.

## Leitura

- Onde o produto lê bem e a música é dedilhada, o alinhador funciona fora dos 3 vídeos de
  partida, em 4 canais (iwaki, kimny, shin izumi, paolo d'angelo).
- As falhas têm duas causas distintas, as duas visíveis no recorte:
  1. leitura da tablatura (cordas faltando ou deslocadas: shin room 335, guitarous sakura);
  2. rasgueado com batidas abafadas (transcriptor campanitas).
- Corda 1 < 8 % é sinal fraco sozinho: o michelle tem 4 % e alinha 116 de 120 (peça de
  iniciante).

## Consequências

1. Pedido à trilha tablatura (via dono): guitarous sakura com as cordas deslocadas em uma.
   Junta-se ao pedido do shin izumi (rodada 2009).
2. Rasgueado (X abafado e setas de batida) precisa de tratamento próprio, ou de recusa
   declarada no produto. Ainda não decidido.
3. Possível marcador cinza no guitarous: conferir o censo.

## Limites

1 vídeo a 2 por canal; tempo não conferido de ouvido neste lote (a precisão de ~100 ms vem
das folhas, em outros vídeos); 2 dos 4 vídeos fracos não olhados.

## Correção (2026-10-13)

A trilha tablatura conferiu o sakura. As cordas estão no lugar: o que acontece é que notas são
**perdidas**, quase todas nas cordas 1 e 2. Os algarismos encostados em hastes de ritmo, em
acordes empilhados ou no fundo cinza são tomados por barline e descartados. A leitura "uma
corda abaixo" acima estava errada; continua sendo erro de leitura (decisão 2004, item 1).

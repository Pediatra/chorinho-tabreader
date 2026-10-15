# 3021 — piloto sem produto: os 11 vídeos lidos

Trilha partitura. Data: 2026-10-15. Sem mudança de código: é medição.

## O que foi feito

Rodei `ler --pasta` (rodada 3019) nos 8 vídeos do piloto que faltavam, na imagem
`chorinho-partitura:dev`, em CPU. Depois reapliquei a armadura do vídeo com a regra da
3020 nos 8 (sem rodar o Audiveris de novo), porque 3 deles leram antes do commit da regra.
A regra nova **não mudou nada** nesses 8.

Log: `data/saida/partitura/diag/piloto_ler_pasta2.txt`; reprocessamento:
`diag/herdar_clave/lote2/`.

## Medição (11 vídeos)

| vídeo | Audiveris ok | pautas | eventos | com erro |
| --- | --- | --- | --- | --- |
| agua de beber | 10/10 | 10 | 403 | 0 |
| athletic theme | 7/8 | 8 | 301 | 1 |
| canon de pachelbel | 6/6 | 6 | 112 | 0 |
| a beam of light | 6/6 | 6 | 98 | 0 |
| amazing grace | 13/13 | 13 | 272 | 0 |
| amores hallaras | 12/12 | 12 | 297 | 0 |
| giant steps | 13/13 | 13 | 428 | 0 |
| blackbird | 20/20 | 20 | 793 | 0 |
| free tab (bryan adams) | 21/23 | 23 | 405 | 2 |
| ólafur arnalds | 10/10 | 10 | 267 | 0 |
| mela | 25/41 | 41 | 265 | 16 |
| **total** | **143/162** | **162** | **3.641** | **19** |

Cerca de 18 s por recorte em CPU; os 8 vídeos levaram 23 min.

## Por que o Audiveris falha: a faixa amarela do cursor

Todas as 19 falhas são "No system found": o Audiveris não acha a pauta e não gera
MusicXML. No mela e no free tab, o programa de partitura pinta de **amarelo** o compasso
que está tocando, e a faixa cobre metade da pauta.

Contei a fração de pixels amarelos em cada recorte (`diag/faixa_amarela/medir.txt`):

| recorte | ok | falha | taxa de falha |
| --- | --- | --- | --- |
| com faixa amarela (> 5%) | 24 | 12 | 33% |
| sem faixa | 119 | 7 | 6% |

A faixa amarela explica a maior parte das falhas, mas não todas. Das 7 falhas sem faixa,
5 são do mela (uma delas, P02b, tem o recorte cortado rente à 1ª linha), uma é do
athletic e uma do free tab.

## Conferência de amostra

O amazing grace P02a está em lá maior (3 sustenidos) e 4 compassos. Conferi contra a
imagem: lá4–dó♯5–lá5 com fá♯3 no baixo, ré♯5 no compasso 2. A leitura bate.

## Limites e próximo passo

- A qualidade da leitura sem produto **não está medida**. Montei um gabarito de 3
  recortes (agua P01a, athletic P01a, canon P06a) para o dono conferir.
- Próximo passo para as falhas: tirar a cor antes do Audiveris (por exemplo, usar o
  maior dos 3 canais, que deixa o amarelo branco e mantém a linha cinza). Isso muda a
  entrada do leitor (regra 9), então precisa ser medido no gabarito R01–R21 antes de
  valer.

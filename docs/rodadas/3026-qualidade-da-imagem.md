# 3026 — a qualidade da imagem e a cobertura do Audiveris

Pergunta do dono (2026-10-18), vendo a conferência da D1: imagem melhor dá pauta mais certa,
sobretudo com muitos elementos na tela? Script:
`data/saida/partitura/diag/qualidade_imagem/medir.py` (só lê). Junta os três gabaritos do dono
(P1, sem produto, D1): 59 recortes conferidos.

Medidas por recorte: entrelinha da pauta no quadro original (px, do `indice.json`), fração de
tinta (cinza < 128), fração de cor (HSV), nitidez (variância do Laplaciano), notas por compasso.

## Resultado

| entrelinha | recortes | certos/(certos+faltando) | certos/lidos |
| --- | ---: | ---: | ---: |
| < 11 px | 10 | 0,868 | 0,970 |
| 11 a 13 px | 12 | 0,885 | 0,981 |
| 13 a 16 px | 7 | 0,868 | 0,953 |
| ≥ 16 px | 30 | **0,934** | 0,982 |

- Correlação de Spearman da cobertura por recorte: tinta **−0,29**, entrelinha +0,11, nitidez
  +0,10, cor +0,03, notas por compasso −0,02.
- **A precisão não muda com a imagem** (0,95 a 0,98 em todas as faixas). O que a imagem pior
  faz é o Audiveris deixar nota de fora.
- Leitura que não sai ("No system found"), piloto + D1, 202 recortes: < 11 px 49/66 saem; ≥ 13
  px 119/125. Mas 16 das 17 falhas abaixo de 11 px são de um vídeo só (mela, faixa amarela,
  hoje apagado do acervo); sem ele, 25 de 26 saem.
- 720p contra 1080p: 0,879 contra 0,904 (7 recortes em 720p).

## Leitura

Apoia a hipótese do dono, com tamanho modesto: pauta grande (≥ 16 px) cobre ~5 pontos a mais, e
tela carregada (tinta) é o fator que mais acompanha a perda. n pequeno e confundido com canal:
os canais de pauta pequena são poucos. É correlação, não causa.

Ampliar com interpolação não é a saída: 3x e 4x pioram (rodada 3003).

## Teste causal: reduzir a pauta grande

`data/saida/partitura/diag/qualidade_imagem/reduzir.py` (resultado em `reduzir.json`,
`reduzir.log`). Os 30 recortes conferidos com entrelinha ≥ 16 px foram lidos de novo pelo
Audiveris na mesma condição da conferência (`x2_margem`): o PNG original (controle) e o PNG
reduzido com INTER_AREA até 11 px de entrelinha. Medida: das notas que o dono marcou `certo`,
quantas a nova leitura ainda acha (alinhamento de eventos, altura sem acidente).

| condição | leitura saiu | notas certas achadas | notas lidas |
| --- | ---: | ---: | ---: |
| controle | 30/30 | 925/925 = **1,000** | 951 |
| reduzido a 11 px | 29/30 | 855/925 = **0,924** | 917 |
| reduzido, sem o que não saiu | 29/29 | 855/902 = 0,948 | 917 |

- O controle reproduz a leitura original nota por nota: o caminho é o mesmo e o efeito é só o
  tamanho.
- 19 dos 30 recortes não perdem nada. A perda está concentrada: taranta de montoya P03a não sai
  ("No system found", 23 notas), R09 −9, R14 −7, danza española P05a −7, 5 miniatures P24a −6,
  spanish romance P07a −5, e outros com −1 a −3.
- A queda (−7,6 pontos; −5,2 sem a leitura que não sai) é do mesmo tamanho da diferença natural
  entre pauta grande e pequena (0,934 contra 0,87–0,89). **O tamanho da pauta causa a perda de
  cobertura**, e explica sozinho a diferença observada. O reduzido não é cópia fiel de uma
  pauta pequena de verdade (não tem a compressão do vídeo naquele tamanho), mas vai na mesma
  direção.

## Consequência

- Dos 59 recortes conferidos com entrelinha, 29 têm pauta < 16 px. Neles há ~5 pontos de
  cobertura a ganhar se a imagem tivesse a resolução da pauta grande.
- Interpolar não devolve o que a redução tirou (3x e 4x pioram, rodada 3003). O ganho só vem de
  informação nova: baixar o vídeo em resolução maior quando existir, juntar vários quadros da
  mesma página (a pauta fica parada; a média de quadros tira compressão) ou super-resolução
  treinada para partitura. A mediana de quadros é a mais barata (já existe em
  `tab/partitura_imagem_mediana.py`, sem GPU nem download); na A1a (rodada 3110) ela só foi
  medida em "a leitura sai ou não", em 6 recortes, nunca em cobertura de pauta pequena.
- Fora disso, a nota que falta continua completada pela tab (rodada 3172, figura `null`).

## Mediana de quadros na pauta pequena (2026-10-18)

`data/saida/partitura/diag/qualidade_imagem/mediana.py` (`mediana.json`, `mediana.log`). Os 29
recortes conferidos com entrelinha < 16 px. Mediana pixel a pixel de até 15 quadros da mesma
página (primeira exibição do índice, ou t ± 3 s), só com quadros parecidos com o do instante t;
leitura do Audiveris `x2_margem` do PNG original (controle) e da mediana.

- Mediana feita em 26 de 29: R20 e R21 (ギタロー, vídeos apagados do acervo) sem quadro; carol of
  the bells P02a sem quadro parecido com o do instante t.
- A mediana fica quase igual ao PNG original: diferença média de 0,0 a 4,9 níveis de cinza (de
  255). O vídeo repete o mesmo quadro e a compressão quase não varia na página parada.

| condição (26 recortes) | saiu | notas certas achadas | lidas | extras (não casam com nota certa) |
| --- | ---: | ---: | ---: | ---: |
| controle | 26/26 | 1376/1376 | 1449 | 73 |
| mediana | 26/26 | 1323/1376 | 1439 | 116 |
| sem flow my tears P06a, controle | 25/25 | 1318/1318 | 1380 | 62 |
| sem flow my tears P06a, mediana | 25/25 | 1316/1318 | 1408 | 88 |

- Nota faltando no gabarito do dono nesses 26: 206. Mesmo que todos os 26 extras a mais fossem
  nota recuperada (não foram conferidos), seria 26 de 206. E não são todos: no 空も飛べるはず
  P07a o dono não marcou nota faltando e a mediana trouxe 4 extras.
- flow my tears P06a (fundo transparente, rodada 3162) quebra com a mediana: 58 → 7 certas.

**A mediana de quadros não recupera a nota que falta.** Não entra no produto. O que a pauta
pequena perde não está no ruído do vídeo, e sim na resolução. Fica só a fonte de resolução maior
(ou super-resolução treinada), e isso não se testa com o que temos hoje.

## Não repetir

- Mediana (ou média) de quadros para tirar ruído de compressão da pauta parada: a página parada
  sai quase igual ao quadro único, e a leitura não muda.

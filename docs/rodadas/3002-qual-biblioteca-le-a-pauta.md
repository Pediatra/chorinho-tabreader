# 3002 — Qual biblioteca lê a pauta (P1 da trilha partitura)

**Data:** 2026-10-13 · **Trilha:** partitura · **Código:** `tab/partitura_omr.py`,
`tab/partitura_avaliar.py`, `tests/test_partitura_omr.py` · **Imagem:** `chorinho-partitura:dev`
(decisão 3001)

## Pergunta

Das bibliotecas prontas de leitura de partitura (OMR), qual lê melhor a pauta dos vídeos, sem
nenhum treino? Ela será a base do ajuste fino (P2).

## Método

- **Entrada**: os 21 recortes de pauta da P1 (`data/saida/partitura/p1/recortes/`, rodada 3001).
  R01–R12 vêm de telas com gabarito de tablatura: greensleeves (pablo romé, telas 1–4), south
  american music (guitar dell'arte, telas 1–3) e gymnopédie (robert lunn, telas 1, 3, 5, 7, 9).
  R13–R21 são de outros canais e não têm referência.
- **Condições**: `nativo` (o recorte como está) e `x2` (ampliado 2x, cúbica, e mais nada).
  É pré-processamento, então conta como entrada do modelo (AGENTS.md, regra 9).
- **Referência de altura (proxy)**: a tablatura do gabarito (`data/gold/ouro_video`, só leitura).
  Cada nota (corda, casa) vira altura em afinação padrão. Como o violão é escrito uma oitava
  acima do som, soma-se 12. As notas a até 6 px uma da outra formam um evento.
  O MusicXML da biblioteca vira uma sequência de eventos (notas com o mesmo início).
  As duas sequências são alinhadas por Needleman-Wunsch (custo 1 − Jaccard, salto 1).
  Cada nota da referência conta como **certa**, **altura errada**, **faltando** ou **inventada**
  (inventada é nota que não existe na tab: é o pior erro).
  A conta é feita por altura exata e por classe de altura (sem oitava).
- **Clave com 8 embaixo** (`clef-octave-change=-1`): o Audiveris grava a altura soada. Ela é
  convertida para a altura escrita em clave de sol simples, que é o que a referência usa.
  Sem essa conversão, o R05 dava 8/85 notas certas no Audiveris x2; com ela dá 73/85.
- **CPU só**, um recorte por vez, timeout de 300 s (oemer: 900 s).

```bash
python -m tab.partitura_omr rodar --biblioteca homr --condicao nativo   # idem x2, audiveris
python -m tab.partitura_omr rodar --biblioteca oemer --condicao x2 --ids R01,R08
python -m tab.partitura_avaliar
```

Resultado completo: `data/saida/partitura/p1/omr/avaliacao.json`.

## Resultado (R01–R12, 546 notas da tab)

| biblioteca / condição | certas (exato) | altura errada | faltando | **inventada** | certas (classe) | saída em | s/recorte |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Audiveris x2** | **479/546 (87,7 %)** | 19 | 48 | **4** | 455/509 | 20/21 | 13,3 |
| homr nativo | 467/546 (85,5 %) | 25 | 54 | 23 | 440/509 | 21/21 | 8,5 |
| homr x2 | 465/546 (85,2 %) | 24 | 57 | 24 | 441/509 | 21/21 | 8,5 |
| Audiveris nativo | 388/546 (71,1 %) | 82 | 76 | 43 | 397/509 | 17/21 | 7,6 |
| oemer x2 | 0/60 (só R01, R08) | — | — | — | — | 0/2 | 462 |

Por vídeo, nota certa por altura exata:

| vídeo | Audiveris x2 | homr nativo |
| --- | ---: | ---: |
| greensleeves (4 recortes) | 106/106 | 106/106 |
| south american (3) | 234/269, 0 inventadas | 217/269, 13 inventadas |
| gymnopédie (5) | 139/171, 4 inventadas | 144/171, 10 inventadas |

## O que os erros mostram

- **Greensleeves sai perfeito nas duas** (106/106): partitura limpa, entrelinha 14 px. Conferi
  a sequência do R01 nota a nota: igual à tab.
- **South american, Audiveris x2: os 15 erros de altura são −1 semitom, 14 deles em R06 e R07.** O vídeo rola a
  partitura, e os recortes R06 e R07 começam no meio do sistema, **sem clave e sem armadura**
  na tela. As duas bibliotecas leem a armadura como 0 sustenidos, e o fá# vira fá. Não é erro
  de leitura: a informação não está no quadro. Conserto óbvio para depois: herdar clave e
  armadura do primeiro quadro do vídeo em que elas aparecem.
- **Gymnopédie**: entrelinha 20 px, linhas grossas, muitos acordes de 3 notas e duas vozes.
  O Audiveris perde mais notas (28 faltando, contra 16 do homr), mas quase não inventa.
  Os −12 que aparecem nas duas são o baixo lido na oitava errada.
- **Audiveris precisa do x2.** No nativo ele falha em 4 de 21 recortes (entrelinha pequena) e
  erra feio onde não há clave (R06: 1/88). No x2 falha só no R21 (guitarous).
- **homr nunca falha** (21/21 com saída) e é mais rápido, mas inventa 6 vezes mais notas.
  Ampliar não muda nada para ele (465 contra 467).
- **oemer não serve**: exit 1 nos dois recortes que rodou (R01 e R08), ~8 min e 5,6 GB cada.
  Foi rodado só em 2 recortes, como planejado, e para aí.

## Conclusão

**Audiveris com ampliação 2x é a base.** Acerta 479 de 546 notas (87,7 %) e só inventa 4.
O homr fica perto em acerto (467), mas inventa 23, e nota inventada é o erro que mais custa.
O homr fica como segunda opinião: onde as duas concordam, a leitura é mais confiável.

## Limites

- **3 vídeos, 12 recortes.** Só três canais (pablo romé, guitar dell'arte, robert lunn) têm
  referência. A diferença de 12 notas entre Audiveris x2 e homr cabe no ruído. A diferença de
  inventadas (4 contra 23) é mais clara.
- **A referência é altura, não ritmo.** A tab não diz duração, pausa nem ligadura. A medida
  diz se a nota está lá e na altura certa, e nada sobre o ritmo lido.
- **Afinação padrão assumida** na conversão tab → altura. Vídeo com capotraste ou afinação
  diferente vai aparecer como deslocamento constante, que o histograma por vídeo mostra.
- R13–R21 (sem referência) só dizem se houve saída e quantas notas.

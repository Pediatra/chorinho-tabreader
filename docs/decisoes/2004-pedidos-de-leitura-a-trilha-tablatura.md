# 2004 — Pedidos da trilha áudio à trilha tablatura (leitura), consolidado

Estado: **proposta da trilha áudio**, para o dono repassar à trilha tablatura (dona de
`tab/video.py`, `tab/painel.py`, `tab/reconhecer.py`, `tab/leitor.py` e `tab/esquema.py`).
Reúne o que as rodadas 2003 e 2009–2012 acharam. A trilha áudio não edita esses arquivos.

## Como a trilha áudio acha erro de leitura

O arquivo `chorinho/audio@1` marca `alarme_leitura` por exibição: o alinhador recusou a
exibição, mas as poucas colunas que casaram com o som casam bem (cos ≥ 0,7). Das telas com
alarme olhadas na imagem, **5 de 6 tinham leitura com falhas**; a sexta era rasgueado,
tratado na rodada 2012. Os arquivos ficam em `data/saida/audio/a5/v21_*.audio.json` e
`data/saida/audio/a4/lote1/v21_*.audio.json`. A lista de telas por vídeo está no fim deste
documento.

## Pedidos, do maior efeito para o menor

| # | o quê | onde foi visto | evidência |
| --- | --- | --- | --- |
| 1 | **Notas lidas uma corda abaixo** (grade de cordas deslocada; a nota da 1ª linha some) | guitarous *sakura*, telas 1–9 | rodada 2010; `data/saida/audio/a4/lote1/quadros/guitarous_sakura_t3.png`; alinhador 0 de 62 |
| 2 | **Corda 1 quase ausente** (4 % das notas, contra 17–27 % nos outros vídeos); pausa lida como nota | shin izumi *room 335* | rodada 2009; `data/saida/audio/a4/shin/quadros/` (telas 12, 25) |
| 3 | **Números de dois algarismos mal lidos** (13, 12, 10, 15, (12) viram 21, 17, 14…); ~25 colunas na imagem, 7 no produto | iwaki *fly me to the moon*, tela 10 | rodada 2011; `data/saida/audio/a4/alarme/quadros/iwaki_fly_me_to_the_moon_t10.png` |
| 4 | **Acordes dentro de elipse ignorados**; acordes 6/6/6, 7/5/5 e 5/5/5 perdidos; ligadura (6)(6) lida como (1,6)(1,0); a corda 6 encosta na borda de baixo do painel | shin izumi *giant steps*, tela 5 | rodada 2011; `data/saida/audio/a4/alarme/quadros/shin_izumi_giant_steps_t5.png` |
| 5 | **Caixa do painel sobe por cima do vídeo** | kimny (*from this place*, todas as telas) | folhas 1 e 2 (rodadas 2005 e 2007) |
| 6 | **Ornamento e arco** no produto (tamanho do glifo; classe `arco`) | MVP | decisão 2002; rodada 2006 |
| 7 | `tab.leitor.pts_nativos(video, t0, t1)` **perde os últimos quadros** da janela (268 PTS onde o ffmpeg decodifica 270) | MVP, 444–453 s | rodada 2003 |
| 8 | Possível **marcador cinza** (fundo da nota atual) num canal que o censo chama de `sem_marcador` | guitarous *sakura* | rodada 2010 |
| 8b | **Painel na partitura em vez da TAB** (notas espúrias), **rótulos "12" lidos como casa**, **início de slide lido como `tecnica`**, coluna faltando repetida em páginas gêmeas | transcriptor *campanitas*, telas 5, 7, 16, 13, 17, 38/20 | rodada 2013; `data/saida/audio/a4/campanitas_alarmes/quadros/` |
| 9 | O X do rasgueado sai como top-1 "15" em `nao_notas` `tecnica`; a trilha áudio depende disso (`TOP1_ABAFADA`). **Avisar antes de retreinar** ou dar ao X classe própria | transcriptor *campanitas* | rodada 2012 |

## Como medir o efeito

Depois de cada conserto, a trilha áudio regera o produto do vídeo, roda o alinhador e
compara colunas com tempo e número de alarmes. Exemplo: sakura com 0 de 62 colunas e 7
alarmes; room 335 com 114 de 552 colunas e 21 alarmes. É uma medida independente da métrica
de glifos, porque vem do som.

## Telas com alarme (v2.1, sem os 8 trechos fora da página da rodada 2014)

- guitarous *sakura*: 1, 3, 4, 7, 8, 9
- iwaki *fly me to the moon*: 10
- shin izumi *dream is a wish*: 19, 20
- shin izumi *giant steps*: 1, 5, 9, 10, 14, 17, 20
- shin izumi *room 335*: 1–5, 7, 12, 15, 16, 18, 21, 22, 25, 28, 33, 40
- transcriptor *charagua*: 6
- transcriptor *campanitas* (descartado pelo dono): 3, 4, 5, 7, 8, 12, 13, 15, 16, 17, 38, 39, 40, 43, 47, 48, 49.
  Rodada 2013: só 3 de 17 são leitura verificada (13, 38, 47). As telas 5 e 7 vêm de painel
  ou rótulo lido como nota. Outras 3 são do método (setas de rasgueado sem X), e 9 não
  foram olhadas.
- sem alarme: MVP, iwaki *la vie en rose*, iwaki *michelle*, kimny *from this place*,
  kimny *群青*, kimny *bach prelude*, paolo d'angelo *those who wait*

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
| 1 | ~~Notas lidas uma corda abaixo~~ **Notas perdidas** (resposta da tablatura: as cordas estão certas; algarismos encostados em hastes, acordes empilhados ou fundo cinza viram barline e são descartados, 19 de 19 numa tela) | guitarous *sakura*, telas 1–9 | rodada 2010 (corrigida); `data/saida/sakura_cordas/` (tablatura); alinhador 0 de 62 |
| 2 | **Corda 1 quase ausente** (4 % das notas, contra 17–27 % nos outros vídeos); pausa lida como nota | shin izumi *room 335* | rodada 2009; `data/saida/audio/a4/shin/quadros/` (telas 12, 25) |
| 3 | **Números de dois algarismos mal lidos** (13, 12, 10, 15, (12) viram 21, 17, 14…); ~25 colunas na imagem, 7 no produto | iwaki *fly me to the moon*, tela 10 | rodada 2011; `data/saida/audio/a4/alarme/quadros/iwaki_fly_me_to_the_moon_t10.png` |
| 4 | **Acordes dentro de elipse ignorados**; acordes 6/6/6, 7/5/5 e 5/5/5 perdidos; ligadura (6)(6) lida como (1,6)(1,0); a corda 6 encosta na borda de baixo do painel | shin izumi *giant steps*, tela 5 | rodada 2011; `data/saida/audio/a4/alarme/quadros/shin_izumi_giant_steps_t5.png` |
| 5 | **Caixa do painel sobe por cima do vídeo** | kimny (*from this place*, todas as telas) | folhas 1 e 2 (rodadas 2005 e 2007) |
| 6 | **Ornamento e arco** no produto (tamanho do glifo; classe `arco`) | MVP | decisão 2002; rodada 2006 |
| 7 | `tab.leitor.pts_nativos(video, t0, t1)` **perde os últimos quadros** da janela (268 PTS onde o ffmpeg decodifica 270) | MVP, 444–453 s | rodada 2003 |
| 8 | Possível **marcador cinza** (fundo da nota atual) num canal que o censo chama de `sem_marcador` | guitarous *sakura* | rodada 2010 |
| 8b | **Painel na partitura em vez da TAB** (notas espúrias), **rótulos "12" lidos como casa**, **início de slide lido como `tecnica`**, coluna faltando repetida em páginas gêmeas | transcriptor *campanitas*, telas 5, 7, 16, 13, 17, 38/20 | rodada 2013; `data/saida/audio/a4/campanitas_alarmes/quadros/` |
| 9 | O X do rasgueado sai como top-1 "15" em `nao_notas` `tecnica`; a trilha áudio depende disso (`TOP1_ABAFADA`). **Avisar antes de retreinar** ou dar ao X classe própria | transcriptor *campanitas* | rodada 2012 |
| 10 | **Observador de marcador não lê** em 9 de 12 canais que o censo chama de faixa/cor (coerência < 0,9) | lote 2: leonardo ramos, robert lunn, kenneth, mr. tabs, tv on guitar, lonelypicker, violaodecria, yunus, vvxo | rodada 2016 |
| 11 | **Troca de página não detectada**: uma tela de 3,75 a 93,1 s com 9 colunas | vvxofingerstyletab *sword art online* | rodada 2016; `data/saida/audio/a4/lote2/quadros/vvxofingerstyletab_sao_t1.png` |
| 12 | **Padrão de ritmo** (pausas e X, sem casa) classificado como tablatura | kenneth acoustic *believer* | rodada 2016; `data/saida/audio/a4/lote2/quadros/kenneth_acoustic_t1.png` |
| 13 | **Leitor `rede`: dois algarismos ligados por tracinho viram um número** ("2·3" → 23, "2·4" → 24, visto no quadro da tela 5): casa errada afirmada. O vídeo tem 32 notas com casa ≥ 13 no `rede` (24 no leitor de glifos); nem todas foram olhadas | kimny *bach prelude* (passo 20,6; telas 1, 3, 5, 6) | rodada 2017; `data/saida/audio/r2017/quadros/bach_t5_zoom.png` |
| 14 | **Leitor `rede`: "10" da corda 1 perdido e nota pequena de ornamento (o 10 do ligado H) lida como coluna** | shin izumi *room 335*, tela 20 (x ≈ 365 e 595 perdidos; x ≈ 455 e 958 são ornamento) | rodada 2017; `data/saida/audio/r2017/quadros/room335_t20_a.png`, `_b.png` |
| 15 | **Leitor `rede`: a ponta da seta de rasgueado é lida como "4" na corda 1** (3 de 6 setas da tela). O som não pega: o 4 da corda 1 está no acorde que se repete | transcriptor *charagua*, tela 6 (x ≈ 392, 743 e 1452) | rodada 2020; `data/saida/audio/r2020/charagua_tela3_setas.png` |

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

## Resposta da trilha tablatura (2026-10-13)

1. Sakura: não é deslocamento de corda, é nota perdida (item 1 corrigido). Duas correções
   foram medidas e reprovadas; sem conserto por ora.
2. Room 335, corda 1: vão medir com o ouro que o dono está rotulando. A causa provável é a
   mesma do sakura.
3. Dois algarismos: fica para depois, porque pede retreino (o gerador cobre as casas 0 a 7).
4. Marcador não lido (item 10): começam agora, por leonardo ramos e mr. tabs.
5. Ritmo do kenneth e página do vvxo (itens 11 e 12): na fila, depois do marcador.
6. X do rasgueado (item 9): o leitor do produto continua o `oficial_3`. A trilha tablatura
   avisa antes de trocá-lo, e a troca virá com classe própria para o X.

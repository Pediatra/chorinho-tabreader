# 3161 — D1: escolha do recorte, leitura e itens da conferência (porta 8121)

Frente D (amostra para um gabarito que vale para o acervo), rodada 3161. Lista final: `amostra_final.json`
(commit `86133016`, 40 vídeos). Briefing: `docs/pesquisa/partitura-onda1-briefings.md`.

**Escolha do recorte.** Um recorte com pauta por vídeo, sorteado com `random.Random("0:<vídeo>")` entre
os recortes com pauta de `videos/<slug>/recortes/indice.json` (módulo `tab/partitura_amostra_ler.py`).
Não é o "mais legível". Resultado em `escolha_recortes.json`: 40 de 40 escolhidos.

**Leitura.** `ler_pasta` (Audiveris + homr) só nos 40 recortes escolhidos, grava dentro de
`videos/<slug>/`. Estado `lido` do `ler_pasta` não garante leitura: o Audiveris pode sair sem
MusicXML. Ficaram sem leitura 5 recortes (cobertura 0, ficam no conjunto):
- `guitar dell ́arte/el choclo⧸kiss of fire (a. villoldo), guitar arrange` — recorte P02a
- `robert lunn/3 middle eastern guitar pieces (vol. 2) - with sheet music` — recorte P03a
- `sky guitar/the phantom of the opera - fingerstyle lesson + tab.mp4` — recorte P02a
- `sky guitar/minuet (bach) - guitar lesson + tab.mp4` — recorte P03a
- `tv on guitar/mario wonder overworld theme tab & std notation ｜ tvongui` — recorte P19a

**Itens.** `tab/partitura_amostra_itens.py`: cópia de `_item_sem_produto` e `preparar_sem_produto`
do `partitura_gabarito`, com uma única mudança: a pasta de origem é `videos/<slug>/` da frente D.
Gera `itens_d1.json` (35 itens) e `ouro_d1_copia.json` (cópia vazia). O gabarito real não é tocado.

**Servidor.** `python -m tab.partitura_gabarito servir --itens ... --ouro ouro_d1_copia.json --porta 8121`
respondeu 200 num container de teste (`-p 127.0.0.1:8121:8121`), parado depois.

**Remendo do paginar.** `tab/partitura_amostra_paginar.py` troca `_forca_de_linha` por uma cópia com faixa
vazia = 0. O `tab/partitura_video.py` não foi editado (decisão da sessão principal).

**Não feito.** A conferência do dono (porta 8121) não foi feita: os itens estão prontos para ele.

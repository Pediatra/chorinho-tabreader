# 3015 — Armadura, compassos e o x como reserva do par

**Data:** 2026-10-15 · **Trilha:** partitura (P3) · **Código:** `tab/partitura_video.py`
(`reparear_por_x`, `_compassos_do_recorte`, `_fifths_origem`), `tests/test_partitura_video.py`

Fecha o que faltava no `<stem>.partitura.json` da rodada 3014, dentro da trilha partitura.
O tempo (`t_ini`) continua com a trilha tablatura.

## O que entrou

- **`fifths` e `fifths_origem` por pauta.** A armadura vem da leitura herdada. A origem é
  `video` quando a armadura do vídeo foi aplicada a um recorte sem clave, e `leitura` nos
  outros casos.
- **`compassos` por pauta**, cada um com `numero`, `fracao` e `x_quadro`. O x é o `left` do
  compasso no `.omr`, dividido pela escala 2 e somado a x0.
- **`reparear_por_x`.** Quando o par pela altura não tem x conferido, ou quando o evento
  ficou sem par, o evento pega a coluna livre mais próxima em x, se ela estiver a até uma
  entrelinha. Cada `par` ganha `metodo` (`altura` ou `x`).
  - Coluna já segurada por um par conferido nunca é tomada.
  - Nada é descartado: sem coluna perto, o evento fica com o par antigo.

## Medição

| | antes | depois |
| --- | ---: | ---: |
| Gym tela 10, pares com x conferido | 0 de 14 | **10 de 14** (10 por x) |
| outras 18 telas | — | iguais (0 par por x) |
| x conferido, total dos 3 vídeos | 423 de 438 | **433 de 438** |
| notas certas contra o gabarito (19 telas) | 723/767 | 723/767 (o `completar_com_homr` não mudou) |

Armadura lida:

| vídeo | fifths |
| --- | --- |
| greensleeves | 1 nas 4 telas |
| south american | 1 nas 3 telas (2 vieram do vídeo) |
| gymnopédie | 4 nas telas 1–11 |

As alturas conferem com a tab (rodada 3014), então a armadura lida está coerente.

## Limites

- **Gym tela 12:** `fifths` 1. É o cartão estreito com um acorde só. A leitura tem clave,
  então a armadura do vídeo não é herdada. Valor provavelmente errado; não corrigido.
- **`fracao`:** só sai na pauta que desenha a fórmula de compasso, o primeiro sistema de
  cada vídeo (3 de 19). Nas outras pautas fica `null`. Quem consome herda da pauta
  anterior.
- **Gym tela 10:** o x acha a coluna certa, mas a altura da tab continua errada (cordas
  deslocadas). O conserto é da trilha tablatura.
- **Os 4 pares que sobram sem x conferido:** sem coluna livre a até uma entrelinha.

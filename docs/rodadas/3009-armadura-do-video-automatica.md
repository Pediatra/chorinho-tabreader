# 3009 — Armadura do vídeo, automática

**Data:** 2026-10-14 · **Trilha:** partitura · **Código:** `tab/partitura_omr.py`
(`armadura_do_video`, `herdar_condicao`, subcomando `herdar`), `tab/partitura_avaliar.py`
(condição `x2_margem_herdada`)

## Pergunta

Na rodada 3007, a armadura do vídeo foi passada à mão. Dá para tirá-la sozinha das leituras do
mesmo vídeo que mostram a clave?

## Regra

- **Armadura do vídeo:** maioria das leituras do vídeo que têm `<clef>`. Leitura com clave e
  sem `<key>` vale 0. Empate vai para a armadura com menos acidentes.
- **Aplicação:** cada leitura sem clave (recorte que começa no meio do sistema) recebe
  `herdar_armadura`.

```bash
python -m tab.partitura_omr herdar --biblioteca audiveris --condicao x2_margem
python -m tab.partitura_avaliar
```

## Resultado (R01–R12, 546 notas da tab)

| condição | certas | altura errada | faltando | inventada |
| --- | ---: | ---: | ---: | ---: |
| x2_margem | 491 | 14 | 41 | 3 |
| x2_margem_herdada | **494** | 11 | 41 | 3 |

Dos 21 recortes, 17 têm clave.

- **R06 e R07** receberam 1 sustenido, vindo do R05. R06 sobe de 79 para 81 de 88, e R07 de
  88 para 89 de 96.
- **Ficaram sem armadura:**
  - R17: é o único recorte do vídeo e não tem clave.
  - R21: o Audiveris não leu.

## Os 5 erros que sobram no R06 não são de armadura

O Audiveris leu **bemóis que não existem** (si bemol e sol bemol) nos compassos 7 e 11. Na
imagem ampliada (`data/saida/partitura/diag/r06_zoom.png`), são si e sol naturais, sem nenhum
acidente.

Na conferência, o dono marcou essas notas como certas. Provavelmente o bemol desenhado passou
despercebido. O caso fica para a próxima rodada de conferência. O gabarito não foi alterado.

## Limites

- **Amostra:** só um vídeo da amostra precisa de herança.
- **Leitura errada na origem:** se a clave for lida, mas a armadura sair errada, a maioria
  pode herdar o erro.

# 3012 — Troca de altura desmentida pela tab

**Data:** 2026-10-15 · **Trilha:** partitura (P3) · **Código:** `tab/partitura_pareamento.py`
(`completar_com_homr`, campo `trocadas` do `EventoPartitura`), `tests/test_partitura_pareamento.py`

**Autorização:** o dono aceitou a troca em 2026-10-15 "se for para a melhora geral".

## Pergunta

Na rodada 3011, em 5 eventos o Audiveris leu uma altura errada, e o homr acrescentou a
certa ao lado. A errada ficava e contava como inventada.

Tirar a nota do Audiveris que a tab desmente melhora o total?

## Regra

- Só quando o homr completa um evento com nota que a tab confirma, as notas do Audiveris
  desse evento que a coluna da tab não tem saem do evento.
- Elas vão para o campo `trocadas`. Ficam guardadas no JSON, não são apagadas.
- Sem nota do homr confirmada, nada é trocado. A tab sozinha não corrige altura.

## Resultado (R01–R12, 546 notas da tab)

| | certas | altura errada | faltando | inventada | notas erradas (altura errada + inventada) |
| --- | ---: | ---: | ---: | ---: | ---: |
| saída única (3011) | 526 | 6 | 14 | 8 | 14 |
| **+ troca pela tab (3012)** | **526 (96,3 %)** | 5 | 15 | 3 | **8** |

Trocas feitas: 6.

- R06, compasso 7: Bb4 → B4, Bb4 → B4, Gb4 → G4 (homr).
- R06, compasso 11: Bb4 → B4, Bb4 → B4 (homr).
- R11, compasso 6: G#5 saiu, ficou A3 (homr).

## O que os números dizem

- As certas não sobem (526). A nota certa já tinha entrado pelo homr. O ganho é tirar as
  erradas.
- Notas erradas caem de 14 para 8. As inventadas voltam a 3.
- As 5 trocas do R06 são exatamente os bemóis que o Audiveris inventou nos compassos 7 e 11.
  A imagem mostra naturais.
- O dono tinha marcado esses símbolos como certos no gabarito (rodada 3004). Isso continua
  para a próxima conferência. O gabarito em `data/gold` não foi mexido.
- R11: o G#5 saiu e o faltando subiu 1 (14 → 15). Aquela nota contava como altura errada,
  pareada com uma nota da tab. Fica para conferir na imagem na próxima rodada de conferência.
- Pareamento sem mudança: 336 de 337 pares no mesmo x.

## Limites

- **Amostra:** 3 vídeos e 12 recortes.
- **Régua:** a tab, não o gabarito do dono.
- **Escopo:** a regra só vale em vídeos com tab.

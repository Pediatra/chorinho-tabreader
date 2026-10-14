# 3006 — P3, primeiro passo: nota do homr só entra se a tab confirma

**Data:** 2026-10-14 · **Trilha:** partitura (P3 liberada pelo dono nesta data) · **Script:**
`data/saida/partitura/diag/fusao_filtrada_tab.py`

## Pergunta

Na rodada 3005, a união cega de homr e Audiveris inventou ~130 notas. E se a nota do homr
entrar só quando a tab do mesmo trecho tem a mesma altura no evento correspondente?

## Método

- **Recortes:** R01–R12, com 546 notas da tab, mesma referência das rodadas 3002 e 3003.
- **Alinhamento:** Audiveris x2_margem e homr nativo são alinhados, cada um, com a sequência
  da tab (Needleman-Wunsch, a régua da avaliação).
- **Aceite:** uma nota da tab que o Audiveris não cobre é aceita do homr quando o evento do
  homr casado com o mesmo evento da tab tem exatamente essa altura MIDI.
- **Inventadas:** por construção, nenhuma nota nova é inventada.

## Resultado

| | certas | faltando ou altura errada | inventadas |
| --- | ---: | ---: | ---: |
| Audiveris x2_margem | 491/546 (89,9 %) | 55 | 3 |
| + homr confirmado pela tab | **523/546 (95,8 %)** | 23 | 3 |

- **Por recorte**, notas recuperadas de quantas faltavam: R05 4/5, R06 6/9, R07 5/8, R08 6/9,
  R09 0/3, R10 5/7, R11 3/8, R12 3/6. R01–R04 já estavam completos.
- **Figura das 32 notas recuperadas**, que vem do homr: 17 mínimas, 5 semínimas,
  6 colcheias e 4 semicolcheias. **Não conferida**, porque essas notas não estavam na leitura
  que o dono conferiu.

## Leitura

- Com a tab como filtro, o homr passa a ajudar: recupera 32 das 55 notas que faltavam, sem
  inventar nada.
- As 23 que sobram não aparecem com a altura certa em nenhuma leitura. A altura delas vem da
  tab, mas a figura não tem fonte. É a próxima pergunta da P3.
- A figura das notas recuperadas precisa de conferência. As mínimas recuperadas (17) são, em
  boa parte, o baixo do robert lunn, que o Audiveris perde em acordes.

## Limites

- **Amostra:** 3 vídeos e 12 recortes.
- **Posição aproximada:** o aceite usa o posto do evento no alinhamento, não a posição x.
- **Contra a tab:** a medida é feita contra a tab, não contra o gabarito do dono.

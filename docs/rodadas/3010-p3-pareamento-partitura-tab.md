# 3010 — P3: pareamento partitura × tab, conferido pela posição na tela

**Data:** 2026-10-14 · **Trilha:** partitura (P3) · **Código:** `tab/partitura_pareamento.py`,
`tests/test_partitura_pareamento.py` · **Protótipo:** `data/saida/partitura/diag/p3_pareamento.py`

## Pergunta

A regra do dono é que o tempo da partitura vem da tab. Para isso, cada evento da partitura
tem que ser ligado à coluna certa da tab. O pareamento por sequência (Needleman-Wunsch sobre
as alturas) acerta a coluna?

## Método

- **Conferência independente: a posição.** A pauta fica em cima da tab, alinhada na vertical.
  Se o par está certo, a nota e a coluna caem no mesmo x do quadro.
- **x da partitura:** sai do `.omr` do Audiveris (`stack left` + `slot x-offset`, na imagem
  2x), somado a `caixa_recorte[0]`.
- **x da tab:** `x_centro_quadro` das notas do gabarito da tela.
- **Tolerância:** 1 entrelinha.
- **Leitura usada:** Audiveris x2_margem_herdada.

```bash
python -m tab.partitura_pareamento   # grava data/saida/partitura/p3/pareamento/<id>.json
```

## Resultado (R01–R12)

| | valor |
| --- | ---: |
| eventos da partitura pareados | 326 de 326 |
| **pares no mesmo x** | **325 de 326** |
| mediana da distância | 0,5 a 2,7 px |

- **O único par fora da tolerância** fica no R05: evento 2 da partitura (x 188), pareado com a
  coluna em x 235,5, a 47,5 px. É troca de par, não erro de posição.
- **Eventos da tab sem par** (16): são as notas que a partitura não leu (rodadas 3004 e 3006).

## O tempo

- O tempo de cada evento da partitura é o `t_ini` da coluna da tab pareada. Não há medidor
  próprio.
- O gabarito de tab não tem `t_ini` por nota.
- Nas saídas da trilha tablatura para esses vídeos (`fase8/medida`), a conta é
  `notas_com_tempo: 0`.
- Então o tempo da partitura aparece quando a trilha tablatura entregar `t_ini`. O encaixe já
  está pronto.
- **Instantes do dono:**
  - no south american (marcador que salta), 37 de 40 instantes caem numa coluna pareada com a
    partitura no mesmo x;
  - no greensleeves (marcador que desliza), o instante marca o cursor entre colunas, e o
    tempo por nota exige a interpolação da trilha tablatura.

## Limites

- **Amostra:** 3 vídeos e 12 recortes.
- **Leitura de entrada:** o x vem só do `.omr` do Audiveris. Leitura do homr não tem posição.
- **Repetições:** uma coluna tocada duas vezes (repetição) terá dois `t_ini`, e o evento da
  partitura herda a lista.

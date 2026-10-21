# 0211 — Recorte alto no rótulo de ataque

Segue a [0210](0210-diagnostico-recorte-do-painel.md). Escrito **antes** de medir e de treinar.
O dono pediu o caminho curto em 2026-10-20.

## A mudança de código (só esta)

- `painel.recorte_alto(quadro, c)`: o recorte do candidato aumentado no quadro até 2,5 passos
  acima da corda 1 e abaixo da 6 (`FOLGA_DETECTOR_PASSOS`, igual a
  `detector_tab.MARGEM_PASSOS`).
  - As colunas e as cordas são as mesmas.
  - Se o `roi` não é um recorte cru do quadro, ele fica como está.
- Usam o recorte alto:
  - `ataque_r4.ler_tela`, com `recorte="alto"` como padrão e `"painel"` para refazer o antigo;
  - `ataque_r4 medir --recorte`, que grava em `medida_<v>_s<s>_alto.json` sem apagar as antigas;
  - `tab.video` **só** com `--rotulo-ataque`. A leitura comum (`DETECTOR_PADRAO`) não muda.
- Conferido: com o `_atqt`, a T8.3 dá 5 · 5 · 5 /71, igual ao `diag/recorte_alto.py`.

## Fase 1 — sem treino

`_atqt` e `_atqe`, 3 sementes, recorte alto, nos ouros (pela dobra fora) e na T8.2 (dobra 0).

- Os limiares são escolhidos nos ouros, como sempre (`escolher_limiar` e `escolher_nao_sei`).
- A casa dos ouros com o recorte alto é comparada com a do recorte antigo, porque o recorte é
  entrada do modelo (regra 9).

## Fase 2 — treino com o recorte alto

- O cache real (ouros, T8.2) é refeito com o recorte alto, em pastas novas (`n4/*_alto`). O cache
  antigo fica.
- `treinar_ft.py --recorte-alto` lê essas pastas.
- O G11–G12 volta a ligar (`P_CADEIA` 0,25, `P_ARCO_ALTO` 0,25), porque a 0210 mostrou que ele
  ajuda quando o arco chega ao modelo.
- São 15 treinos `--ataque --t82 --recorte-alto`, com o nome `_atqa_s<semente>`. A medida é a da
  fase 1.

## Decisão do produto

- Entre `_atqt`, `_atqe` e `_atqa`, todos com o recorte alto, fica o de menor "sim" falso nos
  ouros, na faixa com os limiares escolhidos nos ouros e somadas as 3 sementes.
- Desde que:
  - o custo nos ouros fique ≤ 10 %;
  - a casa dos ouros não caia abaixo do pior `_atqt` com o recorte antigo.
- Muda o `ataque_rotulo.DETECTOR_CALIBRADO` e os limiares, se for o caso.
- A T8.3 é só informada: ela foi usada na 0210.
- **A validação é a T8.4**, um lote novo que o dono confere. O aceite é o do plano: "sim" falso
  ≤ 5 % e custo ≤ 10 %.

## Resultado da fase 1 (2026-10-20)

Medidas em `r4a/medida_{atqt,atqe}_s{1,2,3}_alto.json`. Os limiares escolhidos nos ouros não
mudam com o recorte: `_atqt` com técnica 0,15 e `L` 0,02; `_atqe` com técnica 0,25 e `L` 0,02.

| pesos | recorte | ouros, "sim" falso | ouros, custo | ouros, casa | T8.2, "sim" falso |
| --- | --- | --- | --- | --- | --- |
| `_atqt` | antigo | 4 · 5 · 4 /85 | 100–108 /2593 | 2660–2665 | 2 · 2 · 2 /45 |
| `_atqt` | alto | 4 · 4 · 4 /85 | 99–104 /2593 | 2661–2667 | 2 · 2 · 2 /45 |
| `_atqe` | antigo | 3 · 3 · 3 /85 | 109–122 /2593 | 2659–2663 | 2 · 2 · 2 /45 |
| `_atqe` | alto | 2 · 2 · 2 /85 | 104–123 /2593 | 2659–2664 | 2 · 2 · 2 /45 |

- **A casa não piora com o recorte alto.** Nos ouros ela fica em 2659–2667, contra 2660–2665 no
  antigo.
- Nos ouros e na T8.2 quase não há arco acima do sistema, então eles mudam pouco. A diferença
  aparece na T8.3, na 0210.
- O custo nos ouros fica em 4–5 %, dentro dos 10 %.

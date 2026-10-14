# 3005 — O homr completa as notas que o Audiveris perdeu? Não sem filtro

**Data:** 2026-10-14 · **Trilha:** partitura · **Script:** `data/saida/partitura/diag/fusao_homr.py`
· **Gabarito:** `data/gold/partitura/leitura_p1.json` (rodada 3004)

## Pergunta

Na rodada 3004, o dono marcou 78 notas faltando na leitura do Audiveris. Se as leituras do
homr e do Audiveris forem juntadas, quantas dessas notas voltam, e quantas notas inventadas
entram junto?

## Método

- **Alinhamento:** as sequências de eventos do Audiveris x2_margem e do homr nativo são
  alinhadas por Needleman-Wunsch, com a mesma regra da avaliação.
- **Acréscimos do homr**, de dois tipos:
  - nota que falta num evento casado (completa o acorde);
  - evento inteiro que só o homr viu.
- **Posição de cada acréscimo:** coluna de cabeças do Audiveris no `.omr` (bounds ÷ 2). Num
  evento inteiro, o acréscimo fica no intervalo entre os vizinhos.
- **Degrau da pauta:** sai da posição y em relação à linha do meio. Conferência: 796 de 796
  cabeças do Audiveris dão o mesmo degrau que o próprio Audiveris grava.
- **Recuperada:** clique de faltando do dono com um acréscimo no mesmo degrau, dentro do
  intervalo x ± 1,5 entrelinha (casamento um a um). Acréscimo sem clique conta como inventado.
- **Recortes:** 20 (o R21 já é leitura do homr), com 74 cliques. Nos recortes R01–R12, a
  conta também é feita contra a tab, com a régua da rodada 3003.

## Resultado

| medida | Audiveris só | Audiveris + homr (união) |
| --- | ---: | ---: |
| cliques de faltando recuperados | — | **31/74** (32 com ±1 degrau) |
| acréscimos do homr | — | 164 (133 sem clique) |
| tab R01–R12: certas | 491/546 | 520/546 |
| tab R01–R12: faltando | 41 | 10 |
| tab R01–R12: **inventadas** | **3** | **43** |

Por tipo de acréscimo:

| tipo | acréscimos | casam com um clique |
| --- | ---: | ---: |
| completar acorde | 102 | 14 |
| evento só do homr | 62 | 17 |

Nenhum dos dois tipos serve sozinho.

## O que os números dizem

- **A união cega não paga.** Recupera 31 notas e inventa ~130. Contra a tab, ganha 29 certas e
  perde 40 em inventadas, e nota inventada é o pior erro.
- **O homr também não vê a maioria das faltando:** 43 das 74 não estão em nenhuma das duas
  leituras.
- **Só a tab separa acréscimo bom de ruim.** Aceitar a nota do homr só quando a tab tem a
  mesma altura no evento casado zera as inventadas por construção. Isso, porém, já é
  pareamento partitura × tab (P3), que só começa com aviso do dono.
- **R20:** o dono anotou que a leitura ficou incompleta, mas não marcou nenhuma nota faltando.
  Os 25 acréscimos do homr ali contam como inventados. Pode haver subcontagem nesse recorte.

## Limites

- **Posição aproximada.** A coluna do evento vem do posto, e em 6 recortes o número de colunas
  do `.omr` difere do número de eventos.
- **Inventada é estimativa.** Acréscimo sem clique conta como inventado, mas ele pode
  corresponder a um símbolo que o dono marcou com altura errada.

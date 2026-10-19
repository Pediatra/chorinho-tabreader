# 0204 — R4c: traço, slide curto e arco raso no gerador

Segue a [0203](0203-r4b-arco-no-gerador.md). Com o gabarito corrigido, o R4b ficou em
"sim" falso de 13–18 % nos ouros e 31–36 % na T8.2 (limiar 0,15). Escrito **antes** de
treinar.

## O que escapa no R4b

Na folha de `r4b/erros/`, com o limiar 0,15 e as 3 sementes:

- **alarmes**: 10 no South American, em `3-0-3`. Os algarismos são pequenos e quase
  encostados, então a corda aparece entre eles como um traço. Há outros no From This Place
  (`5-4-2`);
- **perdidas**:
  - o slide desenhado como um risco curto entre dois números (`1/2` no La Vie en Rose, `2/4`
    no From This Place), com escore perto de 0;
  - o arco muito longo e raso (Room 335 t4, t16 e t27, e Shin Izumi).

## O que muda (`tab/sintetico_sistema.py`)

| id | mudança | rótulo |
| --- | --- | --- |
| G8 | colunas apertadas com chance de 0,3 (antes 0,2). Em metade delas, algarismos pequenos (0,45–0,65 passo), e uma corrida de 3 a 5 notas seguidas numa corda só | nenhuma técnica (atacada) |
| G9 | slide: em metade dos casos, um risco curto, mais inclinado, deslocado para cima da corda e encolhido nas pontas | o de hoje (`/` ou `\` na chegada) |
| G10 | arco longo de 2 a 6 colunas (antes 2 a 4); em metade dos casos, raso (ponta a 0,45–0,65 passo da corda, curva de 0,15–0,4 passo) | o de hoje, na chegada |

Folha: `data/saida/tab_rotulo/r4c/folha_gerador_{1,2,3}.png` (`folha_gerador.py`), com 6
sistemas de cada variante, olhada antes de treinar.

## Treino e medida

- Igual ao R4b, com o nome `_atqc_s<semente>`: 15 treinos, roteiro `r4c/rodar.sh`.
- A medida é `tab.ataque_r4 medir --versao atqc`, com a regra do slide.
- O limiar da técnica é escolhido do mesmo jeito: só nos ouros, o menor com "não" em
  atacada até 1 %. Depois ele vale sem mudança na T8.2.
- **Base**: o `_atqg` com o gabarito corrigido, a 0,15: ouros 13 · 11 · 15 /85 e T8.2
  14 · 16 · 14 /45.

## Aceite (o do plano, sem mudança)

- "Sim" falso **≤ 5 %**, e "não" em atacada **≤ 10 %**, nos ouros e na T8.2, separados.
- A casa não piora além da amplitude das sementes.

**Pare se** o "sim" falso na T8.2 não cair além da amplitude do `_atqg` (14–16/45). Nesse
caso, o próximo passo é o arco como objeto próprio (A2), e não mais estilo no gerador.

## Resultado (2026-10-19)

- O primeiro treino caiu em 2026-10-18 às 23:09: a placa sumiu do barramento (Xid 79). Depois
  de reiniciar, os 15 treinos `_atqc` terminaram sem erro (`r4c/treino_*.log`; o log da queda é
  `treino_atqc_d4_s1_queda_gpu.log`).
- Tabela: `r4c/tabela.py`. O limiar escolhido nos ouros é **0,15** (0,59 % de "não" em
  atacada). Sementes `s1 · s2 · s3`.

| teste | medida | `_atqg` 0,15 | `_atqc` 0,15 |
| --- | --- | --- | --- |
| 8 ouros | "sim" falso | 13 · 11 · 15 /85 | 13 · 12 · 10 /85 |
| 8 ouros | "não" em atacada | 29 · 21 · 23 /~2590 | 16 · 16 · 14 /~2588 |
| 8 ouros | casa | 2646 · 2650 · 2650 /~2675 | **2636 · 2649 · 2633** /~2673 |
| T8.2 | "sim" falso | 14 · 16 · 14 /45 | 16 · 14 · 15 /44–45 |
| T8.2 | "não" em atacada | 6 · 10 · 9 /~1482 | 9 · 9 · 13 /~1478 |
| T8.2 | casa | 1518 · 1525 · 1519 /~1527 | 1515 · 1515 · 1520 /~1522 |

Folha dos erros a 0,15 (`r4c/erros/`, comparada com `r4b/erros/`, as duas com o gabarito
corrigido):

| | `_atqg` | `_atqc` |
| --- | --- | --- |
| alarmes ("sim" lido como "não") | 34 | 24 (South American 10 → 6, From This Place 10 → 7) |
| perdidas ("não" lido como "sim") | 30 | 30 (mordente 15 → 16) |

## Leitura

- **A regra de parada dispara.** O "sim" falso na T8.2 (14–16) não sai da faixa do `_atqg`
  (14–16).
- O G8 (o traço) funcionou: os alarmes caem de 34 para 24. O G9 e o G10 (o slide curto e o arco
  raso) não mudam nada nas perdidas.
- **A casa piora** nos ouros: 2633 e 2636 ficam fora da faixa do `_atqg`. A suspeita é o G8
  (algarismos pequenos e apertados), mas isso não foi medido. Os pesos `_atqc` não são adotados.
- O que sobra nas perdidas é sobretudo o **mordente** (16 de 30) e o h/p da T8.2. Mais estilo
  de arco no gerador já não move esse número.

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
| G10 | arco longo de 2 a 6 colunas (antes 2 a 4); em metade dos casos, raso (altura de 0,08 a 0,3 passo) | o de hoje, na chegada |

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

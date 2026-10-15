# 3018 — pauta com uma linha apagada: completar a 5ª linha

Trilha partitura. Data: 2026-10-15.

## Problema

Depois da 3017, o `paginar` ainda perdia pautas em página corrida. No mela (無料タブ譜,
720p), 9 páginas tinham só uma das duas pautas, algumas sem destaque nenhum. Primeiro
testei a escolha do quadro, achando que o destaque escondia a pauta: escolher, em cada
página, o quadro com mais pautas recuperou só 1 recorte (29→30).

Olhando o quadro, a causa ficou clara: as linhas da pauta são cinza-claras (≈200 sobre 244)
e borradas, e uma linha cai entre duas linhas de pixel. A máscara adaptativa fica picotada
nessa linha e a abertura horizontal a apaga. Sobram 4 linhas fortes:

- em t=23, 440, 460, 470 e 481 (falta a de 450);
- em t=92, 128, 139, 150 e 160 (falta a de 118).

Com 4 linhas, a pauta não é reconhecida.

## Mudanças

- `tab/partitura_video.py`: `escolher_instante` lê, em cada página, o quadro com mais pautas
  dentro das exibições da página. No empate, fica o quadro mais perto do instante antigo.
- `tab/partitura_pauta.py`: nova passada `_completar_grupos_de_quatro`, que roda depois dos
  grupos de 5. Ela olha só as linhas fortes que nenhuma pauta usou e testa janelas de 4:
  - **meio**: um intervalo ≈ 2e e dois ≈ e. A candidata é o ponto médio do intervalo duplo;
  - **borda**: três intervalos ≈ e. As candidatas são `ys[0] − e` e `ys[3] + e`. Exatamente
    uma tem de ser crista no cinza. Se as duas forem, há 6 linhas, é tablatura e a janela é
    descartada.

  Depois, a pauta completada passa pelos mesmos testes do laço de 5 linhas: geometria,
  espessura, crista e 6ª linha. Nenhuma constante nova.
- Testes: 5 de `escolher_instante` e 4 do detector:
  - linha do meio apagada;
  - linha da borda apagada;
  - tablatura com a linha do meio apagada, que dá 0;
  - 4 linhas com o 5º lugar vazio, que dá 0.

  Trocar a passada nova por `lambda: []` faz os 2 testes de completar falharem, então eles
  exercitam o código novo.

## Medições

**Censo**: a mesma amostra da rodada 3001 (`--por-canal 30 --semente 0`, 436 vídeos),
comparada quadro a quadro com `p0/amostra.jsonl`. Ver `diag/comparar_censo.txt` e
`diag/censo_completar_mudancas.jpg`.

| | quadros |
| --- | --- |
| ganharam pauta (0 → ≥1) | 18 |
| perderam pauta (≥1 → 0) | **0** |
| ganharam mais uma pauta (n → n+1) | 9 |

Olhei cada um dos 27 quadros na folha de contato:

- 25 são pautas reais. São do guitar dell'arte, pablo romé, paolo d'angelo (3), robert
  lunn (4), transcriptor (3), guitarous (3), lonelypicker (2), serge kottelat e mela (5);
- **transcriptor libertango t=333** é tablatura. O `e_tablatura` do `paginar` a descarta
  (medido em `diag/medir_completadas.txt`);
- **leonardo ramos t=811** é uma faixa de 4 linhas finas com X embaixo, provavelmente
  tablatura com cordas escondidas. Passa no `e_tablatura`. É 1 quadro e fica como limite.

**Validação** (3 vídeos com produto): 4/4, 3/3 e 12/12. As 19 caixas são idênticas.

**Piloto de 11 vídeos** (`diag/piloto_paginar5.txt` contra `piloto_paginar4.txt`):

- 9 vídeos não mudaram;
- **mela**: as páginas passaram de 20 para 22 e os recortes de 30 para 41. Quase toda página
  agora tem as 2 pautas. Olhei o P07b (t=23), que é a pauta recuperada, com clave e armadura;
- **free tab**: as páginas passaram de 14 para 12, com os mesmos 23 recortes. Antes, a 2ª
  pauta sumia em alguns trechos e a mesma página se partia: P02 (4–6 s, 1 pauta) e P03
  (7–12 s, 2 pautas). Agora é uma página só, de 4 a 12 s com 2 pautas. A 1ª pauta da P12 é a
  única que segue sozinha.

## Limites

- A caixa do censo de uma pauta completada pode ser curta, porque é o trecho comum das 4
  linhas e uma delas está picotada. O recorte do `paginar` estende a pauta com
  `extensao_horizontal` e sai quase da largura toda no mela (6–1271 de 1280). Duas
  exceções: P07b (até 1146) e P22b (até 1229) perdem um pedaço da direita.
- mela P10 e P11 (38 s e 40 s) têm as mesmas caixas: são uma página duplicada.
- O falso positivo do leonardo ramos, acima.

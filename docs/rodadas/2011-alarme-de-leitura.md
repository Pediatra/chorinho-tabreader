# 2011 — Áudio: alarme de leitura no `chorinho/audio@1`

Data: 2026-10-13. Código: `tab/audio_produto.py` (`alarme_leitura`, `LIMIAR_ALARME_COS =
0,7`). Saídas regeradas: `data/saida/audio/a5/*.audio.json` e
`data/saida/audio/a4/lote1/*.audio.json` (`data/saida/audio/a4/alarme/rodar.sh`).

## Regra

Uma exibição recebe `alarme_leitura = true` quando o alinhador a recusou e o cosseno médio
das colunas que casaram é ≥ 0,7. A regra vem das rodadas 2009 e 2010, e o limiar foi
fixado antes desta medição. Cada exibição do arquivo também passa a levar `cos_medio` e
`n_casadas`; o validador confere se o alarme é coerente com esses campos.

## Nos 14 vídeos

| vídeo | alarmes | situação conhecida |
| --- | --- | --- |
| MVP, iwaki la vie en rose, kimny from this place | 0, 0, 0 | bons |
| iwaki michelle, kimny 群青, kimny bach, paolo those who wait | 0, 0, 0, 0 | bons |
| iwaki fly me to the moon | 1 de 17 (tela 10) | bom |
| shin izumi dream is a wish | 2 de 22 | bom |
| transcriptor charagua | 2 de 18 | fraco, não olhado |
| shin izumi giant steps | 9 de 20 | fraco |
| guitarous sakura | 7 de 10 | cordas deslocadas (2010) |
| shin izumi room 335 | 21 de 42 | corda 1 perdida (2009) |
| transcriptor campanitas | 21 de 52 | rasgueado (2010): leitura certa |

## Conferência na imagem (recortes em `data/saida/audio/a4/alarme/quadros/`)

- **iwaki fly me to the moon, tela 10** (o único alarme do vídeo): a imagem tem cerca de
  25 colunas, com muitos números de dois algarismos (13, 12, 10, 15, (12)). O produto tem 7
  colunas, quase todas erradas, por exemplo (1,21), (4,17) e (2,14). **Leitura com falhas**:
  o alarme acertou.
- **shin izumi giant steps, tela 5**: o produto não tem os acordes dentro de elipse
  (14/14/13/14, 10/12/11/12, 12/11/12/10) nem as colunas 6/6/6, 7/5/5 e 5/5/5. A ligadura
  (6)(6) virou (1,6) e (1,0). A corda 6 parece encostar na borda de baixo do painel.
  **Leitura com falhas**: o alarme acertou.
- Com as rodadas anteriores, das telas com alarme que foram olhadas, **5 de 6 eram leitura
  com falhas**: shin room 335 telas 12 e 25, guitarous tela 3, fly me tela 10, giant steps
  tela 5. A sexta (campanitas tela 10) era rasgueado com leitura certa.

## Consequências

1. O arquivo de áudio passa a indicar à trilha tablatura **onde olhar**, por tela.
2. Rasgueado gera alarme falso de leitura. Quando houver detector de rasgueado, ele deve
   desligar o alarme nessas telas.
3. Vídeos sem nenhum alarme (7 de 14) ainda podem ter erros de leitura que o alinhador
   absorve. O alarme não é prova de leitura certa.

## Limites

6 telas olhadas no total; limiar não varrido; o alarme só existe onde há áudio alinhável.

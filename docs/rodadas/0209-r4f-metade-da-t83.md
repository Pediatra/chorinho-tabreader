# 0209 — R4f: exemplos do mesmo canal (metade da T8.3 no treino)

Segue a [0207](0207-r4d-t82-no-ajuste-fino.md) e a [0208](0208-r4e-cadeia-e-arco-alto.md).
Escrito **antes** de treinar.

## Por que

O gabarito da T8.3 foi corrigido pelo dono em 2026-10-20: 7 notas em que o arco sai da nota
passaram a "sim, sustentada". Com isso, o `_atqt` dá "sim" falso de 8 · 8 · 9 /70, e o modelo
não vê 8 símbolos marcados.

- A T8.2, de outros canais, no treino não mudou a T8.3 (0207).
- Cadeias e arcos altos no gerador também não mudaram (0208).

Falta saber se **exemplos reais do mesmo canal** ensinam esses desenhos.

## A mudança (só esta)

- `n4/extrair_t83.py` faz o cache das 33 telas da T8.3. Em cada canal, as telas em ordem de id
  vão alternadas para a metade "a" (17 telas) e a "b" (16 telas).
- `treinar_ft.py --t83-metade h` soma ao treino só a metade h, com a técnica do gabarito do dono.
- O resto é igual ao `_atqt`: `--ataque --t82`, 3000 passos, dobra 0 (os ouros no treino).
- São 6 treinos: as metades a e b × 3 sementes, com o nome `_atqm<h>_s<semente>`, no roteiro
  `data/saida/tab_rotulo/r4f/rodar.sh`.

## Teste

- `r4f/medir_metade.py`: o `atqma` é medido nas telas b e o `atqmb` nas telas a. As duas metades
  são somadas, e cada nota da T8.3 é medida uma vez, fora do treino.
- O `_atqt` dobra 0 é medido nas mesmas telas.
- A faixa é a de hoje, sem escolher de novo: técnica 0,15 e `L` 0,02. Na dobra 0 os ouros estão
  no treino.

## Aceite e parada

- **Ajuda** se o "sim" falso somado nas 3 sementes cai pelo menos 4 notas abaixo do `_atqt` nas
  mesmas telas, e se a casa não cai mais de 2 abaixo do pior `_atqt`.
- **Pare se** não cair. Nesse caso, nem exemplo real do mesmo canal ensina esses arcos com este
  modelo, e a rota da técnica volta ao dono com essa conclusão.

## Resultado (2026-10-20)

6 treinos, de 18h27 a 19h53, em `data/saida/tab_rotulo/r4f/`. A medida está em
`r4f/medida_metade.json` e `r4f/medida_metade.log`.

| | "sim" falso | custo | casa |
| --- | --- | --- | --- |
| `_atqt` (sem T8.3) | 8 · 8 · 9 /70 (soma 25) | 31–34 /1417 | 1480–1482 |
| `_atqm` (a outra metade no treino) | 8 · 10 · 8 /70–71 (soma 26) | 36–40 /1416 | 1481–1484 |

- **A regra de parada dispara.** O "sim" falso não cai: a soma vai de 25 para 26, e o custo
  sobe. A casa fica igual.
- Nem exemplo real do mesmo canal ensina esses arcos a este modelo, com 17 telas e 3000 passos.
  Somam-se a T8.2 no treino (0207) e o gerador com cadeias e arcos altos (0208): mais dado,
  real ou sintético, não resolve os símbolos que sobram. São 8 de 70 notas não atacadas, quase
  todas arcos acima do sistema.
- A rota da técnica volta ao dono com essa conclusão.
  - **Fica como está:** `_atqt` com a faixa, 11–13 % de "sim" falso e custo de 2–2,4 %.
  - **Mexer no modelo:** o que resta é mudar a arquitetura, não o dado. Um exemplo é a técnica
    olhar o sistema inteiro acima da corda 1 com mais contexto. Isso é uma pesquisa à parte.

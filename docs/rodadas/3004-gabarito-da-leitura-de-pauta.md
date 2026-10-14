# 3004 — Gabarito do dono: o que o Audiveris erra de verdade na pauta

**Data:** 2026-10-14 · **Trilha:** partitura · **Gabarito:** `data/gold/partitura/leitura_p1.json`
(formato 3, gravado pelo dono na página `tab.partitura_gabarito servir`) · **Leitura conferida:**
Audiveris x2 sobre o recorte com margem 7/7 (rodada 3003); R21 no homr nativo

## Pergunta

A rodada 3003 deixou duas dúvidas abertas: quanto o Audiveris erra no **ritmo**, que a tab não
mede, e se vale treinar o SMT. O dono conferiu os 21 recortes símbolo a símbolo. Cada símbolo
lido ficou como certo, altura errada, figura errada ou não existe. As notas que faltaram foram
marcadas com um clique na imagem original.

## Resultado (21 de 21 recortes confirmados)

| grupo | notas lidas | pausas lidas | certas | figura errada | altura errada | não existe | faltando (cliques) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| R01–R12 (com tab) | 510 | 41 | 542 | 6 (1 nota, 5 pausas) | 0 | 3 | 47 |
| R13–R21 (sem tab, 8 canais) | 302 | 20 | 310 | 1 | 4 | 7 | 31 |
| **total** | **812** | **61** | **852 (97,6 %)** | **7** | **4** | **10** | **78** |

Notações (fermata, ponto, dedilhado e outras): 214 certas e 25 inventadas, nos 21 recortes.

Por recorte, os perfeitos são R01–R05, R07, R14, R15, R17 e R20 (nada errado entre os
símbolos lidos). Os recortes R01–R04 e R20 também não têm nota faltando.

## O que os números dizem

- **O erro principal é nota que falta, não nota errada.** São 78 cliques de faltando contra 21
  símbolos errados (7 de figura, 4 de altura, 10 inventados). O que o Audiveris lê, ele lê
  certo em 97,6 % dos casos.
- **O ritmo do que é lido está quase sempre certo**: 7 figuras erradas em 873 símbolos, 5 delas
  em pausas do robert lunn (R09–R11). As observações do dono acrescentam 2 casos de figura
  errada em notas já marcadas como altura errada (R13, R18). O formulário guarda só um estado
  por símbolo.
- **Altura conferida contra a imagem, não contra o som.** R06 começa no meio do sistema, sem
  armadura na tela. O dono marcou como certas 7 notas em que a tab discorda (F4 lido, F#4 na
  tab). O gabarito diz "a leitura bate com o que está desenhado". A altura que soa vem da
  tab, ou da armadura herdada de outro quadro do mesmo vídeo.
- **Observações que viram tarefa:**
  - R20: o Audiveris leu a fórmula de compasso errada (o certo é 4/4).
  - R21: o recorte cortou a parte de cima da pauta (detector, não leitor).
  - R19: o losango de harmônico precisa virar notação.
  - R12: a mínima e a pausa estão um pouco deslocadas em relação à voz de cima.

## Conclusão: treinar o SMT não se justifica agora

O que a partitura acrescenta à tab é o ritmo, e o ritmo lido pelo Audiveris está certo em
~99 % dos símbolos. O que falta resolver é a **cobertura** (78 notas faltando, mais em acordes
e em vozes de baixo) e a **armadura herdada**. Isso se ataca com as leituras que já existem:

- juntar homr e Audiveris onde um vê nota que o outro perdeu;
- usar a tab para completar as notas faltando nos vídeos que têm tab;
- herdar clave e armadura de outro quadro.

Um modelo novo, com semanas de gerador e treino, não tem alvo claro hoje. A decisão fica para o
dono.

## Limites

- **Um conferente, uma passada.** Não há segunda leitura independente.
- **21 recortes, 12 canais.** A taxa por canal, com 1 a 5 recortes cada, não é estimativa de
  canal.
- **A métrica não mede o que falta em ritmo.** Nota faltando não tem figura, então o ritmo das
  notas faltando não entra na conta.
- **Script da conta:** `data/saida/partitura/diag/medir_gabarito.py`.

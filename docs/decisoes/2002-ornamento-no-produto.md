# 2002 — Pedido à trilha tablatura: marcar nota de ornamento no produto

Estado: **proposta da trilha áudio**, para o dono repassar à trilha tablatura (dona de
`tab/esquema.py`, `tab/reconhecer.py` e `tab/video.py`).

## Contexto

Rodada 2006: no MVP, as colunas que o marcador nunca acende são **notas pequenas de
ornamento** sob um arco (mordente 2–3–2, nota de deslize). No áudio elas soam rápido e
ligadas, muitas vezes sem ataque próprio, e o alinhador as encaixa num ataque vizinho:
na folha de escuta do dono, 2 de 4 colunas desse tipo saíram "errado". O produto hoje não
diz que a nota é pequena nem que há um arco (`nao_notas` só tem as classes `simbolo`,
`harmonico` e `tecnica`). A regra geométrica que tentei para adivinhar (corda 1, nota
única, perto da anterior) foi reprovada pelo gabarito do dono.

O dono já tinha apontado que o tamanho do símbolo é a informação (ESTADO, "o arpejo";
relato do arco de ligadura, Fase 10).

## Opções

1. Campo por nota no produto, por exemplo `altura_glifo_passo` (altura do glifo em
   passos) ou `ornamento: true` quando o glifo é bem menor que os algarismos da tela.
2. Classe `arco` em `nao_notas`, com o `x` de início e de fim e a corda.
3. Nada no produto: a trilha áudio continua sem distinguir ornamento.

## Proposta

1 e 2, nessa ordem. Com (1), o alinhador pode tratar a coluna de ornamento como "ataque
opcional, rápido, ligado à vizinha" em vez de exigir um ataque próprio.

## Consequência

Mudança no esquema (`chorinho/video@…`) feita pela trilha tablatura. A trilha áudio mede
o efeito no gabarito `data/gold/audio/` depois.

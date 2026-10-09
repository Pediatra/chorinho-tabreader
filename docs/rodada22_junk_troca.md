# Rodada 22 — a classe `junk` é uma troca, não um ganho

## 1. Comparação com repetição (o certo, enfim)

Mesmo código, mesmos dados, 320 linhas, 22 épocas — só a presença do rótulo `junk` muda:

| semente | **COM `junk`** | **SEM `junk`** |
| --- | --- | --- |
| 0 | 0,781 (sky 9/15, raman 19/24) | 0,750 (sky 11/15, raman 12/24) |
| 1 | 0,802 (sky 9/15, raman 18/24) | 0,812 (sky 15/15, raman 12/24) |
| 2 | 0,833 (sky 9/15, raman 18/24) | 0,854 (sky 13/15, raman 12/24) |
| **média** | **0,805** | **0,805** |
| amplitude | 0,052 | 0,104 |

**A média é exatamente a mesma.** A classe de rejeição não melhora o sistema: ela **troca** erro
de um canal por outro.

| | com `junk` | sem `junk` |
| --- | --- | --- |
| `raman korshun` (média) | **18,3/24** | 12/24 |
| `sky guitar` (média) | 9/15 | **13/15** |
| `paolo d'angelo` (média) | 26,7/30 | 27/30 |

Ganha ~6 notas no `raman` e perde ~5 no `sky guitar` + `paolo`. **Empate técnico.**

## 2. O que isso corrige no que eu disse

- **"classe de rejeição: 0,854 → 0,865"** — era ruído, agora provado: a média não muda.
- **"regressão sistemática no `sky guitar`"** — parcialmente certo: *com* `junk` ele dava 9/15 nas
  três sementes (sistemático, sim); *sem* `junk` varia 11–15/15. Mas corrigir isso **não** sobe o
  total, porque o `raman` cai junto. Era um trade-off que eu estava lendo como ganho.
- O gancho `junk` **não era inócuo** (custava 4 notas no `sky guitar`), mas também não era o
  vilão que eu supus.

## 3. Decisão

Fico com a versão **sem** `junk` (estado atual do código): os canais verificados ficam melhores
(`sky` e `paolo`) e o único que piora é o `raman`, que é justamente o canal mais fora do padrão —
onde o problema real é a **marca de técnica no token** (`7 → harmonico`), não o lixo.

## 4. Número oficial do sistema

**0,805 (média de 3 sementes), amplitude 0,05–0,10.**

Dois fatos que dão contexto ao número:

- `paolo d'angelo` fez **30/30** na semente 2 — o teto não é o modelo, é a cobertura do dado;
- os dois canais MuseScore (iwaki, sky) chegam a **27/27** e **15/15** em sementes diferentes.

## 5. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura, 95 % com cursor |
| (b) gabarito verificado | 96 glifos / 4 canais |
| (c) classificador multi-classe | **0,805 (3 sementes)** — medido com repetição, sem ganho falso |
| (d) pipeline ponta a ponta | corda, casa, técnica, tempo, compasso e andamento |
| (e) escala nos 3.781 | pendente |

Próximo passo com base no que sobrou de erro: a **marca de técnica dentro do token** (o `7` que
vira `harmonico`/2 dígitos no `raman`) — agora medindo com 3 sementes, para não repetir o erro de
perseguir ruído.

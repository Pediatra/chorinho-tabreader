# 1026 — Primeiro ciclo de revisão: sky guitar

**Data**: 2026-10-18. **Estado**: regras a priori. Este documento ganha commit antes de rodar o
detector nos vídeos. **O dono escolheu**: "pode começar pelo sky guitar, 7 cordas fica fora por
enquanto".

**Antecedente** ([1025](1025-localizador-com-marcas-grosseiras.md)): a cadeia completa passou
num teste de 4 canais novos.
- Falsos não sinalizados: 2/69, os dois num violão de 7 cordas.
- Sinalizados: 43 %.
- Dos 39 quadros não sinalizados, 36 estavam certos.

## Pergunta

Num lote real de vídeos, quanto do braço o detector entrega sozinho e certo? Quanto trabalho
sobra para o dono? E as correções viram dado de treino útil?

## Lote

- **Vídeos**: **8 vídeos do sky guitar** que não aparecem na M3b, no R nem no C.
  - Sorteio com semente 20261026.
  - Um vídeo que o dono marcar como 7 cordas sai do lote.
- **Quadros**: **8 por vídeo**, igualmente espaçados entre 0,15 e 0,85 da duração, num total de
  **64**.

## Detector (congelado, sem nenhuma mudança)

- **Estágio 1**: `L2_todos_s1` com a decodificação conjunta. A semente 1 é escolhida pelo
  desenvolvimento (M11b): foi a de menos falsos, 6 contra 21 e 8. Não há concordância entre
  sementes nesta rodada.
- **Estágio 2**: `A3_100_todos_s1` (v2), com o refino de uma passada.
- **Regra de revisão**: a da 1023 (fe114eb4).

## O que o dono faz

A ferramenta é a de sempre (`tab.maos_braco_gabarito`), numa pasta e num gabarito próprios
(`data/gold/maos/braco_m26.json`). Cada quadro abre **já preenchido** com as marcas do
detector, quando ele achou o braço.
- **Sinalizados** (vêm primeiro): o dono corrige o que estiver errado (cordas, nut ou trastes)
  ou marca "braço não".
- **Não sinalizados** (auditoria; no ciclo normal não seriam vistos): o dono só confere. Se
  estiver certo, aperta "braço sim"; se não, corrige.
- Violão de 7 cordas: observação `7 cordas`, e o quadro sai da medida.

As previsões ficam guardadas à parte, em `data/saida/maos/m26/previsto.json`. Assim a medida
compara a previsão com a versão final do dono.

**Cuidado com a ferramenta**: o preenchimento é testado **numa cópia** antes de abrir para o
dono. O gabarito ao vivo grava a cada clique.

## Medidas

**Por quadro** (previsto contra o final do dono, com `classificar`):
- a classe;
- se o quadro foi sinalizado.

**Totais**:

| | o que é |
| --- | --- |
| **entregue certo** | não sinalizados e certos ÷ quadros com braço |
| **falsos que passam** | não sinalizados e falsos ÷ quadros |
| **trabalho do dono** | sinalizados ÷ quadros, e quantos sinalizados já vieram certos (o "corrigir" não mudou nada) |

**Critério para seguir para a rodada de retreino**, com as correções como dado novo:

| resultado | o que fazer |
| --- | --- |
| falsos que passam ≤ 5 % e sinalizados ≤ 50 % | o ciclo funciona: a 1027 retreina os estágios 1 e 2 com as marcas finais e mede de novo num lote novo |
| falsos que passam > 5 % | parar o ciclo. Investigar por tipo de erro antes de qualquer retreino |
| sinalizados > 50 % | o ciclo é seguro, mas caro: registrar e propor a melhora que mais reduz os sinalizados |

## Riscos declarados antes

- **O sky guitar está no treino** dos dois estágios (R, G e C). Este lote mede a produção num
  canal conhecido, não a generalização. A generalização foi medida na 1025.
- **Auditoria com preenchimento induz concordância**: o dono pode aceitar uma marca quase certa.
  A régua tolera 0,25. A repetibilidade do dono é de 0,14 vão.
- **64 quadros de um canal** dão a direção, não uma taxa firme.

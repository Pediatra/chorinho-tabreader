# 0011 — Tablatura: o produto vira o rótulo da base, e a técnica que importa é o ataque

**Data**: 2026-10-16. **Decisão do dono** (chat, respondendo às três perguntas: "1. sim 2. só os
que mudam o ataque 3. sim").

## Contexto

- A decisão 1006 mudou a trilha das mãos: ela passa a construir uma base em que cada nota do
  gabarito fica ligada às mãos, ao braço e ao som (`docs/guias/plano-dataset-maos.md`). **A
  tablatura da tela é o gabarito dessa base.**
- A trilha da tablatura seguia outro rumo: pesquisa em ondas para subir a leitura (rolagem,
  sondas, o som conferindo a casa), mais o conserto do X como item à parte. O campo `tecnica`
  ficou para depois.
- Medida:
  - a casa está em 0,996 fora do ouro;
  - a rede acha o arco do ligado em 25 de 139 marcas do dono, com classe certa em 4 (rodada
    0104).
- Um ligado, uma ligadura de prolongamento ou um slide ligado são notas **sem ataque** da mão
  direita. O X é ataque sem altura. O harmônico é ataque com outra altura.
- Se o rótulo errar o ataque, a base associa um movimento e um som a uma nota que não os teve: é
  a contaminação que o dono quer evitar. As trilhas do áudio (2002, 2004) e das mãos (K1, K3)
  dependem desse campo.

## Opções

1. **Seguir a onda 2** (B1, E1, E2) e o conserto do X à parte.
   - Contra: mede leitura em geral, não o que contamina a base.
2. **Todos os símbolos de técnica.**
   - Contra: o dono escolheu só os que mudam o ataque. Bend, vibrato e rasgueado não mudam se a
     nota foi tocada.
3. **O rótulo de ataque por nota**, com nível (ouro, prata, recusado) e auditoria do dono, no
   mesmo molde das mãos.

## Decisão

**Opção 3.** Plano em [`docs/guias/plano-rotulo-tablatura.md`](../guias/plano-rotulo-tablatura.md),
fases R1–R6:

1. R1 — esquema;
2. R2 — gabarito do ataque;
3. R3 — linha de base;
4. R4 — detector de arco;
5. R5 — X e harmônico;
6. R6 — auditoria e piloto com as mãos.

Os símbolos do escopo: h, p, mordente, ligadura de prolongamento, slide, X e harmônico.

## Consequências

- A onda 2 como estava escrita para (`docs/pesquisa/tablatura-onda2-briefings.md`). A C1 e a D2
  também param. A B1 só volta se o R4 precisar de arcos de outro estilo.
- O rótulo vem só da tela. O som e as mãos conferem, mas não criam rótulo.
- Na dúvida, o ataque é `nao_sei` e a nota fica prata, nunca "sim".
- O dono precisa de tempo:
  - conferir o ataque nos ouros, a folha de X e os arcos de 3 a 5 vídeos do sky guitar
    (estimativa de 1 a 2 h, a medir);
  - 30 a 40 min por auditoria de 100 notas.

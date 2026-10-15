# 1005 — Mão direita: o produto é a corda atacada, não o dedo

**Data**: 2026-10-15. **Decisão do dono** (chat: "alinhado, pode seguir com o 1, quero só a
corda").

## Contexto

O M5 ([1004](1004-m5-padroes-da-mao-direita.md)) mediu o **dedo** da direita: regra do dono +
confirmação em 40 compassos do sky guitar ([rodada 1010](../rodadas/1010-m5-regra-da-direita-contra-o-dono.md)).
Regra v2: 172/216 fora da amostra (0,796); o resto é preferência do violonista. O dono
perguntou a utilidade e explicou o objetivo: a mão direita serve para saber **quais cordas
soam em cada instante**, para dar precisão à mão esquerda e ao áudio e gerar a
tablatura/partitura fiel.

## Decisão

1. A saída da mão direita é **corda(s) atacada(s) + instante**. O dedo é meio, não produto.
2. Próximo passo (M7): medir se a **câmera da mão direita sozinha** acerta a corda atacada,
   contra a tablatura da tela do sky guitar (gabarito de graça, sem rótulo do dono).
3. Fusão depois: áudio (altura, instante) + direita (restringe a corda) + esquerda (casa).
4. **Não se pede mais rótulo de dedo ao dono.**

## Guardado para o futuro (pedido do dono)

O dono pode querer, depois, um algoritmo que **sugira o melhor dedilhado da direita**
(p-i-m-a) a partir das regras dele. O progresso fica preservado:

- regra: `tab/maos_regra_direita.py` (v2 padrão; v1 em `V1_*`), medidor
  `tab/maos_regra_direita_medir.py`;
- gabarito: `data/gold/maos/padroes_direita.json`, 40 compassos confirmados (formato 2,
  dedo por nota com palpite, regra e dono; `l` = ligada);
- o que falta à regra, pelas observações do dono nos pares: em acordes e alternâncias
  rápidas preferir `i-m` (coordenação motora); polegar repetido (`p-p-p`) conforme a
  distância ao baixo; anelar repetido é exceção; ligado pede o símbolo da tablatura.

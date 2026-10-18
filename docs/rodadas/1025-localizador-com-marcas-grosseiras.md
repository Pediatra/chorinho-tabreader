# 1025 — Localizador com marcas grosseiras de 16 canais e teste em 4 canais novos

**Data**: 2026-10-18. **Estado**: regras a priori. Este documento ganha commit antes de
qualquer treino. **O dono escolheu este caminho** ("vamos de caminho 1") e marcou os quadros.

**Antecedente** ([1024](1024-fase-b-localizador-do-braco.md)): a cadeia é segura, com 0 de 87
falsos passando sem sinalização. Mas ela não foi útil na M11b: 75 % dos quadros foram
sinalizados.
- O gargalo é o estágio 1. Ele treinou com cerca de 900 quadros de **8 canais**, e esses
  quadros vinham de só **2 a 11 vídeos por canal**.
- Nos canais novos, ele acertou o eixo em 0 a 9 de 28 quadros.

## Pergunta

O estágio 1 treinado com marcas grosseiras de mais vídeos e mais canais generaliza para canais
que nada no sistema viu? E a cadeia fica útil, além de segura?

## Dados novos (marcados pelo dono em 2026-10-18)

**C, treino grosseiro**: `data/gold/maos/braco_m25_treino.json`, com os quadros em
`data/saida/maos/m25/treino/`.
- 144 quadros: 9 por canal, em 16 canais (os 8 de `braco.json` e os 8 da M11b).
- Sorteio com semente 20261025 (`m25/sortear.py`): um instante entre 0,15 e 0,85 da duração. O
  sorteio deu preferência a vídeos fora da M11b e fora da M3b.
- Marcas: corda 1 e corda 6 (2 pontos cada) e o nut. **Sem trastes.**
- Entram os quadros com as duas cordas completas: são **140**.
  - Ficam de fora os dois "braço não" (q97 e q124).
  - Ficam de fora os quadros dos dois vídeos que o dono descartou: q65 (guitarra elétrica) e
    q118 (flauta).

**N, prova**: `data/gold/maos/braco_m25_prova.json`, com os quadros em
`data/saida/maos/m25/prova/`.
- 24 quadros: 6 por canal, de **4 canais que nunca foram usados**: gabriel cryslian, serge
  kottelat, yunus guitarist e ギタロー guitarous.
- **Marcação completa** do dono (cordas, nut e trastes).
- Excluídos antes: o **q08** (guitarra elétrica) e qualquer quadro que o dono deixar sem
  resposta.

## Método (só muda o dado do estágio 1)

- **Estágio 1**: o mesmo da 1024. Mesma arquitetura, mesmos alvos, aumentos, orçamento de 3.000
  passos e `P_MIN` = 0,3. Os dados passam a ser **R + G + C**.
  - O C entra com os mesmos 4 pontos (pontas das cordas 1 e 6 no nut e no extremo) e a mesma
    máscara.
  - A amostragem é uniforme por quadro, como na 1024.
  - Pesos: `L2_todos_s1..3`.
- **Estágio 2**: `A3_100_todos_s<k>`, **sem retreino**, porque o C não tem trastes. Refino de uma
  passada, como na 1024.
- **Regra de revisão**: a da 1023, congelada (fe114eb4).

## Desenvolvimento (só registro)

- **M11b**, 28 quadros com as 3 sementes. Agora ela é desenvolvimento: os canais dela estão no
  C, mas os vídeos dela não estão.
  - Erro do eixo do estágio 1: % dentro do envelope.
  - Cadeia: certos, falsos, sinalizados e falsos não sinalizados.
  - Comparação com a 1024: 9, 0 e 9 de 28 dentro do envelope; 63 de 84 sinalizados.

Nada é ajustado por esses números. Não há limiar livre nesta rodada.

## Prova (N, aberta uma vez depois do commit do treino)

- **Medidas**: os quadros N válidos × 3 sementes.
- **Cadeia**: o quadro inteiro passa por estágio 1 → refino → v2 → regra.
- "Braço não" do dono que sai achado e não sinalizado conta como falso.
- **Dois braços** (observação `2 braços`): conta contra o braço que o dono marcou. Esses quadros
  são reportados à parte.

**Critério** (o mesmo da 1024):

| | passa se |
| --- | --- |
| segurança | falsos não sinalizados ≤ 5 % das medidas |
| utilidade | sinalizados (incluindo "não achou") ≤ 50 % das medidas com braço |

| resultado | o que fazer |
| --- | --- |
| passa nos dois | propor ao dono o ciclo de revisão num lote de vídeos |
| segurança passa e utilidade reprova | registrar se o gargalo segue no estágio 1 (envelope) ou passou para o estágio 2. Propor o próximo dado com o número |
| segurança reprova | não serve para o ciclo. A decisão volta ao dono |

**Também reportados**:
- erro do eixo do estágio 1 em N;
- certos não sinalizados;
- a tabela por canal;
- a amplitude entre as sementes.

## Riscos declarados antes

- **N tem cerca de 23 quadros de 4 canais.** São poucos, e o yunus guitarist tem 1 vídeo só.
  Isso mede a direção, não uma taxa firme.
- **O estágio 2 também não viu N.** A utilidade pode cair por causa dele mesmo com o estágio 1
  bom. O registro separa os dois casos pelo envelope.
- **As marcas grosseiras foram feitas rápido.** O envelope da 1021 tolera de sobra o erro de
  clique; o refino e o estágio 2 decidem o resto.

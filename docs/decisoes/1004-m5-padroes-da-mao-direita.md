# 1004 — M5: padrões da mão direita, rotulados por trecho

**Data**: 2026-10-13. **Decisão do dono** (chat: "concordo", aceitando a proposta de tipos da
[1003](1003-fases-das-maos.md) e a ordem "recusa na calibração, depois M5").

## Contexto

No M2 o dono rotulou o dedo da direita nota a nota e declarou o resultado PARCIAL: com 3
quadros parados por ataque, o dedo que toca não se vê com certeza, e parte das respostas foi
inferida. A [1003](1003-fases-das-maos.md) trocou a unidade: padrão por trecho, não dedo por
nota.

## Decisão

**Unidade**: o compasso tocado (uma exibição de um compasso de uma tela do produto: chave
`tela`, `compasso`, `exibicao`). Compasso é a menor unidade em que o padrão se repete e já
existe no JSON do produto.

**Rótulo do dono, por compasso** (todos aceitam `?`):

| campo | valores |
| --- | --- |
| `tipo` | `arpejo`, `rasgueado`, `tremolo`, `plaqueado`, `melodia`, `misto` |
| `sequencia` | texto livre com os dedos na ordem tocada (ex.: `p-i-m-a-m-i`), só para `arpejo` e `tremolo` |
| `alternancia` | `i-m`, `m-a`, `i-a`, `p`, `outra`, só para `melodia` |
| `apoio` | `apoiado`, `sem_apoio`, `misto` |
| `obs` | texto livre |

**Material**: um **clipe** por compasso, não quadros parados (a lição do M2): o recorte da
mão direita do primeiro ao último `t_ini` do compasso, com 0,3 s de margem, em velocidade
normal e a 0,5×, com a tablatura e o compasso destacado ao lado.

**Amostra**: 40 compassos com pelo menos 3 notas com `t_ini`, de 4 vídeos do sky guitar que
já têm produto e pontas (retrato brasileiro, noturno nº 20, lacrimosa, glimpse of us), 10 por
vídeo, estratificados no tempo, semente 20261013. Sky guitar porque é o canal com tempo
confiável e com câmera própria da mão direita.

**Medição**: primeiro uma regra só pela tablatura (sem visão), como base. Ela olha quantas
cordas soam juntas, se a mesma corda se repete em sequência rápida e o intervalo entre
ataques. A visão (trajetória das pontas da direita) só entra se superar a base, como no M3.

## Consequências

- O gabarito vai para `data/gold/maos/padroes_direita.json`, com formato próprio e escrita
  atômica a cada clique, como os outros gabaritos das mãos. O rótulo do dono é contrato.
- `sequencia` e `alternancia` medem o dedo da direita por trecho. Substituem a direita nota
  a nota do M2, que fica só como indicativa.
- Se o dono achar que 40 compassos de 4 vídeos de um canal só não bastam, a amostra cresce
  depois, sem mudar o formato.

## Revisão (2026-10-13): regra do dono + confirmação, gabarito do zero

O dono achou o rótulo por campos trabalhoso demais ("qual a utilidade de eu rotular isso?") e
propôs trocar o gabarito pela lógica do dedilhado, que vale para ~90% das músicas. A unidade
(compasso tocado), o material (clipes) e a amostra de 40 continuam; muda o que o dono faz.

**Regra** (`tab/maos_regra_direita.py`, só tablatura, sem visão), na ordem:

1. padrão da corda: 6, 5, 4 → `p`; 3 → `i`; 2 → `m`; 1 → `a`;
2. exceção do bordão: corda 4 com polegar na 5 ou 6 no mesmo ataque, ou no ataque anterior
   até `JANELA_POLEGAR_S` = 0,25 s ("logo abaixo") → `i`;
3. acorde: notas fora do polegar recebem `i`, `m`, `a` da corda mais grave para a mais
   aguda, sem nunca ficar abaixo do padrão da corda (cordas 3 e 1 → `i`, `a`);
4. sequência: ataques de uma nota fora do polegar até `JANELA_SEQUENCIA_S` = 0,6 s, na
   mesma corda ou mais aguda, avançam `i` → `m` → `a`; passando de `a`, volta ao padrão.
   A sequência vale mais que a exceção do bordão; um acorde zera a sequência.

As duas janelas e as três escolhas da regra 3 e 4 foram confirmadas pelo dono no chat.
Os exemplos dele viram teste: corda 3 casas 4-5-6 → `i, m, a`; corda 3 casa 2, corda 3
casa 1, corda 2 casa 0 → `i, m, a`.

**Rótulo**: a página mostra as notas do compasso com o palpite da regra marcado; o dono só
troca o que estiver errado e confirma. Formato 2 do gabarito, por compasso: `dedos`
(`corda`, `casa`, `t_ini`, `palpite`, `regra`, `dono`), `alteradas`, `confirmado`, `obs`,
`respondido_em`. `alteradas` / notas é a taxa de erro da regra.

**Página**: 20 dos 40 compassos (os ímpares, 5 por vídeo, `na_pagina` no `indice.json`).

**Gabarito antigo**: o dono mandou descartar as 2 respostas do formato 1 ("vamos começar do
0"). Cópia de registro em `data/saida/maos/m5/padroes_direita_formato1_descartado.json`;
não é gabarito.

**Sanidade indicativa** contra a direita nota a nota do M2 (que o dono declarou parcial e
em parte inferida; a regra **não** foi ajustada a ela): 35/53 (66%). Quase todos os erros
são do padrão da corda (dono marcou `a` ou `i` onde a regra dá `p`/`m`). Detalhe em
`data/saida/maos/m5/sanidade_regra_direita.json`. O número que vale é o `alteradas` do M5.

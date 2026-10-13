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

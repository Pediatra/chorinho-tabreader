# 0216 — Recusar o painel errado antes do rollout

**Data**: 2026-10-23. **Trilha**: tablatura. **Estado**: pré-registro (nada medido na prova).

## A pergunta

Antes do rollout, o produto precisa **recusar** a tela cujo painel não é a tablatura, em vez
de ler notas de outro lugar (braço, pauta, título) e entregá-las caladas. Uma regra simples,
fixada aqui, separa os painéis errados dos certos em vídeos que nenhuma escolha viu?

## O que já se sabe (dado de escolha, não é prova)

Nas 605 telas dos 35 produtos da `r2021` (`data/saida/audio/r2021/produtos`):

- 3 telas sem painel; 602 com painel, das quais **20 erradas** (3,3 %). A conferência visual
  das 51 folhas (`data/saida/tablatura/recusa/folhas_r2021/`) foi da sessão principal.
- Os sinais de cada tela estão em `recusa/sinais_r2021.json` (script `sinais_r2021.py`, feito
  por Haiku; a busca de limiares em `analise_r2021.py`).
- Dois sinais explicam quase tudo:
  - **o painel é uma faixa fixa inteira** (`painel.FAIXAS`: `topo` 0–400 ou `meio` 300–750,
    sem recorte): 13 das 20 erradas, e 2 das 582 certas (nenhuma nota perdida). A faixa
    `base` inteira (620–1080) **não** entra: ela é o painel certo em 194 telas;
  - **poucas notas para a largura** (`notas_por_largura = n_notas / (largura / passo)`):
    os painéis errados leem quase nada.
- A regra combinada abaixo, nesses mesmos dados: **18 de 20 erradas** recusadas, **8 de 582
  certas** recusadas (27 de 25.455 notas certas perdidas). O número é otimista, porque o
  limiar saiu dessas 20.
- O `y0 ≤ 176` que o Haiku achou fica de fora: é a posição em pixels, não o conteúdo.

## A regra (fixa)

Uma tela com painel é **recusada** quando:

```
painel == faixa fixa "topo" ou "meio" inteira (sem recorte)
OU  n_notas / (largura / passo) <= 0,0916
```

Recusada quer dizer: as notas ficam no produto, marcadas `recusado` com o motivo
(`painel_faixa_fixa` ou `painel_poucas_notas`). Nada some calado.

## A prova (lacrada)

- **Amostra**: 30 vídeos sorteados com `random.Random(16)` do `censo_v2.jsonl`
  (`data/saida/tablatura/censo/`) com `tablatura` verdadeiro e canal com `rollout` diferente de
  `fora`.
- **Ficam de fora**: todo vídeo já usado na `r2021`, na `r2017`, em `data/gold/ouro_video/` e
  nos lotes T8.2 a T8.6 (`ferramenta/indice.json`); os canais descartados (`raman korshun`,
  `campanitas`). No máximo 3 vídeos por canal.
- **Leitura**: o produto atual (`DETECTOR_PADRAO` e `DETECTOR_CALIBRADO` de hoje), pela
  `trava_gpu("tablatura", ...)`.
- **Conferência do painel**: as folhas no mesmo formato da `r2021`. A triagem (painel certo ou
  errado) é de um Haiku, com o critério "o retângulo verde está sobre a tablatura da tela?". A
  sessão principal confere todas as telas que ele chamar de erradas e 1 folha em cada 10 das
  outras.
- A regra só é aplicada **depois** da conferência fechada.

### Emenda 1 (2026-10-24, antes de medir)

O `censo_v2.jsonl` só tem o canal `cifra club` (215 vídeos; 37 com tablatura). Com o teto de
3 por canal, a amostra parava em 3 vídeos (o Haiku parou no sorteio, sem ler nenhum
produto). A fonte passa a ser o `censo_cache.jsonl` da mesma pasta: 3.813 vídeos de 21
canais, 2.948 com `tablatura` verdadeiro. Um vídeo do `cifra club` que o `censo_v2` (censo
mais novo desse canal) marca sem tablatura fica de fora. O resto (semente 16, 30 vídeos,
teto de 3 por canal, exclusões, critério) não muda.

## O critério

Por tela com painel, com denominadores:

1. **Custo**: certas recusadas ≤ **3 %** das certas, e notas certas perdidas ≤ **1 %**.
2. **Pega**: recusadas ≥ **60 %** das erradas.

- Os dois passam → a regra entra no produto (`video.ler_tela`), com teste no gate.
- O custo passa, mas a amostra tem menos de 5 erradas → a pega não se mede. A regra entra
  mesmo assim (recusar é o lado seguro), e a pega fica como dívida.
- O custo passa e a pega não → a regra entra (não piora nada), e o que escapou vira a
  próxima rodada.
- O custo reprova → a regra **não** entra; vai para a tabela "não repetir".

## Resultado

Medido em 2026-10-24, no commit c4183a33 + emenda bb61507a. Arquivos em
`data/saida/tablatura/recusa/r0216/`.

**A amostra.** 30 vídeos de 12 canais (`amostra.json`), lidos pelo produto em CPU em ~4 h,
sem falha. Saíram 519 telas, 512 delas com painel.

**A conferência do painel.**
- O Haiku triou as 44 folhas: 490 certas, 18 erradas e 4 dúvidas (`triagem.json`).
- A sessão principal conferiu as 22 marcadas, num mosaico (`conferir_mosaico.py`), e as folhas
  limpas 020, 022 e 027, sorteadas com `Random(16)` (36 telas, todas certas):
  - as 18 erradas se confirmam;
  - das 4 dúvidas, `asturias` t2 e t18 viram erradas (as cordas estão sobre a pauta), e
    `brasiliana` t2 e t3 viram certas (as cordas estão sobre a tab com ritmo).
- No total, **20 erradas e 492 certas** (`conferencia.json`).

**A regra:**

| medida | resultado | critério | |
| --- | --- | --- | --- |
| erradas recusadas (pega) | **16/20 (80 %)** | ≥ 60 % | passa |
| certas recusadas | **12/492 (2,4 %)** | ≤ 3 % | passa |
| notas certas perdidas | **221/20.079 (1,1 %)** | ≤ 1 % | **reprova** |

Ela barra 286 das 398 notas erradas.

**Leitura.** O custo em notas reprova, então **a regra não entra no produto**. Ela vai para a
tabela "não repetir".

O que os números mostram:
- **A faixa fixa faz todo o trabalho.** As 16 erradas pegas são todas pela faixa fixa, que
  custa 7 telas certas e 209 notas. Três dessas telas são da `asturias`, em que a faixa
  `meio` cobre a pauta e a tab.
- **O `notas_por_largura` só custa**: 5 telas certas, 12 notas, e nenhuma errada a mais.
- **As 4 que escapam**: 3 telas da `asturias`, em que o painel recortado ficou na pauta e a tab
  está embaixo, e uma tela de comentários do YouTube (faixa `base`).

A próxima tentativa precisa de uma amostra nova: esta já foi vista e virou dado de escolha.

## Correção da conferência (2026-10-24, depois da medida)

Para desenhar a regra seguinte, a sessão principal olhou as 12 telas "certas" que a regra
recusou (`faixa_certas_1.jpg` e `poucas_certas_1.jpg`). **4 delas eram painéis errados que a
triagem chamou de certos**: `aprende el trémolo` t2, t4 e t11 (as cordas estão sobre a pauta) e
`el desvelao` t22 (as cordas estão sobre o braço). As outras 8 se confirmam:
- as 3 da `asturias` (cordas sobre a tab);
- 5 telas com o painel certo, mas lidas com 1 a 3 notas numa tab cheia.

A correção está em `conferencia.json`. Com ela, **24 erradas e 488 certas**:

| medida | resultado | critério | |
| --- | --- | --- | --- |
| pega | **20/24 (83 %)** | ≥ 60 % | passa |
| certas recusadas | **8/488 (1,6 %)** | ≤ 3 % | passa |
| notas certas perdidas | **145/20.003 (0,72 %)** | ≤ 1 % | passa |

Ela barra 362 das 474 notas erradas.

**A leitura muda, mas a decisão espera.** Com o rótulo corrigido, a regra passa nos três
critérios. Só que a correção veio depois de ver o resultado, e olhou só as telas que a regra
recusou. Por isso ela não decide sozinha. A regra **igual, sem mudar nenhum limiar**, vai à
prova da 0217, em vídeos novos, com uma conferência mais forte: a sessão principal confere
toda tela que a regra recusar, e não só as que a triagem marcar.

O que se aprende sobre a conferência: a triagem do Haiku deixou passar 4 painéis errados entre
os 494 que ele chamou de certos. A conferência de 1 folha em cada 10 não pegou nenhum deles.

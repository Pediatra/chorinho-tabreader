# 0200 — R3: linha de base do ataque (o produto contra o gabarito do R2)

Fase R3 de [`plano-rotulo-tablatura.md`](../guias/plano-rotulo-tablatura.md). Sem treino, CPU.

## Pergunta

Das notas que o dono diz **não atacadas**, quantas o produto atual chama de atacadas ("sim"
falso)? E das atacadas, quantas ele chama de não atacadas?

## Pré-registro (escrito antes de medir; não muda depois)

### Entradas

- **Gabarito**: `data/saida/tab_rotulo/r2/conferir/ataque_<fonte>.json`, conferido pelo dono
  na ferramenta em 2026-10-17. As telas são as de `telas_conferidas`. Fontes: End of Beginning
  (303 notas), Room 335 (320) e From This Place (381). O La Vie en Rose (425 notas, 4 "não")
  não tem leitura do produto gravada e fica fora desta rodada.
- **Produto**: a saída gravada `data/saida/fase8/ger/ger/<slug>.json`, campo `tecnica` de cada
  nota. Cada vídeo foi lido pelo modelo da dobra que **não** o viu no treino (`gerado_por`).
  A tela do produto é a que tem uma exibição `[t0, t1]` contendo o `quadro_ref_s` da tela do
  ouro (o mesmo casamento da rodada 0101).
- **Pareamento**: corda igual, `|dx| ≤ 0,5 passo` no `x_centro_quadro`, guloso pela menor
  distância, uma nota de cada lado no máximo. O passo é o da tela do produto.

### Ataque previsto

A técnica do modelo fica na nota de **chegada** (`tab.sintetico_sistema`: `destino["tecnica"]`).

| `tecnica` do produto | ataque previsto |
| --- | --- |
| `h`, `p`, `/`, `\`, `lig`, `orn`, `enfeite` | não |
| nenhuma, `harm`, `bend`, `vib` | sim |
| nota do ouro sem par no produto | não lida |

### O que se relata

- A matriz ouro (sim, não) × previsto (sim, não, não lida), por fonte e no total.
- **"Sim" falso** = notas "não" do ouro que o produto lê com ataque "sim" ÷ notas "não" do ouro
  que ele leu. A rodada 0104 sugere perto de 80 %.
- **"Não" falso** = notas "sim" do ouro previstas "não" ÷ notas "sim" do ouro lidas.
- O "sim" falso por motivo do ouro (h, p, mordente, prolongamento, slide_ligado).

**Aceite**: não tem. É a régua do R4.

## Resultado

Comando: `python -m tab.ataque_base` (saída em `data/saida/tab_rotulo/r3/linha_de_base.json`).
Leituras: dobra 4 no End of Beginning e no Room 335, dobra 3 no From This Place. Todas as telas
do gabarito casaram com uma tela do produto.

| fonte | "sim" falso | "não" falso | não lidas (sim / não) |
| --- | --- | --- | --- |
| End of Beginning | 15 / 17 | 0 / 286 | 0 / 0 |
| Room 335 | 22 / 29 | 8 / 288 | 3 / 0 |
| From This Place | 7 / 13 | 1 / 362 | 5 / 1 |
| **total** | **44 / 59 (74,6 %)** | **9 / 936 (1,0 %)** | 8 / 1 |

"Sim" falso por motivo do ouro (total):

| motivo | lidas | previstas "sim" |
| --- | --- | --- |
| h | 22 | 21 |
| p | 8 | 8 |
| mordente | 14 | 12 |
| prolongamento | 6 | 2 |
| slide_ligado | 9 | 1 |

## Leitura

- O número esperado se confirma: o produto chama de atacadas **3 de cada 4** notas não
  atacadas (74,6 %, perto dos 80 % previstos pela 0104).
- O slide quase sempre sai certo (8 de 9). O ligado não: h e p ficam em 29 de 30 errados, e o
  mordente em 12 de 14. O prolongamento acerta 4 de 6, mas a amostra é pequena.
- O "não" falso é baixo (1,0 %). O problema é só o arco que o modelo não vê, não o arco que
  ele inventa.
- Para o R4, a régua é esta: "sim" falso 44/59 e "não" falso 9/936 nestas 3 fontes.

## Limites

- Só 59 notas "não", em 3 vídeos. O La Vie en Rose fica fora, sem leitura gravada.
- A regra simples do plano ("tinta que não é algarismo entre dois números da mesma corda"
  vira `nao_sei`) não foi medida nesta rodada.
- O Greensleeves, a Gymnopédie, o South American, o Retrato e a T8.2 entram quando o dono
  terminar a conferência deles.

## Adendo (2026-10-17): fontes novas e correções do dono

O dono conferiu Greensleeves, Gymnopédie e South American, e revisou 3 notas suspeitas:

- End of Beginning t6-n24 virou "não" (h);
- Room 335 t5-n24 ficou "sim": é a primeira nota do hammer-on;
- From This Place t5-n22 ficou "sim": o 12 não tem técnica.

Essas 3 fontes novas têm leitura gravada. O gabarito delas está em
`r2/conferir_novos/`. Retrato e T8.2 não têm leitura gravada e ficam de fora.

| fonte | "sim" falso | "não" falso |
| --- | --- | --- |
| End of Beginning | 16 / 18 | 0 / 285 |
| Room 335 | 22 / 29 | 8 / 288 |
| From This Place | 7 / 13 | 1 / 362 |
| Greensleeves | 0 / 0 | 0 / 106 |
| Gymnopédie | 0 / 0 | 0 / 391 |
| South American | 0 / 0 | 0 / 269 |
| **total** | **45 / 60 (75,0 %)** | **9 / 1701 (0,5 %)** |

As três fontes novas não têm nenhuma nota "não". Elas só medem o "não" falso, que ficou em
zero nelas. **A régua do R4 passa a ser esta:** "sim" falso 45/60 e "não" falso 9/1701.

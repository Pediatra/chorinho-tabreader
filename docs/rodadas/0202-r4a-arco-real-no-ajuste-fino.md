# 0202 — R4a: o arco real no ajuste fino

Fase R4a de [`plano-rotulo-tablatura.md`](../guias/plano-rotulo-tablatura.md). GPU.
Escrito **antes** de treinar. Os parâmetros abaixo não mudam depois de ver o resultado. Uma
variante escolhida depois vale só como diagnóstico.

## Pergunta

O ajuste fino atual (`data/saida/n4/treinar_ft.py`) **zera** a técnica nas telas reais: a
máscara de técnica é toda 0. Se essas telas passarem a ensinar a técnica com o gabarito do R2,
o "sim" falso cai de 45/60 sem estragar a casa?

## O que muda no treino (e só isto)

1. **Rótulo de técnica nas telas reais do cache** (`data/saida/n4/cache`, 63 telas dos 8 ouros).
   - Cada nota do cache casa com a nota do gabarito do R2 (`r2/conferir/` e
     `r2/conferir_novos/`): mesma tela e corda, `|x_roi + x0 − x_centro_quadro| ≤ 0,5 passo`.
   - A técnica fica na nota de **chegada**, como no gerador:

     | motivo do dono | alvo |
     | --- | --- |
     | h | `h` |
     | p | `p` |
     | slide_ligado | `/` se a casa sobe em relação à vizinha da esquerda, senão `\` |
     | prolongamento | `lig` |
     | mordente | `orn` |
     | normal, sustentada, arpejo, rasgueado, slide_entrada, mordente_simbolo, harmonico | nenhuma das 7 abaixo |

2. **Máscara por classe**, não por corda. São supervisionadas só as 7 classes que tiram o
   ataque (`h`, `p`, `/`, `\`, `lig`, `orn`, `enfeite`). Elas valem nos bins a
   `RAIO_CLASSE_BINS` de cada nota casada, e só em tela conferida. `harm`, `bend`, `vib` e os
   bins entre notas ficam sem supervisão, como hoje.
3. Nada mais muda: partida `detector_tab_v3_s1`, 3000 passos, lote 16 real + 16 sintético,
   `lr 3e-4`, mesmo aumento, mesmo gerador, mesmas dobras (`DOBRAS` de `treinar_ft.py`).
   Nome dos artefatos: `detector_tab_v3ft_d<dobra>_atq_s<semente>`.

Notas "não" que entram no treino: as das telas do cache conferidas, cerca de 85 nos 8 ouros.
O número exato entra no resultado, por dobra.

## Teste

- **Ouros**: cada vídeo é lido pela dobra que **não** o viu, como na régua. A medida é a de
  `tab.ataque_base`, com as 7 fontes que têm gabarito. Retrato e La Vie en Rose ganham leitura
  gravada nesta rodada, para as duas versões: a de hoje (`_ger`) e a nova (`_atq`).
- **T8.2**: lida pela dobra 0 (os 8 ouros no treino); ela não está no cache. São 1572 notas e
  41 "não", das 35 telas conferidas. É o teste fora de amostra.
- **Base de comparação**: os modelos de hoje (`_ger`, sementes 1, 2 e 3), lidos pelo mesmo
  caminho. A régua da 0200 é esta mesma base em 6 fontes.
- 3 sementes (1, 2, 3) por dobra: 5 dobras × 3 = 15 treinos.
  Relata-se a média e a amplitude.

## Aceite (o do plano, sem mudança)

Nos ouros fora da dobra e na T8.2, separados:

- "sim" falso **≤ 5 %** das notas não atacadas;
- "não" em nota atacada **≤ 10 %**;
- a casa na T8.2 não piora: 1551/1557, dentro da amplitude das sementes.

**Pare se** o R4a achar menos da metade das notas não atacadas de teste. Antes de mexer no
gerador ou passar ao R4b (o arco como objeto próprio), olhe a folha inteira dos erros.

## Pegadinhas a checar

- O "não" falso hoje é 9/1701. Supervisão positiva com poucos exemplos pode fazer o modelo
  inventar arco: o "não" em nota atacada é o número que vigia isso.
- 85 positivos é pouco. Se a dobra treinar com menos de 40, diga isso ao lado do número.
- O modelo é medido em `eval()`.
- Slide sobe ou desce: confira 5 casos à mão antes do treino.
- `gpu.lock` antes de cada treino. A GPU é dividida com outras trilhas.

## Ajustes antes do treino (2026-10-17, antes de qualquer número do R4a)

- **Leitura direta por tela**, no lugar de `tab.video` inteiro: quadro em `quadro_ref_s`
  (`leitor.quadro_em`), painel do produto (`painel.escolher_ou_mascara`) e detector. As duas
  versões passam pelo mesmo caminho (`python -m tab.ataque_r4 medir`). Conferido: o `_ger` da
  dobra 4 dá por esse caminho os mesmos números da 0200 (EOB 16/18 e 0/285, Room 335 22/29 e
  8/288).
- **La Vie en Rose**: as telas 1, 2 e 6 não têm região e o dono disse que o vídeo não tem
  técnica. Elas foram marcadas como conferidas no arquivo de ataque, todas "sim".
- **Notas supervisionadas** nas 63 telas do cache: 2103 atacadas e 86 sem ataque
  (`h` 24, `p` 19, `orn` 24, `/` 9, `\` 4, `lig` 6).

  | dobra | h | p | orn | / | \ | lig |
  | --- | --- | --- | --- | --- | --- | --- |
  | 1 | 24 | 8 | 14 | 5 | 4 | 6 |
  | 2 | 24 | 19 | 24 | 9 | 4 | 6 |
  | 3 | 21 | 17 | 22 | 8 | 4 | 0 |
  | 4 | 3 | 13 | 12 | 5 | 0 | 6 |

  A dobra 4 testa o End of Beginning e o Room 335, que concentram os h. Ela treina com só 3 h.
- **Base que faltava**: não havia `_ger` da dobra 1 nem o final `_ger` das sementes 2 e 3.
  Esses 5 modelos são treinados agora, com o código de hoje. Os `_ger` das dobras 2 a 4 são os
  de 2026-10-15.
- **Código**: `tab/ataque_r4.py` (alvos e medida) e o flag `--ataque` de
  `data/saida/n4/treinar_ft.py`. Sem o flag, o treino é o de antes. Roteiro:
  `data/saida/tab_rotulo/r4a/rodar.sh`. Um treino leva cerca de 23 min, então são uns 8 h no
  total.

## Resultado (2026-10-18)

Os 20 treinos terminaram sem erro (`data/saida/tab_rotulo/r4a/treino_*.log`). Medidas:
`data/saida/tab_rotulo/r4a/medida_<versao>_s<semente>.json`. As 3 sementes (1, 2, 3) estão
abaixo como `s1 / s2 / s3`.

### "Sim" falso: notas "não" do ouro lidas como atacadas

| teste | `_ger` (hoje) | `_atq` (R4a) |
| --- | --- | --- |
| 8 ouros, dobra fora | 67/84 · 67/84 · 68/84 (80 %) | 31/84 · 34/83 · 33/84 (37–41 %) |
| T8.2, dobra 0 | 28/40 · 29/40 · 28/40 (70–72 %) | 21/41 · 22/41 · 22/41 (51–54 %) |

Por fonte (`_ger` → `_atq`, faixa das 3 sementes):

| fonte | `_ger` | `_atq` |
| --- | --- | --- |
| End of Beginning | 16/18 | 2–3/18 |
| Room 335 | 22–23/29 | 15–17/29 |
| From This Place | 7/13 | 2–3/13 |
| Retrato | 19/21 | 8–9/21 |
| La Vie en Rose | 3/3 | 3/3 |

### "Não" em nota atacada e casa

| teste | medida | `_ger` | `_atq` |
| --- | --- | --- | --- |
| 8 ouros | "não" em atacada | 9 · 10 · 12 / ~2588 | 18 · 19 · 22 / ~2591 |
| 8 ouros | casa | 2652 · 2648 · 2647 / ~2672 | 2644 · 2646 · 2655 / ~2675 |
| T8.2 | "não" em atacada | 7 · 6 · 6 / ~1488 | 8 · 7 · 8 / ~1485 |
| T8.2 | casa | 1520 · 1526 · 1526 / ~1528 | 1519 · 1522 · 1525 / ~1526 |

A Gymnopédie tem a casa mais solta (`_ger` 373–380/391, `_atq` 369–380/392). As faixas se
sobrepõem, então não é uma piora.

## Leitura

- **O aceite não passa.** O "sim" falso fica em 37–41 % nos ouros e 51–54 % na T8.2. O aceite
  pede 5 % ou menos.
- O ganho é real e estável nas 3 sementes: nos ouros o "sim" falso vai de 80 % para cerca de
  39 %. O custo é pequeno: o "não" em nota atacada sobe de 0,4 % para 0,8 %, longe dos 10 %, e
  a casa fica dentro da amplitude.
- **Fora do estilo do treino, o ganho cai à metade.** Na T8.2, canais que nenhum ouro tem, o
  "sim" falso vai de 71 % para 52 %. O modelo acha **19 ou 20 das 41** notas não atacadas: menos
  da metade. **A regra de parada vale para a T8.2.**
- O La Vie en Rose (3 mordentes) não melhora em nenhuma semente.
- O Room 335 melhora pouco (15–17/29). A dobra 4 treina com só 3 h, como previsto.
- Próximo passo, pelo plano: olhar a folha inteira dos erros da T8.2 e dos ouros por motivo
  antes de passar ao R4b (o arco como objeto próprio, com arcos de vários estilos no gerador).
  Os pesos `_atq` não substituem o `DETECTOR_PADRAO`.

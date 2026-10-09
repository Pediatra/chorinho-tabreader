# Rodada 0002 — Portão de tablatura: canais novos, balanceamento e validação por canal

**Data:** 2026-10-09 · **Item (2) do objetivo** · Executado por subagente, consolidado aqui.

## O que foi feito

O portão (`tab/portao.py`) existia com 121 recortes rotulados e número ruim (3/7 na
aceitação). Esta rodada: coletou recortes dos **dois canais que faltavam**, rotulou **lendo
no olho**, balanceou as classes e mediu **deixando um canal inteiro de fora**.

### Coleta e rotulagem

| canal | recortes | tablatura | não | como |
| --- | --- | --- | --- | --- |
| `sky guitar` | 96 (16 vídeos × frações 0,6/0,75/0,9 × 2 candidatos) | **65** | 31 | leitura das folhas |
| `iwaki` | 72 (12 vídeos × 0,25/0,55/0,85 × 2) | **12** | 60 | leitura das folhas |

Total 168 novos (77 positivos, 91 negativos, 0 dúvida) → `data/gold/portao.json` de
**121 para 289** (103 tablatura / 184 não / 2 dúvida), 9 canais. Os 121 primeiros ficaram
**byte-a-byte idênticos** ao backup (`data/saida/portao_backup_121.json`).

- **Os vídeos do conjunto de aceitação foram excluídos da coleta** — inclusive achando a
  origem dos três positivos (`sky4_*` vem de `sky guitar/#4 (beginner) free pdf.mp4`;
  `asturias_t417` de `asturias - guitar lesson + tab.mp4`, conferido quadro a quadro).
- Regra de rótulo: **tablatura** = o recorte tem pauta de TAB com algarismos (mesmo com o
  vídeo do braço embaixo); **não** = foto de instrumento/mão/corpo, ou só a pauta de 5
  linhas sem TAB.
- Auditoria: `data/saida/frames/folha_D..N.png` (11 folhas de 16, ordem embaralhada e sem
  revelar qual é `_p`/`_n`), lupas `zoom_*.png` e o mapa em
  `data/saida/portao_novos/folhas_D.json`.

**Limite conhecido**: o gabarito não é amostra aleatória — são o melhor e o 2º candidato do
detector. Os números valem para a distribuição que o `escolher` produz, não para "a tela".

## Balanceamento: o sintético derruba a generalização

Seed 1, LOCA pooled / conjunto de aceitação:

| configuração | LOCA pooled | aceitação |
| --- | --- | --- |
| sem peso de classe | 230/287 = 0,801 | 5/7 |
| **peso de classe, só real** | **233/287 = 0,812** | **6/7** |
| peso + 300 sintéticos/classe | 184/287 = 0,641 | 6/7 |
| peso + 1500 sintéticos/classe | 188/287 = 0,655 | **7/7** |
| peso + 300 negativos sintéticos | 219/287 = 0,763 | 6/7 |
| peso + 1500 negativos sintéticos | 227/287 = 0,791 | 5/7 |
| só real, 22 épocas | 207/287 = 0,721 | — |

O positivo sintético **custa ~15 pontos** de generalização e a configuração que acerta 7/7
na aceitação é justamente a que pior generaliza. A escolha foi feita **pelo LOCA**, não pela
aceitação — é a diferença entre treinar para a prova e treinar para o mundo.

## Os números finais

| medida | resultado |
| --- | --- |
| conjunto de aceitação (7 casos fixos) | **6/7, 6/7, 6/7** → média 0,857, **amplitude 0** |
| LOCA pooled, 3 sementes | 0,812 / 0,753 / 0,721 → **média 0,762, amplitude 0,091** |
| recall de tablatura (LOCA) | 199/309 = **0,644** |

Por canal deixado de fora (média das 3 sementes): cifra club **1,000** · leonardo ramos
**1,000** · mr. tabs 0,933 · kimny's guitar 0,875 · guitar dell'arte 0,854 · iwaki 0,792 ·
paolo d'angelo 0,667 · **sky guitar 0,656** (recall de TAB 32/65 = **0,49**) ·
**pablo romé 0,452** (aceita 55 % do que não é TAB).

Determinismo conferido (regra nº 1): repetir a seed 1 dá probabilidades idênticas.
A única falha da aceitação é sempre a mesma e é **confiante**: as **tarraxas** de um vídeo
do `shin izumi` aceitas com p ≈ 0,95 nas três sementes.

## Veredito: não adotar ainda

O critério da [`docs/decisoes/0005`](../decisoes/0005-portao-de-tablatura-aprendido.md) era
acertar a aceitação **e** o canal deixado de fora. A aceitação está estável (6/7), mas:

- LOCA médio 0,762 com **amplitude 0,091** — maior que os ganhos que este projeto já tratou
  como reais;
- recall de tablatura 0,64 e **0,49 no `sky guitar`**: o portão rejeitaria **metade** da
  tablatura no canal do MVP;
- `pablo romé` 0,452 num canal nunca visto.

Então o portão **fica fora do pipeline**, como filtro de medida e não de veto. O caminho
para ele melhorar está medido: mais rótulos reais por canal (o sintético não ajuda aqui) e
um seletor de painel que não confunda pauta de 5 linhas com TAB — o `iwaki` rendeu só 12
positivos em 72 recortes por causa disso.

## Reprodução

```bash
python -m tab.portao treinar --gold --pesos --n 0 --epocas 12 --seed S --saida artefatos/portao_real_S
python -m tab.portao avaliar --modelo artefatos/portao_real_S/portao.pt
python -m tab.portao locanal --n 0 --epocas 12 --seed S
```

Logs: `data/saida/final_treino_s{1,2,3}.txt`, `data/saida/final_locanal_s{1,2,3}.txt`.
Modelos: `artefatos/portao_real_{1,2,3}/portao.pt`.

**Nota de artefato**: `artefatos/portao_real_1/portao.pt` foi **sobrescrito** (mesmo nome de
um modelo de rodada anterior, 119 reais + sintético). O antigo é reprodutível a partir de
`data/saida/portao_backup_121.json`, mas não está mais no disco.

# 3001 — Quantos vídeos têm pauta (P0 da trilha partitura)

**Data:** 2026-10-13 · **Trilha:** partitura · **Código:** `tab/partitura_pauta.py`,
`tab/partitura_censo.py`, `tests/test_partitura_pauta.py`

## Pergunta

Quantos vídeos do acervo ativo mostram pauta de 5 linhas, e quantos mostram só pauta (sem tab)?
O número decide o tamanho da trilha.

## Método

- Universo: os 2.998 vídeos do censo v2 (`data/saida/censo/v2/censo_v2_completo.jsonl`).
  `tv cifras` e `violaodecria` estão fora do rollout e fora desta conta.
- Amostra: até 30 vídeos por canal, sorteados com semente 0 (436 vídeos), e os 12 quadros de
  presença de cada um, lidos do cache `/cache/png` (5.232 quadros, 0 faltando). O vídeo não é
  aberto.
- Detector geométrico de pauta: 5 linhas horizontais longas, equiespaçadas (4–40 px) e com crista
  no cinza. O grupo é rejeitado se houver uma 6ª linha a uma entrelinha (seria tablatura).
  A tablatura vem do campo `tab` do censo.
- Classe do vídeo: o melhor quadro decide (pauta+tab > só pauta > só tab > nenhum).
- Custo: 567 s no total, 105 ms por quadro (leitura do HD + detecção), só CPU.

```bash
python -m tab.partitura_censo --por-canal 30 --semente 0 --saida data/saida/partitura/p0
```

## Três rodadas do detector, todas conferidas nas folhas

| rodada | defeito visto na folha | causa medida | conserto |
| --- | --- | --- | --- |
| 1 | P013–P024 (kenneth, kimny): tab lida como pauta | 6ª linha borrada (5 px) descartada pelo limite de espessura; máscara clara achava o fundo branco entre as linhas da tab | 6ª linha procurada por janela na máscara aberta; teste de crista no cinza |
| 2 | N013–N018 (iwaki): pauta perdida | objeto de ~150 px ao lado (chave) engrossava cada linha da pauta para 6–12 px | espessura medida no núcleo (≥ 50 % do pico) |
| 3 | ver abaixo | — | — |

A rodada 1 dava **2.188** vídeos com pauta: o número inflado pela tablatura. Não usar.

## Conferência visual da rodada 3 (`data/saida/partitura/p0/folhas/`)

- **Positivos** (quadros com pauta detectada, até 6 por canal): **66/68 certos**. Errados:
  P013 (kimny, tablatura) e P020 (mr. tabs, vídeo vertical, tablatura). São o único quadro com
  pauta dos seus vídeos, então são **2 vídeos falsos**.
- **Negativos** (quadros sem pauta detectada, até 6 por canal): 15/110 quadros têm pauta visível
  (iwaki 4, paolo d'angelo 6, tv on guitar 2, robert lunn 1, serge kottelat 1, guitarous 1).
  Isso derruba a classe do vídeo em **1 caso só**: paolo d'angelo, *f. kleynjans*, que deu 0 de 12.
  Os outros 14 quadros são de vídeos que já tinham pauta em outros quadros (9 a 11 de 12).
  Dos 48 vídeos "sem pauta" que aparecem nos negativos, 1 tem pauta.

## Resultado (rodada 3, com a correção da conferência)

| canal | vídeos no censo | com pauta na amostra | estimativa no canal |
| --- | ---: | ---: | ---: |
| sky guitar | 417 | 30/30 | 417 |
| robert lunn | 369 | 29/30 | 357 |
| guitar dell'arte | 361 | 26/30 | 313 |
| iwaki | 164 | 30/30 | 164 |
| pablo romé | 123 | 27/30 | 111 |
| serge kottelat | 38 | 30/30 | 38 |
| transcriptor | 35 | 24/30 | 28 |
| paolo d'angelo | 14 | 14/14 (13 + 1 perdido) | 14 |
| ギタロー guitarous | 55 | 4/30 | 7 |
| tv on guitar | 5 | 5/5 | 5 |
| lonelypicker | 3 | 1/3 | 1 |
| kimny's guitar | 108 | 0/30 (1 falso) | 0 |
| mr. tabs | 22 | 0/22 (1 falso) | 0 |
| cifra club, kenneth acoustic, leonardo ramos, shin izumi, vvxo, yunus | 1.483 | 0 | 0 |
| **total** | **2.998** | **220/436** | **≈ 1.455 (49 %)** |

- **Só pauta, sem tab: praticamente não existe.** São 5 vídeos na amostra, e o que se vê na folha
  (ex.: paolo, N056) é tab que o censo não marcou, não vídeo sem tab. A partitura deste acervo
  vem **junto com a tablatura**. Então a conferência cruzada de altura (pauta × tab) e o tempo
  herdado da tab valem para quase todo vídeo com pauta.
- Em quadros: 1.975 de 5.232 quadros (38 %) têm pauta. Entrelinha mediana de 14,5 px; por canal
  vai de 10 px (serge kottelat) a 18 px (transcriptor). O 20,5 px do kimny é o quadro falso.

## Limites

- A amostra tem 30 vídeos por canal. Nos canais grandes, a fração tem erro de ± ~10 pontos
  percentuais. A estimativa por canal é fração × tamanho do canal, sem intervalo de confiança.
- `mr. tabs`: o ESTADO registrou pauta num quadro deste canal (painel #15), e o contexto diz que lá
  a pauta **rola**. A amostra (22/22 vídeos × 12 quadros) não viu nenhuma pauta. É possível
  subcontagem, mas o canal é pequeno (22 vídeos).
- O detector perde pauta densa ou colada (paolo d'angelo), e a conta por vídeo absorve isso.
  Para a P1, o recorte de pauta não pode depender só deste detector sem conferência.

## Adendo (mesmo dia): detector refinado na P1, censo refeito (rodada 6)

Ao montar os recortes da P1, a Gymnopédie (robert lunn) dava 4 de 5 quadros sem pauta. As
linhas dela têm 4 a 5 px (entrelinha 20,5), e o limite de espessura era 4 px. Subir o limite
para 6 px fez barras de colcheia (5 a 6 px) virarem "linhas". Isso derrubava pautas reais
(como falsa 6ª linha, ou quebrando o grupo de 5) e deixava passar tab cuja linha de cima é
coberta de algarismos (kimny). Mudanças finais em `tab/partitura_pauta.py`:

- espessura máxima 6 px; teste de crista com distância proporcional à espessura;
- linha "parecida" = espessura ≤ mediana das 5 linhas + 2 px, exigida dentro do grupo e na
  6ª linha (barra de colcheia não é corda);
- 6ª linha forte: sobreposição ≥ 50 % do próprio comprimento; 6ª linha fraca: ≥ 50 % da
  extensão da pauta.

Censo refeito, mesma amostra e semente (`data/saida/partitura/p0_rodada6.log`), comparado com a
rodada 3 conferida acima: **21 quadros ganhos, 0 perdidos**; os 21 ganhos foram conferidos um a
um (`data/saida/partitura/diag/ganhos_r3_r6.jpg`) e são todos pauta. A única troca por vídeo é
o paolo d'angelo *f. kleynjans*, antes perdido e somado à mão, agora achado. Os 2 falsos
(kimny, mr. tabs) continuam. **O número não muda: 220/436, ≈ 1.455 vídeos.**

# 1007 — Braço pela música: estabilizado; correção pela imagem não adotada

**Data**: 2026-10-12. Continua a rodada [1006](1006-braco-calibrado-pela-musica.md). MVP.

## O que mudou

- **Estabilização** (`tab/maos_refinar_braco.py`): consenso de 10 sementes do RANSAC e refino
  pelo erro de REPROJEÇÃO (Levenberg–Marquardt em numpy, perda de Tukey com escala da largura
  da casa, reassociação da ponta mais perto a cada iteração).
- **Música + imagem** (`tab/maos_linhas_braco.py`): com a H da música, o braço é retificado na
  mediana de 30 quadros e cordas/trastes são procurados só em janelas em volta do previsto.
  Experimento; **não adotado** (abaixo).
- CLI das medições: `python -m tab.maos_medicoes_braco`.

## Medido

Estabilidade (3 conjuntos de 10 sementes): grade difere mediana 0,027 px (amplitude 0,041),
máximo 0,082 px. Sem os instantes do gabarito: difere da versão com todos em mediana 1,07 px,
máximo 2,30 px (na 1006: 30 px e 198 px).

**Dedo** (avaliador oficial, ponta | voto; 53 notas):

| calibração | com instantes do gabarito | **sem instantes do gabarito** |
|---|---|---|
| à mão (coordenadas fixas) | 42 \| 43 | — |
| música (1006) | 42 \| 43 | 40 \| 41 |
| **música estabilizada** | 42 \| 43 | **42 \| 43** (pisadas 29/40) |
| música + imagem | 42 \| 43 | 41 \| 42 |

**Contra o gabarito do dono** (quadro q02 do gabarito do braço, t = 589,35 s, mesma cena):

| | à mão | música (1006) | música estabilizada | música + imagem |
|---|---|---|---|---|
| corda 1: px / fração do vão 1–6 | 1,7 / 0,014 | 18,0 / 0,153 | 14,4 / 0,112 | 4,8 / 0,033 |
| corda 6: px / fração do vão 1–6 | 0,8 / 0,006 | 16,2 / 0,137 | 8,8 / 0,069 | 7,7 / 0,055 |
| nut: px / fração da casa 1 | 0,7 / 0,007 | 14,5 / 0,132 | 3,6 / 0,036 | 10,4 / 0,106 |
| trastes com mesmo número a < 1/4 de casa | 14/14 | 12/14 | **14/14** | 14/14 |
| trastes: fração mediana da casa | 0,030 | 0,051 | 0,032 | 0,035 |

Contra a calibração à mão (`braco.json`, cordas × casas 1–12): música estabilizada 0,091 casa
mediana (p90 0,197); música + imagem 0,040 (p90 0,095).

## Leitura

- **A música estabilizada é adotada**: ao LONGO do braço (trastes e nut) iguala a calibração
  feita à mão contra o rótulo do dono (14/14 trastes, 0,032 casa; nut 0,036 casa) e dá o mesmo
  acerto de dedo sem usar nenhum instante do gabarito (42/53).
- **Através do braço** (cordas) ainda erra: 0,11 do vão 1–6 na corda 1. A escala de v aprendida
  pela música é menor que a real (vão medido na imagem ~179 px contra 160 px da música): a H
  aprende onde ficam as PONTAS DOS DEDOS para cada corda, não as cordas.
- **Música + imagem não adotada**: melhora as cordas, mas piora o nut (3,6 → 10,4 px), não
  melhora o dedo, e é frágil: as cordas 1 e 2 têm contraste fraco e caíram na borda da janela
  (o pico real está fora dela); alargar a janela faz a corda 1 pegar a corda 2. Próximo passo
  para as cordas: atribuir as 6 cordas juntas por espaçamento uniforme (um "pente"), não uma
  janela por corda.

Saídas: `data/saida/maos/m3c/` (`calibracao_v2.json/.jpg`, `mediana_braco.png`, predições
`pred_calib_est_*`, `pred_calib_img_*`).

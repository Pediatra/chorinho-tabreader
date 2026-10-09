# Rodada 64 — a assinatura de lixo separa um canal dos outros três

## 1. A medição

| canal | tokens | largura < 0,3 passo | `partes ≥ 2` | lixo no gabarito |
| --- | --- | --- | --- | --- |
| iwaki | 27 | **0 %** | 0 % | 0 |
| sky guitar | 15 | **0 %** | 0 % | 0 |
| **raman korshun** | 94 | **28 %** | 74 % | **7** |
| paolo d'angelo | 71 | **0 %** | **100 %** | 0 |

## 2. As duas conclusões

**1. A assinatura de lixo separa o `raman` de todos os outros.** Tokens com menos de 0,3 passo de
largura — a marca das barras verticais sem algarismo — aparecem **só no `raman`** (28 %). Nos outros
três, **zero**. É a evidência que faltava para decidir a rejeição **por canal**: ligada onde há
assinatura, desligada onde não há.

**2. `partes ≥ 2` é inútil como proxy de lixo — e agora está provado com números.** O
`paolo d'angelo` tem **100 % dos tokens fundidos** e **zero lixo** (0 % estreitos, 0 rótulos `junk`).
Ou seja: tokens fundidos, ali, são **acordes e apoios**, não sujeira. Foi exatamente esse proxy que me
fez piorar a métrica duas vezes (rodadas 60 e 62).

| proxy | serve? |
| --- | --- |
| `partes ≥ 2` | **não** — 100 % no `paolo` com zero lixo |
| **largura < 0,3 passo** | **sim** — 28 % no `raman`, 0 % nos outros três |

## 3. O que isso destrava

A classe de rejeição, que na rodada 22 eu descartei como "troca" (ganhava 6 no `raman`, perdia 5 em
`sky`+`paolo`), era uma troca **porque eu a liguei em todos os canais**. Agora há um critério
medido para ligá-la só onde ela faz sentido:

- **`raman`** → rejeição **ligada** (28 % de tokens estreitos, 7 rótulos `junk` no gabarito);
- **`iwaki`, `sky`, `paolo`** → rejeição **desligada** (0 %), preservando os 27/27, 15/15 e 30/30 que
  já estão corretos.

## 4. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** — casas | **0,875** (melhor seed) · **0,854** média de 3 sementes · 0,955 alcançável |
| **canais limpos** | `iwaki` 27/27, `sky` 15/15, `paolo` 30/30 — lixo 0 % |
| **`raman`** | 12/24 — **causa: lixo (28 %)**, com critério de decisão agora medido |
| **classe `tecnica`** | treinada, estável, sem ganho de acerto — mantida por estabilidade |
| **tempo** | faixa (`skyguitar`, 0,16 s) e cor (`cifra club`, 41/41 onsets) |
| **gabarito** | restaurado; observações registradas |

## 5. Próximo passo

1. **ligar a classe de rejeição condicionada à assinatura** (fração de tokens estreitos acima de um
   limiar, medido por vídeo — não por canal, porque o marcador me ensinou que varia dentro do canal);
2. **reaferir com 3 sementes** verificando que `iwaki`/`sky`/`paolo` **não regridem**;
3. ampliar o gabarito para casas 8–24;
4. rodar em escala com a decisão por vídeo.

Esta rodada entrega o que faltava desde a rodada 22: um **critério medido** para uma decisão que eu
vinha tomando por palpite (ligar ou não a rejeição). E derruba, com números, o proxy que me custou
duas rodadas.

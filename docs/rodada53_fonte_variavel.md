# Rodada 53 — tamanho de fonte variável: 0,805 → 0,851 (com 3 sementes)

## 1. A correção

No `tools/sintetico.py`, o tamanho da fonte era **fixo em 0,95 do passo** — mas o acervo real tem
algarismo de **0,38 passo** (medido no painel do `cifra club`) e de 0,6 passo (`skyguitar`). Passei a
**sortear entre 0,55 e 1,0 do passo**.

## 2. Medição com 3 sementes (a regra que eu estabeleci depois do erro de ruído)

| semente | iwaki | sky guitar | raman | paolo | **TOTAL** |
| --- | --- | --- | --- | --- | --- |
| 0 | 27/27 | 15/15 | 12/24 | 27/30 | **0,844** |
| 1 | 27/27 | 15/15 | 11/24 | 26/30 | **0,823** |
| 2 | 27/27 | 15/15 | 13/24 | 30/30 | **0,885** |

| | antes (fonte fixa) | **agora (fonte variável)** |
| --- | --- | --- |
| média | **0,805** | **0,851** |
| amplitude | 0,750 – 0,854 | 0,823 – 0,885 |
| iwaki | 23–27 de 27 | **27/27 nas três** |
| sky guitar | 11–15 de 15 | **15/15 nas três** |
| paolo | 24–29 de 30 | 26–30 de 30 |
| raman | 12–19 de 24 | 11–13 de 24 |

## 3. O que é ganho e o que é estabilidade

- **média +0,046** — logo abaixo do limiar de 0,05 que eu mesmo declarei para chamar algo de ganho;
- **mas a estabilidade mudou de patamar**: `iwaki` e `sky guitar` ficaram **perfeitos nas três
  sementes**, quando antes variavam (23–27 e 11–15). Isso é mais forte que a média: antes eu não
  podia afirmar que aqueles canais estavam certos; agora posso, em três execuções.
- **`raman` não melhorou** (11–13 de 24) — e é coerente: os erros dele são **marca de técnica no
  token** (`7` + slide), não tamanho de algarismo. Correção de tamanho não mexe nisso.

## 4. A lição confirmada

Esta é a **segunda vez** que uma mudança no **gerador** move o resultado, e a **quarta** tentativa
de mexer na **visão** que não moveu nada:

| onde eu mexi | efeito medido |
| --- | --- |
| regra de altura no extrator (rodada 12) | 0 |
| regra de orientação no extrator (rodada 13) | 0 |
| trocar arco por barra no gerador (rodada 14) | **−0,166** (revertida) |
| somar variação de corda no gerador (rodada 16) | +0,052 |
| classe de rejeição (rodada 22) | 0 (troca entre canais) |
| **variar tamanho de fonte no gerador (agora)** | **+0,046 e estabilidade** |

O gargalo deste sistema é **cobertura do que eu desenho**, não regra de visão. Está medido seis vezes.

## 5. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, técnica) | **0,851 (3 sementes)**; `iwaki` e `sky` perfeitos e estáveis |
| **painel e geometria** | resolvidos nos dois estilos de painel |
| **tempo — marcador por faixa** | validado no `skyguitar` (desvio 0,16 s) |
| **tempo — marcador por cor** | onset medido (41/41 notas, 8 ataques, 1,80 s) |
| **o que resta no reconhecimento** | `raman` (marca de técnica no token) e a casa dos canais sem gabarito |

## 6. Próximo passo

1. **marca de técnica como classe própria** (é o que resta no `raman`, e agora é o único erro grande);
2. ampliar o **gabarito real** para casas 8–24 (o que limita a medição);
3. janela maior para o **reinício de frase** no marcador por cor;
4. rodar em escala nos canais com gabarito e nos de mesmo estilo.

Número oficial atualizado: **0,851**, medido em 3 sementes — e com a ressalva que continua valendo:
96 glifos, 4 canais, casas 0–7.

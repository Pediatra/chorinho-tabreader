# 1040 — Régua de casas: numerar sem ver o nut (estudo de viabilidade, CPU)

**Data**: 2026-10-21. O pré-registro vem antes da medida. É uma rodada de desenvolvimento: usa
só marcas do dono já vistas e não decide peso nem regra do ciclo.

**A pergunta**: o próprio braço diz o número da casa, sem o nut? A ideia é comparar duas
medidas no meio de cada casa:
- **a largura da casa**, ao longo do braço, que encolhe ~5,6 % a cada casa (fator 2^(−1/12));
- **a abertura das cordas**, da corda 1 à corda 6, que cresce devagar do nut para o corpo.

A razão **r = largura ÷ abertura** cai **~7 % por casa**. Ela é medida no mesmo lugar da
imagem, então a perspectiva se cancela em boa parte.

**Para que serve**:
1. **Pegar a numeração deslocada de 1 casa** (o erro da [1029](1029-ciclo-de-revisao-pablo-rome.md),
   em que o 1º traste é tomado por nut) **como sinal de revisão**, e não como resposta.
2. Numerar quando o nut está fora, se a precisão permitir.

**O risco**: violão de aço e violão clássico têm a abertura diferente (~20 %, o que equivale a ~2
casas). Por isso a medida principal calibra por vídeo.

## Dado

- **As marcas do dono** em M3b, M11b, N (M25 prova), M26, M27, M29, M32 e M36: quadros com o
  nut marcado (não "fora"), as duas cordas e pelo menos 3 trastes numerados.
- **Com capo**, a casa real é a casa contada do capo mais a casa do capo
  (`capo_por_video.json`). Um quadro com capo e sem a casa conhecida sai da medida (b), e na (a)
  ele entra, porque o capo é fixo dentro do vídeo.
- **Os 4 quadros que a 1037 tirou** ficam fora também aqui: M3b q10, M32 q14 e q45, e C q139.

## Medidas

- **(a) Calibrada por vídeo, deixando um quadro de fora.**
  - Ajusta log r = α − β·n nos outros quadros do mesmo vídeo.
  - No quadro de fora, testa os deslocamentos s ∈ {−2, −1, 0, +1, +2}, numerando as casas dele
    como n + s, e escolhe o de menor erro quadrático.
  - Acerto é s = 0. A medida conta só quadros com ≥ 3 casas medidas, em vídeos com ≥ 3 quadros
    utilizáveis.
- **(b) Sem calibração, deixando o vídeo de fora**: uma curva só, ajustada nos outros vídeos, com
  a casa real. Só reportado.
- **(c) O ruído**: o desvio de log r em torno da reta do vídeo, comparado com o passo de uma casa
  (β).

## Critério

| resultado | o que fazer |
| --- | --- |
| (a) acerta s = 0 em ≥ 95 % dos quadros medidos | a régua vira candidata a **sinal de numeração deslocada**. A próxima rodada a mede nas previsões do ciclo (1029 e 1036), contra os falsos que passaram |
| (a) < 95 % | arquivar e ir para o "não repetir". Regra geométrica sem dado novo já deu 0 seis vezes (regra 9 do AGENTS.md) |
| (b) ≥ 80 % | reportar: dá para numerar sem calibração? Não vira regra nesta rodada |

## Riscos declarados antes

- **As marcas dos ciclos foram pré-preenchidas pelo detector**, e o dono só conferiu. O
  traste "impreciso" de ~0,1 casa entra como ruído.
- **O traste é marcado como um ponto no eixo**, e não como linha. A largura sai da diferença de
  posição ao longo do eixo.
- **Com o braço muito inclinado em relação à câmera**, a perspectiva ao longo do braço e através
  dele não se cancela. O ruído (c) mostra o tamanho disso.

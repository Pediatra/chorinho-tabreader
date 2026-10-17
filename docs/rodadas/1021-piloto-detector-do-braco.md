# 1021 — Piloto do detector do braço: aprende sem marca nova? generaliza para canal novo?

**Data**: 2026-10-17. **Estado**: regras a priori. Este documento ganha commit antes do
primeiro treino.

**Pedido do dono**: o dono aprovou a direção (1019 e 1020 encerradas). O ponto de partida é
não marcar 500 a 1.000 quadros sem saber se adianta. O piloto mede a curva de aprendizado
**sem nenhuma marca nova** e diz quanto ainda falta marcar:
- nada;
- cerca de 10 quadros por canal;
- ou parar.

## Pergunta

Um detector treinado só com:
- braços sintéticos;
- os rótulos que o rastreador congelado (`tab.maos_braco_cadeia`, cfg2, commit 1bcb9b35)
  espalha a partir das marcas do dono,

acerta as cordas e os trastes em **canais que ele nunca viu**? E o acerto cresce com mais
vídeos de treino?

## Escopo da fase A (esta rodada)

A fase A mede só a **parte difícil**: os pontos finos dentro de uma faixa do braço já situada.
A localização grosseira fica fora. Ela já tem candidatos: o rastreador, a caixa do modelo de
linguagem (27 de 33 na 1020) ou um estágio 1 futuro. Para não depender deles, a faixa é
simulada com erro.

- **Faixa retificada**: um retângulo girado ao longo do eixo do braço, reamostrado em
  **1024 × 192** px, com o braço na horizontal.
  - O eixo vai do nut até a ponta das cordas no corpo.
  - A altura da faixa é 3 vezes a distância entre as cordas 1 e 6.
  - O eixo vem do gabarito com **erro simulado** (semente fixa 20261021): deslocamento
    perpendicular de até ±0,3 da largura do braço, ±5 % do comprimento ao longo do eixo,
    rotação de ±3° e escala de ±10 %.
- **Saída do modelo**: 3 mapas de calor na faixa:
  - a linha da corda 1;
  - a linha da corda 6;
  - os fios dos trastes, incluindo o nut.
- **Pós-processamento por geometria**:
  - cada corda vira uma reta ajustada à crista do mapa;
  - os trastes viram picos ao longo do eixo, ajustados pelo modelo projetivo das 12 notas
    (`tab.maos_braco_regra`). Fica com o nut e a numeração que melhor explicam os picos;
  - se o ajuste não fecha, a resposta é "não achou".
  - O resultado volta para os pixels do quadro e é medido com `tab.maos_braco_tempo.erros` e
    `classificar`, como em todas as rodadas do braço.
- **Rede**: uma U-Net pequena, em torch e torchvision, já instalados e com licença BSD.
  - Sem ultralytics e sem dependência nova.
  - Codificador ResNet18 com os pesos ImageNet do torchvision (`IMAGENET1K_V1`). O dono
    aprovou o download em 2026-10-17, antes de qualquer treino.
  - Arquivo: `artefatos/torch/hub/checkpoints/resnet18-f37072fd.pth`, com sha256
    `f37072fd…560e07ec`. Para usar, exporte `TORCH_HOME=/app/artefatos/torch`.
- **Determinismo**: `tab.sintetico.fixar_semente`. São **3 sementes por configuração**, com
  média e amplitude reportadas.
- **GPU**: trava própria `data/saida/gpu.lock.maos`, com pelo menos 3 GB livres.

## Dados

| fonte | o quê | papel |
| --- | --- | --- |
| **S** (sintético) | Braço plano desenhado por homografia sobre quadros reais do acervo: madeira com cor e grão variados, trastes nas posições das 12 notas, 6 cordas de espessura crescente e nut claro. Inclui perspectiva, desfoque, ruído, JPEG e oclusão por manchas e recortes de mão. Rótulo exato. | treino |
| **R** (rastreador) | Nos 28 vídeos do `braco.json` (8 canais), cada quadro do dono é o quadro-chave. O rastreador espalha a marca para quadros da mesma cena, de 2 em 2 s. Entra só o que o rastreador entrega como "achou". | treino |
| **G** (gabarito) | Os 66 quadros do dono em `braco.json`. | prova da fase A, por canal deixado de fora |
| **T** (M11b) | Os alvos q46–q77 de `braco_m11b.json`, de 8 canais novos. | **lacrado**: só a fase B |

**Prova por canal deixado de fora**: são 8 dobras, uma por canal do `braco.json`.
- Em cada dobra, os quadros R e G daquele canal saem do treino.
- A prova é feita nos quadros G desse canal.
- O resultado soma as 8 dobras sobre os 66 quadros.

Os quadros da M11b não entram de forma alguma: nem em S (fundo), nem em R, nem em G.

## Experimentos

| | treino | o que mede |
| --- | --- | --- |
| A1 | só S | o sintético sozinho já ensina? |
| A2 | só R, com 25 %, 50 % e 100 % dos vídeos de treino de cada dobra | a curva com rótulo do rastreador |
| A3 | S + R, com 25 %, 50 % e 100 % | a curva com os dois |

- Os subconjuntos de 25 % e 50 % são sorteados por vídeo, com a semente 20261021, e são
  cumulativos: os vídeos de 25 % estão dentro dos de 50 %.
- O treino tem duração fixa, em passos iguais para todos. Não há parada antecipada pelo
  resultado da prova.

## Medidas

- Classes nos 66 quadros G, por experimento e fração: certo, impreciso, falso e não achou.
  São as mesmas regras de sempre: certo é tudo abaixo de 0,25 casa ou vão; falso é algo acima
  de 0,5.
- Mediana de `perp_cordas` e de `pior_traste_casas`.
- Média e amplitude entre as 3 sementes.

## Critério de decisão (congelado)

| resultado do A3 com 100 % (média das sementes) | o que fazer |
| --- | --- |
| certos ≥ 70 % e falsos ≤ 5 % | **segue para a fase B**: estágio 1 de localização e prova lacrada na M11b. Nenhuma marca nova. |
| abaixo disso, mas a curva sobe (certos com 100 % ≥ certos com 25 % + 10 pontos) | **faltam dados**: propor cerca de 10 quadros do dono por canal, com uma nova curva antes de seguir |
| abaixo disso, e a curva plana | **parar**: o detector não aprende com este dado. A conclusão é registrada, e ninguém marca mais. |

O A1 e o A2 não decidem nada sozinhos. Eles explicam de onde vem o resultado do A3.

## Riscos declarados antes

- **Os rótulos do rastreador vêm de 28 vídeos.** A variedade é de vídeos e canais, não de
  quadros. A curva mede justamente isso.
- **A faixa simulada esconde o estágio 1.** Uma aprovação aqui não prova o detector inteiro.
  A fase B mede o conjunto.
- **Nenhum quadro G entra no treino da sua dobra.** Mas os quadros R do mesmo canal entram em
  outras dobras, e por isso a separação é por canal.

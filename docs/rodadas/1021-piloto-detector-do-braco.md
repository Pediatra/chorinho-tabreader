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

## Emenda 1 (2026-10-17, antes de qualquer treino): portões de validação e ordem

O dono pediu para validar tudo antes da corrida longa. Nenhum portão olha os quadros G: eles
usam só S, R e o próprio pós-processamento.

| portão | teste | passa se |
| --- | --- | --- |
| V1 oráculo | Mapas de calor **perfeitos**, desenhados a partir do rótulo G, passam pelo pós-processamento e pela medida. Valida a cadeia de geometria e de métrica sem modelo nenhum. | ≥ 95 % "certo" nos 66 |
| V2 sobreajuste | 300 passos em 32 amostras S. | a perda cai pelo menos 10 vezes, e ≥ 90 % "certo" nessas 32 amostras |
| V3 validação S | Um treino A1 completo (semente 1), medido em 500 amostras S **fora do treino**. | só registro: se der < 50 % certo, o modelo nem aprende o sintético; investigar antes de seguir |
| V4 tempo | Tempo de um treino completo. | total previsto ≤ 10 h. Se passar disso, reduzir os passos **antes** de qualquer medida em G, igual para todos |

- No V1, o rótulo G é usado como entrada do oráculo, não como medida do modelo. Ele só
  confirma que a cadeia não perde precisão.

**Redução e ordem**, para a decisão sair primeiro:
1. **A3 com 100 %**: 8 dobras × 3 sementes. É a linha que decide; resultado parcial no
   critério.
2. **A1**: 3 sementes, sem dobra, porque S não usa rótulo de canal.
3. **A2 com 100 %**: 8 dobras × 3 sementes.
4. **A2 e A3 com 25 % e 50 %**: 8 dobras × **1 semente**. Essas frações servem só para a
   forma da curva; a decisão usa a média das sementes do A3 com 100 %.

A regra da curva continua a mesma: certos com 100 % ≥ certos com 25 % + 10 pontos.

## Emenda 2 (2026-10-17, depois do V1 e antes de qualquer treino)

**Resultado do V1:** 58 de 64 certos (90,6 %), reprovado. G tem 64 quadros e não 66, porque
q09 e q63 estão com nut `fora` no gabarito e não formam faixa.

**Causa:** 6 falsos, todos por numeração deslocada em um traste. O pós-processamento numerava
os trastes pelo melhor ajuste das 12 notas. Mas nesses quadros os trastes do dono não são
projetivos dentro de 3 px:
- a distância do nut ao traste 1 vai de 1,3 a 1,8 vezes o espaço seguinte (no q06, 140 px
  contra 79 px);
- há espaços irregulares sob a mão.

Isso é propriedade do gabarito: o dono estima os trastes sob a mão. Não é defeito do gabarito.
No q50, a perturbação ainda empurrou o nut para fora da faixa (x = −2,8).

**Mudanças**, todas antes de qualquer modelo treinado. O critério do V1 (≥ 95 %) não muda.

1. **Margem da faixa**: 0,12·L antes do nut, em vez de 0,05·L, para que a perturbação nunca
   corte o nut. O G é regenerado.
2. **Canal próprio para o nut**: 4 mapas em vez de 3. O nut é visualmente distinto (osso
   claro, fim da escala).
3. **Numeração por ordem, não por ajuste**:
   - o nut vem do canal próprio;
   - os picos do canal de trastes, da esquerda para a direita a partir do nut, são os
     trastes 1, 2, 3 e assim por diante;
   - um intervalo maior que 1,6 vezes o espaço esperado (pela razão 2^(−1/12) entre os vizinhos
     detectados) conta como traste escondido, e o número pula;
   - o ajuste das 12 notas só preenche os trastes escondidos e estende até o último.

## Emenda 3 (2026-10-17, depois do V1 e do V2, antes de qualquer medida de modelo em G)

**V1 com a Emenda 2: 62 de 64 certos (96,9 %), passou.** Os 2 falsos (q06 e q56) têm o
intervalo nut → traste 1 do rótulo em cerca de 1,7 vez a escala. A regra pula um número ali.

**V2 reprovou (perda 0,92 → 0,51; 0 de 32 certos), com dois defeitos de protocolo:**
- **Aquecimento**: 200 passos de aquecimento em 300 deixam só 100 passos de treino de verdade,
  já em queda pelo cosseno.
- **Piso da perda**: com alvo gaussiano suave, a BCE tem um piso positivo (a entropia do
  alvo). "Cair 10 vezes" pode ser impossível mesmo para um modelo perfeito.

**Tempo:** 1,3 s por passo, medido com a máquina saturada (carga 59 em 12 núcleos: o R sendo
gerado, o treino de outra trilha na GPU e um processo da partitura; GPU a 4 %). O tempo só é
medido de novo com o R terminado.

**Mudanças, só no portão V2** (ele é teste de sanidade, não experimento):
- 1.000 passos, taxa constante (3e-4 no decodificador e 1e-4 no codificador), sem aquecimento
  e sem aumento de dados.
- Critério de perda: **(perda − piso) cai pelo menos 10 vezes**. O piso é a BCE do alvo
  contra ele mesmo, com o mesmo `pos_weight`.
- O critério de ≥ 90 % de certos nas 32 amostras não muda.
- Também é gravada uma folha com entrada, alvo e saída de 4 amostras, para conferir o
  alinhamento a olho.

O cronograma dos experimentos (A1, A2 e A3) não muda aqui. Os passos são decididos no V4, com
a máquina livre.

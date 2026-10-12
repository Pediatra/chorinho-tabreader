# Rodada 1002: escolha do detector de mãos (M1)

Data: 2026-10-12. Trilha das mãos, M1 (ver `docs/guias/contexto-maos.md`).
Decisão: [1002](../decisoes/1002-detector-de-maos.md). Censo de partida: [rodada 1001](1001-censo-de-maos.md).
Imagem do produto: `chorinho-maos:dev` ([decisão 1001](../decisoes/1001-imagem-derivada-maos.md)).

## Pergunta

Qual detector de mãos usar para a mão do violonista, medido em quadros do acervo? Os casos
difíceis são a mão do braço vista de costas, em preto e branco, borrada, ou em close (com a
janela de close separada, sem corpo ligado).

## Candidatos

- **MediaPipe HandLandmarker** (censo M0): quadro inteiro e blocos 2×2, confiança 0,3.
  Não dá lado confiável para a mão do braço (rodada 1001), mas é o ponto de partida.
- **Hand** (rtmlib 0.0.16): RTMDet-nano de mão (`568d3ea9…fbac2`) + RTMPose-m hand
  (`39e85893…cd29`). 21 pontos, **sem lado**.
- **Wholebody** (rtmlib 0.0.16, `to_openpose=False`): YOLOX-m de pessoa
  (`yolox_m_8xb8-300e_humanart-c2c7a14a.onnx`, sha256 `3dea6513…f5f23`) + RTMW-DW-X-L
  (`rtmw-dw-x-l_simcc-cocktail14_270e-256x192_20231122.onnx`, sha256 `9a9bc17c…aa58`).
  133 pontos por pessoa. Mão esquerda nos índices 91 a 111, direita nos 112 a 132. O lado
  vem do corpo, não do rótulo do detector.

## Rodada 1: sondagem (36 quadros do piloto)

Rótulo **provisório (agente)**, o mesmo do M0 (`data/saida/maos/rotulo_agente_piloto.json`,
36 quadros, 34 mãos esquerdas e 33 direitas visíveis). CPU. Duas execuções idênticas.

| detector | quadro certo | mão esquerda | mão direita | falsas | tempo/quadro CPU |
| --- | --- | --- | --- | --- | --- |
| MediaPipe 0,3 + 2×2 | 32/36 | 30/34 | 32/33 | 0 | — |
| Wholebody 0,5 | 36/36 | 34/34 | 33/33 | 0 | 0,53 s |
| Wholebody 0,3 | 34/36 | 34/34 | 33/33 | 2 | 0,53 s |
| Hand | perde 11 de 66 mãos\* (sobretudo a do braço); sem lado | | | 0 | 0,13 s |

\* São 66 mãos nos 35 quadros com rótulo completo. O 36º quadro (24) tem o lado direito
indeciso e fica fora da conta; a esquerda dele entra nas 67 mãos visíveis do rótulo (34 + 33).

Ressalva: os mesmos 36 quadros foram usados para ajustar o MediaPipe (0,3 e 2×2). Esta
tabela não é prova fora do ajuste.

## Rodada 2: pontas dos dedos (20 mãos, 10 esquerdas e 10 direitas)

Distância mediana das pontas dos dedos, normalizada pela palma (punho até a base do dedo
médio), nas mãos que as variantes acham (20 mãos: 10 esquerdas e 10 direitas):

- WB-BGR × WB-RGB (a conversão de cor, só na pose): **0,041** de palma no geral
  (esquerdas 0,042; direitas 0,041).
- WB-BGR × MP: **0,205** no geral; esquerdas **0,263**; direitas **0,131**.
- WB-RGB × MP: **0,196** no geral; esquerdas **0,342**; direitas **0,118**.

Medianas de `data/saida/maos/m1/pontas.json` (`medianas_gerais` e `medianas_gerais_por_lado`).

Leitura: a conversão BGR → RGB muda pouco (0 a 1 quadro de diferença na validação). O produto
usa **BGR**, o padrão da rtmlib. A diferença entre WB e MP é grande: na leitura visual
**provisória (agente)**, o Wholebody põe as pontas melhor na mão do braço. Exemplos:
`kenneth`, onde o MediaPipe joga o polegar no dedo médio; `cifra club`, onde o MediaPipe
deforma a mão.

Limites: o polegar escondido atrás do braço é "inventado" perto do indicador (`iwaki`); mão
muito aberta com pontas sobrepostas. **Não há gabarito de pontas.** Isso só se mede no M2
(dono).

Folhas: `data/saida/maos/m1/pontas_{1..4}.jpg`; dados: `data/saida/maos/m1/pontas.json`.

## Rodada 3: GPU

Wholebody na RTX 3060 Ti: **0,044 s por quadro** (~12,6 vezes mais rápido que a CPU), ~550 MiB
de memória de GPU. Duas execuções idênticas.

GPU × CPU: os pontos diferem em média 0,5 px. Alguns pontos chegam a 14 a 21 px com score
acima de 0,3 (provável empate entre picos do SimCC). Consequência: **o produto usa só a GPU**.
Não se misturam números de CPU e de GPU. Protocolo do `gpu.lock` respeitado (`AGENTS.md`).

Saídas: `data/saida/maos/m1/tempo_gpu.json`.

## Rodada 4: validação fora do ajuste (90 quadros)

90 quadros: 30 da conferência do M0 (C01 a C30) e 60 novos (N01 a N60), sorteados com
`sortear` (semente 20261014), excluindo o piloto e a conferência. Quadro sorteado com
`Random(20261015)`. Rótulo **provisório do coordenador (agente)**, feito em folhas **limpas**
(`rotular_*.jpg`, sem detecção desenhada), **antes de ver as detecções**. Três lados
indecisos ficaram fora da conta (C20 direita, N32 direita, N38 direita). Rótulo em
`data/saida/maos/m1/rotulo_agente_validacao.json`.

| detector | quadro certo | mão esquerda | mão direita | falsas |
| --- | --- | --- | --- | --- |
| MediaPipe (censo M0) | 72/90 | 70/86 | 75/79 | 1 |
| Wholebody 0,5 | 81/90 | 79/86 | 77/79 | 3 |
| Wholebody 0,4 | 84/90 | 84/86 | 78/79 | 3 |
| Wholebody 0,4 + MediaPipe complementando (**ADOTADO**) | 86/90 | 86/86 | 78/79 | 3 |

Só nos 60 novos: MediaPipe 47/60; Wholebody 0,4, 58/60; combinação, 59/60.

Ressalva: o limiar 0,4 foi escolhido nesses mesmos 90 quadros. Com 0,5, a combinação dá
84/90.

**Por que o complemento:** no `sky guitar` (o maior canal, 417 vídeos), a mão do braço fica
numa janela de close separada, sem corpo ligado. O Wholebody não a acha (C28, N53); o
MediaPipe acha.

**Erros que sobram (4):**
- C03: mão direita borrada, não achada.
- C04, C17, N09: close de uma mão só. O Wholebody devolve também uma mão "direita" que não
  existe (falsa). Nenhuma regra atual trata isso (3 de 90).

**Reavaliação offline e registro.** A combinação atual (`tab/maos_combinar.py`), recalculada
das detecções cruas em `detector_validacao.jsonl`, dá **86/90** (esquerda 86/86, direita
78/79, 3 falsas; erros C03, C04, C17, N09). O `detector_validacao.jsonl` gravado às 10:15 é
da versão **com a regra de honestidade** (ver abaixo), e dá 84/90. Por isso existe a
reavaliação `reavaliar_sem_honestidade.py`: ela recalcula as mãos com o código atual, sem
rodar os modelos.

Detector promovido, medido na GPU (`python -m tab.maos_detector`): duas execuções byte a byte
iguais; tempo 0,20 a 0,22 s por quadro, com o MediaPipe incluído (5 chamadas do MediaPipe por
quadro). Regressão: com a imagem nova, o censo do piloto segue 36/36 idêntico.

## Regra de honestidade: medida e REPROVADA

Regra testada: "esquerda e direita da mesma pessoa, com sobreposição ≥ 0,5, viram uma mão de
lado `incerto`".

Resultado gravado (versão com a regra, `detector_validacao.jsonl`): **84/90**; esquerda
82/86; direita 77/79; falsas 1; 4 quadros com `incerto`. Erros: C03, C04, C08, C17, N09, N25.

Efeito, por quadro:
- a regra não ganhou nenhum quadro. C04 e N09 trocaram a mão direita falsa por perder também
  a esquerda verdadeira, que virou `incerto`; continuam errados;
- perdeu 2: C08 e N25, que estavam certos e viraram erro (duas mãos reais, próximas);
- a sobreposição não separa os casos: erros com sobreposição de 0,96 a 1,00; acertos perdidos
  de 0,90 a 1,00. O C17 (sobreposição 0,28) não é tocado.

Resultado: **84/90 contra 86/90**. Além disso, a regra deixou de afirmar 4 mãos esquerdas
(82/86) e 1 direita (77/79). **Removida.** Não ajustar nos mesmos 90 quadros.

## Problemas da rtmlib (não repetir)

1. **Pose sem detector**: com o detector de pessoa vazio, a `pose_model` roda no quadro
   inteiro e inventa pessoa ou mão (`rtmpose.py`). O detector e a pose são chamados em
   **separado** (`tab/maos_detector.py`, `_pessoas_wb`).
2. **OpenCV duplicado**: `rtmlib` com dependências instala `opencv-python` e
   `opencv-contrib-python` sobre o cv2 da base. Instalar com `--no-deps` (o `Dockerfile.maos`
   faz isso; só o `tqdm` é usado).
3. **CUDA caindo em CPU**: `onnxruntime-gpu` cai em CPU sem erro quando o `LD_LIBRARY_PATH` não
   aponta para as bibliotecas CUDA do torch. A imagem fixa o ENV; `_travar_cuda` aborta se a
   sessão não estiver em CUDA (provado: sem a GPU no container, levanta `RuntimeError`).
4. **Cor**: a rtmlib não converte cor. A pose usa média e desvio ImageNet em RGB e recebe
   BGR. Medido: a diferença é pequena (ver rodada 2). Mantido BGR.

## Não repetir

- **Detector vazio com a pose rodando**: inventa pessoa e mão no quadro inteiro.
- **Regra de honestidade por sobreposição** (`incerto` com sobreposição ≥ 0,5): reprovada.
- **Misturar CPU e GPU** nos mesmos números.
- **`onnxruntime-gpu` sem checar o provider**: cai em CPU calado.
- **Instalar a rtmlib com dependências** na imagem de produto: quebra o cv2 da base.
- **Blocos 3×3 na fusão por score**: já medidos no M0 (pioram); não voltar a eles.
- **Limiar 0,5 com o Wholebody sozinho** nos 90 quadros: 81/90, pior que 0,4.

## Comandos

Produto (dentro de `chorinho-maos:dev`, GPU; é o padrão):

```bash
podman build -t chorinho-maos:dev -f Dockerfile.maos .
python -m tab.maos_detector --conjunto data/saida/maos/m1/validacao_conjunto.json \
    --censo data/saida/censo/censo_cache.jsonl \
    --saida data/saida/maos/m1/detector_validacao.jsonl \
    --rotulo data/saida/maos/m1/rotulo_agente_validacao.json
```

Reavaliação offline, sem GPU, das detecções cruas com o `combinar` atual:

```bash
python data/saida/maos/m1/reavaliar_sem_honestidade.py
```

Rascunhos de medição (fora do pacote `tab/`; rodaram em `chorinho-maos-rtm:dev` na CPU e
`chorinho-maos-rtm-gpu:dev` na GPU, imagens de sondagem anteriores ao `Dockerfile.maos`):

```bash
python data/saida/maos/m1/sonda_rtm.py       # rodada 1 (CPU)
python data/saida/maos/m1/pontas.py          # rodada 2
python data/saida/maos/m1/tempo_gpu.py       # rodada 3
python data/saida/maos/m1/validacao.py       # rodada 4 (CPU; monta conjunto e folhas de rótulo, não o rótulo)
```

## Pendências

1. **Gabarito de pontas e de dedo** (M2, dono). Sem ele, a escolha entre as pontas do
   Wholebody e do MediaPipe é só visual, provisória (agente).
2. **Falsa mão direita em close de uma mão só** (3 de 90: C04, C17, N09). Sem regra.
3. **Rótulo da validação é do agente** (provisório). Confirmação do dono nos 90 quadros, ou
   um conjunto novo com rótulo do dono, é a medida que falta.
4. **Limiar 0,4 escolhido nos mesmos 90 quadros.** Número fora do ajuste: **a medir**.
5. **Tempo em vídeo inteiro e no acervo** (2.798 vídeos, 12 quadros cada): **a medir**.
6. **Dispositivo da validação**: a validação rodou na GPU. O comando tinha
   `--device nvidia.com/gpu=all`, e a trava (`_travar_cuda`) aborta se a sessão não estiver em
   CUDA, então não há como ter rodado em CPU.

## Artefatos

- Decisão: `docs/decisoes/1002-detector-de-maos.md`.
- Código do produto: `tab/maos_detector.py` (carga, GPU, execução), `tab/maos_combinar.py`
  (regras puras), `Dockerfile.maos` (imagem; ENV de CUDA).
- Validação: `data/saida/maos/m1/validacao_conjunto.json`, `validacao_deteccoes.json`,
  `detector_validacao.jsonl` (versão com a regra), `detector_validacao_run2.jsonl` (idêntico),
  `rotulo_agente_validacao.json`, `regressao_piloto.jsonl`.
- Sondagem e medições: `sonda_rtm.json`, `sonda_rtm_exec1.json`, `tempo_gpu.json`,
  `pontas.json`, `pontas_{1..4}.jpg`, `folha_rtm_{1..4}.jpg`, `deteccoes_{1..9}.jpg`,
  `rotular_{1..9}.jpg`.
- Rascunhos: `data/saida/maos/m1/{sonda_rtm,pontas,tempo_gpu,validacao,reavaliar_sem_honestidade}.py`.

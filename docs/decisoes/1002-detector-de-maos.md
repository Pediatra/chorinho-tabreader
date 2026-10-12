# 1002 — Detector de mãos: RTMPose Wholebody na GPU, com MediaPipe como complemento

Status: **decidida pelo dono em 2026-10-12** ("agree" à recomendação do agente). A medição
que sustenta a decisão está na [rodada 1002](../rodadas/1002-escolha-do-detector.md); os
números da validação são **provisórios (agente)**, porque o rótulo é do agente.

## Contexto

O censo do M0 ([decisão 1001](1001-imagem-derivada-maos.md), [rodada 1001](../rodadas/1001-censo-de-maos.md))
usou o MediaPipe HandLandmarker sozinho. Ele acha a mão, mas perde mãos e deforma a
posição dos dedos. No piloto, acertou 32 de 36 quadros (provisório, agente). Na validação
fora do ajuste (90 quadros), acertou 72 de 90. O caso difícil é a mão do braço vista de
costas, em preto e branco, borrada ou em close.

O M2 precisa das pontas dos dedos para ligar cada dedo à nota tocada. Por isso o detector
precisa dar pontos da mão, com o lado (esquerda ou direita) e com um critério de existência.

## Opções

1. **MediaPipe sozinho** (o censo do M0, quadro inteiro e blocos 2×2, confiança 0,3).
   Validação fora do ajuste: 72/90. Pontas erradas em casos vistos (`kenneth`: polegar no
   dedo médio; `cifra club`: mão deformada).
2. **Hand** (RTMDet-nano de mão + RTMPose-m hand, 21 pontos, **sem lado**). Perdeu mãos do
   braço na sondagem (sobretudo a do braço). Não foi levado aos 90 quadros.
3. **Wholebody sozinho** (RTMW-DW-X-L, lado pelo corpo, limiar 0,4). Validação fora do
   ajuste: 84/90. No `sky guitar`, não acha a mão do braço num close sem corpo ligado
   (C28, N53).
4. **Wholebody + MediaPipe como complemento**: a mão do Wholebody é a base; o MediaPipe
   entra só com mãos fora da tablatura e com sobreposição menor que 0,3 com toda mão aceita.
   Validação fora do ajuste: 86/90 (provisório, agente).

## Decisão

Opção 4, decidida pelo dono em 2026-10-12:

- base: RTMPose Wholebody (YOLOX-m para a pessoa, RTMW-DW-X-L para a pose), **na GPU**;
- limiar da mão do Wholebody: média dos 21 scores **acima de 0,4** (comparação estrita);
- complemento: mão do MediaPipe fora da tablatura e com sobreposição **menor que 0,3** com
  toda mão aceita do Wholebody;
- o código está em `tab/maos_detector.py` (carga e execução) e `tab/maos_combinar.py`
  (regras puras, com teste no gate).

## Consequências

- **GPU obrigatória no produto.** O `tab/maos_detector.py` (`_travar_cuda`) aborta se a
  sessão do YOLOX ou da pose não tiver `CUDAExecutionProvider` em primeiro. O
  `onnxruntime-gpu` cai em CPU sem avisar quando falta o `LD_LIBRARY_PATH` das bibliotecas
  CUDA do torch; a imagem `chorinho-maos:dev` fixa esse ENV (`Dockerfile.maos`). Medido:
  sem a GPU, a trava levanta `RuntimeError`.
- **Números de CPU e de GPU não se misturam.** Os pontos diferem (média 0,5 px; alguns até
  14 a 21 px com score acima de 0,3). Os números desta decisão são da GPU; a sondagem em
  CPU da rodada 1002 serve só para comparar candidatos.
- **O limiar 0,4 foi escolhido nos mesmos 90 quadros** da validação. Com 0,5, a combinação
  deu 84/90 nesses quadros. O 86/90 não é número fora do ajuste. O número fora do ajuste
  ainda não existe: **a medir** (quadros novos, ou a conferência do dono).
- **Rótulo da validação é do agente** (provisório). Foi feito em folhas limpas, antes de
  ver as detecções; 3 lados indecisos ficaram fora da conta.
- **Regra de honestidade removida.** A regra que fundia esquerda e direita da mesma pessoa
  em `incerto` foi medida e reprovada (rodada 1002). Ela não ganhou nenhum quadro (C04 e N09
  trocaram a mão direita falsa por perder também a esquerda verdadeira, que virou `incerto`)
  e perdeu 2 (C08, N25): 84/90 contra 86/90. Não voltar a ela sem dado novo.
- **Erros que sobram (4 de 90):** C03 (mão direita borrada, não achada); C04, C17 e N09
  (close de uma mão só, em que o Wholebody devolve também uma mão direita que não existe).
  Nenhuma regra atual trata a falsa direita em close.
- **YuNet** (rosto) continua na imagem, por causa do M0, mas **não entra** no detector do
  M1.
- **Tempo** com a GPU: 0,20 a 0,22 s por quadro, com o MediaPipe incluído. O tempo em vídeo
  inteiro e para o acervo de 2.798 vídeos é **a medir**.
- **Os scripts de rascunho** (`data/saida/maos/m1/*.py`) rodaram em imagens de sondagem
  (`chorinho-maos-rtm:dev` e `chorinho-maos-rtm-gpu:dev`). O produto é `chorinho-maos:dev`,
  e a regressão do piloto (36/36 idêntico) foi refeita com ela.

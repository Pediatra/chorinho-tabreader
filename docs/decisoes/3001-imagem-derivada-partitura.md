# 3001 — Imagem derivada para a trilha de partitura (OMR)

Status: **provisório (agente)**. Tomada pelo agente da trilha de partitura em 2026-10-13, para
viabilizar o teste de fumaça das três candidatas. Ainda não foi confirmada pelo dono.

## Contexto

A trilha de partitura lê a pauta de cinco linhas dos quadros de vídeo e transforma em
formato estruturado. A comparação vai ser entre três bibliotecas prontas:

- **homr** (PyPI `homr`, github.com/liebharc/homr): foto ou PDF de partitura para MusicXML;
- **oemer** (PyPI `oemer`, github.com/BreezeWhite/oemer): foto de partitura para MusicXML;
- **Audiveris** (github.com/Audiveris/audiveris): modo batch que exporta MusicXML.

As três trazem pilhas incompatíveis com a imagem compartilhada `chorinho:dev`, que é a base
da trilha tablatura:

- `homr` 0.7.0 exige `opencv-python-headless<5.0.0.0`, e a base tem `5.0.0.93`. Instalar
  pelo pip trocaria o cv2 da base;
- `oemer` 0.1.8 pede `onnxruntime-gpu`, que não convive com o onnxruntime de CPU;
- `homr` puxa `onnxruntime` 1.31.0, e com essa versão o `oemer` não carrega seu modelo
  (ver "Medições" abaixo).

A versão do `homr` é 0.7.0, publicada em 2026-06-26, e não a 0.6.2 que o pedido citava. O
`homr` 0.6.2 continua no PyPI, mas o pedido pedia a versão mais recente disponível.

## Opções

1. Pôr as três bibliotecas no `requirements.txt` compartilhado e reconstruir `chorinho:dev`.
   **Descartada**: mudaria o que a trilha tablatura já faz (cv2 e onnxruntime).
2. Imagem derivada `chorinho-partitura:dev`, com `FROM chorinho:dev`, no `Dockerfile.partitura`,
   com as bibliotecas OMR num venv separado em `/opt/omr`.
3. Instalar no venv da base (`/opt/venv`). **Descartada**: quebraria `cv2` e `numpy` da base.

## Decisão

Opção 2. Detalhes:

- **Venv separado `/opt/omr` em Python 3.12**, criado com `uv` 0.13.0 (num venv próprio em
  `/opt/uvtool`, que é removido no fim do build). O README do homr pede Python 3.11 ou 3.12.
  O venv `/opt/venv` da base não é tocado.
- **homr 0.7.0**, instalado com dependências normais dentro de `/opt/omr`. Os modelos são
  baixados no build com `homr --init`.
- **oemer 0.1.8**, instalado com `--no-deps`, e as dependências restantes (matplotlib,
  pillow, scipy, scikit-learn, typing-extensions) instaladas à mão, sem `onnxruntime-gpu`.
  Os checkpoints são baixados no build reproduzindo a lógica do `main()` de `oemer/ete.py`,
  porque a lib só os baixa na primeira execução.
- **onnxruntime 1.24.1 (CPU) fixado** em `/opt/omr`. É o piso que o homr aceita (>=1.24.1), e
  é a versão com a qual o modelo do oemer carrega.
- **Audiveris 5.10.2** pelo `.deb` oficial Ubuntu 22.04, com sha256 verificado
  (`9470d15e79dd4fe45f817b8545ba9f8e57ddaebff3b3a1031f21218647602068`). O `.deb` traz JRE
  embutido em `/opt/audiveris/lib/runtime`. Não usamos `apt install` do `.deb`: o `postinst`
  registra menu e MIME de desktop e sai com erro 3 no container (medido). Em vez disso,
  instalamos as bibliotecas do campo `Depends` pelo apt e extraímos com `dpkg-deb -x`.
  Launcher em `/usr/local/bin/audiveris`.
- **CPU, não GPU**: a GPU é compartilhada por quatro trilhas. Nenhum provider CUDA é usado.

## Modelos baixados no build

sha256 completo na saída do build (`data/saida/partitura/p1/fumaca/build4.log`). Principais:

- homr, segmentação: `segnet_308-3296ccd40960f90ca6ab9c035cca945675d30a0f.onnx`
  = `6ed36640db4ef5d223098b6d5efe4eda97c66b24a2c72faab8a018c749003a8d`;
- homr, transformer: `decoder_pytorch_model_396-f6feedb42ff90087d898b0941a55d040fa6b2903.onnx`
  = `3e10fd5ae52d0b86792721922fcd954c283a7ed365de7446425bdabe38f3e57d`;
  `encoder_pytorch_model_396-f6feedb42ff90087d898b0941a55d040fa6b2903.onnx`
  = `4c16df852b3789f2676b0d49f0545dab0740e4005f7b472c5252add642f5d5eb`;
- homr, OCR de título (rapidocr): `PP-OCRv6_det_small.onnx`
  = `090f04abcd9d9a7498bc4ebf677e4cb9bdce1fe4197ddb7e529f1ef44e1ff94f`;
  `PP-OCRv6_rec_small.onnx` = `6f327246b50388f3c176ae304bd95767ea6dc0c9ae92153ef8cbe210b3c14884`;
- oemer, `checkpoints/unet_big/model.onnx`
  = `37512e858731096439746f60b377c049f07055b4a23ec6eb9a178ce92cfba174`;
  `checkpoints/seg_net/model.onnx` = `ed2e1a86ea75712ee6cdc740e96f7a36753543cf9bb980227c071c9256d9d82e`.

## Medições (teste de fumaça, recorte `pauta_b31787.png`, 960x140)

Ver `data/saida/partitura/p1/fumaca/`. Tempo e memória medidos com `/usr/bin/time -v` dentro
do container.

- **homr 0.7.0**: exit 0, 7,6 s, RSS máximo 883 MB. Gera `homr/pauta_b31787.musicxml`.
- **oemer 0.1.8**: exit 1, 6 min 54 s, RSS máximo 5,6 GB. Erro:
  `ValueError: max() iterable argument is empty` em `staffline_extraction.py` (`align_staffs`),
  depois da segmentação e da extração de camadas. Ou seja, o modelo carrega e roda, mas não
  acha linhas de pauta. Tentativas adicionais, todas com o mesmo erro:
  - com onnxruntime 1.31.0 (o que o homr puxa): falha antes, em
    `ConvTranspose ... pads must not contain negative values`;
  - com `-d` (sem deskew), no recorte: mesmo erro, 7 min 23 s;
  - com o quadro inteiro `b31787.jpg` (960x540): `ZeroDivisionError`, 6 min 58 s, RSS 5,6 GB.
    Diagnósticos em `oemer/diagnostico/`.
- **Audiveris 5.10.2**, no recorte original: exit 1 em 2,5 s. O passo SCALE mediu interlinha
  de 10 px e marcou a folha como inválida ("resolução baixa, try 300 DPI"). Sem MusicXML.
  Log em `audiveris/pauta_b31787-*.log`.
- **Audiveris 5.10.2, variante ampliada 3x** (cúbica, `audiveris/x3/pauta_b31787_x3.png`,
  2880x420): exit 0, 10,1 s, RSS 447 MB. Gera `audiveris/x3/pauta_b31787_x3.mxl`. A
  interlinha medida fica em 28 px. Esta é uma variante de pré-processamento, rotulada, e não
  a medição principal.

## Consequências

- Imagem `chorinho-partitura:dev` (ID `38b2b184754d`) com **7,94 GB**, contra 6,54 GB da base
  (+1,4 GB). É construída a partir de `chorinho:dev`, que precisa existir antes.
- Versões finais: homr 0.7.0, oemer 0.1.8, onnxruntime 1.24.1, cv2 4.14.0 (dentro de
  `/opt/omr`), numpy 2.5.4 (dentro de `/opt/omr`).
- Base intocada: `/opt/venv` tem torch 2.14.1+cu130, cv2 5.0.0, numpy 2.5.2 antes e depois.
- Audiveris exige **resolução**: no recorte original (interlinha 10 px) não exporta nada. Qualquer
  trilha que use Audiveris precisa de pré-processamento de escala, e isso é entrada do modelo
  (ver `AGENTS.md`, regra 9).
- oemer não produziu saída em nenhuma das três tentativas. A causa não foi investigada além
  do erro; ele fica registrado como falha a reexaminar, não como descarte definitivo.
- A medição de qualidade (se a leitura está certa) não faz parte deste teste de fumaça.

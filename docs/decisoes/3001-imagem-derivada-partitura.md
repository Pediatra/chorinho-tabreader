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

## SMT (Sheet Music Transformer)

Teste sem treino dos modelos públicos do SMT (github.com/antoniorv6/SMT e Hugging Face
PRAIG/antoniorv6). Imagem `chorinho-partitura:smt` (tag separada; `chorinho-partitura:dev`
não foi tocada). Código: `tab/partitura_smt.py`, `tests/test_partitura_smt.py`.

**Imagem**: 9,87 GB, contra 7,94 GB da `chorinho-partitura:dev` (+1,93 GB). Venv próprio em
`/opt/smt` (Python 3.11.17, via uv), torch **2.6.0+cpu** (índice do PyTorch, sem CUDA),
torchvision 0.21.0. Os pacotes seguem o `uv.lock` do repositório SMT:
transformers **4.49.0**, numpy 2.2.3, opencv-python-headless 4.11.0.86, pillow 11.1.0,
scikit-image 0.25.2, tokenizers 0.21.0, huggingface-hub 0.29.1, safetensors 0.5.2,
loguru 0.7.3, pytest 8.3.4. Mais **music21 10.5.0** (conversão kern para MusicXML).

**Código do SMT, dois commits.** Os checkpoints de antoniorv6 (enviados em 2024-09-07)
carregam sem camada faltando só com o código de **d25acd4** (2024-09-03, o último commit antes
de a decodificação mudar em 2025-02). Com o `master` de 2025, o decoder sai com pesos
aleatórios: o transformers avisa "newly initialized" para todas as camadas do decoder
(`cross_attn`, `ffn`, `norm_layers` em vez de `cross_attention`, `ffNet`). Os checkpoints
de PRAIG carregam sem aviso só com o `master`. Por isso a imagem tem os dois:

| uso | commit | pasta na imagem |
| --- | --- | --- |
| antoniorv6 (2 modelos) | `d25acd4` (2024-09-03) | `/opt/smt-src-2024` |
| PRAIG (2 modelos) | `20d8240` (master, 2026-09-27) | `/opt/smt-src` |

O `predict` e a junção dos tokens (`<b>`, `<s>`, `<t>`) são os mesmos nos dois commits.

**Pesos** (revisão de commit do HF fixada, sha256 do `model.safetensors` e do `config.json`):

| modelo | revisão HF | sha256 model.safetensors | sha256 config.json | licença (metadado HF) |
| --- | --- | --- | --- | --- |
| antoniorv6/smt-grandstaff | `2eb5a45c` | `495b5831c5a92fc75b6bf607cbe65d8a8432508177e0f76055da750d132c7be0` | `de430bd1c38063fd002b93eab623fc467527d5f1167bb4ded067637dbe32d961` | MIT |
| antoniorv6/smt-camera-grandstaff | `9c135563` | `93be49ca62c1d270579648e0c6d596cd239a7f0461c796f647ec0597ac085448` | `de430bd1c38063fd002b93eab623fc467527d5f1167bb4ded067637dbe32d961` | MIT |
| PRAIG/smt-grandstaff | `fd3d512a` | `9d29acc558bcbb8c851a80ead7435fc79c35578c845fd89bc97d86f3d49619c8` | `f01907a88fdd1cbdbf82a0f698b5ceec0e1aa233f9cd6d88b8e284f60e351400` | **não declarada** |
| PRAIG/smt-fp-grandstaff | `6f8d5c09` | `3b72668235c0519e2258739c736dd97d9e0d4226dbd628eec7891085a3f4c7e2` | `5327ddb41605a81d95a974a54d3f8c0f748d30f1b10cfba3afbd292ebc7b36da` | MIT |

Commits do HF completos: `2eb5a45c29d63bdf063cd0427175f57675e7da9e`,
`9c1355631fbddc297d3d10fe4e6e5d3b5d3126b7`, `fd3d512a64aab51ee4048435d44c0455d6cc0abd`,
`6f8d5c093d218a71117ef51492efc2952adcc217`.

**Não baixados** (3 de 7):

- `antoniorv6/smt-string-quartets` (revisão `94e23854`): o repositório só tem o README; não
  há `model.safetensors` (404) nem `config.json`.
- `PRAIG/smt-fp-polish-scores` e `PRAIG/smt-fp-mozarteum`: **gated** (401 sem login). O build
  não usa token. Falta o dono aceitar o acesso no Hugging Face e fornecer um token para
  baixar.

**Pré-processamento**: replica `data.py` do repositório (o trecho de uso do `README` não
redimensiona a imagem). Sistema: altura `ceil(max(h, 256) * reduce_ratio)`, largura
`ceil(min(w, 3056) * reduce_ratio)`. Página: `ceil(dim * reduce_ratio)`. `reduce_ratio` vem
da configuração do treino: 1.0 para `GrandStaff` e `FP-GrandStaff`, 0.85 para a câmera. O
`PRAIG/smt-grandstaff` não publica configuração: usou-se 1.0, e isso é premissa.

**Recorte de página (fp)**: a entrada é o recorte de um sistema, no papel de página. A saída
bekern não tem o cabeçalho `**bekern` (o treino tirou as quatro primeiras linhas de tokens),
então o runner acrescenta `**kern` por spine para o music21, com o número de spines lido da
primeira linha de tokens. `saida.krn` guarda o texto cru, sem o cabeçalho.

**Tempo**: um recorte roda em processo próprio (carrega o modelo, prediz e converte). O limite
é 600 s por recorte. Acima disso o modelo para e o relatório diz o tempo.

**Cabeçalho ekern**: a saída dos modelos de sistema sai com `**ekern_1.0`, mas sem os `·`
(o treino os removeu). O music21 não lê esse rótulo (0 notas). O runner troca só o
cabeçalho por `**kern` antes da conversão e grava `cabecalho_ekern_trocado` em
`saida_spines.json`. `saida.krn` guarda o texto cru.

**Estado da rodada (R01–R12, CPU, condição `crop`)**. Sem avaliação de qualidade, só o
que saiu:

| modelo | com MusicXML com notas | falhas | parou por timeout de 600 s |
| --- | ---: | --- | --- |
| antoniorv6/smt-grandstaff | 5 de 9 rodados (R02, R03, R04, R06, R07) | kern malformado: R01, R05, R08 | R09; R10–R12 não rodados |
| antoniorv6/smt-camera-grandstaff | 0 de 2 | kern malformado: R01, R02 | R03 |
| PRAIG/smt-grandstaff | 0 de 12 | kern malformado: 11; R08 erro de tensor | nenhum |
| PRAIG/smt-fp-grandstaff | 0 de 1 rodado | — | R01 (sem saída) |

O R08 tem 288 px de altura, acima do `maxh` = 256 da configuração. A entrada tem
essa altura, e o código de 2025 falha ao posicionar a atenção.

Quando music21 lê o kern e não acha nota, ele devolve um `Score` vazio e não erro. O
runner trata isso como falha (`music21 não leu nenhuma nota`). Sem essa checagem, 5
recortes do antoniorv6 pareceriam certos com MusicXML sem nenhuma nota.

Sanidade do pipeline (uma linha do conjunto de teste GrandStaff, fora da rodada): o
modelo antoniorv6/smt-grandstaff reproduz o gabarito quase igual, a menos dos `·`. Com
cabeçalho `**kern`, o music21 lê a saída: 2 partes, 47 notas.

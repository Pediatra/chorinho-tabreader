# 2019 — Transcritor livre de violão do Riley, medido nos gabaritos de tablatura

**Trilha**: áudio. **Pré-registro**: 2026-10-21, antes de transcrever qualquer vídeo da
amostra. **Antecedente**: a rodada [2018](2018-transcritor-livre-basic-pitch.md) (o Basic
Pitch reprovou). **Decisão de referência**: [2005](../decisoes/2005-validacao-cruzada-tela-som-maos.md).

## Pergunta

O transcritor de violão de Riley et al., que só ouve o áudio, acerta as notas que o dono
conferiu na tela, com os mesmos critérios em que o Basic Pitch reprovou?

## Por que este modelo, e o que mudou desde a 2018

- O dono exige código aberto e uso comercial. O MuScriptor (CC BY-NC) ficou fora. O modelo
  do Riley tem pesos MIT no Hugging Face (`xavriley/midi-transcription-models`), e o dono
  aprovou o download em 2026-10-21. A procedência está em `artefatos/riley_guitar.md`.
- É o CRNN de alta resolução de Kong et al., adaptado ao violão (Riley et al., ICASSP 2024 e
  ISMIR 2024). Os autores publicam ~89 % de F1 de início de nota no GuitarSet, sem treinar
  nele. Esse número não foi medido aqui.
- **Lição da 2018**: o corte escolhido no vídeo de desenvolvimento piorou a prova. Desta vez
  **nada se ajusta**: os limiares são os padrões do pacote do autor, e não há corte.

## O transcritor (congelado aqui)

- `tab.audio_transcrever_riley`, imagem `chorinho-som:dev` (torch 2.5.1 CPU e o fork
  `piano_transcription_inference` no commit `7568dc7f`).
- Pesos lidos com `torch.load(weights_only=True)`. Os globais do pickle foram conferidos com
  `pickletools` antes de carregar: só tensores e arrays numpy.
- Áudio: o FLAC do cache (22.050 Hz) reamostrado para 16 kHz com `soxr_hq`, em segmentos de
  10 s com metade de sobreposição, como no pacote do autor.
- Limiares padrão do autor: onset 0,3, offset 0,3, frame 0,1.
- Tessitura do violão (MIDI 40 a 88), como na 2018.
- **Principal: `guitar-fl.pth`**, treinado em violão solo de aço, jazz e fingerstyle, que é o
  grosso do acervo.
- **Secundário: `guitar-gaps.pth`**, treinado em violão clássico de nylon. É medido e
  relatado, mas **não decide nada nesta rodada** (ver abaixo).
- Determinismo: o vídeo de referência roda duas vezes com o principal; o JSON tem de sair
  igual.

## Amostra, comparação e critérios

São os da 2018, sem mudança:
- **Folha de respostas**: MIDI = corda solta + casa + capo, com a afinação padrão; o capo vem
  de `data/saida/maos/capo_por_video.json`.
- **Prova** (C1, C2): os 7 vídeos com gabarito de tablatura (50 telas, 2.196 notas).
- **Acorde cheio** (C3): as 28 colunas de 5 ou 6 cordas, 22 de `acordes_2018` e 6 das telas
  de prova.
- **Instante** (C4): os 31 pontos de escuta dos vídeos de prova.
- **Referência**: o *retrato brasileiro* v2 é relatado à parte e não entra nos critérios.
  Nesta rodada ele não serve para ajustar nada.
- **Comparação**: `tab.audio_som_medir` com `--amplitude-minima 0`, ou seja, todas as notas,
  com pareamento monotônico por exibição e controle de +1 semitom.

| # | o quê | passa se |
| --- | --- | --- |
| C1 | altura, prova | revocação somada **≥ 0,80**, e ≥ 0,70 em pelo menos 5 dos 7 vídeos |
| C2 | notas a mais, prova | precisão somada **≥ 0,70** |
| C3 | acorde cheio | mediana da fração achada **≥ 4/6** |
| C4 | instante | **≥ 28 de 31** pontos com início a ≤ 100 ms |
| V | validade | revocação do controle (+1 semitom) **≤ 0,25** |

**A prova já foi vista.** Ela mediu o Basic Pitch na 2018. Nenhum parâmetro do modelo do
Riley foi escolhido nela, e os critérios são os mesmos. Para não escolher no teste:
- só o `guitar-fl` decide;
- se ele reprovar e o `guitar-gaps` passar, o `guitar-gaps` **não** é adotado direto: ele
  vai para uma rodada de confirmação em gabarito ainda não usado;
- uma faixa de velocidade (confiança) escolhida aqui também só vale depois de confirmada
  num gabarito novo.

## O que fazer em cada resultado

- **O `guitar-fl` passa C1, C2 e V**: ele vira a fonte "som" da triangulação.
  - O formato `chorinho/som@1` vira decisão própria.
  - Seguem a rodada do capo e da afinação pelo som e o cruzamento tela × som.
  - **C3 reprova**: acorde de 5 ou 6 cordas fica "sem dado" no cruzamento.
  - **C4 reprova**: o instante continua vindo do alinhador.
- **C1 ou C2 reprova**: medem-se revocação e precisão por faixa de velocidade, só como
  descrição.
  - Se houver faixa com precisão ≥ 0,90 e revocação ≥ 0,50, ela vai para uma rodada de
    confirmação.
  - Se não houver, a trilha volta à lista do dono (relatório do Gemini): os modelos que dão
    corda e casa, o Guitar-Transcription e o Noise2Fret.
- **Vídeo com revocação < 0,50**: é olhado antes de concluir (afinação, capo, outro
  instrumento). O critério não muda.

## Também medido (não decide)

- O tempo de execução por vídeo, em CPU.
- A revocação por tamanho de coluna (1, 2, 3, 4+ notas), como na 2018.
- O `guitar-gaps` em tudo, com a mesma tabela.

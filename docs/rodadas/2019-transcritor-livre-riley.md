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

## Resultado (2026-10-21)

Código: commit `1bbca298`. Saídas em `data/saida/audio/r2019/` (`som_fl/`, `som_gaps/`,
`medida_fl.json`, `medida_gaps.json`, `analise.py`).
- **Determinismo**: o *retrato* rodou duas vezes com o `guitar-fl`, e o JSON saiu igual.
- **Tempo**: 1.636 s de CPU para 2.695 s de áudio nos 12 vídeos, 1,65 vez o tempo real.

### Critérios, `guitar-fl` (decide)

| # | medida | resultado | |
| --- | --- | --- | --- |
| C1 | revocação na prova | **1.766/2.196 = 0,804**; ≥ 0,70 em **6 de 7** vídeos | passa, no limite |
| C2 | precisão na prova | 1.766/2.014 = **0,877** | passa |
| C3 | acorde cheio, mediana | **0,667 = 4/6** em 28 colunas; 18 das 28 com ≥ 4/6 | passa, no limite |
| C4 | escuta, ≤ 100 ms | **30 de 31** | passa |
| V | controle +1 semitom | 302/2.196 = **0,138** | método válido |

**O `guitar-fl` passa.** C1 e C3 passam no limite. O único ponto de escuta que falhou é o
`g30` (*room 335*), o mesmo das rodadas 2017 e 2018.

Por vídeo de prova (`guitar-fl`, todas as notas):

| vídeo | capo | revocação | precisão | controle |
| --- | --- | --- | --- | --- |
| kenneth *end of beginning* | 2 | 204/303 = 0,673 | 0,872 | 0,112 |
| pablo romé *greensleeves* | 0 | 102/106 = 0,962 | 0,903 | 0,151 |
| robert lunn *gymnopédie* | 0 | 285/392 = 0,727 | 0,752 | 0,115 |
| iwaki *la vie en rose* | 0 | 386/425 = 0,908 | 0,960 | 0,181 |
| guitar dell'arte *south american* | 0 | 206/269 = 0,766 | 0,949 | 0,056 |
| kimny *from this place* | 0 | 304/381 = 0,798 | 0,886 | 0,152 |
| shin izumi *room 335* | 0 | 279/320 = 0,872 | 0,856 | 0,178 |
| *retrato brasileiro* (referência) | 0 | 458/491 = 0,933 | 0,923 | 0,200 |

Revocação por tamanho de coluna, na prova:

| coluna | Basic Pitch cru (2018) | `guitar-fl` | `guitar-gaps` |
| --- | --- | --- | --- |
| 1 nota | 0,846 | 494/578 = 0,855 | 0,853 |
| 2 notas | 0,795 | 512/644 = 0,795 | 0,781 |
| 3 notas | 0,709 | 373/501 = 0,745 | 0,752 |
| 4+ notas | 0,818 | 387/473 = 0,818 | 0,848 |

### `guitar-gaps` (só relata)

C1 1.774/2.196 = 0,808 (6 de 7 ≥ 0,70), C2 0,894, C3 mediana 0,633 (14 de 28 com ≥ 4/6),
C4 30/31, V 0,134. Ele é parecido no total, melhor na precisão e pior no acorde cheio.
Pelo pré-registro, ele não é adotado nesta rodada.

### Leitura

1. **A revocação é quase a mesma do Basic Pitch cru (0,804 contra 0,794); a diferença está
   na precisão (0,877 contra 0,591).** O Riley escreve muito menos notas que não estão na
   tela: na prova foram 2.014 notas no trecho tocado, contra 2.951 do Basic Pitch.
2. **O que falta é desigual.** O *end of beginning* (capo 2) fica em 0,673, e uma das duas
   colunas de 5–6 cordas dele sai com 0. A causa não foi olhada nesta rodada. Os 0 erros de
   semitom indicam que o capo não está errado.
3. **O *charagua* tem precisão 29/279 = 0,104** na única tela dele (39,0–53,5 s): o som tem 8
   vezes mais notas que a tela. Não entra em C2, mas precisa ser olhado antes do cruzamento.
   Hipóteses: outra parte tocando junto (o vídeo é a "2ª guitarra") ou rasgueado repetido que
   a tela escreve uma vez só.
4. **C1 e C3 passaram no limite**, então o "som" sozinho não basta para afirmar uma nota. É
   para isso que serve o cruzamento com a tela e as mãos (decisão 2005).

**Conclusão: o `guitar-fl` vira a fonte "som" da triangulação.**

**Próximos passos:**
- a decisão do formato `chorinho/som@1`;
- a rodada do capo e da afinação pelo som;
- o cruzamento tela × som;
- olhar o *charagua*.

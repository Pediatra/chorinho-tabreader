# Procedência: `artefatos/riley_guitar/` (transcritor de violão do Riley)

Baixado em 2026-10-21 pela trilha áudio, com aprovação do dono (rodada 2019). Os `.pth`
ficam fora do git.

| arquivo | tamanho | sha256 |
| --- | --- | --- |
| `guitar-fl.pth` | 98.916.957 B | `50d93dba89bdd3401849bc735614478e83d9f46d21fa3f71d8aca5acc0a52028` |
| `guitar-gaps.pth` | 99.178.877 B | `65483e7c0e340a90415b15b520687587698c8c728f5fa470a205f13ee45c6513` |

- **Fonte**: Hugging Face `xavriley/midi-transcription-models`, revisão
  `b7bec65a2b860aca72856b0feef58b5df407b777`, via
  `https://huggingface.co/xavriley/midi-transcription-models/resolve/<revisão>/<arquivo>`.
- **Licença**: MIT, segundo a etiqueta do model card. O código (`xavriley/hf_midi_transcription`
  e o fork `xavriley/piano_transcription_inference`, commit
  `7568dc7f78b625e40cf9776e2806d164006610e3`) declara MIT no README e nos metadados do pacote.
  Os repositórios não têm um arquivo `LICENSE`. O dono aceitou o MIT como declarado.
- **O que são**: o CRNN de alta resolução de Kong et al. (piano), adaptado ao violão por
  Riley, Edwards, Guo e Dixon (ICASSP 2024, arXiv:2402.15258; ISMIR 2024, arXiv:2408.08653).
  - `guitar-fl.pth`: treinado no conjunto de François Leduc (violão solo de jazz e
    fingerstyle; áudio do YouTube).
  - `guitar-gaps.pth`: treinado no GAPS (violão clássico de nylon).
- **Como se carrega**: `torch.load(weights_only=True)` em `tab.audio_transcrever_riley`. O
  arquivo é um pickle, e esse modo não executa código dele.
- **Uso no projeto**: só como fonte "som" de conferência (decisão 2005). Nada dele vira rótulo.

# 2001 — Áudio A0: extração em cache, sincronia áudio × vídeo e custo

Data: 2026-10-13. Trilha: tempo pelo áudio (contexto em `docs/guias/contexto-audio.md`).

## Pergunta

Dá para extrair o áudio de cada vídeo uma vez só, guardar sem perda e converter, sem
desvio, o instante do vídeo (PTS, o mesmo de `tab.leitor` e do `t_ini` do produto) no
índice da amostra de áudio? Quanto custa no acervo?

## O que foi feito

`tab/audio_extrair.py` (`python -m tab.audio_extrair VIDEO [--json SAIDA]`):

- ffmpeg extrai o primeiro stream de áudio para **FLAC mono, 16 bits, 22 050 Hz**
  (`-map 0:a:0 -vn -ac 1 -ar 22050 -sample_fmt s16`), com gravação atômica;
- cache em `/cache/audio/<sha1(chave)[:24]>.flac` + `.json` (meta), com a chave do
  censo (`relativo|tamanho|mtime`); reaproveitado só se chave, taxa e
  `versao_convencao` baterem;
- `indice_de(t_video, meta)` / `instante_de(indice, meta)` com
  `indice = round((t_video − t_amostra0) · taxa)`.

## A convenção de tempo (medida, não suposta)

`t_amostra0` = `best_effort_timestamp_time` do **primeiro frame de áudio decodificado**.
A primeira versão usava o `start_time` do stream, e o teste de sincronia a reprovou:

| codec (contêiner) | áudio deslocado | erro com `start_time` | erro com 1º frame |
| --- | --- | --- | --- |
| PCM (mov) | 0 s / 0,5 s / vídeo 0,3 s + áudio 0,5 s | +0,13 ms | +0,13 ms |
| AAC (mp4) | 0 s / 0,5 s | +0,13 / −0,64 ms | +0,13 / −0,64 ms |
| **Opus (mkv)** | 0 s / 0,5 s | **−6,87 / −5,87 ms** | +0,13 / +1,13 ms |

Teste: clique de 5 ms com envelope, centro em 1,0025 s do áudio, pico por argmax (viés
fixo de +0,13 ms do próprio clique). O Opus tem pré-salto (pre-skip) que o `start_time`
não desconta; **todo o acervo amostrado é Opus**, então a convenção errada teria posto
~7 ms de erro em tudo. O mkv guarda tempo em ms (daí o 1,13). Tolerância do teste: 3 ms.

## Números

**MVP** (`sky guitar/retrato brasileiro - tab & lesson.mp4`): vídeo h264, áudio Opus
48 kHz estéreo; `start_time` 0,0 nos dois; 1º pacote de áudio em −0,007 s, 1º frame em
0,0 s; deslocamento 0,0 ms. Áudio 678,973 s (14 971 355 amostras), vídeo 678,945 s.
Extração 2,7 s, FLAC 11,96 MB. Segunda chamada: cache hit. Extração repetida: amostras
idênticas (`array_equal`).

**20 vídeos** (`data/saida/audio/a0/lista20.txt`: 2 por canal em 10 canais, sorteio com
semente 2001, sem o MVP; 1,47 GB; um vídeo por vez):

- extraídos: **20 de 20**; vídeo h264 10, av1 8, vp9 2; áudio **Opus 48 kHz em 20 de 20**;
- deslocamento áudio − vídeo (`start_time`): **0 ms em 20 de 20** (a amostra não exercita
  deslocamento não nulo; o teste sintético cobre);
- `t_amostra0` pelo 1º frame em 20 de 20;
- duração do áudio extraído − duração do stream de áudio: −0,984 ms em 20 de 20
  (arredondamento da duração do ffprobe; nenhum buraco que mude a duração);
- fim do áudio − fim do vídeo: de −7 a +46 ms (mediana ~19 ms); nenhum acima de 500 ms;
- tempo por vídeo: mediana 1,73 s, máximo 5,39 s (364 MB); total 45,8 s; ~34 MB/s;
- FLAC: 82 MB por hora de áudio.

**Projeção (estimativa, tamanho médio da amostra × 2.998 vídeos ativos)**: ~2,2 h de
leitura do HD, sem paralelismo, e ~24 GB de cache. A amostra tem média de 78,8 MB por
vídeo; o acervo inteiro tem ~65 MB (AGENTS.md), então a projeção tende a ser alta.

## Limites

- A checagem de buraco só pega lacuna que mude a duração total; lacuna compensada no
  meio do stream não aparece aqui (aparecerá como deriva no A1/A3).
- Só o primeiro stream de áudio (`a:0`); vídeos com mais de um não foram vistos.
- Não foi feita sincronia contra verdade real (só sintética); o A1 mede o atraso
  marcador → som no MVP.

## Reprodução

```bash
python -m tab.audio_extrair "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4" --json data/saida/audio/a0/mvp_extracao.json
python data/saida/audio/a0/custo20.py
```

Gate: `ruff check .` `All checks passed!`; `ruff format --check .` 120 arquivos;
`pytest tests/ -m "not integration"` 664 passed, 4 deselected (14 testes novos em
`tests/test_audio_extrair.py`).

# 2002 — Áudio A1: atraso entre o marcador e o som, no MVP

Data: 2026-10-13. Vídeo: `sky guitar/retrato brasileiro - tab & lesson.mp4`. Produto:
`data/saida/conserto_v2/mvp.json` (762 notas, 752 com `t_ini`).

## Pergunta

Para cada coluna com `t_ini` do marcador, quando a nota soa? `Δ = t_som − t_marcador`:
há atraso fixo, deriva, e qual a dispersão?

## Método

- `tab/audio_onsets.py` (numpy): STFT de Hann, **N_FFT 2048, passo 256 a 22 050 Hz
  (11,6 ms)**, quadros centrados; fluxo espectral em `log1p(100·|X|)`; picos acima da
  mediana móvel (±0,1 s) + 0,05·máx. Também um fluxo restrito às alturas esperadas
  (afinação padrão + casa, 4 harmônicos, ±50 cents ou o bin mais próximo).
- `tab/audio_atraso.py`: 636 eventos de coluna `(tela, exibicao, passagem, coluna)`; para
  cada um, o ataque mais próximo numa janela de meia-distância até o evento vizinho
  (teto ±0,30 s). Passada 1 centrada em `t_ini`; passada 2 centrada em `t_ini + mediana`
  da passada 1 (104 ms).
- Transposição pela música: energia nas alturas esperadas transpostas por k = −3…+7;
  **k = 0** (sem capotraste), 1,77× o segundo melhor (k = +1).
- Figuras com matplotlib numa imagem derivada (`Dockerfile.audio`, decisão 2001).

## Viés do detector (sintético)

12 notas com ataque instantâneo (4 harmônicos, τ = 0,3 s): achadas 12 de 12, mas o pico
do fluxo cai **23 a 34 ms ANTES** do ataque (média −27,9 ms): a janela centrada de
93 ms já "vê" o ataque meio quadro antes. O teste de ±15 ms fica como `xfail` estrito com
o número. O fluxo nas alturas **não separa 1 semitom** em 330 Hz (razão 0,98: 10,8 Hz
por bin), também `xfail` com o número. Nenhum Δ abaixo foi corrigido pelo viés.

## Números (denominador: 636 eventos)

| método, passada | com ataque | mediana | p10 | p25 | p75 | p90 | MAD | na borda |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fluxo, 1 | 616 | 104 ms | −29 | 32 | 192 | 243 | 79 | 10 |
| alturas, 1 | 627 | 152 ms | 23 | 82 | 229 | 266 | 73 | 29 |
| **fluxo, 2** | **636** | **139 ms** | 60 | 90 | 214 | 268 | 60 | 1 |
| alturas, 2 | 635 | 170 ms | 47 | 93 | 242 | 290 | 75 | 4 |

**Não é deriva linear: é um DEGRAU em ~448 s.** Mediana de Δ (fluxo, passada 2) por
exibição, em ordem de tempo:

| trecho do vídeo | exibições | mediana de Δ por exibição |
| --- | --- | --- |
| 245–448 s | telas 1–4 (2 exibições cada), 5 e 6 (1ª) | 79 a 125 ms (10 exibições) |
| 449–668 s | telas 7–13, 5 e 6 (2ª), 7–9 (2ª) | 164 a 277 ms (12 exibições) |

A 2ª exibição das telas 5 e 6 (495–531 s) fica com o segundo grupo: o degrau é do
**tempo do vídeo**, não da página. A dispersão também cresce depois do degrau (p25–p75
de ~60 ms para ~100 ms).

## O que foi olhado

- `figuras/trecho1_tela1_exib1.png` (244,5–252,5 s): ataques nítidos no espectrograma;
  os ataques detectados (vermelho) caem sobre as bordas das notas, e o marcador
  (tracejado) vem ~100–130 ms **antes**, de forma regular. Muitas colunas têm **dois
  picos** a ~50–100 ms: baixo e melodia não são simultâneos (dedilhado "rolado"); o
  fluxo pega o primeiro e as alturas, muitas vezes, o segundo — daí a mediana das alturas
  ser maior.
- `figuras/trecho2_tela7_exib1.png` (448–456 s): mesmo padrão, com o marcador ~200 ms
  antes. A coluna 9 tem um pico muito forte em 453,7 s logo junto do marcador e o ataque
  de baixo em ~454,0 s: a escolha é ambígua ali.
- `histograma_delta.png`: bimodal (picos em ~100 e ~230 ms), coerente com o degrau.
  Cauda direita cortada pelo teto de 0,30 s da janela.
- `delta_no_tempo.png`: o degrau em ~448 s; a reta (23 ms/min) não descreve bem.
- Clipes com clique no marcador e no ataque: `data/saida/audio/a1/clipes/` (cliques
  conferidos por número, lag 0, erro ≤ 0,25 ms). **Escuta do dono (2026-10-13): o clique do
  ataque detectado cai junto com as notas.**

## Respostas (provisórias, um vídeo)

(a) O marcador vem **antes** do som, nunca depois, em quase todos os eventos (p10 = +60 ms).
(b) Não há deriva lenta: há um **degrau** de ~+110 ms perto de 448 s, de causa ainda não
medida (corte de edição? mudança de andamento da animação?). (c) Dentro de um trecho
estável, a dispersão (p25–p75) é de 60–100 ms, maior que 1 quadro: **o marcador deste
vídeo não serve como verdade de tempo do som a ±50 ms**, e a régua do A3 não pode usar
`t_marcador + atraso fixo` sem antes entender o degrau.

## Limites

Um vídeo; viés do detector de −28 ms (sintético) não descontado; acorde rolado faz a
coluna ter mais de um ataque; teto de 0,30 s corta a cauda depois do degrau.

## Reprodução

```bash
python -m tab.audio_atraso --produto data/saida/conserto_v2/mvp.json --video "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4" --saida data/saida/audio/a1/atraso_mvp.json
# imagem chorinho-audio:dev:
python -m tab.audio_figuras --atraso data/saida/audio/a1/atraso_mvp.json --video "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4" --pasta data/saida/audio/a1/figuras
```

Duas execuções: JSON idêntico (sha256 `4fcbaf92…`). Gate: `ruff` ok; pytest 679 passed,
2 xfailed, 4 deselected.

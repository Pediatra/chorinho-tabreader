# 2004 — Áudio A2: alinhador colunas → áudio (v1 e v2), no MVP com o marcador escondido

Data: 2026-10-13. Código: `tab/audio_alinhar.py`, `tab/audio_alinhar_avaliar.py`.
Saídas: `data/saida/audio/a2/`.

## Pergunta

Dado o áudio, a sequência de colunas de cada página e a janela em que a página está na
tela, dá para achar o instante em que cada coluna soa, **sem o marcador**, afirmando
pouco tempo falso?

## Método

- `esconder_marcador`: o alinhador recebe só telas, exibições (`t0`, `t1`) e colunas com
  (corda, casa); teste garante que `t_ini`, passagens e observadores não passam.
- Candidatos: picos do fluxo espectral (rodada 2002) em `[t0 − 0,5, t1 + 0,5]`.
- Perfil "nova energia" por candidato: STFT 4096/256, aumento de magnitude ([t, t+0,15]
  contra [t−0,10, t]) em cada MIDI 36–96; molde da coluna com harmônicos (1; 0,5; 0,33;
  0,25 em m, m+12, m+19, m+24); semelhança = cosseno.
- **v1**: programação dinâmica que casa TODAS as colunas da tela, em ordem, a candidatos
  crescentes (pular pico 0,05; coluna sem ataque 0,5; andamento 0,5·|log(dt/(dc·T))|,
  T pela mediana de intervalos entre picos fortes).
- **v2**: (1) **trecho livre**: maximiza Σ(cos − 0,35) com prefixo e sufixo de colunas
  fora do trecho de graça (`fora_do_trecho`), coluna interna sem ataque −0,2; (2) **T
  iterativo**: T0 = mediana dos intervalos entre todos os picos, depois re-estimado dos
  pares casados até variar < 2 %; (3) recusa da exibição com cos médio < 0,40 ou < 4
  colunas casadas. Constantes fixadas antes de medir; sem varredura na v2.
- Por que o trecho livre: medido na régua, cada exibição do MVP toca um **trecho contínuo**
  da página (repetições e casas de volta: tela 9 toca 1–8 na 1ª vez e 9–31 na 2ª; tela 5
  na 2ª vez começa na 9; tela 4 na 2ª vez para na 26).

## Régua (provisória)

`data/saida/audio/a1/atraso_mvp.json`: o ataque achado na janela do marcador (rodada
2002). Mede se o alinhador acha o **mesmo ataque** que a detecção guiada pelo marcador,
não a verdade; o dono conferiu por escuta que esses ataques caem nas notas. A régua não
cobre colunas que o marcador não acendeu.

## Números (Y = 636 colunas da régua)

| métrica | v1 | **v2** |
| --- | --- | --- |
| afirmadas | 583 | **629** |
| ≤ 50 ms do ataque da régua | 425 | **467** |
| ≤ 100 ms | 503 | **548** |
| ≤ 50 ms do ataque de fluxo OU de alturas (acorde rolado) | 530 | **591** (92,9 %) |
| **falsos** (afirmado e > 200 ms dos dois) | 10 (1,6 %) | **3 (0,47 %)** |
| recusadas, régua tocada | 53 | 7 |
| afirmadas sem par na régua | 12 | 16 |

- Trecho [a, b] da v2 igual ao da régua em **19 de 22** exibições; nas outras 3, uma
  coluna a mais na borda (cada uma vira uma afirmada sem par).
- `fora_do_trecho`: 46 colunas, **todas** ausentes da régua naquela exibição; nenhuma
  coluna tocada caiu fora do trecho.
- T convergiu em 22 de 22 exibições (2–3 rodadas), 0,633–0,662 s (régua: ~0,65 s).
- Confiança (cosseno × margem) separa pouco: ≤ 100 ms sobe de 87 % (todas) a 91 %
  (confiança ≥ 0,8); 0 falsos a partir de 0,8, 277 afirmadas.
- Determinismo: duas execuções com sha256 igual.
- **DTW** de passo padrão sobre o mesmo perfil, como linha de base: 14 de 636 a ≤ 100 ms
  sem recusa (619 falsos). Abandonado.

## O que foi olhado

- `figuras/v2_12_0_colunas23a26.png`: perto de 645,8–646,5 s o alinhador põe as colunas
  25 e 26 nos ataques que a régua dá às colunas 23 e 24, e recusa 23–24. Há notas rápidas
  (ornamento) por perto; não dá para decidir pelo espectrograma: vai para a folha do dono.
- `figuras/v2_13_0.png`: 11 colunas coincidem com a régua; 5 ficam 137–288 ms depois.

## Limites

Um vídeo, e a régua não é independente da detecção de ataques. "Afirmada sem par" pode
ser nota real que o marcador não acendeu, ou falso positivo: só a escuta decide. Uma
passagem por exibição (repetição dentro da exibição não tratada).

## Reprodução

```bash
python -m tab.audio_alinhar --produto data/saida/conserto_v2/mvp.json --video "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4" --saida data/saida/audio/a2/alinhado_v2_r1.json --metodo onsets
python -m tab.audio_alinhar_avaliar --alinhado data/saida/audio/a2/alinhado_v2_r1.json --regua data/saida/audio/a1/atraso_mvp.json
```

Gate: `ruff` ok; pytest 702 passed, 2 xfailed, 4 deselected.

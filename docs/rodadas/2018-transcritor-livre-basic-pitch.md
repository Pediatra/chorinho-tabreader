# 2018 — Transcritor livre (Basic Pitch) medido nos gabaritos de tablatura

**Trilha**: áudio. **Pré-registro**: 2026-10-21, antes de qualquer transcrição. **Decisão
de referência**: [2005](../decisoes/2005-validacao-cruzada-tela-som-maos.md) (triangulação,
Regra 1: o som não vê a tela).

## Pergunta

Um transcritor pronto, que **só ouve o áudio** e não recebe nada da tablatura, acerta as
notas que o dono conferiu na tela? Em que fração das notas, com quantas notas a mais, em
acorde cheio e com que instante?

Se ele acertar o bastante, ele vira a fonte "som" da triangulação (proposta
`chorinho/som@1`), e o alinhador atual (`chorinho/audio@1`) deixa de ser a única fonte de
som.

## O transcritor (congelado aqui)

- **Basic Pitch 0.4.0** (Spotify, Apache-2.0), modelo `nmp.tflite` que vem no pacote, na
  imagem `chorinho-som:dev` (`Dockerfile.som`, commit `aa05519d`), Python 3.10, só CPU.
- **Parâmetros padrão** de `basic_pitch.inference.predict`: `onset_threshold` 0,5,
  `frame_threshold` 0,3, `minimum_note_length` 127,70 ms, `melodia_trick` ligado,
  `multiple_pitch_bends` desligado, sem limite de frequência.
- **Nenhum parâmetro se ajusta no gabarito.** Única regra de domínio, fixada antes: nota
  fora da tessitura do violão (MIDI < 40 ou > 88; E2 a E6, que cobre capo 7 + casa 17)
  sai como "fora do violão", contada à parte, e não entra na comparação.
- **Entrada**: o FLAC do cache de áudio (`/cache/audio`, 22.050 Hz, mono,
  `tab.audio_extrair`). O instante da nota é convertido para o tempo do vídeo pelo
  `t_amostra0` do cache, como no alinhador.
- **Determinismo**: o vídeo de desenvolvimento roda duas vezes; o JSON tem de sair igual.

## A folha de respostas

A altura de cada nota do gabarito vem da física (decisão 0011 e seção 11 do AGENTS):
**MIDI = corda solta + casa + capo**, com a afinação padrão (E2 A2 D3 G3 B3 E4 = 40 45 50
55 59 64). O capo é dado de contexto permitido pela Regra 1, com fonte registrada:
`data/saida/maos/capo_por_video.json` (observações do dono nos gabaritos do braço). Vídeo
sem entrada lá conta como sem capo.

1. **Tablatura** (`data/gold/ouro_video/`): só as telas `conferida: true`. A janela de
   tempo de cada tela vem das `exibicoes` do `pre.json` da ferramenta
   (`data/saida/ouro_video/<slug>/pre.json`): é dado de contexto da imagem, sem som.
2. **Acorde cheio** (`data/gold/audio/acordes_2018.json`, commit `90294e04`): 4 telas,
   220 notas, 22 colunas de 5 ou 6 cordas, conferidas pelo dono para esta rodada. A janela
   é a exibição da tela no produto da 2017 (`data/saida/audio/r2017/produtos/`).
3. **Escuta** (`data/gold/audio/folha1–3.json`): os pontos "certo" fora dos controles,
   pela regra da rodada 2017 (40 pontos). É o instante em que a coluna começa a soar, a
   ±100 ms pelo ouvido do dono.

## Amostra

| papel | vídeos | telas conferidas | notas |
| --- | --- | --- | --- |
| **desenvolvimento** (acerta o código; não entra nos critérios) | sky guitar *retrato brasileiro* (v2) | 13 | 491 |
| **prova** (critérios C1, C2) | kenneth *end of beginning* (capo 2), pablo romé *greensleeves*, robert lunn *gymnopédie*, iwaki *la vie en rose*, guitar dell'arte *south american music*, kimny *from this place*, shin izumi *room 335* | 50 | 2.196 |
| **acorde cheio** (C3) | as 4 telas de `acordes_2018` + as colunas de 5–6 notas das telas de prova | 4 + — | 22 + 4 colunas (contagem prévia) |
| **instante** (C4) | os pontos "certo" da escuta nos vídeos de prova: *la vie en rose* 12, *from this place* 10, *room 335* 9 | — | 31 pontos |

- O *retrato brasileiro* é o vídeo mais estudado do projeto. Ele serve para depurar a
  conversão de tempo, a montagem das janelas e o pareamento, e o número dele vai no
  documento só como referência. Os 9 pontos de escuta dele também ficam fora do C4.
- O *retrato brasileiro* v1 (0 telas conferidas) não entra.

## Como se compara (fixado antes)

Por **exibição** de cada tela conferida:

1. **Colunas do gabarito**: notas agrupadas por `x_centro_quadro` (mesma coluna se a
   distância for ≤ 0,5 passo), em ordem de x. Cada coluna é um conjunto de alturas.
2. **Eventos do som**: as notas do transcritor com início em `[t0 − 0,25 s, t1 + 0,25 s]`,
   agrupadas em eventos por cadeia de inícios a ≤ 60 ms um do outro (acorde rasgueado
   espalha os ataques).
3. **Pareamento monotônico** (programação dinâmica, como um LCS): cada coluna pareia com no
   máximo um evento, na mesma ordem, maximizando o número de alturas iguais (MIDI exato).
4. Por tela, vale a exibição com mais alturas pareadas (uma tela pode ficar na tela
   enquanto o professor só fala).

Medidas:
- **Revocação** = notas do gabarito com altura pareada / notas do gabarito.
- **Precisão** = notas do som pareadas / notas do som nas janelas usadas, contadas só entre
  o primeiro e o último evento pareado (fora disso, o som pode ser fala ou outra passagem).
- **Erro de oitava e de semitom**: das notas do gabarito não pareadas, quantas têm no evento
  pareado uma nota a ±12 ou a ±1 semitom. É diagnóstico, não critério.
- **Controle negativo**: o mesmo pareamento com o gabarito deslocado +1 semitom. Mede quanto
  o pareamento acha "por acaso".
- **Acorde cheio**: por coluna de 5–6 cordas, a fração das notas da coluna achadas no evento
  pareado.
- **Instante**: para cada ponto de escuta, se há um início de nota do transcritor a ≤ 100 ms
  de `t_clique`.

## Critérios

| # | o quê | passa se |
| --- | --- | --- |
| C1 | altura, prova | revocação somada nos 7 vídeos **≥ 0,80**, e ≥ 0,70 em pelo menos 5 dos 7 |
| C2 | notas a mais, prova | precisão somada **≥ 0,70** |
| C3 | acorde cheio | mediana da fração achada nas colunas de 5–6 cordas (22 + as das telas de prova) **≥ 4/6** |
| C4 | instante | **≥ 28 de 31** pontos com início a ≤ 100 ms |
| V | validade do método | revocação do controle (+1 semitom) **≤ 0,25**; se passar disso, o pareamento é frouxo demais, e o resultado de C1–C3 não vale (vai para uma rodada nova, com outro método) |

## O que fazer em cada resultado

- **C1, C2 e V passam**: o Basic Pitch vira a fonte "som" da triangulação. Seguem a rodada
  do capo e da afinação pelo som (2019) e o cruzamento tela × som (2020). O formato
  `chorinho/som@1` vira decisão própria.
  - Se o **C3 falhar**: acorde de 5–6 cordas fica "sem dado" no cruzamento, e o MuScriptor
    entra como candidato só para acorde (pede ao dono a licença não comercial e o login no
    Hugging Face).
  - Se o **C4 falhar**: o instante continua vindo do alinhador (`t_audio`), e o transcritor
    só confere altura.
- **C1 falha**: mede-se a revocação e a precisão por faixa de confiança do transcritor.
  - Se houver uma faixa com precisão ≥ 0,90 e revocação ≥ 0,50, só ela entra como
    conferência, marcada.
  - Se não houver, o próximo candidato é o MuScriptor, com as duas decisões do dono.
- **Um vídeo muito abaixo dos outros** (revocação < 0,50) é olhado antes de qualquer
  conclusão: afinação diferente, capo não registrado ou som de outro instrumento. A
  causa vai para a 2019, e **o critério não muda**.

## Fora desta rodada

- Corda e casa: o som não sabe a corda (decisão 2005); a rodada mede só altura e instante.
- Técnica (h, p, slide, harmônico) e duração da nota.
- Ajuste de parâmetro, afinação ou capo pelo resultado: tudo isso é rodada nova.

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

## Emenda 1 — corte de confiança (2026-10-21, antes de medir a prova)

Feita só com o vídeo de desenvolvimento, como o pré-registro prevê. Nenhum vídeo de prova
foi medido; os JSONs do transcritor dos vídeos de prova foram gerados, mas não comparados
com o gabarito.

**O que se viu** no *retrato brasileiro* (13 telas, 491 notas), com o transcritor cru
(determinístico: duas execuções, JSON idêntico, 206 s cada):
- revocação **470/491 = 0,957**, mas precisão **470/1.144 = 0,411**, e o controle (+1
  semitom) em **0,263**, acima do limite V de 0,25;
- das 674 notas a mais no trecho pareado, **554 têm a altura de uma nota da própria tela**:
  é a música ouvida de novo (corda que continua soando, redisparo), e não ruído;
- elas são **mais fracas**: amplitude mediana 0,42 contra 0,65 das pareadas, e duração
  mediana 0,45 s contra 0,73 s.

**Curva do corte por amplitude** (só no desenvolvimento):

| corte | notas | revocação | precisão | controle |
| --- | --- | --- | --- | --- |
| 0 (cru) | 3.371 | 0,957 | 0,411 | 0,263 |
| 0,40 | 2.547 | 0,949 | 0,555 | 0,224 |
| 0,45 | 2.130 | 0,943 | 0,657 | 0,218 |
| **0,50** | **1.744** | **0,904** | **0,765** | **0,204** |
| 0,55 | 1.417 | 0,827 | 0,837 | 0,191 |
| 0,60 | 1.036 | 0,690 | 0,878 | 0,175 |

**Emenda**: a nota ouvida só entra na comparação com **amplitude ≥ 0,50**. A regra foi o
menor corte com precisão ≥ 0,70 e revocação ≥ 0,90 no desenvolvimento.
- **Os critérios C1–C4 e V não mudam.**
- O transcritor cru (corte 0) também é medido na prova e vai no resultado como linha
  secundária, para nada ficar escondido.
- O corte vale para C1, C2, C3 e C4.

## Resultado (2026-10-21)

Código: commit `9c8ce605` (`tab.audio_transcrever` na imagem `chorinho-som:dev`,
`tab.audio_som_medir` na base). Saídas em `data/saida/audio/r2018/` (`som/`,
`medida.json`, `medida_cru.json`, `analise.py`, `por_tamanho.py`). Os 12 vídeos foram
transcritos uma vez cada, a ~3,5 min por vídeo, em CPU.

### Critérios, com o corte da emenda 1 (amplitude ≥ 0,50)

| # | medida | resultado | |
| --- | --- | --- | --- |
| C1 | revocação na prova | **1.355/2.196 = 0,617**; ≥ 0,70 em **2 de 7** vídeos | **reprova** |
| C2 | precisão na prova | 1.355/1.688 = **0,803** | passa |
| C3 | acorde cheio, mediana | **0,367** em 28 colunas (22 de `acordes_2018` + 6 das telas de prova) | **reprova** |
| C4 | escuta, ≤ 100 ms | **30 de 31** | passa |
| V | controle +1 semitom | 255/2.196 = **0,116** | método válido |

- O C3 saiu no resumo da ferramenta com 29 colunas e mediana 0,333, porque ela incluiu a
  coluna do vídeo de desenvolvimento. Sem ela, como pré-registrado: 28 colunas, 0,367.
- O ponto de escuta que falhou é o `g30` (*room 335*, 73,94 s), o mesmo que já ficava a
  104 ms do alinhador na 2017.

Por vídeo de prova:

| vídeo | capo | revocação | precisão | controle |
| --- | --- | --- | --- | --- |
| kenneth *end of beginning* | 2 | 165/303 = 0,545 | 0,809 | 0,086 |
| pablo romé *greensleeves* | 0 | 93/106 = 0,877 | 0,949 | 0,142 |
| robert lunn *gymnopédie* | 0 | 226/392 = 0,577 | 0,766 | 0,117 |
| iwaki *la vie en rose* | 0 | 336/425 = 0,791 | 0,704 | 0,167 |
| guitar dell'arte *south american* | 0 | 149/269 = 0,554 | 0,898 | 0,052 |
| kimny *from this place* | 0 | 248/381 = 0,651 | 0,841 | 0,123 |
| shin izumi *room 335* | 0 | 138/320 = **0,431** | 0,902 | 0,113 |

### Linha secundária: o transcritor cru (corte 0)

| # | resultado | |
| --- | --- | --- |
| C1 | **1.743/2.196 = 0,794**; ≥ 0,70 em 5 de 7 | reprova por 0,006 |
| C2 | 1.743/2.951 = **0,591** | reprova |
| C3 | mediana **0,667** em 28 colunas | passa (≥ 4/6) |
| C4 | 30 de 31 | passa |
| V | 0,152 | válido |

### Leitura

1. **A emenda 1 piorou o resultado.** O corte foi escolhido no *retrato brasileiro*, que é
   quase só melodia: 358 das ~416 colunas têm uma nota. A prova é feita de acordes: só 578
   das 2.196 notas estão em coluna de uma nota. O corte apaga justamente as notas internas
   dos acordes, que soam mais fracas. Revocação por tamanho de coluna, na prova:

   | coluna | cru | corte 0,50 |
   | --- | --- | --- |
   | 1 nota | 489/578 = 0,846 | 0,728 |
   | 2 notas | 512/644 = 0,795 | 0,641 |
   | 3 notas | 355/501 = 0,709 | 0,511 |
   | 4+ notas | 387/473 = 0,818 | 0,560 |

   A amplitude não varia por gravação: a mediana fica entre 0,47 e 0,57 nos 12 vídeos. O
   erro foi o vídeo de desenvolvimento, que não representava a prova.
2. **Faixa de confiança** (passo pré-registrado para quando o C1 reprova), na prova:

   | corte | revocação | precisão | controle |
   | --- | --- | --- | --- |
   | 0 | 0,794 | 0,591 | 0,152 |
   | 0,40 | 0,760 | 0,725 | 0,137 |
   | 0,50 | 0,617 | 0,803 | 0,116 |
   | 0,60 | 0,348 | 0,865 | 0,066 |
   | 0,70 | 0,086 | 0,879 | 0,023 |

   **Nenhuma faixa tem precisão ≥ 0,90 com revocação ≥ 0,50.** O caminho pré-registrado é
   o próximo candidato, o MuScriptor, que depende de duas decisões do dono: aceitar a
   licença não comercial (CC BY-NC) e fazer o login no Hugging Face.
3. **O *room 335* abaixo de 0,50** só acontece com o corte: cru, ele dá 0,697, com 0 erros
   de semitom e 4 de oitava. Não há sinal de afinação diferente nem de capo esquecido. A
   perda é a mesma dos acordes (o vídeo tem 32 colunas de 4 notas nas telas conferidas).
4. **O que o Basic Pitch faz bem**: o instante (30 de 31 pontos de escuta a ≤ 100 ms) e,
   cru, os acordes cheios (mediana 4 de 6). O que ele faz mal é escrever notas a mais: cru,
   de cada 10 notas que ele escreve no trecho tocado, 4 não estão na tela.
5. **O capo funcionou** como dado de contexto. Cru, o *end of beginning* (capo 2) pareia
   197 de 303 notas, com 3 erros de semitom, e o *sakura* (capo 3) pareia 39 de 45, com 0.
   Se o capo estivesse errado, a revocação cairia para perto do controle.

**Conclusão: o Basic Pitch reprova** nos dois pontos de operação, e não vira a fonte "som"
da triangulação. O próximo passo é o MuScriptor, se o dono aprovar as duas decisões.

**Não repetir**: escolher um corte absoluto de confiança num vídeo de desenvolvimento que
é quase só melodia, e aplicá-lo a vídeos de acordes. O desenvolvimento tem de ter a mesma
mistura de tamanhos de coluna que a prova.

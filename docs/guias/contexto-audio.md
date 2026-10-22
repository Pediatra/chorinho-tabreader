# Contexto para o agente do áudio (terceira trilha)

> Documento de passagem de contexto, escrito em 2026-10-13 pelo agente que coordena a trilha
> **tablatura + tempo** (o "cérebro" do projeto). Leia este arquivo, depois o
> [`AGENTS.md`](../../AGENTS.md) **inteiro**, o [`ESTADO.md`](../../ESTADO.md), o
> [`plano-do-produto.md`](plano-do-produto.md) e o [`contexto-maos.md`](contexto-maos.md)
> (seções 2 a 4 e 6 valem para você também: projeto, ambiente, JSON do produto, convivência).
> Este documento não substitui o `AGENTS.md`: as regras de trabalho de lá valem para você.

---

## 1. O objetivo final e onde você entra

O dono quer um **dataset rotulado** para treinar, no futuro, um modelo que receba **só um vídeo
de alguém tocando violão** e devolva **tablatura e partitura**. Cada nota tocada nos vídeos-aula
do acervo precisa sair com tudo alinhado no tempo:

| camada | o que é | quem faz |
| --- | --- | --- |
| tablatura | corda, casa, coluna, compasso, símbolo cru | trilha tablatura (eu): pronta no MVP, Fase 8 em curso |
| tempo pelo marcador | `t_ini` de cada coluna pela faixa/cor que anda na tela | trilha tablatura (eu): pronto no MVP |
| **tempo pelo áudio** | **instante em que a nota soa**, por coluna, em todo vídeo com tablatura | **você** |
| mãos | keypoints e dedo de cada nota | trilha mãos (outra sessão Opus) |

**O problema que você resolve.** Hoje o tempo de cada nota vem do **marcador** da tela. Mas:

1. **Vídeos sem marcador não têm tempo nenhum.** No censo (amostra de 30 vídeos por canal com
   janela, sem cifra club), 109 de 394 vídeos com tablatura são `sem_marcador`: iwaki (25/30),
   shin izumi (29/30), kimny's guitar (29/30), transcriptor (22/30). Pesando pelo tamanho dos
   canais, são **~400 vídeos, ~15 % dos que têm tablatura**. Nesses o produto sai com as notas e
   **sem `t_ini`** (o produto não inventa tempo).
2. **Mesmo com marcador, o tempo é da animação, não do som.** A faixa diz quando a coluna "fica
   acesa" (precisão de 1 quadro, ~33 ms), mas a animação da tablatura vem do software de
   partitura e o violonista toca junto: pode haver atraso, adiantamento ou deriva. Para o modelo
   final (vídeo → tablatura), o que importa é **quando a nota soa**.

O caminho previsto no plano (Fase 10, item 3, autorizado pelo dono): **alinhar os ataques
(onsets) do áudio à sequência de colunas** que a tablatura já dá.

## 2. A ideia central: desenvolver onde já existe a resposta

**Não comece pelos vídeos sem marcador.** Comece pelos vídeos **com** marcador, onde o `t_ini`
de cada coluna já é medido e conferido. Ali você tem verdade para comparar:

- o vídeo do MVP, `sky guitar/retrato brasileiro - tab & lesson.mp4`: 13 páginas, 762 notas
  emitidas, **tempo certo em 39 de 40 instantes do gabarito do dono, 0 tempo falso**
  (`data/gold/ouro_video/retrato_brasileiro_v2.json`; régua `tab.avaliar_video`);
- os vídeos da Fase 8 com faixa (guitar dell'arte, robert lunn, kenneth acoustic, pablo romé),
  quando o dono terminar de rotular (ver seção 7).

O método só vale para vídeo sem marcador **depois** de medido em vídeo com marcador, **com o
marcador escondido** (o alinhador não pode ler a faixa). Só aí aplique a iwaki/shin izumi/kimny.

## 3. O que você já recebe de graça (e que torna o problema mais fácil do que parece)

O JSON do produto (`chorinho/video@1`, definição em `tab/esquema.py`; gerado por
`python -m tab.transcrever VIDEO --json saida.json`; o MVP atual está em
`data/saida/conserto_v2/mvp.json`) dá, **mesmo sem marcador**:

- **a sequência de colunas** de cada página, na ordem, e em cada coluna as notas (corda 1 =
  aguda … 6 = grave, casa). Acorde = várias notas na mesma coluna;
- **as alturas esperadas**: corda + casa + afinação + capotraste → nota MIDI. Afinação padrão
  E A D G B E é o caso comum; vários vídeos escrevem "Tuning/Capo" na tela (kenneth: "Capo:
  Fret 1/4"), e `tab/afinacao.py` existe (926 linhas) mas **nunca foi aferido**: não confie
  nele sem medir. Com as alturas, o problema deixa de ser "achar onsets" e vira **seguir a
  partitura** (score following / DTW em croma ou CQT), que é bem mais robusto;
- **a janela de tempo de cada página**: `telas[].exibicoes[].t0/t1` (segmentação por imagem,
  não depende de marcador). A página só está na tela nesse intervalo: o alinhamento é local,
  página a página;
- `barlines_x` e `compasso` por nota: dá para usar a métrica (compasso) como restrição.

Cuidados com o que o JSON **não** garante:

- **Passagens repetidas** (decisão D2): a mesma página pode ser tocada 2 vezes dentro de uma
  exibição (ou em exibições diferentes). Com marcador, `passagens` diz quantas; **sem marcador,
  o número de passagens é desconhecido** e o alinhador tem de descobrir (ou recusar);
- a página na tela **não é** garantia de que aquele trecho está sendo tocado: há introdução
  falada, versão lenta + normal no mesmo vídeo ("Slow Version"), troca de página adiantada ou
  atrasada em relação ao som;
- casas acima de 7 têm leitura **não validada** (o classificador foi aferido em casas 0–7);
  nota errada na tablatura vira altura errada no alinhamento: o alinhador deve tolerar algumas
  notas erradas sem desmontar;
- o áudio tem voz, metrônomo, música de fundo, às vezes outro instrumento. Cifra club é aula
  falada (e está fora da Fase 8 por falso positivo de presença).

## 4. Proposta de caminho (A0–A5), com critérios

O dono não definiu o "como". Abaixo é a minha proposta, no estilo do projeto (medir antes,
gabarito do dono é contrato, uma coisa por vez). Ajuste, mas **meça**.

**A0 — Áudio e custo.** Extraia o áudio com ffmpeg (já está no container) para mono, taxa fixa
(ex.: 22 050 Hz), e grave num **cache de áudio** no HD externo, irmão do cache de quadros:
`/cache/audio/<hash da chave do vídeo>.flac` (sem perda; a chave é a mesma do censo,
`relativo|tamanho|mtime`, ver `tab/cache.py`). **Meça o custo em 20 vídeos** (regra 2) antes
de pensar em lote: extrair áudio lê o arquivo inteiro do HD. Confira o **deslocamento entre o
relógio do áudio e o PTS do vídeo** (`start_time` do stream de áudio vs. do vídeo no ffprobe):
um desvio aqui contamina tudo.

**A1 — O atraso marcador → som, medido.** No MVP, para cada coluna com `t_ini` do marcador,
ache o ataque mais próximo no áudio (onset por fluxo espectral, ou energia na altura esperada).
Reporte a distribuição de `t_som − t_marcador` (mediana, p10, p90, por página e ao longo do
vídeo), em ms. Isso responde: (a) o marcador está atrasado/adiantado de um valor fixo? (b) há
deriva? (c) qual a precisão alcançável? **Olhe** (ou melhor, escute e plote) 3 trechos antes
de teorizar: espectrograma com as colunas do marcador sobrepostas, em `data/saida/audio/`.

**A2 — O alinhador.** Para cada exibição de cada página: monte a sequência de "eventos
esperados" (colunas, com as alturas) e alinhe ao áudio da janela `t0..t1` (± uma folga). Ponto
de partida razoável: DTW sobre croma/CQT com um molde sintético das alturas esperadas (há
bibliotecas prontas para croma/CQT/DTW; escolha por medição, não por fama), refinando cada
coluna para o onset mais próximo. Saída por coluna: `t_audio`, uma **confiança**, e a
**recusa** explícita quando não há alinhamento confiável (página sem som correspondente,
passagens ambíguas, fala por cima). **Falso positivo é o pior erro do projeto**: um tempo
errado afirmado é pior que um tempo ausente declarado.

**A3 — Régua.** No MVP e nos vídeos com faixa, **com o marcador escondido**:
- fração de colunas com `|t_audio − (t_marcador + atraso_A1)| ≤ 50 ms` e `≤ 100 ms`, com
  denominador ("X de Y colunas"), por vídeo e por página;
- colunas recusadas (quantas e por quê) e colunas com tempo **falso** (afirmado e fora de
  200 ms);
- **critério proposto para aplicar a vídeo sem marcador**: ≥ 90 % das colunas a ≤ 100 ms nos
  vídeos com faixa, e **0,5 % ou menos** de tempo falso. Combine o número final com o dono.

**A4 — Vídeos sem marcador.** Aplique a iwaki, shin izumi e kimny. Aqui não há verdade
automática: monte uma **folha de conferência** que o dono consiga julgar rápido. Por exemplo,
um clipe curto com um "clique"/destaque sobreposto na coluna no `t_audio`, ou um espectrograma
com as colunas marcadas, para ~20 trechos sorteados. O dono diz "certo / errado / não sei".
**O tempo do dono é o gargalo do projeto**: peça o mínimo que mede.

**A5 — Esquema e entrega.** Proponha como o tempo do áudio entra no produto, por exemplo um
campo por nota (`t_audio`, `t_audio_confianca`) e um `origem_tempo` ("marcador" | "audio"),
ou um arquivo irmão `<video>.audio.json` com a chave do evento de nota
`(tela, passagem, exibicao, coluna, corda)`. **`tab/esquema.py` é da trilha tablatura: não
o edite.** Escreva a proposta em `docs/decisoes/2NNN-…` e peça ao dono para me repassar; eu
faço a mudança no esquema.

## 5. Regras de convivência (agora são três trilhas)

As regras da seção 6 do [`contexto-maos.md`](contexto-maos.md) valem integralmente. Para você:

1. **Seus arquivos**: módulos `tab/audio_*.py` (pacote único e plano, sem subpacote), testes
   `tests/test_audio_*.py`, saída em `data/saida/audio/`, gabarito em `data/gold/audio/`,
   pesos (se houver) em `artefatos/audio_*/`, cache em `/cache/audio/`.
2. **Não edite** os arquivos da trilha tablatura (lista na seção 6 do `contexto-maos.md`,
   mais `tab/ouro_video.py`) nem os da trilha mãos (`tab/maos_*.py`, `tests/test_maos_*`,
   `data/saida/maos/`, `data/gold/maos/`, `Dockerfile.maos`). Importar é livre (`leitor`,
   `cache`, `esquema`, `video`).
3. **Documentos**: `docs/rodadas/2NNN-…` e `docs/decisoes/2NNN-…` (tablatura usa 0NNN, mãos
   1NNN). Seção nova no fim de `docs/estado/audio.md` (decisão 9001); no `ESTADO.md`, só a tabela "não repetir"; confira
   `git diff ESTADO.md` antes de commitar: só as suas linhas podem entrar.
4. **Dependências novas** (biblioteca de áudio, DTW…): **não mexa** no `Dockerfile` nem no
   `requirements.txt` da base. Faça uma imagem derivada `Dockerfile.audio` (`FROM
   docker.io/library/chorinho:dev`), como a trilha mãos fez (`Dockerfile.maos`, decisão
   [`1001`](../decisoes/1001-imagem-derivada-maos.md)), com versões fixas. Cuidado para a
   instalação não trocar `torch`/`opencv` da base (a trilha mãos se queimou com isso:
   `--no-deps` quando preciso).
5. **Gate compartilhado** (`ruff check .`, `ruff format --check .`, `pytest tests/ -m "not
   integration"`): os testes do gate rodam na imagem **base**. Teste que importa biblioteca
   que só existe na sua imagem derivada tem de pular limpo (`pytest.importorskip`) ou levar a
   marca `integration`. Um arquivo seu quebrado deixa o gate vermelho para as três trilhas.
6. **Git**: `git add` só por nome; nunca `add -A`, `reset`, `amend`, `stash`, `checkout --`;
   mensagem via arquivo (`git commit -F arq`); um commit por tarefa, com o número medido.
7. **GPU** (uma só, 8 GB, compartilhada): `data/saida/gpu.lock` com
   "audio, <início>, <estimativa>" antes de uso longo; se houver lock de outra trilha, espere
   ou rode em CPU. Alinhamento de áudio provavelmente nem precisa de GPU.
8. **HD externo** é o gargalo de E/S: duas leituras longas ao mesmo tempo dobram o tempo de
   ambas. Extraia áudio uma vez só para o cache; para lote grande, combine a janela de horário
   com o dono.
9. **Comunicação**: as sessões não se falam direto; o dono é a ponte. Decisão que afete outra
   trilha vira arquivo em `docs/decisoes/`.

## 6. Regras do projeto que mais pesam para você (resumo do `AGENTS.md`)

- **Olhe (e escute) antes de teorizar.** Espectrograma com as colunas sobrepostas, em
  `data/saida/audio/`, antes de qualquer conclusão.
- **Rótulo de gabarito só do dono, por leitura (ou escuta) dele.** Agente nunca grava em
  `data/gold/` por conta própria; rótulo provisório de agente vai para `data/saida/`, marcado.
- **Confira o significado do número**: conte colunas distintas, imprima denominadores; diga se
  o número inclui ou não as colunas recusadas.
- **O pré-processamento é parte da medição** (taxa de amostragem, janela da STFT, normalização):
  mudou, invalidou a comparação com o histórico. Registre.
- **Determinismo**: mesma entrada → mesmo JSON. Se houver qualquer aleatoriedade, semente fixa
  e ≥ 3 execuções com média e amplitude.
- **Registre o que falhou** na tabela "não repetir" do `ESTADO.md`.
- Código: Python 3.14, sem import dentro de função, aspas duplas, 88 colunas, type hints,
  docstring Google, **nomes em português**, CLI `python -m tab.audio_x` com `main()`.

## 7. Estado das outras trilhas (2026-10-13)

- **Tablatura (eu)**: censo v2 refeito (2.998 vídeos ativos, 93,9 % com tablatura; arquivo
  `data/saida/censo/v2/censo_v2_completo.jsonl`, com `marcador` e `forma` em 30 vídeos por
  canal). **Fase 8**: gabarito de tablatura+tempo em 7 vídeos paginados, sendo preparado agora
  para o dono rotular: guitar dell'arte (South American Music), robert lunn (Gymnopédie no.1),
  iwaki (La Vie en Rose), kenneth acoustic (End of Beginning), shin izumi (Room 335), pablo romé
  (Greensleeves), kimny's guitar (From This Place). Os de iwaki, shin izumi e kimny **não têm
  marcador**: o gabarito deles terá páginas e notas, mas os instantes vão sair quase todos
  "nenhuma acesa". **Esses três são exatamente o seu alvo**: o gabarito de notas deles serve
  para você, o de tempo não. Dois vídeos rolantes (leonardo ramos, mr. tabs) esperam o formato
  da rolagem (T8.4).
- **Mãos**: outra sessão, detector RTMPose Wholebody + MediaPipe escolhido, gabaritos de dedo
  e do braço em curso (rodadas 1001–1007). Ela usa `t_ini` como instante de cada nota: um
  `t_audio` melhor ajuda ela também, e é mais um motivo para a chave de evento ser a mesma.

## 8. Arquivos para ler primeiro

1. `AGENTS.md` (inteiro): o contrato.
2. `ESTADO.md`: estado medido, tabela "não repetir", seções da Fase 5 (tempo pelo marcador:
   observadores `posicao`, `cor`, `cor_acende`; regra da faixa translúcida) e do censo.
3. `docs/guias/plano-do-produto.md`: fases, critérios de aceite, Fase 10 item 3.
4. `docs/guias/contexto-maos.md`: seções 2, 3, 4 e 6.
5. `docs/rodadas/0004-mvp-video-inteiro.md`: o MVP, números, erros conhecidos.
6. `tab/esquema.py`, `data/saida/conserto_v2/mvp.json`: a chave comum.
7. `tab/leitor.py` (leitor único de vídeo, PTS real), `tab/cache.py` (chave e pastas do
   cache), `tab/video.py` e `tab/estado.py` (como o `t_ini` do marcador é medido).
8. `tab/avaliar_video.py`: a régua de tempo contra o gabarito do dono.

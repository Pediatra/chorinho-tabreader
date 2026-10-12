# Rodada 1001: censo de mãos (M0)

Data: 2026-10-12. Trilha das mãos (ver `docs/guias/contexto-maos.md`, seção 5, M0).
Imagem: `chorinho-maos:dev` ([decisão 1001](../decisoes/1001-imagem-derivada-maos.md)).

## Pergunta

Em quais canais as mãos do violonista aparecem, e como (rosto no quadro, só o tronco,
close do braço), nos 12 quadros de presença de cada vídeo? A resposta decide quais canais
servem para a trilha das mãos antes da escolha do detector (M1). Sem rótulo de gabarito:
é censo de máquina, com uma conferência visual de 30 vídeos.

## Instrumento

- **Quadros**: os 12 quadros de presença de cada vídeo (0,05 a 0,95 da duração), lidos do
  cache de quadros (`tab/cache.py`, montado em `/cache`). A lista de vídeos, os instantes e a
  caixa da TAB vêm do censo de presença (`data/saida/censo/censo_cache.jsonl`). Canais com
  `rollout: fora` (`violaodecria`, `tv cifras`) são pulados (`tab/censo.py`, `ler_rollout` e
  `canais_fora`).
- **Detector de mão**: MediaPipe HandLandmarker 1.1.0, até 4 mãos por chamada, confiança 0,3
  para detecção, presença e rastreio (`CONFIANCA_MAO`). Modelo `hand_landmarker.task`, fixado
  por sha256.
- **Blocos**: cada quadro passa no quadro inteiro e em 4 blocos (2×2), com 25 % de
  sobreposição (`BLOCOS_POR_LADO`, `SOBREPOSICAO_BLOCOS`). O piloto mostrou que o detector de
  palma reduz a imagem a 192 px e perde a mão pequena.
- **Fusão**: detecções da mesma mão (interseção ≥ 0,5 da caixa menor) ficam com a de maior
  score (`fundir_maos`, `SOBREPOSICAO_MESMA_MAO`).
- **Rosto**: YuNet do OpenCV (`cv2.FaceDetectorYN`), quadro reduzido a 960 px, score mínimo
  0,8 (`CONFIANCA_ROSTO`). Rosto cujo centro cai dentro da TAB não conta.
- **Regra da TAB**: mão cujo centro cai dentro da caixa da TAB do censo de presença é marcada
  `na_tab` e não conta (`dentro_da_tab`). É a regra que a auditoria pendente questiona.
- **Vista do quadro**: `rosto` (há rosto), `sem_rosto` (há mão e nenhum rosto) ou `sem_mao`
  (`vista_do_quadro`).
- **Vídeo que serve**: 2+ mãos em pelo menos 50 % dos quadros lidos (`FRACAO_VIDEO_COM_MAOS`).
  O limiar é proposta do M0; o número que decide é a tabela.
- **Módulos**: `tab/maos_censo.py` (detector e CLI); `tab/maos_tabela.py` (regras puras:
  fusão, regra da TAB, resumo por vídeo e por canal, markdown); `tab/maos_conferencia.py`
  (folha de 30 vídeos, sorteio estratificado por canal).

## Piloto

Amostra de 2 vídeos por canal, semente 20261012: 36 vídeos, 432 quadros
(`--max-por-canal 2`; saídas `data/saida/maos/piloto_*.jsonl`).

- **Determinismo**: duas execuções idênticas, 36 de 36 vídeos, tanto na versão com pose quanto
  na versão final.
- **Custo**: 36 vídeos em ~33 s com 6 processos, só CPU.
- **Pose do MediaPipe reprovada para rosto**: marcou "rosto" em 5 de 12 quadros de close das
  mãos do `sky guitar`, onde não há rosto. Foi trocada pelo YuNet. A saída com pose está em
  `data/saida/maos/piloto_pose_reprovada.jsonl`.

Comparação de configurações contra rótulo **provisório (agente)** em 36 quadros
(`data/saida/maos/rotulo_agente_piloto.json`):

| configuração | quadro certo | mão esquerda achada | mão direita achada | falsas |
| --- | --- | --- | --- | --- |
| confiança 0,5 + blocos 2×2 | 28/36 | 26/34 | 32/33 | 0 |
| confiança 0,3 + blocos 2×2 (ADOTADA) | 32/36 | 30/34 | 32/33 | 0 |
| confiança 0,5 + blocos 3×3 | 25/36 | 23/34 | 29/33 | 0 |
| confiança 0,3 + blocos 3×3 | 24/36 | 23/34 | 29/33 | 0 |

- Blocos 3×3 pioram: na fusão, um pedaço de mão com score alto toma o lugar da mão inteira e
  do lado certo.
- Nos 25 quadros que mudaram de 0,5 para 0,3 (contagem do agente, provisória): ~19 ganhos
  reais (mão do braço vista de costas, em preto e branco) e ~3 erros de **troca de lado**
  (L/R). Nenhuma mão inventada fora do violonista.
- Conclusão do piloto: "há mão" é confiável; o rótulo L/R do MediaPipe não é. Por isso a
  tabela usa colunas que não dependem do lado ("alguma mão", "2+ mãos").

## Censo

- 2.798 vídeos de 19 canais ativos (`rollout: fora` pulados); 33.576 quadros (12 por vídeo);
  0 quadros faltando no cache; 2.907 s com 6 processos.
- 57.484 mãos detectadas; 419 (0,7 %) descartadas pela regra da TAB.
- Saídas: `data/saida/maos/censo_maos.jsonl`; log `data/saida/maos/censo_maos.log`.

Tabela por canal, copiada literalmente do fim de `data/saida/maos/censo_maos.log`:

| canal | vídeos | quadros | alguma mão | 2+ mãos | 2+ mãos nos quadros com TAB | vídeos que servem | L | R | L e R | > 2 mãos | rosto / sem rosto / sem mão | palma / altura |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sky guitar | 417 | 5004 | 97 % | 94 % | 95 % (2936/3086) | 416 (100 %) | 94 % | 96 % | 93 % | 2 % | 0 % / 97 % / 3 % | 0.142 |
| robert lunn | 369 | 4428 | 85 % | 42 % | 41 % (1374/3370) | 161 (44 %) | 52 % | 67 % | 34 % | 1 % | 7 % / 78 % / 15 % | 0.131 |
| guitar dell ́arte | 361 | 4332 | 91 % | 66 % | 70 % (1447/2066) | 316 (88 %) | 78 % | 77 % | 64 % | 1 % | 3 % / 88 % / 9 % | 0.172 |
| cifra club | 341 | 4092 | 97 % | 72 % | 81 % (917/1126) | 308 (90 %) | 78 % | 81 % | 63 % | 3 % | 16 % / 81 % / 3 % | 0.114 |
| leonardo ramos | 298 | 3576 | 94 % | 84 % | 88 % (2722/3079) | 296 (99 %) | 86 % | 91 % | 82 % | 1 % | 1 % / 94 % / 6 % | 0.134 |
| kenneth acoustic | 294 | 3528 | 99 % | 88 % | 89 % (1486/1672) | 290 (99 %) | 96 % | 90 % | 87 % | 0 % | 0 % / 99 % / 1 % | 0.118 |
| iwaki | 164 | 1968 | 100 % | 97 % | 97 % (1803/1853) | 164 (100 %) | 96 % | 97 % | 93 % | 1 % | 1 % / 99 % / 0 % | 0.109 |
| shin izumi | 149 | 1788 | 100 % | 97 % | 98 % (1725/1761) | 147 (99 %) | 89 % | 96 % | 85 % | 3 % | 1 % / 98 % / 0 % | 0.080 |
| pablo romé | 123 | 1476 | 94 % | 82 % | 93 % (508/547) | 115 (93 %) | 87 % | 86 % | 79 % | 4 % | 54 % / 44 % / 3 % | 0.093 |
| kimny's guitar | 108 | 1296 | 68 % | 17 % | 18 % (210/1200) | 13 (12 %) | 27 % | 56 % | 15 % | 0 % | 0 % / 68 % / 32 % | 0.159 |
| ギタロー ⧸ guitarous | 55 | 660 | 96 % | 91 % | 94 % (417/445) | 50 (91 %) | 90 % | 92 % | 86 % | 12 % | 0 % / 95 % / 4 % | 0.138 |
| serge kottelat | 38 | 456 | 76 % | 57 % | 61 % (235/384) | 24 (63 %) | 59 % | 67 % | 51 % | 3 % | 60 % / 21 % / 19 % | 0.056 |
| transcriptor | 35 | 420 | 74 % | 64 % | 66 % (214/323) | 23 (66 %) | 68 % | 69 % | 63 % | 2 % | 14 % / 61 % / 25 % | 0.106 |
| mr. tabs | 22 | 264 | 95 % | 76 % | 77 % (186/241) | 20 (91 %) | 77 % | 93 % | 74 % | 3 % | 1 % / 94 % / 5 % | 0.123 |
| paolo d'angelo | 14 | 168 | 98 % | 82 % | 82 % (108/132) | 14 (100 %) | 80 % | 97 % | 79 % | 2 % | 1 % / 97 % / 2 % | 0.165 |
| tv on guitar | 5 | 60 | 97 % | 85 % | 88 % (51/58) | 5 (100 %) | 85 % | 97 % | 85 % | 2 % | 0 % / 97 % / 3 % | 0.104 |
| lonelypicker | 3 | 36 | 64 % | 56 % | 55 % (18/33) | 2 (67 %) | 47 % | 61 % | 44 % | 0 % | 0 % / 64 % / 36 % | 0.090 |
| vvxofingerstyletab | 1 | 12 | 83 % | 75 % | 90 % (9/10) | 1 (100 %) | 83 % | 75 % | 75 % | 0 % | 0 % / 83 % / 17 % | 0.160 |
| yunus guitarist | 1 | 12 | 100 % | 100 % | 100 % (12/12) | 1 (100 %) | 100 % | 100 % | 100 % | 0 % | 0 % / 100 % / 0 % | 0.125 |
| **TOTAL** | 2798 | 33576 | 93 % | 75 % | 77 % (16378/21398) | 2366 (85 %) | 80 % | 84 % | 70 % | 2 % | 7 % / 86 % / 7 % | 0.128 |

Legenda (de `markdown()` em `tab/maos_tabela.py`; porcentagens sobre quadros, salvo onde
indicado):

- **canal**, **vídeos**, **quadros**: vídeos do canal e quadros lidos (12 por vídeo).
- **alguma mão**: quadros com ao menos uma mão válida (fora da caixa da TAB).
- **2+ mãos**: quadros com duas ou mais mãos válidas, de qualquer lado. Não depende do rótulo L/R.
- **2+ mãos nos quadros com TAB**: entre os quadros em que o censo de presença viu TAB, a
  fração com 2+ mãos. Entre parênteses, `quadros com 2+ mãos / quadros com TAB`.
- **vídeos que servem**: vídeos em que 2+ mãos aparecem em pelo menos 50 % dos quadros
  lidos. Entre parênteses, a fração dos vídeos do canal.
- **L**, **R**, **L e R**: quadros com mão de rótulo esquerda, direita, ou ambas. Usam o
  rótulo do detector, que troca a mão do braço visto de costas: coluna secundária.
- **> 2 mãos**: quadros com mais de duas mãos válidas.
- **rosto / sem rosto / sem mão**: vista do quadro. `sem rosto` = há mão e nenhum rosto;
  `sem mão` = nem mão nem rosto.
- **palma / altura**: mediana, entre os vídeos, da mediana da palma por vídeo (punho até a
  base do dedo médio), dividida pela altura do quadro. Mede escala, não presença.

## Leitura

Leitura do coordenador, registrada como leitura. Não é medida nova.

1. Mãos aparecem em 93 % dos quadros e rosto em 7 % (33.576 quadros). O enquadramento típico
   é tronco cortado ou close do braço. Isso pesa a favor de um detector **específico de mão**,
   e não de um que acha a pessoa primeiro.
2. Palma mediana = 0,128 da altura do quadro (~140 px em 1080p). O menor é o
   `serge kottelat`, com 0,056.
3. Número baixo não quer dizer "canal sem mão". No `kimny's guitar` (17 % com 2+ mãos) as
   mãos estão lá, mas o vídeo é preto e branco escuro e o detector falha. O `robert lunn`
   (42 %) mistura close, corpo inteiro e quadros só de partitura.
4. A tabela é um **piso**: os erros observados são de perder mão (e de trocar o lado). O
   único falso observado é um rosto, na conferência (quadro 24, provisório).

## Conferência de 30

`python -m tab.maos_conferencia`, semente 20261013, estratificada por canal, **excluindo os
vídeos do piloto**. Folhas: `data/saida/maos/conferencia_30_{1,2,3}.jpg`. Manifesto:
`data/saida/maos/conferencia_30.json`.

- **Contagem provisória (agente)**: cerca de 25 de 30 quadros (83 %) com esquerda e direita
  certas. O critério é 90 %, então **não fecha**.
- Erros do agente (provisórios):
  - 03: mão direita borrada pelo movimento, não achada. **Pendente do dono**.
  - 04: mão esquerda em close, não achada. **Confirmado pelo dono** em 2026-10-12: "tinha mão,
    a esquerda, mas tava com zoom e aberta fazendo uma nota espaçada".
  - 06: as duas mãos achadas, mas descartadas pela regra "dentro da TAB", porque a caixa da
    TAB do censo de presença cobre o vídeo. **Pendente do dono**.
  - 12 (`kimny's guitar`): preto e branco escuro, nenhuma mão achada. **Pendente do dono**.
  - 17: mão esquerda rotulada como direita. **Pendente do dono**.
  - 24: rosto falso (afeta só a coluna de rosto). Provisório, não conferido pelo dono.
- **Dono (2026-10-12)**: confirmou o 04. Os erros 03, 06, 12 e 17 seguem pendentes.
- **Decisão do dono (2026-10-12)**: seguir para o M1 (escolha do detector) com o censo neste
  estado, porque os erros não mudam a conclusão principal. O critério de 90 % do M0 continua
  aberto e registrado aqui.

## Não repetir

- **Pose do MediaPipe para dizer "tem rosto"**: inventa rosto em close de mãos (5 de 12
  quadros no `sky guitar`).
- **Blocos 3×3 na fusão por score**: pioram (25/36 contra 28/36 com confiança 0,5; 24/36
  contra 32/36 com confiança 0,3).
- **Confiar no rótulo L/R do MediaPipe** para a mão do braço visto de costas: troca o lado.
- **Regra "mão com o centro dentro da caixa da TAB é desenho"**: correta para o diagrama de
  mão do `sky guitar`, mas apaga mão real quando o censo de presença erra a caixa (braço do
  violão tomado por TAB, ou caixa sobre o vídeo). Auditoria pendente.

## Comandos

No container da imagem derivada (`chorinho-maos:dev`):

```bash
podman build -t chorinho-maos:dev -f Dockerfile.maos .
python -m tab.maos_censo --max-por-canal 2 --saida data/saida/maos/piloto_c0.3_b2.jsonl
python -m tab.maos_censo --saida data/saida/maos/censo_maos.jsonl
python -m tab.maos_censo --tabela data/saida/maos/censo_maos.jsonl
python -m tab.maos_conferencia --censo data/saida/maos/censo_maos.jsonl --excluir data/saida/maos/piloto_c0.3_b2.jsonl --n 30 --semente 20261013 --saida data/saida/maos/conferencia_30
```

## Pendências

1. Auditoria da regra "dentro da TAB" nas 419 mãos descartadas (0,7 %). Sem ela, não se sabe
   quantas eram mão real.
2. Confirmação do dono nos quadros 03, 06, 12 e 17 da conferência.
3. Critério de 90 % do M0 em aberto (83 % provisório), com decisão do dono de seguir para o M1.
4. Para a trilha tablatura (via dono): o censo de presença marca o braço do violão como TAB
   em closes do `guitar dell'arte` e do `leonardo ramos`.
5. Dono: apagar o rascunho `data/saida/maos/imagem/Dockerfile` (substituído por
   `Dockerfile.maos`).
6. Contexto do build com 2,8 GB (`data/saida/`, não excluído pelo `.dockerignore`). Decidir se
   o padrão passa a excluí-lo.

## Artefatos

- Censo: `data/saida/maos/censo_maos.jsonl`, `data/saida/maos/censo_maos.log`.
- Piloto: `data/saida/maos/piloto_*.jsonl`, `data/saida/maos/rotulo_agente_piloto.json`.
- Conferência: `data/saida/maos/conferencia_30_{1,2,3}.jpg`, `data/saida/maos/conferencia_30.json`.
- Imagem: `Dockerfile.maos` (raiz); decisão `docs/decisoes/1001-imagem-derivada-maos.md`.

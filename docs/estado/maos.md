# Estado — Mãos e braço

Seções movidas inteiras do [`ESTADO.md`](../../ESTADO.md) na decisão 9001
(fase 5), na mesma ordem. Seção nova desta trilha entra no fim deste arquivo.

## Mãos — 2026-10-12 — M0: censo de mãos (2.798 vídeos, 12 quadros cada)

Rodada completa: [`docs/rodadas/1001-censo-de-maos.md`](../../docs/rodadas/1001-censo-de-maos.md). Imagem: [decisão 1001](../../docs/decisoes/1001-imagem-derivada-maos.md).

**Medido**: MediaPipe (mãos) e YuNet (rosto) em 33.576 quadros (12 por vídeo, 0 faltando) de 2.798 vídeos de 19 canais, em 2.907 s com 6 processos, só CPU. 57.484 mãos detectadas; 419 (0,7 %) descartadas pela regra da TAB. Configuração adotada no piloto (36 vídeos, 2 por canal): confiança 0,3 e blocos 2×2, com 32 de 36 quadros certos (provisório, agente). Determinismo: 36 de 36 vídeos.

Tabela por canal, copiada de `data/saida/maos/censo_maos.log`. Legenda das colunas na rodada.

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

**Leitura** (do coordenador; não é medida nova):
- mãos em 93 % dos quadros e rosto em 7 %: enquadramento típico de tronco cortado ou close do braço. Pesa a favor de detector específico de mão;
- palma mediana 0,128 da altura do quadro; o menor é `serge kottelat`, 0,056;
- número baixo não é canal sem mão: `kimny's guitar` (17 % com 2+ mãos) é preto e branco escuro; `robert lunn` (42 %) mistura close, corpo inteiro e partitura;
- a tabela é um piso: os erros observados são de perder mão.

**Conferência de 30** (semente 20261013, excluindo o piloto):
- provisório (agente): cerca de 25 de 30 (83 %) com esquerda e direita certas. Critério de 90 %: **não fechado**;
- dono (2026-10-12): confirmou o erro do 04 (mão esquerda em close, não achada). Pendentes: 03, 06, 12 e 17;
- dono (2026-10-12): seguir para o M1 com o censo neste estado.

**Não repetir**:
- pose do MediaPipe para dizer "tem rosto": inventa rosto em close de mãos (5 de 12 no `sky guitar`);
- blocos 3×3 na fusão por score: pioram (25/36 contra 28/36; 24/36 contra 32/36);
- rótulo L/R do MediaPipe para a mão do braço visto de costas: troca o lado;
- regra "mão com centro dentro da caixa da TAB é desenho": apaga mão real quando a caixa da TAB está errada. Auditoria pendente.

**Pendências**: auditoria da regra da TAB (419 mãos); confirmação do dono nos quadros 03, 06, 12 e 17; para a trilha tablatura (via dono), o braço do violão marcado como TAB em closes do `guitar dell'arte` e do `leonardo ramos`.

## Mãos — 2026-10-12 — M1: detector de mãos (Wholebody GPU + MediaPipe)

Rodada: [`docs/rodadas/1002-escolha-do-detector.md`](../../docs/rodadas/1002-escolha-do-detector.md). Decisão: [1002](../../docs/decisoes/1002-detector-de-maos.md). Imagem: `chorinho-maos:dev` ([decisão 1001](../../docs/decisoes/1001-imagem-derivada-maos.md)).

**Decisão do dono (2026-10-12)**: detector = RTMPose Wholebody (RTMW-DW-X-L, **na GPU**) como base, com MediaPipe como complemento. Mão do Wholebody com média dos 21 scores acima de 0,4; complemento só com mão do MediaPipe fora da TAB e com sobreposição menor que 0,3 com toda mão aceita.

**Medido** (validação fora do ajuste, 90 quadros; rótulo **provisório (agente)**; o limiar 0,4 foi escolhido nesses mesmos 90):

| detector | quadro certo | mão esquerda | mão direita | falsas |
| --- | --- | --- | --- | --- |
| MediaPipe (censo M0) | 72/90 | 70/86 | 75/79 | 1 |
| Wholebody 0,5 | 81/90 | 79/86 | 77/79 | 3 |
| Wholebody 0,4 | 84/90 | 84/86 | 78/79 | 3 |
| Wholebody 0,4 + MediaPipe (**adotado**) | 86/90 | 86/86 | 78/79 | 3 |

- Só nos 60 novos: MediaPipe 47/60; Wholebody 0,4, 58/60; combinação, 59/60.
- Erros que sobram (4): C03 (mão direita borrada, não achada); C04, C17, N09 (close de uma mão só, com falsa mão direita).
- Piloto (36 quadros, ajustado no MediaPipe): Wholebody 0,5 deu 36/36 em CPU, 0,53 s por quadro. O censo do piloto, com a imagem nova, segue 36/36.
- GPU: 0,20 a 0,22 s por quadro, com o MediaPipe incluído; duas execuções byte a byte iguais. A validação de 90 rodou na GPU (a trava CUDA impede CPU). Não misturar com números de CPU.
- Reavaliação offline da combinação atual (`data/saida/maos/m1/reavaliar_sem_honestidade.py`): 86/90, reproduzido.

**Regra de honestidade REPROVADA**: "esquerda e direita da mesma pessoa, com sobreposição ≥ 0,5, viram `incerto`". A regra não ganhou nenhum quadro (C04 e N09 trocaram a mão direita falsa por perder também a esquerda verdadeira, que virou `incerto`) e perdeu 2 (C08, N25): **84/90 contra 86/90**. Removida. Não ajustar nos mesmos 90 quadros.

**Não repetir**:
- Chamar o `Wholebody` com detector vazio: a pose roda no quadro inteiro e inventa pessoa e mão;
- `onnxruntime-gpu` sem o `LD_LIBRARY_PATH` do torch cai em CPU calado (a trava `_travar_cuda` aborta);
- `rtmlib` com dependências puxa `opencv-contrib-python` sobre o cv2 da base: instalar com `--no-deps`;
- regra de honestidade por sobreposição (reprovada, acima);
- Wholebody sozinho com limiar 0,5 nos 90 quadros: 81/90 (0,4 deu 84/90).

**Pendências**:
1. Gabarito de pontas e de dedo para o M2 (dono);
2. falsa mão direita em close de uma mão só (3 de 90): sem regra;
3. rótulo da validação é do agente (provisório); confirmação do dono ou conjunto novo com rótulo do dono **a medir**;
4. limiar 0,4 fora do ajuste: escolhido nos mesmos 90 quadros; número fora do ajuste **a medir**;
5. tempo em vídeo inteiro e no acervo (2.798 vídeos) **a medir**.

**Artefatos**: `docs/rodadas/1002-escolha-do-detector.md`; `docs/decisoes/1002-detector-de-maos.md`; código `tab/maos_detector.py`, `tab/maos_combinar.py`, `Dockerfile.maos`; validação `data/saida/maos/m1/detector_validacao.jsonl` e `rotulo_agente_validacao.json`.

## 2026-10-12 — Mãos — M2: gabarito de dedos do dono

Rodada completa: [`docs/rodadas/1003-gabarito-de-dedos.md`](../../docs/rodadas/1003-gabarito-de-dedos.md). Gabarito: `data/gold/maos/dedos_retrato_brasileiro.json` (formato 3). Vídeo: `sky guitar/retrato brasileiro - tab & lesson.mp4` (MVP).

**Medido (rotulado pelo dono, 2026-10-12)**: 40 ataques e 56 notas (amostra de 40 sorteios, semente 20261012, estratificada no tempo). Esquerda: 1 = 14, 0 = 13, 2 = 10, 3 = 8, 4 = 8, ? = 3. Direita: p = 17, a = 16, m = 10, i = 10, ? = 3. Pestana: sim 6, não 33, ? 1.

**Confiabilidade**: esquerda alta; **direita PARCIAL** (parte inferida pelo dono; só indicativo). `n19` excluída (o dono disse que a casa 3 da corda 3 não está sendo apertada); `a22` duplica `a21`.

**Lição**: três defeitos da ferramenta foram achados pelo dono no uso (marcava a coluna inteira; perguntava uma nota só do acorde; pestana não preenchia o dedo nem avançava). Testar a ferramenta com acorde e pestana antes de entregar.

**Commits**: `9ba059ce` (ferramenta), `423b9011`, `b4461d45`, `7be3a880`, `561028ca` (correções), `9fa22548` (gabarito rotulado).

## 2026-10-12 — Mãos — M3: nota → dedo (esquerda)

Rodada completa: [`docs/rodadas/1004-dedo-por-visao.md`](../../docs/rodadas/1004-dedo-por-visao.md). Gabarito: [rodada 1003](../../docs/rodadas/1003-gabarito-de-dedos.md).

**Medido**: 53 notas na conta, 40 pisadas, mesmo gabarito para todos os métodos (sem conjunto separado). Acerto total (pisadas entre parênteses):

- `regra_posicao_janela_1` (só tablatura, base): 36/53 (23/40)
- `visao_ponta`: 42/53 (29/40)
- `visao_ponta_voto`: 43/53 (30/40)
- `visao_ou_regra`: 44/53 (31/40)

Calibração do braço (`data/saida/maos/m3/braco.json`): 6 cordas, rms 0,37 a 0,58 px; trastes 0 a 14 (13 de 14 achados); razão 0,949 contra 0,944 teórica; câmera fixa, deriva máxima 4,0 px.

**Ordem das cordas**: a primeira versão (brilho ao contrário) acertou 32/53. O erro apareceu num diagnóstico contra o gabarito. A correção vem da geometria (câmera frontal, mão por baixo do braço) e é conferida pelo brilho (90 a 176 da corda 1 à 6). Ela foi feita depois de ver o gabarito.

**Ressalvas**: um vídeo só; tudo escolhido no mesmo gabarito; câmera de braço frontal e fixa é caso favorável; direita fora de escopo.

**Commits**: `4183fe1e` (avaliador e linha de base), `18ff0890` (visão; gate 562 testes passando).

**Não repetir**:
- (a) brilho para ordenar cordas de NÁILON: os bordões revestidos são os mais claros, não as primas;
- (b) "um dedo por casa" como modelo único da esquerda: teto baixo (9 de 17 erros são formas de acorde);
- (c) entregar ferramenta de rótulo sem testar com acorde e pestana.

## 2026-10-12 — Mãos — M3: abrangência da visão (um vídeo só)

A calibração do braço usa **coordenadas fixas do retrato brasileiro** (não acha a câmera do braço). Medido sem rótulo em 30 vídeos sorteados: calibra em 2/20 do `sky guitar` e 0/10 de outros canais (conferido na imagem; 0 falso sucesso). Os 44/53 da rodada [1004](../../docs/rodadas/1004-dedo-por-visao.md) valem só para este vídeo. Próximo: achar a região do braço a partir da mão esquerda detectada.

**Não repetir**: revisar método de visão sem procurar coordenada fixa no código.

## 2026-10-12 — Mãos — M3: região do braço pelas pontas da mão (reprovada)

Região do braço derivada das pontas da mão esquerda, sem coordenada fixa: MVP igual (53/53 decisões idênticas), abrangência **0/30** (antes 2/30). A região cai em partitura, corpo ou mão. Código revertido; diff em `data/saida/maos/m3/abrangencia_v2/regiao_pelas_pontas.patch`. Detalhes na rodada [1004](../../docs/rodadas/1004-dedo-por-visao.md). Próximo: gabarito do braço (M3b, decisão [1003](../../docs/decisoes/1003-fases-das-maos.md)).

**Não repetir**: achar o braço só pela posição da mão (a mão pode estar sobre partitura ou corpo no quadro).

## 2026-10-12 — Mãos — M3b: gabarito do braço e geometria (dono)

Gabarito do braço do dono: 20 quadros, 8 canais (`data/gold/maos/braco.json`, rodada [1005](../../docs/rodadas/1005-gabarito-do-braco.md)). **Regra das 12 notas + ângulo da câmera (ideia do dono), medida nas marcações**: com nut + trastes 5 e 12 e modelo projetivo 1D, 96,0 % de 327 trastes previstos a < 1/4 de casa (afim: 65,4 %). **Detector por segmentos de reta (LSD) reprovado**: teste por canal (3 canais, 8 quadros) achou o braço em 1/8, trastes com número certo 1/147; a tablatura vira braço.

**Não repetir**: procurar o braço como "família de retas paralelas" no quadro inteiro (a tablatura e a pauta têm a mesma assinatura).

## 2026-10-12 — Mãos — M3c: braço calibrado pela música

Rodada [1006](../../docs/rodadas/1006-braco-calibrado-pela-musica.md). Homografia do braço ajustada por RANSAC só com (corda, casa, instante) do produto e as pontas da mão esquerda, sem linha da imagem. MVP: inliers 465/526; contra a calibração feita à mão, 0,119 casa de erro mediano (p90 0,241; corda 1 sistemática); dedo **40/53 (27/40)** com a calibração excluindo os instantes do gabarito (42/53 com todos; à mão: 42/53). H instável entre sementes (mediana 4–6 px). Próximo: estabilizar e medir fora do MVP contra o gabarito do braço.

## 2026-10-12 — Mãos — M3c: braço pela música estabilizado (adotado)

Rodada [1007](../../docs/rodadas/1007-braco-pela-musica-estabilizado.md). Consenso de 10 sementes + refino por reprojeção: grade estável (mediana 0,027 px entre execuções; 1,07 px sem os instantes do gabarito). **Dedo 42/53 (29/40) sem os instantes do gabarito**, igual à calibração feita à mão. Contra o gabarito do dono (q02): trastes 14/14 a < 1/4 de casa (0,032 casa), nut 0,036 casa; cordas ainda erram (0,11 do vão na corda 1). Correção das cordas pela imagem (janela por corda): não adotada, frágil.

**Não repetir**: procurar cada corda numa janela própria (as primas têm contraste fraco e a janela corta o pico); atribuir as 6 juntas por espaçamento.

## 2026-10-13 — Mãos — M3c: braço pela música fora do MVP (rodada 1008)

- Só q02 e q16 do gabarito do braço são medíveis: q06 e q11 têm 0 notas com tempo no produto; o q07 é de outra câmera (abertura).
- **q16**: estável (0,17 px) e errado: trastes **10/15** dentro de 1/4 de casa, nut **0,49** de casa, corda 1 a **0,35** do vão 1–6. Grade comprimida no sentido das cordas: a ponta do dedo fica ~1 passo para a corda 6 em relação ao contato (q02: ~0,3).
- **Não repetir**: recuo constante da ponta sobre o DIP. Escolhido no q02 = 0 (qualquer recuo piora o nut); o q16 melhoraria em 0,4–0,6. Os quadros discordam.

## 2026-10-13 — Mãos — M3c: correção do braço pela imagem em pente (rodada 1009, reprovada)

- Pente de 6 cordas (3 faixas) + trastes pela regra de 12 notas sob projetiva 1D, sobre a mediana da cena. Constantes fixadas antes; dev q02/q16, teste q21/q23.
- Piora: q16 trastes 10/15 → 2/15 e cordas 0,35 → 0,65; q21 cordas 0,14 → 0,42; q23 trastes 9/14 → 0/14 e nut 0,05 → 0,66. Cada metade (só cordas, só trastes) acerta num quadro e erra em outro.
- **Não repetir**: busca global de pente por perfil de linhas claras no layout do sky guitar sem critério de "não achou" (pega a borda do braço e o painel da mão direita).

## 2026-10-15 — Mãos — M8: corda sem a mão direita (rodada 1013)

Rodada: [`docs/rodadas/1013-m8-corda-sem-a-mao-direita.md`](../../docs/rodadas/1013-m8-corda-sem-a-mao-direita.md). Código `tab/maos_corda_sem_direita.py`; saída `data/saida/maos/m8/`. 4 vídeos do sky guitar, 2.437 notas (2.280 ambíguas pela altura), altura e gabarito tirados da tablatura do produto.

| degrau | acurácia de corda | erros |
| --- | --- | --- |
| D0 casa mais baixa | 0,860 | 341 |
| D1 decodificador (polifonia + continuidade, Viterbi), sem câmera | 0,883 | 285 |
| D2 + janela da mão esquerda pela câmera (só gabarito do braço) | 0,883 | 285 |
| D3 + janela dos vizinhos ± 2 (teto otimista, sem vazar) | 0,912 | 214 |

- Corda solta 690/690 em todos os degraus. Deixando um vídeo de fora: D1 0,888, D2 0,891, D3 0,915.
- D2 = D1 porque a câmera casa com o quadro do gabarito em 96/1.470 ataques com nota presa (6,5 %): a mão dentro do modelo derruba o NCC, e a câmera muda de plano. Onde existe, a janela contém a casa certa (93–100 %), mas tem 4,3–5,8 casas.
- D3: 130 erros com a casa certa dentro da janela (ambiguidade dentro da região da mão) e 66 de posição.
- Próximo: frentes de pesquisa em [`docs/pesquisa/maos-frentes.md`](../../docs/pesquisa/maos-frentes.md) (rastreio do braço, janela por dedo, timbre, custo aprendido).
- **Não repetir**: casar a câmera pelo braço com a mão dentro do modelo; janela da mão inteira [floor(min) − 1, ceil(max) + 1] para desempatar corda.

## 2026-10-16 — Mãos — Frentes da pesquisa: ondas 1 e 2 (rodadas 1101–1170)

Plano: [`docs/pesquisa/maos-frentes.md`](../../docs/pesquisa/maos-frentes.md) (seções 4.1 e 4.2). Cada frente rodou numa worktree com critérios congelados (CA1–CA7) e regras escritas antes da medida. **Nenhuma passou.** Os documentos das rodadas estão em `docs/rodadas/`. O código das frentes ficou só nos branches `maos/f0-residuo`, `maos/a3-custo-aprendido`, `maos/b1-janela-dedo`, `maos/c1-inarmonicidade` e `maos/d1-ligados`.

| rodada | frente | resultado contra o D1 do M8 (285 erros; ambíguas 1.995/2.280) |
| --- | --- | --- |
| 1101 | 0 — resíduo | "outros" 97/285 (34 %), acima do limite de 30 % |
| 1110 | A3 — custo aprendido (perceptron) | ambíguas −1,36 pp, 0 consertadas, 31 quebradas |
| 1111 | A1 — transição com `dt` | consertadas 9, quebradas 22 |
| 1112 | A2 — Minimax / L_p | consertadas 7, quebradas 40 |
| 1130 | B1 — janela por célula do dedo | contém 92,3 % e 94,1 % (piso 95 %) |
| 1131 | B1b — D2 com grade fixa, pontas no som | 243 erros (+1,84 pp, saldo 42); reprova no CA3: lacrimosa −0,72 pp |
| 1150 | C1 — β separa cordas | inconclusiva: 0 pares com 8 notas por lado; inclinação log β × casa 0,94 do esperado |
| 1151 | C1b — β com máscara de parciais | parou no controle sintético sobreposto (161 kb/s: 99/117) |
| 1170 | D1 — ligados na mesma corda | sem efeito: só 0,6 % dos intervalos ≤ 0,5 s |

- **Único sinal positivo: a janela da mão esquerda com a grade fixa do quadro do dono, sem o teste de câmera.** Diagnóstico do revisor (`data/saida/maos/m8/d2_fixo.py`): 285 → 242 erros, cobertura 99 %, +1,9 pp nas ambíguas, saldo 43. Com as pontas no som (1131), 243. Reprova no CA3 nas duas versões, cada vez por um vídeo diferente: glimpse −0,63 pp com as pontas no `t_ini`, lacrimosa −0,72 pp com as pontas no som (3 a 4 notas). Próximo passo: confirmação fora da amostra (rodada 1014), em vídeos novos do sky guitar com o mesmo método e os mesmos limiares.
- Corrige o "não repetir" da 1013: a janela da mão inteira **desempata**, desde que cubra o vídeo (grade fixa). O problema da 1013 era a cobertura de 6,5 %. O que sobra são 207 erros com a casa certa dentro da janela.
- Frentes fechadas: A (o decodificador só com a sequência de notas não melhora), D (sem nota onde atuar) e C (sem amostra nos 4 vídeos).
- **Não repetir** (detalhes nas rodadas):
  - perceptron com φ somado por sequência e η = 0,1;
  - Minimax como estimador do que foi tocado;
  - escolher `p` ou a escala de `dt` com 3 vídeos de treino;
  - célula de 10–20 % do vão do traste como janela;
  - excluir a nota inteira por "ainda soa" de 2 s (derruba ~95 % das medidas);
  - "ainda soa" com o `t_ini` de ataques seguidos e janela de 0,5 s;
  - ligado restrito à corda anterior sem limite de casa;
  - "sem ataque no áudio" como rótulo de ligado (0/8);
  - trocar `t_ini` por `t_audio` sem separar os 170 ataques sem casamento.

## 2026-10-16 — Mãos — M9: confirmação fora da amostra da janela fixa (rodada 1014)

[`docs/rodadas/1014-m9-confirmacao-janela-fixa.md`](../../docs/rodadas/1014-m9-confirmacao-janela-fixa.md). Regras e CA3 (opção b, do dono) gravados antes da medida; quadros q32–q36 marcados pelo dono.

- **Reprovou.** 6 vídeos novos do sky guitar: 153 → 146 erros, +0,57 pp nas ambíguas (mínimo +1,0), saldo 7 (mínimo 20); ganho só em 2 dos 4 vídeos grandes. Nos 4 de trabalho o ganho segue 285 → 242. **A janela fixa não entra no produto; a referência continua o D1 do M8.**
- Diagnóstico: o erro que sobra é quase todo **"previu corda solta onde a nota é presa"** (118/242 nos de trabalho, 122/146 nos novos; 101/102 no no surprises). A janela da mão esquerda não atua nesse erro porque a corda solta não depende da posição da mão.
- Hipótese pós-hoc, não testada: penalizar a solta quando a janela contém a alternativa presa. Só com regras novas e vídeos não olhados.
- **Não repetir**: tratar o ganho da janela fixa nos 4 vídeos de trabalho como efeito geral (não se repetiu fora da amostra).

## 2026-10-16 — Mãos — nova direção: base de treino das mãos (decisão 1006)

Decisão do dono: a trilha das mãos **grava as mãos de cada nota** (base de treino) e não tenta mais adivinhar a corda pela mão. A tablatura da tela é o rótulo; as mãos, o braço e o som são a entrada. Plano: [`docs/guias/plano-dataset-maos.md`](../../docs/guias/plano-dataset-maos.md); decisão: [`1006`](../../docs/decisoes/1006-maos-viram-base-de-treino.md).

- Fases: M10 esquema e regras → M11 braço quadro a quadro (a peça que falta) → M12 mãos quadro a quadro → M13 tempo do som (trilha do áudio) → M14 associação e auditoria do dono (≤ 2 associações falsas em 100 eventos ouro, proposta) → M15 piloto de 20 vídeos do sky guitar e rollout → M16 modelo, depois.
- Regras centrais: nada da entrada é calculado com o gabarito; associação pelo `t_audio`, não pelo marcador (o som vem 165–275 ms depois); caixa da tablatura guardada para mascarar; cru + confiança + nível (ouro/prata/recusado), nunca exclusão calada.
- O D1 do M8 (88 % da corda do professor) fica como linha de base do modelo futuro.
- **Não repetir**: reabrir as ondas de regra para adivinhar a corda pela mão.

## 2026-10-17 — Mãos — M11a: braço rastreado do quadro-chave (rodada 1015): reprova no CA2

- O dono marcou q37–q66 (teste, 6 canais) e as partes do violão em todos os 66 quadros (decisão [1008](../../docs/decisoes/1008-partes-do-violao-no-gabarito-do-braco.md)).
- O rastreador (`tab.maos_braco_rastreio`: ORB 5000, Lowe 0,8, RANSAC, "não achei" por inliers, reprojeção e determinante) foi congelado no sky guitar e medido uma vez:
  - **0 falsos em 30** (a grade fixa tem 18);
  - ⊥ mediano de **0,17 vão** contra 1,10 da grade fixa;
  - mas só **8 de 11 "achei" certos** (CA2 pede 95 %) e cobertura de **11/30**.
- Causa da cobertura zero em kenneth, shin izumi e iwaki (câmera aberta): os 5000 pontos do alvo vão para a tablatura. No braço caem 0, 19 e 1 pontos; buscando só no braço, são 2919, 3472 e 1654.
- Próximo:
  - nova rodada com a busca restrita a uma região e quadros de teste novos;
  - medir a variação do próprio dono ao remarcar, porque os imprecisos ficaram em 0,27–0,35 vão, perto do limite de 0,25.
- **Não repetir**: ajustar o rastreador num canal só, com o braço em close, e esperar que ele passe em câmera aberta.

## Mãos — 2026-10-21 — braço: estado consolidado (rodadas 1016–1036, decisões 1009 e 1010)

Estas rodadas estavam só nos documentos de rodada. Esta seção junta o estado, e o detalhe está
em `docs/rodadas/10NN-*`.

- **Como o braço é feito hoje (decisão 1009, ciclo de revisão).**
  - Estágio 1: localizador do braço, `L3_todos_s*`, que acha 4 pontos.
  - Estágio 2: U-Net na faixa retificada, `A4_100_todos_s*`, que dá cordas, trastes e nut.
  - Decodificação conjunta, regra de revisão da 1023 (S1/S2) e sinal de nut suspeito v2 da
    1033 (bordas do quadro e linhas de painel, 2 %).
  - O dono confere só os sinalizados, em `tab.maos_braco_gabarito servir`. A CLI do ciclo é
    `python -m tab.maos_braco_ciclo {sortear,escolher-pesos,prever,medir} --rodada N`.
- **Ciclos medidos contra o dono:**
  - 1026 (sky guitar): 92 % certos sem revisão, 0 falsos que passam;
  - 1029 (pablo romé): 54/60 certos e 4/63 falsos que passam, todos com o nut fora da
    imagem: o 1º traste é tomado por nut, e a numeração desloca 1 casa;
  - 1032 (kenneth): 63/64 certos e 0 falsos, medido **antes** da regra do capo;
  - 1036 (violaodecria, cortes verticais): 1/32 falso que passa e 22/32 sinalizados.
- **Capo é o nut (decisão 1010, 2026-10-20).**
  - Com capo, o gabarito numera os trastes a partir do traste à frente do capo, e `k` marca o
    capo. A casa do capo fica na observação, e `python -m tab.maos_braco_capo` junta as casas
    por vídeo: 33 vídeos, 0 conflitos.
  - O dono remarcou 125 quadros com capo em 7 gabaritos.
  - Com a regra nova, a 1032 dá **16/64 certos e 46 falsos que passam**: o detector acha o nut
    verdadeiro atrás do capo. **O detector atual não serve para vídeo com capo até o
    retreino.**
- **Nut fora da imagem, sem capo:** os vizinhos (V), a junção (J) e o A5 (1031) reprovaram, e
  as marcações do braço (1034 e 1035) também. O que protege hoje é o sinal v2: ele pega 5 dos 6
  falsos antigos e manda o quadro para revisão.
- **Pedido da trilha áudio** (decisão 2005, triangulação): uma camada por quadro com (corda,
  casa) pressionada e corda atacada, com probabilidade calibrada, e uma saída que não dependa
  do `t_audio`. Entra quando o M11 (braço) e o M12 (mãos) existirem.
- **Não repetir**: medir o detector com a regra do capo usando pesos treinados com a regra
  antiga (o capo vira erro silencioso).
- **Retreino com capo (1037, 2026-10-21): reprova; o par antigo continua.**
  - O par escolhido (`L4_capo_s2` + `A6_capo_s1`) passa na segurança (0/32 na M36, 1/21 no
    N), mas acerta só 2 quadros com capo (o antigo, 6) e 5 sem capo (o antigo, 15).
  - Causa: a semente 2 do estágio 1 **inverte o braço** e põe o nut na boca do violão. Ela
    sinaliza quase tudo, e o critério da 1029 ("menos falsos que passam" primeiro) a escolheu.
  - Os outros 6 pares (sementes 1 e 3) são sãos: com capo, 1–2 falsos que passam (o antigo,
    4) e 6–9 certos (o antigo, 6); sem capo, 12–15 certos (o antigo, 15). Nenhum passa os três
    critérios: o melhor perde no critério 3 por 1 quadro.
  - **Calibração (2005):** sem capo, o S1 do par antigo é honesto (161 de 165 certos entre os
    entregues sem sinal, nos ciclos 1026–1036); com capo, é cego (6 de 63).
- **1040 (numerar sem o nut pela régua de casas): reprova**, 82,7 % contra 95 %.
- **1039 (ciclo de capo, shin izumi)**: 64 quadros de 8 vídeos com capo, previstos com o par
  antigo, esperando a revisão do dono.
- **1041 (capo sobreamostrado 3×, escolha com piso): o critério 3 reprova** (sem capo, 9
  certos contra 15 do antigo, na M36 + N).
  - O piso barrou a semente que sinaliza tudo, mas o par escolhido (L5 s2 + A7 s2) **inverte
    o braço em 7 de 28 quadros verticais da M36** (o antigo, em 0).
  - Os critérios 1 e 2 saem na 1039, depois da revisão do dono. O melhor caso agora é "só
    com capo, dependendo da 1038".
- **Próximo:** investigar a orientação do braço no estágio 1. Uma semente em três inverte (na
  1037 e na 1041), e a folha de escolha precisa de vídeo vertical.

### 2026-10-22 — a 1039 revisada: o capo nas casas 4 e 5 ainda engana

- **A 1039 revisada pelo dono** (64 quadros, todos com capo, casas 2 a 5):
  - par antigo: 0 certos e **39 falsos que passam** (61 %), com o nut no nut verdadeiro;
  - par da 1041 (L5 s2 + A7 s2): 9 certos e **15 falsos que passam** (23 %). **Critérios 1 e 2
    reprovam.**
- **Por tipo de erro**: com capo nas casas 2 e 3, o par da 1041 põe o nut no capo (32 de 40).
  Com capo na casa 4, volta ao nut verdadeiro (14 de 16) e **12 passam sem sinal**. O treino
  tinha ~13 quadros com capo na casa 4 e 1 na casa 5: é cobertura.
- **Próximo**: a 1042 (as 64 marcas da 1039 no treino; veto de inversão na escolha, pela M36)
  e a 1043 (lote novo, 5 vídeos com capo do kimny's guitar, 40 quadros) como prova lacrada.
- A ferramenta do braço escondia o quadro atrás do cabeçalho em tela pequena (corrigido em
  `dda828da`).

### 2026-10-23 — a 1042 reprova na 1043: retreinar canal a canal não generaliza o capo

- **1042** (as 64 marcas da 1039 no treino, veto de inversão): na 1043 (kimny's guitar, 40
  quadros, 39 com capo, canal nunca visto) entrega 1 certo e **2 falsos que passam**; o par da
  1041, 1 e 1. Critério 2 reprova; o 3 já reprovava no N (9 certos contra 12). Não adotado.
- **O erro é o mesmo da 1039**: o nut vai para o nut verdadeiro (17 de 39) ou para o capo (7).
  Nos dois pares, quase tudo vem sinalizado (37 e 38 de 40): seguro, mas sem uso.
- **Próximo** (combinado com o dono): a 1044, sem retreino: validadores físicos, várias
  tentativas (9 pares, giro e espelho) e **um violão por tomada** com o capo pela conta. Depois,
  se faltar, retreino com sintético com capo e um backbone pré-treinado.
- **1046 (capo pelo Grounding DINO tiny, sem treino): para no desenvolvimento.** O melhor
  texto acha 18 de 64 capos da 1039 com ≤ 2 % de falsos; as caixas cobrem 75–99 % do quadro
  (o violão inteiro), então nem esses são acerto. A 1043 não foi medida.
- **1044 (validadores físicos + 22 hipóteses + tomada, sem retreino)**, na M44 (8 canais, 36
  medidos): **0 falsos que passam contra 4** da referência, mas 10 certos contra 18 (o
  mínimo era 22). Critérios 1 e 3 passam, o 2 reprova. A tomada (S4b) com 5 quadros por
  vídeo tirou 6 certos. Só registro: sem a tomada, 18 certos e 0 falsos; precisa de um lote
  lacrado novo para confirmar.
- **1047 (a cadeia da 1044 sem a tomada, lote lacrado de 8 canais): passa nos três
  critérios.** 20 certos e **0 falsos que passam**, contra 18 e 3 do par antigo. Vira a cadeia
  do ciclo sem capo (`python -m tab.maos.braco.validadores_gpu preencher --rodada N`).
- **Próximo:** a 1045, o capo como uma 5ª saída do estágio 2 (pontos `k` do dono), com o nut
  pela conta da 1046.

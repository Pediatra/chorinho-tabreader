# Estado — Áudio

Seções movidas inteiras do [`ESTADO.md`](../../ESTADO.md) na decisão 9001
(fase 5), na mesma ordem. Seção nova desta trilha entra no fim deste arquivo.

## Áudio — 2026-10-13 — A0: áudio em cache e sincronia (rodada 2001)

- `tab/audio_extrair.py`: FLAC mono 16 bits 22 050 Hz em `/cache/audio/`, chave do censo; `indice_de`/`instante_de` convertem o PTS do vídeo em amostra.
- **`t_amostra0` = 1º frame de áudio decodificado**, não o `start_time`: com Opus o `start_time` erra **~7 ms** (pré-salto). Teste sintético de clique: erro ≤ 1,1 ms em PCM/AAC/Opus, áudio deslocado 0 e 0,5 s.
- 20 vídeos (2 por canal, 10 canais): **20 de 20** extraídos, **Opus em 20 de 20**, deslocamento áudio−vídeo **0 ms em 20 de 20**, nenhum buraco que mude a duração; 1,7 s por vídeo (mediana), 82 MB de FLAC por hora. Projeção (estimativa): ~2,2 h de HD e ~24 GB para 2.998 vídeos.
- **Não repetir**: usar o `start_time` do stream de áudio como instante da amostra 0 (−7 ms em todo o acervo Opus).

## Áudio — 2026-10-13 — A1: atraso marcador → som no MVP (rodada 2002)

- `tab/audio_onsets.py` (STFT 2048/256 a 22 050 Hz, fluxo espectral) e `tab/audio_atraso.py`: 636 eventos de coluna do MVP, ataque mais próximo em janela de meia-distância (teto ±0,30 s), 2 passadas.
- **O marcador vem ANTES do som**: Δ = t_som − t_marcador, fluxo, passada 2: ataque em **636 de 636**, mediana **139 ms**, p10 60, p90 268. Sem capotraste (transposição pela música: k = 0).
- **Degrau, não deriva**: mediana por exibição 79–125 ms até ~448 s (10 exibições) e 164–277 ms depois (12 exibições), inclusive na 2ª exibição de telas já vistas. Causa não medida.
- Viés do detector no sintético: −28 ms (pico antes do ataque); o fluxo nas alturas não separa 1 semitom com N_FFT 2048 (razão 0,98). Os dois testes ficam `xfail` estrito com o número.
- **Não repetir**: usar `t_marcador + atraso fixo` como verdade de tempo do som neste vídeo (degrau de ~110 ms e dispersão de 60–100 ms).

## Áudio — 2026-10-13 — A1b: o "degrau" de 448 s não é degrau (rodada 2003)

- **Corrige a seção A1 acima**: não há degrau único. Descartados por medição: troca de observador, andamento diferente (razão som/marcador **1,0017** em 614 intervalos), pausa só na troca 6→7 (a mediana das 21 trocas é −36 ms) e corte de edição (o único pico de imagem em 444–453 s é a troca de página; o áudio não tem descontinuidade).
- O Δ é quase constante dentro de cada página, mas o nível **vagueia** de 60 a 324 ms ao longo do vídeo (13 mudanças > 50 ms, 7 para cima e 6 para baixo), e nota a nota a diferença de intervalos tem **desvio padrão 90 ms**: o marcador anda na grade do software; o violonista toca com rubato.
- Escuta do dono: o clique no ataque detectado cai junto com as notas.
- **Não repetir**: régua de tempo do som como `t_marcador + atraso` (A3 do contexto). O marcador dá a coluna e a janela (±0,3 s); o tempo fino vem do áudio, e a verdade de som tem de ser conferida pelo dono.

## Áudio — 2026-10-13 — A2: alinhador sem marcador, v1 e v2 (rodada 2004)

- `tab/audio_alinhar.py`: casa as colunas de cada exibição a picos de ataque por programação dinâmica (alturas esperadas × "nova energia" + andamento), com o marcador escondido.
- **v2** (trecho contínuo com início e fim livres + andamento iterativo), MVP, régua = ataques do A1: **591 de 636** a ≤ 50 ms (fluxo ou alturas), **3 falsos de 636 (0,47 %)**, 7 recusas; trecho igual ao da régua em 19 de 22 exibições. v1 (página inteira): 10 falsos.
- Cada exibição do MVP toca um **trecho contínuo** da página (repetições e casas de volta); forçar a página inteira gerava 7 dos 10 falsos da v1.
- **Não repetir**: DTW de passo padrão sobre o perfil de alturas (14 de 636 a ≤ 100 ms); alinhar a página inteira em cada exibição.

## Áudio — 2026-10-13 — folha 1: primeiro gabarito de tempo do som, por escuta (rodada 2005)

- `data/gold/audio/folha1.json` (26 clipes, aprovado pelo dono): MVP com régua concordante **4 de 4** certos; os **3 "falsos" pela régua do A1 estavam certos** (erro da régua); colunas que o marcador nunca acende: 2 de 4 erradas (tela 2, cols 17–18); sem marcador (iwaki, kimny, shin izumi): **8 certos, 1 errado, 3 não sei em 12**.
- A régua do A3 passa a ser o gabarito de escuta. Próximo conserto: coluna sem ataque (ligadura/ornamento) não pode receber tempo.
- **Não repetir**: controle errado deslocado para onde há coluna recusada vizinha (o clique caiu numa nota real; f03).

## Áudio — 2026-10-13 — colunas que o marcador não acende são ornamentos; v3 reprovada (rodada 2006)

- No MVP, as 10 colunas com nota que o marcador nunca acende são **notas pequenas de ornamento sob arco** (mordente 2–3–2, deslize), vistas nos recortes. Às vezes soam com ataque (f21 certo), às vezes não (f20, f26 errados).
- Regra por proxy (corda 1 + nota única + ≤ 1,75 passo): 6 de 10 ornamentos e 0 de 400 colunas acesas no MVP, mas no gabarito do dono **recusa 2 "certos"** (f06, f21) e não resolve o f11. **Reprovada e desfeita.**
- Pedido à trilha tablatura: marcar ornamento (tamanho do glifo) e arco no produto (`docs/decisoes/2002-ornamento-no-produto.md`).
- **Não repetir**: adivinhar ornamento por geometria de coluna (corda/nota única/distância).

## Áudio — 2026-10-13 — folha 2: vídeos sem marcador; a escuta separa coluna, não ms (rodada 2007)

- `data/gold/audio/folha2.json` (30 clipes, aprovado pelo dono): afirmadas do alinhador v2 nos 3 vídeos sem marcador, **23 de 27 certos, 0 errados, 4 não sei**.
- **Controles não detectados: 0 de 3** (clique a 226–244 ms das notas, sem ataque a < 80 ms, ouvido "certo"). Com a folha 1: 1 de 4. "Certo" em folha de clique único = **coluna certa**, não ±50 ms (vale também para a folha 1).
- A5 proposto: `docs/decisoes/2003-tempo-do-audio-no-produto.md`. Arquivo irmão `chorinho/audio@1` por (tela, exibição, coluna), com recusas e motivo e `afericao.nivel = "coluna"`; sem mexer no `chorinho/video@1`.
- **Não repetir**: tratar "certo" de folha de clique único como precisão de tempo. Próximo formato: comparação A/B com deslocamentos de 50/100/200 ms.
- **Adendo (q21–q23, sky guitar, marcados pelo dono)**: q21 14/14 trastes, nut 0,30, cordas 0,14/0,06; q23 9/14, nut 0,05, cordas 0,06/0,15; q22 instável (85 px entre conjuntos) porque as notas ficam quase todas nas casas 2 e 4. Robustez: nota com casa > 14 é pulada e contada; semente com H inválida é descartada. **Não repetir**: confiar na calibração pela música sem conferir a cobertura de casas e a estabilidade entre conjuntos.

## Áudio — 2026-10-13 — folha 3 A/B: o tempo do áudio está a ~100 ms (rodada 2008)

- `data/gold/audio/folha3.json` (40 pares, aprovado pelo dono): o dono escolheu o clique do alinhador contra um deslocado em **10 de 10** com 200 ms (2 "não sei") e **9 de 11** com 100 ms; com 50 ms, **7 de 12 "não sei"**. Não há tendência de cedo ou tarde.
- `chorinho/audio@1` (`tab/audio_produto.py`, commit `b6da3b38`): arquivo irmão por (tela, exibição, coluna), validado nos 4 produtos (MVP 645/699 colunas com tempo; iwaki 245/273; kimny 158/222; shin izumi 114/552). Aferição agora `nivel = "ms"`, `resolucao_escuta_ms = 100`.
- **Não repetir**: deslocamento (controle ou par A/B) que cai a menos de |d| + 50 ms de uma coluna vizinha, afirmada ou não. No shin izumi, p21 e p24 caíram em outra nota.
- Abaixo de ~50 ms, o ouvido não separa: a medição tem de ser com áudio sintético.

## Áudio — 2026-10-13 — A4: o shin izumi falha porque o produto perde a corda 1 (rodada 2009)

- 23 de 42 exibições recusadas, todas por "poucas colunas casadas", mas com cosseno **alto** (0,83). Descartados por medição: casas > 7 (as recusadas têm menos), afinação (transposição 0 é a melhor: 114 afirmadas, contra 0–8 nas outras) e densidade de notas (10 candidatos/s nos dois grupos).
- Causa apoiada: o produto do shin izumi tem só **4 % das notas na corda 1** (42 de 998), contra 17–27 % nos outros vídeos. Nos recortes, as telas 12 e 25 perdem as notas da corda 1, e na 25 pausas viram notas. Pedido à trilha tablatura (via dono).
- Exibição recusada com cosseno alto é **alarme de leitura** (colunas faltando).

## Áudio — 2026-10-13 — A4: alinhador em 10 vídeos sem marcador (rodada 2010)

- 10 de 10 rodaram sem erro (37 min): **2799 de 4531 colunas com tempo (62 %)**, 64 de 184 exibições recusadas. **6 de 10 bons** (77–97 % das colunas: iwaki ×2, kimny ×2, shin izumi *dream is a wish*, paolo d'angelo).
- Falhas olhadas no recorte: **guitarous sakura 0 de 62**, porque o produto lê tudo uma corda abaixo (pedido à trilha tablatura); **transcriptor campanitas 201 de 935**, por ser rasgueado com batidas abafadas "X" (limite do método, a leitura está certa). Giant steps e charagua não olhados.
- **Recusa da calibração pela música** (`tab/maos_braco_fora.py::avaliar_confianca`, campo `confianca` no medicao.json): ≥ 5 casas com ≥ 5 notas, vão ≥ 5 casas, estabilidade entre conjuntos ≤ 2 px. Recusa o q22 (três motivos); aceita q02, q16, q21, q23. **O q16 passa e é ruim** (nut 0,49, 10/15): o critério pega instabilidade e pouca cobertura, não o viés da ponta do dedo. Limiares escolhidos depois de ver o q22, ainda não validados.

## Áudio — 2026-10-13 — alarme de leitura no arquivo de áudio (rodada 2011)

- `chorinho/audio@1` ganha, por exibição, `cos_medio`, `n_casadas` e `alarme_leitura`: recusada com cos ≥ 0,7. Nos 14 vídeos: 0–2 alarmes nos 9 bons; 7–21 nos 4 fracos.
- Das telas com alarme olhadas na imagem, **5 de 6 têm leitura com falhas**: colunas faltando, cordas deslocadas, números de dois algarismos e acordes em elipse. A sexta é rasgueado com leitura certa.

## Áudio — 2026-10-13 — rasgueado: colunas abafadas no alinhador v2.1 (rodada 2012)

- Coluna abafada = ≥ 4 `nao_notas` `tecnica` em cordas distintas, sem nota e com ≥ 4 de top-1 "15". Campanitas: 122. Nos 9 vídeos bons: 0. Recortes confirmam pilhas de X.
- v2.1: as abafadas entram como ataque sem altura. Nos 9 bons a saída é **idêntica à v2 (4131 de 4131 colunas)**. Campanitas: notas com tempo 201 → **268 de 935**, alarmes 21 → 17, 12 exibições marcadas `rasgueado` (alarme desligado). Não conferido de ouvido.
- **Não repetir**: regra de 3 cordas `tecnica` para X (pega acordes de números e ornamentos em 3 vídeos bons).

## Áudio — 2026-10-13 — campanitas: os 17 alarmes restantes; pedidos consolidados à tablatura (rodada 2013, decisão 2004)

- Causas: 3 de 17 do método (setas de rasgueado sem X), 3 de 17 de leitura, 2 de 17 outras (painel na partitura; uma sem causa), 9 de 17 não olhadas. **14 de 17 têm página gêmea aceita**, e 38 × 20 têm sequências idênticas no produto: o alinhador casa 1 coluna numa passagem e 5 na outra. Hipótese: o alinhador escolhe trecho mínimo quando há mais ataques que colunas. Não provado.
- `docs/decisoes/2004-pedidos-de-leitura-a-trilha-tablatura.md`: 9 pedidos de leitura com evidência e as telas com alarme por vídeo, para o dono repassar.

## Áudio — 2026-10-13 — campanitas descartado pelo dono

- O dono tirou o transcriptor *campanitas* (Ernesto Cavour) do dataset, por não atender aos padrões dele. A folha 4 não entra no gabarito. As rodadas 2012 e 2013 ficam como registro; o v2.1 não muda os outros 13 vídeos.

## Áudio — 2026-10-13 — por que o alinhador fica com trecho curto (rodada 2014)

- Medição sem mudar código, em 6 exibições recusadas (room 335 e giant steps) e 4 boas. O DP perde o caminho que cobre a página por causa do termo de andamento (3 casos) ou do custo de coluna sem ataque (3). Afrouxar λ aceita até 5 de 6, mas muda 10 a 15 de 112 colunas boas em mais de 30 ms. **Alinhador fica como está**; a causa é leitura com colunas faltando (decisão 2004).
- Achado: 8 dos 42 alarmes de leitura vêm de trecho escolhido todo na margem de 0,5 s fora da página (casou a página vizinha). Proposta: o alarme ignorar esses casos. Ainda não feito.

## Áudio — 2026-10-13 — alarme de leitura ignora trecho fora da página (rodada 2014)

- `tab.audio_produto`: nova chave `fora_da_pagina` por exibição (trecho escolhido inteiro na margem de 0,5 s). O alarme não dispara nesses casos. Nos 13 vídeos: alarmes **42 → 34**, colunas iguais 5342 de 5342. Lista de telas da decisão 2004 atualizada.

## Áudio — 2026-10-13 — andamento com lacunas: não adotado (rodada 2015)

- Variante do termo de andamento que aceita buracos de 2T e 3T (κ por coluna perdida). Em nenhum κ os 6 casos da rodada 2014 passam. Com κ = 0,1, 3 exibições a mais passam, mas 69 de 3760 colunas boas mudam em mais de 30 ms; nenhum dos 72 itens do gabarito muda. **Alinhador fica v2.1**; o conserto é a leitura (decisão 2004).

## Áudio — 2026-10-13 — lote 2: 12 canais novos (rodada 2016)

- 12 de 12 vídeos rodaram sem erro; **2292 de 4587 colunas com tempo (50 %)**. 5 vídeos bons (74–98 %), 5 no meio, 2 falham por causa da entrada: kenneth acoustic é padrão de ritmo sem casa; vvxofingerstyletab tem 1 tela de 90 s (troca de página não detectada).
- Som × marcador (3 canais com `t_ini`): tirado o atraso fixo do canal (−115 a +178 ms), 77–95 % das colunas ficam a ≤ 100 ms. O produto leu marcador em só 3 de 12 canais marcados. Pedidos 10–12 na decisão 2004.

## Áudio — 2026-10-20 — regressão do alinhador com o leitor `rede` (rodada 2017)

- 15 vídeos com número antigo, produto gerado de novo (leitor `rede`, CPU) e alinhador v2.1 sem mudança. Determinismo do produto conferido (2 execuções iguais).
- 14 vídeos bons: colunas com tempo **4707/5666 (0,831) → 5337/6220 (0,858)**; *room 335* 114/552 → 357/603. Colunas presentes nos dois: **4516 de 4648 (97,2 %) a ≤ 30 ms**. Som × marcador: queda máxima 1,6 pp. Gabarito de escuta: 37 de 40 pontos certos mantidos, 1 recusado, 2 fora (104 e 116 ms).
- **Critério 1 reprovado em 2 de 14** (*michelle* −2,9 pp, *bach prelude* −2,6 pp), e as causas são de leitura, vistas no quadro: o acorde final que o `rede` passa a ler encurta o trecho no *ritardando* (limite da rodada 2014); o `rede` junta "2·3" em "23" (casa errada); o `rede` perde "10" na corda 1 do *room 335* e lê ornamento como coluna. Pedidos 13 e 14 na decisão 2004.
- **Não repetir**: comparar fração de colunas com tempo entre leitores sem olhar o denominador: a leitura nova muda as colunas (acorde final, algarismos juntados), e a fração cai sem o alinhador mudar.

## Áudio — 2026-10-21 — transcritor livre Basic Pitch (rodada 2018): reprova

- O transcritor ouve o áudio sozinho, sem ver a tela, e foi comparado com o gabarito de tablatura do dono pela física (corda solta + casa + capo). Imagem própria `chorinho-som:dev` (Python 3.10, Basic Pitch 0.4.0, numpy 1.26.4). É determinístico e leva ~3,5 min por vídeo em CPU.
- Prova com 7 vídeos e 2.196 notas, mais o gabarito novo de acorde cheio do dono (`data/gold/audio/acordes_2018.json`: 4 telas e 22 acordes de 5–6 cordas).
- **Com o corte de amplitude da emenda 1 (0,50)**: revocação **1.355/2.196 = 0,617** (C1 reprova), precisão 0,803, acorde cheio mediana 0,367 (C3 reprova) e escuta **30/31 a ≤ 100 ms**. **Cru**: revocação 0,794, precisão 0,591, acorde 0,667 e escuta 30/31.
- Nenhuma faixa de confiança chega a precisão ≥ 0,90 com revocação ≥ 0,50. Próximo candidato: o MuScriptor, que espera duas decisões do dono (licença CC BY-NC e login no Hugging Face).
- **Não repetir**: corte absoluto de confiança escolhido num vídeo de desenvolvimento quase só melódico (o *retrato*) e aplicado a vídeos de acordes. Ele apaga as notas internas do acorde: na prova, a coluna de 3 notas caiu de 0,709 para 0,511.

## Áudio — 2026-10-21 — transcritor de violão do Riley (rodada 2019): passa

- Pesos MIT (`xavriley/midi-transcription-models`, `guitar-fl.pth`, procedência em `artefatos/riley_guitar.md`), sem ajuste, na imagem `chorinho-som:dev` (torch CPU). É determinístico e roda a 1,65 vez o tempo real.
- Prova da 2018 (7 vídeos, 2.196 notas): revocação **1.766/2.196 = 0,804** (6 de 7 vídeos ≥ 0,70), precisão **0,877**, acorde cheio mediana **4/6** (28 colunas), escuta **30/31** e controle 0,138. **Passa**, com C1 e C3 no limite.
- Diferença para o Basic Pitch cru: quase a mesma revocação (0,794), e precisão muito maior (0,591 → 0,877).
- É a fonte "som" da triangulação (decisão 2005). A olhar: o *charagua* tem 8 vezes mais notas no som que na tela; o *end of beginning* fica em 0,673.

## Áudio — 2026-10-21 — cruzamento tela × som (rodada 2020): K1 passa só na soma, K2 reprova

- Cada nota da tela (leitor `rede`) recebe um veredito do som do Riley (`tab.cruzar_fontes`). Ele é medido contra o gabarito do dono em 2.906 notas.
- **K1** (erradas entre as confirmadas): **14/2.409 = 0,58 %** na soma, o que **passa**. Mas a amostra fora do treino do leitor dá **7/184 = 3,8 %**. Das 7, 4 parecem deslize no gabarito do *paolo* (a tela e o som dizem casa 3), e o dono vai rever. As outras 3 são setas de rasgueado lidas como "4", "confirmadas" pela repetição do acorde. Por isso o `confirma` não promove nota a ouro até a rodada na T8.2.
- **K2** (erros acusados): **7/21 = 33 %**, **reprova**. A precisão do alarme é 7/497 = 1,4 %.
- **Não repetir**: usar "o som não confirma" como alarme de erro da tela, porque o som perde nota de verdade (490 das 497 não confirmadas estão certas). E não pôr critério na soma de uma amostra dentro do treino com outra fora: a de dentro domina.


## Áudio — 2026-10-22 — correção do dono no `acordes_2018` e a 2020 refeita

- O dono corrigiu na ferramenta a corda 2 dos rasgueados do fim da tela 1 (*paolo*): 0 → 3,
  como a tela mostra (0 3 0 2 3). O cruzamento tela × som tinha apontado essas notas.
- Ficou uma nota repetida no 4º rasgueado (`d3`: corda 2, casa 3, posta pelo dono em cima da
  `m23`). Ela espera o dono apagar na ferramenta; o agente não grava no ouro.
- **2020 refeita com o gabarito corrigido** (`data/saida/audio/r2020/medida.json`, que foi
  sobrescrita): fora do treino, K1 = **3/184 = 1,6 %** (as 3 setas de rasgueado do
  *charagua*); somadas, K1 = 10/2.409 = 0,42 % e K2 = 7/17 = 41 % (ainda reprova). A leitura
  da rodada não muda: o `confirma` não promove nota até a rodada na T8.2.

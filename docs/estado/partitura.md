# Estado — Partitura

Seções movidas inteiras do [`ESTADO.md`](../../ESTADO.md) na decisão 9001
(fase 5), na mesma ordem. Seção nova desta trilha entra no fim deste arquivo.

## Partitura — 2026-10-13 — P0: quantos vídeos têm pauta (rodada 3001)

- Amostra de 436 vídeos (até 30 por canal, semente 0) × 12 quadros do cache, com o detector geométrico `tab/partitura_pauta.py`, conferida nas folhas de miniaturas `data/saida/partitura/p0/folhas/`.
- **≈ 1.455 dos 2.998 vídeos ativos têm pauta (49 %)**; 220/436 na amostra, já descontados 2 vídeos falsos e somado 1 perdido. Canais: sky guitar, robert lunn, guitar dell'arte, iwaki, pablo romé, serge kottelat, transcriptor, paolo d'angelo, tv on guitar (quase todos os vídeos); guitarous 4/30; os demais 0.
- **Pauta sem tab praticamente não existe** (5 vídeos na amostra, e era tab não marcada pelo censo). A partitura vem junto da tablatura.
- Conferência: positivos 66/68 certos; nos negativos, 15/110 quadros têm pauta visível, mas só 1 vídeo muda de classe.
- Adendo (rodada 6, detector refinado para a Gymnopédie e barras de colcheia): 21 quadros ganhos, 0 perdidos, mesmo número de vídeos.
- **Não repetir**: (1) limite de espessura medido na sequência inteira de linhas de pixel: a 6ª linha borrada da tab e a chave ao lado da pauta engrossam a sequência (a 1ª rodada deu 2.188 vídeos, inflada por tab lida como pauta); medir no núcleo (≥ 50 % do pico). (2) máscara de polaridade clara sem teste de crista: acha o fundo branco entre as linhas da tab como "linhas". (3) subir o limite de espessura sem exigir espessura parecida: barra de colcheia (5 a 6 px) vira 6ª linha falsa.

## Partitura — 2026-10-13 — P1: qual biblioteca lê a pauta (rodada 3002)

- 21 recortes reais de pauta; R01–R12 medidos contra a tab do gabarito convertida em altura (546 notas, 3 vídeos). CPU, sem treino.
- **Audiveris com ampliação 2x: 479/546 notas certas (87,7 %), 4 inventadas**, saída em 20/21 recortes, 13 s por recorte. homr: 467/546, 23 inventadas, 21/21, 8,5 s. Audiveris sem ampliar: 388/546. oemer: falha (0/2, 8 min cada).
- Greensleeves 106/106 nas duas. No south american, 14 erros do Audiveris são fá# lido como fá em recortes sem clave e sem armadura na tela (a partitura rola): herdar clave e armadura do vídeo.
- **Base para a P2: Audiveris x2**; homr como segunda opinião. A medida é de altura, não de ritmo.
- **Não repetir**: (1) comparar MusicXML do Audiveris sem aplicar `clef-octave-change` (clave de sol com 8): a altura sai uma oitava abaixo (R05 dava 8/85, é 73/85). (2) oemer neste acervo: falha em todos os recortes testados, ~8 min e 5,6 GB cada.

## Partitura — 2026-10-14 — comparativo: variantes do Audiveris e SMT sem treino (rodada 3003)

- R01–R12 (546 notas da tab), mesma régua: **Audiveris x2 com margem 7/7: 491/546, 3 inventadas, 70/83 compassos cheios** (x2 com margem 4/6: 479, 67/83). homr: 467, 23 inventadas, 44/78.
- Ampliar 3x/4x piora (417/270); binarizar quebra 4 recortes (196); colar clave e armadura do início do sistema não ajuda (466).
- SMT sem treino (4 dos 7 pesos públicos rodaram; 3 sem pesos ou com acesso fechado): o melhor acerta 20/546, os outros 0. São pesos de piano, fora do domínio; o SMT só entra treinado (P2).
- Ferramenta de conferência (`tab.partitura_gabarito servir`, porta 8099) pronta; o dono ainda não gravou nada em `data/gold/partitura/`.
- **Não repetir**: (1) ampliar além de 2x para o Audiveris. (2) binarizar por Otsu antes do Audiveris. (3) pesos antoniorv6/SMT com o código `master`: o decoder carrega aleatório e só avisa ("newly initialized"); usar o commit d25acd4.

## Partitura — 2026-10-14 — gabarito do dono: o que o Audiveris erra (rodada 3004)

- O dono conferiu os 21 recortes (`data/gold/partitura/leitura_p1.json`). Dos 873 símbolos lidos, **852 estão certos (97,6 %)**: 7 com figura errada, 4 com altura errada e 10 que não existem. Há **78 notas faltando**.
- O ritmo do que é lido está certo em ~99 % dos símbolos. O gargalo é a cobertura (notas que faltam) e a armadura que não aparece no recorte (R06).
- Recomendação: não treinar o SMT agora. Primeiro juntar homr + Audiveris, completar pela tab e herdar a armadura. A decisão é do dono.
- **Não repetir**: tratar a altura do gabarito como altura soada. O dono confere contra o desenho: sem armadura na tela, um F#4 sai como F4 "certo".

## Partitura — 2026-10-14 — homr completando o Audiveris (rodada 3005)

- A união cega das leituras recupera **31 das 74** notas faltando, mas acrescenta 164 notas (~133 sem clique do dono). Na tab de R01–R12: certas 491→520, **inventadas 3→43**.
- 43 das 74 faltando não aparecem em nenhuma das duas leituras. Filtrar pela tab zeraria as inventadas, mas isso é pareamento (P3): só com aviso do dono.
- **Não repetir**: juntar homr e Audiveris sem filtro, seja completando acordes (14/102 casam), seja com eventos só do homr (17/62).

## Partitura — 2026-10-14 — P3 liberada: homr confirmado pela tab (rodada 3006)

- O dono liberou a P3 em 2026-10-14. Primeiro passo: a nota do homr só entra se a tab tem a mesma altura no evento casado. Resultado em R01–R12: **certas 491→523/546 (95,8 %), inventadas continuam 3**.
- 23 notas continuam sem leitura nenhuma: a altura vem da tab, mas a figura não tem fonte. A figura das 32 recuperadas vem do homr e não foi conferida.
- R20: a segunda metade não foi lida, e o dono não marcou faltando. O gabarito do R20 vale só para os símbolos lidos.
- Armadura herdada (rodada 3007): aplicando a armadura do R05 à leitura sem clave, R06 sobe de 79 para 81/88 e R07 de 88 para 89/96 (R07 sem altura errada). Falta tirar a armadura automaticamente do quadro do vídeo onde a clave aparece.
- Recorte (rodada 3008): conjunto de barras de colcheia, mais grosso que 1,5 entrelinha, deixa de contar como vizinho. Com isso, R21 e R14 deixam de cortar a parte de cima; as outras 19 caixas não mudam. `recortes_margem/` foi mantido, porque o gabarito usa as coordenadas dele.

## Partitura — 2026-10-14 — armadura do vídeo automática (rodada 3009)

- `python -m tab.partitura_omr herdar`: a armadura vem da maioria das leituras do mesmo vídeo que têm clave e é aplicada às leituras sem clave. R01–R12: **491 → 494/546**, inventadas continuam 3.
- No R06, as 5 alturas que sobram são bemóis inventados pelo Audiveris (compassos 7 e 11). O dono marcou essas notas como certas na conferência: rever o R06 na próxima rodada de conferência, sem mexer no gabarito por conta própria.

## Partitura — 2026-10-14 — P3: pareamento partitura × tab (rodada 3010)

- `python -m tab.partitura_pareamento`: o pareamento por sequência põe **325 de 326 pares no mesmo x do quadro** (mediana de 0,5 a 2,7 px, R01–R12).
- O tempo da partitura é o `t_ini` da coluna pareada. Hoje ele sai vazio: nem o gabarito de tab nem a saída `fase8/medida` desses vídeos têm `t_ini` por nota. Depende da trilha tablatura.

## Partitura — 2026-10-14 — saída única da partitura (rodada 3011)

- `python -m tab.partitura_pareamento` agora faz leitura com armadura do vídeo + notas do homr confirmadas pela tab + pareamento. R01–R12: **526/546 certas (96,3 %)**. As notas erradas continuam 14 (as inventadas sobem de 3 para 8 só por troca de categoria). São 336 de 337 pares no mesmo x.

## Partitura — 2026-10-15 — troca de altura desmentida pela tab (rodada 3012)

- Quando o homr completa um evento com nota que a tab confirma, a nota do Audiveris que a tab desmente sai para `trocadas`. R01–R12: certas seguem **526/546**, notas erradas caem de **14 para 8** (inventadas 8 → 3). 5 das 6 trocas são os bemóis inventados do R06.

## Partitura — 2026-10-15 — harmônico não é troca (rodada 3013)

- A troca do R11 (3012) era um harmônico artificial: a pauta desenha a nota presa e a tab escreve o som, uma oitava acima. Nota igual à da tab em outra oitava não é mais trocada. R01–R12: **526/546 certas**, 9 notas erradas (uma é o próprio harmônico), 5 trocas (os bemóis do R06).

## Partitura — 2026-10-15 — pareada com o produto, em todas as telas (rodada 3014)

- `tab.partitura_video` (`recortar`, `ler`, `parear`) gera `<stem>.partitura.json` (`chorinho/partitura@1`) para cada produto: 19/19 telas com pauta nos 3 vídeos. Nas 12 telas da P1, pareada com o produto: **527/546** (era 526 com o gabarito). Nas 7 telas novas do gymnopédie: 196/221. Gym tela 10: a tab do produto tem as cordas deslocadas de uma e o x denuncia (0 de 14 conferidos), um erro da trilha tablatura.

## Partitura — 2026-10-15 — armadura, compassos e x de reserva (rodada 3015)

- O `<stem>.partitura.json` ganha `fifths`, `fifths_origem` e `compassos` por pauta, e `metodo` (`altura` ou `x`) em cada par. Quando o x desmente o par pela altura, o evento pega a coluna livre mais próxima a até uma entrelinha: Gym tela 10 vai de 0 para 10 de 14 pares conferidos; total 433 de 438. Notas certas iguais (723/767). Gym tela 12 tem `fifths` 1, provavelmente errado; `fracao` só na primeira pauta de cada vídeo.

## Partitura — 2026-10-18 — documento final por vídeo com a nota que a tab tem (rodadas 3026, 3027)

- **Tamanho da pauta causa a perda** (3026): 30 pautas grandes reduzidas a 11 px caem de 925/925 para 855/925 notas certas achadas (0,924). Mediana de 15 quadros na pauta pequena não recupera nada (1376 → 1323 certas, extras 73 → 116). Só resolução de verdade ajuda.
- **P4** (3027): `tab.partitura_video parear` completa a pauta com a nota da tab que a pauta não leu (`origem` `tab_completada`, figura `null`) e marca `pauta_pequena` (< 16 px) e `leitura_ok` por pauta. A nota não entra se houver pausa na mesma voz, se estiver no cabeçalho ou se houver conflito de oitava. Nos 3 vídeos: 66 candidatas, 50 entram, 16 ficam fora. 442 eventos existentes idênticos.
- **Contra a tab do gabarito do dono**: fora da tela 10 da Gymnopédie, 12 de 22 completadas estão certas; na tela 10, 2 de 28. A completada vale o que vale a tab do produto naquele ponto, e as duas fontes erram nos mesmos lugares. Tratar como sugestão.

## Partitura — 2026-10-18 — onda 1 das frentes fechada (rodadas 3101–3103, 3110, 3160–3162, 3170–3172, 3026)

- **D1, gabarito sorteado** (40 vídeos, 13 canais; 35 conferidos pelo dono, `leitura_d1.json`): **certos/lidos 0,962**, **certos/(certos+faltando) 0,906**, 0 altura errada; 5 de 40 recortes sem leitura do Audiveris. Confirma o P1 (0,976 e 0,916): o Audiveris quase não inventa; falta cobertura. guitar dell'arte e pablo romé são os piores (0,84). Ver 3162.
- **F0, régua**: as marcas do Audiveris (`abnormal`, duração do compasso) avisam em 14 de 49 compassos com nota faltando (29 %); `expected="1"` do `.omr` é falta de fórmula, não duração (decisão: tratar como sem duração esperada daqui para frente). Troca pelo homr em R01–R12: 3 consertadas, 0 quebradas. Tempo pelo par: 217/438 eventos; as 4 inversões são da partitura. Ver 3101–3103.
- **E1, completar pela tab**: 56 notas completadas; o dono avaliou os trechos como "praticamente tudo errada" sem marcar nota a nota, e a olhada da sessão achou 19/21 figuras batendo (conflito não resolvido; desenho da conferência provavelmente enganou). **Decisão: nota completada entra com altura e instante da tab e figura `null`.** Nos produtos, 14 de 37 completadas herdam erro da tab. Ver 3170–3172.
- **A1, imagem limpa**: nenhuma variante passa de 25/36 (meta 30/36); a moldura recupera 2 e quebra 1. Não adotada. Ver 3110.
- **Qualidade da imagem** (59 recortes dos três gabaritos): pauta ≥ 16 px cobre 0,934, menor que isso 0,87–0,89; precisão igual em todas as faixas; tela carregada (tinta) acompanha a perda (Spearman −0,29). Correlação, não causa; teste causal proposto (reduzir pauta grande e reler). Ver 3026.
- Ferramenta de conferência: imagem dos recortes da frente D, id com acento, e `paginar` com pauta na borda de baixo do quadro corrigidos.
- **Não repetir**: (1) agente de frente numa pasta copiada sem git, container e ffmpeg (travou a onda); a worktree com `host-spawn` resolve. (2) sorteio "proporcional" lido só nos canais pequenos (kimny's guitar com 22 de 40 vagas e ~4 vídeos com pauta). (3) conferência de "só a figura" desenhando só as notas a julgar.

## Partitura — 2026-10-15 — homr troca o compasso em vídeo sem produto (rodada 3025)

- Regra adotada: no compasso em que o homr lê ≥ 2× as notas do Audiveris, entra o compasso do homr, com as notas marcadas `homr_sem_confirmacao` (`trocar_compassos_pelo_homr`). A leitura do Audiveris fica guardada. `ler --pasta` agora roda o homr também (160/162 ok). Nos 11 vídeos do piloto: **30 compassos trocados em 17 recortes** (11 no amores hallaras, 10 no blackbird). No athletic P01a, a troca recupera 25, inventa 8 e **perde 2** notas certas do Audiveris. Conferência do dono na porta 8097, gabarito `data/gold/partitura/compassos_homr.json`. Ver `docs/rodadas/3025-homr-troca-compasso-sem-produto.md`.

## Partitura — 2026-10-15 — o homr nas notas que faltam, sem tablatura (rodada 3024)

- Regra por compasso: aceitar o homr onde ele tem pelo menos 2× as notas do Audiveris. Resultado: 25/40 recuperadas e 8 inventadas sem produto; 5/50 e 2 no gabarito antigo (14 recortes comparáveis). É o caso de voz inteira perdida (athletic, R08, R19). Nota solta em acorde não se resolve assim. Proposta para o dono: trocar o compasso, marcando a nota como "sem confirmação". Ver `docs/rodadas/3024-homr-nas-notas-que-faltam.md`.

## Partitura — 2026-10-15 — gabarito do dono sem produto: Audiveris em 3 recortes (rodada 3023)

- Dos símbolos lidos, **98,9%** estão certos (176/178): 0 altura errada, 0 figura errada, 2 inexistentes. A cobertura é **81,5%** (40 notas faltando, 31 delas no athletic P01a, onde o Audiveris descartou a voz de cima dos compassos 3–4). Clave e armadura certas nos 3. A ferramenta agora grava o `--itens` servido em `fonte_itens`. Ver `docs/rodadas/3023-gabarito-sem-produto.md`.

## Partitura — 2026-10-15 — fileira de vigas não corta mais o topo do recorte (rodada 3022)

- Estrutura horizontal só limita o recorte se cobrir pelo menos 60% da sua extensão (`COBERTURA_MIN_VIZINHA`). Vigas cobrem 24–32%, linha de pestana ~55%, linha de verdade 94–100%. Caixas mudam em 40/162 recortes sem produto, 0/19 de produto e 1/21 do gabarito (R16, que não foi refeito). Nos 40 recortes, os eventos foram de 668 para 742, com o mesmo Audiveris ok (30). Ver `docs/rodadas/3022-viga-nao-corta-o-recorte.md`.

## Partitura — 2026-10-15 — piloto sem produto: 11 vídeos lidos (rodada 3021)

- `ler --pasta` nos 11 vídeos do piloto: Audiveris ok em **143/162** recortes, 3.641 eventos. As 19 falhas são "No system found". A faixa amarela do cursor explica a maioria: com faixa, 12/36 falham (33%); sem faixa, 7/126 (6%). O mela concentra 16 falhas. A regra de armadura da 3020 não mudou nada nos 8 novos. Ver `docs/rodadas/3021-piloto-sem-produto-11-videos.md`.

## Partitura — 2026-10-15 — armadura do vídeo também para leitura com clave e sem armadura (rodada 3020)

- `herdar_condicao` aplica a armadura do vídeo quando a leitura não tem clave **ou** não tem `<key>`. Gabarito R01–R21 idêntico; 3 produtos sem mudança; canon P06a None→2 (5 notas F→F#). Ver `docs/rodadas/3020-armadura-herdada-com-clave.md`.

## Partitura — 2026-10-15 — `ler --pasta`: partitura de vídeo sem produto (rodada 3019)

- `python -m tab.partitura_video ler --pasta <sem_produto/slug>` (imagem `chorinho-partitura:dev`) roda só o Audiveris nos recortes do `paginar` e grava `<slug>.partitura.json`: pautas com página, exibições, armadura, compassos e eventos, **sem par e sem tempo em segundos** (o tempo só vem da tab).
- Piloto: agua 10/10 (403 eventos), athletic 7/8 (301), canon 6/6 (112); ~18 s por recorte em CPU.
- Qualidade **não medida** (sem gabarito). Visto: canon P01a leu 5 de 16 notas; canon P06a perdeu a armadura de 2♯. Ver `docs/rodadas/3019-ler-pasta-sem-produto.md`.

## Partitura — 2026-10-15 — pauta com uma linha apagada ganha a 5ª linha (rodada 3018)

- Linha cinza e borrada some na abertura e sobram 4. O detector agora completa a 5ª linha no meio ou na borda, se ela for crista no cinza; 6 linhas = tablatura, descartada.
- Censo (436 vídeos, mesma amostra da 3001): **18 quadros ganharam pauta, 0 perderam**, 9 ganharam mais uma pauta. Dos 27, 25 são pautas reais, 1 é tablatura que o `paginar` descarta, 1 é falso (leonardo ramos).
- Validação 4/4, 3/3, 12/12, caixas idênticas. Piloto: mela 30→41 recortes; free tab 14→12 páginas (sem página partida), 23 recortes.
- O `paginar` também passa a ler o quadro com mais pautas de cada página. Ver `docs/rodadas/3018-quinta-linha-que-falta.md`.

## Partitura — 2026-10-15 — paginar resiste a destaque colorido e tira a tablatura (rodada 3017)

- Tinta passou a ser contraste com o fundo local (top-hat). Quando só o destaque amarelo ou rosa anda, a diferença caiu de até 0,74 para ≤ 0,06; troca real de página fica em 0,49–0,55.
- A tablatura confundida com pauta é descartada pela 6ª linha, medida no 2º pior de 10 trechos da largura: tablaturas ≥ 0,88, pautas reais ≤ 0,65 (antes as vigas tiravam 7 pautas reais).
- Validação: 4/4, 3/3 e 12/12, caixas idênticas às do produto.
- Piloto de 11 vídeos: canon 16→6 e beam 21→6 páginas em relação à 1ª tentativa; nenhuma pauta real descartada.
- **Ainda perde pauta sob destaque em página corrida** (mela, free tab): é o próximo passo. Faixa que rola fica como limite. Ver `docs/rodadas/3017-paginas-com-destaque-e-tab.md`.

## Partitura — 2026-10-15 — páginas de pauta sem o produto da tab (rodada 3016)

- `python -m tab.partitura_video paginar --video` acha as páginas de pauta direto do vídeo (1 quadro/s, assinatura da região das pautas, trechos estáveis, repetições juntadas). Nos 3 vídeos com produto: **19 de 19 telas** achadas, caixas idênticas às do produto, sem página sobrando, ~25 s por vídeo. Saída em `data/saida/partitura/sem_produto/`.


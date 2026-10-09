# HISTÓRICO — consolidação das rodadas 1 a 65

O projeto transcreve, de vídeos-aula, a tablatura de violão que aparece na tela em JSON por vídeo (corda, casa, técnica, compasso e instante), com geometria determinística + classificador de ~74 mil parâmetros treinado só em dado sintético.
Este documento é o histórico consolidado das rodadas: substitui a leitura dos 65 arquivos soltos em `docs/` (a rodada 1 é o `docs/decisao_modelo.md`; as demais são `rodadaN_*.md`).
**Os 65 originais foram removidos do disco na reestruturação e continuam recuperáveis no git** (`git show de1fcca:docs/rodada10_gabarito_ampliado.md`) — este resumo não é a única cópia.
Cobre 65 rodadas (rodada 1 + rodadas 2 a 65), de 2026-10-08, e preserva os números exatamente como os documentos os registram.

## Tabela cronológica

| rodada | o que foi testado | número medido (antes → depois) | decisão |
| --- | --- | --- | --- |
| 1 | escolha de modelo: GOT-OCR2.0 (580 M) × geometria + CNN pequena; cursor; grade | GOT **0 de 15** algarismos na linha com gabarito; CNN com rótulos prata 0,88 (canais vistos) / 0,64 (2 canais novos); 161/163 recortes com 6 cordas; cursor em 99,9 % dos quadros; 6.882 glifos válidos | pipeline próprio de duas camadas: geometria determinística + classificador de **74.382 parâmetros** em sintético; **sem VLM** |
| 2 | tempo do cursor contra o pipeline antigo; binarização nas 5 famílias; correção do acorde | diferença mediana **−0,159 s** (máx. 0,195); cascata 5/5 e 24/24 (Otsu 3/5 e 24/24; contraste local 1/5 e **0/24**); `tup` l.1: 110 glifos/44 % centrados → 152/85 %/33 colunas; acervo 6.882 → **11.594 glifos** | cascata Otsu → contraste k=21 → k=31; fatiar por corda; tempo validado (offset 0,16 s → ~0,03 s) |
| 3 | inventário do acervo real (319 vídeos, 12 canais); remoção de corda mutilando glifos | 96 % com tablatura e 95 % com cursor; 3.781 vídeos/190 GB; ffmpeg 140 × OpenCV 179; amostras 741 → **1.072**; treino 0,82 → **0,94**; canais novos 0,67 → **0,70**; passo 14,8–36,3 px | painel em 3 faixas (a posição não é fixa); fallback ffmpeg; remover runs longos só nas linhas da corda |
| 4 | filtro de margem (iwaki: 1ª barline em x=623); início do gabarito verificado | 11.780 glifos; **506 (4,3 %)** seriam apagados; **60 de 163** linhas afetadas; iwaki 19 → **27** glifos; `tup` l.1 107 → **127**; gabarito **42** glifos (iwaki 27 + sky 15) | rótulo `TAB` reconhecido por **forma** (largura > 0,95 passo, ≥3 cordas), não por posição |
| 5 | gerador sintético; diagnóstico do baixo acerto | 12.352 glifos de 300 linhas, 19 classes; treino **0,58**; razão glifos/nota **1,44** (959 notas, 1.380 glifos, 1.257 casados) | implementar agrupamento em **token** (mesma corda, Δx < 0,25 passo) |
| 6 | tokenização | 11.780 glifos → **9.123 tokens**; treino 0,58 → **0,985**; iwaki **27/27 = 1,00**; sky **14/15 = 0,93**; total **41/42 = 0,976** (prata 0,63–0,70) | tokens passam a ser a unidade de classificação |
| 7 | 1ª transcrição ponta a ponta (skyguitar l.1) | **14/15 = 0,933**; 15 tokens; tempos 1,84 / 8,81 / 15,85 s | falta classe de rejeição + verificação de forma |
| 8 | verificação de forma (harmonico ≥2 comp. ou ≥1,2 passo; 1 dígito ≤1,15 passo; 2 dígitos ≥0,85 passo) | 14/15 = 0,933 → **15/15 = 1,000**; **1 de 15** corrigido pela forma | manter; `reconhecer.py` com barlines e confiança por nota |
| 9 | aferição em quadro de vídeo real (iwaki, tema escuro, tab embaixo) | 15/15 + 27/27 = **42/42 = 1,000**; confiança média **0,958** | o gargalo muda do modelo para o **gabarito** |
| 10 | gabarito ampliado com raman korshun (casas 4–7, slides) | 42 → **66 glifos**; 4 → **9 classes**; raman **12/24 = 0,50**; total **54/66 = 0,818** | faltam classe de rejeição e separar a marca de técnica do token |
| 11 | compasso e andamento no JSON | compassos **4/4/4/3**; 59,9 notas/min; intervalo mediano 1,001 s | BPM só em campo de suposição (`bpm_se_1_nota_por_tempo`), separado do medido |
| 12 | regra de altura para casa de 2 dígitos (≥0,5 passo) no extrator | 54/66 = 0,818 → **0,818**; raman 12/24 → 12/24 (erro virou `24` → `2`) | mantida por inofensiva, mas **não resolve** |
| 13 | regra de orientação (coluna com traço ≥60 % da altura) no extrator | 54/66 = 0,818 → **0,818**; raman 12/24 | o erro é do gerador, não do extrator: corrigir o dado |
| 14 | desenhar a barra diagonal do slide no gerador | iwaki 27/27 → **23/27 (0,85)**; sky 15/15 → **9/15 (0,60)**; raman 12/24 → 11/24; total 0,818 → **0,652 (−0,166)** | **revertida** |
| 15 | gabarito com paolo d'angelo (passo 16 px) | 66 → **96 glifos**; 3 → **4 canais**; paolo **23/30 = 0,77**; total **77/96 = 0,802**; raman erros `junk→1`, `junk→8`, `7→15` | no gerador, **sortear** entre buraco na corda e corda por cima |
| 16 | buraco na corda sorteado (metade/metade) | paolo 23/30 → **28/30 = 0,93**; total 0,802 → **0,854 (+0,052)**; erros `1→4` de 3 para 2 | manter: somar variedade em vez de trocar forma |
| 17 | colher a classe `junk` das sobras do sintético | 19 classes e **`junk` ausente**; 82/96 = **0,854** inalterado; patch da linha 134 nunca executado | desenhar o lixo **de propósito** no gerador |
| 18 | traços verticais rotulados `junk` | 19 classes e `junk` ausente; 0,854; 30 linhas: 937 notas, 888 tokens, **3 sem par** | desenhar o lixo nos **vãos entre colunas** |
| 19 | lixo nos vãos entre colunas | 19 classes e `junk` ausente; 0,854; traço de 2 px sobrevive a 16 px (limiar 1,1) e é descartado a 30 px (limiar 2,1) | desenhar **barra dupla** e medir tokens sem par **antes** de treinar |
| 20 | mesmo código rodado 2× (variância do treino) | 0,854 (sky 0,67, raman 0,75, paolo 0,90) × **0,729** (sky 0,27, raman 0,75, paolo 0,83); variação **0,125** no total e **0,40** num canal | fixar a semente do PyTorch; **≥3 execuções**, média e amplitude |
| 21 | semente fixa (`--seed`) e 3 sementes | sementes 0/1/2 = 0,781 / 0,802 / 0,833 → **média 0,805, amplitude 0,052**; sky **9/15 nas três** (regressão) | número oficial passa a **0,805**; remover o gancho `junk` |
| 22 | com `junk` × sem `junk` (3 sementes) | média **0,805 = 0,805**; com: raman 18,3/24, sky 9/15, paolo 26,7/30; sem: raman 12/24, sky 13/15, paolo 27/30; amplitudes 0,052 × 0,104 | ficar **sem** `junk`: é troca entre canais, não ganho |
| 23 | ponta a ponta em 3 canais fora do gabarito | shin izumi 38 notas/7 compassos/passo 22,0; serge kottelat 91/5/15,0; cifra club 58/10/16,6 | pré-requisito do rollout cumprido; **acurácia não medida** nesses canais |
| 24 | `tools/transcrever.py`: vídeo → JSON (shin izumi, via ffmpeg) | 76 notas; 10 barlines; notas por compasso `{1:12, 4:5, 8:26, 9:33}`; passo 21,6 px; **tempo ausente** | barline robusta é o elo frágil; medir cobertura do cursor |
| 25 | cursor em 24 vídeos (quadro a 40 % da duração) | painel **24/24 = 100 %**; cursor **9/24 = 38 %** (inventário dizia 95 %) | erro de medição (janela fixa de 40 s × 40 % da duração): refazer alinhado |
| 26 | cursor com janela iniciando no quadro do painel | painel 24/24 = 100 %; cursor **12/24 = 50 %**; 0 % em paolo/shin/tv on guitar, 100 % em raman/tv cifras/violaodecria | ler como **intermitência**; varrer o vídeo por janelas ativas |
| 27 | varredura de janelas (`varrer_cursor`) no shin izumi | 57 notas; 12 barlines; `janelas_com_cursor` = **[]** e **0 s** de 150 s varridos | tempo é cobertura por canal, não código; o JSON passa a **avisar** onde não há |
| 28 | cobertura de tempo (2 vídeos/canal, 120 s por vídeo) | painel 24/24 = 100 %; **13/24 = 54 %** com alguma janela; média **56,4 s**; ~**104 s de 120 s (≈87 %)** dentro dos vídeos com cursor; guitar dell'arte 113,0, shin izumi 119,5, guitarous 119,5, serge 104,2, paolo 59,8, tv cifras 59,5, sky 56,0, violaodecria 45,5, iwaki/raman/tv on guitar/cifra club 0 | ~54 % dos vídeos com cursor; ~46 % precisam de outra fonte (áudio/manual) |
| 29 | rollout em 5 vídeos de 5 canais | **323 notas**, todas com tempo; guitar dell'arte 30, serge 7, shin izumi 145/24 compassos, violaodecria 7, sky guitar 134 | contar instantes distintos; escolher trecho por densidade; barline robusta |
| 30 | contagem de instantes distintos nos 5 JSONs | guitar_del_0 30 notas/**1** instante; serge 7/**1**; shin 145/**8**; sky 134/**3**; violaodecria 7/**1** | implementar tempo por **travessia**; os 323 tempos não são utilizáveis |
| 31 | tempo por travessia de x(t) | patamar 36 notas/**3** instantes → travessia 36/**5**; janela com só 4 s de cursor | transcrever por **sistema**, não por janela arbitrária |
| 32 | `passagens()` por sistema | **57 passagens** (ruído); melhor passagem 0–4 s, x 96–1181; **2 de 36** notas; **1** instante distinto | olhar o quadro: o sinal detectado pode não ser um cursor |
| 33 | verificação visual do "cursor" no quadro | caixa sobre o **corpo do violão**: 149 px, matiz **16** (laranja), saturação 85 (cursor real do skyguitar: matiz **109**, núcleo 15–22 px) | rodar o detector só no painel; exigir assinatura (estreita, vertical, matiz de playback) |
| 34 | trava de assinatura (largura ≤6 % e matiz 85–140) | inventário **95 % → 12 % (3/24)**; a varredura de 54 % fica invalidada; painel 24/24 = 100 % | cobertura real desconhecida; refazer a varredura (12 % não é comparável ao 54 %) |
| 35 | correção do usuário: o marcador nem sempre é faixa; medição no cifra club | 74 tokens, passo 14,8; tokens coloridos 51/44/41/33/50/53 em 6 instantes; matizes 10–20 | **série temporal de cor por token** como máquina única (faixa, cor ou nada) |
| 36 | série de cor por token (fração cromática) | **45 dos 74** tokens variam >0,5; variação mediana **0,59**; em t=0,46 quase todos vão a 0,00 | normalizar por instante (o sinal medido é global) |
| 37 | normalizar por quadro (token − mediana do quadro) | **17 a 25** outliers por instante (mediana do quadro 0,10–0,83) | a cor é de **voz**: trocar quantidade por categoria de cor |
| 38 | categoria de cor por token contra a própria base | base vermelho **48**, sem-cor **26**; **6–15** tokens mudam por instante, sem padrão que avance; colunas 7 e 22 em quase todos | olhar um quadro com as caixas desenhadas (não achei o marcador) |
| 39 | imagem do cifra club com as caixas dos "tokens" | caixas sobre as **cordas do braço**: "66–74 tokens" são corda/trastes/marcadores | portão de **fundo uniforme**; o braço tem 6 cordas e engana o detector |
| 40 | vídeo indicado pelo usuário (a banda — chico buarque, 2220×1080) | tab em **y ≈ 500–890**; letra em y ≈ 890–1010; marcador **branco → laranja** (t=0,45 laranja; 0,44 e 0,46 branco) | rodar a série de cor na região certa; fundo uniforme como portão |
| 41 | segmentar na região correta (y 490–900) | otsu 12,4 % tinta/0,70/4 picos; k=21 13,8 %/0,81/3; k=31 11,0 %/0,72/2; **0 linhas e 0 tokens**; tab ~x 40–1500 de 2220 | detectar o painel por uniformidade; suavização menor; largura parcial |
| 42 | 3 sub-regiões candidatas por estimativa | y540–700: 8 %/1 pico/0 linhas; y560–720: 3 %/0/0; y500–760: 16 %/5/0; y480–660: platô de 68–70 % em ~80 px | parar de escolher y por chute: **variância local** |
| 43 | uniformidade de fundo | 5 faixas de altura **41**; cordas em y ≈ 643/688/732/776/820/864, passo **≈44 px**; no painel 3 % de tinta e **0 picos > 0,30** (cobertura ~0,33 × limiar 0,30) | recortar x ao painel (40–1500) e baixar o limiar 0,30 → 0,15 |
| 44 | máscara de tinta **mais clara** que o fundo | delta 8: 5,1 % tinta/0,44/**6 picos**/espaçamento 44; delta 12: 4,6 %/0,40/6/44; delta 18: 4,0 %/0,38/6/44 | adicionar a variante "tinta clara" e usar a faixa uniforme como entrada |
| 45 | máscara clara ligada no código | **6 linhas** `[24, 68, 112, 156, 200, 245]`; passo **44,2 px**; máscara `contraste_claro_k21_d12`; **41 tokens** (1:3, 2:13, 3:10, 4:7, 5:4, 6:4) | rodar a série de cor nos 41 tokens |
| 46 | teste de cor em 13 instantes (0,440–0,500) | **0 tokens laranja em todos**, contra a imagem que mostra laranja | conferir a máscara numa imagem (contradição registrada, causa não isolada) |
| 47 | medir a cor real dentro das caixas e baixar o limiar de 45 % para 20 % | tokens laranja: 1 / **7** / **13** / 2 / 3 / 6; H ≈ 11–12, S ≈ 235, V ≈ 217 | o marcador por cor **funciona** (avanço 1 → 7 → 13 colunas, cumulativo); converter em `t_ini`/`t_fim` |
| 48 | JSON por nota de um canal de cor (`cifra_abanda.json`) | 41 tokens, **39 (95 %) com tempo**; acorde de 4 notas em x=89 com o mesmo intervalo 66,0–70,8 s | alargar a janela; declarar o mecanismo; matar o vazamento de `harmonico` |
| 49 | janela de observação de ~21 s | **41/41** com tempo; duração mediana **9,1 s** (mín 0,0, máx 20,8); **16 "frases" em 24 amostras** | `t_fim` **não é duração**: é o próximo onset; endurecer o detector de frase |
| 50 | onset por nota com semântica correta | **41/41** onsets; **8 instantes distintos**; onsets 63,3 · 65,1 · 66,9 · 67,8 · 68,7 · 69,6 · 74,1 · 78,7; intervalo mediano **1,80 s**; reinícios 0 | gravar `t_ini` e `t_proxima`, nunca "duração" |
| 51 | origem do `harmonico` no JSON do cifra club | tokens de **17 px/1 componente** com p=0,84 e 0,58; a regra exige ≥2 comp. ou ≥1,2 passo (**53 px**) e rejeita; veio do script ad-hoc da rodada 46 (`argmax`) | usar sempre `reconhecer_linha`; investigar a extração (hipótese) |
| 52 | hipótese de fragmentação da extração (±0,15 / ±0,08 / ±0,05 passo) | **idêntico nos três**: 57 glifos, 17 px, **0,38 passo** (skyguitar: 17–18 px = 0,6 passo) | hipótese **derrubada**; variar o tamanho da fonte no gerador |
| 53 | fonte sorteada entre 0,55 e 1,0 do passo | 0: 0,844; 1: 0,823; 2: 0,885; média **0,805 → 0,851**; iwaki **27/27** e sky **15/15** nas três; raman 11–13/24 | manter: 2ª vez que mexer no gerador move o número (a visão deu 0 ou −0,166) |
| 54 | trava de largura mínima 0,22 passo e leitura do teto do gabarito | raman: **70 de 94 (74 %)** tokens com ≥2 comp.; erros 11 de 24 (9 de 11 com ≥2); **85/96 = 0,885** bruto; **85/89 = 0,955** alcançável; raman sem `junk` 13/17 = 0,76 | trava é segurança, não ganho; separar a marca do algarismo antes de classificar |
| 55 | medir o fenômeno no sintético × no canal real | sintético: 683 tokens, 117 notas com técnica, 293 com ≥2 comp., **22 com técnica fundida (3,2 %)**; real: 94 tokens, **70 (74 %)** com ≥2 comp. | desenhar a marca cruzando o algarismo e rotular o token fundido como `tecnica` |
| 56 | portão de medição antes de treinar | 683 tokens; 293 (**42,9 %**) com ≥2 comp.; **22 (3,2 %)** receberiam `tecnica`; limiar 10 % → **não treinou**; 9 de 23 notas com técnica (39 %) fundidas | consertar o patch (não aplicou) e aumentar a fração de notas com técnica |
| 57 | quebrei o `sintetico.py` (IndentationError linha 286) e consertei | 683 tokens; **22 (3,2 %)**; limiar 10 % → não treinar; `ast.parse` OK, `import` OK | editar com a indentação do bloco e verificar `ast.parse` + `import` na mesma rodada |
| 58 | patch correto: diagonal atravessando em 80 % das notas com técnica | 740 tokens; **24 (3,2 %)** `tecnica`; limiar 10 % → **não treinar** | medir fração de notas com técnica × taxa de fusão antes de qualquer treino |
| 59 | descobrir a linha certa: atribuição de técnica 8 % → 35 % | 750 tokens; **88 (11,7 %)** `tecnica`; **44 %** das notas com técnica fundem; portão **passou** | treinar com 3 sementes (nunca 1) |
| 60 | treinar a classe `tecnica` (modelo com **20 classes**) | 0: 0,844 (27/27, 15/15, 12/24, 27/30); 1: 0,844; 2: 0,875; média **0,851 → 0,854**; amplitude **0,062 → 0,031**; raman 12/24 nas três | manter por **estabilidade**; o gabarito não recompensa a classe |
| 61 | relabelar por proxy `partes >= 2` (13 tokens do raman) | 0: **0,708** (raman 4/24); 1: 0,750 (4/24); 2: 0,792 (4/24); modelo concordou em **4 dos 13**; raman 12/24 → 4/24; revertido → **84/96 = 0,875** | **revertida**: rótulo só por leitura visual |
| 62 | ler os 70 tokens fundidos do raman, um a um | ~**18** com técnica, ~**21** limpos, **3** entre parênteses (`(6)`, `(4)`), ~**27** lixo | relabelar por leitura; representar `ligada` (`(n)`) no JSON |
| 63 | relabelar só os 7 tokens confirmados como `tecnica` | raman **9/24** (0,771) / 9/24 (0,823) / 10/24 (0,802) — pior que 12/24; **7 dos 24** rótulos são `junk` | o problema do raman é **lixo**; rejeição por canal |
| 64 | assinatura de lixo por canal | iwaki 27 tokens / **0 %** largura<0,3 passo / 0 % partes≥2 / 0 junk; sky 15 / 0 % / 0 % / 0; **raman 94 / 28 % / 74 % / 7**; paolo 71 / 0 % / **100 %** / 0 | rejeição condicionada à assinatura, decidida **por vídeo** |
| 65 | rejeição por assinatura (vídeo com >10 % de tokens estreitos recusa o token) | 0: 0,844 (iwaki 25/27, sky 14/15, **raman 17/24**, paolo 25/30); 1: **0,906** (27/27, 14/15, 17/24, 29/30); 2: **0,927** (27/27, 15/15, 17/24, 30/30); média **0,854 → 0,892**; melhor 0,875 → 0,927; raman 12/24 → **17/24 nas três** | manter; próximo: gabarito 8–24, escala e `ligada` (`(6)`) no JSON |

## Descobertas que destravaram

- **Fatiar por corda** (rodada 2): o acorde fazia os algarismos virarem um só componente; cada corda passou a ter faixa de ±0,45 do passo. `tup` l.1: 110 glifos com 44 % centrados → 152 glifos com 85 % centrados; acervo 6.882 → 11.594 glifos.
- **Tokenização** (rodada 6): agrupar componentes da mesma corda com Δx < 0,25 passo. Treino 0,58 → 0,985; no gabarito real, 41/42 = 0,976 (contra 0,63–0,70 do modelo treinado em rótulo prata). A razão glifos/nota era 1,44.
- **Cascata de máscaras com polaridade validada pelo resultado** (rodada 2): Otsu → contraste k=21 → k=31 deu 5/5 capturas e 24/24 do acervo (a escolha ingênua de polaridade dava 0/24).
- **Verificação de forma** (rodada 8): exigir que a classe caiba no recorte medido levou a linha real de 14/15 = 0,933 → 15/15 = 1,000, corrigindo 1 de 15.
- **Fallback por ffmpeg** (rodada 3): 140 de 319 quadros só abriam por ffmpeg (44 %); sem ele, quase metade do acervo seria ignorada em silêncio.
- **Máscara de tinta mais CLARA que o fundo** (rodadas 44–45): era o que faltava para painel escuro; deu 6 picos com espaçamento 44 px, 6 linhas, passo 44,2 px, 41 tokens e máscara `contraste_claro_k21_d12` (antes: 0 linhas).
- **Uniformidade de fundo para achar o painel e rejeitar o violão** (rodadas 42–43): 5 faixas uniformes de altura 41 px, cordas em y ≈ 643/688/732/776/820/864, passo ≈44 px — o braço do violão tem 6 cordas e uma "grade de 6 linhas" quase idêntica.
- **Tamanho de fonte variável no gerador** (rodada 53): sortear 0,55–1,0 do passo em vez de 0,95 fixo; média 0,805 → 0,851, com iwaki 27/27 e sky 15/15 nas três sementes (antes variavam 23–27 e 11–15). O acervo tem algarismo de 0,38 passo (cifra club) e 0,6 passo (skyguitar).
- **Rejeição por assinatura medida** (rodadas 64–65): só o raman tem 28 % de tokens com largura < 0,3 passo (os outros três canais, 0 %); com a regra por vídeo, raman 12/24 → 17/24 e média 0,854 → 0,892.
- **Portão de medição antes do treino** (rodadas 56–59): 3,2 % < limiar de 10 % evitou dois treinos (rodadas 56 e 57) e, ao corrigir a atribuição de técnica de 8 % para 35 %, o fenômeno subiu a 11,7 % dos tokens, com 44 % de fusão.
- **Marcador por cor no algarismo** (rodadas 40, 47–50): o cifra club marca branco → laranja; limiar de 20 % da caixa dá avanço cumulativo 1 → 7 → 13 colunas, 41/41 onsets, 8 ataques distintos e intervalo mediano de 1,80 s.

## Tentativas que falharam

| tentativa | efeito medido | revertida? |
| --- | --- | --- |
| rodada 12 — regra de altura (2 dígitos exigem comp. ≥0,5 passo) no extrator | 0,818 → **0,818**; raman 12/24 → 12/24 (o erro só virou `24` → `2`) | não (mantida por inofensiva, sem resolver) |
| rodada 13 — regra de orientação (coluna com traço ≥60 % da altura) no extrator | 0,818 → **0,818**; raman 12/24 (a diagonal passa no teste de haste) | não; diagnóstico migrou para o gerador |
| rodada 14 — trocar o arco por barra diagonal no gerador | 0,818 → **0,652 (−0,166)**; iwaki 27/27 → 23/27; sky 15/15 → 9/15 | **sim** |
| rodadas 17–19 — criar a classe `junk` colhendo sobras e depois desenhando lixo (3 retreinos) | 19 classes e `junk` **ausente** nas três; 0,854 → 0,854; só 3 tokens sem par em 937 (rodada 18) | não (gancho removido na rodada 21) |
| rodada 22 — classe de rejeição global em todos os canais | média **0,805 = 0,805**: ganha ~6 no raman e perde ~5 em sky+paolo | sim (código fica sem `junk`) |
| rodada 25 — medir cursor com janela fixa de 40 s e painel a 40 % da duração | **9/24 = 38 %** contra os 95 % do inventário; erro de medição identificado | refeita na rodada 26 |
| rodadas 30–32 — patamar → travessia de x(t) → `passagens()` por sistema, para dar tempo por nota | rodada 30: **3** instantes para 134 notas; rodada 31: 3 → **5** instantes para 36 notas; rodada 32: **57** "passagens", 2 de 36 notas, 1 instante | sim (anexo de tempo parado; sinal suspeito) |
| rodada 33 — detector de cursor sem assinatura | media o **corpo do violão** (149 px, matiz 16, saturação 85) e contaminou todas as medições de cobertura | corrigida por duas travas na rodada 34 |
| rodada 34 — trava de assinatura estreita e azul | 95 % → **12 % (3/24)** e rejeita o cifra club por construção | revista na rodada 35 (a premissa "marcador = faixa" caiu) |
| rodadas 36–38 — fração cromática, normalização por quadro e categoria de cor, medidas no cifra club | 45 dos 74 tokens variam >0,5; **17–25** outliers por instante; **6–15** tokens mudam por instante, sem avanço | sim: mediam o **braço do violão** (confirmado na rodada 39) |
| rodadas 41–42 — achar o painel por coordenada y estimada (3 tentativas) | **0 linhas e 0 tokens** nas três sub-regiões | substituídas pela uniformidade de fundo |
| rodada 46 — teste de cor exigindo 45 % da caixa em laranja | **0 tokens laranja em 13 instantes**, contra a imagem que mostrava laranja | não; limiar baixado para 20 % na rodada 47 |
| rodada 51 — hipótese de que a extração fragmentava o algarismo | idêntico em ±0,15/±0,08/±0,05 passo: 57 glifos, 17 px, 0,38 passo | n/a (hipótese derrubada na rodada 52, nada foi mudado) |
| rodadas 56–58 — patch da marca de técnica cruzando o algarismo (3 tentativas) | patch não aplicou; IndentationError na linha 286; fenômeno ausente (**3,2 %**) | corrigido na rodada 59 (atribuição 8 % → 35 % → 11,7 %) |
| rodada 61 — relabelar por proxy geométrico `partes >= 2` | raman 12/24 → **4/24**; total 0,854 → 0,708 / 0,750 / 0,792 | **sim** (0,875 restaurado com os rótulos lidos à mão) |
| rodada 63 — relabelar 7 tokens como `tecnica` (por leitura) | raman 12/24 → **9/24** (0,771 / 0,823 / 0,802): o modelo já acertava o algarismo | sim (rótulos voltam a ser o algarismo) |

## Lições metodológicas

1. **Semente fixa + ≥3 execuções, com média e amplitude.** O mesmo código deu **0,854 e 0,729** (rodada 20) e **0,40 de variação num único canal**; sem isso reportei ruído como ganho.
2. **Meça a amostra antes de gastar o treino.** Três retreinos foram queimados descobrindo que a classe não nascia (rodadas 17–19); depois, o portão de 10 % evitou dois treinos (3,2 % nas rodadas 56–57).
3. **Confira o significado do número.** "323 notas com tempo" eram **3 instantes** (rodada 30); "41 notas com duração" eram **8 ataques** sem duração (rodada 50). Conte instantes distintos.
4. **Olhe o quadro antes de teorizar.** Duas vezes o detector mediu o violão achando que era a tablatura: o **corpo** (rodada 33) e o **braço** (rodada 39); e o teste de cor deu zero contra a imagem (rodada 46).
5. **Rótulo de gabarito só por leitura visual.** Relabelar por proxy geométrico piorou duas vezes (raman **12 → 4** na rodada 61; **12 → 9** na rodada 63) e foi revertido nas duas.
6. **O gargalo é cobertura do gerador, não regra de visão.** Medido repetidas vezes: regras geométricas deram **0** (rodadas 12 e 13), uma mudança de gerador deu **−0,166** (rodada 14), e as mudanças de dado deram **+0,052** (rodada 16), **+0,046** (rodada 53) e **+0,038** (rodada 65).
7. **Verifique que a edição aplicou.** Um patch não aplicou (rodada 56), outro quebrou o arquivo com IndentationError na linha 286 (rodada 57); desde então, `ast.parse` + `import` antes de qualquer medição.
8. **Não generalize de uma amostra.** O tempo foi validado num canal e não valia nos outros; a cobertura do cursor varia **por vídeo dentro do mesmo canal** (rodada 28, shin izumi 119,5 s num vídeo e 0 s em outro).
9. **Declare o mecanismo e a semântica no JSON.** Faixa ou cor por canal; `t_ini` é onset medido e `t_fim` não é duração (rodadas 47–50).

## Contradições encontradas

Entre os 65 documentos:

1. **`0,865` não existe em nenhuma medição.** As rodadas 17, 18 e 19 registram o total **inalterado em 0,854**; as rodadas 20, 21 e 22 citam a afirmação "classe de rejeição: **0,854 → 0,865**" como um resultado que eu teria reportado. Arquivos: `rodada17_rejeicao_colheita.md`, `rodada18_lixo_lugar_errado.md`, `rodada19_rejeicao_terceira.md` × `rodada20_variancia.md`, `rodada21_variancia_medida.md`, `rodada22_junk_troca.md`.
2. **Cobertura do cursor: 12 % × 4 %.** A rodada 34 registra **12 % (3/24)** com a trava de assinatura; a rodada 35 chama o mesmo número da rodada anterior de "**4 %** de cobertura". Arquivos: `rodada34_trava_cursor.md` × `rodada35_marcador_varia.md`.
3. **Contagem de glifos do acervo (163 linhas): 11.594 × 11.780.** A rodada 2 registra **11.594 glifos**; as rodadas 4 e 6 usam **11.780** como o mesmo total. Arquivos: `rodada2_medicoes.md` × `rodada4_gabarito_e_bugs.md`, `rodada6_tokenizacao.md`.
4. **Tokens sem par no sintético: 3 × 91.** A rodada 18 mede **3 sem par em 937** (30 linhas) e a rodada 19 não registra outro valor; a rodada 21 cita "depois corrigido (**91 em 30 linhas**)", número que nenhum outro documento traz. Arquivos: `rodada18_lixo_lugar_errado.md`, `rodada19_rejeicao_terceira.md` × `rodada21_variancia_medida.md`.
5. **Quais rodadas pioraram por proxy geométrico.** A rodada 64 diz que o proxy "me fez piorar a métrica duas vezes (**rodadas 60 e 62**)"; a rodada 61 localiza as duas tentativas em "**rodada 14 e agora**" e foi a rodada **61** que mediu 4/24 — a rodada 60 mediu 0,854 e a 62 não alterou métrica. Arquivos: `rodada64_assinatura_lixo.md` × `rodada61_proxy_geometrico_falhou.md`, `rodada60_tecnica_treinada.md`, `rodada62_leitura_dos_fundidos.md`.
6. **A conta do proxy revertido: −0,1 (2×) × −0,104 + −0,166.** A rodada 65 resume "relabelar por proxy geométrico **−0,1** (revertida, **2×**)"; a rodada 61 registra a queda do proxy em 0,708 / 0,750 / 0,792 (**−0,104** sobre 0,854) e atribui a outra ocorrência à rodada 14, que foi mudança de gerador e vale **−0,166**. Arquivos: `rodada65_rejeicao_por_assinatura.md` × `rodada61_proxy_geometrico_falhou.md`, `rodada14_slide_piorou_revertido.md`.
7. **Número do estado entre as rodadas 53 e 59: 0,851 × 0,885.** A rodada 53 fixa **0,851** (média de 3 sementes) como número oficial; as rodadas 54 a 59 registram **0,885 bruto** na linha "tablatura — casas" do estado, sem indicar semente nem repetição; a rodada 60 volta a chamar **0,851** de valor "antes". Arquivos: `rodada53_fonte_variavel.md` × `rodada54_metrica_alcancavel.md` a `rodada59_portao_abriu.md`, `rodada60_tecnica_treinada.md`.
8. **Rodada de origem dos rótulos restaurados.** A rodada 61 diz ter restaurado "os rótulos lidos à mão na **rodada 15**"; o canal relabelado é o raman korshun, cujos rótulos de casas 4–7 entraram na **rodada 10** — a rodada 15 rotulou o paolo d'angelo. Arquivos: `rodada61_proxy_geometrico_falhou.md` × `rodada10_gabarito_ampliado.md`, `rodada15_gabarito_4canais.md`.

Citações e arquivos:

9. **Os caminhos citados nos documentos não existem hoje.** As 65 rodadas citam `tools/tabseg.py`, `tools/sintetico.py`, `tools/reconhecer.py`, `tools/avaliar.py`, `tools/transcrever.py`, `tools/inventario.py`, `tools/cursor.py`, `tools/ouro.py`, `tools/exp_binarizacao.py`, `gold/gabarito.json` e `saida/skyguitar_linha01.json`, `saida/exemplo_0..2.json`, `saida/cifra_abanda.json`, `saida/rollout/*.json`, `saida/rollout/resumo.json`, `saida/video_completo.json`. No estado atual do projeto eles estão em `tab/`, `data/gold/gabarito.json` e `data/saida/` — nenhum existe em `tools/` nem em `saida/` (diretórios inexistentes). Não editei nenhum deles; registro porque qualquer comando da tabela acima precisa do caminho novo.

Fora dos 65 documentos (documentos de raiz, incluídos por afetarem o mesmo número):

10. **Número oficial divergente.** `ESTADO.md` diz **0,851** (média 0,844 / 0,823 / 0,885); `RESUMO_PAUSA.md` diz **0,892** (média 0,844 / 0,906 / 0,927); `AGENTS.md` diz 0,892 e afirma que o `RESUMO_PAUSA.md` "diz 0,851", o que não confere com o próprio arquivo. As rodadas 65 e `RESUMO_PAUSA.md` concordam em **0,892**.
11. **Contagem do acervo.** A rodada 3 declara **3.781 vídeos** em 12 canais, mas a tabela por canal do mesmo documento soma **3.557** (faltam 224 vídeos não atribuídos a nenhuma linha da tabela); `AGENTS.md` fala em **13 canais** e `RESUMO_PAUSA.md` em **12 canais**.

## Anexo — trilha do número oficial e estado ao fim da rodada 65

Trilha do acerto no gabarito real, como cada conjunto de documentos registra (não uniformizaram o protocolo):

| marco | valor | base | origem |
| --- | --- | --- | --- |
| rótulos prata, canais vistos | 0,88 | 1.944 glifos | rodada 1 |
| rótulos prata, 2 canais novos | 0,64 → 0,67 | 1.944 glifos | rodadas 1 e 3 |
| sintético + tokenização | **0,976** | 42 glifos / 2 canais | rodada 6 |
| gabarito de 96 glifos | 1,000 → **0,818** | 66 glifos / 3 canais | rodadas 9 e 10 |
| média de 3 sementes (fonte fixa) | **0,805** (amplitude 0,052) | 96 glifos / 4 canais | rodadas 21 e 22 |
| média de 3 sementes (fonte variável) | **0,851** (0,823–0,885) | 96 glifos / 4 canais | rodada 53 |
| média de 3 sementes (classe `tecnica`) | **0,854** (amplitude 0,031) | 96 glifos / 4 canais | rodada 60 |
| média de 3 sementes (rejeição por assinatura) | **0,892** (0,844 / 0,906 / 0,927) | 96 glifos / 4 canais | rodada 65 |
| acerto sobre os rótulos alcançáveis | **0,955** (85/89; 7 rótulos `junk` inalcançáveis) | 96 glifos / 4 canais | rodada 54 |

Estado ao fim da rodada 65, com o que os documentos dão como medido:

- **tablatura**: 0,892 (3 sementes); iwaki 25–27/27, sky 14–15/15, paolo 25–30/30, raman **17/24 igual nas três sementes** (17/17 nos algarismos; os 7 restantes são os rótulos `junk`), melhor execução 0,927; ressalva que continua valendo: 96 glifos, 4 canais, **casas 0–7** — casas 8–24 seguem sem aferição;
- **técnica**: classe treinada e estável, **sem ganho de acerto** mantida por estabilidade (amplitude 0,062 → 0,031);
- **tempo**: dois mecanismos medidos — faixa no `skyguitar` (1 nota/s, desvio 0,16 s) e cor no `cifra club` (41/41 onsets, 8 ataques, intervalo 1,80 s); a cobertura do cursor ficou **em aberto** depois de as medições antigas caírem (95 %, 54 % e 38 % invalidadas nas rodadas 33–35);
- **compasso**: 4/4/4/3 confiável onde a barline é limpa; implausível nos canais de vídeo (`{1:12, 4:5, 8:26, 9:33}` e `{1:6, 7:13, 10:29}`);
- **pendências declaradas na rodada 65**: ampliar o gabarito para casas 8–24, rodar em escala com a decisão por vídeo, representar `ligada` (`(6)`) no JSON e aferir a casa dos canais fora do gabarito (o `cifra club` tem corda e tempo, casa não aferida);
- **fora desta cadeia**: tab ASCII e partitura de 5 linhas exigem leitor próprio (registrado nas rodadas 1, 2 e 3).

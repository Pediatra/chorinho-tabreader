# Frentes de teste da pesquisa da partitura

**Data**: 2026-10-16. **Base**: [`partitura.md`](partitura.md), a revisão de literatura que o dono
trouxe (feita com o Gemini). **Autor**: trilha partitura, sessão principal, que também revisa o
que as frentes entregarem. **Para quem**: agentes que vão testar as ideias em worktrees separadas.

> **Leia antes de começar**: `AGENTS.md`; este documento inteiro; a parte de `partitura.md`
> citada na sua frente; no `ESTADO.md`, as seções "Partitura —" de 2026-10-14 e 2026-10-15; as
> decisões `docs/decisoes/3001` (imagem derivada) e `3002` (partitura no produto); as rodadas
> `3004` (gabarito do dono), `3021` (piloto sem produto) e `3023` a `3025`.

**Sumário**

1. Objetivo
2. Onde estamos (o que já foi medido)
3. Triagem da pesquisa: o que serve, o que já temos, o que fica fora
4. Ordem dos testes
5. Régua comum (vale para todas as frentes)
6. Regras para quem trabalha numa worktree
7. As frentes: Frente 0 e Frentes A a E
8. Pegadinhas que valem para todas as frentes
9. O que cada frente entrega
10. Decisões do dono

---

## 1. Objetivo

### 1.1 Do projeto

O produto é um JSON por vídeo com **corda, casa, coluna, compasso, técnica e tempo** de cada
nota, para milhares de vídeos-aula. O alvo final é um dataset vídeo → tablatura + partitura para um
modelo futuro. A partitura sai num arquivo irmão, `<stem>.partitura.json` (decisão 3002), e o
**tempo dela vem do pareamento com a tablatura**, não de um medidor próprio (regra do dono).

### 1.2 Da pesquisa

O pedido ao Gemini cobriu sete perguntas:

1. combinar dois leitores de pauta (Audiveris e homr) sem inventar nota;
2. confiança por nota ou por compasso quando não há segunda fonte;
3. leitura de pauta em quadro de vídeo: cursor, destaque colorido, recorte;
4. leitores para várias vozes numa pauta só (violão clássico);
5. pauta e tablatura lidas juntas, uma restringindo a outra;
6. métricas em nível musical e tamanho do gabarito humano;
7. datasets de partitura de violão com MusicXML conferido.

### 1.3 Deste documento

Do que a pauta lê, quase tudo está certo: **97,6 %** dos símbolos lidos no gabarito do dono
(seção 2). O que falta é nota que **não foi lida**. Este documento responde, com medida, a três
perguntas:

1. **Cobertura sem inventar.** O que faz a pauta ler mais notas sem inventar? Hoje a cobertura é
   de **91,6 %** no gabarito R01–R21 e de **81,5 %** nos 3 recortes sem produto. Com a tab, ficam
   **14 de 546** notas sem leitura, e essas não têm figura.
2. **Confiança sem juiz.** Sem tablatura (o piloto sem produto, e toda tab que o produto ainda
   não lê), que compasso merece confiança? Hoje nada avisa.
3. **Régua que vale para o acervo.** O gabarito cobre **14 vídeos** de cerca de **1.455** com
   pauta. Quanto gabarito novo, sorteado como, para saber a cobertura com ± 3 %?

---

## 2. Onde estamos (o que já foi medido)

Todos os números desta seção foram **remedidos em 2026-10-16** pelo script do CA1 (seção 5.3),
na `main` do commit `0bdc9439`.

**O leitor.** A cadeia da partitura é esta:

- recorte da pauta com margem de 7 entrelinhas em cima e embaixo (`x2_margem`, rodada 3003), que
  não para em fileira de vigas (rodadas 3008 e 3022);
- **Audiveris 5.10.2** ampliado 2x (`tab/partitura_omr.py`), com a **armadura herdada** do vídeo
  quando a leitura não tem clave ou não tem armadura (rodadas 3009 e 3020);
- **homr 0.7.0** como segundo leitor (rodadas 3005, 3006 e 3025);
- **pareamento com a tab** pelo x do quadro (`tab/partitura_pareamento.py`, rodadas 3010 e 3015);
- saída `<stem>.partitura.json` (`tab/partitura_video.py`, rodada 3014).

Audiveris e homr estão só na imagem `localhost/chorinho-partitura:dev`, em CPU: cerca de 18 s
por recorte no Audiveris e de 7 a 9 s no homr.

**Com tablatura: R01–R12.** São 12 recortes de 3 vídeos. A referência são as notas da tab do
gabarito (`data/gold/ouro_video/`) convertidas em altura escrita:

| leitura | notas da tab | certas | altura errada | faltando | inventadas |
| --- | --- | --- | --- | --- | --- |
| só Audiveris, com armadura do vídeo | 546 | 496 | 9 | 41 | 3 |
| + homr confirmado pela tab | 546 | **528** | 4 | 14 | 3 |

- 337 pares partitura × tab, 336 no mesmo x do quadro;
- 32 notas vieram do homr, e a figura delas **não foi conferida**;
- 5 notas do Audiveris foram trocadas porque a tab as desmente.

O `ESTADO.md` diz 526: o gabarito de tab da Gymnopédie foi corrigido depois (commit `741f66da`), e
o número de hoje é 528. Com o gabarito antigo, o mesmo script dá 526
(`data/saida/partitura/diag/ca1/ouro_antigo/conferir.txt`).

**Com tablatura: os 3 produtos (19 telas com pauta).** A partitura do produto é pareada com a tab
do **produto**, não com a do gabarito:

| vídeo | notas da tab | certas | altura errada | faltando | inventadas |
| --- | --- | --- | --- | --- | --- |
| Greensleeves | 106 | 106 | 0 | 0 | 0 |
| South American | 269 | 266 | 0 | 3 | 0 |
| Gymnopédie | 392 | 355 | 9 | 28 | 7 |
| **partitura, 19 telas** | **767** | **727** | **9** | **31** | **7** |
| só a tab do produto, mesmas telas | 767 | 723 | 21 | 23 | 17 |

A Gymnopédie tem 392 das 767 notas e 28 das 31 que faltam. O `ESTADO.md` diz 723 para a
partitura; pela mesma correção do gabarito, hoje são 727.

**O gabarito do dono (leitura visual).** O dono conferiu cada símbolo lido contra o desenho e
clicou nas notas que faltavam:

| gabarito | recortes | vídeos | lidos | certos | erros | faltando | cobertura |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `leitura_p1.json` (R01–R21) | 21 | 11 | 873 | 852 (97,6 %) | 7 figura, 4 altura, 10 não existem | 78 | 852/930 = 91,6 % |
| `leitura_sem_produto.json` | 3 | 3 | 178 | 176 (98,9 %) | 2 não existem | 40 | 176/216 = 81,5 % |
| `compassos_homr.json` | 4 de 17 itens | 3 | 282 | 272 | 10 não existem | 4 | não vale (ver abaixo) |

Por vídeo, no R01–R21 (`data/saida/partitura/p1/conferencia/itens.json`):

| vídeo (canal) | recortes | lidos | certos | faltando |
| --- | --- | --- | --- | --- |
| greensleeves (pablo romé), R01–R04 | 4 | 107 | 107 | 0 |
| south american (guitar dell'arte), R05–R07 | 3 | 259 | 258 | 17 |
| gymnopédie (robert lunn), R08–R12 | 5 | 185 | 177 | 30 |
| when the love falls (sky guitar), R13 | 1 | 33 | 27 | 2 |
| if (sky guitar), R14 | 1 | 35 | 35 | 1 |
| titanic (iwaki), R15 | 1 | 29 | 29 | 4 |
| serge kottelat, R16 | 1 | 63 | 62 | 8 |
| la llorona (transcriptor), R17 | 1 | 21 | 21 | 2 |
| ruins (tv on guitar), R18 | 1 | 55 | 53 | 5 |
| horizons (paolo d'angelo), R19 | 1 | 28 | 27 | 5 |
| 感電 (guitarous), R20 e R21 | 2 | 58 | 56 | 4 |

- **R20**: a segunda metade não foi lida e o dono não marcou faltando. Vale só para os símbolos
  lidos.
- **R21** é leitura do homr (`homr/nativo`); os outros 20 são do Audiveris (`x2_margem`).
- No sem produto, **31 das 40** que faltam são do athletic P01a: o Audiveris descartou a voz de
  cima dos compassos 3–4 (rodada 3023).
- O tempo do dono foi medido: os 21 recortes do R01–R21 levaram 65 min (cerca de 3 min por
  recorte).
- O `compassos_homr.json` **não está completo e não está no git**:
  - agua P10a: o desenho da conferência falhou (`TypeError` em `getHalfTone`);
  - athletic P01a: o dono anotou "praticamente tudo inventado, não marquei tudo";
  - só amores P01a e P11a valem.

**Sem tablatura: o piloto de 11 vídeos** (`data/saida/partitura/sem_produto/`, 162 recortes):

- Audiveris lê **143/162** recortes. As 19 falhas são "No system found";
- a faixa amarela do cursor explica a maioria: com faixa, 12 de 36 falham (33 %); sem faixa, 7 de
  126 (6 %);
- a faixa só aparece em 2 vídeos (mela e free tab), e o mela tem 16 das 19 falhas;
- o homr lê 160/162;
- a regra da rodada 3025 (troca o compasso pelo do homr quando ele lê 2× ou mais as notas do
  Audiveris) trocou **30 compassos em 17 recortes**. No athletic P01a, medida por degrau, ela
  recupera 25, inventa 8 e perde 2. A conferência do dono nesse recorte diz o contrário, mas está
  incompleta.

**Marcas que o Audiveris grava no `.omr`** (`data/saida/partitura/diag/ca1/omr_marcas.txt`):

| conjunto | compassos | `abnormal` | duração ≠ esperada | sem duração esperada | símbolos com grade < 0,5 |
| --- | --- | --- | --- | --- | --- |
| R01–R21 | 148 | 8 | 9 | 88 | 110/5559 |
| piloto | 598 | 24 | 25 | 502 | 706/41410 |

**Ninguém mediu** se essas marcas caem nos compassos com erro.

**Tempo.** O `.partitura.json` não copia o tempo (decisão 3002). O campo `t` dos eventos é
posição em tempos dentro do compasso, não segundos. O consumidor acha o segundo pelo `t_ini` da
coluna pareada (`tela`, `coluna`) no produto da tab. Nos produtos (`data/saida/fase8/rede/`):

| vídeo | notas da tab com `t_ini` | exibições | exibições com tempo medido | eventos da partitura com par |
| --- | --- | --- | --- | --- |
| Greensleeves | 209/212 | 8 | 8 | 72/72 |
| South American | 215/269 | 3 | 3 | 184/184 |
| Gymnopédie | 0/385 | 12 | 0 | 182/186 |

O tempo da tab **não foi validado** por gabarito. Quantos eventos da partitura acabam com segundo
**não foi contado**.

**O acervo** (rodada 3001, `data/saida/partitura/p0/`, amostra de 436 vídeos):

- cerca de **1.455 dos 2.998** vídeos ativos daquela data têm pauta (49 %);
- **pauta sem tab praticamente não existe**: a partitura vem junto da tablatura;
- extrapolação por canal (soma 1.459): sky guitar 417, robert lunn 357, guitar dell'arte 313,
  iwaki 164, pablo romé 111, serge kottelat 38, transcriptor 28, paolo d'angelo 14, guitarous 7,
  tv on guitar 5, kimny's 4, lonelypicker 1, mr. tabs 1;
- os 5 primeiros canais somam cerca de 93 %.
- Produto da tab existe hoje para **8 vídeos** (`data/saida/fase8/rede/`), e só 3 deles têm pauta.

**Correlação dentro do recorte (ICC)** no R01–R21 (`data/saida/partitura/diag/ca1/icc.txt`):

- cobertura: p = 0,916, ICC = **0,023**, 930 notas, cerca de 44 notas por recorte;
- precisão: p = 0,976, ICC = **0,044**;
- nos 3 recortes sem produto o ICC não vale nada (3 grupos).

**O que não foi medido.**

- O ritmo e as vozes fora do que o dono conferiu: as figuras das 32 notas do homr e as figuras das
  notas que faltam.
- A qualidade nos canais fora dos 14 vídeos do gabarito.
- Se as marcas do Audiveris acusam os compassos errados.
- A regra 3025 contra um gabarito completo.
- O tempo em segundos das notas da partitura.

---

## 3. Triagem da pesquisa: o que serve, o que já temos, o que fica fora

Critério: a ideia serve se pode subir a **cobertura sem inventar**, **avisar o compasso suspeito**
sem tab ou **medir com uma régua que valha para o acervo**, com as dependências que temos ou que o
dono aprovar.

### 3.1 Testar

| ideia (seção de `partitura.md`) | frente | por quê |
| --- | --- | --- |
| régua por compasso: onde estão os erros e se as marcas do Audiveris os acusam (§2, "violação da invariante rítmica"; §1, fase 2) | F0.1 | sem ela, B1 e B2 não têm número |
| a troca do compasso pelo homr (regra 3025) julgada pela tab (§1, "fusão assimétrica") | F0.2 | a regra já está no produto e só foi medida em 1 recorte |
| quantas notas da partitura ganham tempo pelo par (regra do dono; §5, passo 1) | F0.3 | nenhuma nota da partitura tem segundo contado |
| mediana de quadros no tempo, cor tirada e moldura branca (§3) | A1 | 19 de 162 recortes não têm leitura nenhuma; 12 de 36 com faixa |
| compasso decidido pela soma do ritmo e acorde completado no mesmo tempo (§1, fases 2 a 4) | B1 | partitura sem tab: o piloto e toda tab que o produto não lê |
| bandeira de confiança por compasso (§2) | B2 | sem tab, hoje nada avisa |
| leitor de várias vozes treinado: SMT (§4) | C1 | só se a polifonia for o que sobra depois de A, B e E |
| amostra estratificada, um recorte por vídeo (§6) | D1 | 14 vídeos não representam cerca de 1.455 |
| completar pela tab a nota de acorde e o ataque isolado (§5, passos 3 e 4) | E1 | 14 notas sem leitura em R01–R12 e 31 nas 19 telas; nenhuma tem figura |

### 3.2 Já temos (não refazer)

| ideia | onde já está |
| --- | --- |
| Audiveris ampliado 2x, com margem | condição `x2_margem` em `tab/partitura_omr.py` (rodada 3003: 491/546) |
| homr como segundo leitor | rodadas 3005 e 3006 |
| armadura herdada do vídeo (§1, fase 2, "fórmula herdada") | `herdar_condicao`, rodadas 3007, 3009 e 3020 |
| projeção pelo x, pauta × tab (§5, passo 1) | pareamento: 336 de 337 pares no mesmo x (rodadas 3010 e 3015) |
| correção de altura pela tab (§5, passo 2) | nota do Audiveris desmentida vai para `trocadas` (3012); harmônico não é troca (3013) |
| nota do homr só com confirmação da tab | rodada 3006 |
| troca do compasso pelo homr sem tab | `trocar_compassos_pelo_homr` (3025), notas `homr_sem_confirmacao` |
| destaque colorido na paginação | top-hat (3017), **só** no `paginar`, não na entrada do leitor |
| páginas do vídeo, quadro estável | `paginar` (rodadas 3016 a 3018) |
| recorte que não para em viga | rodadas 3008 e 3022 |
| ferramenta de conferência do dono | `python -m tab.partitura_gabarito servir` |
| ICC medido (§6) | `data/saida/partitura/diag/ca1/icc.txt` |
| GPU de 8 GB, um modelo por vez | protocolo `data/saida/gpu.lock` |

### 3.3 Fora agora (com o motivo)

| ideia | motivo |
| --- | --- |
| super-resolução de documento (§3, "~15 ms") | a pesquisa não nomeia o modelo; ampliar 3x e 4x já piorou (417 e 270 de 546, rodada 3003) |
| binarizar antes do leitor (Otsu, SAE) (§3) | Otsu quebrou 4 recortes (196/546, rodada 3003); o SAE não foi conferido |
| ampliar o recorte para ± 3,5 alturas de pauta (§3) | a margem de 7 entrelinhas foi medida (3003); abaixo da pauta vem a tab, e o gabarito usa as coordenadas do recorte atual. A moldura branca entra na A1 |
| votação S2 / ROVER (§1) | exige 3 leitores ou mais; temos 2 (o oemer falha, o SMT sem treino acerta 20/546) |
| LEGATO (§4) | o código é MIT, mas o codificador é o Llama 3.2 Vision, de acesso fechado |
| SMT sem treino (§4, §8) | o melhor peso acertou 20/546 (rodada 3003) |
| Transcoda, SMT++ (§4) | não conferidos; um leitor treinado por vez (C1) |
| SMB, GrandStaff, PDMX, DadaGP como dado (§7) | piano, quarteto e manuscrito; licença por arquivo no PDMX; o DadaGP já foi descartado pelo dono nas trilhas mãos e tablatura |
| MV2H, OMR-NED, TEDn (§6) | pedem a partitura de referência inteira do vídeo; o nosso gabarito é por símbolo, e a contagem por símbolo já responde |
| log-probabilidade do decodificador do homr (§2) | exige mexer no código do homr, que é AGPL |
| homr na GPU (§8) | em CPU já dá 7 a 9 s por recorte, e a GPU é disputada |
| calibração de confiança (§2) | a própria pesquisa não acha nada aplicável |
| Smashcima, video-to-score, repositório de robustez do homr (§3) | o Smashcima é síntese de manuscrito; os outros não foram conferidos |
| YOLO (Ultralytics) | licença AGPL-3.0 |
| leitura da tablatura (OTR) da §5 | é da trilha tablatura |

### 3.4 O que a checagem já mostrou (2026-10-16)

A revisão do Gemini traz números que **não batem** com a fonte. Conferi estes itens:

| item | a pesquisa diz | a fonte diz |
| --- | --- | --- |
| `homr` | licença MIT; GPU com `poetry install --only main,gpu` | o repositório é **AGPL-3.0**; a GPU vem pelo extra `homr[cuda]` |
| Smashcima | leitura de quadro do YouTube | é **síntese de manuscrito** (escrita à mão) |
| LEGATO (arXiv 2506.19065) | leitor aberto | código MIT, mas depende do **Llama 3.2 Vision**, de acesso fechado |
| `musicdiff` | MIT, `pip install musicdiff` | confere: MIT, Python ≥ 3.12. **Não está** em nenhuma imagem nossa |
| SMT (`antoniorv6/SMT`) | MIT, pesos prontos para violão | MIT confere; sem treino, o melhor peso acerta **20/546** (rodada 3003) |
| MV2H | métrica pronta | existe; MIT, em **Java** |
| Verovio | — | **LGPL-3.0** (repositório `rism-digital/verovio`) |
| "cobertura de 81,5 % para 96,5 %" | um ganho | mistura dois gabaritos: 81,5 % é a cobertura de 3 recortes sem produto (176/216); 96,5 % é 527/546 de R01–R12 com a tab (rodada 3014; hoje 528) |
| "51 % sem pauta combinada" | metade tem pauta sem tab | 51 % **não têm pauta**; pauta sem tab praticamente não existe (rodada 3001) |
| ICC de 0,05 a 0,10, 30 notas por recorte | suposto | medido: **0,023** (cobertura) e **0,044** (precisão), cerca de 44 notas por recorte |
| "24 recortes de cerca de 15 vídeos" | — | 24 recortes de **14** vídeos (21 do R01–R21, de 11 vídeos, e 3 sem produto) |
| "cobertura medida em 12 recortes" | — | a cobertura foi medida nos 21 (91,6 %) e nos 3 sem produto (81,5 %) |

O artigo de Padilla et al. (ISMIR 2015) existe; o número "~95 %" dele **não** foi conferido.

**Regra.** Antes de depender de um repositório, a frente confere **que ele existe**, a
**licença** e o **número** na fonte original. O resultado vai no documento da rodada. Os outros
itens da pesquisa não foram conferidos.

---

## 4. Ordem dos testes

Crie as worktrees **a partir do commit `0bdc9439` ou depois**: é o código da regra 3025, e os
números da seção 2 foram remedidos nele.

| ordem | teste | frente | depende de | custo |
| --- | --- | --- | --- | --- |
| 1 | régua por compasso e marcas do Audiveris | F0.1 | nada | baixo (CPU, sem vídeo) |
| 2 | troca do compasso pelo homr julgada pela tab | F0.2 | nada | baixo (CPU, leituras já gravadas) |
| 3 | tempo pelo par | F0.3 | nada | baixo (CPU, sem vídeo) |
| 4 | amostra estratificada para gabarito novo | D1 | nada (o dono rotula) | médio (CPU, `paginar` e Audiveris em 40 vídeos; cerca de 2 h do dono) |
| 5 | imagem limpa antes do leitor | A1 | nada | médio (CPU, 15 quadros por exibição, Audiveris a 18 s por recorte) |
| 6 | completar pela tab | E1 | nada; o aceite usa a conferência do dono | baixo (CPU) |
| 7 | compasso pela soma do ritmo | B1 | F0.1 (fórmula de compasso) e F0.2 (a regra 3025 como referência) | baixo (CPU) |
| 8 | bandeira de confiança por compasso | B2 | F0.1; o teste final usa a amostra D1 | baixo (CPU) |
| 9 | SMT treinado | C1 | D1, A1 e B1 mostrarem que a polifonia sobra; dono; GPU | alto (GPU) |

As frentes podem rodar em paralelo, cada uma na sua worktree. A ordem acima é de **prioridade**
(qual resultado muda mais o plano), não de espera.

**Por que esta ordem.**

1. **A Frente 0 vem primeiro** porque três coisas não têm número hoje:
   - em que compasso estão os erros, e se o Audiveris avisa;
   - se a regra 3025, que já está no produto, ganha ou perde fora do athletic;
   - quantas notas da partitura têm segundo.

   A F0.1 decide o desenho da B1 e da B2. A F0.2 decide se a regra 3025 fica no produto.
2. **A D1 vem cedo** porque depende do tempo do dono, que é o passo mais lento. E todo número
   final depende de uma amostra que represente o acervo: 14 vídeos não representam. O dono rotula
   enquanto as outras frentes rodam.
3. **A A1 ataca a única falha total**: recorte sem leitura nenhuma (19/162), quase todo sob a faixa
   do cursor.
4. **A E1 é o ganho mais barato onde há tab**: as notas que faltam já têm altura; falta a figura.
5. **A B1 e a B2 são para a pauta sem tab.** Hoje isso é o piloto; amanhã, toda tab que o produto
   não lê (rolagem e canais fora).
6. **A C1 custa GPU, dado de treino e dependência.** Só vale se o que sobrar depois de A, B e E
   for polifonia.

**Revisão da ordem.** A Frente 0 pode mudar a ordem. Por exemplo, se a F0.1 mostrar que menos da
metade dos compassos com nota faltando tem a fórmula de compasso conhecida, a B1 tem pouco a ganhar
e a E1 e a B2 sobem.

---

## 5. Régua comum (vale para todas as frentes)

### 5.1 Dados

**Gabaritos do dono** (`data/gold/partitura/`, **só leitura**):

| arquivo | o que é | itens servidos | completo? |
| --- | --- | --- | --- |
| `leitura_p1.json` | R01–R21: 21 recortes, 11 vídeos, 10 canais | `data/saida/partitura/p1/conferencia/itens.json` | sim, exceto o faltando do R20 |
| `leitura_sem_produto.json` | 3 recortes sem produto (agua P01a, athletic P01a, canon P06a) | `data/saida/partitura/diag/conferencia_sem_produto/itens.json` | sim |
| `compassos_homr.json` | conferência da regra 3025, 4 de 17 itens | `data/saida/partitura/diag/troca_homr/itens.json` | **não**; fica só na cópia principal, fora do git |

- O formato é o 3: `simbolos` com `idx`, `compasso`, `palpite` (o que o leitor disse: `t`, `midi`,
  `figura`, `pontuada`, `voz`, `acorde`, ligaduras, `graca`, `notacoes`), `dono` (`certo`,
  `altura_errada`, `figura_errada`, `nao_existe`) e `notacoes_dono`; e `faltando`, uma lista de
  cliques `{x, y}` **sem figura**. Pausas entram.
- Cada item servido diz a leitura de origem no campo `fonte` (por exemplo
  `audiveris/x2_margem_herdada`). Use essa leitura, não outra.
- O `fonte_itens` do `leitura_sem_produto.json` aponta errado para `p1/conferencia/itens.json`.
  Os itens certos são os da tabela.

**Gabarito de tab** (`data/gold/ouro_video/`, só leitura): greensleeves, south_american e
gymnopedie. A conversão em altura escrita é `tab.partitura_avaliar.referencia_do_recorte`; a
contagem é `tab.partitura_avaliar.contar` no modo `"exato"`.

**Leituras gravadas** (`data/saida/partitura/`, só leitura):

- `p1/recortes_margem/` e `indice.json`: os recortes do R01–R21 nas coordenadas do gabarito;
- `p1/omr/audiveris/x2_margem/` (a leitura do gabarito), `x2_margem_herdada/`, `p1/omr/homr/nativo/`
  e `homr/x2/`. Cada pasta de recorte do Audiveris tem `entrada.png`, o `.omr`, o `.mxl` e o
  `saida.musicxml`;
- `video/<stem>/<stem>.partitura.json` e `video/<stem>/omr/` dos 3 produtos;
- `sem_produto/<slug>/` dos 11 vídeos do piloto: `recortes/` (com `indice.json` e as `exibicoes`
  `{t0, t1}` de cada página), `omr/` e `<slug>.partitura.json`. A pasta `ólafur_...` é uma cópia
  vazia: use a `o_lafur_...`;
- `p0/resumo.json` e `p0/amostra.jsonl` (436 vídeos da rodada 3001).

**Produtos da tab** (`data/saida/fase8/rede/<stem>.json`): 8 vídeos, 3 com pauta. Cada nota tem
`tela`, `coluna`, `exibicao`, `passagem` e `t_ini`.

### 5.2 Unidades e métricas

**Altura com tab** (Frentes 0, A, B e E, e qualquer frente que mexa na leitura):

- a unidade é a nota da tab do gabarito, convertida em altura escrita;
- as contagens são: notas da tab, certas, altura errada, faltando e inventadas;
- reporte por recorte, por tela e por vídeo, sempre com o denominador;
- reporte também **consertadas e quebradas**: nota da tab que passou de não certa para certa, e o
  contrário.

**Gabarito do dono** (Frentes A, B, C, D e E):

- a unidade é o símbolo lido, com o estado que o dono deu;
- **precisão** = certos / lidos; **cobertura** = certos / (certos + faltando);
- o R20 só entra na precisão;
- um símbolo de leitura nova sem `palpite` igual no gabarito (mesmo `compasso`, `t` e `midi`) é
  **não conferido**: conte-o à parte e leve-o para a conferência do dono.

**Por compasso** (Frentes 0 e B):

- a unidade é o compasso da leitura do Audiveris;
- um compasso tem **erro** se tem símbolo que não é `certo`, ou um clique de faltando dentro dele;
- o clique entra no compasso pelo x entre as barras do `.omr`, e no degrau pelo y. O método é o de
  `data/saida/partitura/diag/homr_sem_produto/regra.py` (rodada 3024);
- no gabarito de tab, um compasso tem erro se tem nota da tab sem par certo ou uma inventada.

**Tempo** (Frente 0):

- a unidade é o par (evento da partitura, exibição da tela);
- o par "tem tempo" se a coluna pareada tem `t_ini` naquela exibição;
- conte também as **inversões**: dois eventos seguidos da mesma exibição em que o tempo volta.

Reporte sempre por vídeo e por canal, e também sem os vídeos que carregam a conta (CA4).

### 5.3 Critérios de aceite comuns (CA)

Uma variante só é "aprovada" se cumprir **todos**:

- **CA1 — reprodução.** Antes de mexer em qualquer coisa, a worktree reproduz **exatamente** os
  números abaixo. O script só lê o que está gravado (leituras, `.partitura.json`, gabaritos), não
  lê vídeo nem grava nada, e leva cerca de 4 s na imagem `chorinho:dev`:

  ```bash
  python data/saida/partitura/diag/ca1/ca1.py
  ```

  A saída tem de trazer estas linhas, iguais:

  ```text
  A. P3 R01-R12 (12 recortes), ordem ['referencia', 'certas', 'altura_errada', 'faltando', 'inventada']
     so Audiveris (com armadura do video): [546, 496, 9, 41, 3]
     com homr confirmado pela tab:         [546, 528, 4, 14, 3]
     pares 337, x conferido 336, notas do homr 32, trocadas pela tab 5
  B. produtos (.partitura.json) contra a tab do gabarito
     greensleeves_g: [106, 106, 0, 0, 0]
     south_american: [269, 266, 0, 3, 0]
     gymnopedie_no_: [392, 355, 9, 28, 7]
     total partitura (19 telas): [767, 727, 9, 31, 7]
     so a tab do produto, mesmas telas: [767, 723, 21, 23, 17]
  C. leitura_p1: 21 recortes (21 confirmados), lidos 873, certos 852, {'altura_errada': 4, 'certo': 852, 'figura_errada': 7, 'nao_existe': 10}, faltando 78, cobertura 852/930
  D. leitura_sem_produto: 3 recortes (3 confirmados), lidos 178, certos 176, {'certo': 176, 'nao_existe': 2}, faltando 40, cobertura 176/216
  F. piloto sem produto, leituras que sairam:
     audiveris/x2_margem: 143/162
     audiveris/x2_margem_herdada: 143/162
     homr/nativo: 160/162
  ```

  - A linha `E.` só sai na cópia principal: o `compassos_homr.json` não está no git. Na worktree
    ela não aparece, e não conta.
  - Se não bater, pare e relate. As réguas da Frente 0, depois de commitadas, viram referência
    também.
- **CA2 — a partitura não piora.** Toda mudança que toca a imagem, o recorte, a leitura ou o
  produto mantém:
  - em R01–R12, com o homr confirmado pela tab: certas ≥ 528, e altura errada + inventadas ≤ 7;
  - nas 19 telas dos produtos: certas ≥ 727, inventadas ≤ 7 e altura errada ≤ 9;
  - no gabarito do dono: nenhum símbolo `certo` some sem que a frente explique onde foi parar.
- **CA3 — ganho.** Cada frente tem o seu, definido na seção 7.
- **CA4 — sem um vídeo carregando o resultado.**
  - O ganho aparece em pelo menos 2 vídeos.
  - Nenhum vídeo piora.
  - Reporte também sem a Gymnopédie (392 das 767 notas e 28 das 31 que faltam), sem o athletic
    P01a (31 das 40 que faltam sem produto) e sem o mela (16 das 19 falhas do Audiveris).
- **CA5 — fora da amostra.**
  - Limiar ou regra se escolhe num conjunto e se mede em outro, **declarado antes** no documento
    da rodada. Por padrão: escolha no gabarito de tab (R01–R12 e as 7 telas novas da Gymnopédie)
    e meça no gabarito do dono (R13–R21 e os 3 sem produto) e, quando existir, na amostra D1.
  - Nunca se ajusta olhando o conjunto de teste.
  - Os critérios desta seção estão congelados depois que o dono aprovar.
- **CA6 — determinismo.**
  - Antes de comparar variantes, confira que o Audiveris e o homr dão saída idêntica em duas
    execuções do mesmo recorte. Se não derem, meça a amplitude e exija ganho maior que ela.
  - Pós-processamento: duas execuções dão resultado idêntico.
  - Treino: 3 sementes, média e amplitude, e o ganho tem de ser maior que a amplitude.
- **CA7 — olhar o caso.**
  - 10 casos olhados (5 consertados e 5 quebrados), com o caminho do recorte.
  - Afirmação sobre imagem sem o caminho da imagem não vale.
- **CA8 — gate.** `ruff check`, `ruff format --check` e `pytest` verdes **na worktree**.

---

## 6. Regras para quem trabalha numa worktree

### 6.1 A armadilha principal: `data/saida/` e `artefatos/` não estão no git

**O que falta numa worktree nova.** Ela tem o código e o `data/gold/` do git. Não tem:

- as leituras do Audiveris e do homr, os recortes e os `.partitura.json`;
- os produtos da tab (`data/saida/fase8/`);
- o script do CA1 (`data/saida/partitura/diag/ca1/`);
- o `compassos_homr.json`, que só existe na cópia principal.

**Como montar.** Monte a cópia principal **só para leitura** e, para escrita, só as pastas da sua
frente:

```bash
WT=/caminho/da/sua/worktree
PRINCIPAL=/var/home/gabriel/Projects/chorinho-dataset
FRENTE=f0_regua   # f0_regua | fa_imagem | fb_fusao | fc_polifonico | fd_gabarito | fe_completar
IMAGEM=docker.io/library/chorinho:dev   # localhost/chorinho-partitura:dev para Audiveris e homr
host-spawn -no-pty -cwd "$WT" podman run --rm --security-opt label=disable \
  -v "$WT":/app \
  -v "$PRINCIPAL/data/saida":/app/data/saida:ro \
  -v "$PRINCIPAL/data/saida/part_frentes/$FRENTE":/app/data/saida/part_frentes/$FRENTE \
  -v "$PRINCIPAL/artefatos":/app/artefatos:ro \
  -v "$PRINCIPAL/artefatos/part_frentes/$FRENTE":/app/artefatos/part_frentes/$FRENTE \
  -v /run/media/gabriel/3014CD4714CD1130/chorinho:/acervo:ro \
  -e PYTHONPATH=/app -w /app "$IMAGEM" bash -c "<comando>"
```

- **Imagens.** `chorinho:dev` tem Python, `numpy` e `opencv`. O Audiveris e o homr só existem em
  `localhost/chorinho-partitura:dev` (o homr em `/opt/omr/bin/homr`). O SMT está em
  `localhost/chorinho-partitura:smt` (venv `/opt/smt`).
- **GPU** (só C1): acrescente `--device nvidia.com/gpu=all`.
- **Porta** (ferramenta de conferência): acrescente `-p 127.0.0.1:<porta>:<porta>` e rode o
  servidor com `--porta <porta> --host 0.0.0.0`.
- **Onde a sessão roda.** Se ela roda direto no host, sem distrobox, tire o
  `host-spawn -no-pty -cwd "$WT"`.
- **Confira as montagens antes de medir.** Dentro do container,
  `ls /app/data/saida/partitura/p1/omr/audiveris/x2_margem_herdada` e
  `ls /app/data/saida/partitura/sem_produto` têm de listar arquivos. Se vierem vazios, a montagem
  está errada: **pare**.
- **Scripts que gravam em pasta só de leitura.** Estes não rodam na worktree como estão:
  - `python -m tab.partitura_pareamento` grava em `p3/pareamento/`;
  - `python -m tab.partitura_video recortar`, `ler --produto` e `parear` gravam em `video/<stem>/`;
  - `python -m tab.partitura_omr rodar` e `herdar` gravam em `p1/omr/`.

  Várias funções já aceitam a pasta: `rodar_um(..., pasta_base=..., origem=...)` em
  `tab/partitura_omr.py`, e `ler_pasta(pasta)` e `paginar(video, pasta)` em
  `tab/partitura_video.py` (na CLI: `ler --pasta` e `paginar --pasta`). Quando não aceitam, copie
  a função para o seu módulo e mude **só** o destino (para a pasta da sua frente). Registre o diff
  no documento da rodada.
- **Teste de unidade** não pode depender de `data/saida/`, de `artefatos/` nem do acervo. O gate
  roda sem eles.
- **Aspas.** Comando com aspas aninhadas falha: escreva um `.py` na worktree e rode-o.
- **Gate.** O `ruff` precisa de `--no-cache` e o `pytest`, de `-p no:cacheprovider`, por causa
  da montagem.

### 6.2 Território de cada frente

| frente | pasta de saída (`tab/caminhos.py`) | prefixo de módulo e teste | rodadas | porta |
| --- | --- | --- | --- | --- |
| 0 | `PART_FRENTE_0` → `part_frentes/f0_regua/` | `tab/partitura_regua*.py` | 3101–3109 | — |
| A | `PART_FRENTE_A` → `part_frentes/fa_imagem/` | `tab/partitura_imagem*.py` | 3110–3129 | 8123 |
| B | `PART_FRENTE_B` → `part_frentes/fb_fusao/` | `tab/partitura_fusao*.py` | 3130–3149 | 8124 |
| C | `PART_FRENTE_C` → `part_frentes/fc_polifonico/` | `tab/partitura_polifonico*.py` | 3150–3159 | — |
| D | `PART_FRENTE_D` → `part_frentes/fd_gabarito/` | `tab/partitura_amostra*.py` | 3160–3169 | 8121 |
| E | `PART_FRENTE_E` → `part_frentes/fe_completar/` | `tab/partitura_completar*.py` | 3170–3179 | 8122 |

- Os testes seguem o mesmo prefixo: `tests/test_partitura_regua*.py` e assim por diante.
- As rodadas de 3180 a 3189 ficam para a sessão principal.
- As portas de 8097 a 8099 são das ferramentas do dono; de 8101 a 8104, das frentes das mãos; a
  8111, da Frente C da tablatura.
- As pastas já existem na cópia principal (`data/saida/part_frentes/` e
  `artefatos/part_frentes/`), e as constantes `PART_FRENTE_*` e `PART_FRENTES_PESOS` já estão em
  `tab/caminhos.py`.

### 6.3 O que é proibido

1. **Escrever fora da sua pasta**, inclusive nas pastas de outras frentes, em `partitura/`,
   `fase8/` e `sem_produto/`. A montagem só para leitura existe para isso.
2. **Editar `ESTADO.md`.** Ele é compartilhado e daria conflito entre worktrees. O "não repetir"
   vai no documento da rodada, e a sessão principal consolida no `ESTADO.md`.
3. **Editar o que já existe da partitura no `main`**: os módulos `tab/partitura_*.py` de hoje, os
   testes deles e o padrão do produto (`chorinho/partitura@1`, decisão 3002). Importe e rode. Se
   precisar mudar uma função, copie-a para o módulo da sua frente. A integração é da sessão
   principal, **depois de remedir**.
4. **Editar arquivo de outra trilha**, com os testes dele. Importar e rodar é permitido.
   - mãos e áudio: `tab/maos_*` e `tab/audio_*`;
   - tablatura: `tab/detector_tab.py`, `tab/painel.py`, `tab/ouro_video.py`, `tab/esquema.py`,
     `tab/musicxml.py` e os outros módulos dela;
   - frentes da tablatura: `tab/tecnica_*`, `tab/rolagem_*`, `tab/som_casa_*`, `tab/sonda_*` e
     `tab/gerador_*`.
5. **Gravar em `data/gold/`.** Rótulo só do dono, por leitura visual. A frente monta os itens da
   conferência, e a sessão principal leva ao dono.
6. **Ferramenta do dono.** Para testar a ferramenta de conferência, use uma **cópia** do gabarito,
   nunca o vivo: ela grava a cada clique.
7. **Dependência nova sem o dono.** As imagens têm o que está na seção 6.1. Não têm `musicdiff`,
   Verovio, MV2H, `scipy` nem `scikit-image`. Seção 10.
8. **Copiar código GPL ou AGPL** para o repositório. O Audiveris e o homr são AGPL: rodá-los como
   programa é permitido; copiar ou alterar o código deles, não. Reimplemente a ideia e cite a
   fonte.
9. **GPU sem a trava.** No host, antes de treinar:
   - confira `data/saida/gpu.lock`; se ela existir e não for sua, espere;
   - grave a sua trava (`<frente>, <data>, <duração>`);
   - ao terminar, apague **só a sua**.
10. **Ler vídeo inteiro do HD externo** sem necessidade. É o gargalo de E/S: duas leituras longas
    ao mesmo tempo dobram o tempo das duas. Leia só os quadros de que precisa
    (`tab.leitor.quadro_em`) e registre quantos leu. O `paginar` lê 1 quadro por segundo: rode-o
    em 1 vídeo por vez.
11. **Commit em `main`.** Trabalhe no branch da worktree.

---

## 7. As frentes

Cada teste segue o mesmo molde: **Contexto**, **Hipótese**, **Como**, **Entradas**, **Saída**,
**Aceite**, **Reprova ou para**, **Pegadinhas e falsos positivos**.

---

### Frente 0 — Régua por compasso, troca do homr e tempo pelo par

#### F0.1 — Em que compasso está o erro, e o Audiveris avisa?

**Contexto.**

- O dono conferiu por símbolo, e as notas que faltam são cliques (seção 2).
- O Audiveris grava marcas por compasso no `.omr`: `abnormal`, a duração do `stack` contra a
  esperada e o `grade` de cada símbolo. Em R01–R21 são 148 compassos: 8 `abnormal`, 9 com duração
  diferente da esperada e **88 sem duração esperada**.
- A pesquisa propõe o desvio métrico (Δm > 0) como bandeira (§2) e a soma do ritmo contra a
  fórmula de compasso como juiz (§1, fase 2).
- Ninguém mediu se as marcas caem nos compassos errados.

**Hipótese.** Nenhuma: é medida de partida.

**Como.**

1. Escreva `tab/partitura_regua.py`. Para cada recorte dos dois gabaritos completos (21 + 3), ele
   lê a leitura que o dono conferiu (campo `fonte` do item) e o `.omr` dela.
2. Divida em compassos: o símbolo pelo `compasso` do `palpite`; o clique de faltando pelo x entre
   as barras do `.omr` (seção 5.2).
3. Para cada compasso, guarde:
   - os símbolos e o estado do dono, e os cliques;
   - as marcas do Audiveris: `abnormal`, a soma das durações por voz, a duração esperada, o menor
     e o mediano `grade`;
   - a duração esperada **de duas fontes**, separadas: a do `.omr` e a herdada da fórmula de
     compasso do vídeo (`compassos` e `fracao` no `.partitura.json`, rodada 3015).
4. Faça o mesmo no gabarito de tab: R01–R12 e as 7 telas novas da Gymnopédie.
5. Monte a tabela compasso com erro × marca (`abnormal`; déficit; excesso; `grade` < 0,5;
   nenhuma). Para cada marca: quantos compassos com erro ela acusa e quantos alarmes falsos dá.
   Essa tabela é a referência da B1 e da B2.
6. Recorte cada caso olhado: o recorte vai para a pasta da frente, com o caminho na tabela.

**Entradas.** Os dois gabaritos completos, os itens servidos, as leituras e os `.omr` da seção
5.1, e o gabarito de tab.

**Saída.** `PART_FRENTE_0/regua_compassos.json` e os recortes; rodada 3101.

**Aceite.**

- As contagens por gabarito batem com o CA1: 873 lidos, 852 certos e 78 faltando; 178 lidos, 176
  certos e 40 faltando.
- Duas execuções dão o mesmo resultado.
- Há 5 casos olhados por marca.
- O documento diz, por marca, quantos dos compassos com erro ela acusa e quantos alarmes falsos dá,
  com o denominador.

**Reprova ou para.** Se mais de 10 % dos cliques de faltando não couberem em nenhum compasso (barra
que falta no `.omr`, clique fora da pauta), a régua por compasso não serve. Pare e descreva.

**Pegadinhas e falsos positivos.**

- **R20 e R21.** O R20 não tem os faltando da segunda metade: ele não entra na conta de compasso
  com nota faltando. O R21 é leitura do homr: não tem `.omr` nem marca do Audiveris. Reporte os
  dois à parte.
- **Duração esperada.** 88 dos 148 compassos não têm. A fórmula herdada do vídeo pode estar errada
  (a tela 12 da Gymnopédie tem `fifths` 1, provavelmente errado, rodada 3015). Reporte as duas
  fontes separadas.
- **Compasso curto de verdade.** Anacruse e compasso partido entre duas telas são curtos sem erro.
  Conte-os e olhe.
- **Quiálteras.** Tercina não reconhecida dá déficit falso.
- **Duas vozes.** A soma é por voz. Uma voz que o leitor juntou com a outra estoura a soma sem
  faltar nota.
- **O gabarito de tab não vê figura** e o do dono vê. Não junte os dois na mesma conta.
- **O dono confere contra o desenho** (rodada 3004): sem armadura no recorte, um fá♯ soado sai fá
  "certo".

#### F0.2 — A troca do compasso pelo homr, julgada pela tab

**Contexto.**

- A regra 3025 está no produto sem tab: no compasso em que o homr lê 2× ou mais as notas do
  Audiveris, entra o compasso do homr, com as notas marcadas `homr_sem_confirmacao`.
- Ela só foi medida no athletic P01a, por degrau: recupera 25, inventa 8 e perde 2.
- A conferência do dono contradiz esse recorte e está incompleta (seção 2).
- Nos 3 vídeos com produto há gabarito de tab. Dá para aplicar a regra **sem olhar a tab** e
  julgar **com a tab**.

**Hipótese.** A regra recupera mais notas certas do que quebra, também fora do athletic.

**Como.**

1. Escreva `tab/partitura_regua_troca.py`. Ele aplica `trocar_compassos_pelo_homr` (importado de
   `tab.partitura_pareamento`, com a `RAZAO_TROCA_HOMR` de hoje, 2,0) às leituras do Audiveris com
   armadura herdada (`x2_margem_herdada`), usando a leitura `homr/nativo`. Sem a tab.
2. Faça isso em R01–R12 e nas 7 telas novas da Gymnopédie.
3. Conte contra o gabarito de tab, com `contar` no modo `"exato"`:
   - a referência em R01–R12 é o só Audiveris do CA1 (`[546, 496, 9, 41, 3]`);
   - nas 7 telas novas, grave a referência só Audiveris primeiro.
4. Reporte por tela e por vídeo: consertadas, quebradas, inventadas novas e compassos trocados.

**Entradas.** As leituras da seção 5.1 e o gabarito de tab.

**Saída.** `PART_FRENTE_0/troca.json`; rodada 3102.

**Aceite.** É medida: não tem limiar.

- O número, com o denominador, por vídeo.
- Duas execuções dão o mesmo resultado.
- 10 casos olhados (5 consertados e 5 quebrados), com o caminho do recorte.

**O que vem depois** não é desta frente: se quebradas + inventadas passarem das consertadas, a
sessão principal leva ao dono a proposta de desligar a regra no produto (seção 10, item 5).

**Pegadinhas e falsos positivos.**

- **A referência certa é 496, não 528.** O 528 já usa a tab. A F0.2 simula o caso sem tab.
- **Contagem de compassos diferente.** Quando o homr e o Audiveris têm número de compassos
  diferente, a regra não troca nada (6 recortes do gabarito antigo, rodada 3024). Conte quantos
  recortes ficam assim.
- **A nota trocada não tem x** (o homr não tem `.omr`). Ela não entra no pareamento pelo x: a
  contagem é por sequência, como no CA1.
- **A tab só julga altura.** A figura do homr não é conferida. Conte quantas notas trocadas têm
  figura diferente da do Audiveris na mesma posição.
- **Harmônico** (rodada 3013): nota uma oitava acima da tab no mesmo evento não é erro de leitura.
- **A Gymnopédie domina**: reporte também sem ela (CA4).
- **Os 2 itens válidos do `compassos_homr.json`** não estão na worktree. A sessão principal mede
  esses dois.

#### F0.3 — Quantas notas da partitura ganham tempo pelo par

**Contexto.**

- Regra do dono: o tempo da partitura vem do pareamento com a tablatura.
- A decisão 3002 manda não copiar o tempo para o `.partitura.json`: o consumidor acha o `t_ini` da
  coluna pareada (`tela`, `coluna`) no produto da tab.
- Na tab do produto, há `t_ini` em 209/212 notas da Greensleeves, 215/269 da South American e 0/385
  da Gymnopédie (seção 2).
- Ninguém contou quantos eventos da partitura acabam com segundo, nem conferiu a ordem.

**Hipótese.** Nenhuma: é medida de partida.

**Como.**

1. Escreva `tab/partitura_regua_tempo.py`. Para cada evento com `par` nos 3 `.partitura.json`, ele
   acha as notas do produto com a mesma `tela` e `coluna` e, para cada exibição, o `t_ini`.
2. Conte, por vídeo e por exibição: eventos com tempo, eventos sem par, e par sem `t_ini`.
3. Confira a ordem: dentro de cada exibição, os eventos na ordem da pauta (`compasso`, `t`) têm de
   dar tempo que não volta. Conte as inversões e olhe cada uma: é erro de par ou erro do tempo da
   tab?
4. Não mude o formato do produto.

**Entradas.** Os 3 `.partitura.json` e os 3 produtos da tab com pauta.

**Saída.** `PART_FRENTE_0/tempo.json`; rodada 3103.

**Aceite.**

- O número, com o denominador, por vídeo e por exibição.
- Todas as inversões olhadas, com o caminho do recorte.
- Duas execuções dão o mesmo resultado.

**Pegadinhas e falsos positivos.**

- **O tempo da tab não foi validado** por gabarito (trilha tablatura). A F0.3 mede cobertura e
  ordem, não acerto. Não escreva "tempo certo".
- **Tela repetida** tem várias exibições e, portanto, vários tempos para o mesmo evento. Conte por
  par (evento, exibição).
- **Par pelo x de reserva.** Os eventos com `par.metodo` igual a `"x"` (rodada 3015) vão à parte.
- **Acorde** tem várias notas na mesma coluna e no mesmo tempo: não é inversão.
- **Ligadura e nota de enfeite** não têm ataque próprio. A nota ligada não ganha um segundo novo.
- **O `t` do evento é tempo musical**, não segundo. Não misture os dois.

---

### Frente A — Imagem limpa antes do leitor

#### A1 — Mediana no tempo, cor tirada e moldura branca

**Contexto.**

- No piloto, 19 de 162 recortes não têm leitura nenhuma ("No system found", rodada 3021). Com a
  faixa amarela do cursor, 12 de 36 falham; sem faixa, 7 de 126.
- A faixa só aparece em 2 vídeos (mela e free tab), e o mela tem 16 das 19 falhas.
- A pesquisa propõe (§3):
  - a mediana de N = 15 quadros da exibição, pixel a pixel, que tira o cursor que anda;
  - pintar de branco o pixel com saturação > 0,20 e brilho > 0,40 (HSV), contra caixa colorida
    parada;
  - uma moldura branca de 40 a 60 px em volta do recorte.
- O que temos: margem de 7 entrelinhas (3003); recorte que não para em viga (3022); top-hat só na
  paginação (3017). A rodada 3021 sugeriu usar o maior dos 3 canais (o amarelo vira branco e a
  linha cinza fica). Não há moldura branca hoje.
- Mudar a imagem é mudar a entrada do leitor (`AGENTS.md`, regra 9): exige remedir tudo.

**Hipótese.** Parte das falhas e das notas que faltam vem do cursor e da faixa sobre a pauta.
Limpar a imagem antes do Audiveris recupera recortes sem quebrar os que funcionam.

**Como.**

1. Escreva `tab/partitura_imagem.py`, com funções que recebem o recorte (ou os quadros da
   exibição) e devolvem a imagem limpa, do mesmo tamanho e nas mesmas coordenadas. A moldura é a
   exceção: tire-a das coordenadas depois.
2. Meça cada variante sozinha e, depois, a melhor combinação:
   - **A1a**: mediana de N = 15 quadros espaçados em `[t0, t1]` da exibição, na mesma caixa;
   - **A1b**: o maior dos 3 canais (proposta da 3021);
   - **A1c**: HSV, saturação > 0,20 e brilho > 0,40 viram branco (§3);
   - **A1d**: moldura branca de 50 px em volta do recorte, antes de ampliar 2x.

   Declare N e os limiares antes de medir. Não ajuste no teste.
3. Rode o Audiveris na condição `x2_margem` por `rodar_um`, com `pasta_base` na pasta da frente.
   Meça primeiro nos 36 recortes com faixa e nos 21 do gabarito; os outros 126 do piloto e as 19
   telas dos produtos, só com a melhor variante.
4. Conte como no CA1: pareamento e `contar` nas 19 telas e em R01–R12.
5. Dos recortes recuperados (de falha para leitura), prepare até 6 para a conferência do dono, na
   porta 8123, com uma cópia do gabarito.

**Entradas.** O índice do piloto (`exibicoes`), as telas dos produtos, e os quadros pelo
`tab.leitor.quadro_em` (o AV1 passa pelo `ffmpeg`).

**Saída.** `PART_FRENTE_A/a1.json` e os recortes; rodada 3110.

**Aceite.**

- Nos recortes com faixa, o Audiveris passa de **24/36 para 30/36 ou mais**.
- Dos 143 que já leem, **nenhum** passa a falhar.
- CA2 vale: em R01–R12, certas ≥ 528 e altura errada + inventadas ≤ 7; nas 19 telas, certas ≥ 727,
  inventadas ≤ 7 e altura errada ≤ 9.
- Nos recortes recuperados, conferidos pelo dono: **0,95 ou mais** dos símbolos lidos certos.
- O ganho aparece em pelo menos 2 vídeos (CA4).

**Reprova ou para.**

- Se a mediana dos quadros não bate com o quadro estável (a página muda dentro de `[t0, t1]`), o
  intervalo da exibição está errado. Pare e descreva antes de medir.
- Se o ganho só aparecer no mela, a A1 não passa no CA4. Relate, e a amostra D1 diz quão comum é a
  faixa.

**Pegadinhas e falsos positivos.**

- **Nota pintada.** Há canais que pintam a nota tocada (vermelho, azul). A A1c pinta de branco a
  própria cabeça da nota. Meça a tinta perdida dentro da pauta e olhe.
- **Destaque que fica** a maior parte da exibição sobrevive à mediana. Isso é para a A1b e a A1c.
- **A moldura muda as coordenadas.** Os cliques de faltando do gabarito (`x`, `y`) estão nas
  coordenadas do `recortes_margem`: tire a moldura antes de comparar.
- **Quadro de transição.** Mediana com quadro do fade de página cria nota fantasma. Use só quadros
  de dentro da exibição estável.
- **E/S.** São 15 quadros por exibição, do HD externo: registre quantos leu, 1 vídeo por vez.
- **AV1** só decodifica pelo leitor do projeto (`ffmpeg`). Não use o `cv2.VideoCapture` direto.
- **Tempo de CPU.** São 18 s por recorte no Audiveris. Quatro variantes em 200 recortes passam de
  4 h: siga a ordem do passo 3.

---

### Frente B — Juntar Audiveris e homr sem a tab

#### B1 — Compasso pela soma do ritmo e acorde completado no mesmo tempo

**Contexto.**

- A pesquisa propõe uma fusão em 4 fases (§1):
  1. alinhar os compassos das duas leituras;
  2. **S1**: se a soma do Audiveris não fecha a fórmula de compasso e a do homr fecha, entra o
     compasso do homr;
  3. **injeção vertical**: nota do homr no **mesmo tempo e com a mesma duração** de um acorde do
     Audiveris entra no acorde;
  4. **injeção horizontal com teto**: nota do homr entra só se a soma não passar da fórmula.
- Hoje: a regra 3025 decide pela **contagem** de notas (2×), sem olhar a fórmula. A união cega
  (3005) recuperou 31 de 74, mas inventou 43; eventos só do homr casaram 17 de 62.
- 88 de 148 compassos do R01–R21 não têm duração esperada no `.omr` (a F0.1 diz quantos ganham a
  fórmula herdada).

**Hipótese.** Decidir pela soma do ritmo, com a fórmula do vídeo, recupera tanto quanto a regra
3025 e inventa menos.

**Como.**

1. Escreva `tab/partitura_fusao.py`.
2. Alinhe os compassos pela posição, como a regra 3025. Com número de compassos diferente, não
   funda nada naquele recorte e conte.
3. Regras, declaradas antes no documento da rodada:
   - **B1a (S1)**: soma do Audiveris menor que a esperada e soma do homr igual à esperada → entra o
     compasso do homr, com as notas `homr_sem_confirmacao` (como na 3025). A leitura do Audiveris
     fica guardada;
   - **B1b (vertical)**: num compasso do Audiveris que fecha, nota do homr no mesmo `t` e com a
     mesma figura de um acorde do Audiveris entra no acorde;
   - **B1c (horizontal)**: nota do homr entra só se soma + duração ≤ esperada.
4. Decida sem a tab e julgue com a tab: R01–R12 e as 7 telas novas da Gymnopédie (767 notas).
   Nos 3 sem produto, julgue pelos cliques do dono (régua da F0.1).
5. Compare com o só Audiveris (496 em R01–R12) e com a regra 3025 (F0.2).

**Entradas.** As leituras da seção 5.1, a régua F0.1 e o resultado F0.2.

**Saída.** `PART_FRENTE_B/b1.json`; rodada 3130.

**Aceite**, nas 767 notas, com a decisão tomada sem a tab:

- consertadas − quebradas ≥ 10, contra o só Audiveris com armadura herdada;
- as inventadas sobem no máximo 3;
- melhor que a regra 3025 (F0.2) em consertadas − quebradas − inventadas novas;
- ganho em pelo menos 2 vídeos (CA4);
- os símbolos do homr que entraram, conferidos pelo dono numa amostra de até 60 (porta 8124):
  **0,90 ou mais** certos em altura e figura.

**Reprova ou para.** Se a F0.1 mostrar que menos da metade dos compassos com nota faltando tem
déficit calculável (duração esperada conhecida e soma menor que ela), a S1 tem pouco a ganhar.
Relate e recomende E1 ou B2.

**Pegadinhas e falsos positivos.**

- **Compasso cheio não é compasso certo.** O homr pode fechar a soma com notas erradas (a nota do
  dono no athletic P01a). A tab julga a altura, não a figura.
- **Mudança de fórmula** no meio da música, **anacruse** e **quiáltera** enganam a soma.
- **Vozes.** A soma é por voz, e o Audiveris e o homr separam as vozes de jeitos diferentes.
- **Número de compassos diferente** entre as leituras: não force o alinhamento.
- **A referência certa é 496**, não 528 (o 528 já usa a tab).
- **A Gymnopédie domina**: reporte também sem ela.

#### B2 — Bandeira de confiança por compasso, sem juiz

**Contexto.**

- A pesquisa propõe três sinais (§2): o desvio métrico (Δm > 0) ou a marca de erro do Audiveris; a
  concordância entre leitores (OMR-NED, pelo `musicdiff`); e a probabilidade do decodificador.
- Dá para usar sem dependência nova: as marcas do Audiveris (`abnormal`, duração contra esperada,
  `grade`) e a concordância com o homr contada por nós (número de notas e alturas no mesmo tempo).
- Ficam fora: o `musicdiff` (dependência) e a probabilidade do homr (exige mexer em código AGPL).

**Hipótese.** As marcas do Audiveris, somadas à discordância do homr, acusam a maioria dos
compassos com erro, com poucos alarmes falsos.

**Como.**

1. Escreva `tab/partitura_fusao_confianca.py`. Para cada compasso, ele calcula os sinais:
   `abnormal`; |Δm| com a esperada do `.omr` ou herdada; o menor e o mediano `grade`; e a
   discordância do homr (número de notas e conjunto de alturas por tempo).
2. Escolha a regra e os limiares no gabarito de tab (R01–R12 e as 7 telas novas da Gymnopédie),
   com "compasso com erro" como na F0.1. Escreva-os no documento da rodada **antes** de medir no
   teste.
3. Meça no gabarito do dono (R13–R21 e os 3 sem produto) e, quando existir, na amostra D1, que é o
   teste final.
4. A bandeira só marca: nunca apague nota por causa dela.

**Entradas.** A régua F0.1, as leituras e os `.omr`.

**Saída.** `PART_FRENTE_B/b2.json`; rodada 3140.

**Aceite**, no conjunto de teste, com a regra congelada:

- revocação de **0,6 ou mais** dos compassos com erro;
- alarme falso em **0,15 ou menos** dos compassos sem erro;
- precisão de **0,5 ou mais** (metade dos compassos marcados têm erro de verdade).

**Reprova ou para.** Se no conjunto de escolha a regra não chegar a revocação 0,4 com alarme falso
de 0,2 ou menos, o sinal não existe com os nossos leitores. Relate.

**Pegadinhas e falsos positivos.**

- **Os dois gabaritos veem coisas diferentes.** O de tab não vê figura, e o do dono vê. A regra é
  escolhida num e testada no outro: reporte a diferença.
- **R20 e R21** (seção F0.1): à parte.
- **Recorte sem leitura** ("No system found") é bandeira trivial. Reporte à parte.
- **O `grade` é medida interna do Audiveris.** Ele diz que o leitor hesitou, não que errou (seção
  8, item 10).

---

### Frente C — Leitor de várias vozes treinado (condicional, GPU)

#### C1 — SMT treinado em pauta de violão

**Só comece se** valerem as duas condições:

- depois da A1 e da B1 (e da E1, onde há tab), a cobertura na amostra D1 fica abaixo de 0,90, e
  mais da metade das notas que faltam é de voz ou de acorde, não de imagem;
- o dono aprovou a fonte de música e o uso de GPU (seção 10).

**Ideia** (§4): o SMT (MIT) lê a pauta inteira de uma vez, com várias vozes. Sem treino, o melhor
peso público acerta 20/546 (rodada 3003): os pesos são de piano, fora do nosso domínio.

**Como.**

- Gere pauta de violão (clave de sol com 8, duas vozes) a partir de **arquivos próprios**,
  renderizada por um renderizador aprovado pelo dono (Verovio, LGPL-3.0), com as degradações de
  vídeo do nosso gerador.
- Treine no `localhost/chorinho-partitura:smt` (SMT e `music21` 10.5.0 em `/opt/smt`), com a trava
  da GPU, 3 sementes.
- Nada de PDMX, DadaGP ou GrandStaff como dado (seção 3.3).

**Aceite.**

- cobertura +0,05 sobre a B1 na amostra D1, com precisão dos símbolos lidos de 0,97 ou mais
  (gabarito do dono);
- 3 sementes, ganho maior que a amplitude (CA6);
- CA2 vale.

**Pegadinhas.**

- **Sintético contra real.** O teste sem treino já mostrou o tamanho do buraco (20/546).
- **Texto na pauta**: letra, nome de acorde e dedilhado confundem o leitor.
- **Corpus próprio é pequeno.** Declare quantos arquivos e quantos sistemas distintos entraram.
- **Estilo de canal.** Guitar Pro, MuseScore e Sibelius desenham diferente. Um renderizador é
  **uma** fonte de estilo, não todas.

---

### Frente D — Amostra para um gabarito que vale para o acervo

#### D1 — Um recorte por vídeo, sorteado antes de ler

**Contexto.**

- O gabarito tem 24 recortes de 14 vídeos. O acervo tem cerca de 1.455 vídeos com pauta (rodada
  3001), concentrados em 5 canais.
- ICC medido: 0,023 na cobertura, cerca de 44 notas por recorte (seção 2). Com isso, o efeito de
  desenho é 1 + 43 × 0,023 ≈ 2,0.
- Para p = 0,85 e ± 3 % (95 %), são cerca de 1.090 notas, ou 25 recortes. **Com 40 recortes**
  (cerca de 1.760 notas), a margem fica em ± 2,3 %. O ICC por recorte não mede a variação entre
  canais: por isso, um recorte por vídeo e vários canais.
- O dono leva cerca de 3 min por recorte (seção 2): 40 recortes são cerca de 2 h.

**Hipótese.** Nenhuma: é régua.

**Como.**

1. Escreva `tab/partitura_amostra.py`.
2. **Sorteie antes de ler qualquer coisa**, com semente fixa:
   - população: os vídeos dos canais com pauta no P0 (`p0/amostra.jsonl` e `resumo.json`), no
     acervo de hoje, fora os 14 vídeos dos gabaritos;
   - estratos: 1 vídeo para cada um dos 10 canais com 5 vídeos ou mais estimados; os outros 30,
     proporcionais à estimativa por canal;
   - grave a lista ordenada (com reservas na ordem do sorteio) e commite-a **antes** de rodar o
     `paginar`.
3. Para cada vídeo: `paginar --pasta` na pasta da frente; confira que tem pauta; sorteie 1 recorte
   entre os recortes do vídeo, com a mesma semente; rode o Audiveris (e o homr) nele.
4. Monte os itens com `python -m tab.partitura_gabarito preparar --saida <pasta da frente>`, sirva
   na porta 8121 com uma **cópia vazia** do gabarito e teste os cliques nela.
5. Entregue à sessão principal, que leva ao dono. O dono marca faltando no recorte inteiro.

**Entradas.** `p0/`, o acervo e as imagens com Audiveris e homr.

**Saída.** `PART_FRENTE_D/amostra.json` (lista sorteada, semente, estratos), `itens.json` e os
recortes; rodada 3160.

**Aceite.**

- A lista foi sorteada e commitada antes de qualquer leitura (o hash vai no documento da rodada).
- 40 recortes, de 8 canais ou mais, 1 por vídeo.
- Nenhum recorte trocado por ter saído ruim: recorte sem leitura fica na amostra, com cobertura 0.
- A ferramenta foi testada numa cópia, e o documento estima o tempo do dono.

**Reprova ou para.** Se o `paginar` não achar página em mais de 25 % dos vídeos sorteados que o P0
deu como "com pauta", a amostra puxaria para os vídeos fáceis. Pare e descreva.

**Pegadinhas e falsos positivos.**

- **Trocar recorte ruim enviesa.** Só se troca um vídeo quando ele **não tem pauta** (detector e
  olho), pela próxima reserva, e isso vai registrado.
- **O acervo cresceu.** O P0 contou 2.998 vídeos ativos; hoje são 3.899. Canal novo, sem P0, tem
  peso desconhecido: liste-os e deixe fora da amostra, dizendo isso.
- **Escolha do recorte** é por semente, não "o mais legível".
- **Pauta que rola** (rodada 3017) é um limite do `paginar`. Conte quantos vídeos sorteados são
  assim.
- **O gabarito do dono é leitura do desenho** (rodada 3004).
- **Tempo do dono.** Os 3 min por recorte são do R01–R21. Recorte com muita polifonia leva mais.

---

### Frente E — Completar pela tab o que a pauta não leu

#### E1 — Nota de acorde e ataque isolado pela tab

**Contexto.**

- Com a tab, em R01–R12, sobram **14 notas sem leitura**: a altura vem da tab, mas a figura não
  tem fonte (rodada 3006). Nas 19 telas dos produtos, são **31**.
- A figura das **32 notas do homr** confirmadas pela tab não foi conferida.
- A pesquisa propõe (§5):
  - **passo 3**: nota de acorde que falta entra com a duração e a voz da haste que já existe no
    mesmo x (cordas 4 a 6 vão para a voz 2);
  - **passo 4**: ataque isolado sem cabeça na pauta ganha a duração pelo déficit do compasso e
    pela proporção do x entre os vizinhos.

**Hipótese.** A maioria das notas que faltam é nota de acorde com haste no mesmo x. A figura dela
é a da haste.

**Como.**

1. Escreva `tab/partitura_completar.py`. Ele parte do pareamento (19 telas, tab do produto; e
   R01–R12, tab do gabarito) e, para cada coluna da tab sem nota da partitura com aquela altura:
   - **acorde**: se há evento da partitura no mesmo x (par conferido), a nota entra nele, com a
     figura e a voz do evento (voz 2 para as cordas 4 a 6, se o compasso tem duas vozes);
   - **ataque isolado**: se não há evento, calcule o déficit do compasso (esperada − soma da voz) e
     a proporção do x entre os vizinhos; se o déficit cabe numa figura só, a nota entra com ela;
   - se nada decide, a nota entra **com a altura e figura vazia**. Nunca se descarta.
2. A nota completada sai com `origem` `"tab_completada"`. Os símbolos que já existem não mudam.
3. Prepare a conferência do dono (porta 8122, cópia do gabarito): as notas completadas e as 32 do
   homr. A pergunta é só uma: a figura está certa?

**Entradas.** Os `.partitura.json`, os produtos da tab, o gabarito de tab e as leituras.

**Saída.** `PART_FRENTE_E/e1.json`; rodada 3170.

**Aceite.**

- Na conferência do dono: figura certa em **0,95 ou mais** das notas de acorde, em **0,80 ou mais**
  das notas por déficit e em **0,95 ou mais** das 32 notas do homr.
- Nenhum compasso passa da duração esperada depois de completar.
- Os símbolos que já existiam ficam **idênticos**: confira todos os campos.
- CA2 vale. As notas completadas contam à parte (veja a primeira pegadinha).

**Reprova ou para.** Se mais da metade das notas que faltam não tiver nem evento no mesmo x nem
déficit calculável, a E1 tem pouco a dar. Relate.

**Pegadinhas e falsos positivos.**

- **A altura é circular.** Em R01–R12 a altura completada vem da tab do gabarito e é julgada contra
  ela: sai "certa" por construção. O que a E1 mede de verdade é a **figura**. Nas 19 telas a tab é
  a do produto, que tem 21 alturas erradas: conte quantas notas completadas herdam um erro da tab.
- **Harmônico** (rodada 3013): a tab escreve o som e a pauta, a nota presa. Não complete um
  harmônico como nota nova.
- **Nota ligada.** A tab pode repetir a casa entre parênteses, como `(6)`. Isso não é ataque novo:
  não complete.
- **A regra da voz** (cordas 4 a 6 na voz 2) é da pesquisa, não do dono. Ela vai para a
  conferência também.
- **Pausa.** A tab não tem pausa. O déficit pode ser uma pausa, não uma nota.
- **Tela 10 da Gymnopédie**: a tab do produto tem as cordas deslocadas (rodada 3014). Use o par
  pelo x, e conte à parte.

---

## 8. Pegadinhas que valem para todas as frentes

1. **Número da pesquisa não é meta.**
   - O "81,5 % para 96,5 %" mistura dois gabaritos (seção 3.4).
   - O "~95 %" de Padilla e o "99 % com OMR-NED zero" não foram conferidos.
   - Nenhum número de `partitura.md` serve de critério de aceite nem de argumento de que "deve
     funcionar".
2. **Referência não conferida não existe.** Só os itens da seção 3.4 foram conferidos. Confira o
   resto antes de depender.
3. **O recorte é parte da medida** (`AGENTS.md`, regra 9). Mudou margem, escala, moldura, mediana
   ou cor? Remeça a referência com a mudança antes de comparar.
4. **Gabarito parcial.**
   - O R20 vale só para os símbolos lidos.
   - O `compassos_homr.json` está incompleto e não está no git.
   - O clique de faltando não tem figura.
5. **Os dois gabaritos respondem perguntas diferentes.** O do dono é leitura do desenho, com
   figura. O de tab é altura, sem figura, e o harmônico é uma oitava diferente (rodada 3013).
6. **Um vídeo carregando.** A Gymnopédie tem 392 das 767 notas e 28 das 31 que faltam; o athletic
   P01a tem 31 das 40 que faltam sem produto; o mela tem 16 das 19 falhas. Reporte com e sem eles.
7. **Troca não é ganho.** Mais cobertura com mais inventadas não se adota: a união cega da 3005
   levou as certas de 491 para 520 e as inventadas de 3 para 43.
8. **Afirmação sobre imagem precisa da imagem.** Toda frase sobre o que aparece num recorte vem
   com o caminho dele. O revisor vai abrir.
9. **Símbolo não se descarta** (`AGENTS.md`). Nota sem figura fica com a altura e a figura vazia;
   a leitura do Audiveris fica guardada quando o compasso é trocado (3025). Perder informação é o
   único erro inaceitável.
10. **Medida interna não é validação.** `grade` do Audiveris, concordância entre leitores e
    "compasso cheio" dizem que o leitor está seguro, não que está certo. Valem o gabarito do dono,
    a tab ou o olho.
11. **O tempo vem da tab.** Nenhuma frente cria medidor de tempo próprio para a partitura (regra do
    dono).
12. **Leitor determinístico?** Antes de comparar variantes, confira que o Audiveris e o homr dão a
    mesma saída em duas execuções (CA6).

---

## 9. O que cada frente entrega

1. **Código** com o prefixo da frente e testes de unidade sem `data/saida/`, sem `artefatos/` e
   sem acervo. O gate tem de estar verde na worktree.
2. **Saídas** só na pasta da frente. Pesos só em `artefatos/part_frentes/<frente>/`, com comando e
   semente.
3. **Documento de rodada** na faixa da frente, com estas partes:
   - a pergunta;
   - limiares e regras a priori, escritos antes da medida;
   - a checagem da fonte (existe, licença, número);
   - a tabela no formato da seção 5.2, com consertadas e quebradas;
   - os 10 casos olhados, com as imagens;
   - o que deu errado e o "não repetir".
4. **Commit no branch da worktree**, com o número medido na mensagem. Não commitar em `main`.
5. **Resumo para o dono** em português, curto:
   - o que a frente acha, conserta ou quebra, e se passou nos critérios;
   - o que ela **não** prova.

A sessão principal remede o número antes de integrar e consolida o `ESTADO.md`.

---

## 10. Decisões do dono (pendentes)

Cada item traz a minha recomendação. Nada abaixo vale antes da resposta do dono.

1. **Dependências.**

| dependência | frente | licença | recomendação |
| --- | --- | --- | --- |
| `musicdiff` (e `music21` no venv principal) | B2 | MIT / BSD-3 | **não agora**: a B2 começa com as marcas do Audiveris e a concordância com o homr contadas por nós |
| `homr[cuda]` (homr na GPU) | — | AGPL-3.0 | **não agora**: em CPU já dá 7 a 9 s por recorte, e a GPU é disputada |
| MV2H | — | MIT (Java) | **não**: pede a partitura de referência inteira, que não temos |
| Verovio | C1 | LGPL-3.0 | **só se a C1 abrir** |
| treino do SMT | C1 | MIT | já está na imagem `chorinho-partitura:smt`; **treinar só se a C1 abrir**, com GPU e trava |
| LEGATO | — | código MIT; codificador Llama 3.2 Vision, de acesso fechado | **não** |
| Ultralytics (YOLO) | — | AGPL-3.0 | **não usar** |

   A dependência entra na imagem só no branch da frente. Quem muda o `Dockerfile.partitura` no
   `main` é a sessão principal, depois de remedir.
2. **Música para treinar a C1.** Recomendo **arquivos próprios**: nada de PDMX, DadaGP ou
   GrandStaff (licença por arquivo, domínio de piano, e o DadaGP já foi descartado nas outras
   trilhas).
3. **Gabarito novo que o dono rotularia** (em sessões separadas, cerca de 3,5 h no total):

| o quê | frente | quanto | tempo estimado |
| --- | --- | --- | --- |
| amostra estratificada | D1 | 40 recortes, 1 por vídeo | cerca de 2 h |
| figura das notas completadas e das 32 do homr | E1 | cerca de 30 a 80 notas | cerca de 45 min |
| recortes recuperados pela imagem limpa | A1 | até 6 recortes | cerca de 20 min |
| símbolos do homr que entraram pela fusão | B1 | até 60 símbolos | cerca de 20 min |
| refazer agua P10a (desenho falhou) e athletic P01a (incompleto) | — | 2 recortes | cerca de 10 min |

   Recomendo que o dono marque faltando **no recorte inteiro**, sempre (a lição do R20).
4. **Quais gabaritos valem como completos.** Recomendo:
   - `leitura_p1.json`: completo, menos o faltando do R20;
   - `leitura_sem_produto.json`: completo. Posso corrigir o campo `fonte_itens`, que aponta para os
     itens errados? Mexer em `data/gold/` só com a sua autorização;
   - `compassos_homr.json`: **incompleto** (só 2 de 4 valem). Não usar como régua, e não commitar
     até refazer. Os 13 itens que faltam esperam a F0.2.
5. **A regra 3025 no produto.** Recomendo **manter**, com as notas marcadas `homr_sem_confirmacao`,
   até a F0.2 medir. Se quebradas + inventadas passarem das consertadas, desligar.
6. **O que fica fora.** Recomendo aceitar a lista da seção 3.3 como está.
7. **Critérios de aceite.** Recomendo aprovar e congelar os da seção 5.3 e os de cada frente na
   seção 7. Mudar um limiar depois de ver o resultado invalida a frente.

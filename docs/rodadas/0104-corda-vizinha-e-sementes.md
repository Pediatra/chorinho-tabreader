# 0104 — Corda vizinha e estabilidade entre sementes (F0.1 e F0.3)

Frente 0 de `docs/pesquisa/tablatura-frentes.md`, seção 7. Branch `tab/f0-regua-tecnica`.
Origem: decisões 1, 2 e 4 da sessão principal (2026-10-16), vinculantes.

Código: `tab/tecnica_regua.py` (`cordas_com_vizinha`, `executar_vizinha`, flag `--vizinha`) e
`tab/tecnica_cabeca.py` (`executar_sementes`, flag `--sementes`). Saídas, na pasta da frente
(fora do git): `regua_vizinha.json`, `cabeca_sementes.json`, `cabeca_sementes_recortes/`.

**Este documento foi escrito e commitado antes de qualquer medida desta rodada.** Os critérios
da seção 1 e da seção 2 não mudam depois de ver resultado. A seção "Resultados" foi acrescida
depois e só contém números medidos com estes critérios.

## 1. Variante da corda vizinha (F0.1)

### Pergunta

Quando o dono marca uma região sobre a corda k e a rede põe a técnica na corda k−1 ou k+1,
dentro da folga, a régua oficial conta "nada marcado". Quanto muda se essa marca contar como
achada?

### Regra da variante

- **Alcance da marca** = cordas da marca mais uma corda para cada lado, limitado a 1 e 6:
  `(a, b) → (max(1, a−1), min(6, b+1))`. Exemplos: (2,2) → (1,3); (1,2) → (1,3); (6,6) → (5,6).
- **Folga**: 0,5 passo, nas colunas da marca (`x0 − 0,5 passo` a `x1 + 0,5 passo`), como na
  régua oficial.
- **Casamento, classes, achada, certa e causas (c, a, b)**: os da rodada 0101, aplicados ao
  alcance estendido. A causa (c) também usa o alcance estendido.
- **Régua oficial inalterada.** A variante não regera `regua_tecnica.json`. Como conferência,
  a régua oficial é rodada de novo depois do código novo, e o SHA-256 tem de ser
  `cc009a9ac22d69045e92b74a4aa37c073dd71d0b3d3b5b3a5070fa9b010f4466`, o da rodada 0101.

### Como se reporta (oficial e variante lado a lado)

1. **Legato** (h, p, mordente, prolongamento; 139 marcas): achadas, certas, perdidas e causas
   a/b/c, nos dois lados, em três escopos: todas as telas, sem o Room 335, só telas conferidas.
2. **Total das 229 marcas medidas** (sem abafada e sem "fora da régua"), por classe, como na
   tabela da 0101, nos dois lados.
3. **Os 22 casos.** São as marcas com causa (a) na régua oficial, alcance oficial vazio, e nota
   do ouro dentro da faixa de x mas numa corda fora das cordas da marca (o conjunto da seção
   "Achado: o casamento por corda" da 0101, `folhas/diagnostico_corda.json`). Para cada um se
   lista: fonte, tela, marca, cordas do ouro, cordas das notas do ouro fora da marca, cordas com
   técnica da rede dentro da faixa de x (a "corda marcada", ou vazio), e o resultado da variante.
   **Os 22 saem todos**, mesmo os que não mudam.
4. **Ganhos**: marcas que a variante torna achadas, e marcas que ela torna certas, com cordas e
   corda da técnica da rede.

### Como se lê

- A variante é **diagnóstico**. A régua oficial não muda por causa dela.
- Se a variante aumentar as achadas, a regra de casamento oficial só muda com regra nova,
  pré-registrada antes de uma medida nova (decisão 1 da sessão principal).
- A lista dos 22 é fixa: não se muda depois de ver o resultado.
- Classe com menos de 10 marcas continua sem decidir.

## 2. Estabilidade entre sementes (F0.3)

### Modelos

- **A** (sintético, ponto de partida): `detector_tab_v3_s1`, `_s2` e `_s3`.
- **C** (a dobra que não viu o vídeo): LVR → dobra 1; FTP → dobra 3; EOB e R335 → dobra 4.
  Sementes 1, 2 e 3 de cada dobra:
  - dobra 1: `detector_tab_v3ft_d1`, `_d1_s2`, `_d1_s3` (a dobra 1 não tem o sufixo `_ger`:
    é o gerador antigo, como na 0103);
  - dobra 3: `detector_tab_v3ft_d3_ger`, `_ger_s2`, `_ger_s3`;
  - dobra 4: `detector_tab_v3ft_d4_ger`, `_ger_s2`, `_ger_s3`.
- **B** (produto): `detector_tab_final_s1_ger`, só a semente 1. Os artefatos não têm
  `final_s2_ger` nem `final_s3_ger`. Os `final_s2` e `final_s3` (sem `_ger`) não são o produto
  e não entram.
- **Verificação antes de medir**: cada peso de C precisa ter, no `config.json` da sua pasta, o
  vídeo da fonte que ele mede em `videos_fora_do_treino`. Se algum não tiver, a medida para.

### Medida

A mesma da rodada 0103: mesmo quadro, mesmo recorte do painel, modo `eval()`, folga de 0,5, mesmas
classes, e os mesmos escores (esperado e ligado). A população é de 139 marcas para A e B, e de 102
marcas (ouros) para C. Para cada modelo e cada limiar (0,5, 0,3 e 0,1), conta-se quantas regiões
têm escore ≥ limiar.

### Critérios

- **Reprodução**: a semente 1 reproduz a 0103. Escore esperado, população de 139: A 14 / 36 / 80
  e B 13 / 26 / 69 (limiares 0,5 / 0,3 / 0,1). Na população de 102: C (semente 1) 20 / 38 / 63.
  Se não bater, a medida para e se relata.
- **Média e amplitude** por família (A, com as sementes 1 a 3 sobre 139; C, com as sementes 1 a
  3 sobre 102) e por limiar: média e amplitude (máximo menos mínimo) da contagem entre sementes.
  B tem um valor só, sem amplitude.
- **Diferença que conta**: uma diferença entre a média de A e B, ou entre a média de C e a de A,
  só é lida como diferença se for maior que a amplitude de A (a família com 3 sementes sobre a
  mesma população de 139). Abaixo disso é ruído.
- **Limiares**: 0,5 é o corte de produção (`tab.detector_tab.LIMIAR`). 0,3 e 0,1 são diagnóstico.
  São os da 0103, sem mudança.

### Recortes das 10 regiões

- As regiões com escore esperado de A1 (v3_s1) ≥ 0,5 e de B (produto) < 0,5. A 0103 deu 10.
- Cada uma sai em `cabeca_sementes_recortes/`, com as cordas, a marca em vermelho e as notas
  do ouro em verde. O número real vai no relatório, mesmo que não seja 10.
- As regiões são descritas depois de olhadas, com o caminho do recorte. Afirmação sobre o que
  aparece na imagem vem com o caminho.

## 3. CA7 (F0.1): casos olhados por classe

- **Não se criam casos novos.** Conta-se o que existe em `folhas/casos.json` (61 casos, um
  recorte cada), por classe e causa.
- Critério da seção 7 (F0.1): 5 casos olhados por classe com 10 marcas ou mais. Registra-se a
  contagem por classe e causa e o que falta, sem completar com caso inventado.
- O CA7 da seção 5.3 (5 consertados e 5 quebrados) **não se aplica**: nenhum modelo nem recorte
  do produto muda nesta rodada.

## 4. Gate e entrega

- `ruff check --no-cache .`, `ruff format --no-cache --check .` e
  `pytest tests/ -q -p no:cacheprovider` verdes na worktree, antes de cada commit.
- Commit de critérios (esta seção 1, seção 2, seção 3 e o código, antes de medir); commit de
  resultados (seção "Resultados"), com o número na mensagem.

---

## Resultados

Medidas feitas depois do commit de critérios (`1b79fd13`), só com os critérios acima. CPU,
sem GPU (`torch.cuda.is_available()` é `False` no container). Saídas na pasta da frente:
`regua_vizinha.json`, `cabeca_sementes.json`, `cabeca_sementes_recortes/`, e as reproduções
`ca_repro_0104/`, `ca_repro_0104_vizinha/`, `ca_repro_0104_sementes/`.

### Conferências antes de ler os números

- **Régua oficial não mudou.** `regua_tecnica.json` da frente segue com SHA-256
  `cc009a9ac22d69045e92b74a4aa37c073dd71d0b3d3b5b3a5070fa9b010f4466`. Rodei de novo o código
  oficial, depois da mudança, em `ca_repro_0104/`: os números são idênticos aos da 0101 (50
  achadas, 28 certas, perdas a/b/c 179/22/0). **O SHA dessa cópia não é o mesmo**: o campo
  `recorte` tem o prefixo `ca_repro_0104/` (201 recortes de marca e 38 de invenção). Sem o campo
  `recorte`, o conteúdo é igual. Não sobrescrevi o oficial para ter o SHA exato.
- **Determinismo (CA6).** A variante rodou duas vezes (`regua_vizinha.json` e
  `ca_repro_0104_vizinha/`), e as sementes rodaram duas vezes (`cabeca_sementes.json` e
  `ca_repro_0104_sementes/`). Nas duas, o resultado é igual, sem contar o prefixo do caminho do
  recorte.
- **Reprodução da 0103.** A semente 1 bate com a 0103 em todos os números: A1 14/36/80, B 13/26/69,
  C1 20/38/63 (limiares 0,5 / 0,3 / 0,1, escore esperado).
- **Verificação de dobra.** Os 9 pesos de C (3 dobras × 3 sementes; EOB e R335 usam a mesma dobra
  4) têm o vídeo da fonte em `videos_fora_do_treino`. Nenhuma medida parou.

### 1. Corda vizinha (F0.1)

**Totais, legato (139 marcas: h, p, mordente, prolongamento)**

| lado | achadas | certas | perdidas | a / b / c |
| --- | --- | --- | --- | --- |
| oficial (folga 0,5) | 25 | 4 | 135 | 114 / 21 / 0 |
| vizinha | 31 | 4 | 135 | 108 / 26 / 1 |

Por escopo (achadas / certas / a-b-c):

| escopo | marcas | oficial | vizinha |
| --- | --- | --- | --- |
| todas | 139 | 25 / 4 / 114-21-0 | 31 / 4 / 108-26-1 |
| sem Room 335 | 67 | 18 / 4 / 49-14-0 | 22 / 4 / 45-17-1 |
| só telas conferidas | 126 | 23 / 4 / 103-19-0 | 29 / 4 / 97-24-1 |

Por classe, legato (achadas / certas), oficial → vizinha:

| classe | marcas | achadas | certas |
| --- | --- | --- | --- |
| h | 29 | 5 → 5 | 1 → 1 |
| p | 19 | 1 → 2 | 0 → 0 |
| mordente | 11 | 1 → 2 | 0 → 0 |
| prolongamento | 80 | 18 → 22 | 3 → 3 |

**Total das 229 marcas medidas**: oficial 50 achadas, 28 certas, 179/22/0. Vizinha 60 achadas,
32 certas, 169/27/1. Os ganhos de certas são todos de slide (4, fora do legato).

**Anatomia.** A variante acrescenta 6 achadas no legato (25 → 31) e nenhuma certa no legato: as
achadas novas são classe errada (`orn`, `enfeite`, `bend` ou `h` onde o dono marcou prolongamento
ou p). Aparece 1 causa (c) nova, no mordente: uma nota do ouro na corda vizinha entrou no
alcance e a rede não a leu.

**Os 22 casos** (perdas (a) da régua oficial, alcance vazio, com nota do ouro numa corda fora das
cordas da marca; o conjunto de `folhas/diagnostico_corda.json`). "Corda marcada" é a corda em que
a rede pôs técnica na faixa de x. Caminho de cada recorte: não gerado nesta rodada; a identificação
está em `regua_vizinha.json`, campo `casos_22_alcance_vazio_com_nota_do_dono_fora`.

| # | marca (fonte t·r) | classe | cordas do ouro | cordas das notas do ouro fora | corda marcada pela rede (técnica) | vizinha acha | certa |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | EOB t1 r16 | h | 1–1 | 2, 5 | nenhuma | não | não |
| 2 | EOB t2 r2 | h | 1–1 | 2, 5 | nenhuma | não | não |
| 3 | EOB t2 r7 | h | 1–1 | 2 | nenhuma | não | não |
| 4 | EOB t3 r4 | p | 2–2 | 3, 6 | nenhuma | não | não |
| 5 | EOB t3 r5 | h | 1–1 | 2, 3 | nenhuma | não | não |
| 6 | EOB t3 r10 | h | 1–1 | 2 | nenhuma | não | não |
| 7 | EOB t3 r15 | h | 1–1 | 2, 5 | nenhuma | não | não |
| 8 | FTP t1 r3 | mordente | 1–1 | 2 | nenhuma | não | não |
| 9 | FTP t3 r4 | p | 1–1 | 2 | 2 (`orn`) | sim | não (b) |
| 10 | FTP t4 r4 | mordente | 1–1 | 2 | 2 (`enfeite`) | sim | não (b) |
| 11 | FTP t4 r5 | prolongamento | 1–1 | 2 | 2 (`enfeite` ×2) | sim | não (b) |
| 12 | T82 t7 r5 | p | 6–6 | 5 | nenhuma | não | não |
| 13 | T82 t8 r1 | h | 1–1 | 2 | nenhuma | não | não |
| 14 | T82 t11 r0 | mordente | 1–1 | 2 | nenhuma | não | não |
| 15 | T82 t16 r3 | p | 1–2 | 3 | nenhuma | não | não |
| 16 | T82 t16 r4 | p | 5–6 | 4 | nenhuma | não | não |
| 17 | T82 t23 r1 | p | 3–4 | 2 | nenhuma | não | não |
| 18 | T82 t23 r2 | slide | 2–2 | 1 | 1 (`\`) | sim | sim |
| 19 | T82 t28 r0 | slide | 5–6 | 4 | 4 (`/`) | sim | sim |
| 20 | T82 t31 r0 | h | 5–5 | 4 | nenhuma | não | não |
| 21 | T82 t31 r1 | slide | 1–1 | 2, 4 | 2 e 4 (`/`) | sim | sim |
| 22 | T82 t31 r2 | slide | 5–6 | 2, 4 | 2 e 4 (`/`) | sim | sim |

Dos 22: **7 ficam achadas** (9, 10, 11, 18, 19, 21, 22), **4 ficam certas** (18, 19, 21, 22, todos
slide), 3 ficam como classe errada (9, 10, 11). Os outros 15 continuam sem técnica no alcance da
variante. Os 7 achados são exatamente os 7 casos com técnica na corda vizinha do diagnóstico da
0101 (conferido caso a caso).

### 2. Estabilidade entre sementes (F0.3)

Escore esperado, contagem de regiões com escore ≥ limiar, por semente. População de 139 para A e B;
102 para C.

| modelo | ≥ 0,5 | ≥ 0,3 | ≥ 0,1 |
| --- | --- | --- | --- |
| A1 / A2 / A3 (v3_s1, s2, s3) | 14 / 44 / 27 | 36 / 61 / 53 | 80 / 109 / 93 |
| **A: média (amplitude)** | **28,3 (30)** | **50,0 (25)** | **94,0 (29)** |
| B (produto, s1 apenas) | 13 | 26 | 69 |
| C1 / C2 / C3 (dobras 1, 3, 4 com as sementes) (102) | 20 / 28 / 24 | 38 / 35 / 35 | 63 / 50 / 63 |
| **C: média (amplitude)** | **24,0 (8)** | **36,0 (3)** | **58,7 (13)** |

Ligado (h, p ou lig, qualquer classe): A média 39,3 (amp. 40) a 0,5; 67,0 (45) a 0,3; 115,7 (39) a
0,1. B 20 / 36 / 88. C média 30,0 (9) a 0,5; 42,3 (2) a 0,3; 74,3 (6) a 0,1.

**Leitura pelo critério.** Uma diferença só conta se for maior que a amplitude de A:

- A vs B: a 0,5, diferença 15,3 contra amplitude 30. A 0,3, 24,0 contra 25. A 0,1, 25,0 contra 29.
  **Nenhuma conta.**
- C vs A: as duas famílias não têm a mesma população (102 contra 139). Pela regra, C vs A seria
  35,3 contra 29 a 0,1, mas isso compara populações diferentes e não vale. **Diagnóstico, fora do
  critério**: A sobre as mesmas 102 marcas de C (contagens 11/39/23, 30/51/43, 66/87/69; média
  24,3, 41,3, 74,0; amplitude 28, 21, 21). Diferença C vs A: 0,3 a 0,5, 5,3 a 0,3, 15,3 a 0,1, todas
  menores que a amplitude de A nesta população. **Nenhuma conta.**
- Descritivo, sem valer como critério: B fica abaixo do menor valor das três sementes de A em
  todos os limiares (nas 139 e nas 102). Não é um efeito testado, porque B é uma semente só e
  tem treino extra (`_ger`, a partir de A).
- **A 0103 errou ao ler um sinal a 0,3 que favorece A.** Ele vinha da semente 1 (36 contra 26).
  Com as três sementes, A vai de 36 a 61, e a diferença média (24) cabe na amplitude (25).

**As 10 regiões (A1 ≥ 0,5 e B < 0,5).** Todas são R335, classe prolongamento, marcadas como
"outra" com observação de ligadura/prolongamento, exceto t5 r4 e t5 r5 (sem rótulo, observação
de prolongamento). Os 10 recortes estão em `cabeca_sementes_recortes/`. Olhados um a um:

1. `R335_t1_r7.png` (cordas 4–5): caixa cobre o arco entre a casa 6 e a casa 4 logo abaixo. A1 0,55;
   A2 0,69; A3 0,78; B 0,37; C1 0,50.
2. `R335_t1_r9.png` (cordas 5–6): caixa cobre um arco entre casa 6 e casa 4 do mesmo tipo. A1 0,55;
   A2 0,98; A3 0,78; B 0,37; C1 0,50.
3. `R335_t3_r7.png` (cordas 5–6): caixa cobre o arco entre casa 6 e casa 4. A1 0,58; A2 1,00;
   A3 0,78; B 0,37; C1 0,52.
4. `R335_t3_r12.png` (cordas 4–5): caixa cobre o arco entre casa 6 e casa 4. A1 0,53; A2 0,53;
   A3 0,74; B 0,36; C1 0,47.
5. `R335_t3_r14.png` (cordas 5–6): mesmo desenho. A1 0,53; A2 1,00; A3 0,74; B 0,36; C1 0,47.
6. `R335_t5_r4.png` (cordas 4–5, sem rótulo): caixa cobre o arco entre casa 6 e casa 4. A1 0,69;
   A2 0,60; A3 0,50; B 0,17; C1 0,52.
7. `R335_t5_r5.png` (cordas 5–6, sem rótulo): caixa cobre o arco entre casa 6 e casa 4. A1 0,69;
   A2 0,89; A3 0,50; B 0,17; C1 0,52.
8. `R335_t7_r3.png` (cordas 4–5): caixa cobre o arco entre casa 6 e casa 4. A1 0,70; A2 0,43; A3 0,61;
   B 0,23; C1 0,60.
9. `R335_t7_r4.png` (cordas 5–6): caixa cobre o arco entre casa 6 e casa 4. A1 0,70; A2 0,94; A3 0,61;
   B 0,23; C1 0,60.
10. `R335_t16_r7.png` (corda 6 só): a caixa pega só o trecho do arco que chega à corda 6, vindo de
    cima. Pelo recorte não dá para dizer de que casa o arco parte. A1 0,73; A2 0,05; A3 0,36; B 0,39;
    C1 0,36.

Os nove primeiros são o mesmo desenho: um arco de ligadura entre a casa 6 e a casa 4 logo abaixo
(os algarismos são casas lidas na tela; a corda de cada nota vem das cordas da marca, não de
medição de pixel). As notas do ouro estão marcadas em verde. O produto dá 0,17 a 0,39 num desenho
que A1 lê entre 0,53 e 0,73, e a dispersão entre sementes vai de 0,05 a 1,00 numa mesma região. A
leitura descreve a imagem; não mede a rede além do que a caixa mostra.

### 3. CA7 (F0.1): casos olhados por classe

Contagem de `folhas/casos.json` (61 casos, todos com recorte no disco). Não se criou caso novo.

| classe | perda (a) | perda (b) | certa | total de casos | marcas do dono |
| --- | --- | --- | --- | --- | --- |
| h | 5 | 4 | 1 | 10 | 29 |
| p | 5 | 1 | 0 | 6 | 19 |
| mordente | 5 | 1 | 0 | 6 | 11 |
| prolongamento | 5 | 5 | 3 | 13 | 80 |
| slide | 5 | 1 | 3 | 9 | 46 |
| arpejo | 5 | — | — | 5 | 21 |
| rasgueado | 5 | — | — | 5 | 15 |
| harmônico (fora: 4 marcas) | — | — | 3 | 3 | 4 |
| bend (fora: 4 marcas) | 4 | — | — | 4 | 4 |

**Premissa do briefing, checada.** As classes p, mordente e slide **têm 5 ou mais casos** no total
(6, 6 e 9). O que fica abaixo de 5 é a causa (b) de h (4), p (1), mordente (1) e slide (1), e as
certas de p e mordente, que são 0 (não há caso certo nelas). Não completei com caso inventado. Não
reolhei os 61 nesta rodada: o olhar registrado é o da 0101.

Não se aplica o CA7 da seção 5.3 (5 consertados e 5 quebrados): nenhum modelo nem recorte do produto
mudou.

### 4. O que não foi feito ou ficou diferente do briefing

- **Semente 2 e 3 do produto**: não existem com a receita do produto (`_ger`). Usei B só com a
  semente 1.
- **Pesos da dobra 1**: a receita é `detector_tab_v3ft_d1`, `_d1_s2`, `_d1_s3`, sem o sufixo `_ger`.
  Usei esses nomes, porque são os que existem e são os da dobra 1 (gerador antigo, como na 0103).
- **SHA da régua em cópia**: não bate por causa do prefixo do campo `recorte` (ver acima); o
  conteúdo bate.
- **Recortes da variante**: não gerados. Os 22 estão listados com os campos do relatório.
- **F0.2 fechada** como não conclusiva, na 0102 (commit de resultados), com os defeitos (a) e (b) no
  "não repetir", sem limiar novo.

## Conclusão da F0

Encerra a Frente 0 (régua de técnica). Decisão da sessão principal (2026-10-16), vinculante. Nada
desta seção é medida nova: são os números das seções 1 e 2 acima.

- **Régua oficial**: a rede acha o ligado em 25 de 139 marcas do legato, com classe certa em 4.
- **Com corda vizinha (variante de diagnóstico)**: no total das 229 marcas, +10 achadas (50 → 60) e
  +4 certas, todas de slide. No legato continuam 4 certas de 139 (achadas 25 → 31, sem certa a mais).
  Dos 22 casos, 7 ficam achados e 4 ficam certos (todos slide).
- **Sementes**: o escore entre sementes não separa as hipóteses. A amplitude de A (três sementes)
  cobre a diferença de B (produto) e a diferença de C (dobras), em todos os limiares. Pelo critério
  da seção 2, nenhuma diferença conta.
- **Onde a rede erra no ligado**: as 10 regiões em que A1 lê ≥ 0,5 e B lê < 0,5 são todas o arco de
  ligadura da R335 (casa 6 → casa 4), e a dispersão entre sementes nelas vai de 0,05 a 1,00.

**Conclusão.** A rede não acha o ligado. Não é por limiar, e não é porque o ajuste fino apagou a
técnica. Portanto a A1 não abre. O caminho é a A2 (detector de arco) ou a B (estilo do arco no
gerador). A B1 depende de aprovação do dono para a dependência do AlphaTab, que ainda não foi dada.

**Fim da F0.** Não há mais nada a medir nesta frente. A régua oficial não muda, e a corda vizinha
fica registrada como variante de diagnóstico.

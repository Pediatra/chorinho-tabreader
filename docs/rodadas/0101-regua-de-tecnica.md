# 0101 — Régua de técnica: o que a rede acerta das marcas do dono (F0.1)

Frente 0 de `docs/pesquisa/tablatura-frentes.md`, seção 7. Branch `tab/f0-regua-tecnica`.
Saída: `data/saida/tab_frentes/f0_tecnica/` (`regua_tecnica.json`, recortes, folhas).

## Pergunta

Quando o dono marca uma técnica numa região da tela, a rede (`tab.detector_tab`) acha essa
técnica? Acha a classe certa? Quando erra, é porque não marcou nada, marcou outra classe,
ou nem leu a nota?

## Pré-registro (escrito antes de medir a técnica)

Esta seção foi escrita antes de qualquer número de técnica. Não muda depois de ver resultado.

### Entradas

- **Marcas**: 415 regiões, nos campos `regioes` de 5 fontes (`data/gold/ouro_video/*.json`
  e `data/saida/t82/ferramenta/conferencia_t82.json`):

  | fonte | regiões | telas com marca | telas conferidas |
  | --- | --- | --- | --- |
  | End of Beginning | 114 | 7 | 7 de 22 |
  | La Vie en Rose | 5 | 4 | 8 de 8 |
  | From This Place | 32 | 5 | 5 de 5 |
  | Room 335 | 177 | 13 | 11 de 42 |
  | T8.2 (18 canais) | 87 | 24 | 35 de 35 |

  No Room 335, 34 regiões estão em telas **não conferidas** (telas 19 e 22). Elas entram nas
  415 marcas (a soma precisa dar 415), e a conta "só telas conferidas" as tira.

- **Leitura primária (produto)**: `artefatos/detector_tab_final_s1_ger`, lido no quadro da
  tela (`quadro_ref_s`) com `painel.escolher_ou_mascara` e `detector_tab.detectar`. Em todas
  as telas com marca, e nas telas conferidas do La Vie e da T8.2 sem marca (para a conta de
  técnica inventada). O modelo viu os ouros no treino, mas a técnica nunca foi supervisionada
  em tela real (ESTADO, fase 8; plano seção 10, item 4). Por isso ele é a medida válida de
  técnica.
- **Leitura secundária (dobras, para checar que a conta não muda)**:
  - End of Beginning, From This Place, Room 335: as leituras gravadas
    `data/saida/fase8/ger/ger/<slug>.json` (campo `tecnica` de cada nota, tela = id da tela do
    ouro, confirmado pelo intervalo `exibicoes[t0,t1]` contendo `quadro_ref_s`);
  - La Vie en Rose: **não há leitura gravada**. Lida no quadro com
    `artefatos/detector_tab_v3ft_d1` (pesos da dobra 1, cujo `config.json` lista o La Vie como
    vídeo fora do treino), pelo mesmo caminho do produto. Não é módulo novo: o `d1` carrega
    com `tab.detector_tab.carregar`.
  - Greensleeves, Gymnopédie e South American não têm marca de técnica: não entram na conta.

### Casamento (plano seção 5.2)

- Nota prevista `p` cai na região `r` se `min(cordas_r) ≤ corda_p ≤ max(cordas_r)` e o centro
  `x_centro_quadro_p` está dentro de `[x0_r − f·passo, x1_r + f·passo]`, com `passo` da tela
  (do painel, ou `passo` da tela do gerador gravado).
- Conferido antes de casar (3 casos, ver seção "Checagem de coordenadas"): o x do ouro, o x
  do gerador e o `x_quadro` da região estão no mesmo sistema (o quadro inteiro).
- **Folga `f`**: candidatos `{0; 0,25; 0,5; 0,75; 1,0}` passo. A folga escolhida é **a menor
  que maximiza as regiões com técnica certa nas 4 fontes com marca (End of Beginning, From This
  Place, Room 335 e La Vie), na leitura primária**. A escolha usa só os ouros, não a T8.2. Esta
  regra é aplicada igual na T8.2.
  - **Revisão (2026-10-16):** a regra acima contradiz a seção 5.2 do plano, que fixa a folga em
    0,5. A folga usada é **0,5**, fixa. Ver "Revisão" nos resultados.

### Classes (rótulo do dono → classe da régua)

| classe | rótulo do dono (`tecnica`, `obs`) | a rede conta se |
| --- | --- | --- |
| hammer-on `h` | `['h']` (inclui `arco de ligadura`) | token `h` no alcance |
| pull-off `p` | `['p']` | token `p` |
| mordente | `['h','p']`, ou `obs` com "mordente" | 3 ou mais notas com `h`, `p` ou `orn` no alcance |
| prolongamento | `[]` ou `['outra']` com `obs` com "prolong", "legato" ou "arco prolongamento" | token `lig` |
| slide | `['/']`, `['\\']`, ou `[]` com `obs` "ligadura slide" | `/` ou `\` (sentido conta à parte) |
| harmônico | `['harm']` | token `harm` |
| bend | `['bend']` sem "release" na `obs` | token `bend` |
| arpejo | `['arpejo']` | **a rede não tem saída**: sempre perdida |
| rasgueado | `['rasg']` | **a rede não tem saída**: sempre perdida |
| abafada `x` | `['x']` | à parte: rótulo `x` da nota prevista no alcance |
| fora da régua | `obs` de figura (colcheia, semicolcheia, semibreve), compasso, ritornelo, "bend release" | não entra; só contagem |

Decisões declaradas aqui, antes de medir: a `obs` "legato em cima do slide" (um caso) entra
em prolongamento, porque o dono disse que o arco sobre o slide quer dizer que a corda não é
tocada de novo. "Legato" e "arco legato" (Room 335) entram em prolongamento. Região cuja classe
não cai em nenhuma linha vai para `nao_classificada` e fica fora da conta.

Classe com menos de 10 marcas (harmônico, bend) é reportada e **não decide** aceite.

### Métricas (plano seção 5.2), por classe e por fonte

1. **marcas**: regiões do dono (contadas uma vez);
2. **achadas**: alguma técnica prevista no alcance (rótulo `x` para abafada);
3. **certas**: a classe prevista é a do dono (regra da tabela acima);
4. **perdidas** = marcas − certas, com causa:
   - **(c)** a nota não foi lida: existe nota do dono dentro da região (mesma corda, centro
     dentro do alcance) que a rede não leu (nenhuma nota prevista na mesma corda com
     `|dx| ≤ 0,5` passo). Esta regra vem antes das outras;
   - **(a)** nada marcado: a nota foi lida, mas nenhuma técnica prevista no alcance;
   - **(b)** classe errada: a rede marcou técnica no alcance, outra classe. Para arpejo e
     rasgueado, toda técnica prevista no alcance cai aqui;
5. **técnica inventada**: nota prevista com técnica (qualquer token, exceto o rótulo `x`)
   **fora de toda região da tela**, com a mesma folga. Só nas fontes com marca completa
   (plano seção 10, item 4): End of Beginning, La Vie, From This Place, Room 335 e as 35
   telas da T8.2. Para End of Beginning e Room 335, só nas **telas conferidas**. Greensleeves,
   Gymnopédie, South American e Retrato não contam.
6. **sem o Room 335**: todos os totais são repetidos sem essa fonte.
7. Abafada (`x`) e "fora da régua" ficam à parte, nas duas contas.

### Regra de parada

- Se mais de **10 %** das regiões com classe da rede tiverem **duas ou mais notas previstas
  com técnica** no alcance (qual nota leva a marca fica ambíguo), a regra de casamento não
  serve: **parar e relatar**.
- Se as regiões por fonte não somarem `(114, 5, 32, 177, 87)`, parar.
- Se o CA1 não bater, parar. **CA1 bateu** (ver abaixo).

### Recortes

Cada perda (a, b, c) tem um recorte do quadro do produto, com a região marcada em vermelho e
as linhas das cordas, em `data/saida/tab_frentes/f0_tecnica/recortes/`. O caminho de cada
recorte vai na tabela do relatório. Pelo menos 5 casos por classe com 10 marcas ou mais são
vistos (CA7).

### Duas execuções

O resultado precisa ser o mesmo nas duas execuções (CA6).

## Checagem de coordenadas (3 casos, antes de casar)

Ver a seção de resultados.

## Divergências do briefing (registradas)

1. O plano cita `data/saida/fase8/ger/tab`, que a seção 6.1 diz não existir. **Ele existe**
   (36 arquivos, `base_*` e `ger_*`), mas usei `ger/ger`, como o briefing manda.
2. `tab/detector_tab_v3ft_d1.py` não existe. Existe a pasta de pesos
   `artefatos/detector_tab_v3ft_d1`, que carrega com o `tab.detector_tab` atual. Não foi
   preciso módulo novo para o La Vie.
3. A frase do briefing sobre a folga (1,0) contradiz a seção 5.2 do plano (0,5). Usei 0,5, como
   o plano manda. A medida com 1,0 foi feita e está registrada abaixo.

## CA1 (reprodução), antes de tudo

- T8.2 com `final_s1_ger` (`ca1/t82_comparar.py`, cópia do original com só o caminho de saída
  trocado): ouro 1573, entregues 1566, casadas 1557, casa 1551/1557, inventadas 9, perdidas 16.
  **Bateu.**
- Dobras (`python -m tab.avaliar_video` nas 6 gravadas, somando `notas.total`): notas do
  ouro 1774, entregues 1799, casadas 1764, casa certa 1747, inventadas 35, perdidas 10.
  **Bateu.** (O campo do ouro no relatório é `notas_ouro`.)

## Revisão (2026-10-16): folga 0,5, como manda o plano

Motivo: a sessão principal apontou que a folga de 1,0 contradiz a seção 5.2 do plano, que fixa
a folga em 0,5 passo. A regra "escolher a folga nos ouros" acima foi escrita sem ver isso e levou
a 1,0. A folga usada agora é **0,5, fixa** (`FOLGA_PLANO` em `tab/tecnica_regua.py`; a escolha
nos dados saiu do código). A tabela de 1,0 continua abaixo, para comparação.

Ambiente: worktree com `main` mesclada em `e51d42d2` (merge sem reset). Relatório:
`data/saida/tab_frentes/f0_tecnica/regua_tecnica.json`. Versão com 1,0, feita antes da mescla:
`regua_tecnica_folga1_0_premerge.json`, recortes em `recortes_folga1_0_premerge/`.

### CA1 depois da mescla (refeito antes de medir)

Script: `ca1/ca1_rodar.sh` (pasta da frente).

- T8.2 com `final_s1_ger`: ouro 1573, entregues 1566, casadas 1557, casa 1551/1557, inventadas 9,
  perdidas 16. **Bateu.**
- Dobras (6 leituras gravadas, `tab.avaliar_video`, `notas.total`, `ca1_dobras_v2/`): ouro 1771,
  entregues 1799, casadas 1761, casa certa 1744, inventadas 38, perdidas 10. **Bateu.**

### Contagens (CA, sem mudança)

- Regiões por fonte: EOB 114, FTP 32, R335 177, LVR 5, T82 87. **Soma 415.** (As 5 fontes do
  briefing batem, com o nome do La Vie como `LVR`.)
- Telas lidas com o modelo do produto: 68, todas `ok`.
- Modelo do produto: `artefatos/detector_tab_final_s1_ger`. LVR também com `d1`.

### Parada da regra de casamento (folga 0,5): não dispara

- Regiões com duas ou mais notas com técnica no alcance: **18 de 229 = 7,86 %** (limite 10 %).
  Por classe: prolongamento 8, slide 8, h 1, harmônico 1.
- Esperado no pré-registro: 7,9 %. Bate.

### Tabela primária, folga 0,5 (modelo do produto, 229 marcas, todas as telas)

| classe | marcas | achadas | certas | perdidas | causa a / b / c | decide (≥10) |
| --- | --- | --- | --- | --- | --- | --- |
| hammer-on h | 29 | 5 | 1 | 28 | 24 / 4 / 0 | sim |
| pull-off p | 19 | 1 | 0 | 19 | 18 / 1 / 0 | sim |
| mordente | 11 | 1 | 0 | 11 | 10 / 1 / 0 | sim |
| prolongamento | 80 | 18 | 3 | 77 | 62 / 15 / 0 | sim |
| slide | 46 | 21 | 20 | 26 | 25 / 1 / 0 | sim |
| harmônico | 4 | 4 | 4 | 0 | — | não |
| bend | 4 | 0 | 0 | 4 | 4 / 0 / 0 | não |
| arpejo | 21 | 0 | 0 | 21 | 21 / 0 / 0 | sim |
| rasgueado | 15 | 0 | 0 | 15 | 15 / 0 / 0 | sim |
| **total** | **229** | **50** | **28** | **201** | **179 / 22 / 0** | |

- Slide: 42 com sentido medido, 15 com o sentido certo (a classe conta qualquer sentido).
- Abafada `x`, à parte: 124 marcas, 1 achada (rótulo `x`), 123 "nada".
- Perdas por causa: (a) nada marcado = 179 de 201 (89 %); (b) classe errada = 22 (11 %);
  (c) nota não lida = 0. **Mas ver "Achado: o casamento por corda" abaixo: o zero de (c) não
  enxerga nota fora das cordas da região.**

### Lado a lado: folga 0,5 e folga 1,0 (mesma régua, leitura primária, todas as telas)

| classe | marcas | achadas 0,5 / 1,0 | certas 0,5 / 1,0 | perdidas 0,5 / 1,0 | a / b / c 0,5 | a / b / c 1,0 |
| --- | --- | --- | --- | --- | --- | --- |
| h | 29 | 5 / 5 | 1 / 1 | 28 / 28 | 24 / 4 / 0 | 24 / 4 / 0 |
| p | 19 | 1 / 1 | 0 / 0 | 19 / 19 | 18 / 1 / 0 | 18 / 1 / 0 |
| mordente | 11 | 1 / 1 | 0 / 0 | 11 / 11 | 10 / 1 / 0 | 10 / 1 / 0 |
| prolongamento | 80 | 18 / 26 | 3 / 3 | 77 / 77 | 62 / 15 / 0 | 54 / 23 / 0 |
| slide | 46 | 21 / 36 | 20 / 34 | 26 / 12 | 25 / 1 / 0 | 10 / 2 / 0 |
| harmônico | 4 | 4 / 4 | 4 / 4 | 0 / 0 | — | — |
| bend | 4 | 0 / 0 | 0 / 0 | 4 / 4 | 4 / 0 / 0 | 4 / 0 / 0 |
| arpejo | 21 | 0 / 0 | 0 / 0 | 21 / 21 | 21 / 0 / 0 | 21 / 0 / 0 |
| rasgueado | 15 | 0 / 0 | 0 / 0 | 15 / 15 | 15 / 0 / 0 | 15 / 0 / 0 |
| **total** | **229** | **50 / 73** | **28 / 42** | **201 / 187** | **179 / 22 / 0** | **156 / 31 / 0** |

- A folga 1,0 foi medida antes da mescla. Depois da mescla, a sensibilidade do relatório novo
  reproduz 1,0 com 42 certas, 23 ambiguidades e 22 invenções: a mescla não mudou esses totais.
- Folga nos 4 ouros (164 marcas, só para informação, a folga não é escolhida por isso):
  0 → 4 certas; 0,25 → 8; 0,5 → 18; 0,75 → 27; 1,0 → 29. Nas 229 marcas: 9, 15, 28, 40, 42.
- Ambiguidade: 0,5 → 7,86 % (18); 1,0 → 10,04 % (23). Só 1,0 passa do limite.

### Conferência da "conclusão que deve se manter" (com 0,5)

- **Legato** (h, p, mordente, prolongamento, 139 marcas): a rede **acha** em **25 de 139 (18 %)**,
  antes 33 (23,7 %). **Mudou.** Classe certa: 4 de 139 (2,9 %). **Mantém.**
- **Perdas**: (a) 179, (b) 22, (c) 0. Antes: 156, 31, 0. **Mudou**: a proporção de "nada marcado"
  sobe de 83 % para 89 %, e a de classe errada cai de 17 % para 11 %.
- **Slide**: certas **20 de 46**, antes 34 de 46. **Mudou.** Sentido certo: 15 de 42 com sentido
  medido (antes 26 de 42). Slide deixa de ser o ponto forte que era em 1,0. Ainda é a classe com
  mais acerto na tabela.
- **Harmônico 4 de 4**: mantém (classe com menos de 10 marcas, não decide).
- **Arpejo e rasgueado sem saída**: mantém (21 e 15 perdidas, todas (a)).
- **Prolongamento** confunde-se com h (8) e slide (5), e 3 certas: mantém a leitura.

### Sem o Room 335 (120 marcas, folga 0,5)

h 19 / achadas 5 / certas 1; p 17 / 1 / 0; mordente 7 / 1 / 0; prolongamento 24 / 11 / 3;
slide 16 / 5 / 4; harmônico 4 / 4 / 4; bend 4 / 0 / 0; arpejo 21 / 0 / 0; rasgueado 8 / 0 / 0.
Total: 120 marcas, 27 achadas, 12 certas, 108 perdidas (a 93, b 15, c 0). (1,0: 33 achadas,
16 certas, 104 perdidas.)

### Só telas conferidas (207 marcas, folga 0,5)

Total: 207 marcas, 42 achadas, 22 certas, 185 perdidas (a 165, b 20, c 0). (1,0: 61, 33, 174.)
Prolongamento cai para 67 marcas, 16 achadas, 3 certas.

### Leitura secundária (dobras gravadas e La Vie com `d1`, 164 marcas, folga 0,5)

| classe | marcas | achadas | certas | causa a / b / c |
| --- | --- | --- | --- | --- |
| h | 23 | 2 | 0 | 20 / 2 / 1 |
| p | 10 | 0 | 0 | 9 / 0 / 1 |
| mordente | 6 | 0 | 0 | 6 / 0 / 0 |
| prolongamento | 63 | 11 | 0 | 52 / 11 / 0 |
| slide | 35 | 18 | 15 | 17 / 3 / 0 (sentido certo 12 de 35) |
| arpejo | 15 | 0 | 0 | 15 / 0 / 0 |
| rasgueado | 12 | 3 | 0 | 9 / 3 / 0 |
| abafada x | 115 | 115 | 115 | — (ver ressalva abaixo) |

Total de técnica: 164 marcas, 34 achadas, 15 certas, 149 perdidas (a 128, b 19, c 2). (1,0: 53
achadas, 28 certas, 109/25/2.) A conclusão se mantém: h, p, prolongamento e mordente não são
achados. Slide é o único com acerto razoável, mas caiu de 28 para 15 certas.

### Invenção (técnica prevista fora de qualquer marca), folga 0,5

38 notas no total: EOB 3, FTP 5, R335 11, LVR 5, T82 14. Sem o Room 335: 27. (1,0: 22 notas, por
fonte EOB 2, FTP 5, R335 1, LVR 4, T82 10.) Em EOB e R335 só contam as telas conferidas.

### Matriz de confusão (primária, folga 0,5)

| dono \ rede | nada | h | p | slide | prolong. | harm | bend | outra | acerto |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| h (29) | 24 | 1 | | | | | | 4 | 1 |
| p (19) | 18 | | | | | | | 1 | 0 |
| mordente (11) | 10 | | | 1 | | | | | 0 |
| prolongamento (80) | 62 | 8 | | 5 | 3 | | 2 | | 3 |
| slide (46) | 25 | | | 20 | | | 1 | | 20 |
| harm (4) | | | | | | 4 | | | 4 |
| bend (4) | 4 | | | | | | | | 0 |
| arpejo (21) | 21 | | | | | | | | 0 |
| rasgueado (15) | 15 | | | | | | | | 0 |
| x (124) | 123 | | | | | | | | 1 (`x`) |

### Checagem de coordenadas (3 casos, antes de casar)

Sem mudança. As três notas da rede ficam a 0,3 a 6,9 px das notas do dono, na mesma corda (EOB
t1, t2 e t4). O x da nota e o `x_quadro` da região estão no mesmo sistema.

### Determinismo (CA6)

Duas execuções com 0,5 (mesmo código, mesma montagem): `regua_tecnica.json` com o mesmo
SHA-256, `cc009a9ac22d69045e92b74a4aa37c073dd71d0b3d3b5b3a5070fa9b010f4466`.

### Achado: o casamento por corda (diagnóstico, a regra não mudou)

Dos 179 casos (a), **114 têm alcance vazio**: nenhuma nota prevista cai na região, nem em outra
corda que não a da região. Script: `folhas/diagnostico_corda.py`; saída: `folhas/diagnostico_corda.json`.

- 26 dos 114 têm nota prevista na faixa de x da região (em alguma corda);
- 7 têm técnica prevista numa corda vizinha (±1 corda da região);
- **22 têm nota do ouro dentro da faixa de x, numa corda fora de `cordas` da região.** Ex.: EOB
  tela 1, região 16, marcada na corda [1,1], com notas do dono "0" e "1" na corda 2 (x 1229,0 e
  1279,5). O arco desenhado entre as duas notas fica entre a corda 1 e a 2, e o dono o marcou
  na corda de cima.

Consequências. (1) Um arco marcado numa corda acima da nota vira "nada marcado", mesmo que a rede
tivesse marcado a nota. (2) A causa (c) nunca dispara para nota fora das cordas da região, porque
`nota_nao_lida` usa o mesmo `casa`. O zero de (c) não prova que a rede lê todas as notas da
região. Não mudei a regra de casamento: os critérios estão congelados (plano, seção 10, item 6).
Decisão para a sessão principal: se a regra por corda deve aceitar uma corda vizinha para arcos,
isso muda a régua e precisa ser pré-registrado antes de medir de novo.

### Casos olhados (CA7)

Folhas: `folhas/folha_<classe>.png` (uma por classe, com as classes harmônico e bend), índice em
`folhas/casos.json` (61 casos). Os recortes estão em `folhas/casos/`. Gerado por
`folhas/gerar_casos.py`. Olhei cada folha inteira. Cada caso abaixo tem legenda com fonte, tela,
região, técnica do dono, classe prevista e as notas previstas no alcance.

Limite do critério "5 por classe com 10 marcas ou mais": h, p, mordente, prolongamento, slide,
arpejo e rasgueado têm 5 casos (a) ou mais. Perda (b) só tem 4 em h, 1 em p, 1 em mordente, 5 em
prolongamento e 1 em slide: não há 5. Certas: 1 de h, 3 de prolongamento, 3 de slide. Harmônico
(3 de 4 certas) e bend (4 de 4 perdas, a) entram na folha.

- **h (a)**: EOB t1 r11 (região [1,2]): arco entre notas 0 e 1 da corda 2; a rede leu as notas,
  nenhuma técnica. Outras quatro (EOB t1 r16, t2 r2, t2 r7, t3 r5): região [1,1], arco entre notas
  da corda 2, alcance vazio. Caso do corda acima.
- **h (b)**: FTP t1 r1, FTP t3 r3, FTP t4 r3, LVR t8 r0: a rede marcou `orn` ou `enfeite` nas notas
  do arco (classe errada). **h (certa)**: T82 t17 r0, rede `h`.
- **p (a)**: EOB t2 r16, EOB t5 r0, EOB t5 r7: arco sobre notas lidas (corda 2 ou 3), nenhuma
  técnica. EOB t3 r4 e EOB t4 r13: região na corda de cima, alcance vazio. **p (b)**: FTP t5 r7,
  rede `enfeite` na nota.
- **mordente (a)**: R335 t4 r10, R335 t4 r11, R335 t6 r7: arco sobre três notas lidas (corda 3
  ou 4), nenhuma técnica. FTP t1 r3 e FTP t4 r4: região pequena sob um símbolo em zigue-zague,
  alcance vazio. **mordente (b)**: T82 t24 r1, dono `h+p`, rede `\` (slide) na nota.
- **prolongamento (b)**: FTP t3 r2, t3 r5, t4 r2, t4 r6, t5 r1: o dono marcou arco de
  prolongamento sem técnica, a rede marcou `h` nas notas do arco. Há confusão real entre h e
  arco de prolongamento. **prolongamento (a)**: R335 t1 r7, r8, r9, r15: arco entre notas na faixa
  de x, rede sem técnica; FTP t4 r5: símbolo pequeno, rede sem técnica.
  **prolongamento (certa)**: FTP t5 r3, T82 t13 r1 e r2, rede `lig`.
- **slide (a)**: EOB t3 r18, FTP t3 r6, R335 t1 r1, r3, r4: a barra de slide entre notas, rede sem
  técnica; em R335 as notas estão fora da região (alcance vazio). **slide (b)**: LVR t3 r1, rede
  `bend`. **slide (certa)**: EOB t4 r5 (`\`), R335 t1 r2 (`/`), R335 t3 r0 (`\`).
- **arpejo (a)**: EOB t5 r17, EOB t6 r4, FTP t1 r2, t1 r4, t2 r0: símbolo de onda na coluna, rede
  sem técnica. Esperado: a rede não tem saída para arpejo.
- **rasgueado (a)**: EOB t5 r18, EOB t6 r5, t6 r10, t7 r0, t7 r5: seta para baixo na coluna, rede
  sem técnica. Esperado: sem saída.
- **harmônico (certa)**: T82 t16 r0 (`<12>` em quatro cordas), T82 t20 r1 e r2 (`<7>`). A quarta
  marca de harmônico não entrou na folha (critério: três certas por classe).
- **bend (a)**: T82 t2 r0, r2, r4, r6: símbolo `b` entre 6 e 7 (ou entre notas), rede sem bend.

Ressalvas: os recortes são de tela (alguns canais em fundo escuro, T82 t2; amarelo em EOB t5 r7).
Estes casos descrevem a imagem olhada; não medem a rede além do que está no recorte.

### Achados de técnica que valem para as frentes seguintes

- Parte das perdas (a) vem do casamento por corda, não da leitura: ver "Achado: o casamento por
  corda". A medida não separa isso da falta de marca da rede.
- A rede marca `h` em notas de arco que o dono marcou como prolongamento (sem técnica na marca).
  Isso aparece como classe errada (b), não como nota não lida.

### Não fiz nesta revisão

- F0.2 (rodada 0102) e F0.3 (rodada 0103): ficam para os próximos commits.

## Primeira medida (folga 1,0, descartada)

Relatório da primeira medida: `regua_tecnica_folga1_0_premerge.json`. O texto abaixo é o de antes
da revisão e não vale como resultado final. A folga de 1,0 foi medida, mas não é a folga do plano.

Relatório completo: `data/saida/tab_frentes/f0_tecnica/regua_tecnica.json` (linha a linha, com o
caminho de cada recorte). Código: `tab/tecnica_regua.py`, testes em `tests/test_tecnica_regua.py`.

### Parada da regra de casamento (nesta rodada)

A regra de parada do briefing dispara: com a folga escolhida pela regra pré-registrada (**1,0**),
**23 de 229 regiões medidas (10,04 %)** têm duas ou mais notas com técnica no alcance. O limite
é 10 %. Pela regra, **parei aqui**: não medi a F0.2 (rodada 0102), não gerei `topo.json` nem a
folha de cortados, e não commitei. A decisão fica com a sessão principal.

Sobre a própria parada, para julgar:

- A medida é uma proxy minha ("duas ou mais notas com técnica ou abafada no alcance"). Com 22,9
  regiões seria o limite; estão 23. A margem é de **uma** região.
- A fração depende da folga: 2,2 % (0), 4,4 % (0,25), 7,9 % (0,5), 10,0 % (0,75), 10,0 % (1,0).
  Com a folga do plano (0,5), a parada **não** dispara.
- A folga escolhida está **na borda da grade** (1,0). A regra "menor folga que maximiza as certas
  nos ouros" não achou um máximo interior: as certas nos ouros sobem sempre (4, 8, 18, 27, 29).
  Não estendi a grade depois de ver isso (critério congelado). Um máximo além de 1,0 é possível e
  não foi medido.

### CA1 (reprodução): bateu

- T8.2, `final_s1_ger`: ouro 1573, entregues 1566, casadas 1557, casa 1551/1557, inventadas 9,
  perdidas 16.
- Dobras (6 vídeos, `tab.avaliar_video`, `notas.total`): ouro 1774, entregues 1799, casadas 1764,
  casa certa 1747, inventadas 35, perdidas 10.

### Contagens e cobertura

- Regiões por fonte: EOB 114, La Vie 5, From This Place 32, Room 335 177, T8.2 87. **Soma 415.**
- Telas lidas com o modelo do produto: 68 (EOB 7, La Vie 8, FTP 5, R335 13, T8.2 35). Todas
  com estado `ok` (nenhuma tela sem quadro ou sem painel).
- No Room 335, 34 regiões (de 177) estão em telas não conferidas (19 e 22).

### Folga (escolhida só nos 4 ouros, 164 marcas)

| folga (passo) | 0 | 0,25 | 0,5 | 0,75 | 1,0 |
| --- | --- | --- | --- | --- | --- |
| certas nos ouros | 4 | 8 | 18 | 27 | **29** |

Escolhida: 1,0 (regra pré-registrada; na borda da grade, ver acima).

### Tabela primária (modelo do produto, folga 1,0), por classe

Medidas = 229 marcas (sem `x` e sem "fora da régua").

| classe | marcas | achadas | certas | perdidas | causa a / b / c | decide (≥10) |
| --- | --- | --- | --- | --- | --- | --- |
| hammer-on h | 29 | 5 | 1 | 28 | 24 / 4 / 0 | sim |
| pull-off p | 19 | 1 | 0 | 19 | 18 / 1 / 0 | sim |
| mordente | 11 | 1 | 0 | 11 | 10 / 1 / 0 | sim |
| prolongamento | 80 | 26 | 3 | 77 | 54 / 23 / 0 | sim |
| slide | 46 | 36 | 34 | 12 | 10 / 2 / 0 | sim |
| harmônico | 4 | 4 | 4 | 0 | — | não |
| bend | 4 | 0 | 0 | 4 | 4 / 0 / 0 | não |
| arpejo | 21 | 0 | 0 | 21 | 21 / 0 / 0 | sim |
| rasgueado | 15 | 0 | 0 | 15 | 15 / 0 / 0 | sim |
| **total** | **229** | **73** | **42** | **187** | **156 / 31 / 0** | |

- Slide: 42 com sentido medido, 26 com o sentido certo (a classe conta qualquer sentido).
- Fração das regiões de legato (h, p, mordente, prolongamento, 139 marcas) que a rede **acha**:
  33 de 139 (23,7 %). Com a classe certa: 4 de 139 (2,9 %).
- **Perdas por causa**: (a) nada marcado = 156 de 187 (83 %); (b) classe errada = 31 de 187
  (17 %); (c) nota não lida = 0 de 187.

### Sem o Room 335 (120 marcas medidas)

h 19 / achadas 5 / certas 1; p 17 / 1 / 0; mordente 7 / 1 / 0; prolongamento 24 / 12 / 3;
slide 16 / 10 / 8; harmônico 4 / 4 / 4; bend 4 / 0 / 0; arpejo 21 / 0 / 0; rasgueado 8 / 0 / 0.
Total: 120 marcas, 33 achadas, 16 certas, 104 perdidas (a 87, b 17, c 0).

### Só telas conferidas (207 marcas medidas)

Total: 207 marcas, 61 achadas, 33 certas, 174 perdidas (a 146, b 28, c 0). Prolongamento cai
para 67 marcas (44 a, 20 b).

### Leitura secundária (dobras gravadas e La Vie com `d1`, 164 marcas, folga 1,0)

| classe | marcas | achadas | certas | causa a / b / c |
| --- | --- | --- | --- | --- |
| h | 23 | 2 | 0 | 20 / 2 / 1 |
| p | 10 | 0 | 0 | 9 / 0 / 1 |
| mordente | 6 | 0 | 0 | 6 / 0 / 0 |
| prolongamento | 63 | 15 | 0 | 48 / 15 / 0 |
| slide | 35 | 33 | 28 | 2 / 5 / 0 (sentido certo 22 de 35) |
| arpejo | 15 | 0 | 0 | 15 / 0 / 0 |
| rasgueado | 12 | 3 | 0 | 9 / 3 / 0 |
| abafada x | 115 | 115 | 115 | — (só EOB e R335; ver abaixo) |

A leitura secundária dá a mesma conclusão: slide é o único ponto que a rede acerta; h, p,
prolongamento e mordente não são achados. Os 2 casos de causa (c) aqui são notas que a leitura
gravada não leu (h 1, p 1). A leitura primária não tem nenhum (c).

### Abafada (x), à parte

- Primária: 1 de 124 regiões `x` achada. No quadro de teste (EOB, tela 1), o modelo do produto
  dá 26 notas com rótulos 0 a 3, nenhum `x`. A cabeça de classe tem 26 saídas nos três modelos
  (inclusive o do produto), então a diferença não é de forma de saída. **Não resolvi** por que o
  caminho `tab.video` (que gravou as nao_notas) produz `x` e o `detectar` do produto não.
- Secundária: 115 de 115 regiões `x` (EOB 76, R335 39) batem com nao_notas `x` gravadas, nas
  mesmas cordas e posições (ex.: tela 1, cordas 5–6, x≈535, 749, 1017). **Ressalva**: a
  coincidência de contagem e de posição não prova que a marca do dono foi feita às cegas; as
  regiões `x` podem ter sido pré-preenchidas pela ferramenta a partir do próprio modelo. Não
  verifiquei isso.

### Matriz de confusão (primária, folga 1,0)

| dono \ rede | nada | h | p | mordente | prolong. | slide | harm | bend | outra rede | acerto |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| h (29) | 24 | 1 | | | | | | | 4 | 1 |
| p (19) | 18 | | | | | | | | 1 | 0 |
| mordente (11) | 10 | | | | | 1 | | | | 0 |
| prolongamento (80) | 54 | 8 | | | 3 | 9 | | 6 | | 3 |
| slide (46) | 10 | | | | | 34 | | 2 | | 34 |
| harm (4) | | | | | | | 4 | | | 4 |
| bend (4) | 4 | | | | | | | | | 0 |
| arpejo (21) | 21 | | | | | | | | | 0 |
| rasgueado (15) | 15 | | | | | | | | | 0 |
| x (124) | 123 | | | | | | | | | 1 (`x`) |

Prolongamento confunde-se com h (8 vezes) e com slide (9); mordente sai como nada (10 de 11).

### Ambiguidade

Regiões com duas ou mais notas com técnica no alcance (folga 1,0): 23 de 229, por classe:
h 1, prolongamento 8, slide 13, harmônico 1.

### Invenção (técnica prevista fora de qualquer marca), folga 1,0

22 notas no total, por fonte: EOB 2, FTP 5, R335 1, La Vie 4, T8.2 10. Sem o Room 335: 21.
Tipos: `enfeite`, `vib`, `h`, `lig`, `orn`, `bend`. Recortes em `recortes/invencoes/`.

Em EOB e R335 só contam as telas conferidas. Greensleeves, Gymnopédie, South American e Retrato
não entram.

### Checagem de coordenadas (3 casos, antes de casar)

| caso | marca (cordas, x_quadro) | nota do dono (corda, x) | nota da rede (corda, x) |
| --- | --- | --- | --- |
| EOB t1, h | 1–2, [912,3; 966,0] | 2: 914,0 e 965,5 | 2: 916,5 e 963,4 |
| EOB t2, p | 2–3, [1473,5; 1528,9] | 3: 1476,2 e 1524,4 | 3: 1478,8 e 1525,3 |
| EOB t4, h | 1–2, [66,1; 124,2] | 2: 68,8 e 122,4 | 2: 69,0 e 115,5 |

As coordenadas batem (diferença de 0,3 a 6,9 px, até 0,26 passo). Confirmado: o x da nota e o
`x_quadro` da região estão no mesmo sistema.

### Determinismo

Execuções 1 e 2 (mesmo código): `regua_tecnica.json` com o mesmo SHA-256. Depois corrigi o nome
dos arquivos de invenção (token `/` virava subpasta); a terceira execução tem os mesmos números
(resumo e sensibilidade idênticos) e outro SHA, só pelo caminho desses recortes. Não rodei uma
quarta vez para fechar o SHA da versão final.

### Recortes e casos olhados

- 187 recortes de perda (`recortes/perdidas/`, causa no nome), 22 de invenção (`recortes/invencoes/`).
- Olhei 1 recorte: `recortes/perdidas/EOB_t1_r11_h_a.png` (hammer-on entre as notas 0 e 1 da corda
  2, na tela 1 do End of Beginning). O arco aparece, a rede leu as duas notas e não marcou técnica
  (causa a). O critério do CA7 pedia 5 por classe, e não olhei os outros.

### Gate

- `ruff check .` e `ruff format --check .`: passaram (com as duas mudanças de formatação e de
  lint feitas nos meus arquivos).
- `pytest tests/ -q -p no:cacheprovider`, com a receita do container do briefing (a saída da
  principal montada **para leitura** e a pasta da frente gravável): **1251 passaram, 2 pulados,
  4 desselecionados, 2 xfail, 0 falhas**. A execução anterior tinha falhado em
  `tests/test_portao.py::test_gold_do_portao_mantem_formato_e_rotulos` só por ambiente (faltava
  `data/saida/portao_casos/121_p.png` sem a montagem); com a montagem, passa. Não é efeito desta
  mudança.
- Meus testes (`tests/test_tecnica_regua.py`): 34 passaram.

### Gate (revisão, folga 0,5)

- `ruff check --no-cache .`: All checks passed!
- `ruff format --no-cache --check .`: 185 files already formatted.
- `pytest tests/ -q -p no:cacheprovider`: 1257 passed, 2 skipped, 5 deselected, 2 xfailed.
  (A rodada anterior tinha 1251 passed, 2 skipped, 4 deselected, 2 xfailed, antes da mescla.)

### Não fiz nesta revisão

- F0.2 (rodada 0102) e F0.3 (rodada 0103): próximos commits. Ver os respectivos documentos.


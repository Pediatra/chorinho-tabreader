# 3027 — Partitura: documento final por vídeo, com a nota que a tab tem e a pauta não leu

**Data:** 2026-10-18 · **Trilha:** partitura (P4) · **Branch:** `part/p4-produto` ·
**Código:** `tab/partitura_completar_pauta.py` (novo), `tab/partitura_video.py`
(`parear_produto`, `_completar_pauta_do_recorte`, `pasta_video`), `tab/partitura_completar.py`
(`--saida`, `harmonico_tab` pela `tecnica`).
**Saída:** `data/saida/part_frentes/fp_produto/` (fora do git).

## Pergunta

Pôr no `<stem>.partitura.json` a nota que a tab tem e a pauta não leu, com a altura e o instante
da tab e `figura` `null` (decisão da rodada 3172), **sem mudar nada do que já existia**?

## Regras a priori (rodada 3172 e briefing)

- Nota completada: altura e coluna da tab, `figura` `null`, `pontuada` falso, sempre.
- Acorde (coluna com evento pareado por `confere_x`): símbolo novo no fim de `simbolos` desse evento.
- Isolado (coluna sem par): evento novo, `compasso` de `_compasso_de_x`, `t` `null`, `x_quadro`
  da coluna, `par` com `metodo` `tab`. Entra em ordem de x; um evento que já estava fora de ordem
  fica onde está.
- Harmônico (`tecnica` `harm`): não entra se a pauta tem a nota uma oitava acima no mesmo x; senão
  entra com `harmonico` true.
- Nota `tecnica` `lig`: não entra, e conta.
- Tela 10 da Gymnopédie: entra pela regra geral; na contagem fica à parte.
- Aviso por pauta: `pauta_pequena` (entrelinha < 16,0) e `leitura_ok` (falso se a pauta tem `erro`).

## Aceite (congelado, do briefing)

1. Os 3 documentos novos, comparados com os atuais: todos os eventos e símbolos que já existiam
   ficam idênticos, campo a campo, e nenhum evento perde o par. Só entram símbolos com origem
   `tab_completada`, eventos novos com `metodo` `tab` e os campos novos do item 3.
2. Completadas fora da tela 10 da Gymnopédie: 37 na E1 (30 de acorde, 7 isoladas). O número novo
   pode ser menor só pelos harmônicos com oitava e pelas notas `lig`; cada diferença, nota a nota.
3. Toda nota completada tem figura `null`.
4. `e1.json` regerado igual ao atual, salvo o campo de harmônico corrigido (com explicação).
5. CA1 (`docker.io/library/chorinho:dev`) dá as mesmas linhas de antes; a linha "E." não conta.
6. Gate verde na worktree.

**Nota sobre a ordem.** O briefing pede escrever este aceite antes de medir. Eu rodei o parear e o
comparador antes de escrever esta rodada. O texto acima é o do briefing, sem mudança de limiar. Na
primeira rodada do comparador, a única diferença era o campo `produto`: a gravação atual tinha o
caminho relativo (`data/saida/fase8/rede/...`) e a minha, o do container (`/app/data/...`). Corrigi
rodando o parear de novo com o caminho relativo, igual ao da gravação atual. Não mexi em critério.

## Resultado

Denominadores: 3 documentos, 19 pautas, 442 eventos que já existiam, 66 notas completadas.

| critério | resultado |
| --- | --- |
| 1. eventos e símbolos que já existiam, campo a campo (3 documentos, 442 eventos) | **0 diferenças** (`comparar_partitura.py`) |
| 1. eventos novos (`metodo` tab) com `t` null, `confere_x` true, só `tab_completada` | **0 falhas** |
| 2. completadas fora da tela 10 (E1: 37) | **37** (30 de acorde, 7 isoladas): igual à E1 |
| 2. não completadas por harmônico | **0**: nenhuma nota dos produtos tem `tecnica` `harm` |
| 2. não completadas por `lig` | **0**: nenhuma nota dos produtos tem `tecnica` `lig` |
| 3. completadas com figura não `null` | **0 de 66** |
| 4. `e1.json` regerado (passo 1 e depois do passo 2) | passo 1: **igual byte a byte** (`cmp`); passo 2: **0 campos** diferentes |
| 5. CA1, linhas A, B, C, D e F | **iguais** à referência (`ca1.txt`); a linha E não saiu na releitura, e o aceite não a conta |
| 6. gate | ver a seção "Gate" abaixo |

O resultado de E1 vs. documento novo bate exatamente: 37 + 29 = 66 notas completadas nos 3
produtos, nas duas contas.

### Tabela por vídeo

| vídeo | pautas | pautas pequenas (< 16 px) | completadas de acorde | isoladas | não completadas por harmônico | por `lig` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| greensleeves | 4 | 0 | 0 | 1 | 0 | 0 |
| south american | 3 | 3 | 3 | 1 | 0 | 0 |
| gymnopédie | 12 | 0 | 27 | 5 | 0 | 0 |
| **tela 10 da gymnopédie (à parte)** | — | — | 17 | 12 | — | — |

- Total: 66 notas completadas (37 contadas + 29 à parte).
- Gymnopédie: as colunas de acorde e de isoladas somam 44 e 17 no documento, que incluem a tela 10.
  Separadas, ficam 27 + 5 contadas e 17 + 12 à parte.
- As 3 pautas pequenas são as do south american (entrelinha < 16 px). O aviso não muda a leitura.

### Candidatos de harmônico que entraram completados

A regra de oitava (rodada 3013) é só diagnóstico. Como nenhuma nota dos produtos tem a marca de
harmônico, os 7 candidatos abaixo entraram completados, com `harmonico` ausente:

- south american, tela 3 (recorte T03), compasso 12: midi 52 e 59 (acorde);
- gymnopédie, tela 6 (T06), compasso 4: midi 52 (acorde);
- gymnopédie, tela 11 (T11), compasso 3: midi 61 (acorde);
- gymnopédie, tela 12 (T12), compasso 1: midi 64 (acorde);
- R07 (R01–R12), compasso 10: midi 52 e 59 (acorde).

Isso é o que a E1 já tinha dito (`harmonico_nao_detectado_candidatos_oitava` = 7). O documento não
tem como separá-los sem a marca da tab. A decisão de quais ficam é do dono.

## Cinco notas olhadas no recorte

Recortes em `data/saida/part_frentes/fp_produto/casos/` (3× ampliados, linha vermelha no x da nota).

1. **`greensleeves_T03_c8_m73_isolado.png`**: C#5, isolada, compasso 8. **Errada.** No recorte há
   um símbolo de pausa no mesmo x. É o caso suspeito da E1 (3170, caso 5), e continua no
   documento: a completação não checa pausa.
2. **`south_T01_c1_m60_acorde.png`**: C4, acorde, compasso 1. **Inconclusiva**: a nota fica abaixo
   da pauta, e na escala não dá para ler a altura com segurança.
3. **`south_T01_c1_m76_isolado.png`**: E5, isolada, compasso 1. **Inconclusiva**: há colcheia
   perto do x, e a altura não se lê na escala.
4. **`gym_T04_c4_m52_acorde.png`**: E3, acorde, voz 2, compasso 4. **Inconclusiva**: a voz 2 fica
   no grupo de graves, e a altura não se lê na escala.
5. **`gym_T01_c1_m64_isolado.png`**: E4, isolada, compasso 1. **Errada.** O x cai sobre a clave de
   sol, no início do sistema, antes da primeira nota lida da pauta. A checagem de cabeçalho
   (`cabecalho_p4.py`) achou também a gymnopédie tela 7 (T07, x = 247,6, E3, antes da primeira
   nota lida em x = 324). Essa última não foi olhada no recorte.

Resultado dos 5: 2 errados (um de pausa, um de cabeçalho), 2 inconclusivos e 1 que não se
decide com a escala. Nenhum certo confirmado. Com esta amostra, a completação não tem precisão
medida.

## O que deu errado e o "não repetir"

- **Regra de harmônico sem dado.** O briefing diz `tecnica` `harm`. Os 3 produtos não têm nenhuma
  nota com essa marca (`diag_tecnica.py`), e nem `lig`. A regra existe, é testada com dados à mão,
  e não atua no dado real. O harmônico segue sem medição na tab.
- **Cabeçalho da pauta.** Uma isolada pode cair na clave, antes de qualquer nota lida. A completação
  não tem limite de x à esquerda da primeira nota lida. Não corrigi: é decisão do dono (ver
  "Pendências").
- **Parâmetro padrão ligado na importação.** Pôr `PASTA_VIDEO` como padrão do parâmetro
  `pasta_video` quebrou dois testes que trocam `PASTA_VIDEO` por uma pasta temporária: o padrão era
  lido uma vez, na definição. Corrigido: `pasta_video=None` e a leitura de `PASTA_VIDEO` é feita na
  chamada. **Não repetir**: padrão de parâmetro que aponta para constante de módulo, em função com
  teste que troca a constante.
- **Caminho do produto no campo `produto`.** Rodar o parear com caminho absoluto muda a string do
  campo `produto`, e o comparador acusa uma diferença. **Não repetir**: rodar o parear com o mesmo
  argumento que gerou o atual.
- **Comparar por índice.** Os eventos novos entram no meio da lista. Por isso o comparador compara
  os eventos que já existiam, na ordem, sem os eventos `metodo` `tab`.
- **`_nome` copiado.** O briefing manda importar `_nome` de `partitura_completar_itens`, mas esse
  módulo importa `partitura_video`, e o import daria ciclo. Copiei a função (4 linhas) para o módulo
  novo, e não editei o módulo da E1.
- **South american T01 já estava fora de ordem em x** no documento atual. Mantive a ordem existente
  e inseri os eventos novos pelo x, sem reordenar.

## Pendências para o dono

1. Os 7 candidatos de harmônico entraram completados: ficam, ou saem? A tab não tem a marca.
2. Cabeçalho: limitar a completação a partir da primeira nota lida da pauta? Pelo menos 2 casos
   (gymnopédie T01 e T07).
3. Pausa: checar pausa no mesmo x antes de completar (caso greensleeves T03 c8).
4. Figura continua `null` em todas as 66: a conferência de figura não foi feita (rodada 3172).

## Arquivos de apoio (fora do git, em `data/saida/part_frentes/fp_produto/`)

- `comparar_partitura.py`: o aceite 1, por campo, e o cruzamento com a E1.
- `comparar_e1.py`: comparação campo a campo do `e1.json`.
- `casos_p4.py`: os 5 recortes e a lista dos 7 candidatos.
- `cabecalho_p4.py`: isoladas antes da primeira nota lida.
- `diag_tecnica.py`, `diag_ordem.py`: contagem de `tecnica` e de tipos e ordem nos documentos atuais.
- `e1_passo1.json`, `e1_passo2.json`: o `e1.json` regerado.
- `video/<stem>/<stem>.partitura.json`: os 3 documentos novos.

## Gate

`ruff check --no-cache .` e `ruff format --check --no-cache .` passaram. Pytest em `tests/`:
1596 passed, 2 skipped, 5 deselected, 2 xfailed. Os testes novos estão em
`tests/test_partitura_completar_pauta.py` (9) e `tests/test_partitura_video.py` (3). Não usam
`data/saida`, `artefatos` nem o acervo.

## Ajuste 1: a tab só completa onde a pauta está presente

**Motivo.** A revisão da sessão principal achou dois casos errados: gymnopédie T01 E4, sobre a clave
de sol, e greensleeves T03 C#5, sobre uma pausa. O erro é da tab do produto, e não da partitura.
Decisão do dono: uma nota da tab não é completada quando a pauta está calada naquele x, quando
fica antes do começo da pauta, ou quando a pauta tem a mesma nota uma oitava acima ou abaixo.

**Regras (a priori).** Tolerância `TOLERANCIA_PX` = 5,0 px no quadro, como nas outras regras.

- `ligada`: `tecnica` `lig`. Não entra (regra da P4 original).
- `harmonico`: `tecnica` `harm` com oitava na pauta. Não entra (regra da P4 original; o produto
  não tem essa marca).
- `pausa`: há uma pausa da leitura herdada (`x2_margem_herdada`) a até `TOLERANCIA_PX` do x da
  coluna, no mesmo recorte. O x da pausa sai dos slots do `.omr`, igual aos das notas.
- `cabecalho`: x da coluna < primeiro x da pauta (nota ou pausa) − `TOLERANCIA_PX`.
- `oitava`: a pauta tem a mesma nota, a até `TOLERANCIA_PX`, uma oitava acima ou abaixo. Vale para
  acorde e isolado. A regra antiga da 3013 (só acima) fica como diagnóstico na E1.

Motivo de cada nota que não entra: a primeira regra da lista acima que se aplica.

**Aceite (congelado antes da medida).**

1. Os 442 eventos que já existiam nos 3 documentos ficam idênticos, campo a campo, com o comparador.
2. gymnopédie T01 E4 (x 41,4) e greensleeves T03 C#5 (x 1768,1) não entram.
3. Os 7 candidatos de oitava da 3027 não entram. Cinco estão nos documentos finais: south T03 c12
   midi 52 e 59; gymnopédie T06 c4 midi 52; T11 c3 midi 61; T12 c1 midi 64. Os outros dois são do
   R07 (R01–R12), que não entra no documento final, e não se medem aqui.
4. Lista de cada nota que deixou de entrar (vídeo, tela, x, nota, motivo). As 66 da 3027 ficam
   divididas entre as que entram e as que saíram. Diz também se a gymnopédie T07 E3 (x 247,6)
   caiu em alguma regra.
5. Tabela nova por vídeo: completadas de acorde, isoladas, e não completadas por pausa, cabeçalho,
   oitava, harmônico e ligada. Tela 10 da gymnopédie à parte.
6. O `e1.json` da frente E não muda (`cmp` contra `fe_completar/e1.json`): as regras novas só valem
   no documento final.
7. Gate verde, o mesmo do briefing.

**Limite registrado antes da medida.** Uma pausa sem slot no `.omr` não tem x, e por isso não entra
na regra de pausa. A quantidade dessas pausas sai na rodada.

### Resultado do Ajuste 1

Gate: `ruff check`, `ruff format --check` e `pytest tests/` passaram (1602 passed, 2 skipped,
5 deselected, 2 xfailed).

| item do aceite | resultado |
| --- | --- |
| 1. 442 eventos que já existiam, campo a campo | **0 diferenças** (`comparar_partitura.py`: topo, pautas, eventos, símbolos existentes, resumo antigo) |
| 2. gymnopédie T01 E4 e greensleeves T03 C#5 não entram | **não entram**: T01 E4 por `cabecalho`; T03 C#5 por `pausa` |
| 3. os 7 candidatos de oitava não entram | **5 de 5 que estão no documento não entram**: south T03 c12 m52 e m59 (`oitava`); gym T06 c4 m52 (`pausa`, que vem antes de `oitava`); T11 c3 m61 (`oitava`); T12 c1 m64 (`oitava`). Os 2 do R07 não estão no documento final |
| 4. lista das notas que deixaram de entrar, com o motivo | **41 notas** (tabela abaixo). 66 = 25 que entram + 41 que saem |
| 4. gymnopédie T07 E3 (x 247,6) | **caiu em `pausa`** (isolada, compasso 1). Outras 4 notas do T07 também caem em `pausa` |
| 5. tabela por vídeo | ver abaixo |
| 6. `e1.json` da frente E não muda | **igual** (`cmp` contra `fe_completar/e1.json`: 0) |
| 7. gate | **verde** |

**Conciliação com a E1** (`motivos_p4.py`): fora da tela 10, a E1 tem 37 notas; 11 entram e 26
saem (pausa 21, cabeçalho 1, oitava 4). Na tela 10 da gymnopédie, a E1 tem 29; 14 entram e 15
saem. Conferido por script: "OK".

Ponto para o dono: `comparar_partitura.py` ainda compara as completadas com a E1 como se nada
tivesse saído. Esses 4 avisos são esperados (a conta não fecha sem as 41 notas que saíram); a
conciliação correta é a do `motivos_p4.py`, que fecha.

**Tabela por vídeo (completadas que entram; motivos de não entrar)**

| vídeo | pautas | pautas pequenas | acorde | isoladas | pausa | cabeçalho | oitava | harmônico | ligada |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| greensleeves | 4 | 0 | 0 | 0 | 1 (iso) | 0 | 0 | 0 | 0 |
| south american | 3 | 3 | 1 | 1 | 0 | 0 | 2 (acorde) | 0 | 0 |
| gymnopédie (sem a tela 10) | 12 | 0 | 8 | 1 | 20 (17 acorde, 3 iso) | 1 (iso) | 2 (acorde) | 0 | 0 |
| **gymnopédie tela 10 (à parte)** | — | — | 5 | 9 | 14 (12 acorde, 2 iso) | 0 | 1 (iso) | 0 | 0 |
| **total** | 19 | 3 | 14 | 11 | 35 (29 acorde, 6 iso) | 1 | 5 | 0 | 0 |

Total: 25 entram (14 acorde, 11 isoladas); 41 saem (35 por `pausa`, 1 por `cabecalho`, 5 por
`oitava`). Por `harmonico` e `ligada`: 0 e 0, como antes (o produto não tem essas marcas).

**Lista das 41 notas que deixaram de entrar** (vídeo, tela, recorte, x no quadro, nota, tipo, compasso, motivo):

| vídeo | tela | recorte | x | nota | tipo | compasso | motivo |
| --- | ---: | --- | ---: | --- | --- | ---: | --- |
| greensleeves | 3 | T03 | 1768,1 | C#5 | isolado | 8 | pausa |
| south | 3 | T03 | 1882,7 | E3 | acorde | 12 | oitava |
| south | 3 | T03 | 1882,7 | B3 | acorde | 12 | oitava |
| gym | 1 | T01 | 41,4 | E4 | isolado | 1 | cabecalho |
| gym | 1 | T01 | 1450,5 | A#5 | acorde | 6 | pausa |
| gym | 2 | T02 | 476,0 | A3 | acorde | 2 | pausa |
| gym | 2 | T02 | 476,0 | G#6 | acorde | 2 | pausa |
| gym | 2 | T02 | 708,0 | E3 | isolado | 3 | pausa |
| gym | 2 | T02 | 1679,5 | E3 | acorde | 7 | pausa |
| gym | 3 | T03 | 744,3 | D#6 | acorde | 3 | pausa |
| gym | 3 | T03 | 981,9 | G#6 | acorde | 4 | pausa |
| gym | 3 | T03 | 1219,5 | C#6 | acorde | 5 | pausa |
| gym | 4 | T04 | 986,1 | E3 | acorde | 4 | pausa |
| gym | 4 | T04 | 1443,7 | E3 | acorde | 6 | pausa |
| gym | 4 | T04 | 1701,1 | E3 | acorde | 7 | pausa |
| gym | 6 | T06 | 1034,1 | E3 | acorde | 4 | pausa (também oitava) |
| gym | 7 | T07 | 247,6 | E3 | isolado | 1 | pausa |
| gym | 7 | T07 | 992,2 | A3 | acorde | 4 | pausa |
| gym | 7 | T07 | 992,2 | B4 | acorde | 4 | pausa |
| gym | 7 | T07 | 1474,0 | G#6 | acorde | 6 | pausa |
| gym | 7 | T07 | 1707,6 | E3 | isolado | 7 | pausa |
| gym | 8 | T08 | 967,8 | A#5 | acorde | 4 | pausa |
| gym | 9 | T09 | 240,3 | G#6 | acorde | 1 | pausa |
| gym | 9 | T09 | 1680,3 | E3 | acorde | 7 | pausa |
| gym | 10 | T10 | 245,6 | A3 | acorde | 1 | pausa |
| gym | 10 | T10 | 467,3 | A3 | isolado | 2 | pausa |
| gym | 10 | T10 | 538,8 | G4 | acorde | 2 | pausa |
| gym | 10 | T10 | 538,8 | C5 | acorde | 2 | pausa |
| gym | 10 | T10 | 538,8 | E5 | acorde | 2 | pausa |
| gym | 10 | T10 | 717,5 | A3 | acorde | 3 | pausa |
| gym | 10 | T10 | 789,0 | G4 | isolado | 3 | oitava |
| gym | 10 | T10 | 967,8 | A3 | acorde | 4 | pausa |
| gym | 10 | T10 | 1218,0 | A3 | acorde | 5 | pausa |
| gym | 10 | T10 | 1218,0 | B5 | acorde | 5 | pausa |
| gym | 10 | T10 | 1468,3 | A3 | acorde | 6 | pausa |
| gym | 10 | T10 | 1689,9 | A3 | isolado | 7 | pausa |
| gym | 10 | T10 | 1761,4 | G4 | acorde | 7 | pausa |
| gym | 10 | T10 | 1761,4 | C5 | acorde | 7 | pausa |
| gym | 10 | T10 | 1761,4 | E5 | acorde | 7 | pausa |
| gym | 11 | T11 | 697,7 | C#4 | acorde | 3 | oitava |
| gym | 12 | T12 | 831,7 | E4 | acorde | 1 | oitava |

**Pergunta aberta para o dono (a regra literal de pausa).** A regra da pausa vale para toda nota,
inclusive a que tem nota pareada no mesmo x. Por isso ela tira 29 notas de acorde da gymnopédie:
a pauta tem a nota da coluna, e a pausa está numa outra voz ou num outro sistema. Se a regra valer
só para nota isolada, esses acordes voltam. Não mudei a regra sem a sua decisão. As 6 pausas
isoladas (inclusive a do greensleeves e a do gym T07 E3) continuam fora.

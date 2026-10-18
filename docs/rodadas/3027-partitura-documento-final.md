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

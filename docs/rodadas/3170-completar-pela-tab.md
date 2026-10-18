# 3170 — E1: completar pela tab o que a pauta não leu

Frente E (completar pela tab), item E1 de `docs/pesquisa/partitura-frentes.md`, seção 7.
Briefing da onda 1 (`docs/pesquisa/partitura-onda1-briefings.md`).

**Medida, sem limiar de aceitação.** Feita na cópia isolada `chorinho-partitura-env/repo`.
Módulo: `tab/partitura_completar.py`. Testes: `tests/test_partitura_completar.py` (2, puros).
Saída: `data/saida/part_frentes/fe_completar/e1.json` (só as notas completadas; nenhum
`.partitura.json` foi reescrito).

## Método (no código)

Para cada evento da tab sem nota da partitura com aquela altura:

- **acorde**: há evento da partitura pareado no mesmo x (`confere_x` verdadeiro). A nota entra
  nele, com a figura e a voz do evento. Voz 2 para as cordas 4 a 6, se o compasso tem voz 2.
- **isolado**: não há evento pareado. A figura vem do déficit do compasso: duração esperada
  (fração) menos a maior soma por voz. Se o déficit é uma figura só (inclui pontuada), a figura
  entra. Senão, `figura` fica `null`. Nunca se descarta nota.

Conjuntos: as 19 telas dos 3 produtos (tab do produto `fase8/rede`, pareamento por `coluna`);
R01–R12 (tab do gabarito, pareamento em memória de `_parear_recorte`, o mesmo do bloco A do CA1).

## Contagens

| conjunto | notas que faltavam | acorde | isolado | com figura | figura `null` |
| --- | ---: | ---: | ---: | ---: | ---: |
| 19 telas dos produtos | 66 | 47 | 19 | 47 | 19 |
| R01–R12 | 19 | 12 | 7 | 12 | 7 |
| **total** | **85** | **59** | **26** | **59** | **26** |

- **Isolados nos produtos (19)**: 0 com figura pelo déficit. 17 não têm duração esperada (a
  fração não está nas pautas 2 a 12 da Gymnopédie, `fracao` `None`). 2 têm déficit zero ou
  negativo, e nada decide.
- **Isolados em R01–R12 (7)**: 0 com figura pelo déficit. 4 não têm duração esperada e 3 têm
  déficit zero ou negativo. A causa não foi detalhada nesta rodada.
- **Herança de erro da tab nos produtos**: 39 de 66 notas completadas nos produtos não casam,
  no mesmo x (tolerância 6 px), com nenhuma nota do gabarito de tab. É uma estimativa
  aproximada: a comparação é por x, e o CA1 conta 21 alturas erradas na tab do produto. A
  diferença entre 39 e 21 não foi explicada; fica para checagem.
- **R01–R12**: a altura completada sai certa por construção (vem da tab do gabarito). Nesse
  conjunto a E1 só mede a figura, como diz o plano.

## Fora da conta (regras do plano)

- **Harmônico** (rodada 3013) e **nota ligada** (`(6)`): **não foram detectados**. O método
  não tem essa detecção ainda. Portanto a contagem "quantas saíram" é zero, e isso é ausência de
  detecção, não medida.
- **Tela 10 da Gymnopédie** (cordas deslocadas, rodada 3014): **não foi separada**. Fica na conta,
  o que é um limite.

## Aceite

- **Figura certa na conferência do dono** (0,95 nos acordes, 0,80 nos déficits, 0,95 nas 32 do
  homr): **não medido**. A conferência é do dono, e a ferramenta não foi servida (porta 8122).
- **Nenhum compasso passa da duração esperada**: o método não adiciona duração a compasso algum
  (acorde não soma, isolado sem figura não soma). Não há compasso novo acima da esperada.
- **Símbolos existentes idênticos**: vale por construção. O `e1.json` só traz notas novas.
- **Pare se mais da metade das notas que faltam não tiver evento nem déficit calculável**: 26 de
  85 (31 %) ficam sem nenhum dos dois. Abaixo do limite de 50 %, então a E1 segue.

## Determinismo

Duas execuções dão o mesmo `e1.json` (`cmp`). Lint: `ruff check` e `ruff format --check` passam.

## Não feito

- **Casos olhados** (10 casos, recorte e nota): não olhados. Ficam pendentes.
- **Conferência do dono**: não servida nem montada como item, porque os itens dependem da
  função de item do gabarito, que não foi copiada.
- **Commit**: sem git nesta máquina.


## Casos olhados (2026-10-17)

Recortes em `data/saida/part_frentes/fe_completar/casos/` (ampliados 3×, com 50 px de cada lado
do x da nota):

1. **south american T01, compasso 1, midi 60 (acorde, colcheia, voz 1)**: a imagem não deixa ler a
   altura com segurança nesta escala. O grupo de colcheias com feixe está no meio do recorte.
   Inconclusivo.
2. **gymnopédie T10, compasso 1, midi 57 (acorde, meia pontuada, voz 2)**: a meia pontuada na
   pauta inferior bate com a figura registrada. A figura veio do evento pareado no mesmo x (E5
   meia pontuada). Certo na figura.
3. **gymnopédie T03, compasso 5, midi 85 (acorde, meia pontuada, voz 1)**: a meia pontuada do
   pentagrama superior bate com a figura. A nota de 76 (meia sem ponto, voz 2) não tem altura
   identificável nesta imagem; a figura dela fica inconclusiva.
4. **R05, compasso 1, midi 60**: recorte salvo, não olhado.
5. **R07, compasso 10, midi 52 e 59 (acorde, meia, voz 2)**: acorde de semínimas brancas com 6
   cabeças na haste; as duas completadas estão dentro dele. A figura bate. Certo na figura.

Até aqui: **4 de 10 casos olhados** (1, 2, 3 e 5), com a altura inconclusiva no 1 e a figura
inconclusiva na segunda nota do 3. Os 6 restantes (4, e os de outros compassos) não foram olhados.

A conferência do dono não foi montada nem servida.

## Revisão da sessão principal (2026-10-17)

Rodado de novo no container, na `main`: a saída deu igual byte a byte à da cópia (`cmp`).

- **Base de R01–R12.** `_parear_recorte` já roda `completar_com_homr`. Então as 19 notas que faltam são as da leitura com o homr confirmado pela tab (linha A do CA1: 14 faltando e 4 de altura errada), e não as 41 da leitura só com o Audiveris.
- **39 de 66 nos produtos.** A conta foi feita fora do módulo e não está no `e1.json`. É compatível com a linha B do CA1: a tab do produto tem 21 alturas erradas e 17 inventadas, 38 no total. Leitura provável: nos produtos, a maior parte do que "falta" na partitura é erro da tab, e não da pauta. Completar pela tab do produto tem de esperar a régua da tab, ou a conferência do dono.


## Revisão (2026-10-17): contas feitas pelo código, harmônico e tela 10 à parte

O módulo agora faz as contas (`tab/partitura_completar.py`). A conta antiga de 39 de 66 foi
feita fora do módulo e não vale mais.

- **Contadas** (fora harmônico e tela 10): produtos 32 (25 acorde com figura, 7 isolado sem
  figura); R01–R12 17 (10 acorde, 7 isolado sem figura).
- **Harmônico** (regra da 3013: a pauta tem a nota uma oitava acima no mesmo x): 8, à parte.
- **Tela 10 da Gymnopédie** (rodada 3014): 28, à parte.
- **Nota ligada**: **não detectável** no produto (`tecnica` é `None` em quase todas as notas;
  só uma tem `enfeite`). Contagem 0, e isso é ausência de detecção, não medida.
- **Herda erro da tab** (altura que não existe no gabarito de tab no mesmo x, tolerância 6 px):
  **13 de 32** nos produtos (10 acorde, 3 isolado). Nas R01–R12 a altura é circular por
  construção, então não entra.

## Casos olhados (acumulado: 6)

Recortes em `data/saida/part_frentes/fe_completar/casos/` (ampliados 3×).

- **Acorde, south american T01 c1 midi 60**: inconclusivo na altura (escala pequena).
- **Acorde, gymnopédie T10 c1 midi 57 (meia pontuada, voz 2)**: certo na figura.
- **Acorde, gymnopédie T03 c5 midi 85 (meia pontuada, voz 1)**: certo na figura. A nota de 76
  (meia sem ponto, voz 2) fica inconclusiva.
- **Acorde, R07 c10 midi 52 e 59 (meia, voz 2)**: certo na figura.
- **Isolado, greensleeves T03 c8 midi 73**: **suspeito**. Na pauta, na posição x dessa coluna,
  há uma pausa, não uma nota. A tab não tem pausa (plano, pegadinha da E1). Esse completamento
  pode ser falso.
- **Acorde, R09 c3 midi 87**: **erro**. A imagem tem um losango (harmônico) e a marca "A.H.".
  A regra da oitava não pegou, porque a pauta não lê o losango como nota. A nota completada
  deveria estar à parte.

Pelo critério do briefing (pelo menos 2 isolados e 2 de R01–R12), **ainda falta**: só 1 isolado
foi olhado, e ele é suspeito. Os casos isolados seguem sem a conta fechada.

## Falha achada: harmônico com losango não é detectado

O caso R09 c3 (midi 87) mostra que a detecção de harmônico só pela oitava na pauta não basta:
o losango não vira nota no `.omr`/MusicXML. Isso precisa de outra fonte (a tab, o "A.H." da
imagem ou uma lista de casas harmônicas). Não corrigido nesta rodada.

## Pausa no mesmo x (suspeita)

O caso greensleeves T03 c8 mostra o risco: completar nota onde a pauta tem pausa. Não há
checagem de pausa no código ainda.

## Não feito nesta revisão

- Conferência do dono (`servir` na porta 8122): não montada. O item precisa de um adaptador
  para a ferramenta de conferência, que hoje é por símbolo de MusicXML.
- Os 10 casos completos (faltam 4, com pelo menos 1 isolado a mais).


## Revisão 2 (2026-10-17): decisão do dono sobre harmônico

Decisão do dono: harmônico vem **só da tab** (símbolo de harmônico guardado na tab) e conta à
parte. Nada de detector de imagem. Se a tab não tiver o símbolo, conta como "harmônico não
detectado".

O que a tab tem: o ouro de tab (`data/gold/ouro_video`) guarda só `corda`, `casa`,
`x_quadro` e `x_centro_quadro`; o produto tem `tecnica` `None` em quase tudo (uma nota com
`enfeite`). **Não há símbolo de harmônico em nenhuma das duas fontes.** Por isso:

- **Harmônico (da tab): 0 detectado.**
- **Harmônico não detectado, candidatos pela regra de oitava** (diagnóstico, na 3013): 7.
  Esses 7 continuam contados como completados, porque a regra de oitava saiu da conta.
- **Tela 10 da Gymnopédie**: 29 à parte (antes 28, porque um dos casos saiu como harmônico
  pela regra antiga).
- **Nota ligada**: não detectável (tecnica `None`). Declarado, com 0.

Contagem nova: **contadas 56** (produtos 37: 30 acorde com figura e 7 isolado sem figura;
R01–R12 19: 12 acorde e 7 isolado sem figura).

**Herda erro da tab** (produtos, pelo código): **14 de 37**. Nas R01–R12 a altura é circular.

Caso R09 c3 midi 87 (losango e "A.H." na imagem, visto antes): continua como completado, porque
a tab não tem o símbolo. Esse caso é a falha que o dono precisa ver na conferência.

Não feito: conferência do dono (porta 8122, itens) — ver o ponto de conferência acima.


## Casos olhados (revisão 3: 10 casos distintos)

Recortes em `data/saida/part_frentes/fe_completar/casos/` (3×). O caso "R05 c1 midi 60" é o
mesmo recorte do "south american T01 c1 midi 60" (R05 = south american tela 1), então conta uma
vez só.

| # | caso | leitura | figura registrada | imagem |
| --- | --- | --- | --- | --- |
| 1 | south american T01 / R05, c1, midi 60, acorde | inconclusivo | eighth, voz 1 | altura não dá para confirmar na escala |
| 2 | gymnopédie T10, c1, midi 57, acorde | certo | half pontuada, voz 2 | bate |
| 3 | gymnopédie T03, c5, midi 85, acorde | certo | half pontuada, voz 1 | bate; a de 76 fica inconclusiva |
| 4 | R07, c10, midi 52 e 59, acorde | certo | half, voz 2 | bate |
| 5 | greensleeves T03, c8, midi 73, isolado | **suspeito** | sem figura | há pausa na pauta nesse x (falso completamento?) |
| 6 | R09, c3, midi 87, acorde | **erro** | half | losango e "A.H." (harmônico); a tab não tem o símbolo |
| 7 | gymnopédie T02, c3, midi 52, isolado | figura não resolvida | null | a imagem tem meia pontuada no x; o método não tem como dar a figura |
| 8 | R11, c4, midi 57, acorde | **erro de figura** | quarter, voz 2 | a imagem mostra meia pontuada na pauta de baixo |
| 9 | gymnopédie T07, c4, midi 57, acorde | **erro de figura** | quarter, voz 2 | mesma coisa: meia pontuada na imagem |
| 10 | R10, c2, midi 52, acorde | certo | half pontuada, voz 2 | bate |

**O que isso diz.** Nos acordes com figura que eu consegui olhar (2, 3, 4, 8, 9, 10 e o 6 pela
figura), a figura bate em 4 e erra em 2 (o 6 é harmônico, não figura). Os dois erros (8 e 9) são
o mesmo padrão: a nota da voz 2 em clave de baixo é meia pontuada, e a E1 pega a figura do evento
pareado (a semínima da voz 1), e não a da própria voz. O aceite do briefing pede 0,95 nos
acordes. Com essa amostra, o método **não passa**.

**Isolados.** Dos 2 isolados olhados, um é suspeito de pausa (5) e outro tem figura não
resolvida (7). Nenhum dos dois tem figura correta pelo método. Mínimo de "2 isolados": cumprido,
mas os dois não viram acerto.

**Correção aplicada (revisão 3).** A figura do acorde agora vem do símbolo da **mesma voz**
da nota completada. Se o evento pareado não tem símbolo nessa voz, a figura fica `null` (nada
decide). Isso corrige os erros 8 e 9, mas tira a figura de notas que a leitura não tem na voz
(como os baixos dos casos 2, 4 e 10, que estavam certos por acaso).

Números após a correção: contadas 56. Figura registrada em **22** (produtos 17 de 37, R01–R12
5 de 19). Ficam `null` 34: 20 nos produtos e 14 em R01–R12. Antes eram 14 `null`. Quem decide a
figura dessas 34 é a conferência do dono.

O aceite de 0,95 não é atingido com as olhadas: ver a tabela acima. A conferência do dono
continua sendo a medida; esta rodada só registra o que o código faz agora.

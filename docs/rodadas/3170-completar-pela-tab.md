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

## Revisão da sessão principal (2026-10-17)

Rodado de novo no container, na `main`: a saída deu igual byte a byte à da cópia (`cmp`).

- **Base de R01–R12.** `_parear_recorte` já roda `completar_com_homr`. Então as 19 notas que faltam são as da leitura com o homr confirmado pela tab (linha A do CA1: 14 faltando e 4 de altura errada), e não as 41 da leitura só com o Audiveris.
- **39 de 66 nos produtos.** A conta foi feita fora do módulo e não está no `e1.json`. É compatível com a linha B do CA1: a tab do produto tem 21 alturas erradas e 17 inventadas, 38 no total. Leitura provável: nos produtos, a maior parte do que "falta" na partitura é erro da tab, e não da pauta. Completar pela tab do produto tem de esperar a régua da tab, ou a conferência do dono.

# 0006 — Casa de dois algarismos pela forma (Fase 4, continuação da 0005)

**Data:** 2026-10-10. **Vídeo:** `sky guitar/retrato brasileiro - tab & lesson.mp4`, ouro v2 (`data/gold/ouro_video/retrato_brasileiro_v2.json`, não editado).
**Medições brutas:** `data/saida/fase4_digitos/` (`probe_12_tecnica.py`, `probe_12_forma.py`, `medir_pares_forma.py` → `pares_vao40.json`,
`ler_paginas.py` → `paginas_base.json`, `paginas_soforma.json`, `paginas_fundir040b.json`, `paginas_final.json`,
`comparar_*.txt`, `avaliar_tres_*.txt`, `probe_12_grade*.py`, `probe_sintetico_12.py`).

## Pergunta

A 0005 mostrou que o vão não separa `12` de notas vizinhas e que o token fundido de dois dígitos é rotulado `tecnica`.
Esta rodada pergunta: a casa de dois algarismos se decide pela **forma** (o que o classificador lê das partes), e não pelo vão?

## 1. Por que o `12` fundido vira `tecnica` (pág. 8, corda 2, `x` 1125)

Medido com `probe_12_forma.py` e `probe_12_tecnica.py` no token:

- largura do token 1,20 passo; componentes de 0,37 (`1`) e 0,60 (`2`) passo;
- `partes = 2`, mas `partes_digito = 1`: o `2` não tem haste vertical, então `_fundir` conta uma haste só;
- top-3 do token: `12` 0,888; `tecnica` 0,112; `harmonico` 0,001;
- `compativel("12")` = **False** (exige `partes_digito >= 2`), e a classe cai no próximo top compatível: `tecnica`, que é aceita.

Ou seja: a regra de forma de `compativel` recusa o número por construção. Ela foi escrita para o caso de slide
(`7` com barra fundida, canal `raman korshun`, descartado) e exige haste em **dois** componentes, o que um `2` nunca tem.
O teste `tests/test_compativel.py::test_dois_digitos_exigem_dois_componentes` fixa essa regra e não foi alterado.

Dois outros casos de dois algarismos nem chegam fundidos: `10` (pág. 12, corda 2) e `12` (pág. 12, corda 1) têm vão
0,275 passo, acima do limiar de `agrupar_tokens` (0,25). O `13` (pág. 8, corda 3) tem vão 0,324.

## 2. Pares vizinhos com vão em (0,25; 0,40] passo

`medir_pares_forma.py` mede, para cada par de componentes brutos na mesma corda com vão menor que 0,4 passo, a leitura
isolada de cada um, a leitura do fundido e a probabilidade da concatenação. Rótulo do ouro por centro, como em `medir_vaos.py`.

| par (pág., corda) | ouro | vão | isolados | fundido: top-1 (p) | p(concatenação) |
| --- | --- | --- | --- | --- | --- |
| 8, 2 | `14` (já fundido a 0,231) | 0,231 | `1` 0,74 · `4` 0,90 | `14` 0,83 | 0,832 |
| 8, 2 | `12` (já fundido a 0,231) | 0,231 | `1` 0,68 · `2` 0,94 | `12` 0,89 | 0,888 |
| 12, 2 | `10` | 0,275 | `1` 0,70 · `0` 1,00 | `10` 0,91 | 0,910 |
| 12, 1 | `12` | 0,275 | `1` 0,70 · `2` 0,95 | `12` 0,90 | 0,896 |
| 8, 3 | `13` | 0,324 | `1` 0,62 · `3` 0,99 | `12` 0,63 | não é classe |
| 5, 1 | sem nota casada (`2`→`7`, notas distintas na 0005) | 0,324 | `2` 0,93 · `7` 0,97 | `tecnica` 0,80 | `27` não é classe |
| 5, 1 | sem nota casada (`7`→`4`) | 0,37 | `7` 0,97 · `4` 0,92 | `tecnica` 0,37 | `74` não é classe |
| 8, 1 | sem nota casada (`5`→símbolo) | 0,37 | `5` 0,99 · `14` 0,26 | `tecnica` 0,87 | não é dígito |

Nenhum par com as duas notas casadas ao ouro e de notas diferentes aparece com vão menor que 0,4 (contagem `distintas` = 0).
Os 9 pares `sem_nota` são os da 0005: um componente não tem nota casada, e nenhum forma número de 10 a 24. Os pares
`mesma1` (40 casos) têm vão negativo, ou seja, são sobreposição de componentes da mesma nota, e já são fundidos por `agrupar_tokens`.

Uma linha duplicada (pág. 12, corda 1, vão 0,275, geometria idêntica) aparece no conjunto. Não investiguei a origem;
as duas linhas passam pela mesma regra e não mudam a decisão.

**O critério "fundido maior que os isolados", como pedido, foi medido e reprovado:** no `12` da pág. 8 o fundido (0,888)
é menor que o `2` isolado (0,943), e a regra o rejeitaria. A condição que separa os casos é outra: a concatenação das
leituras isoladas tem de ser uma classe do modelo entre 10 e 24, e o fundido tem de dar a ela pelo menos 0,80.

**Limitação do modelo, não da regra:** os dois-dígitos do `artefatos/oficial_3` são `10, 12, 14, 15, 17, 19, 21, 24`
(o gerador desenha só essas classes). `13` não é classe, então nenhuma regra de forma lê `13`. Corrigir exige
classes novas e retreino, o que é cobertura do gerador (regra 6 do AGENTS.md) e fica para outra rodada.

## 3. Variantes medidas nas 13 páginas (pareamento direto, `comparar_paginas.py`)

Base = HEAD (`paginas_base.json`, reproduz `comparar_antes.txt`).

| variante | casas certas | dois-dígitos certos | inventadas | páginas que pioram |
| --- | --- | --- | --- | --- |
| base (HEAD) | 481/493 | 1 de 5 (só o `14`) | 21 | — |
| A: só forma (`_casa_das_partes` no token, sem fusão nova) | 482/493 | 2 de 5 (`14`, `12` pág. 8) | 21 | nenhuma |
| **B: forma + fusão de pares com vão até 0,40 (escolhida)** | **484/493** | **4 de 5** (`14`, `12` pág. 8, `10` e `12` pág. 12) | **19** | **nenhuma** |

Por página, B contra base: pág. 8 de 41 para 42 (`12` certo, entregues 43 → 44); pág. 12 de 33 para 35 (`10` e `12` certos,
inventadas 2 → 0); as demais páginas iguais, inclusive a pág. 5 (39/42/3), que foi a que quebrou na tentativa 0005.
Único erro de dois dígitos que resta: `13` da pág. 8, que sai `1` (não é classe do modelo).

**Aceite (critério do dono):** dois-dígitos sobe (1 → 4), casas certas não cai (481 → 484), inventadas não sobe (21 → 19),
nenhuma página piora. **Aceito.**

Medição com o código final (`paginas_final.json`, `comparar_final.txt`): 484/493, 19 inventadas.

## 4. Gabarito de glifos (`tab.avaliar`, por índice de token)

`avaliar_tres_base.txt` e `avaliar_tres_final.txt`: oficial_1 66/72, oficial_2 71/72, oficial_3 68/72, iguais antes e depois.
Nenhuma linha "CONTAGEM MUDOU" (conferido também chamando `tab.avaliar.avaliar` diretamente): o número de tokens de cada
canal bate com o gabarito. A fusão nova não mexe na contagem dos canais medidos.

## 5. Implementação

- `tab/reconhecer.py`:
  - `LIMIAR_CASA_DOIS = 0.80`, `VAO_AGRUPAR_PASSOS = 0.25`, `VAO_CASA_PASSOS = 0.40`;
  - `_casa_das_partes(lidos, probs_token, rotulos)`: a casa se as partes são dígitos, a concatenação é classe do modelo entre 10 e 24 e o token dá a ela pelo menos 0,80;
  - `_fundir_pares_de_digitos(...)`: pré-passada que funde dois dígitos isolados com vão em (0,25; 0,40] quando `_casa_das_partes` aceita;
  - `reconhecer_linha` usa a leitura das partes antes de `compativel` para tokens com dois componentes;
  - a nota passa a carregar `caixa` (caixa do token), porque o token fundido não existe na grade de `segmentar`.
- `tab/ouro_video.py::ler_notas`: usa `n["caixa"]` quando existe. Sem isso o centro do token fundido sai deslocado e o pareamento falha (foi o que aconteceu na primeira versão de B: o `10` da pág. 12 sumia).
- `compativel` **não foi alterado**; o teste que fixa a regra de slide continua valendo.

## 6. Testes

`tests/test_casa_dois_digitos.py` (gate, sem pesos):
- decisão `_casa_das_partes`: `12` com confiança vira `12`; sem confiança não vira; `13` (não é classe) não vira; parte que não é dígito não vira; dígito único não vira;
- fusão `_fundir_pares_de_digitos` com `_probs` trocado: `1`+`2` com vão 0,3 funde; `1`+`3` continua dois; `2`+`7` (nota distinta) continua dois; vão 0,2 e vão 0,5 não chegam ao classificador; dígito único não muda.

Ponta a ponta (`@pytest.mark.integration`, pulado sem `artefatos/oficial_3`, porque `artefatos/` está no `.gitignore`):
linha desenhada como o gerador (Liberation Bold, passo 20, fonte 0,75): `12` sai como uma casa `12`; `1` e `2` separados sai como `1`, `2`.
Rodado com `-m 'integration or not integration'`: passa.

Discriminação: na varredura sintética (`probe_12_grade.py` e `probe_12_grade_head.py`), passo 20 com fonte 0,65 e 0,75 sai
`tecnica` com a regra desligada (`LIMIAR_CASA_DOIS = 2.0`, equivalente ao HEAD) e `12` com a regra. O teste usa passo 20 e fonte 0,75.

Gate: `pytest tests/` = **231 passed, 3 deselected** (integração).

## 7. Gate (não fechado)

`make gate` **falha** por `tab/presenca_aval.py` (arquivo novo, não rastreado, de outro agente): `RUF046` (linha 257),
`C416` (linha 269) e formatação (linha 120). Os arquivos desta rodada passam em `ruff check` e `ruff format --check`.
Não toquei nesse arquivo. Por isso **não commitei**: a regra do projeto é gate 0 antes do commit.

## Não repetir

- Critério "fundido maior que o maior isolado" para aceitar a casa: reprova o `12` da pág. 8 (0,888 contra 0,943).
- Fusão por vão sem olhar a leitura do fundido: já medida e revertida (0005).
- `13` como casa: não é classe do modelo; só com classe nova e retreino.

## Defeito separado (não corrigido aqui)

No `reconhecer_linha`, o bloco do **discriminador** de algarismo (3a passada) roda **antes** de `classes` ser preenchido
(o `for` que faz `classes.append` vem depois). Pela ordem do código, `alvos_d` fica sempre vazio e o discriminador não
atua. Não medi o efeito de corrigir isso, e corrigir muda os números de base; fica para uma rodada própria.

## Próximo passo

Fechar o gate (o dono ou o agente de `tab/presenca_aval.py` resolve o RUF046/C416/formatação), rodar `make gate` com saída 0,
e commitar os arquivos desta rodada: `tab/reconhecer.py`, `tab/ouro_video.py`, `tests/test_casa_dois_digitos.py`,
`docs/rodadas/0006-casa-dois-algarismos-forma.md` e a seção no `ESTADO.md`.

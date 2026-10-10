# 0004 — Fase 0: arrumar a régua (2026-10-10)

Plano executado: [`docs/guias/plano-do-produto.md`](../guias/plano-do-produto.md), **Fase 0**.
Gate: **`make gate`** (novo) — `ruff check` + `ruff format --check` + `pytest -q -p no:cacheprovider`.

## O que foi feito, com o número

| tarefa | o que mudou | evidência |
| --- | --- | --- |
| **T0.1** | número oficial: **0,889 (96 glifos / 4 canais)** → **0,949 (66/72, 71/72, 68/72) em 72 glifos / 3 canais**, com a nota de que **não é ganho** (o denominador caiu quando o `raman korshun` saiu); acervo → **3.899 vídeos / 255 GB / 17 canais** | em `AGENTS.md`, `README.md` e `artefatos/LEIA-ME.md`: `0,889`=0, `0,892`=0, `3.908`=0, `183 GB`=0, `96 glifos`=0 (a única ocorrência restante é a frase que **explica** a mudança, no `LEIA-ME`) |
| **T0.2** | `MODELO_PADRAO` → **`artefatos/oficial_3/glifo_sint.pt`** (semente **mediana**, 68/72). Medido antes: o antigo `glifo_sint.pt` dava **72/72 = 1,000** no próprio gabarito | `python -m tab.avaliar` → `modelo carregado: /app/artefatos/oficial_3/glifo_sint.pt` + `TOTAL=68/72=0.944`; decisão em [`docs/decisoes/0008-modelo-do-produto.md`](../decisoes/0008-modelo-do-produto.md) |
| **T0.3** | os números de tempo de 2026-10-10 (**"sky 40/44"**, **"mr. tabs 16/68"**, **"serge 47/49"**) ficam **NÃO VALIDADOS**, com as quatro evidências; os quatro itens entraram na tabela "não repetir" | seção datada no `ESTADO.md` + 4 linhas novas na tabela |
| **T0.4** | `COMPOSE ?=` com os dois `-f` e alvo **`gate`** (receita em TAB, sem `|| echo`) | árvore limpa → `EXIT=0`; com teste quebrado → `EXIT=2` ("1 failed, 120 passed"); revertido → `EXIT=0` |
| **T0.5** | bloco **"4ª rodada"** com **D1–D7** e o ⭐ de cada uma (seguir o padrão e registrar como suposição) | `PERGUNTAS.md`, tabela D1–D7 |

## Decisões tomadas por suposição (na falta do dono)

1. **`docs/` sai do ruff** (`extend-exclude = ["docs"]` em `pyproject.toml`): o `ruff format --check` tentava
   reformatar os **blocos de código de exemplo** do plano do cérebro e **derrubava o gate na árvore limpa** —
   o CA do T0.4 era inalcançável antes disso. **Não** reformatei o documento do cérebro (conteúdo é contrato).
2. **`tab/avaliar.py` passa a imprimir `modelo carregado: <caminho>`**: o CA do T0.2 exige "imprime o caminho"
   e o módulo **não imprimia**; o §4.3 do plano exige dizer qual modelo rodou em todo número.
3. Seguir os ⭐ de **D1–D7** enquanto o dono não responder (registrado no `PERGUNTAS.md`).

## Achados para o cérebro (não são tarefas desta fase)

1. **O plano derrubava o gate da árvore limpa** (§2.5 afirma "gate verde hoje") — pelo **próprio arquivo do
   plano** (blocos de código), e o **CA do T0.4 era inalcançável** antes disso;
2. **T0.1 erra a premissa sobre o `README.md`**: o número lá era **0,892** (órfão, não existe em nenhum outro
   arquivo) e o CA de "grep 0,889" **não o pegaria**; o `AGENTS.md` tinha ainda **dois** lugares que o T0.1
   não lista (tabela Vocabulário e "Limites conhecidos");
3. **`make gate` depende do `DOCKER_HOST`** e falha com erro de socket do Docker — indistinguível de "imagem
   ausente";
4. **`CONTEXTO.md` não está em nenhuma lista de correção** e carrega 3.908 / 183 GB / 0,889 / `FRAME_COUNT=0`
   (este último **corrigido** pelo §2.4 do plano: o `FRAME_COUNT` vem preenchido e o que falha é a
   **decodificação**);
5. **`docs/decisoes/0008` estava livre** (a numeração ia até 0007) — conferido antes de criar.

## Dívida registrada (fora do "pronto")

- A **Fase 1** (leitor único de vídeo, espaço de coordenadas, colunas) começa agora: é ela que **conserta por
  construção** as duas causas mecânicas das evidências 1 e 4 do T0.3.
- O `tab/pipeline.py` e o `tab/transcrever.py` **não foram tocados** nesta fase.

# Relatório da 9001 para a trilha maos

Data: 2026-10-22. Decisão: `docs/decisoes/9001-reestruturacao-dos-arquivos.md` (§9). Gate: 2060 passaram, 2 pulados.

## O que mudou para todas

- `tab/` e `tests/` têm uma pasta por trilha. Os nomes antigos de módulo (`tab.maos_braco_ciclo`…) continuam importando e rodando por apelido (`tab/_apelidos.py`); código novo usa o nome novo, absoluto.
- Funções repetidas viraram uma só em `tab/comum/`: `arquivos` (gravar_atomico, ler_json, nfc, slug), `acervo`, `semente` e `violao.AFINACAO_MIDI`. O nome antigo continua no módulo de origem como o mesmo objeto.
- O `ESTADO.md` é índice; o estado de cada trilha está em `docs/estado/<trilha>.md`.
- Saída nova vai em `data/saida/<trilha>/`. As 156 pastas soltas antigas foram para `data/saida/tablatura/` (155) e `data/saida/partitura/part_frentes`, com link no lugar antigo (o gabarito cita 8 delas, então esses links ficam para sempre).
- O AGENTS.md §10 tem o "Padrão de projeto": onde cada coisa mora e 7 regras.

## Sua trilha

- **Módulos movidos:** 66 (`tab/maos/`, `tab/maos/braco/`, `tab/maos/direita/`; o antigo `maos_braco.py` virou `maos/braco/braco.py`); testes: 57 em `tests/maos/`.
- **Código que mudou de lugar além da pasta:** `_ler_json` e `_nfc` (5 módulos do braço) agora vêm de `tab.comum.arquivos`; `AFINACAO_MIDI` (em `corda_sem_direita` e `direita/desempate`) vem de `tab.comum.violao`; `gravar_atomico` de `gabarito.py` vem de `tab.comum`.
- **Prova byte a byte:** `prova.py` na CPU (6 quadros da M36 com o par do ciclo) deu `cmp` igual a `antes.json` (sha256 2a77d8f6…) depois do código e depois dos dados.
- **Arquivo frio:** `m31/denso` (2,4 GB, os quadros densos da 1030/1031) e `m7c` (154 MB), 10.617 arquivos, 2.546 MB em `chorinho_arquivo/maos/arquivar-2026-10-22.tar` (tar --compare = 0). `m38`, `m16`, `frentes` e o resto de `data/saida/maos` ficam.
- **Pesos:** `artefatos/m21` (45 .pt, 2,7 GB) não foi movido. Os históricos (L1, L2, L4_capo, A1, A3, A5, A6, v2_sobreajuste, ~2,2 GB) podem ser arquivados depois da medida da 1041 na 1039.
- **Dívida que sobra:** ~200 imports de função privada (`from tab.x import _f`), quase todos dentro das mãos, e 11 módulos com mais de 1.500 linhas. Não foram mexidos; a regra 2 do padrão diz como tratar os novos.
- **Seu `data/saida/maos/` não tem `LEIAME.json`** nas pastas; vale criar (padrão regra 4).

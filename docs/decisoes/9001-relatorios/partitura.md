# Relatório da 9001 para a trilha partitura

Data: 2026-10-22. Decisão: `docs/decisoes/9001-reestruturacao-dos-arquivos.md` (§9). Gate: 2060 passaram, 2 pulados.

## O que mudou para todas

- `tab/` e `tests/` têm uma pasta por trilha. Os nomes antigos de módulo (`tab.maos_braco_ciclo`…) continuam importando e rodando por apelido (`tab/_apelidos.py`); código novo usa o nome novo, absoluto.
- Funções repetidas viraram uma só em `tab/comum/`: `arquivos` (gravar_atomico, ler_json, nfc, slug), `acervo`, `semente` e `violao.AFINACAO_MIDI`. O nome antigo continua no módulo de origem como o mesmo objeto.
- O `ESTADO.md` é índice; o estado de cada trilha está em `docs/estado/<trilha>.md`.
- Saída nova vai em `data/saida/<trilha>/`. As 156 pastas soltas antigas foram para `data/saida/tablatura/` (155) e `data/saida/partitura/part_frentes`, com link no lugar antigo (o gabarito cita 8 delas, então esses links ficam para sempre).
- O AGENTS.md §10 tem o "Padrão de projeto": onde cada coisa mora e 7 regras.

## Sua trilha

- **Módulos movidos:** 21 em `tab/partitura/` (sem o prefixo `partitura_`); testes: 10 em `tests/partitura/`.
- **Dados:** `data/saida/part_frentes` foi para `data/saida/partitura/part_frentes` (com link). O `gabarito_vazio` grava `fonte_itens` com o caminho resolvido, então gabaritos NOVOS vão gravar `data/saida/partitura/part_frentes/...`; os antigos têm o texto antigo (nada quebra).
- **Prova byte a byte:** `parear.txt`, `sha256_partitura.txt` e `ca1.txt` iguais; só muda o nome da pasta da cópia, por construção. `compassos_homr.json` e `figura_e1.json` continuam sem commit, e a cópia .tar de segurança está em `chorinho_arquivo/partitura/gabarito_fora_do_git`.
- **Arquivo frio:** 84 itens, 1.700 arquivos, 196 MB em `chorinho_arquivo/partitura/arquivar-2026-10-22.tar`. A imagem do SMT (`chorinho-partitura:smt`, ~24 GB junto com duas imagens das mãos) foi apagada.
- **Mensagens de commit** `data/saida/partitura/msg3193..3197.txt` já usadas estão na lista de apagar.

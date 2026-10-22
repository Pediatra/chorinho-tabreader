# Relatório da 9001 para a trilha audio

Data: 2026-10-22. Decisão: `docs/decisoes/9001-reestruturacao-dos-arquivos.md` (§9). Gate: 2060 passaram, 2 pulados.

## O que mudou para todas

- `tab/` e `tests/` têm uma pasta por trilha. Os nomes antigos de módulo (`tab.maos_braco_ciclo`…) continuam importando e rodando por apelido (`tab/_apelidos.py`); código novo usa o nome novo, absoluto.
- Funções repetidas viraram uma só em `tab/comum/`: `arquivos` (gravar_atomico, ler_json, nfc, slug), `acervo`, `semente` e `violao.AFINACAO_MIDI`. O nome antigo continua no módulo de origem como o mesmo objeto.
- O `ESTADO.md` é índice; o estado de cada trilha está em `docs/estado/<trilha>.md`.
- Saída nova vai em `data/saida/<trilha>/`. As 156 pastas soltas antigas foram para `data/saida/tablatura/` (155) e `data/saida/partitura/part_frentes`, com link no lugar antigo (o gabarito cita 8 delas, então esses links ficam para sempre).
- O AGENTS.md §10 tem o "Padrão de projeto": onde cada coisa mora e 7 regras.

## Sua trilha

- **Módulos movidos:** 11 em `tab/audio/` (sem o prefixo `audio_`), mais `cruzar_fontes` em `tab/cruzamento/`; testes: 7 em `tests/audio/`.
- **Código que mudou de lugar além da pasta:** `MIDI_CORDA` (`audio/onsets`) e `ALTURA_SOLTA` (`audio/som_medir`) agora são `tab.comum.violao.AFINACAO_MIDI`. Os dois `midi_da_nota` ficaram como estão, porque o código deles é diferente. Um teste confere que a altura sai igual por todos os caminhos, em 6 cordas × 25 casas.
- **Prova byte a byte:** `prova.sh` (alinhador, produto, régua, cruzamento e transcritor na imagem 3.10) deu `diff -r` vazio depois do código e depois dos dados.
- **Python 3.10:** o transcritor continua na imagem `chorinho-som`; `tab/__init__.py`, `_apelidos.py`, todos os `__init__.py` e `comum/caminhos.py` ficam em sintaxe 3.10 e só stdlib (um teste do gate trava isso). Isolar o transcritor numa pasta própria fica para depois; mantive o atalho do nome antigo, como você pediu.
- **Arquivo frio:** `audio/a0` e `audio/a1b`, 98 arquivos, 9 MB em `chorinho_arquivo/audio/arquivar-2026-10-22.tar`.
- **Pesos:** `artefatos/riley_guitar` (189 MB) fica onde está.

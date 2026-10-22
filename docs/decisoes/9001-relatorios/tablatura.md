# Relatório da 9001 para a trilha tablatura

Data: 2026-10-22. Decisão: `docs/decisoes/9001-reestruturacao-dos-arquivos.md` (§9). Gate: 2060 passaram, 2 pulados.

## O que mudou para todas

- `tab/` e `tests/` têm uma pasta por trilha. Os nomes antigos de módulo (`tab.maos_braco_ciclo`…) continuam importando e rodando por apelido (`tab/_apelidos.py`); código novo usa o nome novo, absoluto.
- Funções repetidas viraram uma só em `tab/comum/`: `arquivos` (gravar_atomico, ler_json, nfc, slug), `acervo`, `semente` e `violao.AFINACAO_MIDI`. O nome antigo continua no módulo de origem como o mesmo objeto.
- O `ESTADO.md` é índice; o estado de cada trilha está em `docs/estado/<trilha>.md`.
- Saída nova vai em `data/saida/<trilha>/`. As 156 pastas soltas antigas foram para `data/saida/tablatura/` (155) e `data/saida/partitura/part_frentes`, com link no lugar antigo (o gabarito cita 8 delas, então esses links ficam para sempre).
- O AGENTS.md §10 tem o "Padrão de projeto": onde cada coisa mora e 7 regras.

## Sua trilha

- **Módulos movidos:** 45 (`tab/tablatura/{produto,leitura,treino,ataque,ouro,censo}/`); testes: 48 em `tests/tablatura/`.
- **Código que mudou de lugar além da pasta:** `_slug` agora é `tab.comum.arquivos.slug` (reexportado em `produto/video.py`); as 4 funções do acervo estão em `tab.comum.acervo` (reexportadas em `censo/censo.py`); `fixar_semente` está em `tab.comum.semente` (reexportado em `treino/sintetico.py`); `gravar_atomico` em `tab.comum.arquivos`.
- **Dados:** 155 pastas e arquivos soltos foram para `data/saida/tablatura/` (lista em `data/saida/prova_9001/execucao/dados/plano.json`). Os 35 diretórios que eram do root foram corrigidos pelo `chown` do dono.
- **Prova byte a byte:** `comparar.py` deu "IGUAL (19 arquivos)" depois da mudança do código e depois da mudança dos dados.
- **Arquivo frio:** 37 itens, 154.757 arquivos, 2.165 MB em `chorinho_arquivo/tablatura/arquivar-2026-10-22.tar` (tar --compare = 0). Inclui `fase4_13`, `cifra` e `fn05` (fn05/folha_novas.jpg e cifra/vn_suspeitos.jpg ficam no disco).
- **Pesos: decidido, não se movem** (9001 §9). `video.py:823` grava `gerado_por.modelo` com o caminho do peso e `ouro_video.py:1445` grava o do pré-ouro; mover os 145 detectores mudaria esse texto em todo produto novo, sem liberar espaço. Nada a fazer: `artefatos/tablatura/EM_USO.json` lista os que o código usa. Se um dia você quiser que a procedência grave só o nome da pasta, é uma mudança sua, com rodada própria.
- **Atenção:** `tablatura/tab_rotulo/diag/leiame_9001.py`, se rodado de novo, mede o link em vez da pasta (use `du` com barra final e tire `tablatura` da listagem).

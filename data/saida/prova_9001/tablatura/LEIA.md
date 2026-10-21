# Prova de antes: tablatura (decisão 9001)

Referência: `antes/`. Repetição de controle: `antes_repeticao/` (comparada com `antes/`: IGUAL).

## Comandos

Rodar no host (o `prova.sh` roda dentro do container, com `CUDA_VISIBLE_DEVICES=`):

```bash
host-spawn -no-pty -cwd /var/home/gabriel/Projects/chorinho-dataset sh -c 'export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock; docker compose -f compose.yaml -f compose.podman.yaml run --rm --no-deps -e CUDA_VISIBLE_DEVICES= chorinho sh /app/data/saida/prova_9001/tablatura/prova.sh /app/data/saida/prova_9001/tablatura/antes'
```

Dentro do `prova.sh` (cwd `/app`):

- `python -m tab.video "/acervo/pablo romé/greensleeves 💚 guía de estudio 👌 partitura + tab + pdf.mp4" --json <pasta>/produto_greensleeves.json > <pasta>/produto_greensleeves.txt`
- para cada ouro em `data/gold/ouro_video/*.json`, exceto `retrato_brasileiro.json` (v1, substituída pela v2):
  `python -m tab.avaliar_video --ouro data/gold/ouro_video/<slug>.json --pred <pred> --json <pasta>/avaliar_<slug>.json > <pasta>/avaliar_<slug>.txt`
- `<pasta>/ouros_status.txt` registra, por ouro, COM_PRODUTO (com a origem do --pred) ou EXCLUIDO.

## Ouros (8) e origem do --pred

| ouro | --pred |
| --- | --- |
| end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics | `data/saida/fase8/ger/ger/<slug>.json` |
| greensleeves_guia_de_estudio_partitura_tab_pdf | `data/saida/fase8/ger/ger/<slug>.json` |
| gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar | `data/saida/fase8/ger/ger/<slug>.json` |
| south_american_music_easy_guitar_tutorial_with_sheet_and_tab | `data/saida/fase8/ger/ger/<slug>.json` |
| tab_from_this_place_pat_metheny_fingerstyle_guitar_cover | `data/saida/fase8/ger/ger/<slug>.json` |
| tabroom_335_larry_carlton_fingerstyle_guitar | `data/saida/fase8/ger/ger/<slug>.json` |
| la_vie_en_rose_edith_piaf_tab | `data/saida/fase8/rede/<slug>.json` (não existe em ger/ger) |
| retrato_brasileiro_v2 | `data/saida/fase8/rede/<slug>.json` (não existe em ger/ger) |

Fora: `retrato_brasileiro` (v1, substituída pela `retrato_brasileiro_v2`).

## Como repetir depois da mudança

```bash
host-spawn ... sh /app/data/saida/prova_9001/tablatura/prova.sh /app/data/saida/prova_9001/tablatura/depois
python3 data/saida/prova_9001/tablatura/comparar.py data/saida/prova_9001/tablatura/antes data/saida/prova_9001/tablatura/depois
```

## O que o comparar faz

- Nos `produto_*.json`, ignora `gerado_por.em` (data e hora) e `gerado_por.commit` (hash do commit), que mudam por construção. O resto do JSON é comparado depois de re-serializar igual nos dois lados.
- Nos `.txt`, troca o caminho da pasta de saída de cada lado pelo marcador `<PASTA>`. Só esse prefixo: o resto da linha continua byte a byte. Os caminhos trocados são o absoluto no host e o `/app/...` do container.
- O resto (`avaliar_*.json`) é comparado byte a byte.
- Para `.txt` diferente, imprime as linhas que mudam.

## Por que o caminho é trocado

O programa imprime o caminho que recebe (`relatório salvo em …`, `… -> …/produto_greensleeves.json`). Com a pasta de saída em `antes/` e `antes_repeticao/` (ou `depois/`), essa linha muda por construção. Depois da reestruturação a pasta pode estar atrás de um link, e o caminho impresso muda também por isso. Trocar só o prefixo mantém a comparação honesta: qualquer outra diferença na linha ainda aparece.

## Tempos (host, incluindo a subida do container)

- execução 1 (`antes/`): 238 s
- execução 2 (`antes_repeticao/`): 255 s

## Resultado da repetição

`comparar.py antes antes_repeticao`: IGUAL (19 arquivos comparados), exit 0.

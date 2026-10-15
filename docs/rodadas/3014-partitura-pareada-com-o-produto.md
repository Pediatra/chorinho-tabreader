# 3014 — Partitura pareada com o produto, em todas as telas

**Data:** 2026-10-15 · **Trilha:** partitura (P3) · **Código:** `tab/partitura_video.py`
(subcomandos `recortar`, `ler`, `parear`), `tests/test_partitura_video.py`

Passos 1 e 2 da decisão 3002.

## O que mudou

1. **Pareia com o produto, não com o gabarito.** As colunas da tab vêm de `notas[].coluna`
   do `chorinho/video@1` (`data/saida/fase8/rede/<stem>.json`). Uma coluna tocada em duas
   passagens vira um evento só e guarda as duas notas.
2. **Todas as telas do vídeo.** Antes eram só os 21 recortes da P1. Agora cada tela
   paginada do produto vira um recorte:
   - a pauta é a de baixo, acima da base do painel menos 5 passos;
   - o painel só escolhe a pauta e não limita o recorte, para não perder as linhas
     suplementares de baixo.

Saída em `data/saida/partitura/video/<stem>/`: `recortes/`, `omr/` e
`<stem>.partitura.json` (`chorinho/partitura@1`, formato da decisão 3002, sem `fifths` e
sem `compassos` por enquanto). O tempo não é copiado: a chave é `(tela, coluna)`.

```bash
python -m tab.partitura_video recortar --produto data/saida/fase8/rede/<stem>.json
python -m tab.partitura_video ler --produto ...       # imagem chorinho-partitura:dev, CPU
python -m tab.partitura_video parear --produto ...
```

## Medição

Os 3 vídeos com pauta e tab no produto: greensleeves, south american e gymnopédie.

- **Recortes:** 19 de 19 telas com pauta (4 + 3 + 12). As caixas são iguais às da P1 nas
  12 telas em comum (ex.: Gym T01 = R08, `[0, 551, 1920, 883]`).
- **Leitura:** Audiveris 19/19, homr 19/19. Armadura herdada em 2 (south american).

Notas certas contra a tab do **gabarito** (`contar` exato; a referência agrupa por x):

| conjunto | referência | certas | altura errada | faltando | inventada |
| --- | ---: | ---: | ---: | ---: | ---: |
| 12 telas da P1, pareada com o gabarito (3013) | 546 | 526 | 6 | 14 | 3 |
| as mesmas 12, pareada com o **produto** | 546 | **527** | 6 | 13 | 3 |
| 7 telas novas do gymnopédie (2, 4, 6, 8, 10, 11, 12) | 221 | **196** | 7 | 18 | 4 |
| a tab do produto sozinha, 19 telas | 767 | 719 | 25 | 23 | 17 |

Total da partitura nas 19 telas: **723/767**.

Pareamento (`parear.txt`):

| vídeo | eventos | com par | x conferido |
| --- | ---: | ---: | ---: |
| greensleeves | 72 | 72 | 72 |
| south american | 184 | 184 | 183 |
| gymnopédie | 186 | 182 | 168 |

## O que os números dizem

- Trocar o gabarito pelo produto **não piorou**. A única diferença é o R06 (south american
  tela 2): 87 → 88. Aí o `completar_com_homr` usou as colunas do produto em vez do
  agrupamento por x. A causa exata não foi isolada.
- Gym **tela 10**: x conferido 0 de 14. O erro é da tab do produto. As cordas estão
  deslocadas de uma (corda 5 onde o gabarito tem 6), e a tab do produto acerta 10 de 39.
  - Mesmo assim, a partitura acerta 29 de 39 nessa tela.
  - Mas o par pela altura casa colunas erradas, e `confere_x` denuncia: 0 de 14.
  - Avisar a trilha tablatura. O arquivo dela não foi tocado.
- Gym **tela 12**: o acorde de cima está cortado pela borda do cartão. A tab do produto tem 1
  coluna, e a pauta tem 2 eventos.

## Limites

- O tempo continua dependendo do `t_ini` do produto, hoje nulo nesses vídeos (passo 3 da
  decisão 3002, trilha tablatura).
- Quando a tab do produto erra, o par pela altura pode errar junto, e `completar_com_homr`
  pode trocar ou acrescentar nota pela tab errada: na tela 10, 2 trocas e 2 inventadas.
  `confere_x` marca o caso. Usar o x como reserva fica para outra rodada.

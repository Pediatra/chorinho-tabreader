# artefatos/ — pesos treinados e a procedência deles

Os pesos **não** são versionados (o `.gitignore` ignora `*.pt`). O que é versionado é
esta procedência: com o treino determinístico (ver
[`../docs/decisoes/0001-determinismo-do-treino.md`](../docs/decisoes/0001-determinismo-do-treino.md)),
todo peso daqui é **reproduzível** pelo comando registrado.

| pasta | comando | total no gabarito |
| --- | --- | --- |
| `oficial_1` | `python -m tab.sintetico --n-linhas 320 --epocas 22 --seed 1 --saida artefatos/oficial_1` | 83/96 = **0,865** |
| `oficial_2` | idem, `--seed 2 --saida artefatos/oficial_2` | 88/96 = **0,917** |
| `oficial_3` | idem, `--seed 3 --saida artefatos/oficial_3` | 85/96 = **0,885** |
| `det_C` | idem, `--seed 2 --saida artefatos/det_C` | experimento de determinismo (ver abaixo) |
| `casas24_1` | `python -m tab.sintetico --n-linhas 320 --epocas 22 --seed 1 --casas todas --saida artefatos/casas24_1` (lista 0–24; GPU) | 70/72 = **0,972** (régua 72 glifos; não adotado, ver ESTADO) |
| `casas24_2` | idem, `--seed 2 --saida artefatos/casas24_2` | 69/72 = **0,958** |
| `casas24_3` | idem, `--seed 3 --saida artefatos/casas24_3` | 70/72 = **0,972** |
| `detector_tab_final_s1` | `python /app/data/saida/n4/treinar_ft.py --dobra 0 --passos 3000 --semente 1 --nome _s1` (ajuste fino de `detector_tab_v3_s1` com os 8 ouros de vídeo + sintético; o script ainda não está no git) | leitor `rede` do produto até 2026-10-15 (decisão 0010); régua: validação cruzada por vídeo 0,974/0,949/0,987 |
| `detector_tab_final_s1_ger` | `python /app/data/saida/n4/treinar_ft.py --dobra 0 --passos 3000 --semente 1 --nome _s1_ger` (idem, com o gerador de pausa entre cordas e cinza, commit `6cd60d78`, e o cache refeito com os ouros corrigidos em 2026-10-15) | **leitor `rede` do produto desde 2026-10-15**; T8.2 (35 telas fora do ouro): casa 0,996, precisão 0,994, revocação 0,990 |
| `detector_tab_final_s2`, `_s3` | idem, `--semente 2 --nome _s2` / `--semente 3 --nome _s3` | sementes de controle (perda final 0,0541 / 0,0543) |

`casas24_*` foram treinados com **`--casas todas`** (lista 0–24). O comando acima antes saiu sem essa flag:
até f76e73ca a lista 0–24 era o padrão do gerador, e a flag não existia. Desde a restauração, sem `--casas`
o gerador usa a lista **oficial** (0–10,12,14,15,17,19,21,24), e só `--casas todas` reproduz os `casas24_*`.
`casas24_*` **não são o modelo oficial**: o `MODELO_PADRAO` continua `oficial_3`. Medidos no ouro de vídeo v2 (493 notas,
`comparar_paginas.py`): casas certas 473/473/480 contra 470/478/484 dos `oficial_*`; inventadas 24/31/24 contra 20/26/19.

Reprodutibilidade da lista oficial (2026-10-10): `montar(320, seed=1)` com o padrão dá 6.663 glifos e 20 classes
(igual ao registrado antes de f76e73ca); `--casas todas` dá 6.948 glifos e 27 classes.

**Número oficial: média das 3 sementes = **0,949** (66/72, 71/72, 68/72, em **72 glifos / 3 canais** — o `raman korshun` saiu em 2026-10-09, guitarra elétrica, e o denominador caiu de 96 glifos / 4 canais; **não é ganho**)** (amplitude 0,052). Cada semente dá o
mesmo total em execuções repetidas — medido 2× cada.

`det_C` é a **prova do determinismo**: `det_C` e `det_D` saíram idênticos (mesma perda por
época até a 4ª casa). `det_D` foi apagado por ser duplicata bit a bit. O `0,896` que o
treino imprimiu nessa época era o número **deprimido pelo `Dropout`** (modelo em modo
`train()` ao aferir); o valor correto desses pesos, em `eval()`, é outro — use
`tab.avaliar` para obtê-lo.

Para reconferir qualquer peso:

```bash
docker compose run --rm chorinho python -m tab.avaliar \
    --modelo artefatos/oficial_2/glifo_sint.pt
```

**Armadilha:** o container roda como `root`, então estes arquivos pertencem a root no
host e o seu usuário não consegue apagá-los direto. Apague por dentro:

```bash
docker compose run --rm chorinho rm -rf artefatos/<pasta>
```

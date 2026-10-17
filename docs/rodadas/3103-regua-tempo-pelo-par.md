# 3103 — F0.3: quantas notas da partitura ganham tempo pelo par

Frente 0 (régua por compasso, troca do homr e tempo pelo par), item F0.3 de
`docs/pesquisa/partitura-frentes.md`, seção 7. Briefing da onda 1
(`docs/pesquisa/partitura-onda1-briefings.md`).

**Medida, sem limiar.** Só lê o que está gravado. Não lê vídeo e não mexe no produto.
Feita na cópia isolada `chorinho-partitura-env/repo` (ambiente próprio, fora da main).
Módulo: `tab/partitura_regua_tempo.py`. Saída: `data/saida/part_frentes/f0_regua/tempo.json`.

## Definições (escritas antes de medir)

- **Evento**: cada item de `pautas[*].eventos` nos 3 `<stem>.partitura.json`.
- **Evento sem par**: evento sem o campo `par`.
- **Par**: `par` = `{tela, coluna, metodo}`. Pares com `metodo == "x"` ficam à parte.
- **Par sem nota**: a coluna pareada não tem nenhuma nota no produto (`fase8/rede`, mesma
  `tela` e `coluna`).
- **Par (evento, exibição)**: para cada exibição (`exibicao`) das notas da coluna pareada.
  Conta com tempo se a nota dessa exibição tem `t_ini`; senão, par sem `t_ini`.
- **Evento com segundo**: evento com pelo menos um par com tempo, em alguma exibição.
- **Inversão**: dentro de cada `(tela, exibicao)`, eventos ordenados por `(compasso, t)`;
  há inversão quando o `t_ini` do evento é menor que o do anterior. Acorde (mesma `coluna`
  do anterior) não conta.
- O `t` do evento é tempo **musical**; o `t_ini` é segundo do vídeo. Não se misturam.
- O tempo da tab **não foi validado**: a F0.3 mede cobertura e ordem, não acerto.

## Resultado por vídeo

| vídeo | eventos | sem par | par sem nota | pares (evento, exibição) | com tempo | sem t_ini | eventos com segundo | inversões |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| greensleeves | 72 | 0 | 0 | 143 | 142 | 1 | 71/72 | 0 |
| south american | 184 | 0 | 0 | 184 | 146 | 38 | 146/184 | 4 |
| gymnopédie | 182 | 4 | 0 | 182 | 0 | 182 | 0/182 | 0 |
| **total** | **438** | **4** | **0** | **509** | **288** | **221** | **217/438** | **4** |

- Por método: 428 eventos com par `altura` e 10 com `x` (todos na Gymnopédie, sem tempo).
  O `x` de reserva não entrou no tempo.
- A Gymnopédie tem 0 `t_ini` na tab do produto (já sabido, rodada 3014): nenhum evento dela
  ganha tempo. Os 4 sem par também são dela.
- Duas execuções do módulo final dão o mesmo `tempo.json` (`cmp`). Lint: `ruff check` e
  `ruff format --check` passam.

## Inversões olhadas (4, todas em South American)

Conferido pelo x da partitura (`x_quadro`), pelo x do tab (`x_centro_quadro`) e pelas alturas
do par. Não foi olhado o recorte em imagem: a conferência é pelos números dos JSON.

1. **T01, exibição 0, compasso 1.** Evento `t=0.75` (col. 3, x 186,2) vem antes de `t=1.0`
   (col. 2, x 166,0). O tab põe col. 2 (76,56 s) antes de col. 3 (77,01 s), em ordem de x.
   **Erro do `t` musical da partitura** (ordem dentro do compasso). O par está certo: alturas
   G5 e E5 batem com as cordas do tab, distância de x 2,2 e 0,0. Nessa mesma compasso, col. 5
   (x 188,0) está pareada com distância 47,7 e `confere_x` falso: **par ruim à parte**, não
   explica a inversão.
2. **T02, exibição 0, compasso 3.** O evento `t=1.0` (col. 22, x 649,7, B3) está no compasso 3,
   mas o x dele é muito à direita dos outros compassos 3 (x 361 a 471). **Erro de compasso da
   partitura**: o tab (131,2 s) segue o x. O par tem distância 0.
3. **T03, exibição 0, compassos 8 e 9.** O evento `t=1.5` do compasso 8 (col. 47, x 1387,7)
   está muito à direita do compasso 8 (x 999 a 1095); o tab põe col. 47 em 170,1 s, no compasso
   11. E o evento do compasso 9 `t=0.0` (col. 38, x 1137,5) é do compasso 10 no tab (163,9 s).
   **Erro de compasso da partitura**. O tab está em ordem de x.
4. **T03, exibição 0, compasso 12.** O evento `t=0.0` do compasso 12 (col. 60, x 1882,7) está
   muito à direita do compasso 12 (x 1625 a 1743); o `t=0.5` (col. 54, 175,4 s) é do tab,
   mais adiante. **Erro de compasso da partitura**. O tab está em ordem de x.

**Veredito: nenhuma das 4 inversões é erro do tempo da tab.** Três são de compasso atribuído
errado a um evento com x de outro compasso; uma é de `t` musical fora da ordem do x.
Em todas, o tempo do tab segue o x. Erro de par: não explica nenhuma; o par ruim da
inversão 1 (col. 5, distância 47,7) é um caso à parte.

## Pendências

- Não há commit: o ambiente não tem git. Os arquivos ficam na cópia isolada.
- Os 438 eventos com par são o denominador. A conta é de cobertura e ordem, não de acerto.

## Revisão da sessão principal (2026-10-17)

Rodado de novo no container, na `main`: a saída deu igual byte a byte à da cópia (`cmp`).

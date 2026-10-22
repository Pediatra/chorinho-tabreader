# 0214 — R4h: as ligaduras que escaparam na T8.4

Segue a [0211](0211-recorte-alto.md). Escrito **antes** de treinar e de medir (2026-10-22).

## Por que

- O `_atqa` reprovou na T8.4 com "sim" falso de 33/266 (12,4 %). Recontado com a regra da
  ligadura do dono, dá 21/254 (8,3 %), ainda acima dos 5 %.
- Com a correção do dono, os 7 erros por semente que sobram são todos ligadura de
  prolongamento que o gerador não desenha:
  - o destino entre parênteses, `4 ⌒ (4)`. O gerador só tinha o `(n)` como nota opcional
    **atacada** (G7, 0203), e por isso ensinava o contrário;
  - o harmônico ligado, `<12> ⌒ <12>`. O gerador não ligava harmônicos;
  - o arco embaixo da corda (mr. tabs). O gerador já tem o G1 (`P_ARCO_ABAIXO` 0,4), mas
    nunca com o destino entre parênteses.
- **Regra do dono** (2026-10-22): "quando não há segundo número em uma ligadura é a mesma
  coisa que quando tem dois números considere o primeiro como atacado". O gerador não
  tinha arco sem segundo número.

## A pergunta

Com o gerador cobrindo essas ligaduras e com as telas reais da T8.3 e da T8.4 no treino, o
rótulo de ataque passa na prova lacrada T8.5?

## A mudança (só esta)

**Gerador** (`tab/tablatura/treino/sintetico_sistema.py`):

| | o que é | chance |
| --- | --- | --- |
| `P_TIE` | ligadura de prolongamento por coluna | 0,05 → **0,08** |
| G13, `P_TIE_PARENTESES` | o destino da ligadura entre parênteses, `n ⌒ (n)`; o destino é "lig", sem ataque | 0,4 das ligaduras |
| G14, `P_TIE_HARM` | ligadura de harmônicos, `<n> ⌒ <n>`; a origem é "harm" (atacada) e o destino é "lig" | 0,2 das ligaduras |
| G15, `P_ARCO_SOLTO` | arco solto, sem segundo número, numa nota sem técnica; a nota continua atacada. Sai para a direita (0,7) ou chega pela esquerda. Só é desenhado sobre corda vazia | 0,03 por nota |

- O estilo dos arcos é o de sempre (`_pontos_arco`): acima ou abaixo da corda, na borda ou no
  centro, às vezes alto.
- **A amostra, medida antes de treinar** (`data/saida/tablatura/tab_rotulo/r4h/amostra.py`,
  2000 sistemas das sementes de treino):

  | sistemas com | quantos |
  | --- | --- |
  | ligadura | 616 |
  | destino entre parênteses (G13) | 291 |
  | ligadura de harmônicos (G14) | 126 |
  | arco solto (G15) | 274 |

  - São 713 notas "lig" em 2000 sistemas.
  - Olhei os exemplos em `r4h/exemplos/`: o `(10)` ligado, o `<0> ⌒ <0>` e o arco solto
    saem como nos vídeos.

**Telas reais no treino** (`data/saida/tablatura/n4/treinar_ft.py`):

- `--t83-toda`: as 33 telas da T8.3, as duas metades. A T8.3 foi usada na 0210 e não serve
  mais de teste.
- `--t84`: as 29 telas da T8.4, que está gasta. O cache sai de `n4/extrair_t84.py`, já no
  recorte alto. As casas vêm do ouro servido no passe do modo ataque, e o ataque vem do
  `ataque_t84.json`, com as correções do dono.
  - As cordas do painel batem com as da ferramenta nas 29 telas: são 1264 notas com casa
    numérica.
- Com isso, a dobra 0 treina com 159 telas reais, contra 97 no `_atqa`
  (`r4h/conferir_telas.py`).

**O treino:** igual ao do `_atqa`, `--passos 3000 --ataque --t82 --recorte-alto`, mais
`--t83-toda --t84`. São as 5 dobras × 3 sementes, com o nome `_atqb_s<semente>`, no roteiro
`r4h/rodar.sh`. A leitura comum (`DETECTOR_PADRAO`) não muda.

## A prova lacrada: T8.5

- **Sorteio:** `data/saida/tablatura/t85/gerar.py`, com `random.Random(3)`.
  - Ficam fora os vídeos do ouro, da T8.2, da T8.3 e da T8.4.
  - São 2 vídeos por canal, em 15 canais, num total de 30 telas.
- **Telas que saíram, antes de qualquer medida** (dono, 2026-10-22):
  - a **5**: o painel pegou a pauta como se fosse tablatura;
  - a **27**: o recorte cortou a corda 6 e deslocou as cordas de uma.
- **Gabarito:** `r2/conferir_t85/ataque_t85.json`, com **28 telas e 1366 notas**: 1320
  atacadas e 46 não atacadas. O dono conferiu as casas e o ataque sem ver nenhuma leitura de
  modelo de ataque. **Nenhum modelo foi medido na T8.5.**

## A medida e o critério

**1. Nos ouros** (`r4h/decidir.py`, sem ler a T8.5):

- O `ataque_r4 medir --versao atqb` usa as dobras fora e as 3 sementes.
- O limiar da técnica e o `L` saem dos ouros, como sempre (`escolher_limiar` e
  `escolher_nao_sei`).
- O `_atqb` **passa nos ouros** se:
  - o custo fica ≤ 10 % em cada semente;
  - a casa fica ≥ 2660 em cada semente (a mesma régua da 0211);
  - o "sim" falso somado nas 3 sementes não passa o do `_atqa` (6/255) **mais 3**. Isso é o
    ruído entre sementes: o treino novo não pode piorar os ouros.
- **Se não passar:** a T8.5 **não se gasta**, os ouros viram o diagnóstico e nada muda no
  produto.

**2. Na T8.5, uma vez só** (`r4h/medir_t85.py atqb`, dobra 0, 3 sementes, recorte alto, `L`
dos ouros):

- **"Sim" falso:** `nao|sim` / (`nao|sim` + `nao|nao`), com a regra do slide sem origem.
  Nota não lida fica fora do denominador.
- **Custo:** `sim|nao` / (`sim|nao` + `sim|sim`).
- **Aceite (o do plano):** com as 3 sementes somadas, "sim" falso ≤ 5 % e custo ≤ 10 %.
- **Se passar:**
  - o `ataque_rotulo.DETECTOR_CALIBRADO` passa a `_atqb_s1`, com os limiares dos ouros;
  - a etapa do rótulo de ataque fecha.
- **Se reprovar:**
  - a T8.5 fica gasta;
  - os erros viram o diagnóstico seguinte;
  - o `DETECTOR_CALIBRADO` não muda.
- **Depois**, e só para informar, o `_atqa` é medido na T8.5 do mesmo jeito
  (`medir_t85.py atqa`). Ele diz quanto do resultado veio desta rodada e não decide nada.
- **Em nenhum caso** o `DETECTOR_PADRAO` muda sem o OK do dono.

## O que fica de fora

- O X sem número ainda não é nota no arquivo de ataque. Isso é dívida.
- As duas mudanças, o gerador e as telas reais, entram juntas. O resultado não separa o
  efeito de cada uma.

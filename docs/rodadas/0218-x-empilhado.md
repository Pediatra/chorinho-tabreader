# 0218 — O X empilhado: o gerador e os X do dono no treino

**Data**: 2026-10-24. **Trilha**: tablatura. **Estado**: pré-registro (nada medido).

## A pergunta

O detector passa a ler o **X empilhado** (várias cordas abafadas na mesma coluna) sem piorar a
casa nem o rótulo de ataque?

## O que já se sabe

- **O estudo `gap_x`** (`docs/pesquisa/tablatura-gap-x-abafado.md`,
  `data/saida/tablatura/gap_x/`): das 486 cordas cobertas pelas regiões de X do dono, o
  produto leu X em **0**. O X sozinho sai: **28 de 28**.
- **Duas causas prováveis:**
  - o gerador sorteia o X nota a nota (`P_MUDO = 0,05`), então a coluna de X quase não nasce;
  - no ajuste fino do `_atqs` (sem `--ignorar-x`), o gabarito não tinha nota X dentro das
    regiões de X do dono, e o X empilhado real foi treinado como **fundo**.
- **A revisão do dono** (2026-10-24, `data/saida/tablatura/correcoes/`, commits a770472a e
  0d1f3d9e) pôs nota X nas regiões. Nas telas conferidas há:

  | lote | X |
  | --- | --- |
  | EOB | 96 |
  | Room 335 | 34 |
  | T8.2 | 22 |
  | T8.3 | 16 |
  | T8.4 | 55 |
  | T8.5 | 77 |
  | T8.6 | 35 |

- **A revisão foi só do X.** As 48 telas que ganharam "conferida" nela voltaram a não
  conferidas (`revisao_so_x.json`) e **não entram** nem no treino nem na medida.

## As mudanças

1. **Gerador G17** (`tab/tablatura/treino/sintetico_sistema.py`): uma coluna pode virar uma
   **coluna de X**. Com probabilidade `P_COLUNA_X = 0,06` por coluna, 2 a 6 cordas
   vizinhas recebem X. Os pesos dão mais chance a 3–6, o rasgueado.
   - A amostra do gerador é medida antes de treinar (AGENTS §7, regra 2): quantas colunas de X
     nascem em 2.000 sistemas.
   - Um mosaico de exemplos fica em `tab_rotulo/r6/`.
2. **Os X do dono no ajuste fino** (`n4/treinar_ft.py --x-dono`):
   - as notas X das telas conferidas (casa `x`, e também `xs`) entram como alvo da casa,
     lidas de `correcoes/x_dono.json`;
   - a nota do cache que o dono trocou de número para X troca de rótulo;
   - o X **não** ganha rótulo de ataque inferido: fica sem alvo de ataque, como nota sem
     gabarito de ataque (AGENTS §8: o agente não converte rótulo).
3. **A receita é a do `_atqs`**: `--passos 3000 --ataque --t82 --recorte-alto --t83-toda --t84
   --t85`, mais G17 e `--x-dono`. São 5 dobras e 3 sementes, `_atqx`.

## A escolha (nos ouros, validação cruzada por vídeo)

Para cada semente, o `_atqx` contra o `_atqs`:

- **X nos ouros**: as notas X do dono no EOB e no Room 335, lidas pela dobra 4, que deixa
  esses dois vídeos fora do treino. Lido = nota com casa `x` na mesma corda, a até 0,5 passo.
- **Casa e ataque**: a regra de decisão da 0215 (`r5/decidir.py`), agora com o `_atqs` no
  lugar do `_atqr`:
  - o custo fica ≤ 10 % em todas as sementes;
  - a pior semente de casa não fica mais de 2 abaixo da pior do `_atqs`;
  - o "sim" falso somado não passa o do `_atqs` mais 3.

O `_atqx` segue para a prova se, nas 3 sementes, **X lido ≥ 50 %** e a casa e o ataque
ficarem dentro dos tetos. Se não seguir, não há prova: o resultado vai para "não repetir".

## A prova (T8.6)

- **O que se mede**: as 28 telas conferidas da T8.6 e os seus 35 X.
- **Por que serve de prova**: a T8.6 nunca entrou em treino. Ela já foi gasta como prova do
  rótulo de ataque (0215), mas os X dela foram marcados depois disso e nunca escolheram nada.
- **Uma medida só**, com a semente 1, liberada por `r6/t86_x_liberada.json` depois da escolha:
  1. **X lido ≥ 50 %** dos 35;
  2. **X falso** (X lido onde o dono tem um número) ≤ **1 %** das notas numéricas;
  3. casa nas notas numéricas ≥ a do `_atqs` − 0,3 ponto;
  4. ataque dentro dos tetos da 0215 ("sim" falso ≤ 5 %, custo ≤ 10 %).
- **Os quatro passam** → `DETECTOR_CALIBRADO` passa a `detector_tab_final_atqx_s1`. O
  `DETECTOR_PADRAO` não muda sem o dono.
- **Algum reprova** → fica o `_atqs`, e o motivo vai para "não repetir".
- O "antes" para comparar: o `_atqs` leu 0 dos X empilhados da T8.6 (`gap_x`: 0 de 53 cordas).

## Resultado

(a preencher)

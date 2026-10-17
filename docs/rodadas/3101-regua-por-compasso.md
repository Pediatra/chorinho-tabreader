# 3101 — F0.1: em que compasso está o erro, e o Audiveris avisa?

Frente 0 (régua por compasso, troca do homr e tempo pelo par), item F0.1 de
`docs/pesquisa/partitura-frentes.md`, seção 7. Briefing da onda 1
(`docs/pesquisa/partitura-onda1-briefings.md`).

**Medida, sem limiar de aceitação.** Só lê o que está gravado. Feita na cópia isolada
`chorinho-partitura-env/repo` (ambiente próprio, fora da main). Módulo:
`tab/partitura_regua.py`. Saída: `data/saida/part_frentes/f0_regua/regua_compassos.json`.

Ordem real: o módulo foi escrito e rodado antes deste documento. As definições abaixo são
as que estão no código. Uma correção foi feita depois da primeira execução (ver "Correção").

## Definições (no código)

- **Conjuntos**: R01–R21 do `leitura_p1.json` e os 3 do `leitura_sem_produto.json`. A
  leitura é a do campo `fonte` (`audiveris/x2_margem` em R01–R20; `homr/nativo` em R21;
  `audiveris/x2_margem_herdada` nos 3 sem produto). O `.omr` é o `x2_margem/<id>/entrada.omr`.
- **Fora da tabela**: R20 (só precisão, sem a segunda metade dos faltando, rodada 3005);
  R21 (homr, sem `.omr`: à parte); R07 e R17 (número de `stack` do `.omr` diferente do número de
  compassos da leitura, 14 contra 13 e 9 contra 8: a posição do compasso fica incerta).
- **Compasso**: a posição `k` na leitura. O símbolo entra pelo `compasso` do palpite; o clique
  de faltando entra no último `stack` com `left / 2 ≤ x + 5` (o `.omr` é 2× a imagem;
  conferido: `max(right)/2` ≈ `largura_png` nos recortes).
- **Compasso com erro**: tem símbolo que não é `certo` (dono), ou clique de faltando dentro dele.
- **Marcas do Audiveris** (por compasso):
  - `abnormal`: o `measure` de mesmo índice tem `abnormal="true"`;
  - duração do compasso: a maior soma de `duracao` por voz, sem contar acorde duas vezes
    (inclui pausas);
  - **fonte A**: a fração `expected` do `stack` do `.omr` (déficit, excesso, ou sem duração
    esperada);
  - **fonte B**: a fórmula da própria leitura (`compasso_formula`), também como déficit e
    excesso.
- **Alarme falso** de uma marca: compasso que a marca acusa e que não tem erro.

## Conferência (CA1)

`lidos 1051` (873 + 178), `certos 1028` (852 + 176), `faltando 118` (78 + 40). Bate com o CA1.

## Cliques de faltando

- 118 cliques no total. 104 caem em compasso da tabela. 0 deles fica fora de todo compasso (0 %;
  o critério é 10 %).
- 10 cliques (R07: 8; R17: 2) estão fora da tabela pela contagem de `stack` diferente, e 4
  (R21) são do homr. Nenhum deles foi medido por compasso.

## Tabela compasso × marca (139 compassos; 52 com erro)

Os 52 com erro são 49 com clique e 3 só com símbolo não certo.

| marca | acusa | com erro | alarmes falsos |
| --- | ---: | ---: | ---: |
| `abnormal` | 12 | 12 | 0 |
| déficit (fonte A) | 6 | 4 | 2 |
| excesso (fonte A) | 5 | 5 | 0 |
| sem duração esperada (A) | 69 | 25 | 44 |
| déficit (fonte B) | 6 | 4 | 2 |
| excesso (fonte B) | 5 | 5 | 0 |

- **Sem duração esperada** não é marca de erro: é falta de informação. Dos 49 compassos com
  clique, 24 não têm duração esperada. Os 44 "alarmes" dessa linha não contam como falsos.
- **Fonte B é a mesma informação que a A** nesta amostra: concordam em 70 de 70 compassos com
  as duas, e somem nos mesmos 69. A fórmula herdada do vídeo (`fracao` do `.partitura.json`,
  rodada 3015) não está ligada aos recortes R01–R21 nesta rodada. Por isso B não é uma segunda
  prova independente. Fica como limite.
- **Alarmes falsos de déficit** (fonte A): R01 compasso 0 (anacruse: `special=PICKUP`, soma 1 de 3)
  e R19 compasso 4 (soma 1,5 de 4, sem clique nem símbolo errado). A causa de R19 não foi olhada.

## Cobertura (quantos compassos com nota faltando as marcas pegam)

Nos 49 compassos com clique:

- `abnormal` pega 11;
- déficit (A) pega 3 dos 25 que têm duração esperada;
- excesso (A) pega 5;
- alguma das três pega **14 de 49 (29 %)** (com a tolerância corrigida; antes da correção dava 15).

Ou seja: o Audiveris, pelas marcas que este módulo lê, avisa em menos de um terço dos
compassos com nota faltando. Isso é o número de referência da B1 e da B2.

## Não medido

- **`grade` < 0,5**: o `.omr` tem `grade` por glifo, mas não tem o compasso de cada glifo sem o
  x dele. Não entrou na tabela. Fica para a próxima rodada.
- **Duas execuções**: dão o mesmo `regua_compassos.json` (`cmp`).

## Correção (registro)

A primeira execução usava tolerância de 1e-9 na soma das durações. Um compasso (R18, compasso 3)
saiu como excesso por ruído de ponto flutuante: soma 3,000001 contra 3. A tolerância passou a
1e-6. Com isso, o excesso (fonte A) foi de 6 para 5 compassos, e os 5 têm erro. Nenhuma outra
marca mudou.

## Casos olhados

**Casos olhados (crops em `data/saida/part_frentes/f0_regua/casos/`):** Os casos por marca são estes (recorte e
posição `k` do compasso). Imagem de cada recorte: `data/saida/partitura/p1/omr/audiveris/x2_margem/<id>/entrada.png`
para os R; para os sem produto, o `entrada.png` dentro de `data/saida/partitura/sem_produto/<vídeo>/omr/audiveris/x2_margem/<P01a|P06a>/`.

- `abnormal`: R05 k0, R08 k0, R08 k4, R08 k6, R13 k2.
- déficit A: R01 k0 (alarme falso, anacruse), R13 k0, R13 k1, R16 k0, R16 k2.
- excesso A (5 casos, todos com erro): R13 k2, R18 k2, `agua_de_beber_a` k0, `athletic_theme` k0 e k1.
- sem duração esperada: R02 k0–k4 (linha de informação, não de erro).

Veredito de cada caso olhado:

- **Déficit, R01 k0 (anacruse): alarme falso confirmado.** A imagem mostra 3/4 com uma semínima
  só, antes da primeira barra. A anacruse é real, não é erro. A marca não separa anacruse de
  compasso incompleto.
- **Déficit, R19 k4: alarme falso por corte do recorte.** O stack vai de 3526 a 3839 px, e a
  imagem tem 3840 px de largura: o compasso 5 continua além da borda direita. A leitura está
  cortada pelo recorte, não é erro de leitura. Excluir o último compasso quando ele toca a
  borda seria uma regra nova: não entrou nesta tabela, fica para a próxima rodada.
- **Abnormal, R08 k0: erro real, marca certa.** O compasso tem um acorde de três notas (C#5,
  E5, G#5, da tab) que o Audiveris não leu; o homr leu.
- **Abnormal, R05 k0: erro real, marca certa.** Há um marcador azul do vídeo sobre a primeira
  nota, e o Audiveris perdeu essa nota.
- **Excesso, R13 k2 (soma 4,5 contra 4): explicado, e é artefato do `.omr`.** O `stack` de
  R13 k2 tem `expected="1"` (semibreve, 4 semínimas), mas o atributo `duration` e a fórmula
  do compasso são 9/8 (4,5 semínimas). A leitura está certa; a fonte A é que está errada.

**Não olhados:** déficit R13 k0 e k1, R16 k0 e k2; excesso R18 k2 e os sem produto; `sem_A` não é
marca de erro. Por isso o CA7 (5 casos por marca) não está fechado: são 2 de 5 em déficit,
2 de 5 em abnormal e 1 de 5 em excesso.


## Revisão (2026-10-17): o `expected="1"` do Audiveris é padrão, não duração

O atributo `expected="1"` (semibreve, 4 semínimas) aparece quando o Audiveris não sabe a
fórmula do compasso. Em 9 de 60 stacks, o `expected` diverge do `duration`. Isso contamina a
fonte A da tabela congelada: os déficits e excessos de R13 k0–k2, R16 k1 e k3, R19 k4 e os
sem produto em k0–k1 vêm desse padrão.

Efeito nas marcas de duração (fonte A), com e sem `expected="1"`:

| marca | congelada: acusa / com erro / falsos | sem `expected="1"`: acusa / com erro / falsos |
| --- | ---: | ---: |
| déficit (A) | 6 / 4 / 2 | 1 / 0 / 1 |
| excesso (A) | 5 / 5 / 0 | 1 / 1 / 0 |

Cobertura nos 49 compassos com nota faltando: a congelada pega **14**; sem o padrão pega **11**
(só o `abnormal`). Ou seja, as marcas de duração quase não acrescentam nada, e o número
honesto de cobertura do Audiveris, por estas marcas, é entre 11 e 14 de 49 (22 a 29 %).

Esta revisão não troca a tabela acima: ela é o registro do que a fonte A faz. A variante sem o
padrão é a recomendada para a B1 e a B2, mas precisa ser decidida pelo dono, porque muda a
regra que estava congelada.

O R01 k0 (anacruse) não é padrão: `expected="3/4"` e `duration="1/4"`, então é um alarme
verdadeiro da anacruse, como já estava registrado.

## Revisão da sessão principal (2026-10-17)

Rodado de novo no container, na `main`: a saída deu igual byte a byte à da cópia (`cmp`).

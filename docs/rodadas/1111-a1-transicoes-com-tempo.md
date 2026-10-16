# 1111: A1, transições com tempo (Hori e Sagayama) sobre o D1 do M8

**Frente**: A1 de [`docs/pesquisa/maos-frentes.md`](../pesquisa/maos-frentes.md) (seção 7, onda 2).
**Briefing**: [`docs/pesquisa/maos-onda2-briefings.md`](../pesquisa/maos-onda2-briefings.md),
bloco "Briefing — A1/A2".
**Código**: `tab/maos_decod_transicoes.py` (a escrever depois deste commit, implementando estas
regras). Importa o D1 e o agrupamento do M8 (`tab/maos_corda_sem_direita.py`), sem editar, e os
dados e a medida da A3 (`tab/maos_decod_dados.py`, `tab/maos_decod_medir.py`).
**Saída**: `data/saida/maos/frentes/fa_decodificador/a1_medida.json` (só na pasta da frente).

## Pergunta

Quando há tempo entre dois ataques, saltar a mão custa menos? O δ fixo do D1 trata igual um
salto em 0,1 s e um salto em 2 s. Trocando só esse termo por uma Laplace cuja escala cresce com o
`dt` do **som**, o decodificador acerta mais corda que o D1 nas notas ambíguas, sem olhar o
vídeo de teste?

## Regras e pesos a priori

Escritos **antes** de qualquer medida desta rodada. Nenhum número foi gerado para esta frente
até este commit (a A3 e a sua rodada 1110 são de antes). Se alguma regra mudar depois de ver
número, a frente está invalidada (seção 5.3, CA4).

### 1. Dados

- **Vídeos de teste** (os mesmos da A3): retrato = `mvp`, noturno = `q16_chopin_nocturne20`,
  lacrimosa = `sky_4`, glimpse = `sky_8`. Ataque do M8: notas com o mesmo `t_ini` (tolerância
  de 0,02 s), com os filtros do M8. Notas com corda ou casa fora do domínio saem, como no M8.
- **Ouros do dono**: **fora desta rodada**. Não têm `t_ini`, portanto não têm `dt`.
- **Relatório** (não é critério): `sky_1`, `sky_2`, `sky_3`, `sky_5`, `sky_6`, `sky_7`. Não têm
  alinhado de som. Para eles o `dt` é o do marcador (`t_ini`), e isso é rotulado no resultado.

### 2. `dt` pelo som (regra do briefing, ponto 2)

- Para cada ataque, `t_audio` é o da **primeira nota** do ataque, lido de
  `data/saida/maos/m7/audio/alinhado_<slug>.json` pelo par `(tela, coluna)`, campo `t_audio`
  (`exibicao` é sempre 0 nesses arquivos). Slugs: retrato → `retrato_brasileiro`;
  noturno → `chopin_nocturne20`; lacrimosa → `lacrimosa`; glimpse → `glimpse_of_us`.
- `offset_k = t_audio_k − t_ini_k`.
- `dt_k` (para o par de ataques `k−1`, `k`):
  - se os dois ataques têm `t_audio` **e** os dois offsets estão em [−0,1 s; 1,0 s]:
    `dt_k = t_audio_k − t_audio_{k−1}`;
  - senão: `dt_k = t_ini_k − t_ini_{k−1}`, e o par é contado em **`fallback`**.
- `dt` negativo (ataques trocados pelo som): usa `dt⁺ = max(dt, 0)` e é contado em
  **`negativo`**.
- Relatório: a fração de pares em `fallback` e `negativo` vai no resultado, por vídeo.

### 3. Termo de posição

`−log Laplace(Δposição; b)` com `b(dt) = b₀ + b₁ · dt⁺`. Como `−log Laplace = log(2b) + |Δ|/b`:

- `|Δ|/b` entra quando **as duas** posições do par estão definidas (menor casa presa de cada
  ataque; ataque só de cordas soltas carrega a posição anterior, como no M8). Quando uma não
  está definida, o termo é 0, como no D1;
- `log(2b_k)` depende só do par `k`, não do caminho. Por isso é o mesmo para todo caminho que
  passa por esse par e **não muda a decisão do Viterbi**. Fica **omitido** da soma, e o código
  declara isso no próprio arquivo.

### 4. Termo de corda (só na melodia)

- `log(1 + |Δcorda|)`, que é `−log(1/(1 + |Δcorda|))`, somado entre as **notas mais agudas** de
  ataques consecutivos. A nota mais aguda é a de maior altura da tablatura do ataque (altura do
  gabarito; empate: a primeira na ordem do produto). Entre baixo e melodia não há termo.
- Ligado ou desligado, como fator da grade.

### 5. Pesos fixos e grade

- Fixos do D1: `α = 1`, `γ = 5`. O termo de posição do D1 (`δ = 0,5`) é o que sai.
- **Grade**: `b₀ ∈ {0,5; 1; 2; 4}`, `b₁ ∈ {0; 1; 2; 4}` por segundo, termo de corda
  `{desligado; ligado}`. São 32 configurações.

### 6. Escolha da configuração (CA4)

- **Variante principal, fora da amostra**: para cada vídeo de teste `v`, escolhe-se a
  configuração de **maior saldo** (consertadas − quebradas, nas notas ambíguas, contra o D1)
  somado nos **outros 3** vídeos de teste. Mede-se em `v` com essa configuração. São 4 escolhas;
  a variante principal é o conjunto delas.
- **Desempate**: menor `b₀`; depois menor `b₁`; depois corda desligada.
- **Relatório**: a configuração de maior saldo nos **4** vídeos de teste. Nenhum dos 6 `sky_*`
  do relatório entra nessa escolha. `sky_4` e `sky_8` entram na escolha das dobras dos outros
  vídeos, mas nunca na escolha do próprio teste.
- **Variante fixa** (escolhida nos 4 juntos, medida nos mesmos 4): é **diagnóstico**, nunca
  aprovação.

### 7. Sanidade (parte do CA1; se falhar, pare)

- Com `b₀ = 2`, `b₁ = 0` e corda desligada, o decodificador tem de dar **exatamente** o D1: os
  mesmos índices de combinação em **todos** os ataques dos 4 vídeos de teste.
- CA1 também: D0 e D1 refeitos conferem com `data/saida/maos/m8/corda_sem_direita.json`.

### 8. O que conta como aprovação

- **CA1–CA7** da seção 5.3 de `maos-frentes.md`, contra o D1 (R1), com as 4 escolhas do item 6
  e agregado nas notas **ambíguas** dos 4 vídeos.
- **CA2**: ganho líquido ≥ +1,0 pp e consertadas − quebradas ≥ 20.
- **CA3**: ganho em pelo menos 3 dos 4 vídeos, e nenhum piora mais de 0,5 pp.
- **CA5**: duas execuções dão o mesmo `a1_medida.json` (md5). Sem sorteio.
- **CA6** (10 notas no quadro, 5 consertadas e 5 quebradas, com o caminho do recorte): só se a
  variante for aprovada.
- **CA7**: gate verde na worktree.
- A medida secundária (casa ≤ 7) e a contagem por `(tela, coluna)` distinta entram no resultado,
  com denominador.

### 9. O que não entra

- Nenhuma escolha olhando o relatório. Nenhum ajuste de `b` depois de ver o resultado.
- Ouros do dono: sem `t_ini`, sem `dt`, fora desta rodada.
- Tablatura externa (DadaGP): descartada pelo dono.

## Resultados

**Veredito: REPROVADA** pelo pré-registro. Falha em CA2 e CA3. A medida foi feita uma vez, com
a grade e o LOO das regras acima; a segunda execução só confere o CA5. Números: `data/saida/maos/frentes/fa_decodificador/a1_medida.json`.

### Sanidade e CA1

- **Sanidade (regra 7): passa.** Com `b₀ = 2`, `b₁ = 0` e corda desligada, o caminho é
  exatamente o D1 nos 4 vídeos (também coberto por teste unitário).
- **CA1: passa.** D0 e D1 refeitos batem com `corda_sem_direita.json` nos 4 vídeos. D1: 703
  (retrato), 447 (noturno), 393 (lacrimosa), 609 (glimpse) acertos, como no M8.

### Medida principal (escolha por LOO, notas ambíguas)

| vídeo | escolha (fora do vídeo) | ambíguas | D1 | A1 | consertadas | quebradas | ganho (pp) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| retrato | b₀=1; b₁=0; sem corda | 692 | 0,9277 | 0,9220 | 0 | 4 | −0,58 |
| noturno | b₀=1; b₁=1; sem corda | 540 | 0,7611 | 0,7630 | 1 | 0 | +0,19 |
| lacrimosa | b₀=1; b₁=0; sem corda | 418 | 0,8565 | 0,8541 | 0 | 1 | −0,24 |
| glimpse | b₀=0,5; b₁=0; sem corda | 630 | 0,9270 | 0,9127 | 8 | 17 | −1,43 |
| **total** | | **2.280** | **0,8750** | **0,8693** | **9** | **22** | **−0,57** |

- **CA2: falha.** Ganho −0,57 pp (exige ≥ +1,0). Consertadas − quebradas = −13 (exige ≥ 20).
- **CA3: falha.** Só 1 dos 4 vídeos ganha (exige 3); o pior piora 1,43 pp (limite −0,5).
- **CA4**: a escolha de cada vídeo veio dos outros 3 (LOO). Nenhuma escolha usou o próprio vídeo.
- **CA5: passa.** Duas execuções geraram o mesmo `a1_medida.json` (md5 `fd6b0e9c…`).
- **CA6: não se aplica** (variante reprovada).
- **Medida secundária (casa ≤ 7)**: ambíguas 2.099; D1 1.874 → A1 1.861; consertadas 9,
  quebradas 22. Mesmo sentido.
- **Unidades `(vídeo, tela, coluna, corda, casa)`**, ambíguas: 1.742 unidades; D1 acerta 1.502,
  A1 acerta 1.491; consertadas 4, quebradas 15 (líquido −11). O sinal é o mesmo.

### O que a grade diz sobre o tempo (diagnóstico; não é critério)

- **O termo de tempo quase não muda decisão.** Todas as configurações com `b₁ > 0` somam
  entre −2 e +3 notas de saldo nos 4 vídeos. A mudança de decisão vem da **escala** do termo
  de posição (`b₀`), que é o δ do D1 trocado por `1/b₀` (`b₀=0,5` → δ=2; `b₀=1` → δ=1; o D1 é
  `b₀=2`). Ela move em dois sentidos: retrato +5 e glimpse −9 em `b₀=0,5` (saldo por vídeo,
  `b₀=1`, sem corda: retrato −4, noturno +4, lacrimosa −1, glimpse +6; a tabela completa está em
  `grade_saldo_ambiguas` no JSON).
- **3 das 4 escolhas têm `b₁ = 0`.** Nessas dobras a A1 é só o D1 com outro δ, sem tempo. Só a
  escolha do noturno usa `b₁ > 0`.
- **Os dt do som recuaram para o marcador em boa parte dos pares**: retrato 269 de 636 (42 %),
  noturno 102 de 463 (22 %), lacrimosa 20 de 321 (6 %), glimpse 271 de 414 (65 %). Recuo é
  `dt` do `t_ini`, que a rodada cita como fonte de `dt` falso. Com tanto recuo, o teste do
  tempo fica fraco em glimpse e retrato.
- **Negativos**: nenhum `dt` negativo pelo som.

### Relatório (não é critério): `sky_*` sem alinhado de som

- Escolha da variante fixa: `b₀=1; b₁=0; sem corda` (a mesma do retrato e da lacrimosa). Todos
  os pares são do marcador (rotulado). Ambíguas nos 6 vídeos: 1.231 notas; D1 acerta 1.078,
  A1 acerta 1.080. Consertadas 3 e quebradas 1, todas em sky_2 (sky_1, sky_3, sky_5, sky_6 e
  sky_7 ficam iguais). Saldo líquido +2.
- Ouros do dono: **fora** (sem `t_ini`, sem `dt`).

### Pontos que a medida NÃO prova

- Não prova que o tempo não ajuda: a medida testou uma família (Laplace com escala linear no
  `dt`) e um dt que recuou para o marcador em até 65 % dos pares.
- Não prova nada sobre o canal de fora nem sobre o `sky guitar` como um todo (são 4 vídeos de
  um canal).
- A `b₀` pode estar apenas ajustando a escala do δ do D1, que já foi escolhida à mão.

### Consistência com a A3

- O D1 de referência é o da A3: 1.995 acertos em 2.280 ambíguas (0,8750).
- Os ouros do dono, que a main corrigiu (`retrato_brasileiro_v2`, room 335), não entram nesta
  rodada: sem `t_ini`.

## Não repetir

- **Escala linear no dt com b₀ livre, sem corda, para ganhar no sky guitar**: nas 4 dobras o
  que move a decisão é a escala do δ, não o tempo. Retentativa só com `dt` que não recua para o
  marcador (ou com o alinhado corrigido) e com a escala de posição fixa no D1.
- **Usar o `t_ini` como `dt` quando o som não confere**: 6 a 65 % dos pares. Qualquer retentativa
  precisa declarar essa fração antes.
- **Relatar o relatório (sky_1..7) como evidência de tempo**: todos os pares são do marcador.

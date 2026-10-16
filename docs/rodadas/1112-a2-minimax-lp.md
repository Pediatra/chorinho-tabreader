# 1112: A2, Minimax e L_p-Viterbi sobre o D1 do M8

**Frente**: A2 de [`docs/pesquisa/maos-frentes.md`](../pesquisa/maos-frentes.md) (seção 7, onda 2).
**Briefing**: [`docs/pesquisa/maos-onda2-briefings.md`](../pesquisa/maos-onda2-briefings.md),
bloco "Briefing — A1/A2".
**Código**: `tab/maos_decod_lp.py` (Minimax e L_p, em cima do Viterbi de
`tab/maos_decod_transicoes.py`), e `tests/test_maos_decod_lp.py`. Importa o D1 do M8, sem
editar.
**Saída**: `data/saida/maos/frentes/fa_decodificador/a2_medida.json` (só na pasta da frente).

Nota de ordem: o código de `tab/maos_decod_lp.py` já estava escrito quando este documento foi
commitado. **Nenhuma medida da A2 foi rodada** antes deste commit. O código implementa só as
regras abaixo, e a sanidade e o CA1 rodam depois deste commit.

## Pergunta

O D1 usa soma (p = 1) dos custos de transição, que é a estimativa de máxima verossimilhança
para o que foi tocado. O Minimax (p = ∞) escolhe o caminho cujo **pior** salto é o menor. Entre
os dois, uma potência p ∈ {2, 4} favorece saltos pequenos sem chegar ao Minimax. O caminho que
minimiza o pior salto acerta mais corda que o D1, nas notas ambíguas, sem olhar o vídeo de teste?

## Regras e pesos a priori

Escritos **antes** de qualquer medida desta rodada. Se alguma regra mudar depois de ver número,
a frente está invalidada (seção 5.3, CA4).

### 1. Dados

- **Vídeos de teste** (os mesmos da A1 e da A3): retrato = `mvp`, noturno =
  `q16_chopin_nocturne20`, lacrimosa = `sky_4`, glimpse = `sky_8`. Ataque do M8: notas com o
  mesmo `t_ini` (tolerância de 0,02 s), com os filtros do M8.
- **Relatório** (não é critério): `sky_1`, `sky_2`, `sky_3`, `sky_5`, `sky_6`, `sky_7`.
- **Ouros do dono**: **fora**. O briefing manda relatar só onde há `t_ini`. A2 não usa `dt`,
  mas a restrição vale mesmo assim, para não misturar o critério com as tablaturas sem tempo.

### 2. Custo

- **Ataque**: `α·casa + γ` por combinação, com α = 1, γ = 5 e β = 0, somado linear, como no D1.
- **Transição**: `c_k = δ·|Δposição|`, com δ = 0,5. Vale 0 quando um dos dois ataques não tem
  posição (só cordas soltas), como no D1.
- **Custo do caminho** (p finito): `Σ custo de ataque + Σ c_kᵖ`.
  - Só a transição é elevada a `p`. Com `p = 1` o custo é o do D1.
- **p = ∞ (Minimax)**: minimiza-se `max_k c_k`, com desempate pela soma
  `Σ custo de ataque + Σ c_k` (o caso p = 1 do desempate).
  - Exato em dois passos. Passo 1: `M*` é o menor teto tal que existe caminho com todos os
    `c_k ≤ M*`; acha-se por busca binária sobre os valores `δ·d`, para `d` de 0 a `CASA_MAX + 1`.
    Passo 2: Viterbi de soma, só entre os caminhos com `c_k ≤ M*`.
  - Não se usa um Viterbi com a ordem `(máximo, soma)` num único passo: essa ordem não é
    preservada pela soma de passos, e a busca poderia perder o caminho ótimo.

### 3. Sanidade (se falhar, pare)

- **p = 1** tem de dar **exatamente** o D1 (os mesmos índices de combinação em todos os ataques)
  nos 4 vídeos de teste.

### 4. CA1

- D0 e D1 refeitos batem com `data/saida/maos/m8/corda_sem_direita.json`, como na A1.

### 5. Escolha de `p` (CA4)

- **Grade**: `p ∈ {1; 2; 4; ∞}`.
- **Variante principal, fora da amostra**: para cada vídeo de teste `v`, escolhe-se o `p` de
  **maior saldo** (consertadas − quebradas, nas notas ambíguas, contra o D1) somado nos **outros
  3** vídeos de teste. Mede-se em `v` com esse `p`. São 4 escolhas; a variante principal é o
  conjunto delas.
- **Desempate**: o menor `p` (1, depois 2, 4 e ∞). Se nenhum `p` ganha, fica o D1.
- **Relatório**: o `p` de maior saldo nos **4** vídeos de teste (mesmo desempate). Nenhum dos 6
  `sky_*` do relatório entra nessa escolha.
- **Variante fixa** (escolhida nos 4, medida nos mesmos 4): **diagnóstico**, nunca aprovação.

### 6. O que conta como aprovação

- **CA1–CA7** da seção 5.3 de `maos-frentes.md`, contra o D1 (R1), com as 4 escolhas do item 5
  e agregado nas notas **ambíguas** dos 4 vídeos.
  - **CA2**: ganho líquido ≥ +1,0 pp e consertadas − quebradas ≥ 20.
  - **CA3**: ganho em pelo menos 3 dos 4 vídeos, e nenhum piora mais de 0,5 pp.
  - **CA5**: duas execuções dão o mesmo `a2_medida.json` (md5). Sem sorteio.
  - **CA6** (10 notas no quadro, 5 consertadas e 5 quebradas, com o caminho do recorte): só se a
    variante for aprovada.
  - **CA7**: gate verde na worktree.
- A medida secundária (casa ≤ 7) e a contagem por `(tela, coluna)` distinta entram no resultado,
  com denominador.

### 7. Hipótese e pegadinha

- **Hipótese (fraca)**, do briefing: um violonista evita o salto impossível mesmo que o resto da
  frase fique mais caro.
- **Pegadinha**: o Minimax foi feito para **gerar** um dedilhado tocável, não para **adivinhar** o
  que foi tocado. O teste existe para fechar a pergunta com um número. Não se espera ganho.
- Nada é ajustado para "salvar" o resultado. p e δ não são mudados depois de ver número.

### 8. O que não entra

- Ouros do dono (sem `t_ini`), tablatura externa (DadaGP, descartado pelo dono), e qualquer
  mudança no D1 ou no M8.
- A3 não é reaberta nesta rodada. Se a causa das 0 consertadas da A3 aparecer, vai no relatório
  como descrição, sem nova medida aprovável.

## Resultados

**Veredito: REPROVADA** pelo pré-registro. Falha em CA2 e CA3. A medida foi feita uma vez, com a
grade e o LOO das regras acima; a segunda execução só confere o CA5. Números:
`data/saida/maos/frentes/fa_decodificador/a2_medida.json`.

### Sanidade e CA1

- **Sanidade (regra 3): passa.** Com `p = 1` o caminho é exatamente o D1 nos 4 vídeos.
- **CA1: passa.** D0 e D1 refeitos batem com `corda_sem_direita.json` nos 4 vídeos.
- O código tem testes de unidade contra força bruta (20 testes, sem dados): o Viterbi de
  `Σ cᵖ` acha o mínimo para `p = 2` e `p = 4`, e o Minimax acha o menor `(máximo, soma)`
  lexicográfico em sequências pequenas.

### Medida principal (escolha por LOO, notas ambíguas)

| vídeo | escolha (fora do vídeo) | ambíguas | D1 | A2 | consertadas | quebradas | ganho (pp) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| retrato | p = 1 (D1) | 692 | 0,9277 | 0,9277 | 0 | 0 | 0,00 |
| noturno | p = 1 (D1) | 540 | 0,7611 | 0,7611 | 0 | 0 | 0,00 |
| lacrimosa | p = 1 (D1) | 418 | 0,8565 | 0,8565 | 0 | 0 | 0,00 |
| glimpse | p = 4 | 630 | 0,9270 | 0,8746 | 7 | 40 | −5,24 |
| **total** | | **2.280** | **0,8750** | **0,8608** | **7** | **40** | **−1,45** |

- **CA2: falha.** Ganho −1,45 pp (exige ≥ +1,0). Consertadas − quebradas = −33 (exige ≥ 20).
- **CA3: falha.** Nenhum vídeo ganha (exige 3); o pior piora 5,24 pp (limite −0,5).
- **CA4**: cada escolha veio dos outros 3 vídeos. No glimpse, o `p = 4` somava +3 nos outros três
  (retrato −15, noturno +17, lacrimosa +1), e depois perdeu 33 no próprio glimpse. É o caso
  típico de escolha que não generaliza.
- **CA5: passa.** Duas execuções geraram o mesmo `a2_medida.json` (md5 `5e197118…`).
- **CA6: não se aplica** (variante reprovada).
- **Medida secundária (casa ≤ 7)**: ambíguas 2.099; D1 acerta 1.874, A2 acerta 1.841;
  consertadas 7, quebradas 40. Mesmo sentido.
- **Unidades `(vídeo, tela, coluna, corda, casa)`**, ambíguas: 1.742; D1 acerta 1.502, A2 acerta
  1.471; consertadas 2, quebradas 33.

### Grade: saldo (consertadas − quebradas) nas ambíguas, por `p` (diagnóstico)

| `p` | retrato | noturno | lacrimosa | glimpse | soma |
| --- | --- | --- | --- | --- | --- |
| 1 (D1) | 0 | 0 | 0 | 0 | 0 |
| 2 | −6 | +5 | +1 | −9 | −9 |
| 4 | −15 | +17 | +1 | −33 | −30 |
| ∞ (Minimax) | −18 | +3 | −21 | −17 | −53 |

- Ao contrário da A1, aqui a grade mexe em decisões, e na maior parte **para pior**. O Minimax
  piora em 3 de 4 vídeos. O único ganho (noturno, +3) não basta para o veredito.
- Nenhum `p` ganha de forma consistente. A hipótese fraca (evitar o salto impossível) não tem
  apoio nesta medida.

### Relatório (não é critério): `sky_1`, `sky_2`, `sky_3`, `sky_5`, `sky_6`, `sky_7`

- Variante fixa: `p = 1`, ou seja, o próprio D1. Nos 6 vídeos, o caminho é o do D1: 1.231 notas
  ambíguas, 1.078 acertos nos dois, 0 consertadas, 0 quebradas.
- Ouros do dono: **fora** (sem `t_ini`, como na A1).

### Pontos que a medida NÃO prova

- Prova só que, com o δ do D1 e a soma de transições elevada a `p`, nenhuma escolha de `p` ganhou
  de forma consistente nos 4 vídeos. Não prova nada sobre o Minimax com outros pesos.
- O Minimax pode servir para gerar dedilhado tocável (é para isso que foi feito); esta medida não
  testa esse uso, só a adivinhação do tocado. Como a pegadinha do plano previa, a resposta é não
  para adivinhar.
- Não prova nada sobre o canal de fora (são 4 vídeos de um canal).

## Não repetir

- **Minimax com D1 e δ = 0,5 fixo** como estimador do tocado: piora em 3 de 4 vídeos (soma −53).
  Retentativa só como gerador de dedilhado, com outra métrica de sucesso.
- **Escolha de `p` por LOO com 3 vídeos de treino**: o `p = 4` somava +3 nos outros três e
  perdeu 33 no glimpse. A escolha de um `p` não generaliza com os dados atuais.

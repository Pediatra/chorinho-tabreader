# 0003 — Símbolos MULTI-CORDA: onde o código corta (revisão para auditoria externa)

> Escrito a pedido do dono: *"os símbolos ele não tá pegando por inteiro (tem símbolos multi-cordas do
> violão que aparecem em diversos lugares), tá cortando muita coisa"*. Esta é a revisão de código com os
> **pontos exatos**, para ele levar a outros agentes. **Não é opinião: cada ponto traz o número medido
> nesta investigação.**

## A causa de fundo, em uma frase

**O pipeline é mono-corda por construção.** Em quatro lugares independentes ele assume que um símbolo
cabe **dentro de uma corda** — e o vocabulário do próprio dono diz o contrário
(`configs/simbolos.yaml`: *"linha vertical sobre N cordas = arpejo"*; trêmolo, chaves e ligaduras
grandes também cruzam cordas). Um símbolo que cruza duas ou mais cordas é **cortado, dividido ou
recusado** por cada uma dessas quatro camadas, e nenhuma delas sabe representá-lo.

## Os oito pontos de corte (em ordem de gravidade)

### 1. A extração é por corda, uma de cada vez — `tab/tabseg.py:703` (`_glifos_por_faixa`)

O docstring diz literalmente: *"Extrai os glifos DENTRO da faixa de cada corda, **uma corda por vez**"*.
Um elemento vertical que cruza 3 cordas é lido como **3 pedaços**, um por faixa.
**É a origem dos outros cortes.**

### 2. O agrupamento em token é por corda — `tab/tabseg.py:791` (`agrupar_tokens`)

*"Junta componentes vizinhos na MESMA corda em um token"*; a implementação usa
`por_corda: dict[int, list[Glifo]]` (`:799`) e o `Glifo` tem **um único campo `corda`**.
**Não existe, no modelo de dados, um token que ocupe duas cordas.** Multi-corda é
irrepresentável hoje, não só mal recortado.

### 3. Apagar as faixas das cordas FATIA o símbolo — `tab/tabseg.py:872` (`_sem_faixas`)

O caminho do símbolo apaga faixas horizontais de `±0,12 passo` em cada corda (para o arco deixar de
estar colado na linha). Efeito colateral **garantido**: um traço vertical que cruza as cordas é
**cortado em N pedaços** nesses pontos. Foi essa função que me deu o resultado "neutro" medido
(recall 0,216 → 0,210) — e agora eu entendo por quê: ela conserta o arco de uma corda **destruindo**
justamente o que cruza várias.

### 4. O delimitador recusa por tamanho — `tab/tabseg.py:328-330`, usado em `:511-515`

```python
LARGURA_MAX_PASSOS = 2.0   # tab/tabseg.py:328
ALTURA_MAX_PASSOS  = 2.0   # tab/tabseg.py:329
ALTURA_MIN_PASSOS  = 0.20  # tab/tabseg.py:330
```

Qualquer componente com **mais de 2 passos de altura** cai em `alto_demais`; **mais de 2 de largura**,
`largo_demais`. **Medido**: ao rastrear as marcas do dono, **92 componentes** foram recusados por
`alto_demais` e **101** por `largo_demais` — é o maior balde de recusas. Um arpejo sobre 4 cordas tem
~3-4 passos de altura: **recusado por construção**.

### 5. A JANELA que o modelo vê tem 1,6 passo de altura — `tab/reconhecer.py:375`, `:404`, `:501`

```python
hx, hy = round(1.2 * g.passo), round(0.8 * g.passo)   # janela 2,4 x 1,6 passos
```

O recorte que entra na rede tem **1,6 passo de altura — menos de duas cordas**. **Um símbolo multi-corda
não CABE no que o modelo olha.** Mesmo com segmentação perfeita, o classificador nunca vê o símbolo
inteiro.

### 6. O filtro de forma exige "largo e baixo" — `tab/reconhecer.py:210` e `:484`

```python
forma_simbolo: tuple[float, float] = (1.5, 1.5)
if (tk.x1 - tk.x0) < 1.5 * g.passo or (tk.y1 - tk.y0) > 1.5 * g.passo: continue
```

Passa só o que tem **≥1,5 passo de largura e ≤1,5 de altura** — a assinatura de um arco de uma corda.
**Todo símbolo alto (multi-corda) é excluído por construção.** Foi este filtro que criou os "buracos":
**21 de 25** buracos com tinta tinham **token cobrindo a marca** e eram descartados aqui.

### 7. A faixa de trabalho da tablatura — `tab/pipeline.py:184` (`roi_das_cordas`)

`margem = 1 passo` em volta das cordas detectadas. Símbolo **acima da 1ª corda** ou **abaixo da 6ª**
(chaves, setas, indicações) pode ficar **fora da ROI** — e ficou: **25 das 189 marcas** do dono caíram
fora da ROI nas minhas medições.

### 8. O treino nunca viu multi-corda — `data/gold/`

Os positivos são recortes de **2,4 × 1,6 passos centrados nas marcas do dono** — portanto
**single-string**. A rede aprendeu "símbolo = arco baixo". **Corrigir a janela sozinho não resolve**: sem
exemplos multi-corda no treino, a rede vai recusá-los (ou pior, aceitar lixo alto).

## O que isso explica dos números que eu já tinha

| medição | valor | leitura com esta revisão |
| --- | --- | --- |
| recusas do delimitador por tamanho | 92 `alto_demais` + 101 `largo_demais` | é aqui que o multi-corda morre |
| marcas fora da ROI | 25 de 189 | ponto 7 |
| buracos com token cobrindo a marca | 21 de 25 | ponto 6 (o meu filtro de forma) |
| recall fim a fim | 0,216 | teto imposto pelos pontos 1-6 |
| LOCA do classificador | 0,74-0,79 | **alto porque o conjunto é todo de uma corda** |

**A LOCA alta nunca foi evidência de que o símbolo está resolvido**: ela mede o modelo num conjunto onde
**todo símbolo é de uma corda**. É a mesma armadilha das outras vezes — o número mede o que o dado
permite, não o que o produto precisa.

## O que precisa ser decidido (não é conserto pequeno)

1. **Modelo de dados**: `Glifo`/token precisam poder ocupar **N cordas** (hoje têm um `corda: int`).
2. **Extração**: componentes precisam ser extraídos **sem partir por corda** e só depois associados às
   cordas que cruzam (o inverso do que `_glifos_por_faixa` faz).
3. **Delimitador**: os limites de 2 passos precisam ser **função do tipo** (arco de 1 corda × arpejo de
   N cordas), não um teto único.
4. **Janela do modelo**: crescer (ou passar a ser por tipo) e **treinar com multi-corda** — o conjunto
   atual não tem nenhum.
5. **Filtro de forma**: hoje exclui alto por construção; precisa deixar de ser regra de forma e virar
   decisão do modelo (com dado).
6. **Aviso para a auditoria**: o dono está certo em **não rotular** antes disto. Rotular símbolo
   multi-corda numa ferramenta que mostra janela de 1,6 passo **colhe rótulo errado** — ele vê um pedaço
   e responde sobre o todo.

## O que eu NÃO sei (honestidade obrigatória)

- **Quantos** símbolos do acervo são multi-corda: nunca medi. Não tenho o número e não vou estimar.
- **Se** a rede generaliza para multi-corda depois de treinada: não testado.
- **Qual** o desenho certo do token multi-corda (uma caixa por símbolo? várias cordas com um id comum?):
  decisão de arquitetura, não de ajuste.

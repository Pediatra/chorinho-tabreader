# 0152 — Rolagem (C1): consenso, máscara do cursor e remedida dos saltos

**Frente:** C1. **Branch:** `tab/c1-rolagem`. **Saída:** `data/saida/tab_frentes/fc_rolagem/rodada0152/`.
**Segue:** 0151 (aceite não atingido: máscara do kenneth falhou, leonardo com 6 pares).

Este documento tem duas partes, commitadas separadamente. **Parte 1 (critérios):** escrita e
commitada antes de qualquer medida nova. **Parte 2 (resultados):** depois da máscara corrigida
e das remedidas. Nada aqui muda depois de ver o erro; se uma regra se mostrar errada, a correção
vira outra rodada, com o motivo escrito.

## Pergunta

Com a regra de consenso (salto indefinido quando o phaseCorrelate e as barras discordam em mais
de 2 px) e a máscara do cursor corrigida, os saltos com sobreposição dos três vídeos ficam com
erro mediano ≤ 1 px e nenhum salto válido com erro > 5 px?

## Decisões da sessão principal (vinculantes)

1. O limiar de tinta 200 é definição (já commitado na 0151). Os 20 saltos do mr. tabs são novos.
2. Pior caso: nenhum salto válido com erro > 5 px depois da regra de consenso. Indefinido não
   entra nessa conta e não se monta panorama sobre ele.
3. Máscara do cursor claro (kenneth): corrigir o limite de saturação, conferir no quadro que o
   cursor sai da máscara, commitar antes de remedir.
4. Transição do kenneth (184,5–184,9 s): medir do último quadro parado antes ao primeiro parado
   depois. Os quadros da animação não entram.
5. Leonardo: completar os 20 com outro vídeo do mesmo canal; se não houver 20 saltos com
   sobreposição em até 3 vídeos, trocar de canal e registrar.

## Parte 1 — Critérios (escritos antes de medir)

### C1. Consenso (regra fixa)

Para cada salto: `dx_a` (phaseCorrelate, caminho a) e `dx_b` (barras, caminho b; `None` se
menos de 2 barras casam).

- **Válido:** `dx_b` existe e `|dx_a − dx_b| ≤ 2 px`. Valor de consenso = média de `dx_a` e `dx_b`.
- **Indefinido:** qualquer outro caso. Conta-se, lista-se com o motivo (sem barras casadas, ou
  discordância > 2 px). Fica fora das medianas do aceite e do erro máximo do consenso. Não entra
  em panorama. Não se muda o método depois de ver o indefinido.
- Erros de (a) e (b) são reportados de duas formas: sobre todos os saltos com estimativa, e sobre
  os válidos (mesmo conjunto do consenso, para comparar).

Implementado em `tab/rolagem_saltos.py::consenso` (`TOL_CONSENSO_PX = 2.0`), com teste unitário.
O `saltos.json` passa a trazer `dx_consenso` (`None` = indefinido).

### C2. Aceite por vídeo (congelado)

Sobre os saltos **válidos**:

- mediana do erro de (a) ≤ 1 px **e** mediana do erro de (b) ≤ 1 px;
- máximo do erro do consenso ≤ 5 px (pior caso, decisão 2). Se algum vídeo tiver salto válido
  com erro > 5 px, a rodada para e se relata esse salto. Não se reajusta nada depois.

Meta: 20 saltos medidos à mão, com sobreposição, por vídeo. O número de válidos entre eles é
reportado; a mediana é calculada sobre os válidos, com `n` escrito.

Continuidade (olho): o compasso impresso que sai e o que entra batem com o dx do salto. Para o
leonardo, que não tem número impresso, a conferência é pelo conteúdo (mesma posição relativa das
notas nos dois quadros), como na 0151.

### C3. Máscara do cursor claro (kenneth)

- **Calibração:** quadro do kenneth em t = 184,0 s (cursor em x ≈ 1162, como na 0151).
- **Verificação:** quadro do kenneth em t = 110,0 s, com o cursor visível. Se o cursor não aparecer
  nesse quadro, usa-se o próximo instante de 10 em 10 s com cursor visível, registrado.
- **Colunas do cursor:** as colunas da linha azul clara, lidas numa sonda de pixels no quadro de
  calibração (valores escritos nos resultados).
- **Critérios numéricos:**
  - (i) ≥ 95 % dos pixels das colunas do cursor, na faixa do recorte, ficam mascarados;
  - (ii) a máscara do cursor cobre ≤ 0,5 % da tinta do quadro (pixels com cinza < 200), fora do
    cursor.
- **Escolha do limite:** `SAT_CURSOR` passa a ser o maior inteiro ≤ 80 que cumpre (i) e (ii) no
  quadro de **calibração**. Matiz (90–130) e destaque de compasso (sat ≥ 25, val ≥ 150) não mudam.
- **Verificação:** o mesmo limite, no quadro de **verificação**, cumpre (i) e (ii), e a imagem da
  máscara (`rodada0152/mascara/`) é conferida no olho. Se a verificação falhar, a rodada para e
  registra; não se troca o limite.

#### C3, correção antes de escolher o limiar (sonda de pixels, sem deslocamento)

A redação acima não era alcançável, e isso foi visto na sonda de pixels (`rodada0152/_sonda_cursor.py`,
`_sonda_pixels.py`, `_sonda_limiar.py`, `_sonda_limiar2.py`), antes de qualquer escolha de limiar:

- A faixa de colunas 1160–1167 mistura o cursor com pixels de papel: abaixo da linha do cursor
  (linhas 203 a 224) a coluna é branca (246, 246, 246). Esses pixels têm matiz 0 e sat 0, e entram
  no denominador de (i) sem poderem ser mascarados. A cobertura máxima, com qualquer limiar, ficou
  em 0,898 (`_sonda_limiar.py`).
- A tinta azul fora do cursor já aparece com o limiar 80 (0,42 % do quadro de 184 s e **1,12 % do
  quadro de 110 s**). Um critério absoluto de 0,5 % para toda a tinta fora do cursor reprova em
  todos os limiares, mesmo sem mudar nada no cursor. O que importa é o acréscimo do limiar novo.

Correção, escrita antes de escolher o limiar:

- **Núcleo do cursor:** colunas com pelo menos 100 px de matiz azul (90–130) e sat ≥ 5 no quadro.
  No quadro de 184 s são as colunas 1162–1165. **Pixels do cursor:** pixels do núcleo com cinza < 240
  (o papel branco, 246, fica de fora). Não entram as bordas (1160–1161, sat ~17 e matiz verde;
  1166–1167, branco esverdeado).
- **(i) Cobertura:** ≥ 95 % dos pixels do cursor são mascarados pelo novo limiar, nos dois quadros.
- **(ii) Acréscimo de tinta:** a tinta fora do núcleo (cinza < 200) que o novo limiar mascara,
  como fração da tinta do quadro, não passa do que o limiar 80 já mascara **mais 0,5 pontos
  percentuais**, nos dois quadros.
- **Limiar:** `SAT_CURSOR` = maior inteiro ≤ 80 que cumpre (i) e (ii) no quadro de calibração
  (184 s). O quadro de verificação (110 s) confere com o mesmo limiar: (i) e (ii) de novo, e a
  imagem da máscara no olho.
- Se nenhum inteiro de 5 a 80 cumprir (i) e (ii) no quadro de calibração, a rodada para e registra.

A máscara corrigida é commitada antes da remedida. Como ela muda a entrada de todos os vídeos,
**todos os números da 0152 são feitos com o código final**, inclusive os 6 do leonardo que já
existiam na 0151.

### C4. Transição do kenneth (184,5–184,9 s)

- Quadros a 10 qps em [182,0; 187,0] s, com a máscara final. Um par `(t, t+0,1)` é **parado** se
  `|dx| < 0,3 px` e resposta ≥ 0,5 pelo caminho a.
- **Quadro de antes:** `t_A` = último quadro com par parado e `t_A < 184,5`.
- **Quadro de depois:** `t_B` = primeiro quadro com par parado e `t_B ≥ 184,9`.
- Os quadros entre `t_A` e `t_B` não entram: a transição é **um** salto, medido de `t_A` a `t_B`
  pelos caminhos a e b, com a mão pelo compasso visível nos dois quadros.
- Entra como linha própria do kenneth, **fora dos 20** da remedida, mas dentro do pior caso (C2).

### C5. Mr. tabs "no rain": 20 saltos novos

- **Trecho:** 150,0 a 360,0 s, em janelas de 30 s (`t0` = 150, 180, …, 330), 10 qps,
  recorte 807–1019, `x_max` 1920, código final.
- **Seleção:** em ordem de tempo, os saltos com `sobreposicao = True`, `n_passos ≤ 4`, e com
  `t_antes` e `t_depois` a pelo menos 1,0 s de cada borda da janela (saltos na borda são
  registrados e não entram). São os 20 primeiros. Nenhum dos 20 da 0151 entra: todos têm `t < 150 s`.
- Se até 360 s não houver 20, registra-se o número e a rodada para o mr. tabs.
- A seleção não olha o erro. Quem entra é decidido pela regra, não pela medida.

### C6. Kenneth: os mesmos 20 da 0151

- **Conjunto:** os 20 saltos da 0151 com `t_antes` de 66,6 a 135,0 s (`kenneth_w62`, `kenneth_w92`,
  `kenneth_w122`), remedidos com o código final nas mesmas janelas (`t0` = 62, 92, 122).
- Se a lista mudar pelo código novo, usa-se a regra: os 20 primeiros com sobreposição a partir de
  66,6 s, pelo código final. A mudança é registrada.
- **Mão de referência:** a escolha de compasso e de x de `escolhas_kenneth.json` (feita por
  leitura visual na 0151) é mantida para os saltos que batem em `t_antes` (tolerância de 0,05 s).
  O x sub-pixel é recalculado com a máscara final. Registrado como reuso, não como nova leitura.

### C7. Leonardo ramos: 20 pares

- **Aire de zamba (0151):** os 6 saltos com `t_antes` 24,4; 37,5; 78,8; 90,7; 98,7 e 115,9,
  remedidos nas janelas da 0151 (`t0` = 0, 7, 37, 67, 97, 127). A mão é reusada de
  `escolhas_leonardo.json`, como no kenneth.
- **Vídeo 2:** os próximos vídeos da pasta `leonardo ramos`, na ordem de nome em bytes
  (`LC_ALL=C`) que vêm depois de `aire de zamba`. Usa-se o primeiro.
- **Trecho do vídeo 2:** 0 a 150 s, janelas `t0` = 0, 30, 60, 90, 120. Seleção como em C5
  (sobreposição, `n_passos ≤ 4`, borda de 1 s).
- **Vídeo 3 (se o vídeo 2 não bastar):** o seguinte na mesma ordem, mesmo trecho. Nunca mais de
  3 vídeos no total (aire + 2).
- **Mão do vídeo 2 e do 3:** barra escolhida pelo conteúdo, no olho, nos dois quadros.
- Se 3 vídeos não derem 20 saltos com sobreposição, o canal sai e a troca é registrada (regra da
  decisão 5), com o motivo.

### C8. Saídas, gate e commits

- Saída em `data/saida/tab_frentes/fc_rolagem/rodada0152/` (fora do git, pelo bind-mount).
- Scripts de medida ficam na pasta da rodada (como na 0151); o que vale para o código está em
  `tab/rolagem_*.py`.
- Commits: (1) critérios (esta parte, com `consenso` e teste); (2) máscara corrigida (com a
  verificação); (3) resultados (esta rodada, com o número na mensagem).
- Gate antes de cada commit: `ruff check` e `ruff format --check` limpos, `pytest tests/`.
- Sem GPU. Acervo só leitura. Nenhum commit em `data/gold/`, na `main`, em `ESTADO.md` ou nos
  arquivos de outras frentes.

### C9. O que esta rodada não faz

- Não faz panorama, mapa x → t, leitura de notas nem o gabarito do dono.
- Não reabre a definição de salto (passo parado, animação, limiar de tinta 200).
- Não mede trocas de página sem sobreposição: são registradas e ficam fora.

## Calibração da máscara (C3, resultado; sem deslocamento)

Regra de C3 (corrigida acima) aplicada no `_sonda_limiar3.py`, saída em
`rodada0152/calibracao_cursor_escolha.json`:

| quadro | papel | núcleo do cursor | cobertura (i) | acréscimo de tinta fora (ii) |
| --- | --- | --- | --- | --- |
| kenneth 184,0 s | calibração | colunas 1162–1165 | 0,991 | +0,05 pp (0,467 % − 0,415 %) |
| kenneth 110,0 s | verificação | colunas 772–775 | 0,959 | +0,46 pp (1,577 % − 1,120 %) |

- Maior inteiro ≤ 80 que cumpre (i) e (ii) na calibração: **`SAT_CURSOR = 32`** (era 80).
  Matiz 90–130 e destaque (sat ≥ 25, val ≥ 150) não mudam.
- Conferência no olho: `rodada0152/mascara_cursor_ver110_sat32.png` e
  `mascara_cursor_cal184_sat32.png`. A linha do cursor sai inteira da máscara nos dois quadros.
  A máscara também pinta de vermelho algumas franjas azuladas de algarismos (o acréscimo de
  0,46 pp). Está dentro da regra; registra-se como custo, não como defeito.
- Margem da verificação: a cobertura (0,959) passa de 0,95 e o acréscimo (0,457 pp) fica abaixo de
  0,5 pp. Passa, com pouca folga, e a remedida é que mostra se a franja muda o erro.
- **Nota de processo:** a correção de C3 foi escrita depois das sondas de diagnóstico
  (`_sonda_cursor.py`, `_sonda_pixels.py`, `_sonda_limiar.py`, `_sonda_limiar2.py`), que não
  escolheram limiar, e antes do cálculo do limiar (`_sonda_limiar3.py`). Ela **não** foi commitada
  sozinha antes do cálculo: segue no commit da máscara, junto do código. Nenhum deslocamento foi
  medido antes disso.

## Parte 2 — Resultados

**Veredito: aceite da C1 não atingido. A rodada parou no mr. tabs pela regra de parada
(decisão 2 e entrega). O leonardo não foi medido.**

Código final: `tab/rolagem_saltos.py` com `SAT_CURSOR = 32` e `consenso`. Saídas em
`rodada0152/` (fora do git). Estatística: `rodada0152/_estatisticas.py` (stdlib).

### Kenneth "location" (20 da 0151, com a máscara final)

Janelas `kenneth_w62`, `kenneth_w92`, `kenneth_w122` (t0 = 62, 92, 122). Conjunto: os 20 primeiros
com sobreposição a partir de 66,6 s, pelo código final. **Mudança em relação à 0151:** 83,4 s saiu
(com a máscara nova o passo deixou de ser animação e virou indefinido); 135,2 s entrou (20º).
Referência à mão: 19 escolhas da 0151 reusadas pelo instante (t_antes, tolerância 0,05 s), com o
x recalculado pela máscara final; 135,2 s lido agora (compasso 45, x 628 → 537). Sem reuso nos casos
em que o compasso não estava na 0151.

| item | valor |
| --- | --- |
| saltos medidos à mão, com sobreposição | 20 |
| válidos (consenso) | 19 |
| indefinidos | 1: 100,6 s (sem barras casadas; b = None) |
| erro mediano (a), válidos | 0,08 px (máx. 0,35) |
| erro mediano (b), válidos | 0,13 px (máx. 0,47) |
| erro mediano / máximo do consenso, válidos | 0,06 / 0,26 px |
| salto válido com erro > 5 px | nenhum |

Continuidade (olho): os compassos impressos batem com o dx de todos os saltos. Os 19 válidos e o
indefinido de 100,6 s têm compasso visível nos dois quadros.

**Transição 184,4 → 184,9 s (C4):** os quadros parados pela regra são `t_A` = 184,4 s e `t_B` =
184,9 s. Os passos entre eles são: 184,5–184,6 indefinido (resp. 0,04 e 0,07), 184,6–184,7 indefinido,
184,7–184,8 indefinido com dx −205 (resp. 0,47), 184,8–184,9 animação de −17 px. Entre `t_A` e `t_B`
o salto medido por (a) dá dx −0,27 com resposta 0,02 (indefinido); por (b), dx −15,0 com 3 barras
casadas, que é casamento espúrio de compassos repetidos. **Consenso: indefinido.** Não há compasso
visível nos dois quadros: em 184,4 s estão os compassos 59 (x 492) e 60 (x 1071); em 184,9 s estão 61
(x 478) e 62 (x 1056) (ampliação em `rodada0152/transicao_kenneth/rotulos_184.*.png`). Sem referência
à mão. A aritmética de compassos de 578 px sugere dx ≈ −1171 px, mas isso não é medida; a transição
fica fora do aceite e não entra no panorama.

### Mr. tabs "no rain" (20 saltos novos, 150 a 240 s)

Janelas `mrtabs_w150`, `mrtabs_w180`, `mrtabs_w210` (30 s, 10 qps, código final). Seleção pela
regra C5: 155,9 a 233,8 s, 20 saltos, todos com sobreposição, `n_passos ≤ 4`, 1 s de folga das bordas.
Compassos lidos pelo número impresso (para todos os 20); 161,5, 172,7 e 206,1 foram conferidos por
ampliação dos rótulos.

| item | valor |
| --- | --- |
| saltos medidos à mão, com sobreposição | 20 |
| válidos (consenso) | 20 |
| indefinidos | 0 |
| erro mediano (a) | 0,16 px |
| erro mediano (b) | 0,22 px |
| erro mediano / máximo do consenso | 0,23 / 1557,45 px |
| salto válido com erro > 5 px | **3** |

Os 3 saltos com erro > 5 px (dos dois métodos concordam em cada um):

| t_antes | compasso | a | b | consenso | mão (compasso impresso) | erro |
| --- | --- | --- | --- | --- | --- | --- |
| 161,5 s | 102 (x 1496 → 145) | +207,0 | +207,0 | +207,0 | −1350,5 | 1557,4 px |
| 172,7 s | 109 (x 1520 → 165) | −575,8 | −576,5 | −576,2 | −1354,7 | 778,6 px |
| 206,1 s | 130 (x 1471 → 125) | −656,3 | −656,5 | −656,4 | −1346,6 | 690,2 px |

Causa: o padrão do mr. tabs tem compassos alternados de 340 e 439 px (período de dois compassos, ~779
px). Nos três saltos, a e b casam o alinhamento de um período (ou de dois compassos) deslocado, e a
regra de consenso (diferença ≤ 2 px entre a e b) deixa passar, porque os dois erram do mesmo jeito.
Na 0151 o mesmo tipo de falha apareceu em 2 dos 20 pares de mr. tabs; aqui em 3 dos 20.

As outras 17 medidas ficam com erro de consenso ≤ 0,5 px.

### Parada

Pela regra de parada da sessão principal (algum salto válido com erro > 5 px depois do consenso),
a rodada para no mr. tabs. **Não se mediu o leonardo** (6 pares da 0151 e o vídeo 2 da regra C7 ficam
sem remedida), e nenhum panorama, mapa x → t ou gabarito foi montado.

O que a regra de consenso não cobre: alinhamentos errados que os dois métodos compartilham (período de
compassos repetidos). Para decidir a próxima rodada, a sessão principal precisa escolher entre (i)
verificar a continuidade do número de compasso (o dx tem que levar o compasso impresso de antes ao
mesmo número depois) como terceiro critério, ou (ii) limitar o dx a um compasso. Nenhuma das duas foi
implementada nesta rodada, porque mudar a definição depois de ver o erro não cabe aqui.

### Commits desta rodada

- `89f3bb2a` critérios antes de medir (consenso com teste; doc 0152, parte 1).
- `7bf04d82` máscara do cursor: `SAT_CURSOR` 80 → 32 (calibração: cobertura 0,991, acréscimo de tinta
  0,05 pp; verificação: 0,959 e 0,46 pp). Inclui a correção de C3 (ver nota de processo).
- `c1a3d54a` correção do `dx_consenso` no CLI (KeyError; sem medida).
- Commit de resultados: este documento, com os números acima.

### Limites

- Referência à mão: o compasso é lido pelo número impresso. O x é o centro de massa ±4 px (o mesmo de
  0151). Não é independente do limiar de tinta 200 do detector.
- Saltos na borda de janela (±1 s) ficam fora da seleção, por regra; o leonardo não foi medido.
- Os 19 kenneth reusam escolhas visuais da 0151; a escolha do compasso não depende do cursor.

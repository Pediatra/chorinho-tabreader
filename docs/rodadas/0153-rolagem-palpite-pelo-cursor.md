# 0153 — Rolagem (C1): palpite pelo cursor com período (última tentativa da onda)

**Frente:** C1. **Branch:** `tab/c1-rolagem`. **Segue:** 0152 (aceite não atingido: 3 saltos do
mr. tabs com alias de 690, 779 e 1557 px; leonardo não medido).
**Saída:** `data/saida/tab_frentes/fc_rolagem/rodada0153/` (fora do git).

Este documento tem duas partes, commitadas separadamente. **Parte 1 (critérios):** escrita e
commitada, sozinha, antes de qualquer medida nova. **Parte 2 (resultados):** depois das remedidas.
Nada aqui muda depois de ver o erro. Se uma regra se mostrar errada, a correção é outra rodada, e
não entra nesta.

## Pergunta

A regra de consenso não pega o alias de período (os dois métodos erram igual). Um palpite pelo
cursor, escolhendo entre os candidatos `dx_medido + k·P` o mais perto de um `dx_cursor` independente,
corrige o alias? Com os mesmos 20 saltos do mr. tabs e os 20 do kenneth da 0152, o erro mediano fica
≤ 1 px e nenhum salto definido tem erro > 5 px?

## Decisões da sessão principal (vinculantes)

1. **Não limitar dx a um compasso.** Há saltos de ~675 px no mr. tabs, maior que um compasso.
2. **Número de compasso impresso: só conferência, onde existir.** Não é método.
3. **Método: palpite pelo cursor**, com as tolerâncias abaixo, escritas antes de medir.
4. **Mesmos saltos.** Remedir os 20 do mr. tabs da 0152 e os 20 do kenneth; não trocar saltos.
5. **Leonardo:** só se o mr. tabs passar (ver C10). Se não passar, a rodada para antes dele.
6. **Aceite congelado** (como na 0152): mediana ≤ 1 px e nenhum salto definido com erro > 5 px, por
   vídeo. Indefinido não entra nessa conta.

## Parte 1 — Critérios (escritos antes de medir)

### C0. Convenções

- `dx = x_depois − x_antes` (a mesma convenção da 0152; `dx_mao = xb − xa`).
- Quadros: `i_antes` é o último quadro parado antes do salto e `i_depois` o primeiro parado depois,
  como em `tab/rolagem_saltos.py` (`saltos` usa `atual[0]["i"]` e `atual[-1]["j"]`).
- Janelas e parâmetros: os da 0152 (lidos de cada `saltos.json`: `t0`, `dur`, `qps`, `recorte`,
  `x_max`). Código: o de `tab/rolagem_saltos.py` sem alteração (`SAT_CURSOR = 32`).

### C1. Entradas por salto

- **`dx_medido` = `dx_a`** (phaseCorrelate, caminho a). Escolha fixa: é o caminho com erro mediano
  menor na 0152 (0,16 px contra 0,22 px de b).
- **`dx_mao`**: referência à mão da 0152 (`mao_mrtabs_0152.json`, `mao_kenneth.json`). Não há nova
  escolha de compasso nesta rodada. A referência é o compasso impresso e o x de cada quadro, como na
  0152.
- **Mesmos saltos**: entram os saltos cujo `t_antes` bate com o da referência à mão (tolerância de
  0,05 s). Nenhum salto novo entra.

### C2. Cursor (automático, no quadro de antes)

- Máscara do cursor: `sat ≥ 32` e matiz em `[90, 130]` (a parte azul da `mascara`).
- Contagem por coluna dessa máscara, na faixa `[0, x_max)`. Colunas com **≥ 100 px** contam.
- Agrupam-se colunas consecutivas. O **cursor** é o grupo de maior contagem com **largura ≤ 4 px**.
  `x_cursor` = média das colunas do grupo.
- Sem grupo: **indefinido** (motivo: cursor ausente).

### C3. Compasso do cursor antes

- `s_antes` = maior x de `barras(...)` do quadro de antes (com a máscara, como em `medir`) tal que
  `x ≤ x_cursor`.
- Sem barra à esquerda do cursor: **indefinido** (motivo: sem barra antes do cursor).

### C4. Início da linha depois

- `s_depois` = menor x de `barras(...)` do quadro de depois (mesma máscara).
- Sem barra: **indefinido** (motivo: sem barra depois).
- Premissa da sessão principal: o compasso do cursor, depois do salto, fica no início da linha. A
  medida testa essa premissa; ela não é assumida como verdadeira.

### C5. `dx_cursor`

- `dx_cursor = s_depois − s_antes`.
- Nota de sinal: a sessão principal escreveu `x_antes − x_depois`. Com essa expressão, `dx_cursor`
  sai com o sinal oposto ao `dx_medido` e a comparação com os candidatos não faz sentido. Adota-se
  `depois − antes`, a convenção da 0152. Mesma grandeza, sinal igual ao de `dx`.

### C6. Período `P` (autocorrelação da faixa, quadro de antes)

- Perfil de tinta por coluna: `t(x)` = média, sobre todas as linhas da faixa, de `255 − cinza`, com os
  pixels mascarados valendo 0. Faixa `x ∈ [0, x_max)`.
- Autocorrelação normalizada (Pearson sobre a sobreposição, sem média subtraída da curva) para
  `L ∈ [300, 1500]` px.
- `P` = o `L` de maior valor. **Indefinido** se o pico for < 0,2 (motivo: período sem pico claro).
- Registra-se também o valor do pico.

### C7. Candidatos e escolha

- Candidatos: `c_k = dx_medido + k·P`, com `k ∈ {−2, −1, 0, 1, 2}`.
- `c*` = o `c_k` com `|c_k − dx_cursor|` mínimo. Empate: o de menor `|c_k|`.
- **Definido** se `|c* − dx_cursor| < P/2` ("meia distância entre candidatos"). Senão, **indefinido**
  (motivo: nenhum candidato a menos de P/2 do cursor).
- Consequência registrada: pela construção, a condição só falha se `dx_cursor` cair fora de
  `[c_{−2} − P/2, c_{2} + P/2]`. A regra não tem outra folga.

### C8. Saída do método e erros

- `dx_metodo = c*` para os saltos definidos.
- Erro do método: `|dx_metodo − dx_mao|`.
- Comparação: erro do consenso da 0152, `|dx_consenso − dx_mao|`, nos saltos em que o consenso antigo
  é válido, e erro de `dx_a` em todos.
- Mediana e máximo sobre os definidos, com `n` escrito.

### C9. Aceite (congelado)

Por vídeo, sobre os saltos **definidos** pelo método:

- mediana do erro ≤ **1 px**;
- nenhum salto definido com erro > **5 px**.

Indefinidos: contados, listados com o motivo, fora das contas. Não se monta panorama sobre eles.

### C10. Ordem e parada

- Ordem: mr. tabs (20), kenneth (20).
- **Se o mr. tabs não passar em C9, a rodada para.** O leonardo não é medido nesta rodada, e o
  kenneth sai como diagnóstico, com a mesma regra.
- Se o mr. tabs passar, o leonardo entra, com 20 saltos com sobreposição (regra da 0152, C7). Esse
  caso não é esperado pela observação abaixo.

### C11. Não repetir (registro antes da medida)

- Alias de período com dois métodos concordando não se resolve por consenso (0152).
- Remedidas que mudam a regra depois de ver o erro não contam como aceite.

### C12. Risco registrado antes da medida (observação na folha, não medida)

Lido na folha existente `rodada0152/mrtabs_w150/comp/salto00_155.90.png` (salto de 155,9 para 156,0 s,
compasso 96 na referência, dx = −237 px):

- A linha azul do cursor, no quadro de 155,9 s, fica perto de x ≈ 1449 px, dentro do compasso 98
  (barras em ~1298 e ~1726, com a faixa de destaque sobre o compasso).
- No quadro de 156,0 s, o compasso 98 aparece em x ≈ 1062, ou seja, **não** vai ao início da linha:
  a linha só anda 237 px e o compasso do cursor continua a meio da tela.
- Se isso valer para os saltos pequenos (a maioria dos 20), a premissa de C4 não vale, e o método
  escolhe um candidato errado. A medida diz isso com número. Não se corrige o método depois.
- Segundo risco: `barras(...)` pega colunas que não são barras (hastes de notas que cruzam a faixa,
  como os rótulos 63, 140, 578 e 693 da mesma folha). Isso afeta `s_depois` e `s_antes`.

## Parte 2: resultado e encerramento

Números conferidos nos `metodo.json` de `data/saida/tab_frentes/fc_rolagem/rodada0153/` e no
`_log_rodar.txt`. Batem em todos os campos citados abaixo (n, definidos, indefinidos, instantes e
erros). Nenhuma medida nova foi feita nesta parte.

### Resultado por janela (mr. tabs, saltos com referência à mão)

| janela | n | definidos | indefinidos (motivo) | erro mediano (definidos) | erro máximo (definidos) | definidos com erro > 5 px |
| --- | --- | --- | --- | --- | --- | --- |
| 150 s | 7 | 6 | 1: 161,5 s (sem cursor) | 310,09 px | 1259,76 px | 3 |
| 180 s | 9 | 7 | 2: 183,5 s e 199,7 s (sem cursor) | 0,32 px | 1462,90 px | 3 |
| **total** | 16 | 13 | 3 | 0,32 px | 1462,90 px | **6** |

Separando os definidos corretos (erro ≤ 5 px) dos errados (erro > 5 px):

| janela | corretos: n, mediana, máximo | errados: n, mediana, máximo |
| --- | --- | --- |
| 150 s | 3; 0,065 px; 0,124 px | 3; 777,92 px; 1259,76 px |
| 180 s | 4; 0,236 px; 0,321 px | 3; 1277,01 px; 1462,90 px |

Os 3 indefinidos têm o mesmo motivo, "sem cursor". Os outros motivos previstos em C3, C4, C6 e C7
não ocorreram.

Os erros errados estão em 155,9 s (1259,76 px), 172,7 s (620,06 px), 178,2 s (777,92 px), 183,3 s
(1277,01 px), 188,1 s (891,99 px) e 195,3 s (1462,90 px). A mediana do conjunto (0,32 px) passa
em C9, mas C9 também exige nenhum erro > 5 px, e esse ponto falha.

### Veredito de C9

- Mediana dos 13 definidos: 0,32 px (passa o limite de 1 px).
- Definidos com erro > 5 px: 6 (falha).
- **Aceite não atingido.** Nas duas janelas, o limite de erro > 5 px falha separadamente.
- Pela regra C10, a rodada para no mr. tabs. A C1 sai desta onda.

### Comparação com `dx_a` (C8)

O método mudou o `dx_a` em 7 dos 13 definidos. Em 5 deles o `dx_a` estava certo ou quase (erro de
0,009 a 0,236 px) e o método o trocou por um candidato `k·P` errado. Em 2 ele mudou um `dx_a`
errado:

- 206,1 s: `dx_a` tinha erro de 690,31 px; o método deu 0,31 px (correção).
- 172,7 s: `dx_a` tinha erro de 778,94 px; o método deu 620,06 px (melhorou, ainda errado).
- 155,9; 178,2; 183,3; 188,1 e 195,3 s: `dx_a` tinha erro de 0,009 a 0,236 px; o método deu
  778 a 1463 px (piorou).

Nos 6 definidos em que o método ficou igual ao `dx_a`, o palpite escolheu `k = 0`.

### Suspeita de C12, conferida com os números

A suspeita de C12 vale para 155,9 s, e os números confirmam o que a folha mostrava:

- `s_antes = 1298,5 px`: o compasso sob o cursor no quadro de antes (a folha mostrava ~1298).
- `barras_depois` contém 1061,5 px: é o compasso sob o cursor no quadro de depois (a folha
  mostrava ~1062). Ele não foi para o início da linha.
- O método usou `s_depois = 63,0 px`. Esse valor está na lista de barras e é um dos rótulos que
  C12 já apontava como coluna que não é barra (63). Ele também é o início da linha, então o erro
  vem das duas causas de C12 juntas.
- Com `s_depois = 1061,5 px`, `dx_cursor` daria −237 px, igual ao `dx_mao` (−236,7 px). O método
  não tem como saber disso, e C4 não se sustenta.

A frase de C12 "não vale para saltos pequenos" é verdadeira só em parte. Os erros errados não são
só de saltos pequenos: 172,7 s (−1355 px) e 195,3 s (−562 px) também erram. E 178,4 s (−224 px) e
195,5 s (−228 px) acertam. O que os números sustentam é que o palpite pelo cursor não reduz o erro
grande de forma confiável, e que ele estraga saltos que o `dx_a` já acertava.

### O que não foi feito e por quê

- **Janela 210 s:** não concluiu. A pasta `mrtabs_w210/` existe e está vazia.
- **Kenneth:** não medido (C10: a rodada parou no mr. tabs).
- **Leonardo:** não medido (C10).
- **`_estatisticas.py`:** não executado. Ele escreve `resumo.json` dentro de `rodada0153/` no
  principal, lê `kenneth_*` e `mrtabs_w210/metodo.json` (ausentes) e falharia nesses arquivos. As
  contas acima foram feitas direto dos dois `metodo.json`, sem escrita no principal.
- **Parada do container:** a sessão principal registrou a parada depois do veredito. Às 17:14 de
  16/10, `podman ps` ainda mostrava `chorinho-chorinho-run-03e3a1fe8c44` ativo (criado 17:00,
  comando `python /app/data/...`). Esta tarefa não parou nem mexeu nele. Pode ser a remedida da
  janela 210 s. Precisa de conferência pela sessão principal.

### Encerramento

Rodada 0153 encerrada com aceite não atingido. A C1 (rolagem em saltos) sai desta onda. Não há
leonardo nem kenneth nesta rodada. A entrada correspondente em `ESTADO.md` (tabela de não repetir,
AGENTS.md, regra 11) não entra neste commit, porque a tarefa foi só este documento. Fica para a
sessão principal.

## Não repetir

- **(a)** Palpite pelo cursor com a premissa de C4 (o compasso sob o cursor vai ao início da linha)
  não vale no mr. tabs. Em 155,9 s o compasso fica em 1061,5 px no quadro de depois.
- **(b)** Escolher o candidato `c_k` mais próximo de `dx_cursor` não corrige alias de período. Nos
  saltos em que `dx_a` já acertava, a regra trocou por candidato errado (5 saltos). Corrigiu só um
  (206,1 s).
- **(c)** Qualquer nova tentativa de rolagem precisa de um critério que não dependa do cursor nem do
  número impresso, e esse critério precisa estar escrito antes de medir.

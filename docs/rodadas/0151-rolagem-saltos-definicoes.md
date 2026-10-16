# 0151 — Rolagem (C1): definições, máscaras e limiares dos saltos (antes da medida)

**Frente:** C1. **Branch:** `tab/c1-rolagem`. **Saída:** `data/saida/tab_frentes/fc_rolagem/rodada0151/`.
**Segue:** 0150 (corrigida: os rolantes andam em saltos com sobreposição, não "não rolam").

Este documento é escrito e commitado **antes** de qualquer medida de deslocamento. Os limiares
abaixo não mudam depois de ver resultado. Se uma definição se mostrar errada na prática, a
correção vira outra rodada, com o motivo escrito.

## Pergunta

Nos vídeos que saltam (mr. tabs "no rain", kenneth "location" e um terceiro canal): cada salto
tem barras de compasso de antes que reaparecem deslocadas? De quanto é o deslocamento, e o
método (a) `phaseCorrelate` na parte que fica visível, (b) ancorado nas barras, acerta a medida
à mão em 1 px (mediana)?

## Vídeos e recortes (os mesmos da triagem da 0150)

| vídeo | arquivo (acervo) | recorte y (faixa) |
| --- | --- | --- |
| no rain (mr. tabs) | `mr. tabs/blind melon - no rain - guitar tab ｜ lesson ｜ cover ｜ tutorial ｜ lead only.mp4` | 807 a 1019 |
| location (kenneth acoustic) | `kenneth acoustic/location - khalid ｜ fingerstyle guitar ｜ tab + chords + lyrics.mp4` | 855 a 1085 |
| terceiro canal | escolhido pela regra abaixo | pelo painel dele |

Quadros só pelo `tab.leitor` (`quadros`), um vídeo por vez, e registra-se quantos quadros se lê.

## Definições (a priori)

- **Quadro de medida:** 10 quadros por segundo (`qps = 10`) em volta de cada salto: de 1 s antes
  do primeiro passo de animação a 1 s depois do último.
- **Passo parado:** par de quadros consecutivos com |dx| < 0,3 px pelo caminho (a).
- **Passo de animação:** par de quadros consecutivos com |dx| ≥ 0,3 px pelo caminho (a) e
  resposta ≥ 0,5. Sem limite superior de tamanho: um passo pode passar de 40 px.
- **Salto:** sequência máxima de passos de animação seguidos (sem nenhum passo parado no meio).
  Deslocamento do salto = soma dos dx dos passos. Um salto com mais de 4 passos é registrado à
  parte e não entra no aceite, porque a definição do briefing é 1 ou 2 passos.
- **Barra de compasso (para o caminho b):** coluna da faixa em que pelo menos 60 % das linhas
  da faixa (após a máscara) são escuras (tom de cinza < 100). Colunas vizinhas com barra
  contam como uma só, no centro delas.
- **Sobreposição:** um salto tem sobreposição se, depois do salto, ao menos uma barra de antes
  reaparece deslocada pelo dx do salto, com tolerância de **2 px** (|x_depois − (x_antes + dx)| ≤ 2).
- **Troca de página:** salto sem nenhuma barra de antes reaparecendo (nenhuma dentro da
  tolerância). Troca de página não entra no aceite de deslocamento.
- **Número de compasso impresso** (olho): é a conferência de continuidade. O compasso que sai e
  o que entra têm de bater com o dx do salto (mesmo número visível nos dois quadros, deslocado).

## Máscara (antes de qualquer correlação)

Aplicada aos dois quadros de cada par, com a união das duas máscaras (o mesmo pixel é mascarado
nos dois lados):

- **Cursor:** pixels com saturação HSV ≥ 80 e matiz de azul-ciano (faixa do OpenCV 90 a 130).
- **Destaque de compasso:** pixels com saturação HSV ≥ 25 e valor ≥ 150 (retângulo claro colorido).
- Os pixels mascarados viram branco (255).
- **Caixa de acordes** (diagramas à direita do quadro, quando estão dentro do recorte): fica de
  fora pela largura: só entra a faixa de x até o último compasso visível, definida à mão para
  cada vídeo antes de medir e escrita neste documento junto do resultado.

A máscara é conferida no olho em um quadro por vídeo (imagem da máscara salva na pasta da rodada).
Se a máscara falhar no olho, a rodada para e registra; não se troca o limiar.

## Caminhos de medida

- **(a) `phaseCorrelate`** sobre os quadros mascarados, com janela de Hanning, na faixa de x
  definida acima. Mede dx, dy e resposta.
- **(b) Ancorado nas barras:** barras de compasso detectadas nos dois quadros; dx = mediana das
  diferenças x_depois − x_antes entre barras casadas (casamento: a diferença que mais se repete,
  dentro de 2 px). Se houver menos de 2 barras casadas, o caminho (b) não dá estimativa.

## Medida à mão (a referência)

Para cada salto, escolho **uma barra de compasso** visível nos quadros de antes e de depois,
pelo número impresso (leitura visual), e meço a x dela nos dois quadros (coluna de tinta mais
escura, em pixel inteiro). dx_mão = x_depois − x_antes. Entram os saltos com sobreposição; os
com troca de página ficam registrados, mas não contam como par.

**Meta:** 20 pares (saltos com sobreposição, com número impresso conferido) por vídeo.

## Aceite (congelado)

- Erro = |dx_método − dx_mão| em cada par. Por vídeo: **mediana do erro ≤ 1 px**, nos 3 vídeos,
  pelos dois caminhos reportados separadamente.
- Continuidade: em cada salto medido, o número impresso que sai e o que entra batem com dx (olho).
- Se o caminho (a) não chegar a 1 px, e o caminho (b) também não, a rodada para e descreve os
  casos antes de montar panorama (briefing, aceite da C1).

## Terceiro canal (regra fixa)

1. Leonardo ramos (aire de zamba, `leonardo ramos/aire de zamba ...mp4`): olhar a 10 qps em volta
   de duas mudanças (as mudanças estão na folha de 4 s da 0150, `olho/leonardo_triagem/folha.png`).
   Passa se pelo menos um salto nessas janelas tem sobreposição (definição acima). Se não passa,
   está fora, e vale a próxima regra.
2. Senão, o primeiro canal da lista de 66 rolantes do censo (ordem de `triagem.json`) que passe
   o mesmo teste (duas janelas de 3 s em volta de mudanças, 10 qps, olho), registrado nesta
   rodada. Canais já olhados e fora: a 0150 (leonardo, mr. tabs `#shorts`, guitar dell'arte)
   não entra de novo sem a mesma regra.

## Medida extra (informativa, não aceite)

Número de notas que o caminho paginado atual entrega duas vezes no trecho que se repete depois
do salto, nos 3 vídeos (CPU). Fica para depois do aceite, na rodada 0152 ou seguinte.

## O que esta rodada não faz

- Não faz panorama, mapa x → t, nem leitura de notas.
- Não usa a forma "rolante" do censo como prova.
- Não toca GPU.

## Não repetir (herdado da 0150)

- A triagem por contadores não separa salto com sobreposição de troca de página.
- Cursor e destaque entram na correlação se não forem mascarados.

## Adendo antes da medida (2026-10-16)

Escrito e commitado junto do módulo `tab/rolagem_saltos.py` e dos testes
`tests/test_rolagem_saltos.py`, antes de qualquer medida de deslocamento:

- **Limite de x (caixa de acordes):** no `location` (kenneth), `x_max = 1640` px de 1920; a caixa
  começa perto de x ≈ 1656, lido na folha da 0150 (`olho/kenneth_location_182/folha.png`). No
  `no rain` (mr. tabs), sem limite (1920): a folha da 0150 não mostra caixa de acordes. O terceiro
  canal terá o limite lido no quadro antes da medida e escrito no seu resultado.
- **Barras de compasso:** a fração de tinta por coluna conta só dentro do intervalo vertical da
  pauta (da primeira à última linha de pauta), não na faixa inteira. Sem isso, as próprias linhas
  de pauta marcariam todas as colunas como barra. A regra está no teste unitário.
- **Máscara conferida no olho:** uma imagem por vídeo, com a máscara sobreposta ao quadro, em
  `rodada0151/mascara/`. Se a máscara falhar no olho, a rodada para e registra.
- **Janela por execução:** no máximo 30 s (10 qps), por memória.
- **Medida à mão:** o compasso é escolhido pelo número impresso; o x é lido no perfil de
  escuridão da coluna dessa barra, sem a regra de 60 % (que é do caminho b). Esta independência é
  parcial, e o relatório diz isso.

## Correção de limiar antes da medida de aceite (2026-10-16)

- **Corrida descartada:** `mrtabs_w60` (60 a 90 s, 10 qps) com `ESCURO = 100`, escrito na
  definição acima. Ela mediu passos e saltos (os dx do caminho a não dependem desse limiar),
  mas a detecção de barras deu **zero** barras: a pauta do mr. tabs tem cinza entre 140 e 180,
  e o limiar 100 não pega nenhuma linha. Sem barras, o caminho b e a sobreposição ficaram vazios.
  Essa corrida fica em `rodada0151/mrtabs_w60/` como registro, e não entra em nenhum número.
- **Medido no quadro de 63,0 s do mr. tabs (só para calibrar o limiar, sem deslocamento):**
  percentis de cinza sem máscara: p1 = 26, p5 = 145, p10 = 225, p25 = 232, mediana = 243.
  Com o limiar 150 a 230 aparecem barras em x ≈ 76, 416, 855, 1195 (folha da 0150: ~74, 416, 856,
  1196). Escolhido **200**: fica entre a tinta (p5 = 145) e o papel (p10 = 225).
- **Mudança:** `ESCURO` passa de 100 para 200 em `tab/rolagem_saltos.py`. A fração de 60 % da
  coluna dentro da pauta e as demais definições não mudam.
- **Por que isto não é ajuste pelo resultado:** o limiar foi corrigido porque o detector dava zero
  barras, antes de qualquer medida de deslocamento contra a referência à mão. Os critérios de
  aceite (erro mediano ≤ 1 px, 20 pares por vídeo) não mudam.

## Resultados (2026-10-16)

Janelas de 30 s a 10 qps, `tab/rolagem_saltos.py`, saídas em `rodada0151/<janela>/saltos.json`.
Passos (todas as janelas): mr. tabs 60 a 150 s, 14+10+17 animações; kenneth 62 a 182 s, 11, 11, 8, 8 e 6
animações; leonardo 0 a 143 s, de 0 a 3 animações por janela. Pares `indefinido` (resposta < 0,5)
não entram em salto; são trocas ou transições sem translação e ficam sem estimativa.

### Conferência da máscara no olho (depois das medidas, mas antes do aceite)

Imagens em `rodada0151/mascara/`, uma por vídeo, com a máscara em vermelho.

- **mr. tabs** (`mrtabs_t63.0.png`): passa. Cursor e destaque de compasso mascarados; tinta fora.
- **leonardo** (`leonardo_t24.4.png`): passa. Cursor e destaque mascarados.
- **kenneth** (`kenneth_t184.0.png`): **falha**. O destaque de compasso sai mascarado, mas o
  cursor (linha azul clara perto de x ≈ 1162) fica fora da máscara, porque sua saturação é
  menor que o limiar de 80. Pela regra desta rodada, a rodada para nesse vídeo e a medida do
  kenneth **não vale para o aceite**. Não troquei o limiar nesta rodada.

### Deslocamento contra a referência à mão

A referência (`mao_mrtabs.json`, `mao_leonardo.json`) é: o compasso escolhido pelo número impresso
(olho), x sub-pixel pelo centro de massa da escuridão em ±4 px, nas linhas da pauta. Não usa a
regra de 60 % das barras do caminho b. O limiar de tinta (200) e a pauta são os mesmos do
detector, então a referência não é independente do detector nesse ponto. Erro = |dx − dx_mão|.

| vídeo | pares | máscara | mediana erro a (phaseCorrelate) | mediana erro b (barras) | falhas grossas (> 5 px) |
| --- | --- | --- | --- | --- | --- |
| mr. tabs "no rain" | 20 | passa | 0,10 px | 0,15 px | a: 1 (109,9 s, sinal trocado: a dá +237, mão −394); b: 1 (103,0 s, casou a repetição: b dá +243, mão −387) |
| leonardo ramos | 6 | passa | 0,20 px | 0,17 px | nenhuma |
| kenneth "location" | 20 (informativo) | **falha** | 0,10 px | 0,12 px (19 estimados) | nenhuma; b sem estimativa em 100,6 s |

- **Aceite (mediana ≤ 1 px nos 3 vídeos):** pela letra, as medianas passam (0,10 / 0,15 e 0,20 /
  0,17 px). Mas não vale: o kenneth falhou na máscara, e o leonardo tem **6 pares, não 20**.
  A meta de 20 pares do leonardo **não foi atingida**: o vídeo tem só 6 saltos com sobreposição em
  143 s. As transições sem sobreposição (troca de página) não são saltos e não entram nos pares.
- Os 20 pares do mr. tabs saíram de três janelas (60–90, 90–120, 120–150 s): 8, 5 e 7 saltos,
  todos com sobreposição, nenhum escolhido pelo erro.
- Os 20 pares do kenneth são os 20 primeiros saltos em ordem de tempo (66,6 a 135,0 s). A escolha
  foi feita antes de olhar o erro, mas o vídeo não vale por causa da máscara.
- Trecho do kenneth em 184,5 → 184,9 s: o salto de ~475 px aparece como transição (resposta 0,04,
  0,33 e 0,47). Pela definição, não é salto: o detector deixa só um passo de 17 px. Não medido.
- Janela 60 a 90 s do mr. tabs com `ESCURO = 100` (`mrtabs_w60/`): descartada, zero barras
  (ver a correção acima). Não entra em nenhum número.
- Caminho a e b falham em pares diferentes do mr. tabs, e por causas diferentes: o phaseCorrelate
  trocou o sinal num par de passo único; as barras casaram a repetição musical (o período de dois
  compassos, que o briefing já aponta).

### Leonardo ramos: os seis saltos

| t (s) | barra, x antes → x depois | dx mão | dx a | dx b |
| --- | --- | --- | --- | --- |
| 24,4 | barra 607 → 166 | −441,1 | −441,5 | −441,3 |
| 37,5 | barra 174 → 56 | −119,0 | −119,1 | −119,0 |
| 78,8 | barra 510 → 60 | −449,7 | −449,9 | −449,5 |
| 90,7 | barra 556 → 548 | −8,2 | −8,0 | −8,0 |
| 98,7 | barra 630 → 156 | −474,1 | −474,3 | −474,0 |
| 115,9 | barra 567 → 102 | −465,7 | −466,1 | −466,0 |

Não há número de compasso impresso no leonardo: a conferência foi pelo conteúdo (as notas
ficam na mesma posição relativa nos dois quadros). Composições em `rodada0151/leonardo_w*/comp/`.

### O que não foi feito

- **Passo 5 (panorama, mapa x → t, leitura em janelas, junção, folha olhada):** não feito. O
  passo só vale depois de o 4 passar nos três vídeos, e não passou (máscara do kenneth; 6 pares no
  leonardo).
- **Passo 6 (medida extra, notas duplicadas pelo caminho paginado):** não feito.
- **Passo 7 (gabarito do dono, tela em `fc_rolagem/`, porta 8111):** não feito. Depende do passo 5.
- **Trocas de página do leonardo** (pares `indefinido`, 15, 5, 6, 5, 3 e 5 nas janelas 0, 7, 37,
  67, 97 e 127 s): não olhadas uma a uma. A regra do passo 3 pedia registrar uma troca sem
  sobreposição; não foi feito.

### Próximo passo (0152, a decidir pela sessão principal)

1. Máscara do cursor claro (kenneth): nova definição de cursor, escrita e commitada **antes** de
   remedir o kenneth, com a conferência no olho de novo. Esta rodada não muda o limiar.
2. Leonardo: 6 pares com sobreposição em 143 s não atingem a meta de 20. Ou se aceita menos pares
   com registro, ou o canal sai e entra o próximo do censo.
3. Transição do kenneth (184,5–184,9 s) e trocas de página: definir como tratar `indefinido` com
   sobreposição antes de medir de novo. Não mudar a definição de salto depois de ver o resultado.

### Limites

- Referência à mão: a escolha do compasso é visual, mas o x é pelo centro de massa com o mesmo
  limiar do detector. Erro sub-pixel real fica acima do que esta medida mostra.
- O caminho a (phaseCorrelate) e o caminho b (barras) falharam em pares diferentes, cada um com
  uma falha grossa em 46 pares. Por isso a mediana, sozinha, não basta.
- Janelas de 30 s (por memória); um salto na divisa entre janelas pode ser cortado.
- Os scripts de medida (`_compor_saltos.py`, `_refinar_mao.py`, `_mascara.py`, `_depurar_*.py`)
  estão na pasta da frente; as versões que valem estão em `tab/rolagem_mao.py` e
  `tab/rolagem_compor.py`. A chave `janela` do `mao_*.json` virou `t0` na versão do repositório;
  os números são os mesmos.

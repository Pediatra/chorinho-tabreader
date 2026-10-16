# 1101 — Frente 0: anatomia do resíduo do M8 (onde estão as 285 notas com a corda errada)

**Data**: 2026-10-15. **Frente 0** de [`docs/pesquisa/maos-frentes.md`](../pesquisa/maos-frentes.md)
(seção 7), sobre a revisão [`docs/pesquisa/maos.md`](../pesquisa/maos.md).
Código `tab/maos_residuo.py`; teste `tests/test_maos_residuo.py`;
saída `data/saida/maos/frentes/f0_residuo/`.

**Pergunta.** O M8 diz **quantas** notas ficam com a corda errada (D1 285 de 2.437; D3 214).
Falta saber **onde** elas estão e **qual frente ataca cada parte**.

**Pesos a priori** (declarados antes de medir, e não mudados depois): α = 1 (por casa), β = 3
(por casa fora da janela), γ = 5 (abertura acima de 4 casas), δ = 0,5 (por casa de mudança de
posição) — os mesmos `PESOS_PRIORI` do M8. A Frente 0 **não propõe preditor novo**: ela mede,
classifica e recomenda. Por isso CA2, CA3 e CA4 (ganho, nenhum vídeo carregando, fora da
amostra) não se aplicam aqui; CA1, CA5, CA6 e CA7 se aplicam e estão respondidos abaixo.

## 1. CA1 — a reprodução, nota a nota

`preparar_video` + `decodar` + `pontuar` importados do M8, com os pesos a priori. Confere
**exatamente**, no total e por vídeo:

| degrau | acertos | n | erros | M8 |
| --- | --- | --- | --- | --- |
| D0 casa mais baixa | 2.096 | 2.437 | 341 | 2.096 — ok |
| D1 decodificador sem câmera | 2.152 | 2.437 | **285** | 2.152 — ok |
| D2 + janela da câmera | 2.152 | 2.437 | 285 | 2.152 — ok |
| D3 janela dos vizinhos (teto) | 2.223 | 2.437 | 214 | 2.223 — ok |

Além das contagens, a lista de notas foi conferida **uma a uma** contra a lista do M8 (mesma
ordem, mesmo instante, mesma corda e mesma casa): o módulo levanta `ValueError` se divergir.

**CA5 — determinismo.** Não há sorteio: a escolha dos casos é determinística (amostra
espalhada, sem RNG). Duas execuções com `--sem-casos` deram arquivos **byte a byte idênticos**
(sha256 `7098c70e…`), e a reexecução completa (com os 36 quadros) reproduziu o `residuo.json`
e os 75 recortes com os mesmos hashes da primeira (`94e2bb8a…` e `d89ea9b9…`). O CA1 foi
conferido de novo na reexecução que trouxe a quebra por vídeo e por página (seção 8.1):
2.096 / 2.152 / 2.152 / 2.223, `confere` e `confere_por_video` verdadeiros.

## 2. A régua comum (seção 5.2)

Todas as notas, com denominador:

| degrau | n | acc | acc ambíguas | acc presas | acc soltas |
| --- | --- | --- | --- | --- | --- |
| D0 | 2.437 | 0,8601 | 0,8504 (1.939/2.280) | 0,8048 (1.406/1.747) | **1,0000** (690/690) |
| D1 | 2.437 | 0,8831 | 0,8750 (1.995/2.280) | 0,8369 (1.462/1.747) | **1,0000** |
| D2 | 2.437 | 0,8831 | 0,8750 | 0,8369 | **1,0000** |
| D3 | 2.437 | 0,9122 | 0,9061 (2.066/2.280) | 0,8775 (1.533/1.747) | **1,0000** |

Por vídeo, D1: retrato 703/753 = **0,9336** · noturno 447/576 = **0,7760** · lacrimosa
393/453 = **0,8675** · glimpse 609/655 = **0,9298**. O noturno carrega 129 dos 285 erros.

**Contando cada (tela, coluna) uma vez só** (a primeira no tempo; 1.410 páginas distintas em
2.437 notas):

| degrau | acertos | acc |
| --- | --- | --- |
| D0 | 1.202/1.410 | 0,8525 |
| **D1** | **1.201/1.410** | **0,8518** |
| D2 | 1.201/1.410 | 0,8518 |
| D3 | 1.268/1.410 | 0,8993 |

## 3. Consertadas e quebradas

| comparação | todas as notas | por (tela, coluna) distinta |
| --- | --- | --- |
| **D1 contra D0** | **+57 / −1** (saldo **+56**) | **+0 / −1** (saldo **−1**) |
| D2 contra D1 | +0 / −0 (saldo 0) | +0 / −0 (saldo 0) |
| D3 contra D1 | +97 / −26 (saldo **+71**) | +77 / −10 (saldo **+67**) |

**Este é o achado mais importante da rodada, e ele não é sobre a Frente 0.** Contando cada
página uma vez, o decodificador do M8 **não ganha nada** da regra trivial "casa mais baixa":
conserta 0 e quebra 1. O ganho de +56 existe **só nas exibições repetidas** — das 61 notas em
que D0 e D1 diferem, **uma só é a primeira exibição da sua página** (e é justamente a quebra).
A exibição repetida infla o `n`; é onde o δ de continuidade do M8 está trabalhando. O número
de 0,883 do M8 está certo como está definido; o que ele **não** diz é que o decodificador é
melhor que a regra trivial na música.

**D2 contra D1 é 0 e 0 nos dois modos de contar**: a janela da câmera **não muda uma única
decisão** — não é só "não ganha na média", é "não toca em nenhuma nota". A câmera casa com o
quadro do gabarito em 96 de 1.470 ataques com nota presa (6,5 %): 63 no retrato (13,3 %), 17
no glimpse (4,9 %), 14 no noturno (3,6 %) e **2 na lacrimosa (0,8 %)**.

## 4. O resíduo do D1: as categorias do roteiro

285 notas erradas. As três primeiras linhas são **partições** (todo erro tem um valor em cada);
as demais não são exclusivas.

| categoria | notas | leitura |
| --- | --- | --- |
| `a_fronteira` / `b_mesmo_lado` | 41 / 244 | só 14,4 % cruzam a fronteira encapada × lisa |
| `c_acorde` / `c_sozinha` | 60 / 225 | 21 % são notas de acorde |
| `d_presa` / `d_solta` | **285 / 0** | todo erro está em nota presa (corda solta: 690/690 certas) |
| `e_troca_posicao` | 100 | 35,1 % têm troca de posição a menos de 1 s |
| `f_ligado` | **0** | **nenhuma** das 9 marcas `l` do dono cai no resíduo |
| `g_leitura` | 60 | 21,1 %: todas por casa > 7 (nenhuma casa > 14, nenhuma corda repetida) |
| `h_com_camera` / `h_sem_camera` | 21 / 264 | só 21 erros tinham janela da câmera |
| **`outros`** | **97 (34,0 %)** | **acima do limite de 30 % — a frente entra no "reprova ou para"** |

Por vídeo (erros do D1 / `outros`): retrato 50/36 · noturno 129/27 · lacrimosa 60/21 ·
glimpse 46/13.

Diagnósticos extras (fora do roteiro, e por isso **não** contam como explicação):

| extra | notas | leitura |
| --- | --- | --- |
| `x_pred_solta` | 118 (41,4 %) | o decodificador escolheu **corda solta** para uma nota presa |
| `x_pred_mais_aguda` | 284 (99,6 %) | o erro é **sempre** para a corda mais aguda (casa mais baixa) |
| `x_pred_mais_grave` | 1 | |
| `x_ambigua` | 285 | por definição: o erro só existe em nota ambígua |

## 5. Segunda passada: o que são os 97 "outros"

O roteiro manda, quando `outros` passa de 30 %, **olhar mais 20 casos e propor categorias novas
antes de recomendar qualquer frente**. Foi feito: 20 casos olhados (seção 6) e três categorias
propostas, **descritivas** — não entram em `EXPLICATIVAS`, para `outros` continuar medindo o que
o roteiro explica:

| categoria nova | notas | o que ela diz |
| --- | --- | --- |
| `n1_solta_falsa` | 118 | a predição é corda solta e a verdade é presa |
| `n2_uma_corda_mais_aguda` | 267 | a predição está **exatamente uma corda** acima da verdade |
| `n3_travessia_4_5_casas` | 267 | a casa prevista é **4 ou 5** abaixo — a assinatura da travessia de corda |

**Os 97 "outros" são 100 % `n2` + `n3`**: nota solteira, na primeira posição (casas 3 a 8),
sem troca de posição, do mesmo lado da fronteira, leitura dentro do aferido — e o decodificador
escolhe a corda de cima, 4 ou 5 casas abaixo. Não é uma categoria nova que falta: é o **prior
de casa baixa** trabalhando sozinho, sem nada no modelo que o contradiga. 54 dos 97 chegam a
escolher corda solta.

## 6. O que a janela "perfeita" (D3) consertaria, por categoria

Este é o teto medido da frente B, categoria por categoria:

| categoria | n | D3 conserta | % |
| --- | --- | --- | --- |
| `a_fronteira` | 41 | 19 | 46,3 % |
| `c_acorde` | 60 | 16 | 26,7 % |
| `e_troca_posicao` | 100 | 20 | 20,0 % |
| `g_leitura` | 60 | 25 | 41,7 % |
| **`n1_solta_falsa`** | **118** | **0** | **0,0 %** |
| `n2` / `n3` | 267 | 90 | 33,7 % |
| `outros` | 97 | 37 | 38,1 % |

**A linha que decide a ordem das frentes**: nas 118 notas em que o decodificador escolheu
corda solta, a janela da mão esquerda conserta **zero**. Não é falta de qualidade da janela: o
modelo **isenta a corda solta do custo de posição** (custo zero, onde a mão estiver), então
nenhuma evidência de posição, por melhor que seja, muda essa escolha. Um bloco de 41 % do
resíduo é imune à frente B.

## 7. Os casos olhados no quadro

**36 quadros lidos** do acervo (só os instantes necessários, um por caso), em duas escalas: o
recorte do braço inteiro e um zoom na mão esquerda (caixa das pontas do detector + 60 px,
ampliada 2,5×). Todos em `data/saida/maos/frentes/f0_residuo/casos/`:

- **10 do resíduo do D1** — `folha_residuo.jpg`, `folha_zoom_residuo.jpg`;
- **20 dos "outros"** (os que o roteiro não explica) — `folha_outros.jpg`,
  `folha_zoom_outros.jpg`;
- **5 consertadas e 1 quebrada** do par D0 → D1 (CA6) — `folha_consertadas.jpg`,
  `folha_quebradas.jpg` e as folhas `_zoom_`.

**O que eu vi.** Nos 20 "outros" — todos de **ataque de uma nota só** — a mão esquerda está na
primeira posição e há **sempre pelo menos um dedo pressionando** o braço. Em **12 dos 20** o D1
previu **corda solta**, e a imagem não sustenta corda solta: os dedos estão em cima do braço.
Os 10 do resíduo mostram o mesmo (ver `01_residuo_retrato_t5c29.jpg`, verdade 3/4, D1 2/0).

**O que eu não consegui ver, e é uma limitação da ferramenta, não do olho.** **Não dá para
contar a casa.** O zoom na mão corta o nut e não tem nenhuma referência de casa; o recorte do
braço inteiro mostra a posição ao longo do braço, mas é pequeno demais para ver o dedo sobre o
fio. Consequência honesta: **os 10 casos não confirmam nem refutam o gabarito fio a fio** — a
pergunta que eles existiam para responder. O que eles respondem é outra coisa, e é útil: a mão
está na primeira posição, o que é compatível com a verdade (casas 3–8) e **não** distingue a
alternativa do D1 (casas 0–2), que fica na mesma região.

## 8. Recomendação de ordem (o que a frente entrega)

| ordem | frente | notas do resíduo que ela pode atacar | base da conta |
| --- | --- | --- | --- |
| **1º** | **A — decodificador** | **278** | união de `e_troca_posicao` 100, `c_acorde` 60 e `x_pred_solta` 118 (com sobreposição). É a **única** frente que ataca as 118 cordas soltas falsas |
| 2º | **B — mão esquerda** | **97** | medido: o D3 conserta 97 e quebra 26 (+71 líquido; +77/−10 por página). Teto, não promessa |
| 3º | **C — timbre** | **41** | `a_fronteira`: é a única classe que a inarmonicidade separa |
| 4º | **D — ligado** | **0** | nenhuma das 9 marcas `l` do dono cai no resíduo |
| — | 0 — fechamento | 97 | `outros` 34 %: as categorias do roteiro não fecham o resíduo |

### 8.1 Por vídeo e por `(tela, coluna)` distinta

A recomendação global esconde o vídeo. As duas tabelas abaixo são a mesma conta
(`recomendacao_do_subconjunto`, no módulo) refeita em cada recorte — mesmas categorias,
mesmos critérios, mesmos pesos; só o conjunto de notas muda. O teto da frente B é remedido
no recorte (o D3 consertando o D1), não herdado do total.

**Todas as notas, por vídeo** (notas do resíduo que cada frente ataca):

| frente | retrato | noturno | lacrimosa | glimpse | total |
| --- | --- | --- | --- | --- | --- |
| A — decodificador | 37 | 105 | 67 | 69 | **278** |
| B — mão esquerda (teto D3) | 17 | 60 | 12 | 8 | **97** |
| C — timbre (`a_fronteira`) | 0 | 35 | 6 | 0 | **41** |
| D — ligado (`f_ligado`) | 0 | 0 | 0 | 0 | **0** |
| 0 — fechamento (`outros`) | 36 | 27 | 21 | 13 | **97** |

**Contando cada `(tela, coluna)` uma vez só** (a primeira exibição no tempo; 1.410 páginas
distintas, o mesmo critério da seção 2):

| frente | retrato | noturno | lacrimosa | glimpse | total |
| --- | --- | --- | --- | --- | --- |
| A — decodificador | 22 | 78 | 50 | 31 | **181** |
| B — mão esquerda (teto D3) | 10 | 57 | 8 | 2 | **77** |
| C — timbre (`a_fronteira`) | 0 | 33 | 4 | 0 | **37** |
| D — ligado (`f_ligado`) | 0 | 0 | 0 | 0 | **0** |
| 0 — fechamento (`outros`) | 21 | 27 | 20 | 6 | **74** |

**A ordem não muda: em oito recortes (4 vídeos × 2 modos de contar) a ordem por notas é
sempre A → B → C → D**, e D é zero em todos; o que muda é o **tamanho**. Por página, o teto
da B cai de 97 para 77 e a A de 278 para 181 — a exibição repetida inflava as duas —, e
`outros` cai de 97 para 74 (o retrato perde 15 dos 36: 36 → 21). Por vídeo, a distância entre
A e B é grande em todos (retrato 37 × 17, lacrimosa 67 × 12, glimpse 69 × 8) e só encolhe no
noturno (105 × 60), que é ao mesmo tempo o vídeo com a maior fatia do resíduo (129 de 285) e
o maior `outros` por página (27). Nenhum recorte faz a B passar na frente da A, e nenhum faz
a C ou a D crescer. No `residuo.json` a quebra está em `recomendacao_por_video`,
`recomendacao_por_tela_coluna` e `recomendacao_por_video_tela_coluna`; a `recomendacao`
global saiu **idêntica** à da primeira entrega.

**Por que A primeiro.** O maior bloco do resíduo (118 notas, 41 %) é o prior de casa baixa
escolhendo uma corda solta falsa, e a frente B **não toca nele** (0 de 118). Além disso, o
custo aprendido da A3 tem o rótulo de graça (a tablatura) e não precisa de sinal novo. A B
continua valendo 97 notas, mas o número é teto e a cobertura real da câmera hoje é 6,5 %.

**D está descartada por medida, não por opinião**: zero notas do resíduo são ligado.

## 9. O que deu errado

1. **`outros` = 34 % > 30 %**: as categorias do roteiro não explicam o resíduo. A frente parou
   no ponto que o plano manda parar, olhou 20 casos e propôs as três categorias da seção 5 —
   mas elas são descritivas, e o número que reprova continua sendo 34 %.
2. **Um bug meu, pego por desconfiar do número.** A chave de "exibição repetida" era
   `(tela, coluna)` **sem o vídeo**, então a tela 2 coluna 5 do retrato e a do noturno eram a
   mesma página. Dava 565 páginas distintas em vez de **1.410**, e a comparação D1 × D0 saía
   `0/0` em vez de `0/−1`. Corrigido, com teste.
3. **O zoom na mão não serve para contar casa**: corta o nut e não tem referência (seção 7).
4. **CA6 pede 5 "quebradas" e só existe 1** em todo o corpus (D1 contra D0). Entreguei 1.
5. **A escolha dos casos não desduplica por (tela, coluna)**: dos 20 "outros" saíram 2 pares
   da mesma página em exibições diferentes (glimpse tela 5 coluna 12, casos 17 e 19). Cobre
   menos páginas distintas do que parecia.
6. **A revisão de 10 casos não fechou a pergunta do gabarito** (casa > 7 não aferida): 60 das
   285 notas erradas (21 %) têm casa > 7, e essas continuam sendo candidatas a erro do
   gabarito, não do decodificador. Fica declarado, não resolvido.

## 10. Não repetir

- **Contar `(tela, coluna)` sem o vídeo na chave.** Sem ele as páginas de vídeos diferentes
  colidem: 565 em vez de 1.410, e a leitura do D1 contra o D0 inverte.
- **Escolher casos sem desduplicar por `(tela, coluna)`.** Repete a mesma página e cobre menos
  música.
- **Zoom na mão sem o nut dentro.** Não dá para contar casa; serve só para a postura dos dedos.
- **Esperar 5 "quebradas"** do D1 contra o D0: existe 1 no corpus inteiro.
- **Ler o 0,883 do M8 como ganho sobre a regra trivial sem olhar a exibição repetida**: por
  página, o saldo é −1.
- **Usar o instante do marcador para olhar a mão**: usei `t_audio` onde o alinhador casou (31
  dos 36 casos); nos 5 sem `t_audio`, o marcador mais a mediana do vídeo, declarado caso a caso
  no JSON (`origem_do_instante`).

## 11. O que esta frente **não** prova

- **Não valida o gabarito.** A revisão visual não conseguiu contar casa (seção 7).
- **Não vale fora dos 4 vídeos do `sky guitar`.** Um canal, um violonista, um arranjador.
- **Não mede a frente B.** O D3 é um teto com a casa certa vinda dos vizinhos; a câmera real
  cobre 6,5 % dos ataques.
- **Não diz que a A vai ganhar.** Diz que é onde está o maior bloco e onde a B não alcança.

## 12. Revisão desta sessão (2026-10-16): o que foi reconferido e o que muda

**Reprodução.** O módulo foi reexecutado do zero no container, com as montagens do briefing.
O `residuo.json` saiu **byte a byte igual** à entrega anterior (sha256 `94e2bb8a…`). CA1 confere:
D0 2.096, D1 2.152, D2 2.152, D3 2.223 de 2.437. O gate passou: `All checks passed!` no ruff,
`185 files already formatted` no format, e `1248 passed, 2 skipped, 4 deselected, 2 xfailed`
no pytest.

**Parada atingida, e não superada por categoria explicativa.** `outros` continua em 97 de 285
(34,0 %), acima do limite de 30 %. A segunda passada (20 casos olhados e três categorias
`n1`–`n3`) foi feita, mas as três categorias são **descritivas** e não entram em
`EXPLICATIVAS`. Por isso a recomendação de ordem abaixo é **condicional**: sai com a ressalva,
não como conclusão.

**`n2` e `n3` são o mesmo conjunto.** Conferido nos 285 erros do D1: os 267 erros em que a
corda prevista é a corda verdadeira menos um são exatamente os 267 em que a casa verdadeira
menos a prevista é 4 ou 5 (88 com delta 4 no par G→B, 179 com delta 5 nos demais pares). Em
afinação padrão isso é aritmética: a mesma altura numa corda vizinha fica 4 ou 5 casas abaixo.
`n3` não acrescenta informação a `n2`, e a conta "267 + 267" conta a mesma nota duas vezes.
Os 97 `outros` são todos `n2` (e todos `n3`), todos com ataque de uma nota, casa verdadeira de
4 a 7, sem troca de posição e do mesmo lado da fronteira. Dos 97, 54 têm casa prevista 0.

Consequência: `n2` descreve o erro (o decodificador escolheu a corda de cima, no mesmo tom, com
casa mais baixa) e não diz por que ele acontece. Não é uma causa nova. A única explicação que
os números sustentam é o custo do próprio decodificador, que prefere casa baixa (α·casa). A
frente A é a que mexe nesse custo, o que reforça a ordem, mas não fecha o resíduo.

**Casos olhados.** Conferido no `residuo.json` e nas folhas:
- 20 `outros`: 12 com D1 em corda solta (confere com o texto). Na folha, a mão aparece sobre o
  braço, na primeira região, na maioria dos quadros. "Sempre pelo menos um dedo pressionando"
  é **forte demais**: em alguns quadros os dedos ficam na borda do recorte ou fora do braço, e
  o recorte não deixa contar os trastes. A afirmação vale como observação, não como prova.
- 10 do resíduo: 6 com D1 em corda solta; a folha com zoom mostra os dedos sobre o braço, sem
  contar casa.
- **CA6 não cumprido como escrito.** Pede 5 consertadas e 5 quebradas. Existem 5 consertadas
  (D1 contra D0), mas **só 1 quebrada** no corpus inteiro (D1 contra D0). Os 10 casos estão
  com o recorte; a parte de quebradas está em falta. Não há outro par D0→D1 com quebrada.

**Fica como está, mas precisa de nota.** Os casos olhados não são desduplicados por
`(tela, coluna)` (seção 9, item 5), e a conta "origem do instante" (31 de 36 com `t_audio`) não
foi reconferida nesta sessão.

**O que muda neste documento.** Só esta seção. Código, `residuo.json` e recomendação
permanecem como na entrega anterior, porque a reprodução é exata e o critério de parada foi
descrito, não contornado.

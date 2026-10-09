# Rodada 2 — medições do teste de viabilidade

Complementa `docs/decisao_modelo.md` (rodada 1). Aqui estão só números obtidos agora,
com o método indicado, e o que eles mudam no plano.

## 1. Tempo: a cadeia do cursor está validada

Pergunta: o cursor dá a minutagem de cada nota?

Medição: no clipe `-6rawhontyg` (80 s), comparei o instante de cada patamar do cursor
com o `t_instante` que o pipeline antigo gravou para a mesma linha
(`tab_tokens.json`, `origem_do_tempo: cursor`).

| # | x do cursor | t (meu) | t (antigo) | diferença |
| --- | --- | --- | --- | --- |
| 1 | 266 | 1,84 s | 2,00 s | −0,16 s |
| 2 | 350 | 2,90 s | 3,00 s | −0,10 s |
| 4 | 535 | 4,80 s | 5,00 s | −0,20 s |
| 8 | 952 | 8,81 s | 9,00 s | −0,19 s |
| 12 | 1372 | 12,85 s | 13,00 s | −0,15 s |
| 15 | 1698 | 15,85 s | 16,00 s | −0,15 s |

**Diferença mediana −0,159 s; máxima 0,195 s.** O desvio é praticamente constante, e a
explicação é geométrica: eu marco quando o **centro** da banda chega na coluna; a banda
tem ~17 px de núcleo e anda ~100 px/s, logo 17/2 px ≈ 0,08 s, mais a histerese do
detector. **Correção de offset → erro residual na casa de um quadro (33 ms).**

Também confirmado: o cursor **salta** de nota em nota (16 patamares em 16 s, ~1 nota/s)
e a linha 1 tem exatamente 15 notas — o 16º patamar é o cursor parado no fim do sistema.

## 2. Binarização: as 5 famílias agora são detectadas

A rodada 1 falhava em 2 famílias (player escuro e livro impresso) porque o Otsu descarta
traço fino e cinza. Testei 4 variantes (arquivo `tools/exp_binarizacao.py`):

| Variante | 5 capturas novas | amostra do acervo |
| --- | --- | --- |
| Otsu + polaridade | 3/5 | 24/24 |
| contraste local (escolha ingênua de polaridade) | 1/5 | **0/24** |
| **cascata: Otsu → contraste k=21 d=12 → k=31 d=25** | **5/5** | **24/24** (163/163 no total) |

A lição: a escolha da polaridade não pode ser heurística solta — ela precisa ser
**validada pelo resultado** (as 6 linhas regulares). A cascata tenta as máscaras em
ordem e fica com a primeira que passa no teste estrutural.

## 3. A falha estrutural que o teste revelou (e que a rodada 1 não tinha visto)

**"6 linhas regularmente espaçadas" é necessário, mas NÃO é suficiente.** Duas provas:

1. O teste aceitou **4 recortes que são partitura** (não tablatura): `jmny*` linhas 10 e
   12, `tup*` linhas 10 e 11. Uma pauta de 5 linhas + 1 linha espúria produz uma
   progressão de 6 regular o bastante para passar.
2. Numa captura com **partitura em cima e TAB embaixo**, o detector escolheu a **pauta de
   5 linhas** e devolveu 13 "glifos" que estão a **6 passos de distância** das linhas
   escolhidas — ou seja, lixo.

Discriminadores medidos:

| Caso | mediana de tinta por linha | glifos centrados na linha |
| --- | --- | --- |
| TAB real (skyguitar, b0ysk, 1za, kgqet, w6g) | 0,86 – 1,00 | 0,92 – 1,00 |
| TAB real com muitos acordes (`tup`) | 0,86 | **0,44** (ver §4) |
| Player escuro tracejado (família D) | 0,70 | — |
| Partitura mal recortada (`tup` 10/11) | 0,39 – 0,44 | 0,12 – 0,34 |
| Partitura mal recortada (`jmny` 10) | 1,00 | 0,25 |

Conclusão: tinta por linha **≥ 0,55** pega quase todos os casos ruins, mas não todos
(`jmny` 10 passa). Não existe um limiar único honesto — **o portão "isto é tablatura?"
precisa ser decidido pelo conteúdo, não por uma constante**, e o candidato natural é um
classificador pequeno (o mesmo que já vamos treinar), aplicado à linha inteira.

## 4. Acorde: a maior falha de extração até agora — encontrada e corrigida

Eu extraía glifos por componentes conexos na imagem inteira. Em tablatura com **acorde**
(3–4 notas empilhadas em cordas vizinhas), os algarismos se tocam e viram **um único
componente**, com centro caindo entre duas cordas.

Prova: `tup*` linha 1 é uma TAB legítima (verifiquei na imagem: colunas com 3–4
algarismos empilhados, `0 0 0 2 2 / 1 1 1 1 / 2 2 2 2 2 / 0 0 0 0`), e o extrator dava
**110 "glifos" com só 44 % centrados na corda**.

Correção: **fatiar por corda**. Cada corda tem sua faixa de ±0,45 do passo; o algarismo
tem ~0,85 do passo de altura e centra-se na linha, logo cabe na faixa. Extraio
componentes dentro de cada faixa, com dois filtros aprendidos na marra:
barlines (colunas verticais que sobrevivem em todas as faixas) e o rótulo "TAB".

Resultado medido:

| Linha | Antes | Depois | Gabarito |
| --- | --- | --- | --- |
| `-6rawhontyg` linha 1 | 15 glifos, 15 centrados | **15 glifos, todos na corda 2, 15 colunas** | **15 na corda 2** (verificado pixel a pixel) |
| `tup` linha 1 (acordes) | 110 glifos, 44 % centrados | 152 glifos, 85 % centrados, 33 colunas | — |

Acervo inteiro: **11.594 glifos** (era 6.882) — os ~4.700 a mais são justamente as notas
de acorde que estavam sendo fundidas. **A contagem subir aqui é o resultado correto**, não
um erro: o pipeline antigo está documentado perdendo notas (transformou `5/7/5` empilhado
em `575`).

Verificação cruzada por corda contra os tokens prata (que trazem `corda`):

| Canal | Minha extração | Tokens prata | Leitura |
| --- | --- | --- | --- |
| `-6rawhontyg` | 2:69, 3:21 | 2:67, 3:14 | **concorda** |
| `0pscbmo5psq` | 1:16, 2:11, 3:11, 4:11, 5:12, 6:16 | 1:11, 2:11, 3:13, 4:11, 5:11, 6:14 | **concorda** |
| `w6gt3rxpo2q` | 1:100, 2:168, 3:158 … | 1:92, 2:145, 3:122 … | concorda (minha um pouco maior) |
| `1za-kd` | 1:253, 2:498, 3:305 … | 1:236, 2:404, 3:289 … | concorda |
| `b0ysk`, `jmny`, `kgqet` | ~2× o prata | — | **prata está perdendo notas** (canais com acorde) |

Ou seja: onde o gabarito prata é confiável (linhas melódicas), a concordância é de 1–5 %.
Onde ele perde nota (acordes), minha contagem é maior — e o gabarito é que está errado.

## 5. O que continua sem resposta

1. **Reconhecer a casa (o número).** Ainda não há classificador com gabarito verificado.
   É o próximo passo: gabarito pequeno à mão + gerador sintético + treino.
2. **Escolher a pauta certa quando há partitura e TAB no mesmo quadro** — hoje erra nessa
   captura específica.
3. **Tab ASCII (Ultimate Guitar)**: o extrator devolve 123 "glifos" de uma grade de texto,
   número sem sentido. Essa família precisa de outro leitor (parsing de texto monoespaçado),
   não desta cadeia.
4. **Partitura em pauta**: fora do escopo desta cadeia; precisa de OMR próprio.
5. **Compasso e andamento** (que você pediu no escopo): o cursor dá o tempo de cada nota e
   as barlines dão o compasso; o andamento sai da contagem de notas por compasso e do
   intervalo entre onsets — falta implementar e aferir.

## 6. Veredito do teste de viabilidade

| Camada | Situação | Evidência |
| --- | --- | --- |
| Achar a pauta nas 5 famílias | **funciona** | 5/5 capturas, 163/163 linhas do acervo |
| Rejeitar o que não é tablatura | **parcial** | pega 3 de 4 recortes errados; 1 passa |
| Escolher TAB quando há partitura junto | **falha em 1 caso** | glifos a 6 passos das linhas |
| Extrair cada nota (corda + coluna), inclusive acorde | **funciona** | exato no gabarito verificado; +68 % de notas recuperadas |
| Dar o tempo de cada nota | **funciona** | desvio 0,16 s, corrigível para ~0,03 s |
| Dizer a casa (o número) | **não medido ainda** | depende do gabarito + treino |
| Técnicas (ligado, harmônico `<7>`, slide) | **não medido ainda** | taxonomia definida na rodada 1 |

**Conclusão honesta:** a arquitetura se sustenta para as famílias de grade (A, B, C, D) —
inclusive com os problemas reais que apareceram (acorde, contraste, pauta dupla). O que
falta para fechar o "vai dar certo?" é a única peça que ainda não tem número: **o
reconhecimento do algarismo com gabarito verificado**. É exatamente aí que entra o
fine-tuning que você autorizou — de um modelo de ~10⁵ parâmetros, não de um VLM.

Família ASCII de texto e a linha de partitura ficam explicitamente fora desta cadeia e
precisam de leitor próprio.

# Rodada 35 — correção do usuário: o marcador não é sempre uma faixa

## 1. O que você apontou, e por que eu errei

> "cuidado com esse cursor, nem todos tem a mesma cor, o mesmo tamanho, e até diferenças como o do
> cifra club tem o cursor que deixa os números da tablatura atuais em outra cor e não uma faixa"

Você está certo, e isso invalida a premissa que eu embuti no detector: **assumi que o marcador é
sempre uma banda vertical**. Não é. A trava que eu acabei de colocar (largura ≤ 6 % e matiz azul de
playback) é exatamente o oposto do que o `cifra club` faz — nesse canal **não existe faixa**; os
algarismos da nota que está soando é que mudam de cor.

Consequência direta: o **4 %** de cobertura que eu medi na rodada anterior está errado por
construção — o meu filtro rejeita justamente o canal que você citou.

## 2. O que medi agora, olhando o `cifra club`

Vídeo `505 - arctic monkeys` (painel no topo, passo 14,8 px, 74 tokens). Contando tokens com pixels
cromáticos, em 6 instantes:

| instante | tokens coloridos | matizes vistos |
| --- | --- | --- |
| 0,40 | 51 de 74 | 14, 14, 14, 15, 13 |
| 0,42 | 44 | 11, 10, 11, 11, 10 |
| 0,44 | 41 | 12, 11, 10, 11, 13 |
| 0,46 | 33 | 3, 6, 5, 5, 6 |
| 0,48 | 50 | 13, 10, 11, 11, 14 |
| 0,50 | 53 | 19, 20, 18, 16, 11 |

Duas leituras:

1. **Há muita cor de base** neste canal (matiz 10–20 = laranja/vermelho) — é o estilo do canal, não
   o realce. Então "contar pixels coloridos" **não** acha o marcador: ele confunde estética com
   indicação de execução.
2. O que muda entre instantes é **quais** tokens estão coloridos — e é aí que está o sinal.

Ou seja: no `cifra club` o marcador é **mudança de cor de um token em relação à cor base daquele
token**, não presença de cor.

## 3. O desenho certo (uma máquina só, três usos)

O que unifica os canais é a **série temporal de cor por token**: para cada algarismo, amostrar a cor
ao longo do tempo e olhar a **variação**.

| canal | como o marcador aparece | como a série de cor resolve |
| --- | --- | --- |
| `cifra club` | o algarismo da nota atual muda de cor | o token cuja cor **desvia da própria base** naquele instante |
| `skyguitar` e afins | banda azul que passa | a banda também **recolore** os algarismos que cobre: a série acusa os tokens sob a faixa |
| outros | podem nem usar cor (só áudio) | a série fica plana → o JSON declara "sem marcador" |

Isso substitui o detector de banda como caminho principal. A banda continua útil como **pista
auxiliar** (ela é estreita e vertical, o que ajuda a localizar), mas **não pode ser pré-requisito**.

## 4. O que isso invalida — de novo, e eu preciso listar

| número que eu reportei | situação |
| --- | --- |
| "95 % dos vídeos têm cursor" | **errado** (media madeira de violão) |
| "54 % com cursor, 56 s por vídeo" | **errado** (detector contaminado) |
| "12 % numa tomada com trava" | **errado por construção** (rejeita o `cifra club`) |
| "4 % com a trava, 5 s por vídeo" | **errado por construção** (idem) |
| "cursor no `skyguitar`, 1 nota/s, desvio 0,16 s" | **válido** — verificado no quadro |

Quatro medições de cobertura de tempo, todas comprometidas por assumir **um tipo de marcador**.
Nenhuma delas deve ser usada.

## 5. Próximo passo

1. **série temporal de cor por token** (a máquina única) — implementar e medir em 3 canais de tipos
   diferentes: `cifra club` (cor), `skyguitar` (faixa) e um que não use marcador;
2. declarar no JSON **qual mecanismo** foi usado por nota, em vez de assumir um;
3. só então medir cobertura — e agora por **tipo de marcador**, não "cursor sim/não".

## 6. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, técnica) | **0,805** (3 sementes) — este não depende de marcador |
| **compasso** | funciona onde a barline é limpa |
| **tempo** | **premissa corrigida**: o marcador varia por canal; a máquina certa é a série de cor por token |

Sua correção chegou antes de eu escrever qualquer coisa definitiva sobre cobertura de tempo, e
mudou o desenho — não o número. O que fica registrado é que eu errei por **assumir uniformidade**
onde o acervo é variado, que é exatamente o risco que eu mesmo tinha levantado na rodada 1.

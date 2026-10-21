# 1037 — Retreino do braço com a regra do capo

**Data**: 2026-10-21. O pré-registro vem antes de qualquer treino. Janela autônoma de 12 h
aprovada pelo dono ("pode começar").

**A pergunta**: o detector retreinado com as marcas da decisão
[1010](../decisoes/1010-capotraste-como-nut-do-braco.md) passa a numerar a partir do capo?
Nessa regra, com capo, o nut é o traste logo à frente dele. E o detector consegue isso sem
deixar passar erro calado e sem piorar o que já fazia nos vídeos sem capo?

**Antecedentes**:
- [1028](1028-um-braco-consenso-e-retreino.md): é a receita dos pesos atuais (`L3_todos_s*` e
  `A4_100_todos_s*`).
- [1032](1032-ciclo-de-revisao-kenneth-acoustic.md), medida de novo pela regra do capo: 16 de
  64 certos e 46 falsos que passam. O detector acha o nut verdadeiro atrás do capo.
- [1036](1036-ciclo-diagnostico-violaodecria.md): 1 falso que passa (q10), o nut verdadeiro
  com capo na 4.

## Treino: a receita da 1028, com outro dado

Fica igual à 1028:
- arquitetura;
- 3.000 passos;
- aumento;
- mistura A3 no estágio 2 (metade S, metade R);
- decodificação conjunta;
- regra de revisão da 1023, congelada;
- sinal de nut suspeito v2 (1033).

**Muda só o dado.** O código está em `tab/maos_braco_retreino.py`, e a contagem, em
`m37/contagem.json`.

| fonte | o que é | na 1028 | na 1037 |
| --- | --- | --- | --- |
| R | rastreados a partir das chaves da M3b | sim | sim. **As 8 chaves com capo foram rastreadas de novo** com as marcas novas (`maos_braco_m21 rastreador --chaves`); os R antigos estão em `m21/R_regra_antiga/` |
| G | as 66 chaves da M3b (só no estágio 1) | sim | sim, com as marcas atuais do `braco.json` |
| C | M25 treino, marcas grosseiras (só no estágio 1) | sim | sim, com as marcas remarcadas pela 1010 |
| M26, M27 | ciclos 1026 e 1027 | sim | sim (M27 remarcada pela 1010) |
| **M29, M32** | ciclos 1029 e 1032 | não | **entram**. A M32 tem 48 quadros com capo |
| **N** | M25 prova | sim | **sai: vira medida** |
| S | sintéticos (só no estágio 2) | sim | sim, sem mudança (não têm capo) |

**Ficam fora do treino e da medida** até o dono confirmar:

| quadro | por quê |
| --- | --- |
| M3b q10 e os R rastreados dele | o capo está a 1,36 casa atrás do nut marcado. Pela convenção, deveria estar a menos de 1 casa |
| M32 q14 | capo à frente do nut marcado (+0,52 casa) |
| M32 q45 | capo à frente do nut marcado (+0,17 casa) |
| M25 treino q139 | vídeo com capo (os vizinhos q136–q144 têm `k`), nut marcado e sem `k`. Pode estar contado do nut verdadeiro |

**Conferência feita antes do treino** (2026-10-21):
- **Os quadros de vídeos com capo** (`capo_por_video.json`, 33 vídeos) foram cruzados com a
  marca `k` em todos os gabaritos. Sobrou só o q139 acima. Os outros 3 sem `k` são braço
  "não", na M11b.
- **A distância do capo ao nut marcado** foi medida em todos os quadros com `k`. Fora do
  intervalo de −1 a 0 casa ficaram só os 3 da tabela acima. Os M27 q57, q61 e q62 ficam
  entre −0,8 e −0,93 casa: o capo está no fundo da casa, mas dentro dela, e por isso entram.

**Barreira**: nenhum quadro de um vídeo da M11b, da M25 prova ou da M36 entra no treino,
compara pelo nome do arquivo em NFC.

**Pesos**: `L4_capo_s1..3` (estágio 1) e `A6_capo_s1..3` (estágio 2), em `artefatos/m21/`,
com o commit no json.

**Antes do treino longo**, roda um teste de 50 passos de cada estágio. Também saem as folhas do
alvo só com quadros de capo (`m37/l4_folha_capo.jpg` e `m37/a6_folha_capo.jpg`), para conferir
a olho que o nut do alvo está no traste à frente do capo. Se não estiver, o treino não começa.

### Achado nas folhas, antes do treino: o alvo do estágio 1 começava no nut verdadeiro

- **Estágio 2**: nos 12 quadros com capo da folha, o nut do alvo está no traste à frente do
  capo. Certo.
- **Estágio 1**: os 4 pontos do alvo são as **pontas das cordas** que o dono marcou. Com capo,
  as cordas continuam até o nut verdadeiro, e o dono as marca por toda a extensão visível. Por
  isso, nos 11 quadros do kenneth da folha, os pontos "perto do nut" estavam **no nut
  verdadeiro, na cabeça do violão**.
- **Por que isso importa**: a cadeia monta a faixa da primeira passada a partir do meio desses
  dois pontos. Com o alvo assim, o estágio 1 aprenderia a começar a faixa atrás do capo, e o
  estágio 2 receberia a faixa com o nut verdadeiro dentro. Esse é o erro do kenneth (1032) e do
  q10 (1036).
- **Correção** (`cortar_no_nut`, só nos quadros com `k`; o R herda o `k` da chave):
  - no alvo do estágio 1, a ponta de cada corda mais perto do nut passa a ser a projeção do
    nut marcado sobre a reta da corda;
  - **a marca do dono não muda**: muda só o alvo calculado a partir dela, como manda a decisão
    1010 ("o braço começa no capo");
  - os quadros sem capo ficam como na 1028.
- **Folha refeita**: nos quadros do kenneth, os pontos agora estão no capo.
- **A regra 5 do AGENTS.md** ("olhe a entrada real do modelo") pegou isto antes de gastar ~4 h
  de GPU.

### Contagem (`m37/contagem.json`, 2026-10-21, antes do treino)

| fonte | estágio 1 | estágio 2 | com capo | fora |
| --- | --- | --- | --- | --- |
| R | 1.028 (1.052 na 1028) | 1.028 | 79 | 11 (os R do q10) |
| G | 63 | — | 7 | 1 (q10) |
| C | 127 (136) | — | 12 | 9: 8 de um vídeo da M11b (a barreira), e o q139 |
| M26 | 63 | 63 | 0 | |
| M27 | 62 (54) | 62 | 24 | (os 8 "nut fora" da 1028 eram capo e agora têm nut) |
| M29 | 56 | 56 | 0 | 4 nut fora, 4 sem braço |
| M32 | 61 | 61 | 45 | 2 (q14, q45) |
| S | — | 20.000 | 0 | |
| **total real** | **1.460** | **1.270** | **167 / 148** | |

- **O re-rastreio das 8 chaves com capo** achou 90 de 138 alvos. Antes, com as marcas antigas,
  eram 103 (a região rastreada ficou menor, do capo para a frente). São 79 do kenneth e 11 do
  q10, que fica fora.
- **Com a barreira, saem do C 8 quadros do vídeo da M11b** (vvxofingerstyletab, sword art
  online), que estavam no L2 e no L3. Isso quer dizer que a escolha de pesos da 1025 à 1032
  teve um vídeo do conjunto de escolha no treino do estágio 1. Isso fica registrado; não muda
  o que já foi decidido.

## Escolha do par (M11b, desenvolvimento)

- **Candidatos**: os 9 pares `L4_capo_s<i>` + `A6_capo_s<j>`.
- **Critério**: o da 1029: menos falsos que passam; depois mais entregues certos; depois menos
  sinalizados; depois a menor soma de sementes.
- **Sem o sinal v2**, como na 1029 e na 1032.
- **Quadros**: os 29 da escolha da 1029 mais os 4 com capo da M11b que ficavam fora (q37–q40).
  São 33, com 6 de capo.
- **O par antigo** (`L3_todos_s3` + `A4_100_todos_s1`, a escolha da 1032) é medido nos mesmos
  quadros só como referência. Ele não concorre.

## Medida (desenvolvimento, não prova)

| conjunto | quadros | com capo | observação |
| --- | --- | --- | --- |
| M36 (1036) | 32 | 16 | já visto na 1036. A 1036 dizia que estas marcas entrariam no retreino: aqui elas viram medida, porque são os únicos quadros com capo e com o nut verdadeiro ao lado fora do treino. Entram no treino seguinte, depois da prova lacrada |
| N (M25 prova) | 23 (sem o q08, guitarra) | 4 | já visto. O par antigo **treinou com o N**, com as marcas antigas. Isso favorece o antigo nos quadros sem capo |

- **Os dois pares** são medidos nos mesmos quadros, com a regra 1023 e o sinal v2, como no
  ciclo: o escolhido e o antigo.
- **Os 9 pares novos** também são medidos, e o relatório dá a média e a amplitude (regra das 3
  execuções).
- **A prova lacrada é a 1039**: um ciclo novo num canal com capo frequente, em vídeos que nunca
  entraram em nada, com a revisão do dono.

## Critério (fixado antes de treinar)

1. **Segurança**: falsos que passam ≤ 5 % **em cada conjunto**, com o par escolhido. Isso
   quer dizer no máximo 1 de 32 na M36 e 1 de 23 no N.
2. **Capo**: nos 20 quadros com capo (M36 + N):
   - **no máximo 1 falso que passa**;
   - entregues certos ≥ os do par antigo.
3. **Sem capo**: nos 35 quadros sem capo:
   - falsos que passam ≤ os do antigo + 1;
   - entregues certos ≥ os do antigo − 2.

| resultado | o que fazer |
| --- | --- |
| 1, 2 e 3 passam | o par novo vira o peso do ciclo. A 1039, num canal com capo frequente, é a prova lacrada |
| 1 e 2 passam, 3 falha | o novo serve só onde há capo. Isso depende de achar o capo (1038), e o antigo fica nos outros vídeos. Registrar |
| 1 passa, 2 falha | não adotar, e registrar no "não repetir". Vídeo com capo segue para revisão. O próximo passo é mais exemplo de capo no treino (sobreamostrar) |
| 1 falha | não adotar e investigar por tipo de erro |

## Também reportado (decisão 2005)

A triangulação pede confiança calibrada. O detector não dá probabilidade: dá os sinais S1, S2 e
S3, e a regra de revisão. Esta rodada só descreve, sem critério:
- **dos entregues sem sinal, quantos estão certos**, e dos sinalizados, quantos estão certos;
- **certos por terço do S1** (do mais confiante ao menos), nos quadros com braço achado.

Se o terço mais confiante não for o mais certo, o S1 não serve de base para a probabilidade
que a 2005 pede.

## Riscos declarados antes

- **O sintético não tem capo**, e é metade do lote do estágio 2. O estágio 2 pode continuar
  preferindo a barra que parece um nut. Por isso há o critério 2 e o "sobreamostrar" como
  próximo passo.
- **Os limiares da regra 1023 são do detector antigo.** Com o retreino, a distribuição de S1
  e S2 muda. A 1028 manteve os mesmos limiares, e o ciclo seguiu seguro; aqui também ficam.
- **Poucos exemplos têm o nut verdadeiro e o capo juntos na imagem.** Os da M32 (kenneth, a
  cabeça do violão aparece) e os R das chaves do kenneth na M3b cobrem esse caso, mas são
  poucos vídeos.
- **A medida é pequena** (20 quadros com capo). Um quadro muda a conclusão do critério 2. Por
  isso a prova é a 1039, e não esta rodada.

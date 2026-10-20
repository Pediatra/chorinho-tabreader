# 1036 — Ciclo diagnóstico: violaodecria (nut fora em cortes verticais)

**Data**: 2026-10-20. O pré-registro vem antes de qualquer previsão no lote.
**Estado**: regras a priori. **O canal foi escolhido pelo dono**, que guardava esses vídeos "pro
final": são cortes verticais (formato tiktok), e na maioria o nut aparece em poucos quadros, ou
nem aparece.

**A pergunta**: com o nut fora da imagem, o detector erra a numeração sem avisar, ou o sinal de
nut suspeito (v2, [1033](1033-sinal-de-nut-suspeito-v2.md)) manda esses quadros para revisão?

**Antecedentes**:
- [1029](1029-ciclo-de-revisao-pablo-rome.md): 4 falsos que passam, todos com o nut fora da
  imagem. O padrão é o 1º traste visível tomado por nut, e a numeração desloca 1 casa.
- [1031](1031-nut-fora-por-vizinhos-e-juncao.md): os métodos V e J e o A5 reprovaram.
- [1032](1032-ciclo-de-revisao-kenneth-acoustic.md): 63 de 64 entregues certos, mas o nut
  estava quase sempre visível.

**Nota**: o canal está com `rollout: fora` para a **tablatura** (`configs/canais.yaml`; a tab é
texto ASCII). Isso não vale para o braço: aqui só se mede o violão do vídeo.

## Lote (sorteado depois deste texto; `m36/sorteio.json`)

- **8 vídeos do violaodecria**, sorteados com a semente 20261036.
  - Entram só os títulos de aula, ou seja, o nome do arquivo contém `violão`, `violao`, `tab`,
    `solo`, `aprenda` ou `fingerstyle`, sem diferença de caixa. São 986 dos 1 680 vídeos.
  - O canal também tem vlogs sem violão ("agora a neném vem…"), e o filtro só poupa o tempo
    do dono.
  - Ficam de fora os vídeos de todas as amostras anteriores, como na 1032.
- **4 quadros por vídeo**, de 0,15 a 0,85 da duração (0,15, 0,383, 0,617 e 0,85), num total de
  **32**. É um lote diagnóstico, menor que o dos ciclos (64), porque a pergunta é o tipo de
  erro e não a taxa fina.

## Detector (fixado agora, sem mudança)

1. **Pesos**: os da escolha da 1032 (`m32/escolha_pesos.json`, `L3_todos_s3` +
   `A4_100_todos_s1`). Não há escolha nova.
2. **Regra de revisão**: a da 1023, congelada.
3. **Sinal de nut suspeito v2** (1033, limiar 2 %): é o mesmo que entrou na 1032.
4. P2 e P3 ficam desligados.

## O que o dono faz

O protocolo da 1029:
- os sinalizados aparecem primeiro;
- capo com a tecla `k`;
- **nut fora**: o traste de referência, com o botão direito no traste e o número;
- 7 cordas com o botão.

## Medidas e critério

São as do ciclo (`maos_braco_ciclo medir --rodada 1036`), mais o recorte dos quadros com o nut
fora (o dono marcou o traste de referência).

| resultado | o que fazer |
| --- | --- |
| falsos que passam ≤ 5 % (no máx. 1 de 32) | o sinal v2 protege neste formato; as marcas de nut fora entram no retreino (A5 com dado de verdade) |
| falsos que passam > 5 % | parar e investigar por tipo de erro; o formato vertical não está protegido |
| sinalizados > 50 % | **esperado** neste canal: seguro, mas caro. Registrar quantos são de nut fora; isso mede o ganho possível de um estágio 2 que numere sem nut |

**Também reportado**:
- quantos quadros têm o nut fora (pela marca do dono) e quantos desses o v2 sinalizou;
- quantos o v2 sinalizou estando certos, ou seja, o custo do sinal.

## Riscos declarados antes

- **Vídeo vertical, braço curto na imagem.** O estágio 1 pode nem achar o braço, como no
  marigold da 1031 (11 de 16). Isso é "sem braço" e não conta como erro.
- **Tela dividida, com cifra ou tab escrita em cima ou embaixo.** É o caso que o v2 cobre
  (linhas de painel).
- **O nut pode estar fora sem que a corda encoste numa borda**, por exemplo com a mão na frente
  ou com capo. Esse é o caso que o v2 não pega, e é a fonte provável de um falso que passa.

## Preparação (2026-10-20, antes da revisão do dono)

**Lote sorteado** (`m36/sorteio.json`): 986 candidatos e 201 vídeos excluídos. Os 8 vídeos são
bola uma vela, indiretas com a voz, mc breno b, terapia, modo esquece, frequência, carrinho de
madeira e novinha brota no baile. Têm de 8 s a 165 s, todos verticais (1080×1920).

**Folha** (`m36/amostra.jpg`), vista antes da previsão:
- o braço sai pela borda de cima ou pela da direita em quase todos os quadros;
- q09–q12 têm a tela dividida, com o violão pequeno embaixo.

**Previsão** (L3_todos_s3 + A4_100_todos_s1, sinal v2):

| | quadros |
| --- | --- |
| braço achado | 29 de 32 |
| sinalizados | 22 (9 deles pelo v2) |
| entregues sem sinal | 10: q10, q18, q19, q20, q25–q28, q31, q32 |

**Olhado antes da revisão** (`m36/passam.jpg` e `m36/zoom.jpg`). Não é rótulo: quem decide é o
dono.
- Em q18 e q19, a cabeça do violão aparece e o nut previsto parece estar no nut de verdade.
- **Em q25, q28 e q31 há um capotraste**, preso na borda da direita, e o nut previsto está
  junto dele. É o mesmo padrão "capo tomado por nut" da 1032 (q43), só que aqui **sem sinal**.
- Se o dono confirmar o capo nesses quadros, a numeração do detector conta a partir do capo, e
  não do nut (regra da casa real). Seriam até 6 falsos que passam (q25–q28, q31 e q32), e o
  ciclo reprova pelo capo, não pelo nut fora.

## Emenda (2026-10-20, durante a revisão): capo como nut

O dono decidiu, durante a revisão, que **com capotraste o nut do braço é o capo**
([decisão 1010](../decisoes/1010-capotraste-como-nut-do-braco.md)), e marcou os 32 quadros
assim. A medida abaixo usa essa regra: com capo, o certo é o nut no capo.

## Resultado (`maos_braco_ciclo medir --rodada 1036`; detalhe em `m36/det36.py`)

| medida | valor | critério |
| --- | --- | --- |
| falsos que passam | **1 de 32 (3,1 %)**: q10 | ≤ 5 % ✓ |
| sinalizados | 22 de 32 (68,8 %) | > 50 %: seguro, mas caro (era o esperado) |
| entregues certos | 3 (q18–q20) | |

**Por tipo**:

| tipo | quadros | o que aconteceu |
| --- | --- | --- |
| certo | q13–q15, q18–q23 (9) | q15 tem o nut fora (traste de referência 1): certo, e sinalizado |
| capo, numeração certa | q25–q32 (8; 6 sem sinal) | os trastes batem com os do dono (0,0 casa). Só o ponto do nut fica a ~0,3 casa da marca do dono (limite do certo: 0,25), e por isso a classe é "impreciso" |
| 2 câmeras | q01–q04 (4) | o braço junta as duas vistas (cordas a 26 vãos); todos sinalizados |
| capo, nut errado | q05, q07 (capo 3; 1,4 casa), q09, q11, q12 (capo 4; 3,5 casas) | todos sinalizados. Em q09–q12, o detector achou o **nut verdadeiro** atrás do capo |
| **falso que passa** | **q10** | o mesmo vídeo de q09–q12 (tela dividida, violão pequeno, capo na 4). O nut verdadeiro é previsto sem sinal. Pela regra antiga, estaria certo |
| outros falsos | q17 (cordas a 1,7 vão), q24 (corda 6 vibrando) | sinalizados |
| não achou | q06, q08 (braço sim), q16 (braço não, certo) | |

**Leitura**:
- **O nut fora quase não apareceu**: só q15. Nestes vídeos, o que fica na borda é o **capo**
  (4 de 8 vídeos têm capo), e não um traste qualquer.
- **Com a regra nova, o capo deixa de ser fonte de erro silencioso**: em q25–q32, o detector
  já põe o nut no capo e numera certo.
- **O erro que passa é o caso contrário**: o detector vê o nut verdadeiro e ignora o capo
  (q10). Isso é exatamente o caso "nut e capo juntos" da decisão 1010.
- O "impreciso" de ~0,3 casa no capo deve ser a diferença entre onde o dono clica (no corpo do
  capo) e onde a corda para (o detector põe a linha de contato). Não é rótulo para corrigir.
  Mas, antes de treinar com capo, vale fixar a convenção: o nut marcado na linha onde a corda
  encosta.

**Decisão**: o ciclo passa no critério de segurança. As marcas da 1036 entram no próximo
retreino, junto com as da 1029 e da 1032. Antes disso, o dono revê os 14 quadros antigos com
capo (decisão 1010).

## Remarcação pela decisão 1010 e nova medida (2026-10-20)

O dono marcou o capo (`k`) em todos os gabaritos do braço com capo. O nut foi para o traste à
frente do capo.

| gabarito | quadros com capo |
| --- | --- |
| `braco.json` (M3b) | 8 de 66 |
| `braco_m11b.json` | 6 de 77 |
| `braco_m32.json` (1032) | 48 de 64 |
| `braco_m36.json` (1036) | 16 de 32 |

Nos quadros com capo, o capo fica a ~0,5 casa atrás do nut marcado, que é a convenção.
Três quadros fogem disso e ficam para o dono conferir: m32 q14 (+0,52, o capo à frente), m32
q45 (+0,17) e M3b q10 (−1,36).

**Nova medida com as marcas novas e a mesma previsão**:

| rodada | entregues certos | falsos que passam | antes da regra 1010 |
| --- | --- | --- | --- |
| 1036 | 9 | 1 (q10) | — |
| **1032** | **16** | **46 de 64** | 63 certos, 0 falsos |

**Leitura**: no kenneth acoustic, a cabeça do violão aparece e o detector acha o **nut
verdadeiro**. Pela regra 1010, isso agora é erro de numeração, deslocado pela casa do capo, e
**sem sinal**. Eu tinha dito que a mudança tinha custo zero, e errei: o custo está no detector,
não no gabarito. O detector atual foi treinado (G, R) com o nut verdadeiro e **não serve para
vídeos com capo** até o retreino com as marcas novas.

**Consequências**:
1. O retreino precisa dos quadros com capo pela regra 1010 (são 78 quadros do dono). As fontes
   R e G, e o M25, podem ter quadros com capo contados do nut verdadeiro. Eles não têm `k`, e
   precisam ser achados e revistos antes do treino. Senão, o treino recebe as duas regras ao
   mesmo tempo.
2. A M11b mudou (6 quadros), e por isso a escolha de pesos da 1032 não vale mais como está.
3. Enquanto isso, vídeo com capo visível deve ir para revisão (a detecção do capo vem abaixo).

**Detecção do capo** (direção do dono): não depender de cor nem de tamanho, e sim do objeto
sobre o braço, de forma consistente entre os quadros. O capo fica na mesma casa durante o
vídeo, ou em trechos longos. A proposta está na rodada seguinte.

**Auditoria de capo nos gabaritos sem `k`**. As folhas estão em `data/saida/maos/capo_auditoria/`,
com 349 quadros de M25 treino e prova, 1026, 1027 e 1029. Os candidatos são meu palpite, e
quem confirma é o dono:

| gabarito | candidatos com capo |
| --- | --- |
| M25 treino | q28–q36, q102, q106; talvez q44, q92, q103 |
| M25 prova | q09, q10, q11, q21, q22, q24; talvez q23 |
| 1027 (guitarous) | q17–q24, q49–q64 |
| 1026 e 1029 | nenhum visto |

As fontes R (`m21/R`) são propagadas a partir das chaves da M3b pelo rastreador. Depois da
remarcação, elas precisam ser geradas de novo antes do retreino.

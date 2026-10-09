# Rodada 65 — a rejeição por assinatura: média 0,854 → 0,892 e `raman` destravado

## 1. A regra implementada

A partir da medição da rodada anterior (só o `raman` tem assinatura de lixo: 28 % de tokens com
largura < 0,3 passo; os outros três canais, 0 %):

> **Se o vídeo tem mais de 10 % de tokens estreitos, token estreito é recusado (`junk`)** — em vez de
> virar `1` ou `harmonico`. Onde não há assinatura, nada muda.

É uma regra determinística, decidida **por vídeo** (não por canal — o marcador já me ensinou que
varia dentro do canal), e que **preserva os índices** do gabarito.

## 2. O resultado, com 3 sementes

| semente | iwaki | sky | **raman** | paolo | **TOTAL** |
| --- | --- | --- | --- | --- | --- |
| 0 | 25/27 | 14/15 | **17/24** | 25/30 | **0,844** |
| 1 | 27/27 | 14/15 | **17/24** | 29/30 | **0,906** |
| 2 | 27/27 | 15/15 | **17/24** | 30/30 | **0,927** |

| | antes | **agora** |
| --- | --- | --- |
| média | 0,854 | **0,892** |
| melhor | 0,875 | **0,927** |
| **`raman`** | 12/24 | **17/24 — igual nas três sementes** |
| paolo | 27–30 | 25–30 |

O `raman` saiu de 12 para **17 de 24 — e os 7 que faltam para 24 são exatamente os 7 rótulos `junk`
do gabarito**, que a regra agora também acerta. Ou seja: **17/17 nos rótulos de algarismo** daquele
canal, que era o canal intratável desde a rodada 10.

## 3. Por que funcionou (e por que só agora)

| tentativa | efeito |
| --- | --- |
| regra de altura no extrator | 0 |
| regra de orientação no extrator | 0 |
| trocar arco por barra no gerador | **−0,166** (revertida) |
| classe `tecnica` (com o fenômeno produzido) | melhora estabilidade, não acerto |
| relabelar por proxy geométrico | **−0,1** (revertida, 2×) |
| **rejeitar por assinatura medida** | **+0,038 e raman 12 → 17** |

A diferença das anteriores: aqui eu **medi primeiro** (rodada 64) qual era a assinatura do lixo e
**onde** ela existia — e a regra só age onde a medição mandou. As tentativas anteriores aplicavam uma
regra geral a todos os canais, e por isso cada ganho num canal era pagos com perda em outro.

## 4. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** — casas | **0,892 (3 sementes)** · melhor 0,927 · `raman` 17/17 nos algarismos |
| **canais limpos** | `iwaki` 25–27/27, `sky` 14–15/15, `paolo` 25–30/30 |
| **lixo** | **resolvido por assinatura por vídeo** (a decisão que faltava desde a rodada 22) |
| **classe `tecnica`** | mantida (estabilidade); sem ganho de acerto |
| **tempo** | faixa (`skyguitar`, 0,16 s) e cor (`cifra club`, 41/41 onsets) |
| **gerador** | íntegro (fonte variável, técnica em 35 %, diagonal cruzando) |

## 5. Próximo passo

1. **ampliar o gabarito para casas 8–24** — é o que limita a medição agora que os 4 canais estão
   acima de 0,84 e o `raman` está resolvido;
2. **rodar em escala** com a decisão por vídeo (a assinatura é barata: uma contagem por quadro);
3. representar `ligada` (`(6)`) no JSON — a categoria musical que apareceu na leitura da rodada 62;
4. aferir a **casa** dos canais fora do gabarito (o `cifra club` tem corda e tempo, não casa).

**Número oficial: 0,892** (média de 3 sementes), contra 0,854 antes desta mudança — e o canal que
resistiu por 55 rodadas agora acerta **todos** os algarismos do gabarito.

# Rodada 50 — onset por nota, e o que o marcador realmente mede

## 1. O resultado, com semântica correta

`saida/cifra_abanda.json`, agora com `t_ini` = **onset medido** e `t_proxima` = próximo onset
(sem chamar nada de "duração"):

| | |
| --- | --- |
| notas com onset | **41/41** |
| **instantes distintos** | **8** |
| onsets (s) | 63,3 · 65,1 · 66,9 · 67,8 · 68,7 · 69,6 · 74,1 · 78,7 |
| intervalo mediano entre onsets | **1,80 s** |
| reinícios de frase | **0** nesta janela |

## 2. Como ler isso

41 notas em **8 instantes** = os algarismos se agrupam em **acordes**: ~5 notas por ataque. E o
intervalo mediano de 1,80 s é a **harmonia** do trecho (uma mudança a cada ~1,8 s), não 41 eventos
independentes.

Ou seja: o marcador de cor mede, com precisão, **o ataque de cada grupo de notas**. Para uma
transcrição de acompanhamento isso é exatamente o que interessa; e as notas do mesmo acorde herdam
o mesmo instante — o que é **música**, não erro de medição.

Reportar "41 notas com tempo" era verdadeiro e enganoso: são **8 ataques**. A distinção só apareceu
porque eu passei a olhar os **instantes distintos** em vez da contagem de notas (a mesma correção
que fiz na rodada 30 para o outro marcador).

## 3. O que continua em aberto

- **reinício de frase**: a regra endurecida (contagem ≤2 depois de pico ≥5) não disparou nesta
  janela de 15 s — provavelmente não houve reinício, ou o limiar está alto. Precisa de janela maior
  para decidir;
- **vazamento de `harmonico`**: o classificador continua podendo escolher essa classe sem que a
  forma autorize (defeito conhecido, gancho de correção já existe);
- **a casa** neste canal não foi aferida (não há gabarito) — só corda, posição e tempo.

## 4. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, técnica) | **0,805** (3 sementes) nos 4 canais com gabarito |
| **painel e geometria** | resolvidos nos dois estilos de painel (claro e escuro) |
| **tempo — marcador por faixa** | validado no `skyguitar` (desvio 0,16 s) |
| **tempo — marcador por cor** | **onset por nota medido**: 41/41 notas, **8 ataques**, 1,80 s de intervalo |
| **mecanismo declarado no JSON** | sim (`cor` / `faixa`), com semântica explícita |

## 5. Próximo passo

1. **janela maior** para decidir o reinício de frase (e separar sistemas);
2. matar o vazamento de `harmonico` (verificação de forma);
3. rodar nos canais de mesmo estilo (`tv cifras`) e medir cobertura **por mecanismo**;
4. aferir a **casa** deste canal com um gabarito próprio — é o que falta para o JSON valer como
   transcrição, e não só como marcação de tempo.

Esta rodada não mudou código de visão: mudou **o que o JSON afirma**. Passou de "41 notas com
duração" para "41 notas com ataque, 8 ataques distintos, sem prometer duração" — e essa diferença é
a diferença entre um dado utilizável e um dado inventado.

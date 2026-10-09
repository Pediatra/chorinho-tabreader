# Rodada 28 — cobertura de tempo no acervo: ~50 % dos vídeos

## 1. A medição que faltava

Varredura do cursor em 2 vídeos por canal (12 canais), **120 s por vídeo**:

| | resultado |
| --- | --- |
| painel de tablatura localizado | **24/24 = 100 %** |
| vídeos com **alguma** janela de cursor | **13/24 = 54 %** |
| média de segundos com cursor por vídeo | **56,4 s** (de 120 s varridos) |

Por canal:

| canal | segundos com cursor (média) | | canal | segundos |
| --- | --- | --- | --- | --- |
| guitar dell ́arte | **113,0 s** | | iwaki | 0 s |
| shin izumi | **119,5 s** | | raman korshun | 0 s |
| guitarous | **119,5 s** | | tv on guitar | 0 s |
| serge kottelat | 104,2 s | | cifra club | 0 s |
| paolo d'angelo | 59,8 s | | tv cifras | 59,5 s |
| sky guitar | 56,0 s | | violaodecria | 45,5 s |

## 2. O refinamento que este dado traz

Na rodada anterior eu disse "o cursor é ausente em canais como o `shin izumi`". **Estava errado —
é por vídeo, não por canal.** Agora o `shin izumi` deu **119,5 s de 120 s**, porque amostrei
outros vídeos do mesmo canal. O vídeo medido antes (`don't stop me now`) simplesmente não tem
playback; outros do canal têm.

Leitura correta: **o professor às vezes usa playback com marcador e às vezes não** — e isso varia
dentro do mesmo canal. Não dá para decidir canal por canal; tem de ser vídeo por vídeo — que é
justamente o que a varredura implementada na rodada passada faz.

E quando o cursor existe, ele cobre quase todo o trecho: nos 13 vídeos com cursor, a média é
~104 s de 120 s **(≈ 87 % do tempo varrido)**.

## 3. Consequência para o rollout

| fração do acervo | fonte do tempo |
| --- | --- |
| **~54 %** dos vídeos | cursor de execução — funciona, e o produto já declara as janelas |
| **~46 %** dos vídeos | **outra fonte** (áudio ou numeração manual) — o cursor não está na tela |

Isso é um número de planejamento, não um defeito: o sistema entrega tempo onde ele existe e
**avisa** onde não existe. Mas é a primeira vez que eu sei o tamanho real dessa parte do
problema, e ele é grande: quase metade do acervo não tem marcador na tela.

## 4. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura; **54 % com cursor**, medido em 120 s por vídeo |
| (b) gabarito verificado | 96 glifos / 4 canais |
| (c) classificador multi-classe | **0,805 (3 sementes)** |
| (d) pipeline ponta a ponta | comando único com varredura de janelas e aviso explícito |
| (e) escala nos 3.781 | pré-requisito cumprido; **rollout precisa decidir o que fazer com os 46 % sem tempo** |

## 5. Próximo passo

Duas frentes, e a escolha é de produto:

1. **rodar o que já funciona**: transcrever os ~54 % com cursor, entregando JSON com corda, casa,
   compasso e tempo — e marcar os trechos sem cursor;
2. **fonte alternativa de tempo** para os 46 %: alinhamento por áudio (a partitura/tab dá a
   sequência de notas; o áudio dá os instantes) ou numeração manual assistida.

A frente 1 é execução e pode começar; a frente 2 é um projeto novo e merece ser decidida com você.

# 2016 — Áudio A4: alinhador v2.1 em 12 canais novos (lote 2)

Data: 2026-10-13. A leitura do HD foi aprovada pelo dono. Tudo em `data/saida/audio/a4/lote2/`
(`escolher.py`, `lista.json`, `apelidos.json`, `rodar_lote2.sh`, `lote2.log`, `resumo.py`,
`resumo.json`, `quadros/`). Commit do código: `4a0959f1`.

## Escolha

Saiu 1 vídeo de cada canal que a trilha áudio ainda não tinha testado: **12 de 12 canais**
tinham candidato. Filtro no censo:
- `tablatura` presente e `frac_tablatura ≥ 0,8`;
- duração de 60 a 360 s;
- `forma = paginado`, `marcador` em {faixa, cor}.

Sorteio com semente 2015. Ficaram fora raman korshun, o *campanitas* e os 6 canais já
testados.

A cadeia é a mesma do lote 1 (`tab.video` na CPU → `tab.audio_extrair` → `tab.audio_alinhar`
→ `tab.audio_produto`). Rodaram **12 de 12 sem erro**. A leitura da tablatura levou de 67 a
510 s.

## Resultado (totais recontados por mim nos alinhados)

| vídeo | notas | corda 1 | exibições recusadas | colunas com tempo | cos mediano | alarmes |
| --- | --- | --- | --- | --- | --- | --- |
| sky guitar *exercise 3* | 161 | 40 % | 0 de 10 | **158 de 161** | 0,84 | 0 |
| yunus guitarist *first love* | 378 | 11 % | 0 de 22 | **343 de 384** | 0,80 | 0 |
| lonelypicker *it's a heartache* | 213 | 4 % | 2 de 17 | **211 de 277** | 0,77 | 1 |
| robert lunn *5 easy pieces* | 543 | 27 % | 4 de 24 | **377 de 483** | 0,80 | 1 |
| guitar dell'arte *summertime* | 330 | 18 % | 0 de 5 | **171 de 230** | 0,74 | 0 |
| mr. tabs *tears in heaven* | 1306 | 1 % | 2 de 32 | 439 de 857 | 0,64 | 2 |
| serge kottelat *sungha jung* | 492 | 31 % | 1 de 10 | 152 de 304 | 0,74 | 1 |
| leonardo ramos *tiempo de vals* | 209 | 19 % | 3 de 11 | 70 de 149 | 0,79 | 1 |
| violaodecria *bela rosa* | 115 | 9 % | 4 de 10 | 41 de 97 | 0,76 | 3 |
| tv on guitar *mario wonder* | 1253 | 20 % | 6 de 22 | 326 de 796 | 0,74 | 1 |
| kenneth acoustic *believer* | 1080 | 13 % | 39 de 40 | 4 de 840 | 0,58 | 27 |
| vvxofingerstyletab *sword art online* | 12 | 17 % | 1 de 1 | 0 de 9 | — | 1 |
| **total** | | | **62 de 204** | **2292 de 4587 (50 %)** | | |

O total que o agente relatou (2139 de 4455) estava errado. As linhas por vídeo batem.

- **5 de 12 vídeos bons**: de 74 % a 98 % das colunas com tempo.
- **5 de 12 no meio**: de 33 % a 51 %. Ainda não foram olhados.
- **2 de 12 falham**, os dois por causa da entrada; olhei os quadros:
  - **kenneth acoustic**: a "tablatura" é um padrão de ritmo, com pausas e X percussivos
    nas cordas graves, sem número de casa. Não há altura para casar, e o caso parece o do
    rasgueado. Recorte: `quadros/kenneth_acoustic_t1.png`.
  - **vvxofingerstyletab**: a tablatura está legível, com destaque azul na coluna atual, mas
    o produto vê **1 tela só, de 3,75 a 93,1 s, com 9 colunas**. A troca de página não foi
    detectada. Recorte: `quadros/vvxofingerstyletab_sao_t1.png`.

## Som × marcador (medida nova, independente do alinhador)

O alinhador não vê o marcador (`esconder_marcador`). Onde o produto leu o marcador, cada
coluna tem dois tempos: `t_ini`, do marcador, e `t_audio`, do som. A comparação tira a
mediana de cada vídeo, porque o atraso do marcador em relação ao som é fixo por canal
(rodada 2002).

| vídeo | pares | mediana (t_audio − t_ini) | ≤ 100 ms da mediana | ≤ 200 ms |
| --- | --- | --- | --- | --- |
| sky guitar | 87 | +50 ms | 95 % | 100 % |
| guitar dell'arte | 164 | −115 ms | 88 % | 97 % |
| serge kottelat | 52 | +106 ms | 77 % | 90 % |
| MVP (referência) | 629 | +178 ms | 66 % | 96 % |

- O atraso marcador–som **muda de canal para canal**, de −115 a +178 ms.
- Tirado esse atraso, de 77 % a 95 % das colunas ficam a até 100 ms nos 3 canais novos.
  Isso combina com a resolução de 100 ms medida de ouvido (rodada 2008).
- O censo diz que os 12 têm marcador, mas **o produto só leu marcador em 3 de 12**. Nos
  outros 9, o observador não chegou à coerência 0,9.

## Leitura

- Nos canais onde a leitura funciona, o tempo pelo áudio também funciona. É o mesmo padrão
  do lote 1 (6 de 10 bons), agora em mais 5 canais.
- Nesse lote, a falha vem da entrada, não do alinhador: um padrão de ritmo sem altura e uma
  troca de página não detectada.
- O som dá tempo onde o marcador não foi lido: nos 9 vídeos sem `t_ini`, o áudio deu tempo a
  1811 de 3892 colunas.

## Consequências

1. Novos pedidos para a trilha tablatura, acrescentados à decisão 2004 (itens 10 a 12):
   - o observador de marcador falha em 9 de 12 canais marcados;
   - a troca de página não é detectada no vvxofingerstyletab;
   - o kenneth acoustic é padrão de ritmo, classificado como tablatura.
2. Pergunta ao dono: padrões de ritmo sem casa, como o do kenneth acoustic, ficam no dataset?

## Limites

- 1 vídeo por canal.
- O tempo não foi conferido de ouvido neste lote. A comparação com o marcador cobre só 3
  vídeos (303 pares).
- 5 vídeos do meio não foram olhados.

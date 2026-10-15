# 3022 — fileira de vigas não corta mais o topo do recorte

Trilha partitura. Data: 2026-10-15.

## O problema

O dono viu, na conferência sem produto, que a parte de cima de 2 dos 3 recortes vinha
cortada:

- agua de beber P01a: 14 px acima da 1ª linha, com "II" e dedilhado perdidos;
- canon P06a: 1 px acima da 1ª linha, com as vigas das colcheias cortadas.

O normal é ter 70–80 px de folga acima da pauta.

## A causa

`candidatos_verticais` (`tab/partitura_recortes.py`) limita o recorte pela estrutura
horizontal mais próxima. A extensão de uma estrutura era medida da primeira à última
coluna com tinta. Uma fileira de vigas de colcheia separadas, na mesma altura, aparecia
então como uma linha longa. Medido nas estruturas que cortaram (`diag/topo_cortado/`):

| estrutura | cobertura (colunas com tinta / extensão) |
| --- | --- |
| borda do painel (agua) | 1,00 |
| 1ª linha da pauta (agua) | 0,94 |
| vigas acima da pauta (agua P01a) | 0,24 |
| vigas acima da pauta (canon P06a) | 0,32 |
| linha de pestana "III ——" (ólafur P04a) | ~0,55 |

## A mudança

`Estrutura` ganhou o campo `cobertura`. A estrutura só limita o recorte se cobrir pelo
menos `COBERTURA_MIN_VIZINHA = 0,6` da sua extensão. Com isso, linha de tablatura, borda de
painel e outra pauta continuam limitando o recorte; fileira de vigas e linha de pestana
deixam de limitar. Entraram 2 testes novos. A regra só tira limite, então a caixa só pode
crescer, e sempre até a margem de 7 entrelinhas.

## Medição da caixa

Refiz `processar_quadro` em todos os recortes gravados, com limiares de 0,5 a 0,8
(`diag/topo_cortado/medir.txt`). O código final dá exatamente o resultado simulado com
0,6 (`medir_codigo.txt`).

| grupo | recortes | caixa muda com 0,6 | com 0,8 |
| --- | --- | --- | --- |
| gabarito R01–R21 | 21 | 1 (R16: topo 722→711) | 5 |
| produtos (3 vídeos) | 19 | 0 | 6 |
| piloto sem produto | 162 | 40 | 46 |

O 0,6 foi escolhido porque deixa a pestana dentro do recorte e não mexe em nenhum produto.
Os recortes do gabarito estão gravados e não foram refeitos, então o número oficial da
cadeia não muda. Cinco recortes do gabarito (R14, R15, R17, R19, R21) já não se
reproduziam antes desta rodada: são de uma versão anterior do recorte.

## Medição da leitura (7 vídeos refeitos)

Refiz `paginar` e `ler --pasta` nos 7 vídeos cujo recorte mudou
(`diag/topo_cortado/comparar.txt`):

| recortes | eventos antes → depois | Audiveris ok |
| --- | --- | --- |
| caixa mudou (40) | 668 → 742 (+11%) | 30 → 30 |
| caixa igual (122) | 2.973 → 2.973 | 113 → 113 |

Os 122 recortes sem mudança deram exatamente a mesma leitura. Os maiores ganhos foram:

- agua P01a: 30 → 42;
- blackbird P01a: 23 → 34;
- mela P18a: 8 → 15.

Uma perda: athletic P04a caiu de 48 para 39. O recorte novo está certo (agora pega o
"B III" de cima), mas o Audiveris leu 4 notas a menos nos compassos 8 e 10, que têm
semicolcheias ligadas.

As 10 falhas do mela entre os recortes que mudaram continuam falhando. Elas vêm da faixa
amarela do cursor (rodada 3021), não do corte.

A conferência do dono (`diag/conferencia_sem_produto/itens.json`) foi refeita com os
recortes novos. A agua P01a passou a ter 68 notas e 10 pausas.

## Limites

- Mais eventos não quer dizer leitura certa. Sem gabarito, o acerto não está medido.
- A caixa do R16 do gabarito ficaria 11 px maior se o recorte fosse refeito. O recorte
  gravado continua valendo.

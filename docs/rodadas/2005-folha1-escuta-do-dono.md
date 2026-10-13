# 2005 — Áudio: folha 1, o primeiro gabarito de tempo do som (escuta do dono)

Data: 2026-10-13. Gabarito: `data/gold/audio/folha1.json` (gravado com aprovação do dono).
Ferramenta: `tab/audio_folha.py`; clipes e chave em `data/saida/audio/a2/folha/`.

## Pergunta ao dono

Em cada clipe de 4 s, uma coluna da tablatura fica dentro de uma caixa amarela e um clique
toca no instante que o alinhador (v2, rodada 2004) afirma. No instante do clique, começam
a soar as notas daquela coluna? Certo / errado / não sei. Os vídeos tocam servidos por
HTTP local (abrir o `index.html` pelo disco não toca no navegador do dono).

## Demo (antes da folha, 5 clipes do MVP com os ataques da régua do A1)

4 de 4 certos; o controle errado (+0,33 s) foi pego ("uns 500 ms").

## Folha 1 (26 clipes, semente 2001)

| categoria | clipes | certo | errado | não sei |
| --- | --- | --- | --- | --- |
| MVP: alinhador concorda com a régua (≤ 50 ms) | 4 | 4 | 0 | 0 |
| MVP: "falso" pela régua (> 200 ms dos ataques dela) | 3 | **3** | 0 | 0 |
| MVP: coluna sem par na régua | 4 | 2 | 2 | 0 |
| MVP: tela 12, coluna 25 (alinhador × régua) | 1 | 0 | 1 | 0 |
| sem marcador: iwaki (La Vie en Rose) | 4 | 3 | 0 | 1 |
| sem marcador: kimny (From This Place) | 4 | 3 | 1 | 0 |
| sem marcador: shin izumi (Room 335) | 4 | 2 | 0 | 2 |
| controles errados (iwaki, kimny) | 2 | 1* | 1 | 0 |

Leitura:

- **Os 3 "falsos" pela régua estavam certos**: o erro era da régua (ataque achado na
  janela do marcador), não do alinhador. A régua do A1 não é verdade.
- **O erro real do alinhador** está nas colunas que o marcador nunca acende: tela 2,
  colunas 17 e 18 ficaram "errado, adiantado". Hipótese a medir: não são ataques (nota
  ligada ou ornamento), e o alinhador as encaixa num ataque vizinho.
- **f13** (tela 9, coluna 9, exibição 0): o dono respondeu "certo" com a observação de que
  o clique cai numa nota real, mas a coluna 9 não é tocada ali (ritornelo: a 1ª vez da tela
  9 toca só 1–8). Registrado como **coluna errada** (confirmado pelo dono).
- **Tela 12, coluna 25**: "errado, cedo": ali a régua tinha razão.
- **Sem marcador: 8 certos, 1 errado, 3 não sei em 12**. Primeiro sinal de que o método
  funciona sem marcador; amostra pequena.
- *Controle do kimny (f03) inválido*: o clique deslocado (+0,5·T após a coluna 15) caiu no
  ataque da coluna 16, que o alinhador tinha recusado; o "certo" do dono está correto.
  Controle novo tem de evitar colunas vizinhas recusadas. O do iwaki foi pego.

## Consequências

1. A régua do A3 passa a ser o gabarito de escuta (`data/gold/audio/`), que cresce a cada
   folha; a régua do A1 fica só como diagnóstico.
2. Próximo conserto: colunas sem ataque (ligadura/ornamento) não podem receber tempo.

## Limites

26 clipes, um ouvinte; "não sei" em 3 de 12 dos vídeos sem marcador (shin izumi tem
notas rápidas).

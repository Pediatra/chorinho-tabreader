# 2008 — Áudio: folha 3 de comparação A/B, o tempo do áudio está a ~100 ms

Data: 2026-10-13. Gabarito: `data/gold/audio/folha3.json` (gravado com aprovação do dono).
Ferramenta: `tab/audio_folha.py comparar` (commit `2d22a63a`); clipes, pedidos e chave em
`data/saida/audio/a2/folha/` (`folha3/`, `folha3_pedidos.json`, `folha3_chave.json`).

## Pergunta

A folha 2 (rodada 2007) mostrou que a escuta de clique único não separa ~240 ms. Comparando
dois clipes, um com o clique do alinhador e outro deslocado, o ouvido do dono prefere o do
alinhador? A partir de quantos ms?

## Folha

- Itens: os 39 julgados "certo" nas folhas 1 e 2 (sem controle, sem o f13).
- 40 pares (p01–p40), semente 2003:
  - d ∈ {−200, −100, −50, +50, +100, +200} ms, 6 pares cada;
  - 4 pares de atenção com ±400 ms;
  - alinhador em A em 20 pares e em B nos outros 20.
- A e B usam a mesma janela de 4 s, centrada no instante do alinhador. Os quadros saem
  idênticos (0,0000 px de diferença), e a distância entre os cliques bate com d a ≤ 0,25 ms
  (3 pares medidos).
- Instrução do dono: marcou só o que teve certeza; "não sei" quando não deu para separar.

## Resultado

| \|d\| | escolheu o alinhador | escolheu o deslocado | não sei |
| --- | --- | --- | --- |
| 400 ms (atenção) | 3 | 1 (p21, inválido) | 0 |
| 200 ms | **10** | **0** | 2 |
| 100 ms | **9** | 2 | 1 |
| 50 ms | 3 | 2 | **7** |

- Os 5 comentários "as duas praticamente iguais, certas" caem em |d| ≤ 100 ms.
- Sinal das 4 escolhas do deslocado em |d| ≤ 100: +100, +50, −50, −100. Não há tendência de o
  alinhador marcar cedo nem tarde.

## Leitura

- **O tempo do alinhador está, em geral, a menos de ~100 ms do início do som** que o dono
  ouve: com 200 ms ele nunca preferiu o deslocado, e com 100 ms preferiu o alinhador em 9 de 11
  respostas.
- **50 ms é o limite da escuta neste formato** (7 de 12 "não sei"). Abaixo disso, a medição tem
  de vir de áudio sintético (o detector tem viés de −28 ms, rodada 2002), não do ouvido.
- As discordâncias que pesam são do shin izumi, que tem notas rápidas:
  - **p21** (atenção, −400 ms): o clique deslocado cai entre as colunas 13 (−731 ms) e 15
    (−174 ms), onde está a coluna 14, que o alinhador não afirmou. Provavelmente é uma nota
    real, como no f03. **Atenção inválida.**
  - **p24** (−100 ms): as vizinhas estão a −116 e +128 ms, e deslocar 100 ms quase cai
    na nota ao lado. **Ambíguo.**
  - p01 (+100 ms, shin): o dono preferiu o deslocado; as vizinhas estão a −267 e +232 ms.
    Fica como discordância real, uma só.

## Consequências

1. O `chorinho/audio@1` passa a declarar `afericao.nivel = "ms"` e `resolucao_escuta_ms =
   100` (`tab/audio_produto.py`; decisão 2003 atualizada).
2. **Não repetir**: par de comparação ou controle cujo deslocamento cai a menos de |d| + 50 ms
   de uma coluna vizinha, inclusive das não afirmadas. Em música rápida, o clique deslocado
   cai em outra nota.
3. Precisão abaixo de ~50 ms: só com áudio sintético de resposta conhecida.

## Limites

Um ouvinte; 12 pares por |d|; o shin izumi tem poucas exibições aceitas e notas densas.

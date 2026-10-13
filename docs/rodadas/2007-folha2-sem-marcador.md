# 2007 — Áudio: folha 2, só vídeos sem marcador (e o limite da escuta)

Data: 2026-10-13. Gabarito: `data/gold/audio/folha2.json` (gravado com aprovação do dono).
Ferramenta: `tab/audio_folha.py` (commit `592ea597`); clipes, pedidos e chave em
`data/saida/audio/a2/folha/` (`folha2/`, `folha2_pedidos.json`, `folha2_chave.json`).

## Pergunta

Nos três vídeos sem marcador (iwaki *La Vie en Rose*, kimny *From This Place*, shin izumi
*Room 335*), o tempo que o alinhador v2 (rodada 2004) afirma cai nas notas? A folha 1 só
tinha 12 clipes desses vídeos.

## Folha

- 9 colunas afirmadas por vídeo, **uma por faixa de tempo** (o intervalo dos `t_audio` do
  vídeo dividido em 9), sorteio com semente 2002; nenhuma coluna da folha 1.
- 3 controles (um por vídeo), com a regra nova depois do f03: clique no **meio** entre as
  colunas c e c+1, consecutivas e **ambas afirmadas** (sem recusada entre elas),
  t(c+1) − t(c) ≥ 0,40 s, e nenhum pico de fluxo espectral a menos de 80 ms do clique.
  Quadros dos controles conferidos: caixa na coluna certa nos 3.
- 30 clipes embaralhados (g01–g30); a página não mostra a categoria.

## Resultado

| vídeo | afirmadas: certo | não sei | errado | controle |
| --- | --- | --- | --- | --- |
| iwaki | 9 de 9 | 0 | 0 | ouvido "certo" (g21, 244 ms das notas) |
| kimny | 7 de 9 | 2 | 0 | ouvido "certo" (g20, 226 ms) |
| shin izumi | 7 de 9 | 2 | 0 | ouvido "certo" (g14, 238 ms) |
| **total** | **23 de 27** | **4** | **0** | **0 de 3 detectados** |

## Leitura

- **Os controles não foram detectados.** Um clique a ~230–245 ms de duas notas, longe de
  qualquer ataque, soou "certo" nos 3. Somando a folha 1: controles válidos a essa distância
  detectados **1 de 4** (f15, +235 ms, "um pouco adiantado"); a demo pegou +330 ms.
- Portanto, neste formato (clipe de 4 s, clique único), "certo" quer dizer **nota certa**:
  o clique não pulou para a coluna vizinha (~450 ms nestes vídeos). **Não** certifica tempo
  a ±50 ms. Com essa ressalva: **0 errados em 27** nos vídeos sem marcador.
- O mesmo vale, retroativamente, para os "certos" da folha 1 (rodada 2005): a escuta
  separou o erro de ~1 coluna, não o de ~0,2 s.
- Amostra concentrada no shin izumi: 23 de 42 exibições recusadas pelo alinhador; 3 dos
  10 clipes dele (2 afirmadas + controle) caem em 73–75 s, a única região com colunas
  restantes naquela faixa.

## Consequências

1. O gabarito de escuta mede **coluna certa**; precisão fina pede outro formato.
2. Próximo formato (proposto e aceito pelo dono, ainda não feito): **comparação A/B**: o mesmo
   trecho duas vezes, uma com o clique do alinhador e outra deslocada (50, 100, 200 ms,
   para os dois lados, ordem sorteada); a pergunta é qual cai mais junto da nota. Mede a
   resolução da escuta e o erro do alinhador ao mesmo tempo.
3. **Não repetir**: tratar "certo" em folha de clique único como precisão de tempo.

## Limites

Um ouvinte; 30 clipes; 3 controles, todos no mesmo deslocamento (~0,24 s).

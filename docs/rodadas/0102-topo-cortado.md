# 0102 — Topo cortado: o arco da corda 1 sai do recorte do produto? (F0.2)

Frente 0 de `docs/pesquisa/tablatura-frentes.md`, seção 7 (F0.2). Branch `tab/f0-regua-tecnica`.
Código: `tab/tecnica_topo.py`, testes `tests/test_tecnica_topo.py`.
Saída: `data/saida/tab_frentes/f0_tecnica/topo.json` (SHA-256
`588b2733da9b9b4529121b54daefd047571e21ce15b63ba7eece43338c11a32e`), recortes em
`topo_recortes/`, folhas em `folhas_topo/`.

**Resultado: não conclusivo. F0.2 fechada assim** (decisão 3 da sessão principal,
2026-10-16). A medida de tinta não separa arco de texto e tem um erro de polaridade. Não há
número válido de marcas da corda 1 cortadas. Detalhes abaixo. Nenhum limiar novo será
escolhido para esta medida: o próximo passo, se houver, é outra frente com detector de arco
pré-registrado.

## Pergunta

Para cada marca do dono que inclui a corda 1 (ou símbolo acima dela), a tinta fica inteira,
cortada ou fora do recorte que o modelo do produto vê?

## Parâmetros (escritos antes de medir)

- **Topo visível do produto**: `max(y do topo do painel, y da corda 1 − 2,5 passos)`. É a janela
  de `tab.detector_tab.normalizar_sistema` (2,5 passos acima da corda 1, e o painel como limite).
- **Tinta**: pixel mais escuro que a mediana do quadro menos 60 níveis, depois de inverter o
  quadro se o fundo for escuro (mediana < 128), como o modelo faz.
- **Acima**: tinta na faixa de 2 passos acima do topo visível, nas colunas da marca (`x0` a `x1`).
- **Dentro**: tinta do topo visível até a corda mais baixa da marca, mais 0,5 passo, nas colunas.
- **Classes**: `inteira` (tinta só dentro), `cortada` (dos dois lados), `fora` (só acima),
  `sem_tinta`. Mínimo de 3 pixels para contar.
- **Denominador**: marcas com corda 1 em `cordas`, nas telas com painel lido (todas as 113).

## Resultado bruto (o que o código deu, não válido, ver "Por que não vale")

| fonte | marcas com corda 1 | inteira | cortada | fora | sem tinta |
| --- | --- | --- | --- | --- | --- |
| EOB | 19 | 9 | 10 | 0 | 0 |
| FTP | 22 | 15 | 7 | 0 | 0 |
| LVR | 3 | 3 | 0 | 0 | 0 |
| R335 | 28 | 8 | 20 | 0 | 0 |
| T82 | 41 | 25 | 16 | 0 | 0 |
| **total** | **113** | **60** | **53** | **0** | **0** |

Sem painel: nenhuma tela. Se o número fosse válido, 53 de 113 (47 %) estariam cortadas, bem
acima do limite de 5 % do plano. **Não tire conclusão dele.**

## Por que não vale

1. **Texto acima da tab entra como tinta.** Olhei a folha de 12 casos legíveis
   (`folhas_topo/folha_cortadas_12.png`). Em 10 deles a "tinta acima" é texto: letra `C`
   (EOB t1 r11, EOB t3 r5), `G` (EOB t4 r10), `Fmaj7` (EOB t5 r17, t6 r4), `maj7` (EOB t5 r18,
   t6 r5, t6 r10, t7 r0, t7 r5). Nenhum mostra arco cortado. A pegadinha do plano ("letra e nome
   de acorde parecem arco") acontece de fato.
2. **Erro de polaridade.** Em quadro de fundo escuro (mediana 114, FTP t5), a faixa de caixa
   branca uniforme (cinza 249) acima do painel vira "tinta", porque a inversão é global. FTP t5 r2
   e r3 aparecem como recortes em branco liso com 943 e 1312 pixels "acima" (`topo.json`). Isso é
   bug do método, não tinta.
3. **Não há detector de arco.** O método só conta pixels. A forma do arco (largura, espessura,
   curvatura) não entra. Sem isso não dá para separar arco de texto.

Não corrigi o método depois de ver o resultado: uma variante escolhida agora vale só como
diagnóstico (plano, seção 9, e regra de congelamento da seção 10, item 6).

## Folhas olhadas

- `folhas_topo/folha_cortadas_12.png`: 12 casos (10 texto, 2 caixa branca). Olhei todos.
- `folhas_topo/folha_cortadas.png`: 53 casos em escala reduzida, ilegível para olhar cada um.
  Olhei a grade inteira na escala que o visualizador deu. Não descrevo cada célula.
- `folhas_topo/folha_inteiras.png`: 60 casos. **Não olhei** esta folha antes de fechar a rodada.
  Qualquer conclusão sobre `inteira` fica pendente.

## O que a F0.2 não responde

- Quantas marcas da corda 1 têm arco de fato cortado. Precisa de um detector de arco (ou de
  olhar cada caso à mão, com pré-registro novo).
- Se a decisão de 5 % do plano deve ser tomada. Fica com a sessão principal.

## Não repetir

- Medir tinta por limiar global em quadro com fundo misto (caixa branca, faixa escura).
- Contar pixel acima do topo como "arco cortado" sem separar texto de arco.
- **(a) Texto acima da tab contado como arco.** Letra da música, nome de acorde e "let ring"
  entram como tinta acima do topo. Na folha de 12 casos legíveis, 10 são texto
  (`folhas_topo/folha_cortadas_12.png`, item 1 de "Por que não vale").
- **(b) Polaridade em fundo escuro.** Quadro de fundo escuro (mediana < 128) é invertido
  globalmente, e uma faixa de caixa branca uniforme acima do painel vira tinta. FTP t5 r2 e r3
  aparecem como recortes em branco liso com 943 e 1312 pixels "acima" (`topo.json`, item 2 de
  "Por que não vale").
- Não há limiar novo para contornar (a) ou (b) nesta frente: a sessão principal decidiu fechar.

## Gate

Ver a mensagem do commit (gate rodado na worktree antes do commit).

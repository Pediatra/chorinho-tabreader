# 1170 — D1: nota ligada fica na corda de uma nota que ainda soa

**Data**: 2026-10-16. Frente D (ligados) de `docs/pesquisa/maos-frentes.md`, seção 7. Código:
`tab/maos_ligado_fontes.py` (as três fontes do rótulo) e `tab/maos_ligado_medida.py` (a
restrição e a medida). A restrição é uma transição proibida no Viterbi do M8
(`tab/maos_corda_sem_direita.py`), que é importado e não editado.

## Pergunta

Se a nota ligada de altura diferente só puder ficar na corda de uma nota que ainda soa (no
ataque anterior, a até 0,5 s, com casa diferente nessa corda), quantos erros de corda do D1
do M8 caem, e quantos novos aparecem? A medida é por fonte do rótulo, separada.

## Pesos a priori (escritos antes da medida)

- Os pesos do D1 do M8: α = 1, β = 0 (sem câmera), γ = 5, δ = 0,5. Nenhum peso novo.
- A restrição não tem peso nem limiar ajustado. Tem uma constante: a janela de origem de
  0,5 s, do texto da frente. Parâmetros ajustados: **zero**. O CA4 (fora da amostra) vale
  por construção.
- A decisão usa a corda que o decodificador escolheu para a nota anterior. A corda do
  gabarito só entra no diagnóstico de erros em pares origem–ligada, que não decide nada.

## Fontes do rótulo "ligada"

1. **Marcas `l` do dono** em `data/gold/maos/padroes_direita.json`: 9 marcas, em retrato e
   glimpse. Casam com a nota de mesma corda, casa e `t_ini` (tolerância de 2 ms).
2. **Arcos de ligadura na tablatura**: 35 arcos lidos visualmente nos 78 símbolos não
   harmônicos de `nao_notas` (leitura da frente, não gabarito do dono; a lista está em
   `ARCOS_LIDOS`). Cada arco liga a nota à direita na mesma corda (a do símbolo ou a de baixo,
   porque o classificador põe o arco na corda de cima). Significado: regra geral de
   `configs/simbolos.yaml` (`regra_do_arco_pelos_numeros`, confirmada pelo dono). O canal
   `sky guitar` não tem vocabulário próprio nesse arquivo.
3. **Áudio sem ataque**: coluna com `motivo == "sem_ataque_casado"` em
   `data/saida/maos/m7/audio/alinhado_*.json`. Os outros motivos (`fora_do_trecho`,
   `exibicao_recusada`, `cosseno_baixo`) não entram.

**Prolongamento** é nota com a mesma altura de uma nota do ataque anterior (até 0,5 s).
Fica fora da restrição e do ganho, e a medida dele sai à parte. As harmônicas não estão em
`notas` (são símbolos em `nao_notas`), então já estão fora da medida; uma ligada cuja coluna
tem harmônico é excluída da fonte 2.

## Critérios (CA1–CA7, congelados como em `maos-frentes.md`, seção 5.3)

- **CA1**: D0 e D1 reproduzem a rodada 1013 (D0: 341 erros; D1: 285 erros, por vídeo 50, 129,
  60, 46). O D1 com a restrição vazia tem de dar a mesma escolha do M8, nota a nota.
- **CA2**: nas ambíguas, somando os 4 vídeos, ganho ≥ +1,0 ponto e consertadas − quebradas ≥ 20.
- **CA3**: ganho em pelo menos 3 de 4 vídeos, e nenhum piora mais de 0,5 ponto.
- **CA4**: fora da amostra, por construção (zero parâmetros ajustados).
- **CA5**: duas execuções dão o mesmo `sha256` do JSON.
- **CA6**: 10 notas olhadas (5 consertadas, 5 quebradas), com o recorte do painel no caminho
  do arquivo.
- **CA7**: `ruff check`, `ruff format --check` e `pytest` verdes na worktree.

**Ponto de parada**: se a precisão da fonte 3 contra a fonte 2 for menor que 70 %, a fonte 3
não é aprovada, e o motivo vai para o relatório.

## Resultados

Saída: `data/saida/maos/frentes/fd_ligados/d1_ligados.json` (criterio congelado). Sha256 de
duas execuções: `ec86cd61…ca888f` (idênticos, CA5). Diagnóstico pós-medida, não aprovado:
`d1_ligados_diagnostico_sem_janela.json`.

### CA1 (reprodução): aprovado

D0 = 341 erros (retrato 61, noturno 141, lacrimosa 76, glimpse 63). D1 = 285 erros (50, 129,
60, 46). Notas 2.437; ambíguas 2.280. O D1 com a restrição vazia dá a escolha do M8, nota a
nota (conferido em `rodar_video`).

### Ligadas achadas (critério congelado, janela de 0,5 s)

| fonte | ligadas de altura diferente | prolongamento | restrição ativa | D1 já acerta |
| --- | --- | --- | --- | --- |
| 1. marcas `l` do dono | 9 (retrato 7, glimpse 2) | 0 | 1 | 9/9 |
| 2. arcos lidos | 18 (retrato) | 0 | 0 | 18/18 |
| 3. áudio sem ataque | 25 (retrato 8, noturno 17) | 0 | 4 | 20/25 |
| união | 48 | 0 | 5 | 43/48 |

Arcos: 35 lidos; 18 com par de nota na mesma corda; 1 excluído por harmônico; 17 sem par
(retrato 9, chopin 3, glimpse 5).

### CA2 a CA7 (fontes, nas ambíguas, somando 4 vídeos)

| fonte | ganho líquido | consertadas − quebradas | CA2 | CA3 |
| --- | --- | --- | --- | --- |
| 1 | +0,00 pp | 0 | não | não |
| 2 | +0,00 pp | 0 | não | não |
| 3 | +0,00 pp | 0 | não | não |
| união | +0,00 pp | 0 | não | não |

- **CA4**: aprovado por construção (zero parâmetros ajustados; a janela é a do texto).
- **CA5**: aprovado (sha256 igual nas duas execuções).
- **CA6**: não aplicável. Com o critério congelado não há nenhuma nota consertada nem
  quebrada, então não há o que olhar (zero recortes gravados).
- **CA7**: `ruff check .` e `ruff format --check .` passam (`All checks passed!`; 187 arquivos
  formatados). `pytest tests/`: 1232 passed, 2 skipped, 2 xfailed, 4 deselected (marca
  `integration`), sem falhas.

### Precisão da fonte 3: PARADA

Contra a fonte 2 (só retrato é observável para ela): **0/8** = 0 %. Contra a fonte 1 (retrato
e glimpse): **0/8** = 0 %. Abaixo de 70 %: a fonte 3 é reprovada, conforme o próprio
`maos-frentes.md` ("o detector de 'sem ataque' inventa ligado"). A medida foi parada aqui.

### Por que o ganho é zero: a janela não abre

- Mediana do intervalo entre ataques: 0,67 s (retrato), 0,73 s (noturno), 0,80 s (lacrimosa),
  0,67 s (glimpse). A fração de intervalos ≤ 0,5 s é 0,6 % (retrato), 23 % (noturno), 0,9 %
  (lacrimosa), 11 % (glimpse). Com a janela congelada, a restrição quase nunca vale.
- O D1 já acerta **todas** as ligadas das fontes 1 e 2. Na união, o D1 erra 5 das 48 ligadas
  (todas da fonte 3), e nenhuma dessas 5 tem nota de origem no ataque anterior. Ou seja, não
  há erro de "par origem–ligada" a consertar: o resíduo de 285 erros está quase todo fora das
  ligadas marcadas.

### Diagnóstico pós-medida (NÃO aprovado): mesma restrição, sem janela

Trocar a janela depois de ver o zero invalida o critério; por isso isto é só explicação, e o
arquivo leva "DIAGNOSTICO POS-MEDIDA, NAO APROVADO". Com a origem sendo o ataque anterior,
sem limite de tempo:

- fonte 1: ganho −0,13 pp, consertadas − quebradas = −3;
- fonte 3: ganho −0,18 pp, −4;
- união: ganho −0,31 pp, −7.

Os 3 casos da fonte 1 (retrato, t = 416,583 / 500,066 / 557,457 s, corda 1 casa 4 e corda 1
casa 7) estavam certos no D1 e a restrição os levou para a corda 2. A corda 2 tinha uma nota
solta anterior, e a restrição só exige "mesma corda, casa diferente", sem limitar a distância.
A casa 9 da corda 2 passou porque é uma casa diferente da solta. **Conclusão**: a restrição
de corda, sozinha, não basta. Falta uma regra de distância de casa (pull-off ou hammer-on de
poucas casas) e, para o ataque anterior, uma regra de sustentação que não existe no produto.

## Não repetir

- Usar `t_ini` de ataques consecutivos com janela de 0,5 s para "nota ainda soa": 0,6–23 % dos
  intervalos cabem, e o zero é efeito da janela, não do método.
- Restringir a corda de uma ligada só pela corda da nota anterior, sem limite de casa: troca
  certo por errado (os 3 casos acima).
- Usar a fonte 3 (`sem_ataque_casado`) como rótulo de ligada: 0/8 contra as fontes 1 e 2.

## Limitações

- Os arcos foram lidos visualmente nos recortes (`leitura_simbolos/`), por mim, não pelo dono.
  Os recortes são pequenos (poucas dezenas de pixels) e têm fundo de vídeo. Só 35 arcos
  entram, e 17 deles não têm par de nota.
- Diagonais que podem ser slide ficaram fora. Dígitos guardados como símbolo (13) podem ser
  notas perdidas; isso não foi medido.
- O canal `sky guitar` não tem vocabulário próprio em `configs/simbolos.yaml`; a regra de arco
  é a geral, confirmada pelo dono.
- A medida cobre 4 vídeos de um canal e um violonista. O `lacrimosa` tem zero arcos lidos, o
  que pode ser falha da leitura e não ausência de ligada.
- A fonte 1 tem 9 marcas. Com um número tão pequeno, nenhum ganho ou perda aqui sustenta
  conclusão por si só.

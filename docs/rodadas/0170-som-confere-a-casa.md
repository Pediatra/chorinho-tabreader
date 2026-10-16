# 0170 — D1: o som confere a casa (altura esperada contra o espectro)

Data: 2026-10-16. Frente D1 (branch `tab/d1-som-casa`), plano `docs/pesquisa/tablatura-frentes.md`,
seção 7, Frente D, "D1". Código: `tab/som_casa_*.py`; testes `tests/test_som_casa_energia.py` e
`tests/test_som_casa_notas.py`. Saída (fora do git): `data/saida/tab_frentes/fd_som/`.

**Resultado: parada.** A regra de parada da calibração foi acionada (precisão nos ouros 0,111 em
L* = 1,25 dB, abaixo de 0,3). O teste na T8.2 **não foi rodado**. A D1, como especificada, não
decide o aceite.

## Pergunta

Para cada nota lida, a altura esperada (corda + casa + afinação) confere com a energia do
espectro no instante do som? Um sinal independente da imagem acha erro de casa e nota inventada?

## Pré-registro (escrito antes de escolher o limiar e antes de qualquer número do teste)

- **Medida.** STFT de Hann, janela de 8192 amostras, passo de 512, a 22 050 Hz, numa janela de
  ±1 s em volta do instante do som. Para a altura `m = corda + casa` (afinação padrão, transposição
  0), parciais `k = 1, 2, 3` numa faixa de ±50 cents (se nenhum bin cair nela, o bin mais próximo).
  `D_k` = máximo de `10·log10(energia)` nos quadros do ataque (de −30 ms a +120 ms) menos a mediana
  da janela inteira. `score` = média dos `D_k`.
- **Sinal.** Nota sinalizada se `score < L`. Grade de `L`: de −5 a 30 dB, passo 0,25 dB (141 valores).
- **Calibração (só os 4 ouros com áudio alinhado).** `L*` = o **maior** `L` da grade com alarme
  falso ≤ 1 % das notas certas medidas (maior `L` = maior revocação, que só sobe com `L`).
- **Parada da calibração.** Se a precisão em `L*` ficar abaixo de 0,3: parar e relatar se a falha é
  de resolução de altura (D2 vale) ou de alinhamento (D2 não vale).
- **Teste (T8.2, com `L*` congelado).** Aceite: precisão ≥ 0,5; revocação ≥ 0,4 dos erros medidos
  (casa + inventadas); alarme falso ≤ 1 % das notas certas. Parar se houver menos de 10 erros medidos.
- **Exclusão.** Técnica declarada na leitura (`tecnica` ∈ {h, p, lig, /, \, harm, x}) sai da medida.
  Coluna sem instante de som sai da medida e é contada à parte.
- **Afinação e capotraste.** Escaneamento de transposição de −3 a +5 semitons, pela mediana do
  `score` das notas certas, por vídeo, antes de decidir. Um deslocamento ≠ 0 é reportado.

## CA1 (reprodução) — passou

| conjunto | esperado (plano) | obtido |
| --- | --- | --- |
| T8.2, `final_s1_ger` | ouro 1573, entregues 1566, casadas 1557, casa 1551/1557, inventadas 9, perdidas 16 | **igual** |
| dobras (6 vídeos, `avaliar_video`) | ouro 1774, entregues 1799, casadas 1764, casa 1747, inventadas 35, perdidas 10 | **igual** |

Reproduzido por `data/saida/tab_frentes/fd_som/scratch/ca1_run.py` e `ca1_somar.py`.

## Os rótulos batem com a régua oficial

`tab.som_casa_notas.rotular` reusa `casar_telas`, `casar_sem_instante`, `notas_distintas` e
`casar_notas`. Confere com `avaliar_video` nos 3 pares avaliáveis (`scratch/verifica_rotulos.py`):

| vídeo | casadas | casa certa | inventadas | perdidas | entregues |
| --- | --- | --- | --- | --- | --- |
| Retrato (mvp) | 485 / 485 | 483 / 483 | 0 / 0 | 6 / 6 | 485 |
| From This Place | 372 / 372 | 368 / 368 | 17 / 17 | 9 / 9 | 389 |
| Room 335 | 247 / 247 | 229 / 229 | 43 / 43 | 76 / 76 | 290 |

**La Vie en Rose não é avaliável pelo `avaliar_video`** ("tela 6 sem passo válido na predição"). A
frente deixa a tela 6 sem rótulo de casa (`sem_passo`): são 59 notas do ouro sem par, fora da conta.

## Dados lidos

- **Produtos.** Os 26 `.audio.json` não-`v21_` de `data/saida/audio/` têm o `produto` com sha256
  batendo com o arquivo atual (26 de 26). A medida usa a MESMA leitura alinhada.
- **Áudio.** Os 4 FLAC dos ouros estavam no cache de áudio: 4 de 4 `hit`, lidos sem gravar em
  `/cache`. Duração total lida: 1207 s (≈ 20 min): Retrato 679 s, La Vie en Rose 189 s, From This
  Place 174 s, Room 335 166 s.
- **T8.2.** 5 telas com áudio já alinhado (Michelle, Kimny Gunjo, Heartache, Sword Art Online,
  First Love). As outras 31 telas não têm áudio alinhado. O runner `tab/som_casa_produtos.py` foi
  escrito para gerar esses alinhamentos, mas **não concluiu nenhum vídeo**: o `tab.video` do primeiro
  não terminou em ~25 min (CPU, 12 núcleos, com outras trilhas rodando). O job foi parado (exit 137).

## Calibração nos 4 ouros (medida congelada, L* = 1,25 dB)

Notas com casa (rótulo da régua). "Medidas" = têm instante de som e score.

| vídeo | casa (rótulo) | medidas | certas medidas | erros medidos | sinalizadas | erros sinalizados | erros não sinalizados | erros sem instante |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Retrato (mvp) | 485 | 481 | 480 | 1 | 2 | 0 | 1 | 1 |
| La Vie en Rose | 364 | 311 | 311 | 0 | 2 | 0 | 0 | 0 |
| From This Place | 389 | 280 | 278 | 2 | 4 | 0 | 2 | 19 |
| Room 335 | 290 | 10 | 9 | 1 | 1 | 1 | 0 | 60 |
| **total** | **1528** | **1082** | **1078** | **4** | **9** | **1** | **3** | **80** |

- **Precisão 1/9 = 0,111** (abaixo de 0,3: **parada**). Revocação dos erros medidos 1/4 = 0,25.
  Alarme falso 8/1078 = 0,0074 (dentro da regra).
- **Só 4 dos 84 erros de casa + inventadas têm instante de som.** Os outros 80 caem em colunas sem
  instante (alinhador recusou a exibição ou não há coluna). A D1 só pode julgar notas que o
  alinhador já ancorou, e os erros estão justamente fora dessas notas.
- Das 9 sinalizadas, 4 têm `cos < 0,7` (alinhamento fraco, o mesmo limiar do alarme de 2011):
  3 do From This Place e 1 do Room 335. Nenhuma sinalizada vem de coluna recusada, porque só
  entram colunas com instante.
- Curva completa e limiares: `data/saida/tab_frentes/fd_som/d1/calibracao_ouros.json`.

## Diagnóstico (não entra no aceite)

**1. A estatística de baseline não separa nota que soa durante a janela.** Com a nota soando na
metade da janela de ±1 s, a mediana sobe com ela, e o `D` da altura certa cai. A altura ausente
ganha `D` pelo degrau do ataque. Medido no sintético (ruído 0,01 sob um tom de amplitude 0,3, E2 com
parciais, `scratch/explora_sintetico.py`): score da altura certa 4,0 dB; alturas erradas 14 a 24 dB
(e 32 dB a um semitom acima). Não é bug de implementação: `scratch/debug_banda.py` mostra a
mediana da janela em 53,7 dB, no nível da própria nota, contra máximo de 57,4 dB no ataque, então
`D = 3,8 dB`. Teste de caracterização: `tests/test_som_casa_energia.py::
test_mediana_da_janela_nao_separa_nota_sustentada`.

**2. Não é resolução de altura.** Com a FFT de 8192 e a faixa de ±50 cents, a faixa separa um semitom
durante a nota: E2 contra F2 e E3 contra E♭3, com mais de 10 dB de diferença (testes
`test_faixa_separa_semitom_*`).
A FFT de 4096 não separava (a faixa de 1 bin, 5,4 Hz, cobre o semitom de 4,9 Hz em E2). Esse
problema foi corrigido **antes** de qualquer limiar, e está registrado abaixo. Ela não foi calibrada: foi trocada no meio da medida, e os
números desta rodada são todos da FFT de 8192.

**3. Alinhamento é a limitação principal.** 80 de 84 erros não têm instante de som. Entre as
medidas, o alinhamento já é a fonte de 4 de 9 sinalizadas com `cos < 0,7`.

**4. Afinação (escaneamento, não visual).** Mediana das certas por deslocamento (dB, de
`resumo_ouros.json`):

| vídeo | melhor | valores em 0 / +1 / −1 | leitura |
| --- | --- | --- | --- |
| Retrato | +1 | 10,2 / 14,3 / 13,8 | ambíguo: ±1 quase igual |
| La Vie en Rose | +1 | 8,0 / 9,0 / 8,7 | ambíguo |
| From This Place | 0 | 9,8 / 9,3 / 9,1 | fraco |
| Room 335 | 0 | 10,0 / 3,1 / 5,7 | claro |

Não houve aferição visual de afinação ou capotraste (`tab/afinacao.py` continua não aferido). Com a
resolução do sinal ainda ambígua em ±1, o escaneamento não basta para afirmar afinação diferente.

**5. Diagnóstico por instante e baseline** (`scratch/diagnostico_ouros.py`, AUC = P(erro tem score
maior que certa). Valor perto de 0 é o sentido certo (erro com score menor que a certa); perto de 1,
o sentido invertido; 0,5 é acaso. Com 1 a 2 erros por vídeo, não é estatística): Retrato, medida
congelada 0,78; baseline pré-ataque 0,69; instante −0,2 s 0,58; +0,2 s 0,73. From This Place:
0,02; 0,14; 0,03; 0,68. Room 335: 0,00 (1 erro). No From This Place, deslocar o instante −0,2 s
mantém a separação (0,03) e +0,2 s a piora (0,68): o instante não aparece adiantado nem atrasado de
forma clara. Com 2 erros, não se afirma nada sobre alinhamento.

## O que a D1 mostra (e o que não mostra)

- Não mostra que o som separa erro de casa de nota certa. O sinal, como especificado, dá 9
  sinalizadas em 1082 notas medidas, e só 1 é erro.
- O caminho para a D1 passa por cobertura do alinhamento (80 de 84 erros fora) e por uma
  estatística de ataque que não dependa da mediana da janela. Isso é desenho novo, a decidir pela
  sessão principal.
- **D2 (modelo pronto de altura): não se justifica por esta D1.** A falha não é de resolução de
  altura (ponto 2). É de baseline e de cobertura do alinhamento (pontos 1 e 3), e D2 não ataca
  nenhum dos dois.

## Casos olhados (10)

Em `data/saida/tab_frentes/fd_som/casos/` (PNG: recorte da tab no quadro do som acima, espectro de
60 a 700 Hz com o instante e as frequências esperadas f0, 2f0, 3f0):

1. `caso_01_from_this_place_inventada_c3_k5_t58.40.png`: inventada, não sinalizada (score 1,8).
2. `caso_02_from_this_place_inventada_c4_k9_t58.40.png`: inventada, não sinalizada (score 1,9).
3. `caso_03_retrato_mvp_erro_casa_c6_k2_t613.09.png`: erro de casa (lido 2, ouro 0), não sinalizado
   (score 13,9). O recorte parece mostrar o 2 na corda 6, e um score alto diz que a altura lida
   soa no ataque. Isso sugere que o ouro pode estar errado. Caso para o dono conferir no quadro
   original.
4. `caso_04_room_335_inventada_c6_k5_t100.52.png`: inventada, sinalizada (score −3,0). Único acerto.
   O recorte parece mostrar um 5 e um 9 perto da coluna: o ouro pode estar incompleto.
5. `caso_05_from_this_place_certa_c5_k2_t67.89.png`: certa sinalizada (score −3,3). Espectro sem
   subida clara no f0.
6. `caso_06_retrato_mvp_certa_c1_k2_t312.66.png`: certa sinalizada (score −1,9).
7. `caso_07_from_this_place_certa_c2_k4_t67.89.png`: certa sinalizada (score −1,8).
8. `caso_08_from_this_place_certa_c4_k2_t58.03.png`: certa sinalizada (score −1,3).
9. `caso_09_retrato_mvp_certa_c1_k7_t474.39.png`: certa sinalizada (score −0,04).
10. `caso_10_la_vie_en_rose_certa_c3_k2_t85.96.png`: certa sinalizada (score 0,09).

Os 6 certos sinalizados têm score ≤ 0,1: no ataque, o espectro na altura lida não sobe acima da
mediana da janela. Isso é o defeito de baseline do ponto 1, não um erro de leitura.

## Medidas de partida descartadas (não repetir)

1. **FFT de 4096 com faixa mínima de 1 bin.** A faixa cobria o semitom vizinho nas cordas graves
   (5,4 Hz de bin contra 4,9 Hz de semitom em E2). Na escala de 4096 o escaneamento de afinação
   mostrava pico em ±1 semitom em 2 de 4 ouros. Trocado por 8192 e ±50 cents, antes de calibrar
   (a versão de 4096 nunca chegou ao `--calibrar`).
2. **Exclusão de notas por símbolo vizinho** (`nao_notas` de classe técnica, harmônico ou símbolo na
   mesma coluna e corda). Foi testada e não mudou nenhuma medida: a contagem de excluídas foi 0 nas
   duas versões. Eu tinha atribuído a ela a perda de erros; a causa real é a cobertura do
   alinhamento (ponto 3). Removida.
3. **Baseline pela mediana da janela de ±1 s.** Não usar para decidir sinal de ataque com nota
   sustentada (ponto 1).
4. **Afinação pelo escaneamento de sinal.** É ambígua em ±1 semitom com este sinal. A aferição de
   afinação precisa de imagem (`tab/afinacao.py`), não do sinal.

## Gate

Rodado na worktree, no container, com `ruff check --no-cache .`, `ruff format --no-cache --check .`
e `pytest tests/ -q -p no:cacheprovider`:

```
All checks passed!
190 files already formatted
1229 passed, 2 skipped, 4 deselected, 2 xfailed in 99.07s
```

## Arquivos

- Código: `tab/som_casa_produtos.py` (runner da T8.2, incompleto), `tab/som_casa_energia.py`,
  `tab/som_casa_notas.py`, `tab/som_casa_medida.py`, `tab/som_casa_decisao.py`.
- Testes: `tests/test_som_casa_energia.py`, `tests/test_som_casa_notas.py` (sem dados do acervo).
- Saída: `data/saida/tab_frentes/fd_som/d1/` (`notas_ouros.jsonl`, `resumo_ouros.json`,
  `calibracao_ouros.json`, `d1.json`); `casos/` (10 PNG); `ca1/` (CA1); `scratch/` (scripts de
  verificação e diagnóstico).

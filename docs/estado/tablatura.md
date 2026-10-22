# Estado — Tablatura

Seções movidas inteiras do [`ESTADO.md`](../../ESTADO.md) na decisão 9001
(fase 5), na mesma ordem. Seção nova desta trilha entra no fim deste arquivo.

## Tablatura — 2026-10-12 — censo: painel por máscara (TAB de fundo rosa, transparente, escuro)

Caminho **aditivo** em `tab/painel.py` (`candidatos_por_mascara`) e `tab/telas.py` (`_painel_por_mascara`): só roda quando os caminhos claro e escuro do HEAD não acham nada; `escolher` intacto. Gabarito de presença: VN09/10/11 passam a `tablatura_no_quadro=true` e entram 7 `caixas_revistas` (decisão do dono, 2026-10-12, registrada em `como_foi_rotulado`).

**Medido**:
- presença (gabarito do dono): precisão de caixa **134/136 = 0,985** (erros FP02, FP11, já conhecidos), revocação **134/137 = 0,978** (antes 0,948); presença por quadro VP 136, FP 0, VN 7, FN 1 (FN02);
- MVP sem mudança: 485/485, 485/491, casa 483/485, tempo 39/40, tempo falso 0; oficial 66/71/68 (0,949);
- piloto (`--piloto 3`, 38 vídeos em comum com o piloto antigo): **11 SEM→TAB, 0 TAB→SEM**; olhado à mão, presença certa nos 11, caixa certa em 9 (#05 kimny's guitar: caixa no braço do violão; #10 transcriptor: caixa na partitura, TAB logo abaixo).

**Pendências**: caixa no braço do violão (caso 4 da conferência e #05 acima); caixa na partitura em vez da TAB (#10); FP08; casos 10/14/21/27 a reconferir no censo refeito por `--so-cache`.

**Artefatos**: `data/saida/conserto_v2/` (MVP, oficiais, piloto, `piloto_mudaram.jpg`).

## Tablatura — 2026-10-12 — censo v2 (com painel por máscara), refeito do cache

`python -m tab.censo --cache --janelas-por-canal 30`, em 6 processos paralelos por grupo de canais (`data/saida/censo/v2/paralelo.sh`; ~20 s/vídeo em série, só 1 núcleo usado). Sobreviveu a um reinício do PC retomando pela chave. Saída única: `data/saida/censo/v2/censo_v2_completo.jsonl` (2.998 vídeos ativos, 0 com erro; 1.162 linhas de erro `Errno 107` do acervo desmontado no reinício foram refeitas e descartadas).

**Medido** (canais ativos):

| | censo antigo | censo v2 |
| --- | --- | --- |
| vídeos | 2.798 | 2.998 (+199 kenneth, +1 leonardo, novos no acervo) |
| com TAB | 2.565 (91,7%) | 2.814 (93,9%) |
| "sem TAB" | 233 | 184 |
| horas-equivalentes de TAB | 142,8 | 171,3 |

- Em 2.798 vídeos comuns: **TAB→SEM 0** (vídeo e instante); SEM→TAB 51 vídeos, 3.287 instantes (kenneth 1.588, dell'arte 686, robert lunn 398, leonardo 212, …).
- Precisão dos instantes novos (leitura visual, rótulo provisório, não do dono): amostra espalhada 36/40; **cifra club 4/16** (8 no braço, 3 em legenda, 1 no painel de batida); guitar dell'arte 38/40 (2 no braço); kenneth 20/20.
- Largura da caixa não separa erro de acerto: kenneth tem 377 instantes novos com caixa < 0,5 da largura e acertou 20/20.

**Pendências**: falso positivo no braço do violão pelo caminho da máscara (cifra club sobretudo; os 6 vídeos de cifra club que viraram TAB são suspeitos, exceto "you know i'm no good"); folhas para virar gabarito, se o dono confirmar: `data/saida/censo/v2/cifra_todos.jpg`, `dellarte_amostra_*.jpg`, `kenneth_amostra.jpg`, `mudaram_sem_para_tab_*.jpg`.

## Tablatura — 2026-10-13 — Fase 8 (T8.1): ouro v2 inicial de 7 vídeos novos

Escolha aprovada pelo dono (2026-10-12), 1 vídeo por canal, pelo censo v2 (`data/saida/fase8/candidatos.json`, folhas `folha_<canal>.jpg`); cifra club fora (falso positivo de presença), rolantes (leonardo ramos, mr. tabs) esperam o formato da T8.4.

`python -m tab.ouro_video completar VIDEO --ouro-v2 data/gold/ouro_video/<slug>.json --saida data/saida/ouro_video/<slug>/` agora aceita vídeo **sem ouro v1**: páginas do `tab.telas` com as notas do modelo (todas `conferida: false`), 40 instantes sorteados dentro da presença (semente 0, grade 2 s) com a página **sugerida** pelo tempo (`pagina_sugerida: true`: viés de confirmação registrado), tela de borda a borda (o painel do `tab.telas` vinha parcial em 2 de 7), painel refeito só na faixa do `tab.telas` quando o quadro inteiro escolhe o braço do violão, página sem painel descartada e listada. `servir --host` para expor a porta do container. O caminho v1→v2 não mudou.

| vídeo | páginas | notas do modelo | instantes |
| --- | --- | --- | --- |
| guitar dell'arte, South American Music | 7 (1 descartada; 5 são o braço do violão, falso positivo do `tab.telas`) | 168 | 40 |
| robert lunn, Gymnopédie no.1 | 12 | 179 | 40 |
| iwaki, La Vie en Rose | 8 | 423 | 40 |
| kenneth acoustic, End of Beginning | 22 | 624 | 40 |
| shin izumi, Room 335 | 42 | 998 | 40 |
| pablo romé, Greensleeves | 4 | 90 | 40 |
| kimny's guitar, From This Place | 5 | 389 | 40 |

Gate: ruff ok, 620 testes (fora 2 arquivos não rastreados da trilha mãos, um deles com 1 falha da outra sessão). **Pendências**: rotulagem do dono (~2.870 notas no total; shin izumi sozinho tem 998); casas > 7 não aferidas (gymnopédie, room 335, from this place); iwaki/shin izumi/kimny sem marcador: instantes quase todos "nenhuma acesa".

## Tablatura — 2026-10-13 — Fase 8: primeiro vídeo fora do sky guitar (pablo romé, Greensleeves) e régua de tempo

Ouro do dono: 4 páginas, 106 notas, 40 instantes (commit `9f5a62c8`). Medida (`data/saida/fase8/medida/`; 2 execuções do `transcrever` idênticas):
- notas: precisão **88/90**, revocação **88/106**, casa **88/88**, telas 4/4. As 18 perdidas são glifos lidos como símbolo (`nao_notas`): 14 são o algarismo **1** saindo como `harmonico` com casa recuperada 4; 2 inventadas na borda direita (casa 8, fora de 0–7);
- tempo: **1/40 com a régua antiga, 20/40 com a nova**; tempo falso 0. MVP sem mudança (39/40; 38 cliques movidos para o x exato da coluna, todos já dentro da tolerância antiga).

**Régua** (`tab/avaliar_video.py::coluna_do_ouro`): neste canal o marcador é um cursor fino **antes** da coluna, e o dono clica no cursor (~17 px à esquerda do centro dos algarismos, passo 24; tolerância era 0,5 passo). O clique agora vai para a coluna de notas do ouro mais próxima, se a até 1 passo; relatório traz `colunas_ajustadas` (Greensleeves 27 de 40). Não muda nenhum rótulo.

**Pendências (T8.3)**: o `1` deste canal lido como harmônico; 17 erros de tempo + 3 sem tempo (primeiras colunas de cada sistema; coluna cujo único token numérico não tem `t_ini`).

## Tablatura — 2026-10-13 — painel: o braço do violão deixa de ganhar da TAB

Defeito: no `south american music` (guitar dell'arte) o `escolher` devolvia a faixa fixa do
**braço** (6 "linhas" das cordas diagonais cortadas na horizontal) e o `tab.video` relia cada
página com essa caixa: **0 de 269** notas. Propriedade medida: `cordas_continuas` (grupos de
linhas de pixels com corrida contínua de tinta ≥ 50 % da largura, buracos até 1 passo
fechados). TAB do gabarito de presença: mínimo **6** (128 de 134 dão exatamente 6); braço
escolhido no South American: máximo **3** (17 de 24 dão 0). Limiar 4. O portão entra só
depois do `escolher` (se a faixa escolhida falha, procura TAB nos outros candidatos e por
máscara; sem alternativa, `None`); `tab.video.ler_tela` usa `escolher_ou_mascara`.

| medida | antes | depois |
| --- | --- | --- |
| South American (`tab.avaliar_video`) | 0/269 | precisão 254/255, revocação 254/269, casa 245/254, tempo 37/40 (falso 0) |
| MVP | 485/485, 485/491, 483/485, 39/40 | idêntico |
| Greensleeves | 88/90, 88/106, 88/88, 20/40 | idêntico |
| `tab.avaliar` (3 sementes) | 66, 71, 68 /72 | idêntico |
| gabarito de presença (`painel_do_quadro`, 144 quadros) | 134/136, 134/137 | idêntico; 1 caixa mudou (FP02 dell'arte: do braço para a TAB, sem rótulo) |

**Não resolve**: braço **horizontal** com cordas contínuas (cifra club, n ≥ 5) e as 12 + 2
caixas erradas do censo, que vêm das vias escura e por máscara do `telas.py`. O portão nessas
vias derrubava 3 TAB translúcidas de linha fina (pablo romé #20/#21, robert lunn #26: n = 1) e
foi revertido. Saídas: `data/saida/painel_braco/`, `data/saida/fase8/medida/*_v2/`,
`data/saida/mvp_v2/`.

## Tablatura — 2026-10-13 — gerador: fonte serifada fina (robert lunn), candidato `fina3`

O Gymnopédie (robert lunn) usa serifa fina tipo Times; o modelo oficial leu 186 de 392 notas
e errou a casa em 108 (`0` lido como `8`, `4`/`2` como `tecnica`/`harmonico`). Presets novos em
`tab.sintetico --fontes` (padrão `padrao` = sequência de sorteios idêntica, pesos `oficial_*`
reproduzem). Treino `--n-linhas 320 --epocas 22 --seed S`, saída `artefatos/serif3_S`;
medições em `data/saida/serif/t1..t3` (`fina3`: + LiberationSerif-Regular com peso 2, corda por
cima quase sempre, fonte fina grande 1,0–1,4 passo).

| `fina3` semente | oficial /72 | MVP casa | Greensleeves revoc. / casa | Gymnopédie revoc. / casa |
| --- | --- | --- | --- | --- |
| 1 | 63 (0,875) | 464/471, revoc. 471/491 | 106/106, 105/106 | 275/392, 259/275 (0,942) |
| 2 | 70 (0,972) | 483/488, revoc. 488/491 | 106/106, 106/106 | 254/392, 238/254 (0,937) |
| 3 | 69 (0,958) | 481/488, revoc. 488/491 | 101/106, 101/101 | 266/392, 247/266 (0,929) |
| oficial (ref.) | 66, 71, 68 (0,949) | 483/485, revoc. 485/491 | 88/106, 88/88 | 186 lidas, 78 casas certas |

Média oficial 0,935 (amplitude 0,097) contra 0,949: **não promovido** (`MODELO_PADRAO` igual).
Critério do Gymnopédie (casa ≥ 0,95) não alcançado (0,93–0,94), mas a casa saiu de ~0,42 e a
revocação de 0,47 para 0,65–0,70. Ainda falha: `4` lido como `harmonico` e notas não
tokenizadas (revocação). Presets `fina`, `fina2`, `fina4` (com desfoque) medidos e piores
(`data/saida/serif/g2_*`, `g4_*`). Uso: `serif3_2` só para PRÉ-PREENCHER o ouro (o dono corrige).

## Tablatura — 2026-10-13 — régua de tempo: cursor em trânsito vale a última coluna passada (decisão do dono)

Diagnóstico do Greensleeves (`data/saida/tempo_gs/`, folha `folha.png`): dos 17 erros + 3 sem
tempo, **10** eram o cursor fino do pablo romé **entre duas colunas** (a régua levava o clique
para a mais próxima, às vezes a seguinte; o produto dava a última passada); **7** eram coluna
que o produto não leu (o "1" lido como harmônico; o candidato `serif3_*` lê); **3** são a 1ª
coluna de uma exibição, sem tempo (onset atrasado; defeito real, aberto). Decisão do dono: entre
duas colunas vale **a última que o cursor passou** (a nota que soa). `coluna_do_ouro`: a última
coluna à esquerda do clique, salvo se a próxima está a até 0,75 passo à direita **e** mais perto
(cursor chegando, ~17 px antes). A versão "até 0,75 passo, sem comparar" piorava o South
American em t=98 (colunas a 20 px) e foi corrigida antes do commit.

| vídeo | régua antiga | régua nova |
| --- | --- | --- |
| MVP (oficial) | 39/40 | **40/40** |
| Greensleeves (oficial) | 20/40 | **29/40** |
| Greensleeves (`serif3_1/2/3`) | 23, 24, 23 /40 | **33, 33, 32 /40** |
| South American (v2) | 37/40 | 37/40 |

Tempo falso continua 0 em todos. Scripts: `data/saida/fase8/medida/regua_a/`.

## Tablatura — 2026-10-13 — marcador pulado: limiar de tinta 0,02 → 0,01

Causa das colunas puladas do Greensleeves (t = 62, 82, 114): o cursor fino do pablo romé mostra
pouca tinta por dentro (p1 0,0087, p5 0,0115, mediana 0,0276; 291 de 1.238 amostras abaixo de
0,02) e `faixa_translucida` o recusava. MVP (mediana 0,106) e South American (0,129) ficam longe;
a moldura sólida do MVP mede 0,0 exato. Medido com `serif3_2`, mesmo leitor do produto:

| vídeo | 0,02 | 0,01 | 0,005 |
| --- | --- | --- | --- |
| MVP | 40/40 | 40/40 | 40/40 |
| Greensleeves | 33/40 | **38/40** | 38/40 |
| South American | 37/40 | 37/40 | 37/40 |

Nenhum instante piora; no Greensleeves 6 mudam para acerto (62, 82, 114, e 92/130, que eram a
"1ª coluna sem tempo"). MVP e South American saem com JSON idêntico. Greensleeves ganha 12 notas
fora das páginas do ouro (203 → 215), não pontuadas. Adotado 0,01 (o mais conservador dos dois
que empatam). Scripts: `data/saida/limiar_tinta/`.

## Tablatura — 2026-10-14 — detector neural de sistema (N1–N4): medido nos 8 ouros

Troca o recorte por regras (`_glifos_por_faixa` + barline + classificador de glifo) por
uma rede que vê o sistema inteiro (`tab.detector_tab`, 555 mil parâmetros, treinada com
`tab.sintetico_sistema`). A geometria (painel, cordas, passo) continua a do produto.
Medição no mesmo quadro de cada tela conferida dos 8 ouros (63 telas, 2.689 notas):

| leitura | precisão | revocação | casa |
| --- | --- | --- | --- |
| produto (`oficial_3`) | 0,962 | 0,830 | 0,943 |
| v3 só sintético (3 sementes, média) | 0,977 | 0,950 | 0,977 |
| v3 + ajuste fino com ouros, validação cruzada por vídeo (4 dobras) | 0,974 | 0,949 | **0,987** |

- Room 335 corda 1: 8/28 → 28/28; Gymnopédie revocação 0,43 → 0,93; Greensleeves 0,83 → 1,00.
- O que custou caro e foi consertado pelo GERADOR, não por regra: arpejo Guitar Pro, "TAB"/fórmula
  grandes e pausas lidos como nota (74 inventadas → 10); "1" fino de sans regular lido como "4"
  (78 casos; fontes de treino 2 → 6; o ajuste fino zerou o resto).
- Régua: a nota acrescentada por clique guarda o clique como centro, e no "10" o dono clica no "1"
  (50 notas de dois algarismos com centro < 8 px da borda). `casar_notas` usa 0,8 passo para casa
  de dois algarismos (`FOLGA_DOIS_ALGARISMOS`); números do produto não mudam.
- Única piora contra o produto (ajuste fino, 3 sementes): retrato e la vie, 1-2 notas em ~450.
- Viés a favor do produto: os ouros v2 foram pré-preenchidos por ele (posições herdadas).
- Fora do produto até decisão do dono; trocar o leitor muda o X do rasgueado ("15") de que o áudio depende.
Scripts e tabelas: `data/saida/n3/`, `data/saida/n4/`.

## Tablatura — 2026-10-14 — produto troca de leitor: `rede` é o padrão (decisão 0010)

- **Aprovado pelo dono** ("trocar é a escolha certa"). `tab.video` e `tab.transcrever` ganham
  `--leitor rede|glifos`, e o padrão é `rede`. O leitor de glifos fica de reserva.
- **Modelo**: `artefatos/detector_tab_final_s{1,2,3}/`, ajuste fino a partir de `v3_s1` com os 8
  ouros (63 telas) e o sintético, 3000 passos. O comando está no `config.json`
  (`data/saida/n4/treinar_ft.py --dobra 0`). Perda final nas sementes 1/2/3: 0,0541, 0,0541 e
  0,0543. O produto usa a **s1**, declarada antes de medir.
- **Régua de tempo nos 3 vídeos com marcador**, mesmo HEAD. A rede usa o modelo da dobra que
  NÃO viu o vídeo (`data/saida/troca/`):

  | vídeo | leitor | precisão | revocação | casa | tempo |
  | --- | --- | --- | --- | --- | --- |
  | MVP (retrato) | glifos | 1,000 | 0,988 | 0,996 | 40/40 |
  | MVP (retrato) | rede | 0,998 | 0,994 | 0,996 | 40/40 |
  | Greensleeves | glifos | 0,978 | 0,830 | 1,000 | 34/40 |
  | Greensleeves | rede | 0,991 | 1,000 | 1,000 | 38/40 |
  | South American | glifos | 0,996 | 0,944 | 0,965 | 37/40 |
  | South American | rede | 1,000 | 1,000 | 1,000 | 38/40 |

  - Tempo falso: 0 em todos.
  - Esquema: 0 erros nos 3 JSONs da rede.
  - O MVP passa a ter **1 nota inventada** (CA-3 pede 0 no MVP). É a mesma nota da validação
    cruzada.
- **Bug achado e corrigido antes do commit**: nota da rede herdava a borda esquerda de um glifo
  largo (slide `2/3` grudado). Duas notas caíam na mesma coluna e geravam 5 erros de esquema no
  South American. Agora a borda só é herdada se o glifo começa a até 0,8 passo do centro
  (`BORDA_MAXIMA_PASSO`), com teste.
- **Consequências** (decisão 0010):
  - o X sai em `nao_notas` como classe `x`; a trilha áudio foi avisada pelo texto da decisão;
  - `tecnica` da nota vem preenchida pela rede, **sem validação**;
  - o leitor `rede` não grava `simbolo_cru`. É dívida: quem precisar do recorte cru usa
    `--leitor glifos`.

## Tablatura — 2026-10-15 — fase 8: linhas sob faixa de destaque, e régua com ouro parcial

- **Linhas sob a faixa amarela** (`tabseg.extensao_das_linhas`). No End of Beginning (kenneth
  acoustic, t=52 s) a faixa amarela do compasso tocado apagava as cordas no Otsu. O painel
  começava em x=1011, e a tablatura começa em x≈12. Agora a linha conta também pelo contraste
  local, mas **só onde o fundo local é claro** (`FUNDO_CLARO_MINIMO = 150`).
  - A primeira versão, sem a exigência de fundo claro, piorou a Gymnopédie. O papel fica
    sobre vídeo escuro, o painel crescia para fora do papel e, em 163,4–163,6 s, a escolha caía
    no braço ou em nada. A tela 13 ficava sem passo, e a régua recusava o vídeo inteiro.
  - Fundo medido na linha da corda: papel 255, faixa amarela 241, vídeo escuro ≤ 75.
  - 2 testes sintéticos. Cada um falha na versão que não tem o seu conserto (controle negativo
    feito).
- **Régua com ouro parcial** (`tab.avaliar_video`). Em EOB e Room 335 o ouro confere só
  algumas páginas. As notas entregues em tela sem página conferida contavam como
  "inventadas" (464 e 900). Agora ficam fora da conta, e o relatório diz quantas.
- **8 ouros, leitor `rede`, modelo da dobra que não viu o vídeo** (`data/saida/fase8/linhas2/`):

  | vídeo | precisão | revocação | casa | antes (revocação) |
  | --- | --- | --- | --- | --- |
  | retrato | 0,998 | 0,994 | 0,996 | igual |
  | La Vie | 1,000 | 0,995 | 0,998 | igual |
  | Greensleeves | 1,000 | 1,000 | 1,000 | igual |
  | Gymnopédie | 0,951 | 0,931 | 0,932 | 0,934 (1 nota) |
  | South American | 1,000 | 1,000 | 1,000 | igual |
  | From This Place | 0,979 | 0,990 | 0,995 | igual |
  | End of Beginning | 0,981 | **1,000** | 0,997 | **0,670** |
  | Room 335 | 0,922 | 0,991 | 0,991 | igual |

  - Esquema: 0 erros nos 8.
  - CA-8: 66/71/68 de 72, sem mudança.
  - O tempo do EOB continua 0/12 ("json sem tempo"): o marcador do kenneth não é lido. Pendente.
- **Inventadas de Room 335 e From This Place, olhadas uma a uma**:
  - Room 335: 25 de 27 são leitura errada (pausa com forma de "7", rótulo "TAB", setas de
    palheta). 1 é nota que falta no ouro (tela 4, corda 3, um "1"), para o dono decidir.
  - From This Place: 4 são a fórmula de compasso 3/4 em cinza. As outras ficam em volta de
    algarismos pequenos de ligado ("h") e de "harm. 12".
  - O gerador não tem essa pausa nem o 3/4 cinza. É lacuna de cobertura (regra 6).
- **Barra grossa não é corda** (`painel.descartar_grossas`). Na Gymnopédie, tela 10 (t=136,5 s),
  o painel ficava uma corda abaixo. A barra preta de 10 px da borda do vídeo formava, com 5
  cordas reais, um grupo de 6 linhas regular que ganhava por uniformidade (0,827 contra 0,820).
  Agora um grupo com linha grossa (≥ 6 px e ≥ 2× a mediana, medida na extensão das próprias
  linhas) sai quando existe grupo limpo com 5 das suas 6 linhas.
  - Nas 63 telas conferidas dos 8 ouros, só a tela 10 mudou.
  - Gymnopédie: precisão 0,951 → **0,997**, revocação 0,931 → **0,997**, casa 0,932 → 0,957.
    Os outros 7 vídeos ficaram iguais (`data/saida/fase8/grossa/`, no worktree haiku-gym).
  - 3 testes sintéticos; o controle negativo falha sem a regra.
  - A casa da Gymnopédie (0,957) é a pior dos 8. Ainda não olhei quais casas erram.
- **Painel escuro do cifra club** (`painel._candidato_do_grupo` + `tabseg.extensao_das_linhas_claras`).
  O cifra club desenha a TAB em fundo quase preto, com tracejado claro, letras e/B/G/D/A/E em
  bolinhas laranja à esquerda e diagramas de acorde à direita. O grupo de 6 cordas era achado,
  mas `extensao_das_linhas` só vê linha em fundo claro e estreitava o recorte a ~60 px, e a
  escolha recusava. Agora, com faixa de mediana ≤ `FUNDO_ESCURO_MAXIMO`, a extensão é a do
  tracejado claro, começando depois das bolinhas e com buraco máximo de 60 px. Os buracos do
  tracejado têm 17–26 px (46 px num caso), e o intervalo até o diagrama tem 96–113 px.
  - Em 8 quadros de cifra club, de 8 vídeos, o painel certo foi de 0 para 6. Os 2 restantes
    (a grande família t=52, acenda o farol t=43) ainda escolhem o braço do violão antes do
    ramo escuro. Pendente.
  - Nos 6 quadros, as notas lidas batem com as reais contadas à mão (154). Falsas nas letras
    e no diagrama: 33 → 0. A versão intermediária, com a largura cheia, lia essas 33.
  - O bend escrito "6b7"/"b9r8" sai como mais de uma nota. Técnica não validada.
  - Não-regressão do painel: 63 telas dos 8 ouros e 20 telas claras de outros canais com as
    mesmas linhas e a mesma caixa.
  - 2 testes sintéticos; o controle negativo, com a largura cheia, falha.
  - A régua completa dos 8 ouros não foi rodada de novo: o ramo só age em faixa escura, e os
    painéis dos ouros saíram idênticos.
- **Braço do violão contra a TAB escura** (`painel.escolher_ou_mascara`). Em 3 de 14 quadros de
  cifra club, `escolher` aceitava o braço: as cordas dele passam no teste de linhas contínuas.
  O que separa é a **deriva** das cordas, isto é, quanto sobem ou descem de uma borda à outra,
  em passos:
  - TAB: 0,003–0,060 em 97 telas (63 dos ouros, 20 claras, 6 de cifra club);
  - braço: 0,104, 0,336 e 0,389.
  - Com deriva acima de `DERIVA_BRACO_PASSOS = 0,08`, a escolha procura antes uma TAB escura,
    já recortada pelo tracejado (`candidatos_escuros_estreitos`). Se não achar, fica com a
    escolha antiga. A margem é estreita (0,060 contra 0,104).
  - Cifra club: caixa certa em 14 de 14 quadros (antes, 11). As outras 94 telas ficaram
    idênticas.
  - Lidos pela rede, os 3 quadros trocados têm 60 notas reais: 59 certas, 1 perdida (o
    primeiro 7 de um "7/9"), 0 falsas.
  - 2 testes; o controle negativo falha.
- **Ouro da Gymnopédie corrigido pelo dono** (2026-10-15). Cinco notas estavam como 8 e a
  imagem mostra 0: tela 1 corda 5 (x 1191), tela 2 corda 5 (x 1404), tela 3 corda 6 (x 1690),
  tela 8 corda 5 (x 1216) e tela 11 corda 3 (x 542). Com o mesmo JSON previsto, a casa da
  Gymnopédie vai de 0,957 para **0,969**; precisão e revocação não mudam (0,997).
- **Ouro do Room 335: nota que faltava, incluída pelo dono** (2026-10-15). Tela 4, corda 3,
  casa 1, na coluna x 1260 (2-1-2-0 nas cordas 2 a 5; conferido no recorte do quadro t=14 s).
  Com o mesmo JSON previsto, a precisão vai de 0,922 para **0,925** (320 de 346).
- **Gerador: pausa entre cordas e cinza** (`tab/sintetico_sistema.py`). Desenha a pausa que
  fica entre duas cordas (`P_PAUSA_ENTRE = 0,3`, forma copiada dos recortes reais do Room 335)
  e, às vezes, a fórmula de compasso e a TAB inteira em cinza (`P_FORMULA_CINZA`,
  `P_TAB_CINZA` = 0,15). Eram as notas inventadas que sobravam no Room 335 e no From This
  Place. Ajuste fino das dobras 2–4 (`data/saida/n4/treinar_ft.py`), 3 sementes por gerador,
  régua nos 6 vídeos dessas dobras, mesmo código e mesmo ouro (`data/saida/fase8/ger/`):

  | gerador | precisão (s1, s2, s3) | revocação | casa | inventadas |
  | --- | --- | --- | --- | --- |
  | antigo | 0,977 0,973 0,970 | 0,996 0,996 0,995 | 0,990 0,990 0,988 | 41 50 55 |
  | novo | 0,981 0,980 0,978 | 0,994 0,994 0,996 | 0,990 0,988 0,987 | 35 36 40 |

  - A precisão melhora nas 3 sementes, sem sobreposição (pior novo 0,978 > melhor antigo
    0,977), e a amplitude cai de 0,008 para 0,003. Room 335: 0,904–0,925 → 0,928–0,936.
  - Revocação e casa ficam dentro da amplitude. Gymnopédie, casa: 0,962–0,969 → 0,954–0,972.
  - **O produto passa a usar o gerador novo**: `detector_tab_final_s1_ger` (dobra 0, os 8
    ouros + sintético, semente 1 declarada antes, cache refeito com os ouros corrigidos). Nas
    35 telas da T8.2, que nenhum dos dois modelos viu, relidas pelos dois com o mesmo código
    (`data/saida/fase8/ger/t82_comparar.py`):

    | modelo | casa | precisão | revocação | inventadas | perdidas |
    | --- | --- | --- | --- | --- | --- |
    | `final_s1` (antigo) | 1549/1556 = 0,996 | 0,996 | 0,989 | 7 | 17 |
    | `final_s1_ger` (novo) | 1551/1557 = 0,996 | 0,994 | 0,990 | 9 | 16 |

    Fora do ouro é empate: 15 erros do antigo somem e 12 novos aparecem, a maioria de
    algarismo duplo (10, 12, 14) perdido. O antigo reproduz exatamente o número da T8.2,
    então a releitura confere. A troca vale pelo ganho nas dobras, sem perda fora delas.
- **T8.2: casa fora do ouro, conferida pelo dono** (2026-10-15). 36 telas, 2 vídeos por canal
  dos 18 canais fora do ouro (sorteio com semente 0, `data/saida/t82/gerar.py`), lidas pelo
  produto (rede `detector_tab_final_s1`). O dono conferiu 35 na ferramenta do ouro
  (`tab.ouro_video servir` com material de `data/saida/t82/material_ferramenta.py`; respostas
  em `data/saida/t82/ferramenta/conferencia_t82.json`, fora de data/gold). A tela 33 ficou de
  fora: a ferramenta abria o editor longe do clique em imagem muito larga.
  - 1.563 notas lidas: 1.549 certas, 7 com casa errada, 7 falsas e 17 faltando. Casa certa
    em 1.549 de 1.556 casadas (0,996); precisão 0,996; revocação 1.556 de 1.573 (0,989).
  - Causas (31 erros, olhados um a um em `data/saida/t82/erros/`): número de dois
    algarismos 12 (10, 11 e 12 perdidos ou lidos pela metade), nota encostada em haste,
    arco ou barline 7, fundo ou cor 4, símbolo lido como nota 3, "1" de perna comprida lido
    como 4 3, nota fora do recorte 2.
  - Frequência não explica os dois algarismos: o gerador sintético já sorteia cerca de 33%
    de casas com dois algarismos (`P_CASA_ALTA = 0,15` para 13–24, mais 10–12 entre 0–12).
    A causa está no aspecto (espaço entre os algarismos, fonte, corda tocando o número), e
    ainda não foi medida. O "1" de perna comprida é outra fonte que o gerador não tem.

## Tablatura — 2026-10-16 — onda 1 das frentes (F0, C1, D1)

Três frentes fechadas nesta onda. O aceite de nenhuma foi atingido: A1 não abre, C1 sai, D2 não abre.

### F0 — régua de técnica (rodadas 0101–0104)

- **Folga 0,5**, fixa, como manda o plano (§5.2). A medida com 1,0 foi descartada por contradizer o plano; continua registrada na 0101 só para comparação.
- [`0101`](../../docs/rodadas/0101-regua-de-tecnica.md): o legato (h, p, mordente, prolongamento; 139 marcas) é achado em **25 de 139**, com classe certa em **4**. Slide: 20 de 46 certas. Harmônico: 4 de 4 (não decide, menos de 10 marcas). Arpejo (0 de 21) e rasgueado (0 de 15) não têm saída na rede. Das perdas, **179 de 201** são "nada marcado".
- [`0102`](../../docs/rodadas/0102-topo-cortado.md) (F0.2, topo cortado): **não conclusiva**. A medida conta texto acima da tab (10 de 12 folhas legíveis eram letra ou nome de acorde) e erra a polaridade em fundo escuro. Não há limiar novo; a frente fecha assim.
- [`0103`](../../docs/rodadas/0103-cabeca-do-ligado.md) (F0.3, cabeça do ligado): o ajuste fino **não apagou o ligado**. Com escore ≥ 0,5 nas 139 regiões, v3_s1 marca 14 e o produto 13. O escore existe, mas é fraco (mediana 0,1 nos dois modelos).
- [`0104`](../../docs/rodadas/0104-corda-vizinha-e-sementes.md) (corda vizinha, variante de diagnóstico): nas 229 marcas, +4 certas, todas de slide (28 → 32). No legato continuam 4 certas de 139. A variante não entra na régua oficial.
- **Conclusão.** A rede não acha o ligado, e não é por limiar nem por ajuste fino. **A1 não abre.** O caminho é A2 (detector de arco) ou B (estilo do arco no gerador). **B1 abre primeiro**: o dono aprovou a dependência do AlphaTab em 2026-10-16.

### C1 — rolagem (rodadas 0150–0153)

- [`0150`](../../docs/rodadas/0150-rolagem-censo-nao-rola.md): a primeira leitura, "não rolam", estava errada. Os rolantes do censo rolam **em saltos com sobreposição**. A triagem chamou de troca de página todo passo acima de 40 px, e isso foi o erro.
- [`0151`](../../docs/rodadas/0151-rolagem-saltos-definicoes.md): definições, máscaras e limiares dos saltos, antes da medida.
- [`0152`](../../docs/rodadas/0152-rolagem-consenso-e-remedida.md):
  - **kenneth "location" passou**: 19 válidos de 20 (1 indefinido); erro mediano do consenso 0,06 px, máximo 0,26 px; nenhum salto válido com erro > 5 px.
  - **mr. tabs "no rain" falhou**: 3 de 20 com erro > 5 px (690, 779 e 1557 px). É alias de período de dois compassos (~779 px), e a regra de consenso não pega, porque os dois métodos erram igual.
- [`0153`](../../docs/rodadas/0153-rolagem-palpite-pelo-cursor.md): nem o palpite pelo cursor resolveu. Mediana 0,32 px passa, mas 6 de 13 definidos erram mais de 5 px. A premissa de que o compasso do cursor vai ao início da linha não vale: em 155,9 s ele fica em 1061,5 px. A rodada parou no mr. tabs; kenneth e leonardo não foram medidos.
- **C1 sai desta onda.** Ideia anotada para depois: verificar se o salto é animado e somar os passos quadro a quadro (não medido).

### D1 — som confere a casa (rodada 0170)

- [`0170`](../../docs/rodadas/0170-som-confere-a-casa.md): **parada**. Precisão nos 4 ouros em L\* = 1,25 dB: **1/9 = 0,111** (abaixo de 0,3). Revocação dos erros medidos: 1/4.
- **80 de 84** erros de casa + inventadas não têm instante de som. São colunas sem alinhamento, já cobertas pelo alarme por exibição da rodada 2011. A falha é de cobertura e de baseline, não de resolução de altura: **D2 não abre**.
- Dois casos levados ao dono:
  - Retrato v2, tela 11, corda 6: era erro do ouro (0 → 2), corrigido.
  - Room 335, tela 27: o ouro estava certo (5 ligado ao 9 na corda 5). O arco desenhado sobre a corda 6 faz o produto errar a corda.

### Integração: o ajuste fino apagava o X

- O ajuste fino (`data/saida/n4/treinar_ft.py`) ensinava o detector a apagar o X abafado: tudo que não é nota do ouro virava fundo. No End of Beginning o produto dava ~1 X para 76 regiões marcadas; o modelo da dobra que não viu o vídeo dava 93.
- **Conserto parcial** com `--ignorar-x` (região de X não conta como fundo): **38 de 76** no EOB e **5 de 9** regiões no kenneth (T8.2). Notas sem piora: dobras, casa certa 1745 contra 1744 na semente 1, 1737 contra 1738 na semente 2.
- **Próximo passo:** ensinar o X como nota, a partir de palpites conferidos pelo dono. O produto (`DETECTOR_PADRAO`) não mudou.

### Ouro

- Correções do dono no Retrato v2 e Room 335 (commit `3e7d4d74`). CA1 das dobras passou a ouro 1771, entregues 1799, casadas 1761, casa 1744, 38 inventadas, 10 perdidas. A 0170 tinha 1774 / 1799 / 1764 / 1747 / 35 / 10 antes dessa correção.
- `tab.ouro_video servir` desfazia edições feitas fora dela. Agora não sobe se o ouro diverge do estado (commit `bc431c0f`).
- **Gymnopédie diverge** (10 linhas): precisa de acerto antes de ser aberto.

Tabela "não repetir" atualizada acima (5 linhas novas).

## Tablatura — rótulo de ataque na T8.4 (0211, 2026-10-22)

- **O `_atqa` reprova na prova lacrada T8.4.**
  - "Sim" falso de **33/266 (12,4 %)**, com o limite de 5 %. O custo é de 131/3477
    (3,8 %).
  - Recontado com a correção de ligadura do dono, dá 21/254 (8,3 %). Isso só informa.
- **O `DETECTOR_CALIBRADO` continua `_atqt_s1`**, e a T8.4 está gasta.
- **O que escapa é a ligadura de prolongamento** que o gerador não cobre:
  - o `(n)` entre parênteses;
  - o arco embaixo da corda;
  - o harmônico ligado.
- **Regra do dono** (2026-10-22): numa ligadura, **o primeiro número é atacado**, com ou sem
  segundo número.
- **A próxima prova lacrada é a T8.5**: 30 telas de 15 canais, em
  `data/saida/tablatura/t85/`, na conferência do dono.

### T8.5 conferida (2026-10-22)

- **28 telas, 1.366 notas**, conferidas pelo dono nos dois passes (casa e ataque). O
  rótulo está em `data/saida/tablatura/tab_rotulo/r2/conferir_t85/ataque_t85.json`.
  - **1.320 atacadas** e **46 não atacadas**: 17 slide ligado, 16 prolongamento, 6 h,
    5 p e 2 mordente.
  - Saíram 2 telas:
    - a **5**, porque o painel pegou a pauta como se fosse tablatura;
    - a **27**, porque o recorte cortou a corda 6 e deslocou as cordas de uma. Ela foi
      refeita em `t85/refazer27/`, mas o dono não a conferiu.
- **Regra da ligadura de um número só** no `converter.py`
  (`PROLONGAMENTO_UMA_NOTA_ATACADA`): vale só na T8.5. As fontes antigas seguem o lado
  do arco.
- **Na ferramenta, `l` quer dizer "não atacada"**. O dono marcou `l` em 34 notas que
  começam uma ligadura, pensando que era a marca da ligadura. Ele confirmou: "Elas são
  tocadas uma vez e depois são prolongadas". As 34 voltaram para `sim/sustentada`
  (`t85/passe_ataque/correcao_sustentada.py`).
  - **Dívida da ferramenta:** o modo ataque precisa mostrar "~ atacada, prolongada" com
    um nome claro no seletor.
- **Nenhum modelo foi medido na T8.5.** Ela é a prova lacrada da próxima versão do
  ataque.
- Ver `docs/rodadas/0211-recorte-alto.md`, "Resultado na T8.4".

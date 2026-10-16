# Onda 1 das frentes da tablatura — briefings

**Data**: 2026-10-16. **Plano**: [`tablatura-frentes.md`](tablatura-frentes.md), seção 4 ("Ondas de
execução"). **Para quem**: o dono, que abre uma worktree e um agente por frente e cola o briefing
da frente.

## Como abrir cada worktree

Uma worktree por frente, a partir do `main` atual (o commit que trouxe este arquivo ou depois).
Os nomes não colidem com os das frentes das mãos (`../chorinho-wt-f0` etc.):

| frente | worktree | branch |
| --- | --- | --- |
| 0 — régua de técnica e topo cortado | `../chorinho-wt-tab-f0` | `tab/f0-regua-tecnica` |
| C1 — rolagem | `../chorinho-wt-tab-c1` | `tab/c1-rolagem` |
| D1 — o som confere a casa | `../chorinho-wt-tab-d1` | `tab/d1-som-casa` |

```bash
git worktree add ../chorinho-wt-tab-f0 -b tab/f0-regua-tecnica main
```

As três rodam em paralelo e não dependem umas das outras. Nenhuma usa GPU. Só a C1 lê vídeo
denso, um vídeo por vez; a F0 lê só os quadros das telas do ouro e da T8.2, e a D1 lê áudio.

Quando uma frente terminar, avise a sessão principal com o nome do branch. Ela remede na `main`,
integra e consolida o `ESTADO.md`. A onda 2 (A1, B1, E1 + E2) tem briefing próprio, escrito
depois que a régua da F0 for remedida na `main`.

## Regras comuns (todas as frentes)

Estão no `tablatura-frentes.md` e valem inteiras. As que mais pegam:

- **Montagem** (seção 6.1): `data/saida/` e `artefatos/` da cópia principal só para leitura, e só
  as pastas da frente para escrita. Antes de medir, dentro do container, `ls
  /app/artefatos/detector_tab_final_s1_ger` e `ls /app/data/saida/fase8/ger/ger` têm de listar
  arquivos.
- **CA1 primeiro**, antes de mudar qualquer coisa, sem ler vídeo inteiro:
  - **T8.2**: copie `data/saida/fase8/ger/t82_comparar.py` para a pasta da frente e mude só o
    caminho de saída (a pasta original está só para leitura). A linha `novo` tem de dar: ouro
    1573, entregues 1566, casadas 1557, casa 1551/1557, inventadas 9, perdidas 16.
  - **Dobras**: para cada um dos 6 vídeos, rode `python -m tab.avaliar_video --ouro
    data/gold/ouro_video/<slug>.json --pred data/saida/fase8/ger/ger/<slug>.json --json
    <pasta da frente>/ca1/<slug>.json` e some `notas.total`: ouro 1774, entregues 1799, casadas
    1764, casa certa 1747, inventadas 35, perdidas 10. Isto reavalia as leituras gravadas; não
    releia os vídeos.
  - Se não bater, pare e relate.
- **Critérios congelados** (seção 5.3 e seção 10, item 6): limiares e folgas escritos no documento
  da rodada **antes** da medida. Mudar depois de ver o resultado invalida a frente.
- **Proibido** (seção 6.3): escrever fora da pasta da frente; editar `ESTADO.md`, `data/gold/`,
  `DETECTOR_PADRAO` ou o recorte do painel; editar `tab/maos_*`, `tab/audio_*`, `tab/partitura_*`
  e os testes delas (importar e rodar pode); dependência nova; commit em `main`.
- **Entrega** (seção 9): código com o prefixo da frente e testes sem `data/saida/`, sem
  `artefatos/` e sem acervo; gate verde na worktree (`ruff --no-cache`, `pytest -p
  no:cacheprovider`); documento de rodada na faixa da frente; commit no branch com o número na
  mensagem; resumo curto em português.

---

## Briefing — Frente 0 (régua de técnica e topo cortado)

```text
Você trabalha na worktree da Frente 0 da tablatura do projeto chorinho. Leia inteiro, antes de
rodar qualquer coisa: AGENTS.md; docs/pesquisa/tablatura-frentes.md (seções 1 a 6, a Frente 0
na seção 7, e as seções 8, 9 e 10); docs/pesquisa/tablatura-onda1-briefings.md (regras comuns);
no ESTADO.md, a seção "Tablatura — 2026-10-15 — fase 8"; docs/decisoes/0010-leitor-rede.md; o bloco
regra_do_arco_pelos_numeros de configs/simbolos.yaml; data/saida/fase8/ger/t82_comparar.py
(modelo de como ler uma tela).

Tarefa: a F0.1 (régua de técnica) e depois a F0.2 (arco da corda 1 fora do recorte). Siga o
"Como" de cada uma à risca. Faça o CA1 primeiro (regras comuns).

F0.1:
- Escreva tab/tecnica_regua.py: lê as regiões do dono (campo "regioes" das telas dos ouros e
  de data/saida/t82/ferramenta/conferencia_t82.json), casa com as notas previstas como na
  seção 5.2 e grava a tabela por classe e por fonte.
- Modelo do produto (artefatos/detector_tab_final_s1_ger): leia só os quadros das telas
  marcadas, como o t82_comparar.py faz (leitor.quadro_em no quadro_ref_s da tela,
  painel.escolher_ou_mascara, detector_tab.detectar, que já devolve "tecnica" por nota). Não
  leia vídeo inteiro; registre quantos quadros leu.
- Modelos das dobras: use as leituras gravadas em data/saida/fase8/ger/ger/<slug>.json (campo
  tecnica de cada nota). La Vie en Rose é da dobra 1 e não tem leitura do gerador novo: leia
  as telas dela com o detector_tab_v3ft_d1 ou declare-a fora deste passo.
- Antes de casar, confira em 3 casos que o x da nota e o x_quadro da região estão na mesma
  coordenada.
- Escolha a folga nos ouros, escreva-a na rodada e aplique-a igual na T8.2.
- Matriz de confusão dono × rede (com "nada") e, para cada perda, a causa (a) nada marcado,
  (b) classe errada, (c) a nota nem foi lida. Recorte de cada caso na pasta da frente.
- Abafada (x) e o que está "fora da régua" ficam à parte. Reporte tudo também sem o Room 335.
- Técnica inventada só nas fontes com marca completa (seção 10, item 4); nas páginas não
  conferidas do End of Beginning e do Room 335 nada conta.

F0.2: para cada região do dono que inclui a corda 1 (e símbolo marcado acima dela), meça no
recorte DO PRODUTO se a tinta do arco fica inteira, cortada ou fora. Não use o recorte da
ferramenta do dono (tem folga de 1,5 passo). Olhe os casos: letra e nome de acorde acima da
tab parecem arco.

Território: módulos tab/tecnica_regua*.py e tests/test_tecnica_regua*.py; saída só em
TAB_FRENTE_0 (tab/caminhos.py, data/saida/tab_frentes/f0_tecnica/); rodadas 0101–0109. Sem
porta.

Pare e relate se: o CA1 não bater; as regiões por fonte não somarem 415 (114, 5, 32, 177, 87);
mais de 10 % das regiões casarem com mais de um par de notas possível.

Entregue: regua_tecnica.json, topo.json, os recortes e a folha dos cortados, a rodada 0101
(F0.1) e a 0102 (F0.2), gate verde, commit no branch, resumo curto em português. O resumo tem
de dizer: por classe, quanto da perda é (a), (b) e (c); que fração das regiões de legato (h, p,
prolongamento, mordente) a rede ACHA (isso decide entre A1, A2 e B); e quantas marcas da corda
1 estão cortadas, com o denominador. Não proponha mudar o recorte: isso é da sessão principal.
```

## Briefing — C1 (rolagem)

```text
Você trabalha na worktree da frente C1 da tablatura do projeto chorinho. Leia inteiro, antes de
rodar qualquer coisa: AGENTS.md; docs/pesquisa/tablatura-frentes.md (seções 1 a 6, a Frente C
na seção 7, e as seções 8, 9 e 10); docs/pesquisa/tablatura-onda1-briefings.md (regras comuns);
a §4 de docs/pesquisa/tablatura.md; no ESTADO.md, o parágrafo "D7 (rolagem)" e as decisões da
régua de tempo ("régua aceita o rótulo até 1 quadro antes da coluna" e "cursor em trânsito vale
a última coluna passada"); tab/leitor.py.

Tarefa: a C1 — costura da tablatura que rola, ancorada nas barras de compasso, com o mapa
x_partitura → t. Siga o "Como" da C1 na ordem. Faça o CA1 primeiro (regras comuns).

- Os rolantes do censo estão em data/saida/censo/censo_cache.jsonl, campo forma == "rolante"
  (66 linhas; o de tv cifras é ASCII e fica fora). Escolha 3 vídeos de canais diferentes
  (mr. tabs, leonardo ramos, kenneth acoustic) e CONFIRME NO OLHO que rolam: guarde 4 quadros
  de cada. Se um não rolar, troque e registre.
- Deslocamento por dois caminhos (phaseCorrelate puro e ancorado nas barras), contra 20 pares
  medidos à mão por vídeo. Mascare o que não anda (marcador, mão, logo, legenda). Confira a
  continuidade: o erro de um compasso inteiro parece certo na soma.
- Só depois de o deslocamento passar: panorama, mapa monotônico com degraus (pausa do
  professor), leitura em janelas com sobreposição, junção pelo x_partitura sem duplicar.
- O score_capture é GPL-3.0: use a ideia (barras como âncora), nunca o código.
- Quadros só pelo tab/leitor.py (44 % do acervo é AV1; nada de cv2.VideoCapture direto). Um
  vídeo por vez; registre quantos quadros leu de cada.
- Rolagem vertical e vídeo que mistura página e rolagem: conte, meça por trecho, deixe fora.
- Não edite tab/video.py nem o caminho paginado: o caminho rolante fica em tab/rolagem_*.py e
  roda à parte. A identidade dos 8 ouros paginados a sessão principal confere na integração.

Gabarito do dono: monte 1 vídeo rolante em telas do panorama para a ferramenta do ouro
(tab.ouro_video servir), tudo na pasta da frente. Teste a ferramenta numa CÓPIA do arquivo de
ouro, nunca no que o dono vai rotular (ela grava a cada clique). Para servir, acrescente
-p 127.0.0.1:8111:8111 ao podman run e use --porta 8111 --host 0.0.0.0. Não chame o dono:
deixe a pasta e o comando prontos e avise a sessão principal, que leva ao dono.

Território: módulos tab/rolagem_*.py e tests/test_rolagem_*.py; saída só em TAB_FRENTE_C
(data/saida/tab_frentes/fc_rolagem/); rodadas 0150–0169. Porta 8111.

Aceite (congelado): deslocamento com erro mediano ≤ 1 px contra os pares à mão nos 3 vídeos;
panorama sem compasso duplicado nem faltando, olhado, com a folha. No gabarito do dono: casa +
corda ≥ 0,99 nas casadas, revocação ≥ 0,98, inventadas ≤ 2 %, instante na coluna certa em
≥ 0,95 das colunas, com a régua de tempo da fase 5. Pare se o deslocamento não chegar a 1 px
nem com a âncora nas barras: descreva os casos antes de montar panorama.

Entregue: o deslocamento e o mapa por vídeo (JSON), as folhas com os quadros e o panorama, a
rodada 0150 (e seguintes, se precisar), o material do gabarito pronto e testado numa cópia,
gate verde, commit no branch, resumo curto em português. Diga quantos rolantes do censo você
olhou e quantos rolavam de fato.
```

## Briefing — D1 (o som confere a casa)

```text
Você trabalha na worktree da frente D1 da tablatura do projeto chorinho. Leia inteiro, antes de
rodar qualquer coisa: AGENTS.md; docs/pesquisa/tablatura-frentes.md (seções 1 a 6, a Frente D
na seção 7, e as seções 8, 9 e 10); docs/pesquisa/tablatura-onda1-briefings.md (regras comuns);
a §6 de docs/pesquisa/tablatura.md; as rodadas 2001 (convenção do t_amostra0), 2004
(alinhador), 2011 (alarme de leitura) e 2016 (lote 2) em docs/rodadas/.

Tarefa: a D1 — para cada nota lida, a altura esperada (corda + casa + afinação) confere com o
espectro no instante do som? Siga o "Como" da D1. Faça o CA1 primeiro (regras comuns).

Dados:
- Áudio alinhado da trilha áudio: data/saida/audio/a5/*.audio.json (Retrato/mvp, La Vie en
  Rose, From This Place e Room 335, que têm ouro), data/saida/audio/a4/lote1/ e
  data/saida/audio/a4/lote2/. Confira por caminho de vídeo qual ouro ou tela da T8.2 cada um
  cobre.
- Cada .audio.json diz no campo "produto" QUAL leitura foi alinhada (no mvp é a leitura antiga
  de data/saida/conserto_v2/). A régua de casa (o que é erro de verdade) tem de ser feita sobre
  essa MESMA leitura, com tab.avaliar_video contra o ouro. Nota de outra leitura não tem
  instante de som.
- O FLAC fica no cache de áudio (/cache/audio). Monte o cache só para leitura, acrescentando
  -v /run/media/gabriel/3014CD4714CD1130/chorinho_cache:/cache:ro ao podman run. Se faltar
  algum, extraia com tab.audio_extrair.garantir(..., raiz=<pasta da frente>/audio); nunca grave
  em /cache. Registre quanto áudio leu.
- Só numpy e cv2 (a imagem não tem scipy). STFT ou CQT feitas à mão.

Medida:
- Por nota: energia na fundamental e nos 2 primeiros parciais, contra a mediana da janela, no
  instante do SOM (o marcador vem 60–324 ms antes). E energia numa altura sem nota, para as
  perdidas.
- Tire da conta abafadas (x), harmônicos e notas ligadas ou de slide (sem ataque); conte
  quantas saíram.
- Confira a afinação e o capotraste de cada vídeo antes (tab/afinacao.py não foi aferido).
- Escolha o limiar nos 4 vídeos com ouro e congele-o na rodada ANTES de medir o teste. O teste
  são as telas da T8.2 que têm áudio alinhado (alinhe outras com a ferramenta da trilha áudio,
  sem editar o código dela). Se o teste tiver menos de 10 erros de casa + inventadas, pare e
  relate que o aceite não se decide com esse conjunto; não junte treino e teste.
- Relate quantas notas sinalizadas estão em exibição recusada ou de alinhamento fraco: o
  alinhador usa as alturas da tab e pode ter sido puxado pela nota errada.

Território: módulos tab/som_casa_*.py e tests/test_som_casa_*.py; saída só em TAB_FRENTE_D
(data/saida/tab_frentes/fd_som/); rodadas 0170–0179. Sem porta.

Aceite (congelado), no teste, com o limiar congelado: precisão do alarme ≥ 0,5; revocação
≥ 0,4 dos erros de casa + inventadas; alarme falso ≤ 1 % das notas certas. Pare se, nos ouros,
a precisão ficar abaixo de 0,3: relate e diga se a falha é de resolução de altura (aí a D2 vale)
ou de alinhamento (aí não vale).

Entregue: d1.json, a rodada 0170 com 10 casos olhados (recorte da tela + espectro), gate verde,
commit no branch, resumo curto em português com a tabela por vídeo (notas, sinalizadas, erros
de verdade entre elas, erros não sinalizados).
```

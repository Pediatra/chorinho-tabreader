# Plano — do estado atual ao produto (um JSON por vídeo, com cada nota no seu tempo)

> **Para quem é**: o programador (pessoa ou modelo) que vai executar o projeto a partir de
> 2026-10-10. Está escrito como se fosse para alguém júnior: cada fase diz **o que fazer**,
> **por que**, **em que arquivo**, **como saber que terminou** e **onde costuma dar errado**.
>
> **Pré-leitura obrigatória**, nesta ordem: [`AGENTS.md`](../../AGENTS.md) (o contrato),
> [`CONTEXTO.md`](../../CONTEXTO.md) (a passagem de bastão) e as seções de 2026-10-10 do
> [`ESTADO.md`](../../ESTADO.md). Este plano **não repete** o que está lá. Ele parte do que
> está lá e **corrige** alguns pontos com medições novas (§2).
>
> **Regra deste documento**: todo número citado aqui foi medido ou lido num arquivo nesta
> data, e a fonte vem ao lado. Onde algo é proposta e não medição, está escrito "proposta".

---

## 0. Resumo em 30 segundos

1. **O objetivo**: para cada vídeo do acervo que tem tablatura, um JSON com **todas** as
   notas (corda, casa, coluna, compasso, técnica/símbolo cru) e o **instante** em que cada
   uma é tocada. Os números ficam corretos, e o que não foi medido fica declarado.
2. **O que já está sólido**: a leitura do **algarismo** num quadro (0,917 / 0,986 / 0,944 nas
   3 sementes, em 72 glifos de 3 canais) e a geometria (painel, cordas, tokens).
3. **O que ainda NÃO existe**, e é o centro deste plano:
   - **a transcrição do vídeo inteiro**. Hoje `tab.transcrever` lê **um quadro**, e
     `tab.pipeline` lê **um quadro por intervalo**. A tablatura **troca de página**
     durante o vídeo (§2.2), então uma página não é a música;
   - **tempo certo**. Os números de tempo do ESTADO ("`sky guitar` 40 de 44") contam notas
     que **receberam algum tempo**, não notas com o **tempo certo**. Conferi no quadro e
     achei um deslocamento sistemático de coluna e onsets vindos de **outras páginas**
     (§2.3). Não existe gabarito de tempo;
   - **tempo em AV1** (44 % do acervo). A cadeia de tempo usa `cv2.VideoCapture` e, no AV1,
     ele **falha calado** (§2.4).
4. **A ordem proposta**: arrumar a régua → fundações (leitor de vídeo, coordenadas) →
   **gabarito de vídeo** → páginas ("telas") → leitura por tela → tempo por tela → JSON v1
   → **MARCO MVP** (um vídeo do `sky guitar` inteiro correto, que é o MVP que o dono
   pediu em `PERGUNTAS.md` J1) → censo do acervo → generalizar para os canais grandes →
   rollout em lotes com auditoria.
5. **Entre as alternativas do CONTEXTO §10**: **não** escalar agora (A). As alternativas
   B (validar a casa) e G (piloto) **entram no plano**, mas **depois** de existir um JSON de
   vídeo inteiro. Validar casa ou tempo antes disso mede uma peça que ainda vai mudar.

---

## 1. Definição de "pronto": critérios de aceitação do objetivo

O objetivo está **concluído** quando **todos** os critérios abaixo forem verdade, medidos com
os instrumentos da Fase 2 e registrados no `ESTADO.md` com o comando que os reproduz.

Os limiares são **proposta** minha. O dono nunca respondeu H2/H3/H7 do `PERGUNTAS.md` (ver
§5, decisão D1). Se ele mudar um limiar, mude **aqui** e registre a data.

| # | critério | como medir | limiar (proposta) |
| --- | --- | --- | --- |
| **CA-1** | **Cobertura do produto**: todo vídeo do acervo tem uma saída: JSON v1 válido ou registro de recusa com motivo | `tab.lote` + `tab.esquema` sobre a pasta de saída | **100 %** dos vídeos do censo; exceção não tratada ≤ 0,5 % |
| **CA-2** | **Casa e corda** no ouro de vídeo (≥ 9 vídeos, ≥ 7 canais, cobrindo os canais que somam ≥ 80 % do acervo) | `tab.avaliar_video` | acerto de casa+corda nas notas casadas ≥ **0,97** em cada vídeo (mediana ≥ 0,98); revocação ≥ **0,95** |
| **CA-3** | **Nota inventada** (nota numérica entregue que não existe no ouro) | `tab.avaliar_video` | ≤ **0,5 %** por vídeo; **0** no vídeo do MVP |
| **CA-4** | **Casa fora do ouro de vídeo**: amostra estratificada dos 17 canais | `tab.avaliar_video --so-casa` | ≥ **0,95** em cada canal entregue; canal abaixo disso sai com `casa_validada: false` no JSON |
| **CA-5** | **Tempo certo** onde o JSON diz `medido: true` | instantes sorteados do ouro (§Fase 2) | estado correto em ≥ **0,95** dos instantes com coluna acesa |
| **CA-6** | **Zero tempo falso**: onde o ouro diz "nenhuma coluna acesa / sem marcador", o JSON não pode afirmar tempo | idem | **0** telas com `medido: true` nos vídeos sem marcador do ouro |
| **CA-7** | **Invariantes de honestidade** em toda saída | testes do gate + `tab.esquema` | 100 %: todo `medido: false` tem `motivo`; todo `t_ini` cai dentro de uma exibição da sua tela; notas da mesma coluna têm o mesmo onset |
| **CA-8** | **A régua antiga não cai** | `tab.avaliar` nas 3 sementes oficiais | cada semente ≥ a referência (66/72, 71/72, 68/72) |
| **CA-9** | **Auditoria do rollout**: 20 vídeos sorteados do lote final (estratificados por canal) rotulados depois do rollout | `tab.avaliar_video` | métricas a até **0,03** das do ouro (CA-2/CA-5). Se ficar pior, a régua não representa o acervo |
| **CA-10** | **Aceite do dono** | folha de conferência (`tab.conferir`) do vídeo do MVP e de 3 vídeos do rollout | aprovação **escrita** do dono no `ESTADO.md` |
| **CA-11** | **Engenharia** | gate | `make gate` verde; forma do JSON única (um esquema só); **zero** `cv2.VideoCapture` fora de `tab/leitor.py` |

> **Fora do "pronto"** (fica registrado como dívida, não bloqueia): significado de símbolo e
> técnica (hoje com precisão 0,197 como PISO, mas o glifo cru é guardado), tempo por áudio
> nos vídeos sem marcador, tab ASCII, partitura de 5 linhas e afinação medida (até ser
> validada, o JSON declara "standard, não medida").

---

## 2. Onde estamos de verdade (diagnóstico de 2026-10-10)

### 2.1 A régua do algarismo: o número oficial é 0,949 em 72 glifos (o AGENTS.md está atrasado)

- `AGENTS.md` e `artefatos/LEIA-ME.md` dizem **0,889 em 96 glifos / 4 canais**;
- o `ESTADO.md` (seção "escopo do gabarito", linha ~239) registra que o `raman korshun` saiu
  (guitarra elétrica, decisão do dono em 2026-10-09). O resultado é **72 glifos / 3 canais**:
  66/72, 71/72 e 68/72, média **0,949**. A **discrepância do CONTEXTO §2 é só isso**, e
  confere com o arquivo: `data/gold/gabarito.json` tem 4 amostras, e a do `raman` tem a chave
  `descartada`;
- **o 0,949 não é ganho**: o denominador mudou (o ESTADO já diz isso);
- **o produto não usa a régua**: `MODELO_PADRAO = artefatos/glifo_sint.pt`, e esse arquivo
  **não está** na tabela de procedência do `artefatos/LEIA-ME.md`. Não se sabe qual
  semente/comando o gerou.

### 2.2 Não existe transcrição do vídeo inteiro, e a tablatura troca de página

Lido no código:

- `tab/transcrever.py:main` lê **um** quadro (`ler_quadro(video, --inicio)`), reconhece
  **uma** linha e associa tempo a ela;
- `tab/pipeline.py:transcrever_intervalo` lê **um** quadro (`melhor_amostra`) por intervalo de
  presença (6 frações por vídeo).

Medido nos quadros de `sky guitar/retrato brasileiro - tab & lesson.mp4` (679 s), com a imagem
aberta:

| instante | o que está na tela |
| --- | --- |
| 245,5 s | compassos 1–4, marcador na **coluna 1** |
| 266,5 s | compassos **5–8** (outra página) |
| 339,5 s | compassos 1–4 **de novo** (a aula repete o trecho), marcador no compasso 3 |
| 420 s | compassos **17–20** |

Ou seja: **o vídeo é uma sequência de páginas no tempo**, que pode repetir. Uma página só não
representa a música. Para ter o produto falta **segmentar o vídeo em telas**, ler cada tela
e associar o tempo **dentro da exibição de cada tela**.

### 2.3 Os números de tempo do ESTADO não são tempo certo

O JSON `data/saida/piloto/sky2.json` (o "40 de 44"), conferido contra os quadros acima:

1. **Erro de espaço de coordenada (medido).** `painel.refinar` recorta a ROI em x e **não
   guarda o deslocamento**. Neste vídeo o recorte começa em **x0 = 70 px**. O `x` das notas
   está no espaço da **ROI recortada**, e o `x` do marcador (`cursor.rastrear`, que só corta
   em y) está no espaço do **quadro**. Efeito: no quadro de 245,5 s o marcador está na
   coluna 1 (x da ROI = 154, x do quadro ≈ 228). Comparado sem o deslocamento, x = 228 cai
   na célula da coluna 3 (x da ROI = 245; a fronteira com a coluna 2 fica em 222). O JSON
   deu à coluna 3 o onset 245,25 s, e a coluna 1 ficou **sem** tempo. O mesmo erro existe em
   `estado.estado_por_cor`, que recorta `quadro[..., tk.x0:tk.x1]` sem somar o deslocamento.
   No `mr. tabs` o recorte foi x0 = 0, então lá o erro não aparece por acaso.
2. **Onsets vindos de outra página.** `rastrear` percorre o **vídeo inteiro**, e o onset é "a
   primeira vez que o marcador entra na célula", em **qualquer** página. A nota da coluna 2
   (corda 5, casa 2, x = 199) recebeu **266,1 s**, quando a tela mostra o compasso 5. Os
   onsets do JSON vão de 239 s a 584 s para notas de **uma** página.
3. **Acorde recebe no máximo um onset.** Duas notas com o mesmo x deixam a célula de uma
   delas vazia (`nota_do_x` usa o ponto médio entre vizinhos, que vira o próprio x). No
   `sky2.json` o acorde da coluna 1 (cordas 2 e 6) ficou sem tempo.
4. **Sintoma**: ordenando as notas por x, os onsets **invertem** a ordem em 12 de 39 pares
   (`sky2.json`) e em 8 de 15 (`mrtabs.json`).

**Conclusão**: "notas com tempo" mede quantas notas receberam algum número. É o mesmo tipo
de erro do histórico "323 notas com tempo eram 3 instantes" (AGENTS.md regra 3). **Não existe
gabarito de tempo**, e por isso o erro passou. Os números "sky 40/44", "mr. tabs 16/68" e
"serge 47/49" devem ser registrados como **não validados** (tarefa T0.3).

### 2.4 AV1: a cadeia de tempo falha calada em 44 % do acervo

Medido no container, em `mr. tabs/blind melon - no rain ….mp4` (codec `av1`):
`cv2.VideoCapture` **abre** (`isOpened() = True`) e informa `FRAME_COUNT = 16972`, mas
`grab()` falha em **30 de 30** tentativas. `cursor.rastrear` devolve **0 amostras**, que é
indistinguível de "vídeo sem marcador".

Usam `cv2.VideoCapture` direto: `cursor.rastrear`, `transcrever.varrer_cursor`,
`transcrever.tempos_do_cursor`, `transcrever.serie_cursor`, `transcrever.main` (duração),
`pipeline.amostrar_presenca`, `pipeline.serie_do_marcador`, `marcador._amostrar_cv2` e
`varredura.Leitor` (este tem fallback para ffmpeg). Só o observador de **cor** usa
`ler_quadro`, por isso o `mr. tabs` (AV1) deu algum tempo.

> Correção ao CONTEXTO §3: lá está "AV1 → `FRAME_COUNT=0`". Neste arquivo o
> `FRAME_COUNT` veio **preenchido**. O que falha é a **decodificação**. A consequência é a
> mesma, só que mais traiçoeira: o código pensa que leu o vídeo.

### 2.5 Outros fatos que o plano usa

| fato | fonte |
| --- | --- |
| Gate **verde** hoje: `ruff check` "All checks passed!", `ruff format --check` ok, **120 testes** passando | rodado no container em 2026-10-10 |
| Acervo hoje: **3.899 vídeos / 255 GB / 17 canais** (o CONTEXTO diz 3.908 / 183 GB) | `find` no HD em 2026-10-10 |
| Vídeos por canal: violaodecria **1.037** · tv cifras **522** · sky guitar 417 · guitar dell'arte 361 · cifra club 341 · leonardo ramos 290 · robert lunn 229 · iwaki 164 · shin izumi 149 · pablo romé 112 · kimny's guitar 108 · guitarous 55 · serge kottelat 38 · transcriptor 35 · mr. tabs 22 · paolo d'angelo 14 · tv on guitar 5 | idem |
| Os **2 maiores canais** (violaodecria + tv cifras = **40 %** do acervo) quase não aparecem nas medições até hoje | ESTADO / CONTEXTO |
| O sintético sorteia casas até **24**, mas o gabarito só tem **0–7** | `tab/sintetico.py:132` |
| A forma do JSON muda conforme o caminho do código (`iwaki2.json` não tem `andamento` nem `notas_por_compasso`) | CONTEXTO §17.2 |
| No `sky guitar` o marcador também **pinta o algarismo** (azul/verde) além da faixa | quadros de 245,5 s e 266,5 s |
| Rótulos do gabarito de glifos são por **índice de token**: se a segmentação mudar, o índice muda e o rótulo passa a apontar para outro token sem erro nenhum | `data/gold/gabarito.json` |

---

## 3. O desenho-alvo (para entender antes de codar)

```
vídeo
  │  tab/leitor.py ── único jeito de ler vídeo (ffmpeg em passada única; cv2 só se funcionar)
  ▼
presença ao longo do tempo (onde há tablatura de 6 cordas)
  ▼
TELAS: o vídeo vira uma sequência de exibições de páginas
  tela = conteúdo da página (pode reaparecer); exibição = [t0, t1] em que ela está na tela
  ▼
LEITURA POR TELA (uma vez por tela, numa imagem limpa do marcador)
  notas com x NO ESPAÇO DO QUADRO, agrupadas em COLUNAS (acorde = uma coluna)
  ▼
TEMPO POR EXIBIÇÃO (só dentro de [t0, t1] daquela exibição)
  observador de posição (faixa) e de cor (algarismo aceso) → ESTADO = coluna atual
  onset da coluna = 1º instante em que ela passa a ser a atual, em cada passagem
  ▼
JSON v1 (forma única, validado) ──► MusicXML (o exportador que já existe)
```

**Vocabulário novo** (acrescentar ao AGENTS.md na Fase 6):

| termo | significado |
| --- | --- |
| **tela** | o conteúdo de uma página de tablatura (o mesmo conteúdo que reaparece é a mesma tela) |
| **exibição** | um intervalo `[t0, t1]` em que uma tela está visível |
| **coluna** | notas da mesma tela com o mesmo x (diferença < 0,35 passo): um acorde é **uma** coluna |
| **passagem** | uma ida do marcador pelas colunas de uma exibição (a aula pode repetir) |
| **espaço do quadro** | coordenada em pixels do quadro inteiro. **Toda** coordenada que sai de um módulo para outro está neste espaço |

**Por que assim**: o erro de 2.3 vem de três atalhos: um quadro só, tempo do vídeo inteiro e
espaços de coordenada misturados. O desenho elimina os três **por construção**, e não com
remendo.

---

## 4. Como trabalhar (vale para todas as fases)

### 4.1 Ambiente

```bash
cd /var/home/gabriel/Projects/chorinho-dataset
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
C="docker compose -f compose.yaml -f compose.podman.yaml"
$C run --rm chorinho python -m tab.avaliar --modelo artefatos/oficial_2/glifo_sint.pt
```

- Se o seu shell estiver dentro do **distrobox** (sem `git` e sem `docker`), rode no host com
  `host-spawn sh -c '…'`. O `git log` precisa de **`--no-pager`**: sem isso o `less` do host
  falha com `'unknown': I need something more specific`;
- para inspecionar sem risco, monte o código **somente leitura** e mande as saídas para fora
  do repositório:
  `podman run --rm --security-opt label=disable -e PYTHONPATH=/app -w /app -v "$PWD":/app:ro
  -v /run/media/gabriel/3014CD4714CD1130/chorinho:/acervo:ro docker.io/library/chorinho:dev
  python …` (o nome curto `chorinho:dev` não resolve no podman);
- as armadilhas do CONTEXTO §3 continuam valendo (SELinux, `make build`, CDI da GPU, `/tmp`).

### 4.2 Ciclo de cada tarefa (siga sempre, nesta ordem)

1. **Leia** os arquivos que vai tocar (inteiros, na região que importa). Não adivinhe texto.
2. **Meça a linha de base** do que pode ser afetado, **antes** de mexer: `tab.avaliar` nas 3
   sementes e, a partir da Fase 2, `tab.avaliar_video` no(s) vídeo(s) de ouro.
3. **Olhe o quadro** quando o número surpreender (regra 4). Gere a imagem em `data/saida/`.
4. Implemente o **mínimo** e escreva o **teste** (sem GPU e sem acervo; use imagens/vídeos
   sintéticos gerados no teste).
5. `ast.parse` + `import` + rodar de verdade (regra 7).
6. **Meça de novo** e compare com a base. Mudança neutra ou negativa **se reverte**, e o
   número fica no ESTADO (regra 11).
7. `make gate` → só então `git commit` (um commit por tarefa, com o número no título).
8. Registre no `ESTADO.md` (seção datada) e, no fim da fase, escreva **um** documento de
   rodada em `docs/rodadas/NNNN-titulo.md` (a próxima é a **0004**).

### 4.3 Como reportar um número (para não repetir os erros de 2.3)

Todo número de tempo é reportado como **"X de Y instantes do ouro com o estado certo"**,
nunca como "X notas com tempo". Todo número de nota é reportado com **precisão, revocação e
inventadas**, e nunca só "N notas lidas". Sempre diga **qual modelo** rodou (imprima o
caminho) e **qual commit**. Leia o JSON de saída: não confie no seu resumo impresso (o caso
`t_ini` do CONTEXTO §12).

---

## 5. Decisões que são do dono (com o padrão que o executor usa se ele não responder)

Coloque estas perguntas no `PERGUNTAS.md` (bloco novo, "4ª rodada") **na Fase 0**. Enquanto
não houver resposta, siga o ⭐ e registre que foi suposição.

| # | pergunta | ⭐ padrão proposto |
| --- | --- | --- |
| **D1** | Os limiares do §1 (casa ≥ 0,97, inventada ≤ 0,5 %, tempo ≥ 0,95) servem? (H2/H3/H7 nunca foram respondidas) | os do §1 |
| **D2** | Se a aula **repete** um trecho, o JSON traz **uma entrada por passagem** ou deduplica? (G8) | uma entrada por passagem, com `tela` e `passagem` para o consumidor deduplicar |
| **D3** | Vídeo do MVP | `sky guitar/retrato brasileiro - tab & lesson.mp4` (já explorado; H.264; paginado; faixa + cor) |
| **D4** | Vídeo **sem marcador**: entrega as notas com o tempo **da tela** (início/fim da exibição) declarado, ou sem tempo nenhum? | notas + `exibicoes` da tela; `t_ini` por nota fica `null` com motivo; áudio fica para depois |
| **D5** | Canal cuja casa não passar no CA-4: não entrega a casa, ou entrega com `casa_validada: false`? | entrega com a bandeira |
| **D6** | Tempo do dono para rotular: o plano pede **~2 h** até o MVP e **~8 h** até o fim (estimativa na Fase 2) | — (só informar) |
| **D7** | Tablatura **rolante** (contínua): entra no escopo agora? | só se o censo (Fase 7) mostrar ≥ 10 % do acervo |

---

## 6. As fases

Cada fase tem: **objetivo · tarefas passo a passo · testes · critério de aceitação (CA da
fase) · armadilhas**. Uma fase só começa quando o CA da anterior estiver verde, com exceção
da Fase 7 (censo), que só depende da Fase 1 e pode rodar em segundo plano.

---

### Fase 0 — Arrumar a régua (meio dia)

**Objetivo**: ninguém mais citar número errado, e o produto passar a usar um modelo com
procedência.

**T0.1 — Atualizar o número oficial.**
Em `AGENTS.md`, `README.md` e `artefatos/LEIA-ME.md`: trocar "0,889 em 96 glifos / 4
canais" por "**0,949** (66/72, 71/72, 68/72) em **72 glifos / 3 canais** (`raman korshun`
descartado em 2026-10-09: guitarra elétrica)". Deixe a nota de que o 0,949 **não é ganho**,
só mudança de denominador. Atualize também a contagem do acervo (3.899 / 255 GB).

**T0.2 — O produto usa um modelo com procedência.**
1. Meça o `artefatos/glifo_sint.pt` atual com `tab.avaliar` e anote.
2. Proposta: `MODELO_PADRAO` em `tab/caminhos.py` aponta para **`artefatos/oficial_3/glifo_sint.pt`**,
   a semente **mediana** (0,944). **Não** escolha a melhor semente: escolher pelo gabarito de
   72 glifos é sobreajustar a régua.
3. Registre a escolha numa decisão `docs/decisoes/0008-modelo-do-produto.md` (contexto,
   opções, decisão, consequência).
4. Opcional, só **medido**: comitê das 3 sementes (média das probabilidades). Só adote se for
   ≥ à mediana no `tab.avaliar` **e**, depois da Fase 2, no ouro de vídeo.

**T0.3 — Corrigir o registro.** No `ESTADO.md`, seção nova datada: os números de tempo de
2026-10-10 ("sky 40/44", "mr. tabs 16/68", "serge 47/49") ficam **não validados**, com as
quatro evidências de §2.3 e §2.4. Acrescente à tabela "não repetir":
- "contar notas que receberam tempo sem gabarito de tempo";
- "associar a série do marcador do vídeo inteiro às notas de um quadro";
- "misturar x da ROI recortada com x do quadro";
- "`cv2.VideoCapture` fora do leitor (AV1 abre, informa FRAME_COUNT e não decodifica)".

**T0.4 — Gate que barra sozinho.** No `Makefile`, troque a linha `COMPOSE := docker compose`
por `COMPOSE ?= docker compose -f compose.yaml -f compose.podman.yaml` (com `?=` ela pode ser
sobrescrita num host com Docker de verdade) e acrescente um alvo `gate` que pare no primeiro
erro. O `make` já para com código ≠ 0, desde que você **não** use `|| echo`. Recue as linhas
da receita com **TAB**:

```make
gate:
	$(COMPOSE) run --rm -e RUFF_CACHE_DIR=/tmp/ruffcache chorinho ruff check .
	$(COMPOSE) run --rm -e RUFF_CACHE_DIR=/tmp/ruffcache chorinho ruff format --check .
	$(COMPOSE) run --rm chorinho pytest tests/ -q -p no:cacheprovider
```

Daqui em diante, **só** `make gate && git commit …`. (O `-p no:cacheprovider` elimina o aviso
de permissão no `.pytest_cache` do root.)

**T0.5 — Perguntas ao dono** (§5) no `PERGUNTAS.md`.

**CA da Fase 0**
- [ ] `grep -rn "0,889" AGENTS.md README.md artefatos/LEIA-ME.md` só aparece como histórico;
- [ ] `tab.avaliar` com o `MODELO_PADRAO` novo imprime o caminho e dá 68/72 (ou o que T0.2 medir), registrado;
- [ ] `make gate` existe e falha de propósito num teste quebrado (prove isso uma vez e reverta);
- [ ] ESTADO com a seção de correção; PERGUNTAS com D1–D7.

---

### Fase 1 — Fundações: um leitor de vídeo, um espaço de coordenadas, colunas (2–3 dias)

**Objetivo**: acabar com as duas causas mecânicas de erro (AV1 calado e x misturado) antes de
construir em cima.

**T1.1 — `tab/leitor.py`: o único jeito de ler vídeo.**

Antes de escrever, **leia** `marcador._amostrar_ffmpeg` (decodifica uma janela em **uma
passada** com o filtro `fps`; o caminho de um processo por amostra foi medido em 128 s por
vídeo AV1) e `varredura.Leitor`. Reaproveite a ideia em vez de reinventar.

Interface proposta (Google docstrings, nomes em português):

```python
def info(caminho: str) -> dict:
    """codec, largura, altura, fps, duracao_s — via ffprobe (uma chamada)."""

def quadro_em(caminho: str, t_s: float) -> np.ndarray | None:
    """Um quadro no instante t (segundos)."""

def quadros(
    caminho: str, t0: float, t1: float, qps: float,
    recorte_y: tuple[int, int] | None = None,
) -> Iterator[tuple[float, np.ndarray]]:
    """(t, quadro) de t0 a t1 a `qps` quadros por segundo, numa passada de ffmpeg.

    ffmpeg -ss t0 -i V -t (t1-t0) -vf fps=qps[,crop=w:h:0:y0] -f rawvideo -pix_fmt bgr24 -
    lendo largura*altura*3 bytes por quadro do stdout.
    """
```

Regras:
- trabalhe com **segundos**, nunca com índice de quadro (fps varia: o `mr. tabs` tem 60);
- o caminho `cv2` só pode ser usado se ele **decodificar** de fato um quadro de teste (não
  basta `isOpened()`, ver §2.4);
- `ler_quadro(caminho, frac)` e `duracao(caminho)` de `tab/inventario.py` passam a delegar
  para o leitor (mantenha as assinaturas: são usadas no projeto todo).

Testes (`tests/test_leitor.py`, sem acervo):
- gerar no `tmp_path` um vídeo curto com `cv2.VideoWriter` (codec `mp4v`) em que o quadro
  *k* tem uma barra branca em `x = 10·k`. Ler com `quadros(..., qps=fps)` e conferir que a
  barra está onde o tempo diz (isso prova o mapeamento t → quadro);
- `info()` devolve a duração dentro de 1 quadro;
- teste **de integração** (marca `integration`) com um AV1 real do acervo (o `mr. tabs` do
  §2.4): `quadros()` devolve quadros (> 0). O encoder de AV1 **não existe** no container
  (`ffmpeg -encoders` só tem libx264/mpeg4), por isso o AV1 só é testado com arquivo real.

**T1.2 — Migrar todos os chamadores e travar a regra.**
Troque `cv2.VideoCapture` por `tab.leitor` em: `cursor.rastrear`, `transcrever.*`,
`pipeline.*`, `marcador._amostrar_cv2` e `varredura.Leitor`. Depois, um teste do gate:

```python
def test_ninguem_le_video_por_fora():
    """cv2.VideoCapture só em tab/leitor.py (AV1 abre e não decodifica: §2.4 do plano)."""
    for arq in Path("tab").glob("*.py"):
        if arq.name != "leitor.py":
            assert "VideoCapture(" not in arq.read_text(), arq
```

Medição obrigatória **antes e depois** (regra 9: leitura é entrada do modelo): o
`tab.avaliar` nas 3 sementes tem de dar **igual**. Se não der, o leitor novo entrega quadro
diferente (cor/escala). Pare e olhe.

**T1.3 — Um espaço de coordenadas: o do quadro.**
1. `painel.Candidato` ganha `x0: int = 0`. `refinar` passa a gravar `x0 = c.x0 + x0_recorte`
   (no `sky guitar` do §2.3 deve dar **70**);
2. **não mexa** no `x` que o `reconhecer_linha` devolve (ele é da ROI e é entrada do
   classificador). Converta **na fronteira**: quem monta notas para fora grava
   `x_quadro = cand.x0 + nota["x"]`;
3. `estado.estado_por_cor`: recorte `quadro[cand.y0+tk.y0 : cand.y0+tk.y1, cand.x0+tk.x0 :
   cand.x0+tk.x1]`;
4. regra de código: **nome de variável diz o espaço** (`x_quadro`, `x_roi`, `y_faixa`). Variável
   chamada só `x` que atravessa módulo é bug de revisão.

Testes:
- quadro sintético com um painel desenhado em `x ∈ [300, 900]` e margem à esquerda: depois de
  `escolher`, `cand.x0 > 0` e `x_quadro` de uma nota cai em cima do algarismo desenhado;
- **teste de regressão com o caso real** (marca `integration`): no `retrato brasileiro`, em
  245,5 s o marcador tem de cair na **coluna 1**.

**T1.4 — Colunas (o acorde é uma coluna).**
`tab/colunas.py`: `agrupar_colunas(notas, passo, tol=0.35) -> list[Coluna]`, com o x (mediana)
no espaço do quadro e os índices das notas. O estado passa a operar sobre **colunas**
(`nota_do_x(x, xs_das_colunas)`) e o onset da coluna vale para todas as notas dela.
Teste: duas notas com o mesmo x recebem o **mesmo** onset (hoje uma fica sem).

**CA da Fase 1**
- [ ] `make gate` verde, com os testes novos (leitor, coordenadas, colunas, "ninguém lê por fora");
- [ ] `tab.avaliar` idêntico nas 3 sementes (66/71/68 de 72), antes e depois;
- [ ] no AV1 do `mr. tabs`, `rastrear` passa a devolver amostras (> 0) **ou** declara por que não;
- [ ] no `retrato brasileiro`, `cand.x0 == 70` e o marcador de 245,5 s cai na coluna 1.

**Armadilhas**: `-ss` antes do `-i` é rápido e, no ffmpeg atual, preciso. Confira com o teste
da barra, não com fé. O HD é compartilhado e lento, então meça o tempo por vídeo e anote.

---

### Fase 2 — O gabarito de vídeo ("ouro de vídeo") e a régua do produto (3–4 dias + ~1 h do dono)

**Objetivo**: poder responder, com número, "este JSON de vídeo está certo?". Sem isso, todas
as fases seguintes medem às cegas, que foi o que aconteceu em §2.3.

**Ideia central (leia duas vezes)**: o ouro tem **duas partes independentes**:
1. **conteúdo**: as telas distintas do vídeo e, em cada uma, as notas (corda, casa, x). É o
   que mede a casa;
2. **instantes**: ~40 instantes sorteados onde há tablatura e, em cada um, **qual coluna está
   acesa** (ou "nenhuma"). É o que mede o tempo, e mede exatamente a formulação acordada com
   o dono ("qual nota está acesa"). Rotular um instante custa **um clique**.

**T2.1 — Preparar o material a rotular: `python -m tab.ouro_video preparar VIDEO`.**
1. Amostre a faixa de tablatura a cada 2 s (`leitor.quadros`). Use o `painel.escolher` num
   quadro de referência para achar o painel. Se ele mudar de lugar, reavalie.
2. Agrupe quadros consecutivos "iguais" com uma medida **simples e independente** do sistema
   que vai ser testado: diferença média absoluta da faixa em tons de cinza, ignorando pixels
   coloridos (saturação alta = marcador). Melhor errar para **mais** telas (o dono junta)
   do que para menos.
3. Grave em `data/saida/ouro_video/<slug>/`: `telas/NNN.png` (faixa ampliada 2×),
   `instantes/MMM.png` (40 instantes sorteados **dentro** da presença, faixa inteira) e
   `pre.json` com a leitura atual do modelo para cada tela (corda, casa, `x_quadro`), que é
   só um **pré-preenchimento**.

**T2.2 — A ferramenta de rotular que GRAVA enquanto o dono clica: `python -m tab.ouro_video servir`.**
É a lição do CONTEXTO §18.2: as 200 respostas da auditoria do pool **se perderam** porque
viveram só no navegador.
- servidor HTTP mínimo (`http.server` da stdlib), **só em `127.0.0.1`**, como job de fundo
  gerenciado (o processo solto morre com o shell);
- `GET` serve a página; `POST /salvar` grava `data/gold/ouro_video/<slug>.json` **a cada
  alteração** (autosave), mais um botão "baixar JSON" de reserva;
- página de **tela**: a imagem com uma caixa por nota pré-lida; cada caixa tem um campo com a
  casa (o dono corrige só o que está errado), um botão "não é nota" e um clique na imagem para
  **acrescentar** nota que faltou (a corda sai da linha mais próxima);
- página de **instantes**: a imagem; o dono clica na **coluna acesa** ou em "nenhuma acesa" /
  "sem tablatura";
- ordem: telas na ordem do vídeo; instantes **embaralhados**. O dono já foi enganado por
  uma ordem que punha os "sem marca" primeiro (CONTEXTO §13.6).

Formato (`data/gold/ouro_video/<slug>.json`):

```json
{
  "video": "sky guitar/retrato brasileiro - tab & lesson.mp4",
  "como_foi_rotulado": "pre-preenchido pelo modelo <caminho>; conferido e corrigido pelo dono por leitura visual",
  "rotulado_em": "2026-10-..",
  "telas": [
    {"id": 1, "quadro_ref_s": 245.5,
     "notas": [{"corda": 2, "casa": 0, "x_quadro": 224}, {"corda": 6, "casa": 0, "x_quadro": 224}]}
  ],
  "instantes": [
    {"t": 245.5, "tela": 1, "coluna_x_quadro": 224},
    {"t": 101.0, "tela": null, "coluna_x_quadro": null, "obs": "sem tablatura"}
  ]
}
```

> **Rótulo é do dono, e é contrato** (CONTEXTO §13.2). O pré-preenchimento só acelera: o
> campo `como_foi_rotulado` deixa claro que ele **conferiu** cada tela. Se o dono só der
> "ok" sem olhar, o ouro herda o erro do modelo. Por isso mostre a imagem ampliada ao lado de
> cada número.

**T2.3 — A régua: `python -m tab.avaliar_video --ouro data/gold/ouro_video/<slug>.json --json <saida.json>`.**

1. **Casamento de telas**: para cada instante do ouro com tela, procure a exibição prevista
   que contém `t`. A tela do ouro casa com a tela prevista que mais aparece nesses instantes.
2. **Casamento de notas** dentro de cada par de telas: mesma corda e `|Δx_quadro| ≤ 0,5
   passo`, guloso por menor distância.
3. **Métricas de nota**: `notas_ouro`, `entregues` (só casa numérica), `casadas`,
   `casa_certa`, **`inventadas`** (entregues sem par), `perdidas` → precisão, revocação e
   acerto de casa nas casadas.
4. **Métrica de tempo**: para cada instante do ouro, qual coluna o JSON diz que é a atual em
   `t` (a coluna cujo onset mais recente ≤ t, na passagem em curso). Conte **acerto**,
   **erro**, **"JSON sem tempo"** e **"tempo falso"** (o ouro diz "nenhuma" e o JSON afirma
   uma coluna). Tolerância: aceite também a coluna **imediatamente anterior** se `t` estiver a
   ≤ 0,2 s de um onset previsto (resolução da amostragem), e declare essa tolerância na saída.
5. Imprima **sempre** os denominadores e o caminho do modelo.

Testes: dicionários pequenos montados à mão (um caso perfeito, uma nota inventada, uma
perdida, um acorde, um instante "nenhuma" com tempo falso). A régua é código como qualquer
outro: tem de ter teste.

**T2.4 — Rotular o vídeo do MVP (D3) com o dono.**
Estimativa para o `retrato brasileiro`: ~20 telas distintas × ~1,5 min + 40 instantes × 5 s
≈ **35–45 min** do dono. Depois de salvo, rode o `tab.avaliar_video` no JSON **atual**
(o `tab.transcrever` de hoje), que é a **linha de base honesta** do produto. Espere um
número baixo: é para isso que ela serve.

**CA da Fase 2**
- [ ] `data/gold/ouro_video/<slug>.json` do vídeo do MVP existe, salvo pela ferramenta, com
      `como_foi_rotulado`;
- [ ] o `tab.avaliar_video` roda 2× e dá o **mesmo** número (reprodutível);
- [ ] a linha de base do produto atual está no ESTADO, com precisão, revocação, inventadas e
      estado (X de 40);
- [ ] testes da régua no gate.

---

### Fase 3 — Telas: segmentar o vídeo no tempo (3–4 dias)

**Objetivo**: `telas(video) -> list[Tela]`, com as exibições `[t0, t1]` de cada página e as
repetições reconhecidas.

**T3.1 — Presença grossa.** Varra o vídeo a cada 5 s com `escolher` (ou reaproveite o
`tab.varredura`) e marque os trechos com painel. A tablatura aparece e some (regra 10).
Refine as bordas de cada trecho para ≤ 1 s com busca binária.

**T3.2 — Assinatura da tela.** Para cada amostra a **2 qps** dentro da presença:
1. recorte a faixa do painel (espaço do quadro);
2. **tire o marcador**: pixels com saturação alta (HSV S > ~60) viram o fundo (mediana da
   faixa). O marcador é colorido e a tinta da tablatura é acromática. **Meça** isso no
   `sky guitar` (faixa azul translúcida + algarismo pintado) antes de confiar;
3. binarize (Otsu) e reduza (¼ da resolução) → máscara booleana.

**T3.3 — Troca de tela.** Distância entre amostras consecutivas = 1 − IoU da tinta.
**Meça antes de escolher o limiar** (regra 2): faça o histograma das distâncias no vídeo do
MVP e em mais 2 vídeos (um `serge kottelat`, um `cifra club`). Deve haver dois montes
(mesma tela × troca). O limiar fica no vale e vai para uma constante com o comentário do que
foi medido, como as constantes de `tab/caminhos.py`.

**T3.4 — Repetição.** Cada tela nova é comparada com **todas** as anteriores. Se IoU ≥
limiar de "mesma tela", ela vira **outra exibição da mesma tela** (no `retrato brasileiro`,
a página dos compassos 1–4 aparece em 245 s e em 339 s).

**T3.5 — Rolagem (só detectar).** Correlação de fase (`cv2.phaseCorrelate`) entre amostras
consecutivas: deslocamento horizontal consistente, com pico alto e diferença baixa depois de
compensar, é **rolagem**. Nesta fase só **classifique e declare** (`"modo": "paginado" |
"rolante" | "estatico"`). A implementação da rolagem é a T8.4.

**T3.6 — Saída.**

```python
@dataclass
class Tela:
    id: int
    painel: tuple[int, int, int, int]   # x0, y0, x1, y1 NO ESPAÇO DO QUADRO
    exibicoes: list[tuple[float, float]]
    quadro_ref_s: float                 # instante usado para ler (Fase 4)
    modo: str                           # paginado | rolante | estatico
```

Testes: vídeo sintético gerado no teste com 3 "páginas" desenhadas (A, B, A) e uma faixa
colorida andando por cima. Esperado: 2 telas, A com 2 exibições, e a faixa **não** gera troca.

**CA da Fase 3**
- [ ] no vídeo do MVP: ≥ **98 %** dos instantes do ouro caem numa exibição cuja tela casa com
      a tela do ouro daquele instante;
- [ ] **nenhuma** tela do ouro sem tela prevista (revocação de telas = 100 %);
- [ ] telas previstas a mais (super-segmentação) ≤ 10 %. Elas custam leitura repetida, mas
      não erram nota;
- [ ] histograma e limiar registrados no ESTADO, com a imagem em `data/saida/telas/`.

**Armadilhas**: o professor pode **sobrepor** o vídeo da mão à tablatura, ou ela pode mudar de
**tema** (claro/escuro). Nos dois casos a distância sobe sem ser troca de página. Olhe os
casos de borda no quadro antes de mudar o limiar.

---

### Fase 4 — Leitura por tela (2–3 dias)

**Objetivo**: as notas de cada tela, numa imagem **sem marcador**, com x no espaço do quadro e
agrupadas em colunas.

**T4.1 — Imagem limpa.** Proposta: a **mediana temporal** dos quadros da exibição (5–9
quadros espalhados). O marcador anda, e cada coluna só fica acesa uma fração do tempo, então a
mediana tende a apagá-lo. Alternativa: votação da leitura em K quadros. **Meça as duas** no
ouro do MVP (regra 9: o pré-processamento é entrada do modelo) e fique com a de maior acerto
de casa. Empate → a mais simples.

**T4.2 — Ler.** `reconhecer_linha` na faixa da imagem limpa → notas → `x_quadro` (T1.3) →
`agrupar_colunas` (T1.4) → compasso pelas barlines. Tokens que não são algarismo (`junk`,
`harmonico`, `tecnica`, símbolo) **não somem**: vão para `nao_notas`, com o glifo cru
(decisão do dono: símbolo não se descarta).

**T4.3 — Casa como número.** No JSON v1 `casa` é **inteiro** (hoje é string, e `"junk"` cai
no mesmo campo). Algarismo vai para `notas`, o resto para `nao_notas`.

**CA da Fase 4** (no ouro do MVP)
- [ ] acerto de casa+corda ≥ **0,99** nas notas casadas; revocação ≥ **0,98**; inventadas = **0**;
- [ ] `tab.avaliar` igual nas 3 sementes (a cadeia do algarismo não foi tocada);
- [ ] se não bater: **olhe** cada erro na imagem e classifique (painel, grade, token,
      classificador, imagem limpa) **antes** de mexer. Lembre da regra 6: o gargalo histórico
      é cobertura do gerador, não regra de visão.

---

### Fase 5 — Tempo por exibição (3–4 dias)

**Objetivo**: onsets por coluna, **só dentro da exibição**, com o observador declarado. Ou
`medido: false` com motivo.

**T5.1 — Série do estado por exibição.** Para cada exibição `[t0, t1]` de cada tela, a
**6 qps** (≈ o "passo 5 quadros" que já foi medido como necessário: 34 → 47 onsets no
`serge`):
- **observador de posição**: `detectar_cursor` no recorte da faixa → x **no espaço do
  quadro** → coluna atual (`nota_do_x` sobre as colunas);
- **observador de cor**: coloração (`destaque.coloracao`) **por coluna** (caixa da coluna no
  espaço do quadro) → coluna acesa = a que se destaca (o critério atual de `estado_por_cor`:
  ≥ 5,0 e ≥ 3× a mediana);
- **cor cumulativa** (`cifra club`: o algarismo **fica** laranja depois de tocado): a coluna
  atual é a que **acendeu agora** (coloração subiu desde a amostra anterior), não a de maior
  coloração. Teste com uma série sintética.

**T5.2 — Onsets e passagens.** Percorra a série: quando a coluna atual muda, você tem uma
transição. Uma **passagem** termina quando o estado volta para trás (exemplo: da última
coluna para a primeira). Em cada passagem, o onset de cada coluna é o **primeiro** instante
em que ela vira a atual. Exija que o estado fique estável por ≥ 2 amostras antes de aceitá-lo
(anti-ruído) e **meça** se isso ajuda ou atrapalha no ouro.

**T5.3 — Qual observador vale (por exibição, nunca por canal).** Calcule a **coerência** de
cada observador: fração de transições que avançam (+1 ou +2 colunas) e fração da exibição com
estado definido. Fica o de maior coerência, se passar de um mínimo (meça o mínimo no ouro).
Abaixo do mínimo → `medido: false` com o motivo concreto ("posição: 3 amostras com faixa em
412; cor: nenhum destaque").

**T5.4 — Sem marcador (D4).** A exibição ainda tem `t0/t1` (o tempo da tela). Grave isso na
tela, e nas notas `t_ini: null`. **Nunca** distribua tempo uniformemente pelas colunas: nota com
tempo falso é mentira.

**T5.5 — Invariantes (testes do gate).**
- todo `t_ini` ∈ alguma exibição da tela da nota;
- dentro de uma passagem, os onsets **não diminuem** com a ordem das colunas;
- todas as notas da mesma coluna têm o mesmo `t_ini` naquela passagem;
- `medido: false` ⇒ `motivo` não vazio.

**CA da Fase 5** (no ouro do MVP)
- [x] estado certo em ≥ **0,95** dos instantes com coluna acesa (reporte "X de Y"); **39 de 40** no retrato v2 (ESTADO, fechamento da Fase 5);
- [ ] **0** instantes "nenhuma acesa" com tempo afirmado;
- [ ] invariantes verdes no gate e na saída real;
- [ ] imagem de conferência: 6 instantes com a coluna que o JSON diz estar acesa desenhada por
      cima do quadro (`data/saida/conferencia/`). **Olhe** antes de comemorar.

---

### Fase 6 — JSON v1, MusicXML e a folha de conferência (2 dias) → MARCO MVP

**T6.1 — Esquema único.** `tab/esquema.py` com `validar(d: dict) -> list[str]` (lista de
erros), em Python puro (sem dependência nova). O JSON v1:

```json
{
  "esquema": "chorinho/video@1",
  "video": {"arquivo": "sky guitar/…mp4", "canal": "sky guitar", "duracao_s": 678.97,
            "codec": "h264"},
  "gerado_por": {"commit": "abc1234", "modelo": "artefatos/oficial_3/glifo_sint.pt",
                 "em": "2026-10-.."},
  "afinacao": {"valor": "standard", "medida": false},
  "casa_validada": true,
  "telas": [
    {"id": 1, "painel": [70, 296, 1854, 446], "passo": 16.0, "modo": "paginado",
     "barlines_x": [480, 1010, 1430],
     "exibicoes": [{"t0": 239.0, "t1": 262.5}, {"t0": 331.0, "t1": 352.0}],
     "tempo": {"medido": true, "observador": "posicao", "coerencia": 0.97,
               "onset": "primeiro instante em que a coluna passa a ser a atual",
               "duracoes": "inferidas (intervalo ate o proximo onset)"}}
  ],
  "notas": [
    {"tela": 1, "passagem": 1, "coluna": 1, "compasso": 1, "corda": 2, "casa": 0,
     "tecnica": null, "confianca": 0.99, "x_quadro": 224, "t_ini": 245.25}
  ],
  "nao_notas": [
    {"tela": 1, "corda": 1, "x_quadro": 508, "classe": "harmonico", "simbolo_cru": "…png"}
  ],
  "resumo": {"telas": 20, "exibicoes": 27, "notas": 512, "notas_com_tempo": 498,
             "instantes_distintos": 301, "telas_sem_tempo": 1}
}
```

- a forma é **a mesma** em todos os caminhos (com posição, com cor, sem marcador). Teste isso
  com os três casos;
- `transcrever_video(caminho) -> dict` mora em `tab/video.py`. O `tab.transcrever` vira a CLI
  fina (`python -m tab.transcrever VIDEO --json saida.json`), e o `main` valida com
  `esquema.validar` antes de gravar e **falha alto** se houver erro;
- o `tab/pipeline.py` antigo fica **intacto** até o CA-MVP passar. Depois, o ramo de tempo
  velho (`resumo`/`desliza`/`salta`) sai em commit **separado**, com o número antes/depois.

**T6.2 — MusicXML a partir do v1.** Adapte `tab/musicxml.exportar` para ler o v1 (uma parte
por vídeo, notas em ordem de `t_ini`; sem tempo → ordem de tela/coluna e duração constante
**declarada**, como já é feito hoje).

**T6.3 — Folha de conferência: `python -m tab.conferir JSON --n 12`.** Doze instantes
sorteados: o quadro, a coluna que o JSON diz estar acesa (caixa verde) e as casas lidas
escritas embaixo. É a resposta à pergunta G do CONTEXTO: *"é isso que eu quero receber?"*. O
dono olha em 2 minutos.

**MARCO MVP — critérios (todos)**
- [ ] `python -m tab.transcrever "<vídeo do MVP>" --json data/saida/produto/mvp.json` roda o
      vídeo **inteiro**, num comando, e o JSON passa no `esquema.validar`;
- [ ] contra o ouro: casa+corda ≥ **0,99**, revocação ≥ **0,98**, **0 inventadas**, estado ≥
      **0,95**, 0 tempo falso (CA-3, CA-5, CA-6 no vídeo do MVP);
- [ ] `tab.avaliar` ≥ referência nas 3 sementes (CA-8);
- [ ] `make gate` verde;
- [ ] o dono abriu a folha de conferência e o MusicXML e **aprovou por escrito** (CA-10). Esta
      é a frase J1 do `PERGUNTAS.md`: "um vídeo inteiro correto já serve (corda + casa +
      tempo, sem nota inventada)";
- [ ] rodada `docs/rodadas/0004-mvp-video-inteiro.md` escrita.

---

### Fase 7 — Censo do acervo (máquina; pode começar logo depois da Fase 1)

**Objetivo**: saber, por vídeo, **o que** dá para entregar. Isso escolhe os vídeos do ouro da
Fase 8 pelo peso real de cada canal e dimensiona o rollout.

**T7.1 — `python -m tab.censo --raiz /acervo --saida data/saida/censo/censo.jsonl`**, retomável
(pula o que já fez; chave = caminho relativo + tamanho + mtime, porque o acervo **ainda
cresce**). Por vídeo, grave **mais do que precisa** (como a `varredura` já faz), para não
reabrir vídeo na análise:
- `info()` (codec, duração, fps, resolução);
- presença em 12 instantes de 0,05 a 0,95 (regra 10: um instante não responde);
- em até 3 instantes com tablatura, uma janela de 10 s a 3 qps com: há faixa? há destaque de
  cor? há troca de tela? há rolagem?;
- erros declarados (`"erro": "…"`), nunca engolidos.

**T7.2 — Meça o custo antes de soltar.** Rode 20 vídeos (misture AV1 e H.264), meça o tempo
por vídeo e extrapole para 3.899. Se passar de **2 noites**, estratifique: presença em todos e
o resto em 30 vídeos por canal.

**T7.3 — Conferência.** Sorteie 30 vídeos, gere uma folha com 2 quadros de cada e a categoria
que o censo deu, e **olhe**. Concordância ≥ 90 %, senão conserte o classificador do censo
(foi assim que o "pisca 3" se revelou errado).

**CA da Fase 7**
- [ ] 100 % dos vídeos com linha no JSONL (ou erro declarado);
- [ ] tabela por canal no ESTADO: % com tablatura, % paginado/rolante, % com faixa/cor/sem
      marcador, % AV1;
- [ ] conferência de 30 vídeos ≥ 90 %;
- [ ] decisão D7 (rolagem) respondida **com o número** do censo.

---

### Fase 8 — Generalizar: os canais que pesam (1–2 semanas + ~4 h do dono)

**T8.1 — Escolher o ouro de vídeo ampliado** (≥ 9 vídeos, ≥ 7 canais), pelo **peso no acervo**
e pelas **formas** do censo. Proposta:

| canal | vídeos no acervo | por que entra |
| --- | --- | --- |
| violaodecria | 1.037 | maior canal; quase não medido. **Primeiro confirme no censo se tem tablatura** (o detector já escolheu piano lá) |
| tv cifras | 522 | 2º maior; forma "salta" |
| sky guitar | 417 | MVP (já no ouro) |
| guitar dell'arte | 361 | faixa azul; partitura + tab; "notas fantasmas" na virada de tela (`configs/canais.yaml`) |
| cifra club | 341 | cor **cumulativa**, painel **escuro**, algarismo pequeno (0,38 passo) |
| leonardo ramos | 290 | "quase ausência" de marcador |
| robert lunn | 229 | patamar/rolagem? |
| mr. tabs | 22 | cor (destaque azul), **AV1** |
| iwaki | 164 | **sem marcador** (testa o CA-6) |

Rotular cada um como na Fase 2 (~30 min por vídeo).

**T8.2 — Casa fora do ouro (a alternativa B do CONTEXTO).** Do censo, sorteie **2 vídeos × 1
tela** de cada um dos 17 canais com tablatura. O dono corrige **só números** (a ferramenta
da Fase 2 serve: são telas sem instantes). Reporte o acerto **por canal** e, à parte, o das
casas **≥ 8**, que nunca foram aferidas. Canal abaixo de 0,95 → D5 (`casa_validada: false`)
até ser consertado.

**T8.3 — Consertar o que falhar, na camada certa.** Para cada erro: **olhe a imagem** e
classifique (painel errado · grade · token fundido/acorde empilhado · classificador · imagem
limpa · tela · observador). Mudança no gerador sintético → 3 sementes, `tab.avaliar` **e**
`tab.avaliar_video` em todo o ouro, antes e depois. Mudança que melhora um canal e piora
outro é **troca, não ganho** (rodada 22): não adote.

**T8.4 — Rolagem (se D7 = sim).** Tela contínua: o deslocamento por amostra
(`phaseCorrelate`) acumulado vira uma coordenada "da partitura" (`x_partitura = x_quadro +
deslocamento(t)`). As colunas vivem nessa coordenada e o marcador é convertido para ela no
instante dele. Ouro de 1 vídeo rolante antes de declarar pronto.

**T8.5 — Acordes empilhados (CONTEXTO §9.4).** Antes de consertar, **meça**: no ouro ampliado,
quantas notas perdidas/erradas são dígitos de acorde fundidos? Só conserte se for ≥ 1 % das
notas.

**CA da Fase 8**
- [ ] CA-2, CA-3, CA-5, CA-6 e CA-7 em **todos** os vídeos do ouro ampliado (ou o vídeo fica
      registrado como exceção, com causa e decisão do dono);
- [ ] CA-4 por canal (ou bandeira `casa_validada: false` aplicada);
- [ ] `tab.avaliar` ≥ referência (CA-8).

---

### Fase 9 — Rollout em lotes, com auditoria (1 semana de máquina + ~3 h do dono)

**T9.1 — `python -m tab.lote --censo data/saida/censo/censo.jsonl --saida data/saida/produto/`**
- entrada: os vídeos elegíveis segundo o censo; os não elegíveis viram registro de recusa
  com motivo (CA-1);
- saída: `data/saida/produto/<canal>/<slug>.json` + `indice.jsonl` (uma linha por vídeo:
  status, notas, telas, tempo medido?, segundos de processamento) + `falhas.jsonl`;
- **retomável e idempotente**: pula o vídeo já feito com o **mesmo** commit + modelo;
- **tempo-limite por vídeo** e captura de exceção por vídeo (um vídeo ruim não derruba o
  lote);
- paralelismo **medido**: a decodificação de AV1 é CPU e o HD é compartilhado. Comece com 2
  processos e meça antes de subir;
- 1º lote = 1 canal pequeno (ex.: `serge kottelat`, 38 vídeos) → conferência → só então o
  resto.

**T9.2 — Auditoria (CA-9).** Sorteie 20 vídeos do lote final, estratificados por canal,
**que não estejam no ouro**. Rotule 20 instantes + 1 tela de cada (~10 min por vídeo) e rode o
`tab.avaliar_video`. Se a média ficar mais de 0,03 abaixo do ouro, **pare**: a régua não
representa o acervo. Volte para a Fase 8 com esses vídeos.

**T9.3 — Aceite final (CA-10).** Folha de conferência de 3 vídeos do rollout para o dono.

**CA da Fase 9** = CA-1, CA-9, CA-10 e CA-11. Com isso, **todos** os critérios do §1 estão
verdes e o objetivo está concluído.

---

### Fase 10 — Depois do produto (dívidas registradas, fora do "pronto")

Em ordem de valor provável. Cada item precisa de uma pergunta ao dono antes:

1. **Significado de símbolo/técnica**: o vocabulário do dono já está em
   `simbolos_marcados.json` (`formula_compasso`, `arpejo_vertical`, `arco_ligadura`,
   `arco_slide`, `pausa`). Proposta: campo `tecnica` só para classes com precisão medida ≥
   0,9, e o resto continua cru;
2. **Afinação** (`tab/afinacao.py` tem 926 linhas e não foi aferido): validar e ligar no
   `afinacao` do JSON;
3. **Tempo por áudio** nos vídeos sem marcador (autorizado pelo dono): alinhar onsets de áudio
   à sequência de colunas de cada exibição;
4. **Tab ASCII e partitura**: leitores próprios, fora desta cadeia.

---

## 7. Riscos e como perceber cedo

| risco | sinal | resposta |
| --- | --- | --- |
| **Tempo do dono** é o gargalo (CONTEXTO §16.2) | rótulos atrasam a fase | pré-preenchimento, autosave, lotes de 30 min, ordem embaralhada; nunca peça rótulo que a máquina pode medir |
| O marcador pinta o algarismo e muda a binarização | acerto cai só nos quadros com marcador | imagem limpa (mediana temporal), T4.1 |
| Cor cumulativa (`cifra club`) engana o observador de cor | estado "trava" numa coluna antiga | modo "acendeu agora" (T5.1), com teste |
| Painel muda de lugar ou de tema no meio do vídeo | troca de tela espúria | presença por trecho + reavaliar `escolher` na troca (T3.1) |
| Régua que mente | número sobe sem a imagem melhorar | denominadores sempre impressos; folha de conferência a cada fase |
| Gabarito de glifos por índice de token | mexeu em `tabseg` e o `tab.avaliar` mudou "sozinho" | conferir `n_tokens` da amostra; não mudar segmentação sem rodar a régua |
| Acervo crescendo e HD compartilhado | censo/lote lentos ou parciais | tudo retomável; chave por caminho + tamanho + mtime; revarrer no fim (resposta "HD" do dono) |
| Escrita do container como root | não consegue apagar saída | `$C run --rm chorinho rm -rf …`, ou decidir o `user:` do compose (PERGUNTAS) |

---

## 8. O que não fazer (além da tabela do ESTADO)

- **Não** escalar (rollout) antes do MARCO MVP e da Fase 8: sairia errado em parte, sem
  ninguém saber;
- **não** criar regra por canal ou por estilo de marcador. O dono pergunta "e os próximos?". A
  decisão é **por exibição**, com base no que foi medido nela;
- **não** reportar "notas com tempo" sem o ouro de instantes;
- **não** distribuir tempo por interpolação onde não há marcador;
- **não** escolher semente/limiar olhando o mesmo conjunto em que se reporta o número sem
  dizer isso;
- **não** reescrever o `tab/pipeline.py` e o `tab/transcrever.py` no mesmo commit da
  funcionalidade nova. Primeiro o novo passa no ouro, depois o velho sai.

---

## 9. Cronograma indicativo e o que o dono precisa fazer

| fase | máquina/código | dono |
| --- | --- | --- |
| 0 régua | ½ dia | responder D1–D7 (10 min) |
| 1 fundações | 2–3 dias | — |
| 2 ouro de vídeo | 3–4 dias | **~40 min** (vídeo do MVP) |
| 3 telas | 3–4 dias | — |
| 4 leitura por tela | 2–3 dias | — |
| 5 tempo por exibição | 3–4 dias | — |
| 6 JSON v1 → **MVP** | 2 dias | **aprovar a folha** (5 min) |
| 7 censo | 1–2 noites de máquina (em paralelo desde a Fase 1) | olhar 30 vídeos (opcional) |
| 8 generalizar | 1–2 semanas | **~4 h** (8 vídeos + 34 telas) |
| 9 rollout | ~1 semana de máquina | **~3 h** (auditoria de 20) + aprovar 3 folhas |

Total de rótulo do dono até o fim: **~8 h**, espalhadas em sessões curtas.

---

## 10. Checklist de entrega de cada tarefa (cole no commit/PR)

```
[ ] li os arquivos antes de editar (não adivinhei texto)
[ ] medi a linha de base ANTES (tab.avaliar 3 sementes; tab.avaliar_video no ouro)
[ ] olhei a imagem quando o número surpreendeu
[ ] teste novo sem GPU e sem acervo (integration marcado à parte)
[ ] ast.parse + import + rodei de verdade
[ ] medi DEPOIS; neutro/negativo foi revertido e registrado
[ ] make gate verde (vi a linha "All checks passed!" e "N passed")
[ ] ESTADO.md atualizado com número, denominador, modelo e commit
```

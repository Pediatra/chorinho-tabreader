# Contexto para o agente das mãos (trilha paralela)

> **Leia primeiro (decisão 9001, 2026-10-22):** [o relatório da reestruturação para esta trilha](../decisoes/9001-relatorios/maos.md): o que mudou de lugar, o que ela precisa saber e o que fica com ela.

> Documento de passagem de contexto, escrito em 2026-10-12 pelo agente que coordena a trilha
> **tablatura + tempo** (o "cérebro" do projeto). Leia este arquivo, depois o
> [`AGENTS.md`](../../AGENTS.md) **inteiro**, o [`docs/estado/maos.md`](../../docs/estado/maos.md) (índice: [`ESTADO.md`](../../ESTADO.md)) e o
> [`plano-do-produto.md`](plano-do-produto.md). Este documento não substitui o `AGENTS.md`:
> as regras de trabalho de lá valem para você também.

---

## 1. O objetivo final do dono (por que existem duas trilhas)

O dono quer um **dataset rotulado** para treinar, no futuro, um modelo que receba **só um
vídeo de alguém tocando violão** e devolva **tablatura e partitura**. Para isso, cada nota
tocada nos vídeos-aula do acervo precisa sair com tudo alinhado no tempo:

| camada | o que é | quem faz |
| --- | --- | --- |
| **tablatura** | corda, casa, coluna, compasso, símbolo cru, por nota | trilha tablatura (eu) — **pronta no MVP** |
| **tempo do vídeo** | instante `t_ini` em que cada nota é tocada, pelo marcador da tela | trilha tablatura (eu) — **pronta no MVP** |
| **áudio** | onset da nota no áudio, refinando `t_ini` | trilha tablatura (eu) — **ainda não começou** |
| **mão esquerda** | onde os dedos da mão esquerda estão (keypoints), qual dedo pisa qual nota | **você** |
| **mão direita** | keypoints da mão direita, qual dedo (p, i, m, a) toca qual nota | **você** |

No fim, a **chave comum** é a nota do JSON do produto (seção 4). Você não precisa (e não deve)
reler tablatura: o seu trabalho é ligar **o que as mãos fazem** a cada nota que o meu JSON já
diz que foi tocada naquele instante.

## 2. O projeto em uma página

- **Acervo**: vídeos-aula de violão do YouTube com **a tablatura na tela**. Em 2026-10-11:
  **5.018 vídeos / 21 canais / ~290 GB**, e **ainda crescendo** (o dono segue baixando).
  Montado **somente leitura** em `/acervo` (no host:
  `/run/media/gabriel/3014CD4714CD1130/chorinho`). **Nunca escreva lá.**
- **Canais fora** (decisão do dono, [`0009`](../decisoes/0009-canais-fora-da-fase-8.md)):
  `violaodecria` e `tv cifras`. Marcados `rollout: fora` em `configs/canais.yaml`.
- **Canais ativos**: **2.798 vídeos em 19 canais, 269 h de vídeo**; **2.565 com tablatura**
  (92 %), ~143 h de tablatura na tela. Os que pesam: sky guitar (417), robert lunn (369),
  guitar dell'arte (361), cifra club (341, 197 com TAB), leonardo ramos (298), kenneth
  acoustic (294), iwaki (164), shin izumi (149), pablo romé (124), kimny's guitar (108).
  A tabela completa por canal está em `docs/estado/historico-antes-das-trilhas.md` (seção Fase 7, 2026-10-11).
- **Arquitetura da trilha tablatura** (decidida por medição): geometria determinística + um
  classificador de glifos de ~74 mil parâmetros treinado **só em dado sintético**. VLM foi
  testado e perdeu feio. Pacote `tab/`, com uma pasta por trilha (decisão 9001): `tab/maos/`.
- **Número oficial do classificador**: 0,949 (66/72, 71/72, 68/72 nas 3 sementes).
- **MVP aprovado pelo dono em 2026-10-10** (rodada
  [`0004-mvp-video-inteiro`](../rodadas/0004-mvp-video-inteiro.md)): o vídeo
  `sky guitar/retrato brasileiro - tab & lesson.mp4` transcrito inteiro num comando, contra
  um gabarito de vídeo rotulado pelo dono: 0 notas inventadas, revocação 485/491, casa
  483/485, tempo certo em 39/40 instantes, 0 tempo falso.

## 3. Ambiente (o que custou horas para descobrir)

- **Tudo roda no container** `chorinho:dev` (podman). O `.venv` do host é só para o editor.
- O shell do Claude aqui é uma **distrobox sem git e sem docker**. Use:
  - `host-spawn -no-pty -cwd /var/home/gabriel/Projects/chorinho-dataset sh -c "..."`
  - `git --no-pager ...` (sem isso o pager quebra);
  - `DOCKER_HOST=unix:///run/user/1000/podman/podman.sock docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho <comando>`
  - ruff com `RUFF_CACHE_DIR=/tmp/ruffcache`; pytest com `-p no:cacheprovider`.
- **GPU**: uma só, **RTX 3060 Ti, 8 GB**, via CDI (`devices: nvidia.com/gpu=all` em
  `compose.podman.yaml`). Depois de reiniciar o host:
  `sudo nvidia-ctk cdi generate --output=/var/run/cdi/nvidia.yaml` (o dono roda).
  **A GPU é compartilhada entre as duas trilhas**: veja a seção 7.
- **44 % do acervo é AV1**: o OpenCV não decodifica. **Leia vídeo só por `tab/comum/leitor.py`**
  (usa ffmpeg; é o leitor único do projeto; o carimbo de tempo de cada quadro é o **PTS real**
  — isso foi consertado depois de achar quadros 2–3 quadros adiantados).
- **Cache de quadros** no HD externo, montado em `/cache` (host:
  `/run/media/gabriel/3014CD4714CD1130/chorinho_cache`, PNG sem perda, ~56 GB): por vídeo,
  os **12 quadros de presença** (0,05 a 0,95 da duração) em resolução nativa, e janelas de
  10 s a 3 qps em 30 vídeos por canal. Código em `tab/comum/cache.py`. **Use esse cache para o seu
  censo de mãos** (seção 6) — ler o HD de novo custa ~22 h.
- O container escreve como **root**: para apagar saída, use o container
  (`... run --rm chorinho rm -rf <caminho>`).
- `/tmp` do container **não** aparece no host. Artefatos vão para `data/saida/`; pesos para
  `artefatos/` (com comando e semente registrados). Modelo em `/tmp` é modelo perdido.

## 4. A chave comum: o JSON do produto (`chorinho/video@1`)

Gerado por `python -m tab.tablatura.produto.transcrever VIDEO --json saida.json` (valida com
`tab/tablatura/produto/esquema.py` antes de gravar). O MVP está em `data/saida/tablatura/produto/mvp.json`. Estrutura
(resumida; a definição exata é `tab/tablatura/produto/esquema.py`):

```json
{
  "esquema": "chorinho/video@1",
  "video": {"arquivo": "sky guitar/…mp4", "canal": "sky guitar", "duracao_s": 678.97, "codec": "h264"},
  "telas": [{"id": 1, "painel": [x0, y0, x1, y1], "passo": 16.0, "modo": "paginado",
             "barlines_x": [...], "exibicoes": [{"t0": 239.0, "t1": 262.5}], "tempo": {...}}],
  "notas": [{"tela": 1, "passagem": 1, "exibicao": 0, "coluna": 1, "compasso": 1,
             "corda": 2, "casa": 0, "tecnica": null, "confianca": 0.99,
             "x_quadro": 224, "x_centro_quadro": 231.0, "t_ini": 245.011}],
  "nao_notas": [{"tela": 1, "corda": 1, "x_quadro": 508, "classe": "harmonico", "simbolo_cru": {...}}],
  "resumo": {...}
}
```

Pontos que importam para você:

- **Uma entrada por passagem** (decisão D2): se a mesma tela é tocada 2 vezes, cada nota
  aparece 2 vezes, com `t_ini` diferentes. Isso é bom para você: cada aparição é um evento
  de mão diferente. A identidade "musical" da nota é `(tela, coluna, corda)`; a identidade
  do **evento** é `(tela, passagem, exibicao, coluna, corda, t_ini)`.
- **Corda 1 = aguda (mi agudo), 6 = grave.** Casa 0 = corda solta.
- `t_ini` é o instante (segundos, PTS real do vídeo) em que a coluna passa a ser a tocada,
  pelo marcador da tela. Precisão: **1 quadro** (~33 ms a 30 fps). Nota sem `t_ini` = tela sem
  marcador (o produto **não inventa tempo**).
- Acordes: várias notas com a mesma `coluna` e o mesmo `t_ini`.
- `nao_notas`: símbolos (ligado, mordente, harmônico, `p`, `h`, `/`…) guardados **crus**;
  significado ainda não mapeado. **Símbolo não se descarta** (regra do projeto).
- **Dedilhado escrito**: muitas partituras (sky guitar, guitar dell'arte, iwaki) trazem
  números de dedo da mão esquerda (1 2 3 4) e letras da direita (p i m a) **na pauta**, acima
  da TAB. Hoje **ninguém lê isso**. É uma fonte de rótulo grátis para você (seção 5).

## 5. Sua trilha: mãos ⇄ notas (sugestão de caminho, com critérios)

O dono não definiu o "como"; abaixo é a minha proposta, no mesmo estilo do resto do projeto
(medir antes, gabarito do dono é contrato, uma coisa por vez). Ajuste, mas **meça**.

**M0 — Censo de mãos (sem rótulo, só máquina).** Nos 12 quadros de cada vídeo do **cache**,
rode um detector de mãos/pose pronto e registre por vídeo: há violonista no quadro? mão
esquerda visível? direita? escala (px por casa)? ângulo (de frente, de cima, close no braço)?
Muitos canais mostram **só a tablatura** em boa parte do vídeo, ou só o braço em close, ou o
violonista pequeno num canto. Este censo decide **quais canais servem** para mãos. Critério:
folha de 30 vídeos olhada (concordância ≥ 90 %), tabela por canal em `docs/estado/historico-antes-das-trilhas.md`.

**M1 — Escolha do detector por medição.** Candidatos óbvios (pose/keypoints de mão prontos:
MediaPipe Hands, RTMPose/MMPose wholebody, etc.). Regra 1 do `AGENTS.md`: semente fixa,
≥ 3 execuções, média e amplitude. Mãos de violonista têm oclusão (dedos sobre o braço),
desfoque de movimento e cordas que imitam dedos — **meça em quadros do acervo**, não em
benchmark. Lembre: a GPU tem 8 GB e é compartilhada.

**M2 — Gabarito de mãos do dono.** Comece pelo **vídeo do MVP** se ele mostrar as mãos (confira
— ele pode ser só partitura+TAB na tela); se não mostrar, escolha com o censo M0 um vídeo de
canal que pese e mostre as mãos. O dono rotula pouco e bem: por exemplo, em ~40 notas,
"qual dedo da mão esquerda pisa" e "qual dedo da direita toca". Faça uma ferramenta de
rótulo no estilo de `tab/tablatura/ouro/ouro_video.py` (servidor local, autosave, uma decisão por clique).
**O tempo do dono é o gargalo do projeto**: peça o mínimo que mede.

**M3 — Ligação nota → dedo.** Para cada evento do JSON (corda, casa, `t_ini`):
- **esquerda**: com a casa e a corda conhecidas, a ponta do dedo que pisa deve estar perto
  da casa `casa` na corda `corda` em `t_ini` (casa 0 = nenhum dedo). Precisa de um mapa do
  braço (traste/corda em pixels) — isso é geometria, no espírito do projeto;
- **direita**: qual dedo se move/toca a corda em torno de `t_ini` (±1–2 quadros);
- o dedilhado escrito na pauta (seção 4), quando houver, é rótulo fraco para validar.
Critério: acerto de dedo contra o gabarito M2, com denominador impresso ("X de Y").

**M4 — Esquema.** Proponha o formato (um bloco `maos` por evento de nota, ou um arquivo
irmão `<video>.maos.json` com a mesma chave de evento). **Não mude `chorinho/video@1` sem
combinar**: escreva uma decisão em `docs/decisoes/` e me avise pelo dono.

## 6. Regras de convivência entre as duas trilhas (para não quebrarmos um ao outro)

1. **Arquivos.** A trilha tablatura é dona de: `tab/tablatura/leitura/painel.py`, `tab/tablatura/produto/telas.py`,
   `tab/tablatura/produto/video.py`, `tab/tablatura/produto/estado.py`, `tab/tablatura/leitura/reconhecer.py`, `tab/comum/leitor.py`, `tab/tablatura/censo/censo.py`,
   `tab/comum/cache.py`, `tab/tablatura/produto/esquema.py`, `tab/tablatura/treino/sintetico.py`, `tab/avaliar*.py`, `tab/tablatura/ouro/conferir.py`,
   `tab/tablatura/produto/musicxml.py`, `data/gold/presenca_quadros.json`, `data/gold/ouro_video/`. **Não edite
   esses.** Pode **importar** à vontade (leitor, cache, esquema). Se precisar de mudança
   neles, peça ao dono para me repassar.
2. **Seus arquivos**: módulos novos em `tab/maos/<modulo>.py` (o projeto tem **um pacote
   só**, com pastas por trilha — crie o módulo na pasta da trilha, subpacote só acima de ~10 módulos), testes `tests/maos/`, saída em
   `data/saida/maos/`, gabarito em `data/gold/maos/`, pesos em `artefatos/maos_*/`.
3. **Numeração de documentos**: use `docs/rodadas/1NNN-…` (1001, 1002, …) e
   `docs/decisoes/1NNN-…` para não colidir com a minha sequência (0001–0999).
4. **O estado das mãos fica em `docs/estado/maos.md`** (decisão 9001): seção nova no fim
   dele. O `ESTADO.md` é compartilhado (índice e "não repetir"), e **confira `git diff ESTADO.md` antes de commitar** (já aconteceu de um agente
   commitar a seção de outro).
5. **Git** (regras que custaram incidentes): `git add` **só por nome**; nunca `add -A`,
   `reset`, `amend`, `stash`, `checkout --`. Mensagem de commit **via arquivo**
   (`git commit -F arq`): heredoc dentro de `sh -c` já truncou uma mensagem. Um commit por
   tarefa, com o número medido. Trailer de coautoria conforme o sistema indicar.
6. **Gate compartilhado**: `ruff check .`, `ruff format --check .`, `pytest tests/ -m "not
   integration"`. Um arquivo seu não formatado deixa o gate **vermelho para mim também** —
   formate antes de salvar no repo; rascunhos ficam em `data/saida/maos/` ou no scratchpad.
7. **GPU**: antes de treinar ou rodar inferência longa, crie `data/saida/gpu.lock` com
   "maos, <início>, <estimativa>" e apague ao terminar; se existir um lock da trilha
   tablatura, espere ou rode em CPU. Inferência de keypoints em lote no acervo é longa:
   meça o custo em 20 vídeos antes (regra 2) e planeje como o censo foi planejado.
8. **HD externo**: é o gargalo de E/S. Duas leituras longas ao mesmo tempo dobram o tempo de
   ambas (medido). Prefira o **cache** (`/cache`); para ler vídeo inteiro, combine a janela
   de horário pelo dono.
9. **Comunicação**: as duas sessões não se falam direto; o dono é a ponte. Cada decisão que
   afete a outra trilha vira arquivo em `docs/decisoes/`.

## 7. Regras do projeto que mais pesam para você (resumo do `AGENTS.md`)

- **Olhe o quadro antes de teorizar** (duas vezes o violão foi confundido com tablatura).
- **Rótulo de gabarito só por leitura visual, e só do dono.** Agente nunca grava rótulo em
  `data/gold/` por conta própria: monta uma folha e pergunta. Rótulo provisório de agente vai
  para `data/saida/`, marcado como tal.
- **Falso positivo é o pior erro**: grandes trechos dos vídeos não têm o que se procura
  (sem violonista, só partitura). Um dado errado afirmado é pior que um dado ausente
  declarado — o produto prefere "não sei" a inventar (como o tempo: nota sem marcador fica
  sem `t_ini`).
- **Confira o significado do número**: conte eventos distintos, imprima denominadores.
- **O recorte/pré-processamento é parte da medição**: mudou o recorte, invalidou a comparação.
- **Registre o que falhou** na tabela "não repetir" do `ESTADO.md`.
- Código: Python 3.14, sem import dentro de função, aspas duplas, 88 colunas, type hints,
  docstring Google, **nomes em português**, CLI `python -m tab.x` com `main()`.

## 8. O que eu (trilha tablatura) estou fazendo agora e a seguir

- **Agora**: fechando a Fase 7 (censo de presença da tablatura no acervo; consertos de
  detecção em fundos rosa/transparente/vertical; reprocesso pelo cache).
- **A seguir**: Fase 8 — gabarito de tablatura+tempo em ~9 vídeos de ~7 canais (escolha pelo
  censo); tela que **rola** (16 % dos vídeos); depois o rollout (Fase 9) que gera o JSON de
  todos os vídeos com tablatura; e o **alinhamento com o áudio** (onset por nota).
- **O que você recebe de mim**: o JSON v1 de cada vídeo (hoje só o MVP; na Fase 8, ~9
  vídeos com gabarito; na Fase 9, o acervo). Comece pelo MVP e pelo censo de mãos, que não
  dependem de nada meu além do que já existe.

## 9. Arquivos para ler primeiro

1. `AGENTS.md` (inteiro) — contrato.
2. `docs/estado/maos.md` — estado medido; `docs/estado/historico-antes-das-trilhas.md` — tabela do censo por canal; `ESTADO.md` — tabela "não repetir".
3. `docs/guias/plano-do-produto.md` — plano, fases, critérios de aceite (CA-1..CA-11).
4. `docs/rodadas/0004-mvp-video-inteiro.md` — o MVP, números, erros conhecidos.
5. `tab/tablatura/produto/esquema.py`, `data/saida/tablatura/produto/mvp.json` — a chave comum.
6. `tab/comum/leitor.py`, `tab/comum/cache.py`, `tab/tablatura/censo/censo.py` — como ler vídeo e quadros em cache.
7. `tab/tablatura/ouro/ouro_video.py` — modelo de ferramenta de rótulo para o dono.

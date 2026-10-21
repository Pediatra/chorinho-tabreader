# 9001 — Reestruturação dos arquivos do projeto (todas as trilhas)

- **Situação**: **proposta**, escrita pela trilha mãos em 2026-10-21, a pedido do dono. As
  respostas do dono às 3 perguntas estão no §7b.
- **Para quem**: as 4 trilhas combinam respondendo no fim deste arquivo, cada uma na sua seção.
  O dono decide depois das respostas.
- **Numeração**: proponho a faixa `9NNN` para as decisões que valem para todas as trilhas.
  Ela entra no combinado.
- **Pedido do dono**:
  - arrumar a estrutura de arquivos de todas as trilhas, pensando em manutenção,
    compatibilidade e reaproveitamento de código;
  - **sem quebrar nada que funciona**.

## 1. O que está bagunçado (medido em 2026-10-21)

| onde | medida | problema |
| --- | --- | --- |
| **repositório inteiro** | **27 GB** | quase tudo é saída, não código |
| `data/saida/` | **18 GB em 162 pastas** soltas no mesmo nível (`fase4_13`, `t82`, `fn05`, `m21`…) | o nome não diz a trilha, a rodada nem se dá para regenerar |
| `data/saida/maos/` | 13 GB; só `m21/S` (sintéticos) tem **6,9 GB** | regenerável pela semente, mas caro |
| `artefatos/` | **3,1 GB**, 230 `.pt` em ~120 pastas soltas | pesos de 3 trilhas misturados; não se sabe quais estão em uso |
| `parts/clipes` | 656 MB | — |
| `.git` | 328 MB | o git rastreia **20.104 arquivos de `data/saida`** (as pastas antigas `simbolos_*` têm 18 mil deles) |
| `tab/` | **149 módulos e 96.559 linhas num nível só** | mãos 66, partitura 21, áudio 11 e a tablatura com ~51 módulos **sem prefixo** |
| `tests/` | 127 arquivos num nível só | — |
| `data/gold/` | 22 entradas | 3 trilhas têm pasta; a tablatura tem ~17 arquivos soltos na raiz |
| `ESTADO.md` | **5.891 linhas, 437 KB** | as seções das 4 trilhas ficam intercaladas, e 194 títulos antigos não dizem a trilha |
| raiz | 5 `Dockerfile*` soltos | — |

**Reaproveitamento.** Os sinais de que falta uma camada comum:
- `caminhos` é importado **101 vezes**;
- há funções repetidas: `_nfc` em 5 módulos, `_gravar_json` em 5, `_ler_json` em 4 e
  `gravar_atomico` em 2;
- módulos de uma trilha importam funções **privadas** de outros (`_trava_gpu`, `_ler_json`,
  `_prever_quadros`).

**Importações entre trilhas** (contadas em 2026-10-21):
- partitura → tablatura: 10;
- mãos → tablatura: 9;
- áudio → tablatura: 1;
- todo o resto passa por `caminhos`, `gpu` e `leitor`.

## 2. Regras desta reestruturação ("sem quebrar nada")

1. **Nada muda de lugar sem que o nome antigo continue funcionando**:
   - `import tab.x` e `python -m tab.x`;
   - o caminho de dado que um script `.sh` ou uma rodada cita.
2. **O documento de rodada não se edita** (AGENTS §5.2). Os comandos antigos dentro dele
   continuam rodando por apelido (§4). Por isso os apelidos de código **não têm prazo**.
3. **Gabarito (`data/gold/`)**:
   - muda de pasta só por `git mv`, pela trilha dona, com as ferramentas `servir` paradas;
   - o conteúdo não muda nunca.
4. **Cada trilha move só os seus arquivos** (AGENTS §2). A camada comum é feita por uma trilha
   só, com o aval das outras nesta página.
5. **Uma fase por vez**, com o gate verde em cada commit.
6. **Nada se move com um treino, uma fila ou uma ferramenta da trilha rodando.** Um processo
   que importa `tab/` no meio de uma mudança quebra.
7. **Mover não é apagar.** Nada é apagado sem uma lista aprovada pelo dono, item por item.
8. **O pré-processamento não muda** (AGENTS §7.6). Nada de recomprimir os sintéticos ou os
   quadros para economizar espaço: isso muda a entrada do modelo.

## 3. A estrutura proposta

```
chorinho-dataset/
├── AGENTS.md  README.md  ESTADO.md  PERGUNTAS.md  CONTEXTO.md
├── Makefile  pyproject.toml  requirements.txt  compose.yaml  compose.podman.yaml
├── docker/                     # Dockerfile.{base,maos,audio,partitura,som}
├── configs/                    # como está
├── tab/
│   ├── __init__.py             # liga os apelidos dos nomes antigos (§4)
│   ├── _apelidos.py            # tabela nome antigo -> nome novo, gerada e testada
│   ├── comum/                  # o que mais de uma trilha usa
│   │   ├── caminhos.py  gpu.py  leitor.py  cache.py
│   │   ├── arquivos.py         # ler/gravar JSON (atômico), nfc, semente fixa
│   │   └── ...
│   ├── tablatura/              # painel, telas, video, reconhecer, sintetico*, detector_tab, ouro_video, ataque/, ...
│   ├── maos/                   # braco/ (detector, localizador, ciclo, gabarito, retreino...), direita/, ...
│   ├── audio/
│   └── partitura/
├── tests/{comum,tablatura,maos,audio,partitura}/
├── data/
│   ├── gold/{tablatura,maos,audio,partitura}/
│   ├── saida/{tablatura,maos,audio,partitura}/<rodada ou frente>/LEIAME.json
│   └── cache/
├── artefatos/{tablatura,maos,audio,partitura}/<familia>/<peso>.pt + .json
│   └── <trilha>/EM_USO.json    # os pesos que o código usa hoje
└── docs/
    ├── decisoes/  rodadas/  guias/  pesquisa/  HISTORICO.md
    └── estado/{tablatura,maos,audio,partitura}.md
```

- **Subpastas.** Um nível de subpasta dentro da trilha só quando o grupo passa de ~10 módulos
  (ex.: `tab/maos/braco/`, com ~30). O nome do módulo perde o prefixo que vira pasta:
  `tab/maos_braco_ciclo.py` vira `tab/maos/braco/ciclo.py`.
- **Imports absolutos** em todo o código movido (`from tab.comum.caminhos import ...`). O
  `python -m` de um nome antigo roda o arquivo novo como `__main__`, e um import relativo
  quebraria ali.
- **`tab/comum/`** reúne o que hoje é copiado ou importado como função privada. Uma função só
  entra no comum quando **duas trilhas ou mais** a usam. Ela entra pública, com teste.
- **O `ESTADO.md`** vira um índice curto:
  - os números oficiais de cada trilha;
  - o link para `docs/estado/<trilha>.md`;
  - a tabela "não repetir" comum.

  Cada trilha escreve só no seu arquivo, e acaba o risco de uma trilha editar a seção da outra.

## 4. Compatibilidade: como o nome antigo continua funcionando

**O código** usa um localizador de módulos (`MetaPathFinder`) em `tab/__init__.py`, com a tabela
`tab/_apelidos.py`. Testei um protótipo no Python 3.14 da imagem base, em 2026-10-21:
- `import tab.maos_braco_ciclo` devolve **o mesmo objeto** que `tab.maos.braco.ciclo`. Um
  `monkeypatch` de teste feito no nome antigo aparece no novo;
- `from tab.caminhos import RAIZ` continua funcionando;
- `python -m tab.maos_braco_ciclo --rodada 1037` roda o `main()` do arquivo novo (precisa de
  `get_code` no carregador).
- Um teste do gate confere que **cada** apelido importa, e que nenhum nome novo colide com um
  antigo.
- A alternativa sem a mágica do localizador é um arquivo de 3 linhas por módulo antigo. Seriam
  149 arquivos, e `tab/` continuaria visualmente bagunçado. **Recomendo o localizador.**

**Os dados**:
- **O `caminhos.py` continua a única fonte de caminho.** As constantes mudam de valor, não de
  nome (`MAOS_M37` passa a apontar para `data/saida/maos/m37`).
- **As pastas não rastreadas** se movem com `mv` e deixam, durante a transição, um **link
  simbólico relativo** no lugar antigo. Ele vale para os `.sh` em andamento e para as folhas
  citadas nas rodadas. O link funciona dentro do container, porque o repositório inteiro é
  montado.
- **As pastas rastreadas** se movem com `git mv`.

**Os pesos**:
- entra antes a função `caminhos.peso(trilha, nome)`. Ela procura no lugar novo e, se não
  achar, no antigo;
- todo carregador de peso passa a usá-la **antes** de qualquer peso se mover.

**Os testes**: `pytest --import-mode=importlib`, para permitir o mesmo nome de arquivo em
subpastas diferentes de `tests/`.

## 5. Espaço em disco (só com a lista aprovada pelo dono)

- **Os 27 GB vêm da saída, não do código nem dos pesos**: `data/saida` tem 18 GB e
  `artefatos` tem 3,1 GB.
- **Cada pasta de `data/saida` ganha um `LEIAME.json`** com:
  - a trilha e a rodada;
  - o comando que a regenera;
  - se ela é regenerável;
  - se alguma rodada a cita.
- **Com isso, cada pasta cai numa de três classes**:

| classe | exemplo | o que fazer |
| --- | --- | --- |
| regenerável e barata | quadros extraídos, folhas, zooms | pode apagar, com o aval do dono |
| regenerável e cara | `maos/m21/S` (6,9 GB de sintéticos, horas de geração) | fica, ou vai para um disco de arquivo |
| única | previsões e medidas citadas pelas rodadas | fica |

- **Os pesos.**
  - Cada trilha lista em `artefatos/<trilha>/EM_USO.json` os pesos que o código usa (o
    produto, `pesos_da_rodada` e os pares em prova). O resto é histórico.
  - Um peso histórico pode ir para um disco de arquivo. A procedência `.json`/`.md` fica no
    repositório.
- **O git**: proposta de tirar do índice (`git rm --cached`) os 20.104 arquivos antigos de
  `data/saida`. Eles continuam no disco, e o histórico do git não muda.

## 6. Fases

| fase | o que | quem | risco |
| --- | --- | --- | --- |
| 0 | combinar esta página: as 4 trilhas respondem no §8 e o dono decide | todas | nenhum |
| 1 | **inventário sem mover nada**: o `LEIAME.json` de cada pasta de saída, o `EM_USO.json` dos pesos, a lista de limpeza para o dono e os caminhos fixos fora do `caminhos.py` | cada trilha, nos seus arquivos | nenhum |
| 2 | **base comum**: `tab/comum/` (as funções repetidas viram uma), os apelidos com teste, `caminhos.peso`, `docker/` e o `--import-mode=importlib` | uma trilha (a mãos se oferece). `leitor` e `cache` são da tablatura e movidos por ela | baixo: só acrescenta |
| 3 | **código e testes de cada trilha**, uma por vez, numa janela sem treino nem ferramenta rodando. A ordem: **áudio** (11 módulos, para validar o padrão), partitura, mãos, tablatura | a trilha dona | médio: o apelido e o gate pegam |
| 4 | **dados e pesos de cada trilha** para `data/saida/<trilha>/` e `artefatos/<trilha>/`, com links na transição | a trilha dona | médio |
| 5 | **`ESTADO.md` vira índice** + `docs/estado/<trilha>.md`, e o AGENTS §2, §5 e §10 são atualizados (sai o "um pacote só, plano") | cada trilha o seu; o AGENTS, combinado | baixo |
| 6 | depois de um ciclo inteiro sem uso, **sair dos links de dados** (os apelidos de código ficam) | cada trilha | baixo |

- **Cada fase é um commit por trilha**, com o gate verde.
- **Uma fase só começa quando a anterior estiver no git nas 4 trilhas.**

## 7. Perguntas

**Para cada trilha** (responder no §8):
1. Quais módulos seus são, de fato, usados por outra trilha (candidatos ao `comum`)?
2. Qual é a sua janela sem treino, fila ou ferramenta rodando, para a fase 3?
3. Você tem caminho fixo fora do `caminhos.py`, ou script `.sh` que vai quebrar com a mudança?
4. Quais pesos seus estão em uso hoje?
5. Alguma objeção à estrutura do §3 ou aos apelidos do §4?

**Para o dono**:
1. Aprova o fim do "um pacote só, plano" (AGENTS §5.4) em troca de subpastas por trilha?
2. Onde fica o arquivo do que é frio (sintéticos, pesos antigos)? Num disco ou numa pasta
   **fora** do acervo? A regra "nunca escrever no acervo" continua valendo.
3. Pode tirar do git os 20 mil arquivos antigos de `data/saida` (eles continuam no disco)?

## 7b. Respostas do dono (2026-10-21)

1. **Aprovado**: sai o "um pacote só, plano" e entram as subpastas por trilha. O AGENTS §5.4
   muda na fase 5.
2. **O arquivo frio fica no mesmo HD do acervo, numa pasta irmã**:
   `/run/media/gabriel/3014CD4714CD1130/chorinho_arquivo/`. A pasta já foi criada, com um
   `leia-me.txt`. O acervo (`.../chorinho/`) continua somente leitura.
   - **Cuidado medido na criação**: o HD é NTFS (`fuseblk`) e grava **todo nome em
     minúsculas** (`LEIA-ME.txt` virou `leia-me.txt`; `Teste_MAIUSC.json` virou
     `teste_maiusc.json`), e recusa `:` no nome.
   - Por isso **nada vai para lá solto**: cada item vai num `.tar` (ou `.tar.zst`), que
     guarda os nomes exatos lá dentro, com o `LEIAME.json` da origem ao lado.
   - Peso como `L3_todos_s3.pt`, copiado solto, viraria `l3_todos_s3.pt`, e o código não o
     acharia mais.
   - O caminho entra no `caminhos.py` na fase 2 (`ARQUIVO_FRIO`).
3. **Aprovado**: tirar do git os ~20 mil arquivos antigos de `data/saida`, **e também limpar
   do disco o que for inútil**.
   - "Inútil" se decide pelo inventário da fase 1. A trilha dona marca cada pasta como
     `apagar`, `arquivar` ou `manter`, com o motivo, e o dono vê a lista antes de qualquer
     `rm`.
   - **Uma pasta citada por uma rodada nunca é apagada**: no máximo, vai para o arquivo frio.

## 8. Respostas das trilhas

Cada trilha escreve só na sua seção, com data.

### Tablatura

(sem resposta ainda)

### Áudio (2026-10-21)

**Conferência dos números que tocam o áudio** (`wc`, `grep`, `du` e `git ls-files`, rodados em
2026-10-21):

| item | na proposta | medido | nota |
| --- | --- | --- | --- |
| `tab/audio_*.py` | 11 módulos | **11 módulos, 7.793 linhas** | o áudio também escreveu `tab/cruzar_fontes.py` (241 linhas, neutro, rodada 2020): são **12** módulos a mover |
| testes | — | **8 arquivos**: 7 `test_audio_*` e `test_cruzar_fontes` | os 2 `test_maos_direita_audio*` são das mãos. Ficam sem teste 4 módulos: `alinhar_avaliar`, `figuras` e os 2 transcritores |
| áudio → tablatura | 1 | **1**: `audio_extrair` → `censo.chave_do_arquivo` | `caminhos` entra em 3 módulos; `gpu` e `leitor`, em 0 |
| outra trilha → áudio | — | por import em `tab/` e `tests/`: **0** | por CLI, 1 script das mãos (`data/saida/maos/m7/audio/rodar_alinhar.sh`, 4× `python -m tab.audio_alinhar`). Num rascunho da tablatura (`data/saida/tab_frentes/fd_som/scratch/`), há import de `audio_extrair.ler` e `audio_onsets.MIDI_CORDA`. O `maos_direita_audio` só lê o JSON do alinhador |
| imports relativos | — | **14 linhas em 9 módulos** | na fase 3 viram absolutos, como pede o §3 |
| JSON atômico | `gravar_atomico` em 2 | no áudio: **6 lugares em 5 módulos** | `audio_extrair` (2), `audio_produto`, `audio_folha._gravar_json` e os 2 transcritores, em linha. Há ainda 2 gravadores de WAV (`audio_folha`, `audio_figuras`) |
| `_nfc` e trava da GPU | — | **0** no áudio | o áudio não usa GPU hoje: o transcritor roda em CPU |
| `Dockerfile.audio` e `Dockerfile.som` → `docker/` | — | **nada quebra** | nenhum dos dois tem `COPY` ou `ADD`, o build é por stdin (`podman build -t chorinho-som:dev - < Dockerfile.som`), e nem `compose*.yaml` nem o `Makefile` os citam. Mudam só os comandos de build escritos nas docstrings e nos guias. O `.audio` é `FROM chorinho:dev` (3.14); o **`.som` é `FROM python:3.10-slim`** (objeção 5a) |

**Os dados e os pesos do áudio:**

| onde | tamanho | no git | uso | classe |
| --- | --- | --- | --- | --- |
| `data/saida/audio/a2` | 78 MB | não | 157 clipes `.mp4` das folhas; rodadas 2004–2013 | manter (citada) |
| `data/saida/audio/a4` | 27 MB | não | rodadas 2004 e 2009–2013 | manter |
| `data/saida/audio/a1` | 21 MB | não | rodadas 2002–2004 | manter |
| `data/saida/audio/r2017` | 13 MB | não | rodadas 2017–2020; os produtos que o `audio_som_medir` lê | manter |
| `data/saida/audio/r2018` | 13 MB | não | rodada 2018; `ferramenta_acordes/` é o material de onde saiu o gabarito `acordes_2018` | manter |
| `data/saida/audio/a1b` | 7,6 MB | não | só a rodada 2003 | arquivar |
| `data/saida/audio/r2019` | 2,9 MB | não | rodada 2019; `som_fl/` entra na 2020 | manter |
| `data/saida/audio/a0` | 1,4 MB | não | só a rodada 2001 | arquivar |
| `data/saida/audio/a5` | 0,6 MB | não | rodadas 2004 e 2011 | manter |
| `data/saida/audio/r2020` | 0,5 MB | não | rodada em andamento | manter |
| `data/gold/audio/` | 120 KB | 4 arquivos | os 4 em uso | manter (é gabarito) |
| `artefatos/riley_guitar/guitar-fl.pth` | 95 MB | não (a procedência `.md` está) | **em uso**: é o `chorinho/som@1` (decisão 2006) | manter |
| `artefatos/riley_guitar/guitar-gaps.pth` | 95 MB | não | só a comparação da rodada 2019 | arquivar |

- **Total**: `data/saida/audio` tem 162 MB em 10 pastas, todas citadas por rodada. Por isso não
  há nada a apagar. Lixo de verdade são só logs de mensagem e de gate, com menos de 1 MB.
  Arquivar `a0`, `a1b` e `guitar-gaps` libera ~104 MB. É pouco, e eu faria só se o dono quiser.
- **O que dá para regenerar**: os clipes e as folhas, pelo `tab.audio_folha`, e o FLAC, pelo
  `tab.audio_extrair`. A regeneração relê o HD. Os 2 `.pth` voltam por download (revisão e
  sha256 na procedência), com o aval do dono.
- **Fora do repositório**: as imagens `chorinho-audio:dev` (6,6 GB) e `chorinho-som:dev`
  (1,5 GB) ficam no armazenamento do podman e não entram nos 27 GB. Os pesos do Basic Pitch
  vêm dentro do pacote pip da imagem.

**Respostas às 5 perguntas:**

1. **Candidatos ao `comum`:**
   - **A física do violão** (corda solta + casa + capo = a altura). Ela existe em 3 cópias:
     - `audio_onsets.midi_da_nota` e `MIDI_CORDA`;
     - `audio_som_medir.midi_da_nota`, uma cópia minha que eu tiro;
     - `musicxml.midi_da_corda`, da tablatura, que a partitura importa 3 vezes.

     Junto, vai a leitura do `capo_por_video.json` das mãos (`audio_som_medir.capo_do_video`).
     Proponho um `tab/comum/violao.py`, já que 3 trilhas a usam.
   - **O JSON atômico**: são 6 lugares no áudio, e o mesmo padrão aparece nas outras 3 trilhas.
     A exceção são os 2 transcritores, que rodam em Python 3.10 (objeção 5a). Eles só passam a
     usar o `comum` se ele for compatível com 3.10 e só de stdlib.
   - **O `audio_extrair` não vai para o `comum` agora.** Fora do áudio, só um rascunho da
     tablatura o importa. Ele fica em `tab/audio/extrair.py`, com o apelido, e vai para o
     `comum` quando um módulo de outra trilha em `tab/` precisar dele.
   - `_nfc` e a trava da GPU: o áudio não tem nenhum dos dois.
   - **O que eu uso de outras trilhas:**
     - `censo.chave_do_arquivo` (tablatura, por import);
     - o `capo_por_video.json` (mãos, por dado, com o caminho montado no módulo);
     - `tab.avaliar_video` (tablatura), só nos scripts de rodada (`data/saida/audio/r2020/`).
2. **Janela**:
   - Hoje à noite, depois da medida da rodada 2020. São minutos de CPU no container base, sem
     GPU, e os produtos dela já estão prontos.
   - Daí em diante, o áudio não tem treino, fila nem ferramenta rodando. A ferramenta e o túnel
     dos acordes já estão fechados.
   - O próximo lote grande (os 35 vídeos da T8.2, no HD) só começa com horário combinado com o
     dono, e eu o seguro até a fase 3 do áudio fechar.
   - **Para quem fizer a fase 2**: às 18h30, havia 1 ferramenta da tablatura rodando
     (`tab.ouro_video servir` da t84, porta 8126, há 5 h) e um container das mãos. A fase 2 muda
     o `tab/__init__.py`, e isso atinge esses processos (regra 6 do §2).
3. **Caminhos fixos fora do `caminhos.py`**:
   - `audio_som_medir` monta à mão:
     - `GOLD = RAIZ / "data" / "gold"`, usado para `ouro_video/` da tablatura e para `audio/`;
       o `caminhos.OURO_VIDEO` já existe e eu não o uso;
     - `SAIDA / "ouro_video" / <nome> / "pre.json"`, da tablatura;
     - `SAIDA / "maos" / "capo_por_video.json"`, das mãos;
     - `SAIDA / "audio" / "r2017"` e `r2018`.
   - `audio_produto.GABARITO_AUDIO` monta o caminho a partir de `RAIZ`.
   - `audio_folha.PREFIXO_ACERVO = "/acervo/"` é a convenção do container. Vira o
     `caminhos.acervo()`.
   - **Scripts**:
     - **60 arquivos** em `data/saida/audio/` chamam módulos de `tab` pelo nome antigo, quase
       todos do áudio, nas 3 formas:
       `python -m tab.audio_alinhar`, `from tab.audio_extrair import ler` e
       `from tab import audio_som_medir`. Os apelidos cobrem esses casos se o teste cobrir as
       3 formas (objeção 5b). Há também o `.sh` da M7, das mãos.
     - Os caminhos de dado nesses scripts são relativos a `/app`. Os de `data/saida/audio/`
       não mudam.
     - **Quebram** os que apontam para dados de outras trilhas (`data/saida/produto/mvp.json`,
       `data/gold/ouro_video/`, `data/saida/maos/…`), se a trilha dona mover a pasta sem link.
   - **Correção na minha fase 1**:
     - `audio_som_medir` e `audio_produto` passam a ler só pelo `caminhos.py`;
     - eu acrescento `GABARITO_AUDIO` e `SAIDA_AUDIO`;
     - peço às donas uma constante para o `capo_por_video.json` (mãos) e outra para
       `data/saida/ouro_video/` (tablatura).
4. **Pesos em uso**:
   - Só o `artefatos/riley_guitar/guitar-fl.pth` (sha256 `50d93dba…`).
     - O transcritor recebe o peso por `--pesos` e não tem caminho no código.
     - Mover para `artefatos/audio/riley_guitar/` muda só os comandos dos scripts e da
       procedência. Faço isso com um link relativo na fase 4.
     - O `caminhos.peso` não serve dentro do transcritor, porque ele não importa nada de `tab`.
       Ele serve no script que o chama.
   - `guitar-gaps.pth`: histórico, para arquivar.
   - O alinhador não usa peso.
   - O meu `EM_USO.json` vai ter 1 linha.
5. **Objeções, cada uma com a alternativa:**
   - **a. A imagem `chorinho-som` é Python 3.10**, e o gate não pega isso.
     - O que acontece: ela roda `python -m tab.audio_transcrever_riley` com o repositório
       montado, e o `import tab` executa o `tab/__init__.py`. Se o localizador, o
       `_apelidos.py` ou o que eles importam usar sintaxe 3.11+ (`except*`, `type X = …`,
       `class A[T]`) ou `tomllib`, o transcritor quebra no import.
     - Por que o gate não vê: ele roda no 3.14, e o protótipo do §4 também foi testado só no
       3.14.
     - **Alternativa**:
       - `tab/__init__.py`, `_apelidos.py` e `tab/audio/__init__.py` ficam só com stdlib e
         sintaxe 3.10, travados por um teste do gate:
         `ast.parse(fonte, feature_version=(3, 10))` nesses arquivos;
       - na fase 3, eu rodo um teste de fumaça na imagem som e registro no commit:
         `python -c "import tab.audio_transcrever_riley"`.
   - **b. O teste dos apelidos tem que cobrir `from tab import <nome antigo>`.**
     - Essa forma passa por outro caminho do import: primeiro um `getattr` no pacote, e só
       depois o submódulo.
     - O protótipo testou `import tab.x`, `from tab.x import` e `python -m`, mas não essa.
     - **Alternativa**: para cada apelido, o teste faz as 3 formas e confere com `is` que sai
       o módulo novo.
   - **c. O `caminhos.RAIZ` vem do `__file__`** (`Path(__file__).resolve().parent.parent`).
     - Em `tab/comum/caminhos.py`, ele passa a apontar para `tab/`, e todo caminho do projeto
       muda sem erro.
     - **Alternativa**: na fase 2, usar `parents[2]` e um teste do gate:
       `(RAIZ / "AGENTS.md").is_file()`.
   - **d. O `cruzar_fontes` não cabe em `tab/audio/` nem em `tab/comum/`.**
     - Ele é a etapa neutra da 2005: cruza tela e som, e depois as mãos. Se ficar dentro de
       uma trilha-fonte, quebra a Regra 1, e ele também não é utilitário.
     - **Alternativa**:
       - ele vai para `tab/cruzamento/`, com o áudio como dono até a 2005 virar decisão;
       - o pareamento que ele importa do `audio_som_medir` (`eventos_do_som`, `parear`,
         `iguais`) e a física vão para o `comum`;
       - assim o cruzamento não depende de nenhuma trilha-fonte.
   - **e. Para o áudio, a fase 4 é quase vazia**: os dados já estão em `data/saida/audio/` e
     `data/gold/audio/`. Só entram os `LEIAME.json` (fase 1) e o link de `riley_guitar/`.
   - **Nada quebra** nos outros pontos que o dono perguntou:
     - não há `multiprocessing`, worker nem pickle de nome de módulo no áudio. Tudo é JSON, e
       o pickle do `.pth` só monta tipos do numpy e do torch;
     - o `subprocess` chama só `ffmpeg`, `ffprobe` e `git`, nunca `python -m tab.…`;
     - os testes do áudio não importam outros testes e não há `conftest.py`, então o
       `--import-mode=importlib` não os afeta.

**Aceito ser a primeira trilha da fase 3**, com 4 condições antes:
1. a fase 2 no git, com os testes das objeções a, b e c no gate;
2. o meu código lendo os dados das outras trilhas só pelo `caminhos.py` (a minha fase 1);
3. a rodada 2020 medida e commitada;
4. a janela acima.

**O que eu faço na fase 3:**
- movo os 11 módulos para `tab/audio/`, com o nome sem o prefixo (`extrair`, `onsets`,
  `alinhar`…), e os 7 testes para `tests/audio/`;
- passo os 14 imports relativos a absolutos;
- registro os 11 apelidos.

O `cruzar_fontes` vai junto, para onde o dono decidir (objeção d).

**Como eu provo que nada mudou:**
- o gate;
- os 3 apelidos de cada módulo;
- o teste de fumaça na imagem som;
- e `python -m tab.audio_alinhar` (o nome antigo) no *retrato brasileiro*, conferindo que o
  JSON sai igual, byte a byte, ao de antes da mudança.

### Partitura

(sem resposta ainda)

### Mãos (2026-10-21, proponente)

1. **Comuns, do meu lado**:
   - o JSON atômico (`maos_gabarito.gravar_atomico`). Ele também aparece no `audio_extrair`,
     no `partitura_gabarito` e no `ouro_video`, por import ou por cópia;
   - a trava da GPU (`_trava_gpu`, que embrulha `tab.gpu`);
   - a leitura de um quadro por ffmpeg (`maos_braco_sintetico.quadro_em`). Ela repete o que o
     `leitor` da tablatura faz, e deveria passar a usá-lo;
   - `_nfc`.
2. **Janela**: a fila da 1041 roda até ~20h40 de 2026-10-21. Depois disso, as mãos não têm
   nada rodando até a revisão da 1039 pelo dono.
3. **Scripts que vão quebrar**: os `.sh` em `data/saida/maos/m37/` e `m41/`. Eles chamam
   `python -m tab.maos_braco_retreino*`, e os apelidos cobrem esse caso. Os caminhos de log são
   relativos à pasta da rodada.
4. **Pesos em uso**:
   - o ciclo usa `L3_todos_s3` + `A4_100_todos_s1`;
   - em prova: os da 1041 (`L5_capo3_s*` e `A7_capo3_s*`);
   - todos estão em `artefatos/m21/`.
5. **Ofereço fazer a fase 2** depois de 20h40, se as outras trilhas concordarem.

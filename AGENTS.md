# AGENTS.md — chorinho

> Contrato de trabalho deste projeto, para toda sessão e todo agente. Leia **inteiro** antes
> de rodar qualquer coisa. Revisado em 2026-10-22 (estrutura e padrão de projeto da 9001, §10).
>
> - **Números medidos** ficam em [`docs/estado/<trilha>.md`](docs/estado/), com o índice e o
>   que vale para todas as trilhas no [`ESTADO.md`](ESTADO.md), e nas rodadas (`docs/rodadas/`).
> - **Decisões** ficam em `docs/decisoes/`.
> - **O contexto de cada trilha** fica em `docs/guias/contexto-*.md`.
>
> Este arquivo diz o objetivo, o ambiente e as regras. Quando um número daqui divergir do
> `ESTADO.md` ou do `docs/estado/<trilha>.md`, vale o estado.

## 1. O objetivo

O dono quer uma **base de dados de violão** em que cada nota tocada nos vídeos-aula do acervo
tenha, juntos:

| camada | o que é | de onde vem |
| --- | --- | --- |
| **rótulo** | corda, casa e técnica de ataque (h, p, slide, X, harmônico…) | a **tablatura da tela** |
| **tempo** | quando a nota é marcada na tela (`t_ini`) e quando ela soa (`t_audio`) | o marcador da tela, e o som |
| **braço** | cordas, trastes e nut do violão, quadro a quadro | a imagem |
| **mãos** | as duas mãos, quadro a quadro, ligadas a cada nota | a imagem |
| **partitura** | ritmo e altura escrita, quando o vídeo tem pauta | a pauta da tela |

Com essa base, um modelo futuro vai receber **só vídeo e som** de alguém tocando e devolver
tablatura e partitura. Os vídeos têm tablatura na tela, e o dono afirma que ela é exatamente o
que é tocado. Por isso ela é o rótulo grátis, e todo o resto é a entrada que o modelo vai
aprender a ler.

**Três princípios que decidem quase tudo:**

1. **O rótulo vem só da tela** (decisão [0011](docs/decisoes/0011-tablatura-vira-rotulo-da-base.md)).
   O som, as mãos e a partitura **conferem** o rótulo, mas nunca o criam. Nada que o modelo
   futuro vai ver como entrada pode ser calculado a partir do gabarito.
2. **Falso positivo é o pior erro.** Uma casa vizinha errada afirmada contamina a base. Um "não
   sei" declarado só tira a nota do nível ouro. Toda etapa precisa saber **recusar**, ou
   **sinalizar** o caso para o dono revisar, em vez de chutar.
3. **Fontes independentes, cruzadas no fim** (decisão
   [2005](docs/decisoes/2005-validacao-cruzada-tela-som-maos.md), triangulação, proposta da
   trilha áudio).
   - Tela, som e mãos calculam cada uma a sua versão da nota, sem usar a resposta da outra.
   - Uma etapa final compara: 3/3, 2/3 apontando qual fonte errou, ou "sem dado".
   - A concordância só vale como número depois de calibrada numa amostra conferida pelo dono.

## 2. As trilhas

O trabalho é dividido em trilhas, e cada uma é tocada por uma sessão própria. As sessões **não
se falam direto**: o dono é a ponte. Uma decisão que afete outra trilha vira um arquivo em
`docs/decisoes/`, e a trilha dona dos arquivos decide o que muda neles.

| trilha | entrega | módulos e dados dela | rodadas e decisões | guia |
| --- | --- | --- | --- | --- |
| **tablatura** | o produto `chorinho/video@1` (`tab.tablatura.produto.video`): corda, casa, coluna, compasso, técnica e `t_ini` por nota. É o rótulo da base | `tab/tablatura/` (`produto/`, `leitura/`, `treino/`, `ataque/`, `ouro/`, `censo/`); `data/gold/ouro_video/`; `data/saida/tablatura/n4/` | `0NNN` | [`plano-do-produto.md`](docs/guias/plano-do-produto.md), [`plano-rotulo-tablatura.md`](docs/guias/plano-rotulo-tablatura.md) |
| **mãos e braço** | a base `chorinho/maos@1` (decisão 1007): o braço e as mãos quadro a quadro, e a ligação de cada nota às mãos | `tab/maos/` (`braco/`, `direita/`), `data/gold/maos/`, `data/saida/maos/`, `Dockerfile.maos` | `1NNN` | [`contexto-maos.md`](docs/guias/contexto-maos.md), [`plano-dataset-maos.md`](docs/guias/plano-dataset-maos.md) |
| **áudio** | `chorinho/audio@1` (`t_audio` por coluna, decisão 2003); em estudo, um transcritor que ouve sozinho (`chorinho/som@1`) | `tab/audio/`, `data/gold/audio/`, `data/saida/audio/`, `Dockerfile.audio` | `2NNN` | [`contexto-audio-retomada.md`](docs/guias/contexto-audio-retomada.md), [`contexto-audio-triangulacao.md`](docs/guias/contexto-audio-triangulacao.md) |
| **partitura** | `chorinho/partitura@1` (decisão 3002): ritmo e altura da pauta, pareados com a tab | `tab/partitura/`, `data/gold/partitura/`, `data/saida/partitura/`, `Dockerfile.partitura` | `3NNN` | [`contexto-partitura.md`](docs/guias/contexto-partitura.md) |

- **Cada trilha tem a sua pasta** em `tab/` e em `tests/` (decisão
  [9001](docs/decisoes/9001-reestruturacao-dos-arquivos.md), 2026-10-21):
  - `tab/tablatura/`, `tab/maos/`, `tab/audio/` e `tab/partitura/`;
  - `tab/comum/` guarda o que mais de uma trilha usa: `caminhos`, `gpu`, `leitor`, `cache`
    e `celular`;
  - `tab/cruzamento/` guarda a etapa neutra da 2005.
- **Os nomes antigos continuam valendo**: `tab.maos_braco_ciclo`, `tab.caminhos`… importam
  e rodam (`python -m`) o módulo novo, pelo localizador em `tab/__init__.py` e pela tabela
  `tab/_apelidos.py`. **Código novo usa o nome novo**, sempre absoluto
  (`from tab.comum.caminhos import ...`), sem import relativo.
- **Importar de outra trilha é livre. Editar o arquivo dela, não:** peça pelo dono.
- **Arquivos compartilhados:** `tab/comum/caminhos.py` (todos acrescentam os seus caminhos),
  `tab/comum/gpu.py` (a trava da GPU), `tab/__init__.py` e `tab/_apelidos.py`, e este
  `AGENTS.md`.
- **O estado medido** (decisão 9001, fase 5): cada trilha escreve a sua seção nova no fim
  do seu `docs/estado/<trilha>.md` (`tablatura`, `maos`, `audio`, `partitura`). O
  `ESTADO.md` é o índice e guarda só o que vale para todas, como a tabela "não repetir".
  O diário de 08 a 11/10 está em `docs/estado/historico-antes-das-trilhas.md`.

## 3. Onde o projeto está (2026-10-21)

São só os números de referência, com a fonte de cada um. O resto está em `docs/estado/<trilha>.md` (índice: `ESTADO.md`).

- **Acervo**: **4.096 vídeos em 21 canais, 215 GiB**, contados em 2026-10-21, e ainda
  crescendo, porque o dono segue baixando. Os canais com `rollout: fora` em
  `configs/canais.yaml` (decisão 0009) ficam fora da leitura de tablatura. Hoje, do acervo, é o
  `violaodecria`, que tem a tab em texto ASCII.
- **Leitura da tablatura**: o leitor do produto é a rede de sistema inteiro (decisão
  [0010](docs/decisoes/0010-leitor-rede.md)). Medido com validação cruzada por vídeo nos 8
  gabaritos (2.689 notas): **precisão 0,974, revocação 0,949, casa 0,987**.
  - O número antigo, 0,949 em 72 glifos e 3 canais, era do classificador de glifos
    (2026-10-09). Hoje ele é só histórico.
- **Tempo pelo marcador**: no vídeo do MVP (*retrato brasileiro*), **39 de 40 instantes
  certos e 0 tempos falsos** (Fase 5, 2026-10-10).
- **Tempo pelo som**: o tempo bate com a escuta do dono a ~100 ms (rodada 2008). Com o leitor
  `rede`, 0,858 das colunas recebem tempo nos 14 vídeos bons (rodada 2017).
- **Braço**: o ciclo de revisão funciona. Na 1032, medida pela regra antiga do capo, 63 de 64
  quadros saíram certos, e nenhum erro passou sem sinal.
  - Pela regra nova (decisão [1010](docs/decisoes/1010-capotraste-como-nut-do-braco.md)), o
    detector atual **erra o capo sem sinalizar** (16 de 64 certos na mesma 1032), até o
    retreino.
- **Partitura**: o dono conferiu a leitura da pauta, e **852 de 873 símbolos estão certos
  (97,6 %)**. Nas 12 telas da P1, **527 de 546 notas** saem certas quando a pauta é pareada com
  o produto.

## 4. Ambiente: como rodar de verdade

**Tudo roda em container.** O host tem um `.venv` só para o editor ler o código, e ele não
executa o pipeline.

- **O host** é um Bazzite (Fedora atômico) com **podman rootless**.
  - O daemon do docker não roda. O CLI `docker` fala com o socket do podman
    (`DOCKER_HOST=unix:///run/user/1000/podman/podman.sock`), com o override
    `compose.podman.yaml`. O `Makefile` já usa os dois arquivos.
- **A sessão do agente roda dentro de um distrobox**, sem `git`, `podman` nem `make`. Esses
  rodam no host, por `host-spawn`:

  ```bash
  host-spawn -no-pty -cwd "$PWD" git status
  host-spawn -no-pty podman run --rm --security-opt label=disable \
      --device nvidia.com/gpu=all \
      -v "$PWD":/app -v /run/media/gabriel/3014CD4714CD1130/chorinho:/acervo:ro \
      -w /app -e PYTHONPATH=/app docker.io/library/chorinho:dev python -m tab.x ...
  ```

  - Sem GPU, tire o `--device`.
  - `--security-opt label=disable` é obrigatório. Sem ele, o SELinux nega o bind-mount.
  - **Treino com `DataLoader` (workers) precisa de `--shm-size=2g`.** O `/dev/shm` padrão do
    `podman run` é de 64 MB, e o treino quebra com "unable to allocate shared memory". O
    `compose.yaml` já dá 1 GB (`shm_size`); o `podman run` direto, não (1037).
- **As imagens:**
  - **base**: `docker.io/library/chorinho:dev`, Python 3.14, venv em `/opt/venv` (fora de
    `/app`, para o bind-mount não esconder os pacotes);
  - **derivadas por trilha**: `localhost/chorinho-maos:dev`, `chorinho-audio:dev` e
    `chorinho-partitura:dev`.
  - **Dependência nova vai só na imagem derivada da trilha**, nunca na base. Use versão fixa,
    `--no-deps` quando a instalação tentar trocar `torch`, `numpy` ou `opencv`, e confira as
    versões antes e depois (decisões 1001, 2001 e 3001). Um pacote já trocou o `cv2` da base e
    quebrou uma trilha.
- **GPU**: uma RTX 3060 Ti de 8 GB, dividida entre as trilhas.
  - Use **`tab.comum.gpu.trava_gpu("trilha", "estimativa")`** em todo uso da GPU. Ela segue o
    protocolo `data/saida/gpu.lock`, retoma trava de processo morto e confere se há ≥ 3 GB
    livres.
  - **A GPU se divide pela memória** (dono, 2026-10-21): com outra trilha usando, a trava
    entra assim que houver ≥ 3 GB livres, em vez de esperar a outra terminar. Só com
    `checar_memoria=False` ela segue exclusiva.
  - Quem usa a GPU sem o código também cria o `gpu.lock` à mão: "trilha, início,
    estimativa".
  - Nunca pare o container de outra trilha.
  - A GPU no podman é por CDI (`/var/run/cdi/nvidia.yaml`, recriado no boot). Se ele sumir, o
    dono regenera com `sudo nvidia-ctk cdi generate`. **Agente não usa `sudo`.**
- **O acervo** fica em `/acervo`, **somente leitura**. No host, está em
  `/run/media/gabriel/3014CD4714CD1130/chorinho`, num HD externo.
  - **O HD é o gargalo de leitura**: duas leituras longas ao mesmo tempo dobram o tempo das
    duas. Leia uma vez para o cache (`tab.comum.cache`, `tab.audio.extrair`).
  - **Para um lote grande, combine o horário com o dono.**
- **Vídeo se lê por `tab/comum/leitor.py`.** 44 % do acervo é AV1, e o OpenCV não decodifica AV1:
  ele falha **em silêncio**, sem erro. O `ffmpeg` da imagem é o que lê.
  - Nomes com kana e acento precisam de normalização NFC na comparação.
- **`/tmp` do container não aparece no host.** O que precisa ser visto vai para
  `data/saida/`, e pesos vão para `artefatos/`. Modelo treinado em `/tmp` é modelo perdido, e
  isso já aconteceu.
- **Os arquivos escritos pelo container** (podman rootless) saem com o uid do usuário.
- **Cache dentro do container:** o ruff precisa de `--no-cache` (ou de `RUFF_CACHE_DIR=/tmp/…`),
  e o pytest, de `-p no:cacheprovider`. O `make gate` já faz isso.

## 5. Árvore e arrumação

```
chorinho-dataset/
├── AGENTS.md  README.md  ESTADO.md  PERGUNTAS.md  CONTEXTO.md
├── Dockerfile  Dockerfile.{maos,audio,partitura}  compose.yaml  compose.podman.yaml
├── Makefile  pyproject.toml  requirements.txt
├── tab/          # o pacote: comum/, cruzamento/, tablatura/, maos/, audio/, partitura/
├── tests/        # o gate, com uma pasta por trilha (sem GPU e sem acervo)
├── configs/      # canais.yaml (perfil e rollout por canal), simbolos.yaml (símbolo POR CANAL)
├── data/gold/    # gabaritos do dono: contrato
├── data/saida/   # o que é gerado, em <trilha>/ (ignorado pelo git, salvo exceções antigas)
├── artefatos/    # pesos (.pt fora do git; a procedência .md entra)
├── parts/        # recortes de amostra
└── docs/{HISTORICO.md, estado/, rodadas/, decisoes/, guias/, pesquisa/}
```

1. **Sem `.md` solto na raiz** além dos cinco acima. O `CONTEXTO.md` é o handoff de
   2026-10-10 e fica na raiz a pedido do dono.
2. **Um documento por rodada** em `docs/rodadas/NNNN-titulo-curto.md`, com o número da faixa
   da trilha. **Nunca apague documento de rodada.** Uma conclusão errada se corrige numa rodada
   nova.
3. **Uma decisão por arquivo** em `docs/decisoes/`: contexto, opções, decisão e
   consequências, com quem decidiu e quando.
4. **Um pacote só** (`tab/`), com uma subpasta por trilha (decisão 9001). Um nível a mais
   dentro da trilha só quando o grupo passa de ~10 módulos (ex.: `tab/maos/braco/`). Módulo
   novo entra na pasta da trilha e, se precisar de nome antigo, não precisa: só os 149 de
   antes da 9001 têm apelido.
   - `tab/__init__.py`, `tab/_apelidos.py`, todo `__init__.py` e `tab/comum/caminhos.py`
     ficam em sintaxe do Python 3.10 e só stdlib: a imagem do transcritor (3.10) e o
     `celular` (Python do host) importam `tab`. Um teste do gate trava isso.
5. **Modelo treinado vai para `artefatos/`**, com o comando, a semente e o commit registrados.
6. **Saída nova vai em `data/saida/<trilha>/`** (decisão 9001, fase 4). As 156 pastas
   soltas antigas foram para `data/saida/tablatura/` e `data/saida/partitura/` em
   2026-10-22, e o lugar antigo ficou com um link simbólico relativo: o caminho de antes
   continua valendo. As constantes do `tab/comum/caminhos.py` já apontam para o lugar novo (um teste do gate
   trava). Não apague nem substitua um desses links: o gabarito e os `.sh` antigos das rodadas
   ainda os usam.
7. **Caminho não se espalha.** Acervo, gabarito, saída e artefatos vêm de `tab/comum/caminhos.py`.
   Caminho absoluto novo no meio de um módulo é bug de revisão.

## 6. Como uma rodada funciona

Toda medida que decide alguma coisa segue este ciclo:

1. **Pré-registro, commitado antes de medir.** O documento da rodada diz:
   - a pergunta;
   - a amostra;
   - o que fica de fora;
   - o critério, com números;
   - o que fazer em cada resultado.
2. **Emenda só antes de medir**, registrada no documento, com o motivo. **Limiar não se muda
   depois de ver o resultado.**
3. **Prova lacrada.** Dado que já foi visto, ou usado para escolher algo, não é prova. Uma
   prova gasta se registra como gasta.
4. **Medida e leitura** vão no mesmo documento, com denominadores ("X de Y") e o commit do
   código.
5. **O que reprovou** vai para a tabela "não repetir" do `ESTADO.md`, com o motivo.

## 7. Regras de trabalho (cada uma custou rodadas)

1. **Semente fixa, determinismo e ≥ 3 execuções; reporte a média e a amplitude.** Com o cuDNN
   padrão, a **mesma** semente deu 0,927, 0,896 e 0,948, e o projeto tratou diferenças desse
   tamanho como ganho. O determinismo está em `tab.comum.semente.fixar_semente`, travado por teste.
2. **Meça a amostra antes de gastar treino.** Três retreinos foram queimados até descobrir que
   a classe nem nascia no gerador.
3. **Confira o significado do número.**
   - "323 notas com tempo" eram 3 instantes.
   - Com o `Dropout` ligado (`train()`), os mesmos pesos deram 0,812 onde em `eval()` davam
     0,865.
   - Uma fração entre dois leitores diferentes não se compara sem olhar o denominador, porque
     o leitor novo muda as colunas (rodada 2017).
4. **Olhe o quadro antes de teorizar.** Por duas vezes o violão foi medido como se fosse a
   tablatura: o braço tem 6 linhas e engana.
5. **Olhe a entrada real do modelo** antes de concluir que ele "não aprende". Três rodadas
   (~9 h de GPU) puseram mais dado para os arcos acima da corda 1, mas o recorte do painel
   apagava os arcos antes de chegarem ao modelo (rodada 0210). Desenhe o array normalizado.
6. **O pré-processamento é parte da medição.** Mudar a margem do recorte levou os **mesmos
   pesos** de 0,865 a 0,844. Mexeu no recorte, na taxa de amostragem ou na janela? A
   comparação com o histórico deixou de valer.
7. **Abra a folha inteira antes de endossar** uma conclusão visual. Uma rolagem por saltos foi
   rotulada "paginação" porque só a primeira linha da folha foi vista (C1, 2026-10-16).
8. **Rótulo de gabarito só por leitura (ou escuta) humana.** Relabelar por proxy geométrico
   piorou duas vezes. Um VLM marcando o braço reprovou em três rodadas (1016, 1019 e 1020).
9. **O gargalo histórico da leitura é a cobertura do gerador, não a regra de visão.** Foi
   medido 6 vezes: três regras geométricas deram 0, uma deu −0,166, e as duas mudanças de dado
   deram +0,05.
10. **Um instante não responde "tem tablatura?".** A tablatura aparece e some: dos 20 vídeos
    que um scan de 1 instante chamou de "sem tablatura", os 20 têm. Presença se mede ao longo
    do tempo (`tab.tablatura.censo.varredura --frac-inicio/--frac-fim`).
11. **Não valide uma fonte com ela mesma.** Usar a tab para numerar o braço e depois conferir o
    braço pela tab concorda por construção. O mesmo vale para as mãos achadas pelo tempo do som
    e depois conferidas pelo som (decisão 2005, Regra 1).
12. **Depois de editar gerador ou treino, valide o `import`, não só o `ast.parse`, e depois
    rode de verdade.** Um import de pacote errado já passou pelo `ast.parse`.
13. **Antes de remover um `int()` ou `round()`, meça o tipo real.** Índice de matriz e JSON
    dependem disso (RUF046).

## 8. O dono e o gabarito

- **O rótulo do dono é contrato.** Agente nunca altera nem infere rótulo dele, nem por
  conversão "óbvia". O agente não grava em `data/gold/`: só a ferramenta grava, quando o dono
  clica. Rótulo provisório de agente vai para `data/saida/`, marcado como tal.
- **O tempo do dono é o recurso mais escasso do projeto.** Ele marca ~50 quadros por hora.
  - Antes de pedir rótulo, diga para que serve e quanto custa.
  - Prefira **palpite por regra do domínio, pré-preenchido**, para ele só confirmar ou
    corrigir.
  - Use as ferramentas que já existem: `tab.tablatura.ouro.ouro_video servir` (notas) e
    `tab.maos.braco.gabarito servir` (braço). Não crie página nova.
- **Ferramenta de rotular se testa numa cópia**, nunca no gabarito ao vivo, porque ela grava a
  cada clique.
- **Decisão de gabarito é do dono.** Fora isso, ele confia na recomendação do agente. Para
  decisões que não são de gabarito, recomende uma opção e siga.
- **Janela longa sem o dono** (PC livre por horas):
  - siga a sua recomendação sem parar para perguntar;
  - se algo falhar, aprenda, revise e tente de novo;
  - **interrompa só por algo sério**;
  - no fim, entregue um relatório em português com o que deu certo, o que falhou e por quê.
  - Pré-registro, gate, a intocabilidade do gabarito e o "sem download sem aval" continuam
    valendo.
- **Pergunte antes** de qualquer download, dependência nova, ou ação fora do repositório.
  **Nunca escreva no acervo.**
- **Com o dono:**
  - fale em **português**, de forma simples, com números e denominadores;
  - mostre a imagem quando falar de um erro visual;
  - não mande status vazio ("ainda rodando"): fale quando houver resultado;
  - não o faça escolher de uma lista sem mostrar a lista.
- **Delegar a subagente: sempre Haiku 5.5**, com briefing fechado:
  - contexto, arquivos exatos, comandos, o que não tocar, critério e formato do relato;
  - depois, **revise o diff e meça de novo você mesmo**: o número que vai ao dono é o seu;
  - subagente não commita.
- **Nunca imprima, registre em log ou commite** a chave da API DeepSeek.

## 9. Git e gate

- **Git:**
  - `git add` só por nome;
  - **nunca** `add -A`, `reset`, `commit --amend`, `stash` ou `checkout --`, porque há outras
    trilhas no mesmo repositório;
  - mensagem por arquivo (`git commit -F arq`), com a linha de coautoria que a sessão pedir;
  - **um commit por tarefa**, com o número medido quando houver;
  - antes de commitar o `ESTADO.md` (tabela "não repetir"), confira `git diff ESTADO.md`: só as
    suas linhas entram. O seu `docs/estado/<trilha>.md` é só seu.
- **Nunca commite** `data/gold/partitura/compassos_homr.json` nem
  `data/gold/partitura/figura_e1.json`.
- **Gate antes de todo commit, sempre:**

  ```bash
  make gate   # no host, com DOCKER_HOST apontando para o podman; ou, no container:
  ruff check --no-cache . && ruff format --no-cache --check . && pytest tests/ -q -p no:cacheprovider
  ```

  - **Julgue pelo código de saída**, e nunca escreva `gate | tail && git commit`: o `tail`
    engole a falha. Isso já deixou passar um commit quebrado (b2904b05).
  - O gate roda na **imagem base**. Teste que importa biblioteca só de imagem derivada usa
    `pytest.importorskip`. Teste que lê o acervo leva a marca `integration`
    (`make test-integration`).
  - Um arquivo quebrado deixa o gate vermelho para todas as trilhas.
  - Se você não conseguiu rodar o gate, **diga isso explicitamente**.

## 10. Regras de código

- Python 3.14, **sem import dentro de função** (`PLC0415` no `pyproject.toml`).
- Aspas duplas, **88 colunas**, imports no topo em 3 blocos (stdlib / terceiros / locais).
- Type hints nas assinaturas e **docstring estilo Google** em toda função, método e classe
  pública.
- **Nomes em português** (`binarizar`, `achar_cordas`, `passo`, `glifo`).
- Módulo de CLI: `main()` + `if __name__ == "__main__"`, chamado como
  `python -m tab.<trilha>.<módulo>` (o nome antigo `python -m tab.<antigo>` também roda). Nada
  de código solto no nível do módulo.
- **Determinismo:** a mesma entrada dá o mesmo JSON. Toda aleatoriedade tem semente fixa e
  registrada.

### Padrão de projeto (decisão 9001, 2026-10-22)

**Onde cada coisa mora:**

| o quê | onde |
| --- | --- |
| módulo de uma trilha | `tab/<trilha>/`; subpasta quando o grupo passa de ~10 módulos (`tab/maos/braco/`) |
| o que 2 trilhas ou mais usam | `tab/comum/` |
| a etapa neutra da 2005 | `tab/cruzamento/` |
| teste | `tests/<trilha>/test_*.py` (o `--import-mode=importlib` aceita o mesmo nome em pastas diferentes) |
| saída gerada | `data/saida/<trilha>/<rodada ou frente>/`, com um `LEIAME.json` |
| peso treinado | `artefatos/<nome>`, plano e sem mover (o produto grava o caminho); o `.json`/`.md` de procedência junto; os que o código usa, em `artefatos/<trilha>/EM_USO.json` |
| número medido | o fim de `docs/estado/<trilha>.md`; o que reprovou, na tabela "não repetir" do `ESTADO.md` |
| arquivo frio | `chorinho_arquivo/<trilha>/*.tar` no HD do acervo, com o manifesto ao lado |

**Reaproveite antes de escrever.** Já existem, e não se copiam:

- `tab.comum.arquivos`: `gravar_atomico`, `ler_json`, `nfc`, `slug`;
- `tab.comum.violao.AFINACAO_MIDI` (corda solta → MIDI; a altura é solta + casa + capo);
- `tab.comum.semente.fixar_semente`;
- `tab.comum.acervo`: `chave_de`, `chave_do_arquivo`, `ler_rollout`, `canais_fora`;
- `tab.comum.leitor` (vídeo, também AV1), `tab.comum.cache`, `tab.comum.gpu.trava_gpu`,
  `tab.comum.caminhos`.

**Regras do padrão:**

1. **Uma função entra no `comum` quando a segunda trilha precisa dela.** Ela entra pública,
   com docstring e teste. O nome antigo fica no módulo de origem como reexportação (o mesmo
   objeto), e `tests/comum/test_comum_unificado.py` confere isso.
2. **Sem import de função privada de outro módulo** (`from tab.x import _f`). Há ~200 antigos,
   quase todos dentro das mãos: são dívida, não modelo. Precisou de um `_f` de fora? Torne-o
   público no módulo dele, ou no `comum` pela regra 1.
3. **Import absoluto e pelo nome novo**, sempre: `from tab.maos.braco.ciclo import ...`. Os 149
   nomes antigos (`tab/_apelidos.py`) existem só para não quebrar o que já roda. Módulo novo
   não ganha apelido.
4. **Toda pasta nova de `data/saida/<trilha>/` ganha um `LEIAME.json`** com `nome`, `trilha`,
   `classe` (`manter` / `arquivar` / `apagar`), `motivo`, `comando` (o que a regenera),
   `regeneravel`, `rodadas` e `citado_por`. É ele que decide a limpeza depois.
5. **Mudança de estrutura** (mover ou renomear módulo, pasta ou peso):
   - gate verde antes e depois;
   - a prova byte a byte de cada trilha, pelo caminho antigo:
     - áudio: `data/saida/audio/r2020/prova_9001/prova.sh`;
     - mãos: `data/saida/maos/prova_9001/prova.py`;
     - partitura: `data/saida/partitura/diag/r9001/prova_9001.sh`;
     - tablatura: `data/saida/prova_9001/tablatura/LEIA.md`;
   - dado movido deixa um link simbólico relativo no lugar antigo;
   - `git add` por nome.
6. **Apagar só depois do `.tar`**, conferido com `tar --compare` (código 0) e com o sha256 no
   manifesto. **Nunca se apaga**:
   - `data/gold/`;
   - `docs/rodadas/`;
   - um arquivo que o gabarito cita;
   - os links do topo de `data/saida/`;
   - um arquivo rastreado pelo git (esse sai por commit).
7. **Versões do Python:** tudo é 3.14 (imagem base). Só o transcritor do áudio roda em 3.10
   (`chorinho-som`), e por isso os arquivos que ele importa ficam em sintaxe 3.10 e só stdlib
   (§5, regra 4). Um teste do gate trava isso. Não crie outra imagem com outro Python sem uma
   decisão.

## 11. Decisões de dado que valem para todas as trilhas

- **Símbolo não se descarta.** Guarde o glifo cru, sempre, e classifique depois: cada canal tem
  o seu vocabulário (`h`, `p`, `/`, `\`, `<7>`, `(6)`, trêmolo), mapeado **por canal** em
  `configs/simbolos.yaml`. Perder informação é o único erro inaceitável. Símbolo ainda não
  classificado é dívida, não erro.
- **Técnica que importa é a que muda o ataque** (decisão 0011): h, p, mordente, ligadura de
  prolongamento, slide, X e harmônico. Na dúvida, o rótulo é "não sei", nunca "sim".
- **Capotraste** (decisões [1010](docs/decisoes/1010-capotraste-como-nut-do-braco.md) e 1007):
  - a tab da tela e o braço contam as casas **a partir do capo**;
  - a base guarda a casa real, que é a casa da tab mais a casa do capo, e grava a casa do capo
    à parte (`violao.capotraste`, com a fonte);
  - a física liga tudo: **corda solta + casa da tab + casa do capo = a altura que soa**.
- **Cru, confiança e nível; nunca exclusão calada.** O que não passou numa checagem fica
  marcado (ouro / prata / recusado), com o motivo, e não some.

## 12. Vocabulário

| termo | significado exato |
| --- | --- |
| **acervo** | os vídeos-aula do dono, em `/acervo` (somente leitura); ver a seção 3 |
| **canal** | uma pasta do acervo (um professor ou um site); o perfil fica em `configs/canais.yaml` |
| **produto** | o JSON `chorinho/video@1` de um vídeo (`tab.tablatura.produto.video`) |
| **painel** | a região da tela com a tablatura (varia por vídeo: topo, meio ou base) |
| **tela / exibição / passagem** | uma página de tablatura / um intervalo em que ela fica na tela / uma vez que ela é tocada |
| **coluna** | um instante da tablatura; um acorde é uma coluna com várias notas |
| **marcador** | o que indica a nota tocada na tela: uma **faixa** que passa, ou uma **cor** no algarismo; dá o `t_ini` |
| **`t_ini` / `t_audio`** | o tempo da coluna pelo marcador / pelo som. O atraso entre os dois é quase fixo dentro de um canal e muda entre canais (de −115 a +178 ms na rodada 2016) |
| **grade, passo, glifo** | a segmentação das cordas da tablatura; a distância entre cordas em px (14–45); um componente de tinta |
| **casa** | o número escrito na corda; no braço, o espaço entre dois trastes, contado a partir do nut (ou do capo) |
| **nut** | a pestana: a barra onde as cordas começam a vibrar. Com capo, o nut do braço é o capo |
| **braço** | o detector do braço do violão (cordas 1 e 6, trastes e nut), quadro a quadro |
| **sinalizado** | um quadro ou uma nota que a etapa manda para revisão em vez de afirmar |
| **falso que passa** | um erro entregue **sem** sinal; é a medida de segurança de toda etapa |
| **gabarito / ouro** | o rótulo conferido pelo dono, em `data/gold/` |
| **rodada** | uma medida pré-registrada, um documento em `docs/rodadas/` |
| **rollout** | rodar o pipeline em muitos vídeos, com decisão por vídeo |
| **triangulação** | o cruzamento tela × som × mãos (decisão 2005) |

## 13. Limites conhecidos (não prometa além disto)

- **Leitura da tablatura**: medida em 8 vídeos com gabarito (2.689 notas). A casa dos canais
  sem gabarito não está validada nota a nota. **Tab em texto ASCII** (ex.: `violaodecria`) e a
  **pauta** (essa é da trilha partitura) não passam por este leitor.
- **Técnica**: só a que muda o ataque está em medição (plano de rótulo da tablatura). O resto
  é guardado cru.
- **Tempo**: vídeos sem marcador só têm tempo pelo som, e o som tem resolução de ~100 ms. Tab
  só de ritmo, sem casa, não dá altura para alinhar.
- **Braço**:
  - sem capo, o ciclo de revisão é seguro nos canais medidos;
  - **com capo, espere o retreino (rodada 1037)**;
  - com o nut fora da imagem, o quadro vai para revisão em vez de ser numerado;
  - violão de 7 cordas só se marca à mão (botão `7`): o detector é de 6 cordas.
- **Validação cruzada (2005)**: é proposta. As fontes independentes do som (transcritor livre)
  e das mãos (corda e casa por quadro) ainda não existem.
- Perguntas abertas para o dono: [`PERGUNTAS.md`](PERGUNTAS.md).

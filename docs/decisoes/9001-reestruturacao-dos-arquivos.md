# 9001 — Reestruturação dos arquivos do projeto (todas as trilhas)

- **Situação**: **proposta v3**, escrita pela trilha mãos em 2026-10-21, a pedido do dono.
  - As 4 trilhas responderam (§8).
  - O dono respondeu às 3 primeiras perguntas (§7b); faltam as 3 do §7c.
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
9. **O rótulo do dono que mora fora de `data/gold/` é gabarito** (achado da tablatura, objeção
   a):
   - entram aqui as conferências que a ferramenta grava, as correções dadas no chat e os
     gabaritos convertidos que o treino lê;
   - **entra no git antes de qualquer outra coisa** (`git add -f` por nome, sem mudar o
     conteúdo);
   - nunca vai para o arquivo frio nem para "apagar";
   - muda para `data/gold/<trilha>/` só na fase 4, com a ferramenta parada.
10. **Arquivo que o gabarito cita fica no lugar e no git** (objeção b da tablatura). O gabarito
    não se edita, então o caminho dentro dele tem de continuar valendo.
11. **O código vivo e a procedência entram no git**: os scripts de treino e de medida que moram
    em `data/saida` e os `config.json` dos pesos (objeção c da tablatura).
12. **O número de testes pulados não pode subir.** Em cada fase, compara-se o resumo do
    `pytest -rs` antes e depois (objeção e da tablatura). Um teste que passa sem conferir nada
    é pior que um teste vermelho.
13. **Uma função que muda de módulo deixa o nome antigo no módulo antigo**, por reexportação
    (`_slug = slug`). O apelido de módulo não cobre um nome de função que saiu do arquivo, e
    há 4 módulos e 6 scripts da partitura que chamam `video._slug` (objeção da partitura).
14. **Uma função unificada no `comum` dá exatamente o resultado de hoje** em todas as
    entradas, e um teste compara com cada cópia antiga. Exemplo: a altura da nota (`violao`)
    contra as 5 cópias, em toda combinação de corda e casa. O capo é um parâmetro explícito
    (padrão 0), nunca somado por dentro: se fosse somado por dentro, a partitura inteira
    mudaria sem dar erro.

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
│   ├── comum/                  # o que mais de uma trilha usa (só stdlib no que o host roda)
│   │   ├── caminhos.py  gpu.py  leitor.py  cache.py  celular.py
│   │   ├── arquivos.py         # ler/gravar JSON (atômico), nfc, semente fixa
│   │   ├── acervo.py           # chave_do_arquivo, canais_fora, ler_rollout (do censo)
│   │   ├── violao.py           # corda solta + casa + capo = altura (hoje em 5 cópias)
│   │   └── ...
│   ├── cruzamento/             # a etapa neutra da 2005 (cruzar_fontes); não é de trilha-fonte
│   ├── tablatura/              # produto/ leitura/ treino/ ataque/ ouro/ censo/ (árvore no §8, Tablatura)
│   ├── maos/                   # braco/ (detector, localizador, ciclo, gabarito, retreino...), direita/, ...
│   ├── audio/
│   └── partitura/
├── tests/{comum,tablatura,maos,audio,partitura}/
├── data/
│   ├── gold/{tablatura,maos,audio,partitura}/
│   ├── saida/{tablatura,maos,audio,partitura}/<rodada ou frente>/LEIAME.json
│   └── cache/
├── artefatos/{tablatura,maos,audio,partitura}/<familia>/<nome exato de hoje>
│   └── <trilha>/EM_USO.json    # os pesos que o código usa hoje
└── docs/
    ├── decisoes/  rodadas/  guias/  pesquisa/  HISTORICO.md
    └── estado/{tablatura,maos,audio,partitura}.md
```

- **Subpastas.** Um nível de subpasta dentro da trilha só quando o grupo passa de ~10 módulos
  (ex.: `tab/maos/braco/`, com ~30). O nome do módulo perde o prefixo que vira pasta:
  `tab/maos_braco_ciclo.py` vira `tab/maos/braco/ciclo.py`.
- **O peso não muda de nome nem de formato**: a pasta (`detector_tab_x/modelo.pt` +
  `config.json`) ou o arquivo (`m21/L3_todos_s3.pt` + `.json`) mantém o nome exato de hoje. Só
  ganha a pasta da trilha e da família na frente. Há teste que confere o `parent.name`, e o
  `tab.video` compara caminhos resolvidos (objeção d da tablatura).
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
- **Os testes do gate que a fase 2 traz** (pedidos do áudio e da tablatura):
  1. **cada** apelido, nas **3 formas** (`import tab.x`, `from tab.x import f` e
     `from tab import x`), devolve **o mesmo objeto** (`is`) que o nome novo. Também confere
     que nenhum nome novo colide com um antigo;
  2. **`tab/__init__.py`, `_apelidos.py`, todo `tab/*/__init__.py` e o
     `tab/comum/caminhos.py` só usam a stdlib e a sintaxe do Python 3.10**
     (`ast.parse(..., feature_version=(3, 10))`). O `tab/comum/__init__.py` fica vazio. O
     motivo:
     - o transcritor do áudio roda na imagem `chorinho-som`, em Python 3.10;
     - o leitor SMT da partitura roda numa imagem com Python 3.11 e importa o `caminhos`;
     - o `celular` roda no Python do host;
     - todos importam `tab`.
     - O `leitor.py` já usa sintaxe do 3.14, então fica fora dessa lista. Quem roda em
       imagem antiga não pode importá-lo.
  3. **`(caminhos.RAIZ / "AGENTS.md").is_file()`**: em `tab/comum/`, a raiz passa a ser
     `parents[2]`. Se errar, todos os caminhos mudam sem nenhum erro;
  4. **os testes que varrem `tab/`** (como o `test_sem_videocapture`) usam `rglob` e um mínimo
     de arquivos conferidos. Sem isso, eles passam vazios.
- **Prova de que nada mudou**, por trilha, na fase 3: rodar um comando pelo nome antigo antes
  e depois e conferir que a saída sai igual, byte a byte. O áudio propõe o alinhador no
  *retrato brasileiro*.
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
| **1a** | **pôr no git o que só existe no disco** (regras 9 a 11): o rótulo do dono fora de `data/gold`, as imagens que o gabarito cita, os scripts vivos e os `config.json` dos pesos. Só acrescenta arquivos; pode começar já | cada trilha (a tablatura já começou) | nenhum |
| 1b | **inventário sem mover nada**: o `LEIAME.json` de cada pasta de saída (manter / arquivar / apagar, com o motivo), o `EM_USO.json` dos pesos, a lista de limpeza para o dono e os caminhos fixos fora do `caminhos.py`, corrigidos para ler o `caminhos.py` | cada trilha, nos seus arquivos | baixo |
| 2 | **base comum**: `tab/comum/` (as funções repetidas viram uma), `tab/cruzamento/`, os apelidos e os 4 testes do §4, `caminhos.peso`, `docker/` e o `--import-mode=importlib` | a mãos. `leitor`, `cache`, `celular` e as partes do `censo` são da tablatura, e ela as move | baixo, mas muda o `tab/__init__.py`: **só com as 4 trilhas paradas** (regra 6) |
| 3 | **código e testes de cada trilha**, uma por vez, numa janela sem treino nem ferramenta rodando. A ordem: **áudio** (12 módulos com o `cruzar_fontes`), partitura, mãos e tablatura. A tablatura lista antes para o dono os 5 ramos não juntados | a trilha dona | médio: os apelidos, a prova byte a byte e o gate pegam |
| 4 | **dados e pesos de cada trilha** para `data/saida/<trilha>/` e `artefatos/<trilha>/`, com links na transição | a trilha dona | médio |
| 5 | **`ESTADO.md` vira índice** + `docs/estado/<trilha>.md`. As seções antigas vão **inteiras, sem reescrever**, na ordem de hoje. O AGENTS §2, §5 e §10 são atualizados (sai o "um pacote só, plano") | cada trilha o seu; o AGENTS, combinado | baixo |
| 6 | depois de um ciclo inteiro sem uso, **sair dos links de dados** (os apelidos de código ficam) | cada trilha | baixo |

- **Cada fase é um commit por trilha**, com o gate verde e o mesmo número de testes pulados.
- **Uma fase só começa quando a anterior estiver no git nas 4 trilhas.** A exceção é a 1a, que
  cada trilha faz quando puder.
- **Calendário provável**, pelas janelas dadas no §8:
  - **1a e 1b**: já, em cada trilha;
  - **2**: a partir de 2026-10-22, quando a tablatura fechar a 0211 e a 0213 e parar a
    ferramenta da T8.4 e o `celular`. A fila da 1041 das mãos termina ~20h40 de 21/10;
  - **3**: áudio, partitura, mãos e tablatura, nessa ordem;
  - a partitura ainda não respondeu.
- **Limpeza das 6 cópias antigas do repositório** (`fase4_13`, `cifra`, `fn05`; 2,2 GB):
  - o dono pediu para limpar o inútil;
  - a recomendação é apagar as **duplicatas conferidas por hash** contra o repositório e pôr
    no `.tar` do frio só os 38 arquivos únicos, o `_diag` e os `tab/` copiados;
  - a lista item a item vai para o dono antes do `rm`.

## 6b. Revisões

- **2026-10-21, v1** (mãos): a proposta.
- **2026-10-21, v2** (mãos), com as respostas da tablatura (`d66f7a7d`) e do áudio
  (`0f713333`):
  - regras 9 a 12: o rótulo fora do ouro, as imagens que o ouro cita, os scripts vivos e o
    controle dos testes pulados;
  - o peso mantém o nome exato;
  - os 4 testes da fase 2 (Python 3.10 e stdlib, as 3 formas do apelido, a raiz, o `rglob`);
  - entram `tab/cruzamento/`, `comum/violao.py`, `comum/acervo.py` e `celular` no comum;
  - a fase 1a vem antes de tudo;
  - a fase 2 espera as 4 trilhas paradas.

- **2026-10-21, v3** (mãos), com a resposta da partitura (`08189389`):
  - regra 13: a função que muda de módulo deixa o nome antigo;
  - regra 14: a função unificada no comum tem de dar o resultado de hoje, e o capo é sempre
    um parâmetro explícito;
  - o teste 2 cobre o `comum/caminhos.py` (Python 3.11 da imagem SMT);
  - a partitura fica sem subpastas (21 módulos, nenhum grupo passa de 10);
  - 3 perguntas novas ao dono no §7c;
  - **as 4 trilhas responderam.** A partitura também topa a fase 3 logo depois do áudio.

**Fase 1a das mãos (2026-10-21): feita, mas dentro do commit `6c6f9695` da tablatura (0213).**
- **O que entrou**, por nome e sem mudar o conteúdo:
  - 14 arquivos no formato de gabarito que estavam em `data/saida/maos`: as cópias "antes" de
    marcas do dono e a remarcação cega da M11b;
  - a conferência dos 30 (1001);
  - 78 scripts `.py` e `.sh`;
  - as 44 procedências `.json` de `artefatos/m21`.
- **O que aconteceu**: eu deixei os 137 arquivos preparados (`git add`) enquanto o gate
  rodava. Nesse intervalo, a tablatura commitou a 0213, e o commit levou o índice inteiro.
- **Lição para as 4 trilhas** (o índice do git é um só): rodar o gate primeiro, e depois
  `git add <nomes> && git commit` **num comando só**. Nunca deixar arquivo preparado esperando.

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

## 7c. Perguntas novas para o dono (da revisão da partitura, 2026-10-21)

1. **Apagar a imagem do leitor SMT** (`chorinho-partitura`, 9,87 GB, fora do repositório)?
   - Ela não é usada desde a rodada 3003.
   - Refazê-la exigiria baixar os modelos de novo, e isso pede o aval do dono.
   - **Recomendação: sim**, se a partitura confirmar que nenhum plano próximo usa o SMT.
2. **A exceção à regra 9 para uma cópia de segurança.**
   - `compassos_homr.json` e `figura_e1.json` ficam onde estão e fora do git (AGENTS §9),
     e ganham uma linha cada no `.gitignore`.
   - A proposta é guardar uma **cópia** em `.tar` no arquivo frio. Hoje a única outra cópia do
     `compassos_homr` é a sobra de um teste da ferramenta.
   - **Recomendação: sim.** É cópia, não mudança de lugar, e é a única proteção desses dois
     arquivos.
3. **Os canais com pauta** (sua marcação de 17/10 no chat) não estão em nenhum arquivo.
   - A trilha mãos tem a lista na memória. A partitura transcreve para um arquivo marcado "a
     confirmar", e o dono confere.
   - **Só tablatura**: cifra club, kenneth acoustic, kimny's guitar, leonardo ramos,
     lonelypicker, mr. tabs, shin izumi.
   - **Misto**: guitar dell arte, iwaki, pablo romé, paolo d'angelo, robert lunn, serge
     kottelat, sky guitar, transcriptor, tv on guitar.
   - **Misto por vídeo**: ギタロー ⧸ guitarous.

**Respostas do dono ao §7c (2026-10-21):**
1. Sim: apagar a imagem `chorinho-partitura:smt`.
2. Sim: guardar uma cópia `.tar` dos dois gabaritos fora do git no arquivo frio.
3. Concorda: transcrever os canais com pauta para um arquivo "a confirmar".

**Quem executa (pedido do dono, 2026-10-21):**
- **A sessão das mãos que escreveu esta proposta faz a mudança inteira**, nas 4 trilhas. As
  trilhas não movem o próprio código.
- **Cada trilha continua fazendo a sua fase 1**:
  - versionar o rótulo e os scripts;
  - corrigir os caminhos fixos;
  - preencher o `LEIAME.json` e o `EM_USO.json`.

  Só a trilha dona sabe o que está vivo, e o rótulo fora do ouro foi achado assim.
- **Cada trilha confere depois**, com a sua prova byte a byte. A AGENTS §2 ("editar o arquivo
  de outra trilha, não") tem esta exceção, dada pelo dono.

## 8. Respostas das trilhas

Cada trilha escreve só na sua seção, com data.

### Tablatura (2026-10-21)

**Conferência dos números que tocam a tablatura.** Medi com `ls`, `wc`, `du`, `git ls-files`,
e com um grafo de imports por `ast` no Python 3.14 do container, em 2026-10-21:

| item | na proposta | medido | nota |
| --- | --- | --- | --- |
| módulos sem prefixo em `tab/` | ~51 | **51** (sem o `__init__`) | são da tablatura **48 módulos, 28.610 linhas**. Os outros 3: `caminhos` e `gpu` (comuns) e `cruzar_fontes` (áudio, rodada 2020) |
| imports relativos na tablatura | — | **136 linhas em 34 dos 48** | no projeto inteiro: **425 linhas em 117 arquivos**. Todas viram absolutas na fase 3 (§3) |
| testes da tablatura | — | **51 de 53** `tests/test_*.py` sem prefixo | os outros: `test_cruzar_fontes` (áudio) e `test_gpu` (comum) |
| outra trilha → tablatura | mãos 9, partitura 10, áudio 1 | por arquivo: **mãos 8, partitura 10, áudio 1** | detalhe na pergunta 1 |
| `data/gold/` solto na raiz | ~17 arquivos | **15 arquivos + 3 pastas** (4.678 arquivos nas pastas), **todos da tablatura** e todos no git | 18 das 22 entradas do `data/gold/`. Leitores na tabela abaixo |
| `simbolos_*` no git | 18 mil | **18.372 arquivos em 8 pastas, 79,5 MB** (+18 da `simbolos/`) | **nenhum código nem teste lê** essas 8 pastas. O `ESTADO.md` cita 2 (`_antes` e `_tamanho`, linhas 294 e 358). São a coleta de símbolos de 2026-10-09 (commit `6875b13a`) |
| `data/saida` rastreado | 20.104 | **20.104**, e **20.102 são da tablatura** | os 2 restantes são de `part_frentes` |
| tablatura em `data/saida` | — | **3,9 GB em 158 entradas** (97 pastas + 61 arquivos soltos) | o `gpu.lock` é comum. 575 scripts `.py` fora das cópias de código |
| pesos da tablatura | — | **188 `.pt`, 339,5 MB**: 145 pastas `detector_tab_*` (312 MB) e 51 pastas pequenas | de 231 `.pt` em `artefatos/`. Dos 3,1 GB, as mãos têm 2,6 GB (`m21`) e o áudio 189 MB. O `artefatos/torch/` (45 MB, resnet18) é das mãos |

**Os 15 arquivos e 3 pastas soltos em `data/gold/`** (todos rótulo do dono, de 2026-10-09 a 12):

| entrada | quem lê |
| --- | --- |
| `gabarito.json` (96 glifos) | `caminhos.GABARITO`: `sintetico`, `avaliar`, `digito` e o teste `test_gabarito` (gate) |
| `portao.json` | `portao.GOLD_PORTAO`; as imagens dos casos ficam em `data/saida/portao_casos` |
| `simbolos.json`, `simbolos_2.json`, pasta `simbolos_crops/` (49) | `digito` (treino do discriminador do leitor `glifos`) |
| `simbolos_marcados.json`, pasta `simbolos_marcados/` (3.208) | `simbolo` |
| pasta `simbolos_marcados_j25/` (1.421) | é **saída** do `regerar_janela` (recortes refeitos a partir das marcas). É derivado, não rótulo |
| `marcas_simbolos_6.json` | `fimafim` e `folha_simbolos`, por caminho relativo ao diretório atual |
| `presenca_quadros.json` | `presenca_aval` e 12 scripts em `data/saida` |
| `simbolos_3.json`, `marcas_simbolos{,_2..._5}.json`, `auditoria_simbolo_rotulada.json`, `folha_labels.json` | **nenhum leitor**. São rótulos históricos, ficam no ouro |

**Respostas às 5 perguntas:**

1. **Candidatos ao `comum`** (o que outra trilha importa da tablatura, por arquivo):
   - `leitor`: partitura 3. As mãos repetem o leitor em `maos_braco_sintetico.quadro_em`.
     Vai para o `comum`.
   - `cache`: mãos 4, partitura 2. Vai para o `comum`.
   - `censo`: só `chave_do_arquivo` (áudio 1, mãos 1) e `canais_fora`/`ler_rollout` (mãos 1)
     vão para o `comum` (`comum/acervo.py`). O resto do `censo` (938 linhas) fica na
     tablatura.
   - `sintetico.fixar_semente`: mãos 2. Vai para o `comum` (a semente fixa de §10). O gerador
     fica na tablatura.
   - `video._slug`: partitura 4, importando uma função **privada**. Vira pública no `comum`.
   - `musicxml.midi_da_corda`: partitura 4. Apoio o `comum/violao.py` do áudio. A tabela das
     cordas soltas (64, 59, 55, 50, 45, 40) existe em **5 cópias**: `musicxml.AFINACAO_PADRAO`,
     `audio_onsets.MIDI_CORDA`, `audio_som_medir.ALTURA_SOLTA`,
     `maos_corda_sem_direita.AFINACAO_MIDI` e `maos_direita_desempate.AFINACAO_MIDI`.
   - `ouro_video.gravar_atomico`: vai para o `comum/arquivos.py`, com o das mãos.
   - **`celular` também é comum**: abre no celular as ferramentas de todas as trilhas
     (`ouro_video servir`, `maos_braco_gabarito servir`). Ele **roda no host**, com o
     `python3` 3.14.8 do Bazzite e fora do container. Por isso o `tab/__init__.py` e o
     `_apelidos.py` têm de importar só a stdlib (é a objeção a do áudio, agora também no host).
   - `tabseg.segmentar` (mãos 1) fica na tablatura, importado pelo nome público.
2. **Janela**: ver a proposta no fim desta seção.
3. **Caminhos fixos fora do `caminhos.py`, e scripts que quebram:**
   - **Em `tab/`**:
     - o caminho do ouro é montado à mão em `digito` (`SAIDA.parent / "gold" / ...` e
       `SAIDA / "frames" / "gold"`), `simbolo` e `regerar_janela`
       (`ARTEFATOS.parent / "data" / "gold" / ...`), `portao` (`GABARITO.with_name(...)` e
       literais `"data/saida/frames/..."`), `presenca_aval` e `avaliar`;
     - `fimafim` e `folha_simbolos` usam o padrão `"data/gold/marcas_simbolos_6.json"`,
       relativo ao diretório atual;
     - os pesos são montados por nome em `ataque_rotulo.DETECTOR_CALIBRADO`,
       `ataque_r4.modelo_da_dobra`, `detector_tab` (`detector_tab_s<n>`), `digito`
       (`digito_2`), `simbolo` (`simbolo_2`, ou pela variável `SAIDA_SIMBOLO`) e `simbolos`
       (`oficial_2`);
     - o `video` grava os recortes em `SAIDA / "video"`.

     Corrijo tudo isso na minha fase 1: cada um passa a ler uma constante do `caminhos.py`.
   - **Os scripts vivos de `data/saida`** chamam a tablatura nas três formas:
     - **107** fazem `sys.path.insert(0, "/app")`;
     - `from tab import detector_tab as D` e funções privadas (`D._amostra_treino`,
       `D._iniciar_trabalhador`) aparecem no `n4/treinar_ft.py`;
     - **10** fazem `sys.path.insert(0, "/app/data/saida/n3")` e `import medir`. Entre eles
       estão `tab_rotulo/diag/painel_0213.py` e `diag/recorte_comum.py`, da 0212 e da 0213;
     - **3** importam o `n4`.

     Os apelidos cobrem os imports. Os links de dado cobrem os caminhos absolutos
     (`treinar_ft.py`: `CACHE`, `CACHE_T82`, `PARTIDA` e `OURO_VIDEO` em `/app/...`).
   - **O que quebra mesmo com os apelidos:**
     - **4 scripts antigos importam testes pelo nome** (`fase4_digitos/probe_*.py` ×3 e
       `painel_braco/dbg_test.py`, com `sys.path.insert(0, "/app/tests")`). Eles quebram
       quando os testes forem para `tests/tablatura/`. São históricos, e eu aceito a quebra.
     - **`n3/medir.videos_do_run()` lê `data/saida/barline_fina/run.sh`** para saber o vídeo
       de cada ouro. Mas o ouro já tem o campo `video`. Na fase 1, eu passo o `medir` a ler o
       ouro, e o `barline_fina` deixa de ser dependência viva.
     - **Os 145 `config.json` dos pesos** registram
       `"comando": "python /app/data/saida/n4/treinar_ft.py ..."`. O link de `n4` mantém
       esse caminho válido. **O conteúdo deles não se edita.**
4. **Pesos em uso** (61 das 145 pastas `detector_tab_*`, ~134 MB):

   | uso | pastas |
   | --- | --- |
   | o produto, leitura comum (`DETECTOR_PADRAO`) | `detector_tab_final_s1_ger` |
   | o rótulo de ataque (`DETECTOR_CALIBRADO`) | `detector_tab_final_atqt_s1` |
   | a validação **pendente** da 0211 na T8.4 | as 45 de `_atqa`, `_atqt` e `_atqe` (`final_*_s{1,2,3}` e `v3ft_d{1..4}_*_s{1,2,3}`) |
   | a comparação da 0212 | as 14 de `_ger` (`v3ft_d{1..4}_ger`, `_ger_s2`, `_ger_s3`, `final_s{2,3}_ger`) |
   | a partida do ajuste fino (`PARTIDA`) | `detector_tab_v3_s1` |
   | o leitor `glifos` e as ferramentas antigas | `oficial_3` (`MODELO_PADRAO`, também no teste `test_casa_dois_digitos`), `oficial_2` (`simbolos`), `digito_2` e `simbolo_2` |

   - **Histórico**: são 84 pastas `detector_tab_*` (~181 MB): `_atq`, `_atqg`, `_atqc`,
     `_atqma`, `_atqmb`, `_arcop`, `_gerx`, `v3ft_d*` sem sufixo, `final_s{1,2,3}`, `s1`,
     `s2`, `v2_*`, `v3_s2` e `v3_s3`. Somam-se ~20 MB de pesos pequenos: `serif*` 12,
     `portao*` 11, `candidato_*`, `casas24_*`, `det_C`, `j25`, `oficial_1`, `digito_{1,3}`,
     `simbolo_{1,3}`, os `simbolo_j25_*` (vazios) e o `glifo_sint.pt` solto na raiz.
   - **Só arquivo esses pesos depois que a 0211 fechar.** A família vencedora entra no
     `EM_USO.json`.
   - **Não há risco de pickle**: os 231 `.pt` de `artefatos/` só guardam `OrderedDict` e
     tensores (medido com `pickletools`). Nenhum cita um módulo `tab.*`. O único `.pkl` da
     tablatura (`serif/cache_rois.pkl`) só cita o numpy.
5. **Objeções, cada uma com a alternativa** (em ordem de gravidade):
   - **a. Há rótulo do dono em `data/saida`, e fora do git.** Esta é a mais grave. A
     `.gitignore` ignora `data/saida/`, e tudo isto existe numa cópia só, no disco:
     - as conferências que a ferramenta grava a cada clique:
       `t82/ferramenta/conferencia_t82.json`, `t83/ferramenta/conferencia_t83.json` e
       `t84/ferramenta/conferencia_t84.json`. A última está sendo gravada agora: o
       `ouro_video servir --ouro data/saida/t84/...` roda desde as 13:18;
     - **três versões diferentes da T8.2**: `t82/ferramenta` (15/10, 15:50), `t82/erros`
       (15/10, 15:34) e `tab_rotulo/r2/conferir_novos` (18/10, que tem o passe do modo
       ataque). O `cmp` diz que as três diferem;
     - **correções que o dono deu no chat, escritas como constantes de script**:
       `tab_rotulo/r2/novos_t84.py` (`CORRECOES_DO_DONO`, `NOTAS_DO_DONO` e
       `ATAQUE_DO_DONO`);
     - os gabaritos de ataque convertidos (`tab_rotulo/r2/conferir*/ataque_*.json`). O treino
       lê esses arquivos (`treinar_ft.py`, `ataque_r4.GABARITOS`), e a 0211 os chama de
       "Gabarito".

     **Alternativa:**
     - **Na fase 1, antes de qualquer outra coisa**, eu versiono esses arquivos onde estão, com
       `git add -f` por nome. São ~6 MB. O conteúdo não muda.
     - Na minha fase 4, com a ferramenta parada, as conferências vão para
       `data/gold/tablatura/conferencias/t8x/`, e as três versões da T8.2 vão juntas, sem
       escolher uma. Os scripts com as correções do chat também vão para lá.
     - O próximo lote já serve a ferramenta com `--ouro` dentro do `data/gold/`.
     - **Nenhuma dessas pastas** (`t82`, `t83`, `t84` e `tab_rotulo`) entra no arquivo frio
       nem no "apagar".
   - **b. O ouro cita imagens de `data/saida`.** O `git rm --cached` dos 20.104 e a limpeza têm
     que poupar essas imagens.
     - **25 caminhos** citados dentro de `data/gold` existem hoje, e todos estão no disco:
       - `frames/folha_{A..N}.png` e `folha_simbolos_{1,2,3}.png` (do `portao.json` e dos
         `simbolos*.json`). Estes estão no `.gitignore`, então **não estão no git**;
       - `c1b/folha_novas.jpg`, `cifra/vn_suspeitos.jpg`, `diag_v2/gold2/`,
         `fn05/folha_novas.jpg`, `presenca/` e `presenca_7_1/revisao_FN05.jpg` (do
         `presenca_quadros.json`);
       - `t500/quadros_500.jpg` (do `ouro_video/retrato_brasileiro_v2.json`).
     - **São a imagem do rótulo**:
       - `frames/gold/` (3 PNGs, lidos pelo `avaliar` e pelo `digito`);
       - `portao_casos/` (122 de 290 PNGs no git);
       - `auditoria_simbolo/` (248, as janelas que o dono auditou).

     **Alternativa:**
     - essas entradas ficam **no git**, e o resto dos 20.104 sai do índice (cerca de 19.700
       arquivos);
     - as `simbolos_*` saem do índice e podem sair do disco depois do `.tar`, porque o
       histórico do git já as guarda;
     - o ouro não se edita, então o caminho antigo continua valendo, pelo arquivo no lugar ou
       por link.
   - **c. Código vivo e procedência fora do git.** Os scripts de treino e de medida da
     tablatura moram em `data/saida` e não estão versionados:
     - `n4/treinar_ft.py`, que gerou o `DETECTOR_PADRAO`;
     - `n4/extrair*.py`, `n4/cache_alto.py` e `n3/medir*.py`;
     - `tab_rotulo/r2/*.py`, `r4g/decidir.py` e `t84/gerar.py`.

     São **~66 `.py`**. As rodadas citam "o commit do código", mas esse código não está em
     commit nenhum. Os 145 `config.json` dos pesos (140 KB) também ficam fora, porque só
     `artefatos/*.md` entra.

     **Alternativa:**
     - na fase 1, versionar esses scripts e os `config.json` (exceções na `.gitignore`);
     - na fase 3, o `treinar_ft.py` vira módulo (`tab/tablatura/treino/ajuste_fino.py`), e no
       lugar dele fica um script de 3 linhas, para os comandos dos `config.json` continuarem
       valendo.
   - **d. Não achatar o peso em `<familia>/<peso>.pt`** (o §3 mostra
     `<familia>/<peso>.pt + .json`).
     - Hoje cada peso é uma pasta com `modelo.pt` e `config.json`.
     - O `test_ataque_r4` confere o `parent.name` da pasta.
     - O `tab.video` compara `Path(detector).resolve()` com `DETECTOR_CALIBRADO.resolve()`.
       Uma cópia no lugar de um link reprova essa comparação.

     **Alternativa:**
     - `artefatos/tablatura/detector_tab/<nome de hoje>/modelo.pt`, mantendo o nome exato da
       pasta;
     - `caminhos.peso` antes de mover, usado também pelo `ataque_r4.modelo_da_dobra`, pelo
       `treinar_ft.py` e pelo `n3/medir.DETECTORES_CAMINHO`;
     - o arquivo frio só por `.tar`, porque `det_C` tem maiúscula.
   - **e. Testes que, depois da mudança, passam vazios ou pulam calados**, e o gate continua
     verde:
     - **`test_sem_videocapture`** faz `(RAIZ / "tab").glob("*.py")` sem recursão, com
       `RAIZ = parents[1]`. Com os módulos em subpastas, ou com o teste em `tests/comum/`,
       ele confere 0 arquivos e passa. A trava do AV1 (AGENTS §4) morre calada;
     - `test_casa_dois_digitos` usa `Path("artefatos/oficial_3/glifo_sint.pt")` e vira
       `skip` se o peso se mover;
     - `test_esquema::test_saida_real_do_motor_valida` vira `skip` sem a
       `data/saida/fase5/mvp.json`.

     **Alternativa:**
     - `rglob`, com um mínimo de arquivos conferidos (≥ 140);
     - o caminho do peso pelo `caminhos`;
     - `fase5/` em "manter";
     - e em cada fase, comparar o resumo do `pytest -rs` (passados e pulados) antes e depois.
       O número de `skip` não pode subir.
   - **f. Os apelidos do §4: o que medi que não quebra na tablatura.**
     - O multiprocessing é só `fork`: `detector_tab` e `treinar_ft` usam
       `mp.get_context("fork")`, e o `Pool` manda a função pelo `__module__`, que o
       processo filho já tem.
     - Não há `spawn`, `forkserver`, `__module__`/`__qualname__` em JSON, cache indexado por
       nome de módulo, `importlib` nem `monkeypatch` por string nos testes da tablatura.
     - O `tab.cache` usa a chave `relativo|tamanho|mtime` do vídeo, sem nada do código.
     - A forma `from tab import X as D` (objeção b do áudio) é a dos scripts de treino: o
       teste dos apelidos precisa dela.
     - O `gerado_por.modelo` do produto é o caminho do peso relativo à raiz. Ele muda quando o
       peso se mover. Ninguém compara esse campo, mas a regra "mesma entrada, mesmo JSON"
       passa a valer só com o peso no mesmo lugar. Registro isso na rodada que mover os
       pesos.
   - **g. Os ramos não juntados da tablatura**, que vão dar conflito de renome:
     - `tab/c1-rolagem` tem 14 commits fora da main, e `tab/f0-regua-tecnica`, 10;
     - `tab/e-sondas` tem 2, e `tab/d1-som-casa` e `dsh-tablatura`, 1 cada;
     - todos são de 15 a 16/10, e as worktrees deles estão `prunable`.

     **Alternativa:** antes da minha fase 3, eu listo para o dono o que cada ramo tem, e ele
     decide juntar ou arquivar o ramo (`git tag`). Nada se apaga.
   - **h. O `ESTADO.md`**: dos 268 títulos `##`, só 12 começam por "Tablatura", e a maior parte
     dos 231 sem trilha é da tablatura (fases 0 a 8).
     - **Alternativa**: o `docs/estado/tablatura.md` recebe essas seções **inteiras, sem
       reescrever**, na ordem de hoje.
     - O índice fica com os números oficiais (0,974 · 0,949 · 0,987 em 2.689 notas; 39 de 40
       instantes) e com a tabela "não repetir" comum.

**A árvore que proponho para os 48 módulos da tablatura:**

```
tab/tablatura/
├── produto/   video, telas, estado, esquema, colunas, tempo, destaque, musicxml,
│              transcrever, pipeline
├── leitura/   painel, tabseg, cursor, reconhecer, detector_tab, digito, simbolo, portao,
│              inventario, glyphset, glyph_bench, marcador, formas_do_marcador
├── treino/    sintetico, sintetico_sistema (+ o ajuste_fino, vindo do n4/treinar_ft.py)
├── ataque/    ataque_base, ataque_rotulo, ataque_r4, ataque_pares, ataque_divergencia
├── ouro/      ouro_video, ouro, conferir, avaliar, avaliar_video, auditoria, presenca_aval
└── censo/     censo, varredura, afinacao, simbolos, folha_simbolos, fimafim,
               regerar_janela, exp_binarizacao
```

- Vão para o `comum`: `leitor`, `cache` e `celular`.
- **O produto depende do gerador**: o `tab.video` puxa 27 módulos, entre eles o
  `sintetico_sistema` (3.513 linhas, via `detector_tab`). Por isso o `treino/` não pode ser
  tratado como "fora do produto".
- **O nome perde só o prefixo de grupo**: `ataque_r4` vira `ataque/r4`. Os outros nomes ficam
  iguais, para o apelido ser óbvio.

**O disco da tablatura (3,9 GB em `data/saida` e 0,34 GB em `artefatos`):**

| classe | o quê | MB | por quê |
| --- | --- | --- | --- |
| **manter** | `t82` 178, `t83` 77, `t84` 72, `tab_rotulo` 105 | 432 | rótulo do dono e gabarito de ataque (objeção a) |
| manter | `n4` 60, `n3` 37, `barline_fina` 4 | 101 | treino e medida vivos (0211 a 0213) |
| manter | `ouro_video` 158, `censo` 48, `produto` 13, `fase8` 25, `conserto_v2` 19, `fase5` 5 | 268 | ferramenta dos 8 ouros, o censo, o `MVP` e o `FASE8_GER` (lidos pelas mãos, pelo áudio e pela partitura), um teste |
| manter | `frames` 67, `portao_casos` 118, `auditoria_simbolo` 7, `simbolos` 24, `paineis` 15 e os citados pelo ouro (`c1b`, `diag_v2`, `presenca`, `presenca_7_1`, `t500`) | ~270 | a imagem do rótulo (objeção b); o treino do `digito` lê a `simbolos` |
| manter | `tab_frentes` 70 | 70 | `TAB_FRENTE_*` e as rodadas 0101–0170 |
| **arquivar** (`.tar` no frio, depois sai do disco) | 6 cópias inteiras do repositório: `fase4_13` 1.129, `cifra` 788, `fn05` 308 | 2.225 | snapshots de 10/10 para comparar versões do código. Medido: nos `data/` delas, só 38 arquivos não têm par no repositório principal (26 na `cifra/copia`, 12 na `fn05/copia`), e o resto é duplicata. Como a 0008 cita a `fase4_13`, vai para o frio, não para o lixo. Ficam no lugar `cifra/vn_suspeitos.jpg` e `fn05/folha_novas.jpg`, que o ouro cita |
| arquivar | `painel_braco` 191, `video` 53 (12.908 recortes de glifo do `tab.video`, que nenhum JSON cita), `simbolos_*` 80, `afinacao` 31, `serif` 18, `fase5_moldura` 18, `n1` 17, `fase4_arco` 14 | 422 | histórico citado no `ESTADO.md`, regenerável só relendo o HD |
| arquivar | ~45 pastas e arquivos pequenos de 08 a 14/10 (`fase4*`, `fase5b`, `fase6_*`, `haiku_*`, `tempo_gs*`, `limiar_tinta`, `n2`, `intervalos*`, `novas*`, `coleta_tab`, `tablaturas`, os `.txt`/`.json` soltos…) | ~110 | histórico. Antes de cada `rm`, a lista vai item a item para o dono (regra 7) |
| arquivar | 84 pastas `detector_tab_*` e ~20 MB de pesos pequenos | ~200 | histórico, **só depois de a 0211 fechar** |
| **apagar** sem arquivar | `__pycache__` dentro de `data/saida` e a pasta vazia `presenca_v2` | ~2 | regenerável e sem valor |

- **Somas**: manter ~1,15 GB; arquivar ~2,95 GB (2,75 de saída + 0,2 de pesos), que saem do
  SSD; apagar ~0,002 GB.
- **Apagar de verdade quase nada**, porque cada pasta grande da tablatura é citada ou guarda
  rótulo. O espaço vem do arquivo frio. O HD tem 575 GB livres (medido com `df`).
- **Alternativa mais agressiva**, se o dono quiser: apagar sem `.tar` as duplicatas dentro das
  6 cópias (~2,1 GB), arquivando só os 38 arquivos únicos, o `_diag` da `cifra/copia` (64 MB)
  e os `tab/` copiados.

**A janela da tablatura** (para as fases 3 e 4; a fase 2 também precisa dela, porque muda o
`tab/__init__.py`):
- **Hoje, rodando**:
  - a ferramenta da T8.4 (`ouro_video servir`, porta 8126, desde as 13:18), que espera o passe
    do dono no modo ataque;
  - o `celular` no host (desde as 09:52);
  - e ainda falta a medida da 0213 (~1 h).
- **Depois do passe do dono**, há ~10 min de GPU para fechar a 0211. Os treinos de hoje já
  acabaram.
- **Proposta**: a janela da tablatura abre quando a 0211 e a 0213 estiverem medidas e
  commitadas e a ferramenta e o `celular` estiverem parados. Pela ordem do §6, a tablatura é
  a última, e isso deve cair a partir de 2026-10-22.
- **Até lá, nenhum lote novo da tablatura** (T8.5) começa, e eu aviso o dono quando a janela
  abrir.
- **A minha fase 1 começa já**: o versionamento da objeção a só acrescenta arquivos. Os
  caminhos do item 3 ficam para depois do passe do dono.

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

### Partitura (2026-10-21)

**Conferência dos números que tocam a partitura.** Medidos em 2026-10-21 com `ls`, `wc`, `du`,
`git ls-files`, `podman` e um grafo de imports por `ast` no Python 3.14 do container
(`data/saida/partitura/diag/r9001/imports.py`):

| item | na proposta | medido | nota |
| --- | --- | --- | --- |
| `tab/partitura_*.py` | 21 | **21 módulos, 13.527 linhas** | `partitura_gabarito` (2.595) e `partitura_video` (2.055) são os maiores |
| testes | — | **10** `tests/test_partitura_*.py` | 11 módulos não têm teste próprio: `amostra*` (4), `avaliar`, `censo`, `imagem*` (2), `completar_itens` e `regua_tempo`/`regua_troca` |
| partitura → tablatura | 10 | **10 módulos**, 13 imports por nome, mais 1 teste | `leitor` 3 (`info`, `quadro_em`, `quadros`), `cache` 2 (`ModoCache`, `caminho_do_quadro`, `ler_quadro`, `pasta_do_video`), **`musicxml.midi_da_corda` 4** + `test_partitura_video` (o áudio contou 3), `video._slug` 4 |
| outra trilha → partitura | — | **0** | nenhum módulo nem teste fora da partitura importa `tab.partitura_*` |
| imports relativos | — | **42 linhas em 13 arquivos** | viram absolutos na fase 3 |
| `data/saida/partitura` | ~570 MB | **570 MB** | `sem_produto` 224, `p1` 165, `diag` 125 (165 entradas), `video` 29, `p0*` 27 |
| `data/saida/part_frentes` | ~304 MB | **304 MB**, 2 arquivos no git (`fd_gabarito/amostra.json` e `amostra_final.json`) | `fd_gabarito` 182, `fa_imagem` 88, `fp_produto` 31, `fe_completar` 2, `f0_regua` 1; `fb_fusao` e `fc_polifonico` vazias |
| `data/gold/partitura` | — | 1,5 MB, **3 no git** (`leitura_p1`, `leitura_sem_produto`, `leitura_d1`) + 2 fora (`compassos_homr`, `figura_e1`) | já está em `data/gold/partitura/`: **a fase 4 não move o ouro da partitura** |
| pesos em `artefatos/` | — | **nenhum** (`artefatos/part_frentes/*` vazias) | os pesos do SMT moram dentro da imagem `chorinho-partitura:smt` (`/opt/smt-modelos`) |
| scripts em `data/saida` | — | **84 `.py` e 4 `.sh`, 420 KB, fora do git** | 68 chamam `tab` pelo nome antigo; 7 fazem `sys.path.insert`; 25 linhas com `/app/...` absoluto |

**Rótulo do dono fora do git ou fora do `data/gold`** (regra 9):

1. **Os itens que o ouro cita estão fora do git (regra 10).** Cada ouro da partitura guarda
   `fonte_itens`, e os itens citam o PNG do recorte. As posições `faltando` (x, y) que o dono
   clicou só têm sentido sobre esse PNG. São **5 `itens.json` + 84 PNG/MusicXML, 17,9 MB**, nenhum
   no git:
   - `p1/conferencia/itens.json` (de `leitura_p1`), 21 PNG;
   - `diag/conferencia_sem_produto/itens.json` (de `leitura_sem_produto`), 3;
   - `part_frentes/fd_gabarito/itens_d1.json` (de `leitura_d1`), 35;
   - `diag/troca_homr/itens.json` (de `compassos_homr`), 17;
   - `part_frentes/fe_completar/itens_e1.json` (de `figura_e1`), 17.

   **Fase 1a**: versiono os 89 arquivos onde estão (`git add -f` por nome, conteúdo intacto).
   Eles ficam no lugar.
2. **`compassos_homr.json` e `figura_e1.json`** (AGENTS §9: nunca commitar).
   - O `compassos_homr` é do dono.
   - O `figura_e1` grava "certo" em 37 notas que o dono julgou erradas (rodada 3172). A
     observação dele por trecho é rótulo, mas a marca por nota não vale.
   - **Na reestruturação**: ficam no lugar (`data/gold/partitura/` não muda) e fora do git. Hoje
     aparecem como `??` no `git status`, e um `git add` largo os levaria. **Proposta**:
     - uma linha para cada um na `.gitignore`;
     - **uma cópia de segurança** num `.tar` em `chorinho_arquivo/`, sem mover o original. Hoje
       a única outra cópia do `compassos_homr` é `diag/troca_homr/teste_remarcar.json` (o `cmp`
       diz que é igual), que sobrou de um teste da ferramenta.
     - Isso esbarra na regra 9 ("nunca vai para o arquivo frio"). Peço a exceção ao dono, porque
       uma cópia não é mover. Depois do `.tar` conferido, o `teste_remarcar.json` pode sair.
3. **Correção dada no chat**: a marcação do dono de quais canais têm pauta (2026-10-17: só
   tablatura, misto, misto por vídeo) existe só na memória da sessão. A rodada 3160 guarda só os
   vídeos trocados. **Fase 1a**: transcrevo em `data/saida/partitura/pauta_por_canal_dono.json`,
   marcado "transcrito do chat, a confirmar", e versiono. Depois que o dono confirmar, vai para
   `data/gold/partitura/` na fase 4.
4. **Não é rótulo** (conferido):
   - `ouro_d1_copia.json` e `ouro_e1_copia.json` (part_frentes) são as cópias de teste da
     ferramenta, vazias (`"recortes": {}`);
   - `diag/ca1/ouro_antigo/gymnopedie….json` é o ouro de tablatura antes do `741f66da`, igual
     byte a byte à versão do histórico do git.

**Disco da partitura** (874 MB; lista item a item para o dono na fase 1b):

| classe | o quê | MB | por quê |
| --- | --- | ---: | --- |
| **manter** | `sem_produto`, `p1/omr`, `p1/recortes`, `p1/recortes_margem`, `p1/conferencia`, `p1/variantes`, `video`, `p0`, `p3`, `diag/ca1`, `diag/troca_homr`, `diag/conferencia_sem_produto`, `fd_gabarito` (sem a `_INVALIDA`), `fe_completar`, `f0_regua` e os scripts e `.json` de `diag/qualidade_imagem` e `fp_produto` | ~567 | lidos pelo código (`p0/resumo.json`, `p0/amostra.jsonl`, `p1/*`, `video/`), citados pelos ouros, pelo CA1 ou pelas rodadas 3001–3027 e 3101–3172 |
| **arquivar** (`.tar`) | `p1/fumaca` 35, `fa_imagem` 88 (A1 reprovada, 3110), `p0_rodada3`/`p0_rodada4`/`p0_teste`/`p0_olhar` 20, `p1/recortes_teste` 7, `fd_gabarito/videos_v1_INVALIDA` 5 (sorteio refeito), ~160 entradas de `diag/` ~50 | ~205 | histórico citado; regenerável só relendo o HD |
| **apagar** | `diag/qualidade_imagem/{reduzido,mediana,leituras,leituras_mediana}` 72 (PNG e leituras refeitas em minutos pelos scripts, que ficam), `fp_produto/video` 29 (cópia das 3 pastas de `partitura/video`, iguais pelo comparador da 3027), `msg*.txt`, as 2 cópias vazias do ouro, `fb_fusao` e `fc_polifonico` (vazias) | ~102 | regenerável ou duplicado |

- **Fora dos 27 GB**: a imagem `chorinho-partitura:smt` tem **9,87 GB** no podman, e o SMT não é
  usado desde a 3003 ("não treinar agora"). A receita está no `Dockerfile.partitura`, mas
  refazer a imagem baixa os pesos do Hugging Face. Proponho ao dono **remover a imagem** (`podman
  rmi`). É a maior economia da partitura.

**Respostas às 5 perguntas:**

1. **Candidatos ao `comum`**: a partitura não exporta nada (0 imports de fora). Do que importo da
   tablatura, o `comum/` proposto serve, com 3 condições:
   - **`leitor` e `cache`**: servem como estão, com os mesmos nomes públicos.
   - **`video._slug`**: vira público no `comum`, mas **o nome privado continua em
     `tab.video`** (reexportado), porque 4 módulos meus e 6 scripts de `data/saida` o importam
     por esse nome. O apelido de módulo não cobre um nome que saiu do módulo.
   - **`musicxml.midi_da_corda` → `comum/violao.py`**: tem de dar a **mesma altura** de hoje
     (afinação padrão, sem capo, `None` para corda fora da afinação). Se a função nova somar o
     capo por padrão, toda a partitura muda sem erro. **Alternativa**: a função de hoje fica com
     a mesma assinatura, e o capo entra numa função separada. Um teste compara as 6 × 25
     combinações com a versão antiga.
   - O `SEMITONS_ESCRITA` (+12, a escrita do violão uma oitava acima do som) é da partitura e
     fica nela.
   - Achado lateral, fora desta reestruturação: a partitura ignora o capo (decisão 1010). Num
     vídeo com capo, o pareamento compara a pauta com a tab deslocada. Vira rodada própria.
   - **JSON atômico**: o `partitura_gabarito` grava o ouro a cada clique. Ele só troca para o
     `comum/arquivos.py` testado numa cópia do ouro, nunca no vivo.
2. **Janela**: **nada da partitura está rodando** (nenhum container `part-*` no `podman ps`, sem
   treino, fila nem ferramenta). Os 4 ramos de frente (`part/a1-imagem`, `d1-amostra`,
   `e1-itens`, `p4-produto`) estão todos juntados na `main`, e as worktrees estão `prunable`.
   - **A janela da partitura é a partir de agora, sem data de fim.** Fico sem rodar nada até a
     minha fase 3 fechar.
   - A fase 3 leva ~2 h:
     - mover;
     - 42 imports relativos viram absolutos;
     - registrar 21 apelidos;
     - provar.
   - **Prova byte a byte**, antes e depois:
     - `python -m tab.partitura_video parear` (nome antigo) dos 3 produtos numa pasta
       temporária, conferido com `cmp` contra os `.partitura.json` de hoje;
     - a saída do `data/saida/partitura/diag/ca1/ca1.py` igual linha a linha;
     - o `pytest -rs` com o mesmo número de pulados.
   - A ferramenta `partitura_gabarito servir` sobe numa cópia do ouro e serve um PNG de cada
     uma das 3 pastas da lista de permissão.
   - Antes da fase 3, peço para remover as 4 worktrees (`git worktree prune`). Os ramos ficam.
3. **Caminhos fixos e scripts que quebram:**
   - **Em `tab/`**:
     - 31 constantes montam o caminho à mão a partir de `caminhos.SAIDA` (`SAIDA / "partitura" /
       "p1" / ...`) em 14 módulos;
     - 3 apontam para dado da tablatura: `SAIDA / "fase8" / "rede"` (`completar`,
       `regua_tempo`) e `SAIDA / "censo" / "v2" / ...` (`censo`);
     - `partitura_smt` tem `/opt/smt*` (dentro da imagem; fica);
     - `partitura_omr` tem `/opt/omr/bin/homr` e `/opt/audiveris/bin/Audiveris` (fica).
     - **Na fase 1b** as 31 constantes passam a ler constantes novas do `caminhos.py`
       (`PARTITURA_P1`, `PARTITURA_VIDEO`…). Peço à tablatura `FASE8_REDE` e `CENSO_V2`.
   - **A pasta da partitura não muda de lugar**: o alvo do §3 (`data/saida/partitura/`) é onde
     ela já está. Na fase 4 só o `part_frentes/` vai para `data/saida/partitura/frentes/`, pelos
     `PART_FRENTE_*` do `caminhos.py`, com link no lugar antigo.
   - **Scripts**:
     - 68 dos 84 chamam `tab` pelo nome antigo, nas 3 formas: `from tab.partitura_x import`,
       `from tab import partitura_pauta as pp` e `python -m tab.partitura_video` (4 `.sh`).
     - Eles importam funções privadas: `_carregar_ouro` 9, `_cinza` 9, `_e_nota` 8,
       `_tinta_escura` 6, `_slug` 6… O apelido devolve o mesmo módulo, então elas seguem
       valendo, desde que nenhuma saia do módulo (ver `_slug` acima).
     - **Os 25 caminhos `/app/data/saida/part_frentes/...`** quebram se o `part_frentes` mudar
       sem link. O link da fase 4 os cobre.
   - **Dentro dos dados**: os ouros citam `fonte_itens` por caminho relativo, e os itens citam
     o PNG. Isso exige o arquivo no lugar ou o link (regra 10).
   - A ferramenta confere o PNG com `resolve()` contra a lista de permissão
     (`PASTA_RECORTES`, `PASTA_SEM_PRODUTO` e `PART_FRENTE_D`, todas com `resolve()`). Com
     link e constante apontando para o mesmo lugar, ela segue servindo. **Testar numa cópia
     depois da fase 4.**
   - **`Dockerfile.partitura` → `docker/`**:
     - **não quebra**: não tem `COPY` nem `ADD`, e nem `compose*.yaml` nem o `Makefile` o
       citam;
     - muda o comando de build escrito no próprio arquivo, na decisão 3001 e no
       `contexto-partitura.md`: `podman build -f docker/Dockerfile.partitura .`;
     - o estágio do SMT está no mesmo arquivo.
4. **Pesos em uso**: **nenhum** em `artefatos/`. O Audiveris, o homr e o oemer baixam os modelos
   no build da imagem (sha256 na decisão 3001). O `EM_USO.json` da partitura fica vazio, com essa
   nota.
   - **Os 2 testes pulados do gate hoje são da partitura**: `test_partitura_smt.py:101` e `:114`
     (`importorskip("music21")`, que só existe na imagem `:smt`). O gate de 2026-10-21 deu 1859
     passados e 2 pulados. Esse é o número de referência da regra 12. Remover a imagem `:smt`
     não muda essa conta.
5. **Objeções, cada uma com a alternativa:**
   - **a. Uma imagem em Python 3.11 importa `tab`, e o teste do §4 não pega isso.**
     - O que acontece: `partitura_smt` roda cada recorte com `/opt/smt/bin/python -m
       tab.partitura_smt inferir` (Python **3.11.17**, imagem `:smt`). Esse import executa o
       `tab/__init__.py` e importa o `tab.caminhos` no topo do módulo.
     - Por que o teste não pega: ele cobre `tab/__init__.py`, `_apelidos.py` e os
       `tab/*/__init__.py`, mas **não o `comum/caminhos.py`**.
     - O risco é real: `tab/leitor.py` já usa `except ValueError, TypeError:` sem parênteses,
       sintaxe que só existe no 3.14. O mesmo vale para `audio_extrair`, `video` e
       `partitura_video`.
     - **Alternativa**:
       - o teste do `feature_version=(3, 10)` inclui `tab/comum/caminhos.py`;
       - `tab/comum/__init__.py` fica **vazio**, sem reexportar o `leitor` nem o `cache`.
     - É o mesmo caso do transcritor do áudio (3.10) e do `celular` (host).
   - **b. Subprocesso pelo nome do módulo.** O `partitura_smt` monta o comando com o literal
     `"tab.partitura_smt"`. O apelido faz o nome antigo funcionar, e na fase 3 eu troco para o
     nome novo (`tab.partitura.smt`). O `partitura_omr` chama o Audiveris e o homr como
     executáveis (Java e o venv `/opt/omr`, Python 3.12). Eles não importam `tab` e não mudam.
   - **c. Sem subpastas dentro da partitura.**
     - São 21 módulos, e nenhum grupo passa de ~10 (regra do §3): leitura 8, pareamento e
       régua 6, gabarito e amostra 7.
     - **Proposta**: `tab/partitura/` plano, com o nome sem o prefixo (`video`, `gabarito`,
       `omr`, `pauta`, `recortes`, `smt`, `censo`, `avaliar`, `pareamento`, `completar`,
       `completar_pauta`, `completar_itens`, `regua`, `regua_tempo`, `regua_troca`, `amostra`,
       `amostra_itens`, `amostra_ler`, `amostra_paginar`, `imagem`, `imagem_mediana`).
     - Os testes vão para `tests/partitura/` **com o nome de hoje** (`test_partitura_*.py`),
       para o `-k partitura` e as rodadas que citam o arquivo continuarem valendo.
   - **d. O resto dos apelidos, medido, não quebra a partitura:**
     - não há `multiprocessing`, worker nem `ProcessPool`;
     - não há pickle: o `.omr` é zip com XML, e o resto é MusicXML e JSON;
     - nenhum JSON gravado guarda nome de módulo (`gerado_por` é texto livre, e `produto` é
       caminho de dado);
     - não há `conftest.py` nem teste que importe outro teste.
     - **Muda com a fase 4** o campo `produto` do `.partitura.json` (caminho do JSON da tab):
       se a tablatura mover o `fase8/rede`, o mesmo comando grava outro texto ali. Registro
       isso na rodada que regerar.
   - **e. A ordem da fase 3 serve**: áudio e depois partitura. A partitura não depende das fases
     de outra trilha, só do `comum` da fase 2.

**Fase 1 da partitura (2026-10-21), commit `eae7c3a5`:**
- **Versionado** (`git add -f`, conteúdo intacto): 184 arquivos, 18,2 MB.
  - Os 5 `itens.json` que os ouros citam e os 84 PNG/MusicXML que eles citam (regra 10).
  - Os 88 scripts `.py`/`.sh` de `data/saida/partitura` e `part_frentes` (regra 11).
  - A saída de referência do CA1 (`diag/ca1/ca1.txt`).
  - A marcação dos canais com pauta, transcrita do chat
    (`data/saida/partitura/pauta_por_canal_dono.json`, "a confirmar").
  - Os 4 `LEIAME.json`.
- **Caminhos**: o `caminhos.py` ganha `PARTITURA`, `PARTITURA_P0/P1/P3/VIDEO/SEM_PRODUTO/DIAG`,
  `GOLD_PARTITURA`, `PART_FRENTE_P`, `FASE8_REDE` e `CENSO_V2`. Os 14 módulos
  `tab/partitura_*` não montam mais caminho à mão. Os valores são os mesmos: a prova abaixo
  regera os 3 documentos iguais aos de antes da mudança.
- **`.gitignore`**: `compassos_homr.json` e `figura_e1.json`. A cópia `.tar` está em
  `chorinho_arquivo/partitura/gabarito_fora_do_git/`, conferida por `sha256sum -c` (§7c, item 2).
- A imagem `chorinho-partitura:smt` já não existia no `podman` quando fui apagá-la (§7c, item 1).
- **Inventário (`LEIAME.json`, item a item)** em `data/saida/partitura/`, `partitura/p1/`,
  `partitura/diag/` (165 itens) e `part_frentes/`. Cada item tem classe, motivo, se é
  regenerável, o comando, os MB e as rodadas que o citam. O gerador é
  `diag/r9001/leiame.py`.
- **`EM_USO.json`**: a partitura não tem peso em `artefatos/` (lista vazia). Os modelos do
  Audiveris e do homr vêm dentro da imagem `chorinho-partitura:dev`.

**Prova de "antes"** (registrada no commit desta linha). Ela roda tudo pelo nome antigo:

```bash
bash data/saida/partitura/diag/r9001/prova_9001.sh antes    # já feito; depois da mudança: depois
diff -r data/saida/partitura/diag/r9001/prova/antes data/saida/partitura/diag/r9001/prova/depois
```

- **O que o script faz:**
  - `python -m tab.partitura_video parear` dos 3 produtos numa cópia de
    `data/saida/partitura/video`. Depois confere com `cmp` que os 3 `.partitura.json` saem
    iguais, byte a byte, aos de `data/saida/partitura/video/`, e grava o `sha256_partitura.txt`;
  - `python data/saida/partitura/diag/ca1/ca1.py` (o CA1 contra os gabaritos do dono) →
    `ca1.txt`;
  - `python -m tab.partitura_gabarito servir` numa **cópia** de cada um dos 3 ouros. O script
    baixa um PNG de cada pasta da lista de permissão (`ferramenta.txt`: 3 × HTTP 200) e confere
    com `cmp` que a cópia do ouro não mudou.
- **Referência**: `data/saida/partitura/diag/r9001/prova/antes/` (no git).
- **`pytest -rs` de hoje, na cópia de trabalho**: **1859 passed, 2 skipped, 5 deselected,
  2 xfailed**. Os 2 pulados são `test_partitura_smt.py:101` e `:114` (music21). Só a partitura:
  230 passed, 2 skipped (`prova/antes/pytest_rs.txt`).
- **Parada**: nenhum container, servidor, túnel ou fila da partitura rodando (`podman ps`,
  20h22). Não faço commit nem lote no HD até o aviso da sessão das mãos.

PRONTA E PARADA — 2026-10-21 20:25 — commit eae7c3a5

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

**Fase 1 das mãos (2026-10-21, a sessão da 1041):**
- **1a, versionar o que só existia no disco**: feita, mas entrou no commit `6c6f9695` (ver o
  §6b):
  - os 14 gabaritos "antes" e a remarcação cega;
  - a conferência dos 30;
  - 78 scripts;
  - as 44 procedências.
  - **As imagens que o gabarito das mãos usa** são os `quadros/` de cada pasta de ciclo,
    achados pelo `indice.json` e pelas constantes `MAOS_M*`. O gabarito não guarda caminho de
    imagem. Por isso **toda pasta de ciclo fica em "manter"**.
- **Caminhos fixos**: os 6 que restavam (`maos_braco_capo`, `maos_braco_detector` ×2,
  `maos_conferencia` ×2 e `maos_censo`) passam a ler `CAPO_POR_VIDEO`,
  `CONFERENCIA_MAOS_30`, `CENSO_MAOS`, `CENSO_PRESENCA`, `PESOS_MAOS` e `PESOS_RESNET18`, do
  `caminhos.py`. O `CAPO_POR_VIDEO` serve também ao áudio, que o pediu no §8.
- **Inventário de `data/saida/maos`** (13 GB, 71 entradas):

| classe | o quê | tamanho | por quê |
| --- | --- | --- | --- |
| **manter** | `m21` (`S` 6,9 GB de sintéticos, `R` 323 MB, `fundos`, `G`) | 7,5 GB | é a entrada do treino dos dois estágios. O `S` se regenera pela semente, mas leva horas, e recomprimir muda a entrada (regra 8) |
| manter | as pastas de ciclo e de gabarito: `m1`, `m2`, `m3`, `m3b`, `m3c`, `m3d`, `m5`, `m7`, `m8`, `m9`, `m11`, `m11b`, `m25`–`m27`, `m29`, `m30`, `m32`, `m36`, `m37`, `m39`–`m41` | ~1,2 GB | os quadros que o dono marcou, os índices, as previsões e as medidas citadas pelas rodadas |
| manter | `m38` | 0,9 GB | os 688 quadros da 1038, que espera um par aprovado |
| manter | `frentes`, `capo_por_video.json`, `capo_auditoria`, `censo_maos.jsonl`, `conferencia_30*`, `imagem`, `m16` | ~0,2 GB | citados por rodadas ou lidos pelo código |
| **arquivar** (`.tar` no frio) | `m31/denso` | 2,4 GB | os quadros densos a 2 fps da 1030/1031, que reprovaram. Dá para regenerar relendo o acervo. **Pode ser apagado**, se o dono preferir |
| arquivar | `m7c` | 154 MB | não é citado por nenhuma rodada nem pelo código |
| arquivar | os pilotos soltos (`piloto_*.jsonl`, `folha_piloto*`, `folha_teste_det*`, `mudou_c03*`, `teste_conferencia*`, `teste_det`, `olhar`, `m19`, `m20`, `*.log`) | ~20 MB | histórico de 10/10 a 14/10; a maioria não é citada |
| apagar | nada | — | — |

- **Pesos** (`artefatos/m21`, 45 `.pt`, 2,7 GB). O `EM_USO`:
  - **o ciclo**: `L3_todos_s3` e `A4_100_todos_s1`;
  - **em prova** na 1039: `L5_capo3_s*` e `A7_capo3_s*`;
  - o `resnet18` em `artefatos/torch`.
  - **Histórico**, para arquivar **depois** da medida da 1041 na 1039: L1, L2, L4_capo, A1,
    A3_\*, A5, A6_capo e `v2_sobreajuste`. São ~2,2 GB.

**Prova de "antes" das mãos** (2026-10-21, 20h):
- **Comando**, pelos nomes de hoje, nas 3 formas de import, na CPU e sem GPU:
  `CHORINHO_MAOS_CPU=1 python data/saida/maos/prova_9001/prova.py <saida.json>`, no container
  `localhost/chorinho-maos:dev` com `--shm-size=2g`.
  - Ele prevê 6 quadros da M36 com o par do ciclo (`L3_todos_s3` + `A4_100_todos_s1`), o
    que carrega os pesos de `artefatos/m21`.
  - Ele refaz a casa do capo por vídeo (`maos_braco_capo`).
- **Referência**: `data/saida/maos/prova_9001/antes.json` (22.688 bytes, sha256
  `2a77d8f6…a603a`).
  - Rodado duas vezes, deu o mesmo arquivo, byte a byte, então a prova é determinística.
  - Depois da mudança, `depois.json` tem de ser igual a ele.
- **O `pytest -rs` de hoje**: no commit desta fase, ver a linha abaixo.

**Prova de "antes" das mãos** (2026-10-21, 20h):
- **Comando**, pelos nomes de hoje, nas 3 formas de import, na CPU e sem GPU:
  `CHORINHO_MAOS_CPU=1 python data/saida/maos/prova_9001/prova.py <saida.json>`, no container
  `localhost/chorinho-maos:dev` com `--shm-size=2g`.
  - Ele prevê 6 quadros da M36 com o par do ciclo (`L3_todos_s3` + `A4_100_todos_s1`), o
    que carrega os pesos de `artefatos/m21`.
  - Ele refaz a casa do capo por vídeo (`maos_braco_capo`).
- **Referência**: `data/saida/maos/prova_9001/antes.json` (22.688 bytes, sha256
  `2a77d8f6…a603a`).
  - Rodado duas vezes, deu o mesmo arquivo, byte a byte.
  - Depois da mudança, `depois.json` tem de ser igual a ele.

**PRONTA E PARADA — 2026-10-21 20:28 — commit 6be39b08** (mãos, sessão da 1041: nenhuma fila, ferramenta ou container rodando; a 1039 espera a revisão do dono).

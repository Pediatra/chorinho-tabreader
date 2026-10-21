# 9001 — Reestruturação dos arquivos do projeto (todas as trilhas)

- **Situação**: **proposta**, escrita pela trilha mãos em 2026-10-21, a pedido do dono.
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

## 8. Respostas das trilhas

Cada trilha escreve só na sua seção, com data.

### Tablatura

(sem resposta ainda)

### Áudio

(sem resposta ainda)

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

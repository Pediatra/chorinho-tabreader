# AGENTS.md — chorinho

> Contrato de trabalho deste projeto. Leia **inteiro** antes de rodar qualquer coisa.
>
> **Este arquivo substitui a versão anterior**, que era um template herdado de outro
> projeto e descrevia arquivos que não existiam (`Dockerfile`, `compose.yaml`,
> `Makefile`, `pyproject.toml`, `tests/`, pacote `chorinho`). Agora eles existem.

## O que é o projeto

Transcrever, de forma estruturada, a **tablatura de violão que aparece na tela** de
milhares de vídeos-aula, associando cada nota ao **instante do vídeo** em que ela é
executada. O produto é um **JSON por vídeo**: corda, casa, coluna, compasso, técnica
e tempo.

Arquitetura decidida por medição: **geometria determinística + classificador de glifos
de ~74 mil parâmetros, treinado só em dado sintético**. Não é VLM — a alternativa foi
testada e perdeu (GOT-OCR2.0, 580 M, acertou **0 de 15** algarismos numa linha com
gabarito verificado à mão).

**Número oficial: 0,889** (média de 3 sementes: 0,865 / 0,917 / 0,885) em 96 glifos /
4 canais / casas 0–7, **reprodutível** — cada semente dá o mesmo total em execuções
repetidas. Ver [`ESTADO.md`](ESTADO.md), [`docs/HISTORICO.md`](docs/HISTORICO.md) e
[`docs/decisoes/0001-determinismo-do-treino.md`](docs/decisoes/0001-determinismo-do-treino.md).

## Ambiente

**Tudo roda dentro do container.** O host tem um `.venv` (5,8 GB) apenas para o editor
ler o código — ele **não** executa o pipeline.

```bash
cd /var/home/gabriel/Projects/chorinho-dataset
make build            # constrói a imagem
make verify-install   # confere torch+CUDA+ffmpeg DENTRO do container
docker compose run --rm chorinho python -m tab.avaliar
```

- Imagem `chorinho:dev`, base `python:3.14-slim`, venv em `/opt/venv` (fora de `/app`,
  para o bind-mount do código não esconder os pacotes);
- **GPU por CDI**: o daemon deste host **não** tem o runtime `nvidia` registrado, e
  registrar exigiria `sudo`. `gpus: all` no `compose.yaml` funciona assim mesmo —
  verificado: `torch.cuda.is_available() == True` na RTX 3060 Ti;
- **acervo** montado em `/acervo`, **somente leitura**: **3.908 vídeos / 183 GB / 17
  canais** em `/run/media/gabriel/3014CD4714CD1130/chorinho`, e **ainda crescendo** (o
  dono do projeto segue baixando). Nunca escreva lá; para varrer, use `tab.varredura`,
  que lê por instante e é retomável;
- **`ffmpeg` e `fonts-liberation` são dependências de trabalho, não enfeite**:
  `ffmpeg` porque **44% do acervo é AV1** e o OpenCV não decodifica (sem ele quase
  metade do acervo passa em branco); as fontes porque são o **dado** do gerador
  sintético — trocar de fonte muda a métrica.

**Armadilha do bind-mount:** `/tmp` dentro do container **não** aparece no host.
Artefato que precisa ser visto/inspecionado vai para `data/saida/` ou `artefatos/`.
Modelo treinado em `/tmp` é modelo perdido (já aconteceu).

**O que o container escreve sai como `root`:** o serviço não roda com o seu uid, então
`data/saida/` e `artefatos/` ficam com dono root e o seu usuário não apaga direto. Use
`docker compose run --rm chorinho rm -rf <caminho>`. (Rodar com `user:` no compose é uma
decisão em aberto; ver `PERGUNTAS.md`.)

## Árvore

```
chorinho-dataset/
├── AGENTS.md  README.md  ESTADO.md  PERGUNTAS.md
├── Dockerfile  compose.yaml  requirements.txt  Makefile  pyproject.toml
├── tab/            # o motor, flat: caminhos tabseg cursor sintetico reconhecer
│                   # transcrever avaliar inventario ouro glyphset glyph_bench
├── tests/          # gate: unitários, sem GPU e sem acervo
├── configs/        # canais.yaml, simbolos.yaml (mapa de símbolo POR CANAL)
├── data/gold/      # gabarito rotulado à mão
├── data/saida/     # artefatos gerados (visíveis no host)
├── artefatos/      # pesos .pt — NUNCA em /tmp
├── parts/clipes/   # 18 recortes de amostra
└── docs/{HISTORICO.md, rodadas/, decisoes/, guias/}
```

Regras de arrumação:

1. **Nada de `.md` solto na raiz** além dos quatro do topo.
2. **Um documento por rodada** em `docs/rodadas/`, nome `NNNN-titulo-curto.md`. Nunca
   apague documento de rodada — é o registro das medições.
3. **Uma decisão por arquivo** em `docs/decisoes/`: contexto, opções, decisão, consequência.
4. **Sem `src/` e sem pacote dentro de pacote.** Um pacote só, na raiz, nome curto.
5. **Modelo treinado vai para `artefatos/`**, com o comando e a semente registrados.
6. **Caminho não se espalha**: acervo, gabarito, saída e artefatos vêm de
   `tab/caminhos.py`. Caminho absoluto novo no meio de um módulo é bug de revisão.

## Regras de trabalho (custaram rodadas — não repita)

1. **Semente fixa + determinismo + ≥3 execuções; reporte média e amplitude.** Semente
   sozinha não significa nada: com o cuDNN padrão a **mesma** semente deu 0,927, 0,896 e
   0,948 (amplitude 0,052) — e o projeto tratou diferenças desse tamanho como ganho. O
   determinismo está em `tab.sintetico.fixar_semente` e é travado por teste.
2. **Meça a amostra antes de gastar treino.** Três retreinos foram queimados
   descobrindo que a classe não nascia.
3. **Confira o significado do número.** "323 notas com tempo" eram **3 instantes**;
   "41 notas com duração" eram **8 ataques sem duração**. Conte instantes distintos — e
   confira o **modo do modelo**: com o `Dropout` ativo, os mesmos pesos deram 0,812 onde
   em `eval()` davam 0,865.
4. **Olhe o quadro antes de teorizar.** Duas vezes medi o violão achando que era a
   tablatura — o braço tem 6 cordas e engana o detector.
5. **Rótulo de gabarito só por leitura visual.** Relabelar por proxy geométrico
   (`partes>=2`) piorou duas vezes e foi revertido.
6. **O gargalo histórico é cobertura do gerador, não regra de visão** — medido 6 vezes:
   3 regras geométricas deram 0, uma deu −0,166; as duas mudanças de dado deram +0,05.
7. **Depois de editar gerador ou treino, valide `ast.parse` + `import`** antes de rodar,
   e depois **rode de verdade**. Sintaxe válida não é import válido: na reestruturação um
   import de pacote ficou errado e passou pelo `ast.parse`.
8. **Antes de remover um `int()`/`round()`, meça o tipo real.** RUF046 sugeria remover
   `int(round(...))`; só é seguro porque medi que `round()` de escalar numpy devolve
   `int` neste numpy. Índice de matriz e JSON dependem disso.
9. **O recorte é parte da medição.** Troquei a margem do recorte do classificador (de 1 px só
   em cima/à esquerda para simétrica) e os **mesmos pesos** passaram a dar 0,844 onde davam
   0,865. Pré-processamento não é detalhe de implementação: é **entrada do modelo**, e mexer
   nele invalida comparação com o histórico.
11. **Registre o que falhou** "tem tablatura?"** A tablatura aparece e desaparece, e no
   `sky guitar` ela só aparece da **metade para o fim** do vídeo: dos 20 vídeos que um scan de
   1 instante (em 0,35 da duração) chamou de "sem tablatura", **20 de 20 têm** em algum
   instante. Presença se mede **ao longo do tempo**, e a janela amostrada importa
   (`tab.varredura --frac-inicio/--frac-fim`).
10. **Um instante não responde na tabela "não repetir" do `ESTADO.md`, para não gastar de novo.

## Decisão de dado: símbolo NÃO se descarta

O extrator lia o número e **jogava fora** o símbolo em volta: um `7` com barra de slide
virava `{"casa": "7"}` e o slide desaparecia. Direção definida pelo dono do projeto:
**guardar o glifo cru, sempre, e classificar/significar depois** — cada canal tem seu
próprio vocabulário (`h`, `p`, `/`, `\`, `<7>`, `(6)`, trêmolo), e o significado é
mapeado **por canal** em `configs/simbolos.yaml`. Perder informação é o único erro
inaceitável aqui; símbolo ainda não classificado é dívida, não erro.

## Regras de código

- Python 3.14, **sem import dentro de função** (a regra existe em `pyproject.toml` via
  `PLC0415` — não é opcional);
- aspas duplas, **88 colunas**, imports no topo em 3 blocos (stdlib / terceiros /
  locais) ordenados;
- type hints nas assinaturas; **docstring estilo Google** em toda função, método e
  classe pública;
- **nomes em português** (`binarizar`, `achar_cordas`, `passo`, `glifo`);
- módulo de CLI: `main()` + `if __name__ == "__main__"`, invocado como `python -m tab.x`.
  Nada de código solto no nível do módulo (foi assim que `avaliar.py` virou script).

## Gate (antes de todo commit — sempre)

```bash
make lint     # ruff check . + ruff format --check .
make test     # pytest tests/ -q
```

- Só commite com **`All checks passed!`** e os testes passando.
- Testes que exigem acervo levam a marca `integration` e ficam fora do gate padrão
  (`make test-integration`).
- **Um commit por tarefa**, com a descrição do que foi feito e com o número medido
  quando houver medição.
- Se você não conseguiu rodar o gate, **diga isso explicitamente** — não finja que rodou.

## Vocabulário

| termo | significado exato |
| --- | --- |
| **grade** | resultado da segmentação: linhas de corda, barlines, passo, glifos |
| **passo** | distância vertical entre duas cordas, em px (14–45 no acervo) |
| **glifo** | componente conectado de tinta, antes de agrupar |
| **token** | glifo(s) da mesma corda já agrupados = uma nota (ou um símbolo) |
| **painel** | a região da tela com a tablatura (varia por vídeo: topo/meio/base) |
| **marcador** | o que indica a nota tocada: **faixa vertical** que passa, ou **cor** no algarismo |
| **casa** | o número na corda (a pestana pisada) |
| **ligada** | nota presa/ligada, desenhada como `(6)` ou arco |
| **harmônico** | `<7>` ou losango |
| **acervo** | os 3.908 vídeos (crescendo), 183 GB, 17 canais, montados em `/acervo` |
| **rollout** | rodar o pipeline em muitos vídeos, com decisão por vídeo |

## Limites conhecidos (não prometa além disto)

96 glifos, 4 canais, **casas 0–7**; aferição **glifo a glifo**, não da música inteira.
A **casa** dos canais fora do gabarito (ex.: `cifra club` — tem corda e tempo, casa não)
**não está validada**. A métrica **não cobre** técnica nem símbolo. **Tab ASCII**
(Ultimate Guitar) e **partitura de 5 linhas** exigem leitor próprio e estão **fora**
desta cadeia. Perguntas abertas para o dono: [`PERGUNTAS.md`](PERGUNTAS.md).

# AGENTS.md — chorinho

> Contrato de trabalho deste projeto. Leia **inteiro** antes de rodar qualquer coisa.
>
> **Este arquivo substitui a versão anterior**, que era um template herdado de outro
> projeto e descrevia arquivos que **não existem aqui** (`Dockerfile`, `compose.yaml`,
> `Makefile`, `pyproject.toml`, `tests/`, pacote `chorinho`). Ver "Ambiente" abaixo.

## O que é o projeto

Transcrever, de forma estruturada, a **tablatura de violão que aparece na tela** de
centenas de vídeos-aula, associando cada nota ao **instante do vídeo** em que ela é
executada. O produto é um **JSON por vídeo** com: corda, casa, coluna/compasso,
técnica e tempo.

Decisão de arquitetura já tomada e medida: **geometria determinística + classificador
pequeno de glifos (~74 mil parâmetros), treinado só em dado sintético**. Não é VLM —
a alternativa foi medida e perdeu (GOT-OCR2.0, 580 M, acertou **0 de 15** algarismos
numa linha com gabarito verificado à mão).

### Número oficial

| métrica | valor |
| --- | --- |
| acerto no gabarito real | **0,892** (média de 3 sementes: 0,844 / 0,906 / 0,927) |
| base | 96 glifos rotulados à mão, 4 canais, **casas 0–7** |
| acerto nos rótulos alcançáveis | 0,955 (excluindo os 7 `junk` do `raman`) |

Detalhe completo em [`ESTADO.md`](ESTADO.md). **Sempre reporte a média de ≥3 sementes**,
nunca uma execução única.

## Ambiente

A realidade medida desta máquina, hoje:

- Python **3.14.7** em `.venv/` **no host** (5,8 GB);
- `torch 2.14.1+cu130` com **CUDA ativa** na RTX 3060 Ti (8 GB), `opencv 5.0.0`;
- **acervo** em `/run/media/gabriel/3014CD4714CD1130/chorinho` (HD externo, 190 GB) —
  **somente leitura**, nunca escreva nada lá;
- 92 GB livres em `/var/home`.

Comando padrão (é assim que todo o trabalho foi feito até aqui):

```bash
cd /var/home/gabriel/Projects/chorinho-dataset
.venv/bin/python tools/<script>.py ...
```

**Pendência declarada:** o dono do projeto ainda vai decidir se a execução continua no
`.venv` do host ou se migra para um Compose com GPU. Até essa resposta (pergunta
**A1** em [`PERGUNTAS.md`](PERGUNTAS.md)), **use o `.venv` do host** — é o único
caminho que hoje tem CUDA funcionando.

Ferramentas ainda **ausentes** e que são tarefa: `ruff`, `pytest`, `pyproject.toml`,
`Makefile`. Enquanto não existirem, as regras de lint/teste abaixo são intenção, não
gate executável — **diga isso explicitamente** ao reportar, em vez de fingir que rodou.

## Árvore de arquivos

Estado em 65 rodadas (o que existe hoje):

```
chorinho-dataset/
├── AGENTS.md            # este contrato
├── ESTADO.md            # número oficial e o que está medido
├── RESUMO_PAUSA.md      # ⚠ divergente do ESTADO.md (diz 0,851) — unificar
├── PERGUNTAS.md         # levantamento de requisitos para o dono responder
├── tools/               # 10 scripts + README
├── docs/                # 65 documentos de rodada, soltos
├── gold/gabarito.json   # 96 glifos rotulados à mão
├── saida/               # JSONs gerados
├── parts/clipes/        # 18 recortes de amostra (656 MB)
└── .venv/               # 5,8 GB — nunca versionar
```

Alvo (a confirmar — pergunta **B5**):

```
chorinho-dataset/
├── AGENTS.md  README.md  ESTADO.md  PERGUNTAS.md
├── pyproject.toml  Makefile
├── tab/                 # o motor, flat: segmentar glifos sintetico marcador transcrever avaliar
├── tests/               # unit + integration (dados externos)
├── configs/             # canais.yaml, simbolos.yaml (mapa símbolo→técnica POR CANAL)
├── data/gold/  data/saida/
├── artefatos/           # modelos .pt — NUNCA em /tmp (hoje o modelo vive em /tmp, é efêmero)
└── docs/{rodadas,decisoes,guias}/
```

Regras de arrumação, já valendo:

1. **Nada de `.md` solto na raiz** além dos quatro acima. Documento novo vai para
   `docs/` no subdiretório certo.
2. **Um documento por rodada** em `docs/rodadas/`, nome `NNNN-titulo-curto.md`.
3. **Uma decisão por arquivo** em `docs/decisoes/` (ADR curto: contexto, opções,
   decisão, consequência).
4. **Nunca apague** documento de rodada — é o histórico das medições. Consolidar, sim
   (pergunta **B3**); apagar, não sem ordem explícita.
5. **Sem `src/` e sem pacote dentro de pacote.** Um pacote só, na raiz e com nome
   curto. Profundidade de diretório é custo, não organização — pergunta **B5** decide
   o nome (`tab/` hoje).
6. **Modelo treinado vai para `artefatos/`**, com o comando e a semente no nome ou num
   JSON ao lado. Modelo em `/tmp` é modelo perdido.

## Regras de trabalho (custaram rodadas — não repita)

1. **Semente fixa + ≥3 execuções, reporte média e amplitude.** Sem isso o mesmo código
   deu 0,729 e 0,854 e eu reportei ruído como ganho.
2. **Meça a amostra antes de gastar treino.** Três retreinos foram queimados
   descobrindo que a classe não nascia.
3. **Confira o significado do número.** "323 notas com tempo" eram **3 instantes**;
   "41 notas com duração" eram **8 ataques sem duração**. Conte instantes distintos.
4. **Olhe o quadro antes de teorizar.** Duas vezes medi o violão achando que era a
   tablatura — o braço tem 6 cordas e engana o detector.
5. **Rótulo de gabarito só por leitura visual.** Relabelar por proxy geométrico
   (`partes>=2`) piorou duas vezes (raman 12→4, 12→9) e foi revertido.
6. **O gargalo histórico é cobertura do gerador sintético, não regra de visão.**
   Medido 6 vezes: 3 regras geométricas deram 0, uma deu −0,166; as duas mudanças de
   dado deram +0,052 e +0,046.
7. **Depois de editar o gerador ou o treino, valide `ast.parse` + `import`** antes de
   rodar. Quebrei o `sintetico.py` uma vez com indentação e só descobri no treino.
8. **Registre o que falhou.** A tabela "não repetir" no fim do `ESTADO.md` existe para
   impedir que uma rodada gasta seja gasta de novo.
9. **Um commit por tarefa** (quando o repositório existir — pergunta **B1**).

## Regras de código

- **Python 3.14**, sem import dentro de função;
- aspas duplas, **88 colunas**, imports no topo em 3 blocos (stdlib / terceiros /
  locais) ordenados;
- **type hints** em todas as assinaturas; docstring estilo Google em toda função,
  método e classe pública;
- **nomes em português** (é o padrão vigente: `binarizar`, `achar_cordas`, `passo`,
  `glifo`) — pergunta **B6** resolve se muda;
- lint `ruff` (convenção Google) e testes **antes** de todo commit: `make lint`,
  `make typecheck`, `make test`. Só commite com `All checks passed!`.

## Vocabulário (para não haver dúvida)

| termo | significado exato |
| --- | --- |
| **grade** | resultado da segmentação: linhas de corda, barlines, passo, glifos |
| **passo** | distância vertical entre duas cordas, em px (14–45 no acervo) |
| **glifo** | componente conectado de tinta antes de agrupar |
| **token** | glifo(s) da mesma corda já agrupados = uma nota (ou um símbolo) |
| **painel** | a região da tela com a tablatura (varia por vídeo: topo/meio/base) |
| **marcador** | o que indica a nota sendo tocada: **faixa vertical** que passa, ou **cor** que muda no algarismo |
| **casa** | o número na corda (a pestana pisada) |
| **ligada** | nota presa/ligada, desenhada como `(6)` ou arco |
| **harmônico** | `<7>` ou losango |
| **acervo** | os 3.781 vídeos, 190 GB, 13 canais no HD externo |
| **fold/rollout** | rodar o pipeline em muitos vídeos e decidir por vídeo |

## Limites conhecidos (não prometa além disto)

96 glifos, 4 canais, **casas 0–7**; aferição **glifo a glifo**, não da música inteira.
A casa dos canais fora do gabarito (ex.: `cifra club` — tem corda e tempo, casa não
aferida) **não está validada**. **Tab ASCII** (Ultimate Guitar) e **partitura** de 5
linhas exigem leitor próprio e estão **fora desta cadeia**.

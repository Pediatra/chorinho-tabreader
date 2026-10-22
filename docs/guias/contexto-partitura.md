# Contexto para o agente da partitura (quarta trilha)

> Documento de passagem de contexto, escrito em 2026-10-13 pelo agente que coordena a trilha
> **tablatura + tempo** (o "cérebro" do projeto). Leia este arquivo, depois o
> [`AGENTS.md`](../../AGENTS.md) **inteiro**, o [`docs/estado/partitura.md`](../../docs/estado/partitura.md) (índice: [`ESTADO.md`](../../ESTADO.md)), o
> [`plano-do-produto.md`](plano-do-produto.md), o [`contexto-maos.md`](contexto-maos.md)
> (seções 2 a 4 e 6: projeto, ambiente, JSON do produto, convivência) e o
> [`contexto-audio.md`](contexto-audio.md) (seção 5: convivência com quatro trilhas segue o
> mesmo molde). Este documento não substitui o `AGENTS.md`: as regras de lá valem para você.

---

## 1. O objetivo final e onde você entra

O dono quer um **dataset rotulado** para treinar, no futuro, um modelo que receba **só um vídeo
de alguém tocando violão** e devolva **tablatura e partitura**. Cada nota tocada nos vídeos-aula
do acervo precisa sair com tudo alinhado no tempo:

| camada | o que é | quem faz |
| --- | --- | --- |
| tablatura | corda, casa, coluna, compasso, símbolo cru | trilha tablatura (eu) |
| tempo pelo marcador | `t_ini` de cada coluna pela faixa/cor que anda na tela | trilha tablatura (eu) |
| tempo pelo áudio | instante em que a nota soa | trilha áudio (outra sessão Opus) |
| mãos | keypoints e dedo de cada nota | trilha mãos (outra sessão Opus) |
| **partitura** | **pauta de 5 linhas lida da tela → formato estruturado** | **você** |

**O que a partitura acrescenta que a tablatura não tem:**

1. **Ritmo de verdade.** A tablatura dá corda e casa; a duração hoje é **inferida** pelo
   intervalo entre ataques (`tab/tablatura/produto/musicxml.py` declara isso no cabeçalho). A pauta escreve
   figura (semínima, colcheia…), pausa, ponto, ligadura, fórmula de compasso, vozes.
2. **Conferência cruzada.** Corda + casa + afinação → altura exata. Onde pauta e tablatura
   aparecem juntas, cada nota da pauta tem que bater em altura com a coluna da tab embaixo dela.
   Divergência denuncia erro de leitura de um dos lados (ex.: o classificador da tab lendo 0 onde
   é 8, erro que o dono acabou de corrigir à mão 67 vezes no Gymnopédie).
3. **Vídeos que só têm pauta**, se existirem em número relevante: ali a partitura é a única fonte.

**Direção do dono:** OMR é um problema muito difícil; **usar uma biblioteca pronta e fazer
ajustes finos**, não construir leitor do zero. Escolha da biblioteca **por medição**.

## 2. A ideia central: o tempo você herda, não mede

Nos vídeos "partitura + tab" (pablo romé *Greensleeves*, guitar dell'arte *South American
Music*, robert lunn *Gymnopédie*, mr. tabs, sky guitar…), a pauta fica **logo acima** da
tablatura e as duas são **alinhadas na horizontal**: a nota da pauta está em cima da coluna da
tab que a toca. A coluna da tab já tem, no JSON do produto, a posição `x` e o `t_ini`.

Então o tempo da partitura sai de um **pareamento** (por `x` dentro da mesma tela e exibição,
confirmado pela altura), não de um medidor novo. **Não construa medidor de tempo próprio.**

Hoje o tempo da tablatura ainda não está bom fora do MVP (Greensleeves: 20 de 40 instantes
certos). Eu estou consertando isso (T8.3). Por isso o pareamento com tempo é a **última** fase
(P3), depois que eu avisar, via dono, que o tempo da tab está aferido nos vídeos da Fase 8.

## 3. O que já se sabe sobre pauta neste acervo (aprendido a duras penas)

- A pauta foi até agora **ruído** para a trilha tablatura: decisão
  [`0007`](../decisoes/0007-painel-com-partitura-e-tablatura.md). Painel que pegava pauta +
  tab fazia o detector achar "6 linhas" na mistura (5 da pauta + 1). O detector de painel
  (`tab/tablatura/leitura/painel.py`, `tab/tablatura/produto/telas.py`, `tab/tablatura/leitura/tabseg.py`) está **sendo mexido agora** por outro
  agente meu para não escolher o braço do violão. **Não dependa do retângulo de painel dele
  para achar a pauta**, e não o altere: faça seu próprio localizador de pauta
  (`tab/partitura/`). Você pode, sim, usar o retângulo da **tablatura** como âncora (a pauta
  costuma estar logo acima), lendo do JSON do produto.
- **Resolução**: bibliotecas de OMR são treinadas em PDF/scan a 300 dpi. Num quadro de vídeo
  1080p a pauta pode ter entrelinha de ~8–15 px e linhas de 1–2 px, com compressão AV1/H.264
  (44 % do acervo é AV1: decodifique com `tab/comum/leitor.py`, que usa ffmpeg).
- Há vídeos onde a pauta **rola** (mr. tabs, leonardo ramos) em vez de paginar; deixe-os para
  depois, como a trilha tablatura fez (T8.4).
- A lição do projeto com modelo grande pronto: um VLM (GOT-OCR2.0, 580 M) acertou **0 de 15**
  algarismos de tablatura. Biblioteca famosa não é garantia: **meça em quadro real**.

## 4. Proposta de caminho (P0–P3), com critérios

**P0 — Quantos vídeos têm pauta?** O censo v2 (`data/saida/tablatura/censo/v2/censo_v2_completo.jsonl`,
2.998 vídeos ativos, 12 instantes por vídeo, com `rect` da tablatura) **não mede pauta**. Meça
numa amostra estratificada por canal (ex.: 30 vídeos por canal, poucos instantes por vídeo,
**lendo do cache de quadros** em `/cache` quando houver, para não martelar o HD externo):
- classes: **pauta + tab**, **só pauta**, **só tab**, nenhuma;
- detector simples de pauta (5 linhas paralelas equiespaçadas), **conferido visualmente** numa
  folha de miniaturas antes de acreditar no número (regra 4 do `AGENTS.md`);
- saída: fração por canal com denominador, extrapolada pelo tamanho dos canais.
Este número decide o tamanho da trilha. Leve ao dono antes de seguir.

**P1 — Comparação de bibliotecas.** Candidatas a considerar (verifique estado e licença na hora;
não confie nesta lista): **homr**, **oemer**, **Audiveris** (Java, CPU), outras que achar.
- Monte ~20 recortes de pauta de quadros reais, variando canal, resolução e densidade;
- **gabarito pequeno do dono**: para cada recorte, alturas e figuras das notas. Proponha o
  formato mais barato para ele (ex.: ele confirma/corrige a leitura da melhor biblioteca, como
  na página de ouro da tab, em vez de digitar do zero). O tempo do dono é o gargalo;
- métricas por nota com denominador: altura certa, figura certa, nota faltando, nota inventada.
  **Nota inventada é o pior erro** (falso positivo vale mais que ausência declarada);
- conte também custo (s por recorte, CPU/GPU, memória) e se a saída é MusicXML/estruturada.

**P2 — Ajuste fino da escolhida.** Pré-processamento (recorte, escala, binarização), e só se
necessário, ajuste de pesos com dado do acervo. O pré-processamento é **entrada do modelo**:
mudou, invalidou a comparação anterior (regra 9). Três sementes se houver treino.

**P3 — Pareamento com a tablatura e o tempo (só depois do meu aviso).** Para cada tela e
exibição: parear nota da pauta ↔ coluna da tab por `x` e altura; herdar `t_ini`. Reportar
quantas notas pareadas, quantas divergentes em altura (e de que lado parece estar o erro),
quantas sem par. Proponha como isso entra no produto (arquivo irmão
`<video>.partitura.json` ou campos novos, usando a chave de evento
`(tela, passagem, exibicao, coluna, corda)`), em `docs/decisoes/3NNN-…`. **`tab/tablatura/produto/esquema.py` e
`tab/tablatura/produto/musicxml.py` são da trilha tablatura: não edite**; eu faço a mudança quando o dono aprovar.

## 5. Regras de convivência (agora são quatro trilhas)

Valem integralmente a seção 6 do `contexto-maos.md` e a seção 5 do `contexto-audio.md`. Para você:

1. **Seus arquivos**: `tab/partitura/<modulo>.py` (pasta da trilha, decisão 9001), `tests/partitura/`,
   saída em `data/saida/partitura/`, gabarito em `data/gold/partitura/`, pesos em
   `artefatos/partitura_*/`.
2. **Não edite** arquivos de outras trilhas: tablatura (lista do `contexto-maos.md` seção 6, mais
   `tab/tablatura/ouro/ouro_video.py`, `tab/tablatura/ouro/avaliar_video.py`, `tab/tablatura/leitura/painel.py`, `tab/tablatura/produto/telas.py`,
   `tab/tablatura/produto/esquema.py`, `tab/tablatura/produto/musicxml.py`, `data/gold/ouro_video/`), mãos (`tab/maos_*`,
   `Dockerfile.maos`), áudio (`tab/audio_*`, `Dockerfile.audio`). Importar é livre.
3. **Documentos**: rodadas e decisões com prefixo **3NNN** (tablatura 0NNN, mãos 1NNN, áudio
   2NNN). Seção nova no fim de `docs/estado/partitura.md` (decisão 9001); no `ESTADO.md`, só a tabela "não repetir"; confira
   `git diff ESTADO.md` antes de commitar: só as suas linhas entram.
4. **Dependências novas**: imagem derivada `Dockerfile.partitura` (`FROM
   docker.io/library/chorinho:dev`), versões fixas, sem trocar `torch`/`opencv` da base
   (`--no-deps` quando preciso). Java (Audiveris) também vai nela, nunca na base.
5. **Gate compartilhado** (`ruff check .`, `ruff format --check .`, `pytest tests/ -m "not
   integration"`) roda na imagem **base**: teste que importa biblioteca só da sua imagem usa
   `pytest.importorskip` ou a marca `integration`. Gate vermelho trava as quatro trilhas.
6. **Git**: `git add` só por nome; nunca `add -A`, `reset`, `amend`, `stash`, `checkout --`;
   `git commit -F arq`; um commit por tarefa, com o número medido.
7. **GPU** (uma, 8 GB, quatro trilhas): `data/saida/gpu.lock` com
   "partitura, <início>, <estimativa>" antes de uso longo; se houver lock alheio, espere ou use
   CPU. Prefira CPU na P0 e na P1.
8. **HD externo** é o gargalo de E/S: leia do cache de quadros quando houver; varredura longa,
   combine o horário com o dono.
9. **Comunicação**: as sessões não se falam; o dono é a ponte. Decisão que afete outra trilha
   vira arquivo em `docs/decisoes/`.

## 6. Regras do projeto que mais pesam para você (resumo do `AGENTS.md`)

- **Olhe o quadro antes de teorizar**; figuras em `data/saida/partitura/`, nunca em `/tmp`.
- **Rótulo de gabarito só do dono, por leitura visual dele.** Agente nunca grava em
  `data/gold/` por conta própria; leitura provisória vai para `data/saida/`, marcada.
  Ferramenta de rotulagem com autosave: **nunca teste clicando no arquivo real do dono**,
  teste numa cópia.
- **Confira o significado do número**: notas distintas, denominador sempre.
- **Determinismo**: mesma entrada → mesma saída; aleatoriedade = semente + ≥3 execuções.
- **Registre o que falhou** na tabela "não repetir" do `ESTADO.md`.
- Código: Python 3.14, sem import dentro de função, aspas duplas, 88 colunas, type hints,
  docstring Google, **nomes em português**, CLI `python -m tab.partitura.x` com `main()`.

## 7. Estado das outras trilhas (2026-10-13)

- **Tablatura (eu)**: Fase 8, gabarito de tab + tempo em vídeos paginados, rotulado pelo dono
  na página `tab.tablatura.ouro.ouro_video`. Prontos: retrato brasileiro (MVP), Greensleeves, South American
  Music, Gymnopédie (`data/gold/ouro_video/`). **Greensleeves, South American e Gymnopédie têm
  pauta acima da tab**: são o seu primeiro banco de teste, e as notas da tab deles, conferidas
  pelo dono, dão a altura esperada de graça (corda + casa → altura) para checar a leitura da
  pauta antes mesmo de existir gabarito de partitura. Rodando agora: conserto do detector de
  painel (braço do violão) e fonte serifada no gerador do classificador.
- **Áudio**: alinhador de ataques às colunas, rodadas 2001–2006.
- **Mãos**: detector de mãos e dedo por nota, rodadas 1001–1007.

## 8. Arquivos para ler primeiro

1. `AGENTS.md` (inteiro).
2. `docs/estado/partitura.md`: estado medido, seções sobre partitura no painel; `ESTADO.md`: "não repetir" (busque
   "partitura" e "pauta").
3. `docs/decisoes/0002-presenca-da-tablatura-e-musicxml.md` (MusicXML é o produto final) e
   `0007-painel-com-partitura-e-tablatura.md`.
4. `docs/guias/plano-do-produto.md`, `contexto-maos.md` (seções 2–4, 6), `contexto-audio.md`
   (seção 5).
5. `tab/tablatura/produto/esquema.py` (JSON `chorinho/video@1`, chave de evento), `tab/tablatura/produto/musicxml.py` (como a
   duração é inferida hoje), `tab/tablatura/censo/afinacao.py` (corda+casa→altura; **nunca aferido**, meça).
6. `tab/comum/leitor.py` (leitor de vídeo com PTS real), `tab/comum/cache.py` (cache de quadros).
7. `data/gold/ouro_video/*.json` dos três vídeos com pauta (formato v2: telas, notas `mN`/`dN`,
   `conferida`).

# Retomada da trilha áudio (2026-10-21)

> Briefing para o agente novo da trilha áudio. Ele foi escrito pela sessão da trilha
> **mãos/braço**, a pedido do dono, em 2026-10-21. Leia, nesta ordem:
> 1. [`AGENTS.md`](../../AGENTS.md), inteiro: é o contrato;
> 2. este arquivo;
> 3. [`contexto-audio.md`](contexto-audio.md) (2026-10-13), seções 2 a 6: a história e as
>    regras da trilha;
> 4. as seções **"Áudio —"** do [`ESTADO.md`](../../ESTADO.md) e as rodadas
>    `docs/rodadas/2001…2016`.
>
> A memória do projeto (`MEMORY.md`) carrega sozinha. Ela traz as preferências do dono, e as
> que mais pesam estão resumidas na seção 6.

---

## 1. Por que a trilha volta, e com que escopo

**O pedido do dono** (2026-10-21) tinha duas partes:
- separar o som do violão dos barulhos externos;
- classificar todos os sons em notas musicais, para depois juntar tablatura, mãos e notas.

**O que foi combinado com ele.** O escopo é **altura condicionada à tablatura**, e não a
transcrição livre do áudio:

- **A decisão [0011](../decisoes/0011-tablatura-vira-rotulo-da-base.md) vale:** o rótulo vem só
  da tela. O som e as mãos **conferem**, mas não criam rótulo. A tablatura já diz quais notas
  devem soar. A pergunta fácil e mensurável é "a nota esperada soou, quando e com que altura?",
  e não "que notas há neste áudio?".
- **Separar o violão do ruído** (Demucs ou parecido) pede download, dependência nova e GPU.
  Isso só entra **depois de medido** que o ruído derruba a conferência (frente D), e **com
  aprovação do dono** para o download.
- **A GPU está liberada pelo dono quando estiver desocupada.** Use a trava da seção 4, que
  espera sozinha.

## 2. Onde a trilha parou, e o que mudou desde então

**Parou em 2026-10-13, na rodada 2016.** O alinhador v2.1 rodou em 22 vídeos e 18 canais (lotes
1 e 2):
- nos canais onde a tablatura é bem lida, de 74 % a 98 % das colunas recebem `t_audio`;
- nos 3 canais novos em que o produto leu o marcador, tirado o atraso fixo do canal (de −115
  a +178 ms), de 77 % a 95 % das colunas ficam a até 100 ms do marcador;
- o formato `chorinho/audio@1` (arquivo irmão do produto) está na decisão
  [2003](../decisoes/2003-tempo-do-audio-no-produto.md);
- os pedidos à trilha tablatura estão na [2004](../decisoes/2004-pedidos-de-leitura-a-trilha-tablatura.md).

**O que mudou depois, e afeta você:**

1. **O leitor do produto mudou** (decisão [0010](../decisoes/0010-leitor-rede.md), 2026-10-14):
   o padrão agora é o leitor `rede`.
   - **O X do rasgueado** deixou de sair com top-1 `"15"` e passou a sair como `nao_notas` de
     classe `"x"`. Com isso, `colunas_abafadas` (`tab/audio_alinhar.py`) **não acha nenhuma
     coluna abafada num JSON novo**. Leia o "Aviso à trilha áudio" no fim da 0010.
   - **A revocação das notas subiu de 0,83 para 0,95.** Os números das rodadas 2001–2016 são
     do leitor antigo e não se comparam direto com os novos.
2. **A base de treino das mãos depende do `t_audio`** (decisão 1006 e
   [`plano-dataset-maos.md`](plano-dataset-maos.md), item M13). O tempo de cada nota da base é
   o do **som**, e não o do marcador.
3. **Capotraste** (decisão [1010](../decisoes/1010-capotraste-como-nut-do-braco.md)):
   - no braço, o nut é o capo, e os trastes contam a partir dele;
   - a tablatura da tela também vem contada a partir do capo;
   - **a altura que soa = corda solta + casa da tab + casa do capo.** É o `--transposicao` do
     `tab.audio_alinhar`, que hoje é sempre 0;
   - o dataset precisa da casa do capo por vídeo (`violao.capotraste` na decisão 1007), e
     anotar vídeo a vídeo gasta o tempo do dono. O som pode dar esse número.
4. **A trava da GPU virou código** (`tab/gpu.py`; ver a seção 4).

## 3. Frentes, em ordem

Cada frente é uma rodada `20NN`, a próxima é a 2017, sempre com **pré-registro antes de
medir**. Os critérios abaixo são propostas, e você os fixa no pré-registro.

### A. Regressão com o leitor `rede` (2017; CPU)

- **Antes de qualquer coisa nova:** gere de novo o produto (`tab.video`) e rode o alinhador
  em uma amostra que já tem número antigo, com o leitor `rede`:
  - o MVP;
  - os 5 vídeos bons do lote 2;
  - os vídeos bons do lote 1.
- **Ajuste `colunas_abafadas`** para a classe `"x"`, mantendo o top-1 `"15"` para os JSONs
  antigos, como a 0010 sugere.
- **Meça:** colunas com tempo e som × marcador, por vídeo, antigo contra novo, com o
  denominador de cada um.
- **Critério:** não piorar onde o leitor antigo era bom. Se piorar, ache a causa antes de
  seguir.

### B. Casa do capo pelo som (2018; CPU)

**A verdade, já pronta:** `data/saida/maos/capo_por_video.json`. Ela é gerada por
`python -m tab.maos_braco_capo` a partir das observações do dono.
- **33 vídeos com capo** (casas de 1 a 6), e **0 conflitos** entre quadros do mesmo vídeo.
- **180 vídeos sem capo** nos quadros que o dono viu (`sem_capo`): é o controle negativo, com
  casa esperada 0. **Atenção:** o controle só garante os quadros vistos. O capo pode aparecer
  em outro trecho do vídeo.
- **Ficam de fora os 4 vídeos do violaodecria:** a tab deles é texto ASCII, e o produto não lê
  (`configs/canais.yaml`, `rollout: fora`).
- **Ficam de fora (ou como recusa esperada) as tabs só de ritmo, sem casa**, como o *believer*
  do kenneth na rodada 2016.

**O método sugerido:** para cada vídeo, rodar o alinhamento com a `transposicao` de 0 a 7 e
escolher a que melhor casa o som com a tab, com **recusa** quando a margem entre a melhor e a
segunda for pequena.
- **Cuidado com o molde do alinhador:** ele soma a 12ª (`DESLOCAMENTOS_MOLDE = (0, 12, 19,
  24)`). Isso pode fazer uma transposição de 7 semitons (uma quinta) pontuar alto. Meça essa
  confusão.

**Critério proposto:** **0 casa de capo errada afirmada** (o falso positivo é o pior erro do
projeto), e decisão em pelo menos metade dos vídeos com tab legível.

**Entrega:**
- um arquivo seu em `data/saida/audio/` com a casa estimada por vídeo, a margem e a recusa;
- a trilha mãos põe esse número em `violao.capotraste`;
- o `capotraste_fonte` da decisão 1007 ainda não tem o valor `"som"`. Peça pelo dono, e a
  trilha mãos acrescenta. **Não edite a 1007.**

### C. Conferência nota a nota (2019; CPU)

Esta é a parte do pedido do dono de "classificar os sons em notas", dentro da 0011. Para cada
nota com `t_audio`, a altura esperada (com o capo da frente B) soou?

- **As classes:**
  - **soou**;
  - **não soou**;
  - **outra altura**: de ±1 a ±2 semitons. Isso indica uma casa vizinha mal lida na tab, ou um
    capo errado.
- **Saída: checagens por nota, nunca rótulo.** Elas servem para três coisas:
  - alarmes à trilha tablatura (como os da 2004);
  - conferir a numeração do braço, já que casa vizinha errada é o erro inaceitável do dono;
  - filtrar a base das mãos.
- **Critério:** fixe-o no pré-registro, por amostra que o dono julgue por escuta (veja a regra
  do tempo do dono, seção 6). Peça o mínimo que mede.

### D. Separação do violão (só se a frente C mostrar a necessidade)

- **Antes de propor:** conte, nos dados da C, que fração das recusas ou falhas cai em trecho
  com voz, metrônomo ou música de fundo. Para isso, olhe e escute amostras: a regra 4 do
  AGENTS.
- **Se a fração for relevante:**
  - proponha ao dono a dependência, com nome, versão, tamanho e fonte, e **peça aprovação
    antes de baixar**;
  - instale na imagem derivada `Dockerfile.audio`, nunca na base, com `--no-deps` e conferência
    das versões (decisão 2001);
  - use a GPU pela trava.

## 4. GPU, HD e containers

- **A trava da GPU:**

  ```python
  from tab.gpu import trava_gpu

  with trava_gpu("audio", "40 min"):
      ...  # o trabalho na GPU
  ```

  - Ela cria `data/saida/gpu.lock` ("trilha, início, estimativa") e espera se outra trilha
    estiver usando a GPU.
  - Ela retoma uma trava que sobrou de processo morto e confere se há ≥ 3 GB livres.
  - **A trilha mãos usa a mesma trava.** Nos próximos dias ela tem janelas de ~6 h de
    retreino. Quando a GPU desocupar, você entra sozinho.
- **Nunca pare nem mexa em container de outra trilha.** O ajuste fino da trilha tablatura
  (`data/saida/n4/treinar_ft.py`), por exemplo, pode usar a GPU sem a trava, e por isso ela
  confere a memória livre.
- **O HD externo do acervo é o gargalo de leitura.** Extraia cada áudio uma vez para o cache
  (`tab.audio_extrair`). Para um lote grande, combine o horário com o dono.
- **Como rodar.** Esta sessão roda dentro de um distrobox:
  - o container é o podman do host, chamado por `host-spawn -no-pty podman run ...`;
  - o git também vai por `host-spawn -no-pty -cwd $PWD git ...`;
  - imagens: a base é `docker.io/library/chorinho:dev`, e a sua é `localhost/chorinho-audio:dev`
    (`Dockerfile.audio`);
  - GPU no podman: `--device nvidia.com/gpu=all`;
  - bind-mounts: `-v <repo>:/app -w /app -e PYTHONPATH=/app --security-opt label=disable` e o
    acervo em `/acervo:ro`;
  - um exemplo completo da cadeia está em `data/saida/audio/a4/lote2/rodar_lote2.sh`.
- **Ruff dentro do container:** use `--no-cache`. **Pytest:** use `-p no:cacheprovider`.

## 5. Convivência (quatro trilhas)

| trilha | arquivos dela (não edite) | rodadas / decisões |
| --- | --- | --- |
| tablatura (+ tempo do marcador) | a lista da seção 6 do [`contexto-maos.md`](contexto-maos.md) (`tab/esquema.py`, `tab/video.py`, `tab/leitor.py`, `tab/cache.py`…), mais `tab/ouro_video.py`, `tab/detector_tab.py`, `tab/sintetico_sistema.py`, `tab/afinacao.py` e `data/saida/n4/` | `0NNN` |
| mãos / braço | `tab/maos_*.py`, `tests/test_maos_*`, `data/gold/maos/`, `data/saida/maos/` (**ler é livre**, por exemplo o `capo_por_video.json`), `Dockerfile.maos` | `1NNN` |
| **áudio (você)** | `tab/audio_*.py`, `tests/test_audio_*.py`, `data/saida/audio/`, `data/gold/audio/`, `Dockerfile.audio` | `2NNN` |
| partitura | `tab/partitura_*.py`, `Dockerfile.partitura`, `data/gold/partitura/` | `3NNN` |

- **`tab/gpu.py` é compartilhado.** Se precisar mudar, a mudança passa pelo dono.
- **Nunca commite** `data/gold/partitura/compassos_homr.json` nem
  `data/gold/partitura/figura_e1.json`. Eles ficam fora do git de propósito.
- **Git:**
  - `git add` só por nome;
  - nunca `add -A`, `reset`, `amend`, `stash` ou `checkout --`;
  - **um commit por tarefa**, com o número medido;
  - no `ESTADO.md`, só seções "Áudio —", e confira `git diff ESTADO.md` antes de commitar.
- **Gate antes de todo commit:**
  `ruff check . && ruff format --check . && pytest tests/ -q`.
  - **Julgue pelo código de saída:** nunca `gate | tail && commit`, porque o `tail` engole a
    falha.
  - O gate roda na imagem **base**: teste que importa biblioteca só da sua imagem usa
    `pytest.importorskip`.
- **As sessões não se falam direto.** O dono é a ponte, e decisão que afeta outra trilha vira
  arquivo em `docs/decisoes/`.

## 6. Como o dono trabalha (o que mais pesa)

- **Fale com ele em português**, de forma clara e curta, com números e denominadores.
  - Não faça o dono escolher de uma lista sem mostrar a lista.
  - Não mande status vazio ("ainda rodando"): fale quando tiver resultado.
- **O tempo do dono é o gargalo do projeto.** Para gabarito trabalhoso:
  - faça **palpite por regra do domínio**, e o dono confirma ou corrige;
  - para conferência, prefira a ferramenta que já existe (`tab.ouro_video servir`) a uma
    página nova;
  - folha por escuta: pouca coisa, que ele julgue rápido (certo / errado / não sei).
- **O rótulo do dono é contrato.** Nunca altere nem infira um rótulo dele. O agente não grava
  em `data/gold/`. Rótulo provisório vai para `data/saida/`, marcado.
- **Ferramenta de rotular se testa numa cópia**, nunca no gabarito ao vivo, porque ele grava a
  cada clique.
- **Para delegar, use sempre o Haiku 5.5**, com briefing fechado. Depois, **revise e meça de
  novo você mesmo**: o número que vai para o dono é o seu.
- **Em janela longa e autônoma** (o dono fora por horas), siga a sua recomendação sem
  perguntar. Se algo falhar, aprenda, revise e tente de novo. As falhas vão para o relatório
  final e para a tabela "não repetir" do `ESTADO.md`. **Só interrompa por algo sério.**
- **Pergunte antes** de download, dependência nova, ou qualquer coisa fora do repositório. O
  acervo (`/acervo`) é **somente leitura**.
- **Nunca imprima, registre em log ou commite** a chave da DeepSeek.

## 7. Arquivos para ler primeiro

1. `AGENTS.md`, e este arquivo.
2. `docs/guias/contexto-audio.md`, seções 2 a 6.
3. `ESTADO.md`, nas seções "Áudio —" (rodadas 2001 a 2016).
4. As decisões 2001 a 2004, mais a [0010](../decisoes/0010-leitor-rede.md) (o aviso no fim), a
   [0011](../decisoes/0011-tablatura-vira-rotulo-da-base.md), a 1007 (formato da base, campo
   `violao`) e a [1010](../decisoes/1010-capotraste-como-nut-do-braco.md).
5. `docs/guias/plano-dataset-maos.md`: onde o `t_audio` entra na base.
6. O código: `tab/audio_alinhar.py` (`alinhar`, `--transposicao`, `colunas_abafadas`,
   `DESLOCAMENTOS_MOLDE`), `tab/audio_extrair.py`, `tab/audio_produto.py`, `tab/gpu.py` e
   `tab/maos_braco_capo.py`.

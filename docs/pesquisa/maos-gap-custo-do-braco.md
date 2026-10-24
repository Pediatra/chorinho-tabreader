# Tarefa delegada — Deixar a cadeia do braço mais rápida, com a mesma resposta

**Data**: 2026-10-23. **Trilha**: mãos (rodadas `1NNN`). **Quem escreveu**: a sessão principal das
mãos. **Para quem**: um agente que **não** viu a conversa. Tudo o que você precisa está aqui; se
algo não estiver, **pare e pergunte ao dono**, não suponha.

**Tempo máximo**: 1 dia de trabalho (8 horas). Passou disso, pare e entregue o que tem.

---

## 1. O projeto em poucas linhas

- O projeto monta uma **base de dados de violão**: para cada nota tocada nos vídeos-aula, guarda
  a nota, o instante do som, o **braço do violão** (nut, trastes e cordas) e as duas mãos,
  quadro a quadro.
- O braço é achado por uma **cadeia** de redes neurais já treinada e medida. Ela é **segura**:
  nas duas provas lacradas (76 quadros), deu **0 erros sem aviso**. Ninguém pode mudar a
  **resposta** dela. Esta tarefa só pode mudar a **velocidade**.
- Leia `AGENTS.md` (na raiz) **inteiro** antes de rodar qualquer coisa. As regras dele valem
  para você, em especial as seções 4 (ambiente), 7 (regras de trabalho), 9 (git e gate) e 10
  (código).
- Fale com o dono em **português simples**, com números e denominadores.

## 2. O problema

A cadeia roda **22 hipóteses** por quadro: 11 pares de pesos (`PARES` em
`tab/maos/braco/validadores.py`) × 2 modos (o quadro original e o espelhado na horizontal).
Depois, uma regra escolhe a resposta (`cadeia_sem_tomada`, no mesmo arquivo).

Medido em 2026-10-23: **~1 s por quadro por par**, ou **~20 s por quadro** com as 22 hipóteses.
Para a base de 20 vídeos isso dá ~50 horas de GPU, e para o acervo inteiro fica inviável.

## 3. O caminho do código (leia nesta ordem)

1. `tab/maos/braco/validadores_gpu.py`, função `hipoteses_na_pasta(pasta_quadros, indice,
   saida)`: grava os quadros espelhados em disco, e para cada modo e cada par chama
   `prever_quadros`, depois `aplicar_sinal_nut_v2`, desespelha e alinha as cordas. Grava um
   JSON por hipótese em `saida/`.
2. `tab/maos/braco/ciclo.py`, funções `prever_quadros` → `_prever_quadros`: carrega os dois
   modelos do par **uma vez** e, para **cada quadro**, lê o PNG e chama `cadeia(...)`.
3. `tab/maos/braco/localizador.py`, função `cadeia(...)` (por volta da linha 995): por quadro,
   - estágio 1: `prever_localizador(modelo_loc, [canvas])` (GPU, **1 imagem por vez**) e a
     decodificação (CPU);
   - estágio 2, 1ª passada: `prever_mapas(modelo_dois, [faixa])` (GPU, 1 por vez) e
     `decodificar_com_dados` (CPU);
   - estágio 2, 2ª passada: de novo;
   - `_extras(...)`: `N_EXTRAS` faixas perturbadas numa chamada só de `prever_mapas`, e uma
     decodificação por extra (CPU).
4. `tab/maos/braco/ciclo.py`, `aplicar_sinal_nut_v2`: para cada quadro, `linhas_de_painel` na
   imagem (CPU). É chamada uma vez por par: **11 vezes** a mesma conta por quadro em cada modo.

Você **não sabe ainda** onde o tempo vai. O primeiro passo é medir (seção 6, passo 2).

## 4. O que você pode e o que não pode mudar

**Pode** (se a resposta continuar igual, seção 7):
- não refazer a mesma conta (ex.: `linhas_de_painel` 1 vez por quadro e modo, em vez de 11);
- não gravar os espelhos em disco (virar a imagem em memória);
- pôr várias imagens na mesma chamada da GPU (`prever_localizador` e `prever_mapas` já aceitam
  lista);
- rodar as decodificações de CPU em paralelo (processos), com o resultado na mesma ordem;
- ler cada PNG uma vez só.

**Não pode**:
- mudar pesos, limiares, `PARES`, `N_EXTRAS`, sementes, o recorte da faixa, a resolução, a
  ordem das hipóteses, ou qualquer regra de decisão;
- tirar hipóteses ou pares ("rodar só 6 dos 11") — isso muda a resposta e precisa de rodada
  nova, que **não** é esta tarefa;
- mudar `float32` para `float16` em lugar onde hoje não é;
- editar arquivos de outras trilhas (`tab/tablatura/`, `tab/audio/`, `tab/partitura/`) ou
  `data/gold/`; escrever no acervo.

## 5. Onde trabalhar (importante: há uma execução longa rodando)

Até ~05h30 de 2026-10-24 há uma execução usando a GPU e **importando o código de `tab/` da
pasta principal**. Se você mexer em `tab/` na pasta principal, pode estragar essa execução.
Por isso **trabalhe numa worktree** (uma cópia do repositório em outra pasta, num branch
próprio):

```bash
cd /var/home/gabriel/Projects/chorinho-dataset
host-spawn -no-pty git worktree add ../chorinho-wt-custo-braco -b maos/custo-braco
```

A worktree **não tem** os pesos (`artefatos/`) nem os dados (`data/saida/`), porque eles ficam
fora do git. Monte os da pasta principal no container. O comando-modelo (GPU):

```bash
P=/var/home/gabriel/Projects/chorinho-dataset
W=/var/home/gabriel/Projects/chorinho-wt-custo-braco
host-spawn -no-pty podman run --rm --security-opt label=disable \
    --device nvidia.com/gpu=all --shm-size=2g \
    -v "$W":/app -v "$P/artefatos":/app/artefatos:ro -v "$P/data/saida":/app/data/saida \
    -w /app -e PYTHONPATH=/app \
    localhost/chorinho-maos:dev python SEU_SCRIPT.py
```

- O agente roda num distrobox **sem** `git` e `podman`: eles rodam no host por `host-spawn`.
- `--security-opt label=disable` é obrigatório (SELinux).
- **Grave tudo o que gerar em** `data/saida/maos/custo_braco/` (que, pelo comando acima, é a
  pasta principal). Não grave em outro lugar de `data/saida/`.
- **GPU**: todo uso passa pela trava. `prever_quadros` já usa uma (`_trava_gpu`). Se você criar
  outro caminho que use a GPU, envolva-o em `tab.comum.gpu.trava_gpu("maos", "estimativa")`. A
  trava deixa dividir a GPU se houver ≥ 3 GB livres. **Nunca** pare o container de outra
  sessão.

## 6. O que fazer, passo a passo

1. **O conjunto de teste**: os 40 quadros da rodada 1047, em `data/saida/maos/m47/` (o
   `indice.json` diz o PNG de cada quadro; `quadros/` tem os PNGs). Use **só** esses.
2. **A linha de base, com o código sem mudança** (na worktree recém-criada, antes de editar):
   - rode `hipoteses_na_pasta(MAOS_M47, indice, SAIDA_BASE)` com
     `SAIDA_BASE = data/saida/maos/custo_braco/base/`;
   - meça o tempo de cada etapa com `time.perf_counter()` ou `cProfile` (por exemplo, perfil de
     5 quadros com 1 par): quanto vai para a GPU, para a decodificação (CPU), para ler e
     gravar PNG, e para `aplicar_sinal_nut_v2`;
   - grave o tempo total e por etapa em `data/saida/maos/custo_braco/base/tempos.json`.
   - Confira também: os 22 JSONs gerados devem ser **iguais** aos de
     `data/saida/maos/m44/hipoteses/1047/`. Se não forem, **não pare**: anote a diferença no
     relatório e use a **sua** linha de base como referência daqui para frente.
3. **Escolha as mudanças pelo perfil**: comece pela etapa que mais gasta. Uma mudança por vez.
4. **Depois de cada mudança**: rode de novo nos 40 quadros, em
   `data/saida/maos/custo_braco/tentativa_N/`, e compare com a linha de base pelo critério da
   seção 7. Se não passar, **desfaça** essa mudança.
5. **Gate** na worktree antes de cada commit (no branch `maos/custo-braco`, nunca na `main`):

   ```bash
   host-spawn -no-pty podman run --rm --security-opt label=disable \
       -v "$W":/app -w /app -e PYTHONPATH=/app docker.io/library/chorinho:dev \
       sh -c 'ruff check --no-cache . && ruff format --no-cache --check . && pytest tests/ -q -p no:cacheprovider'
   ```

   Julgue pelo **código de saída** (0 = verde). Nunca `gate | tail && git commit`.
   Commit com `host-spawn -no-pty git -C "$W" add <arquivos por nome>` e
   `git -C "$W" commit -F arquivo_da_mensagem`, terminando a mensagem com
   `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (ou a linha que a sua sessão
   pedir). **Não** faça merge na `main`; a sessão principal revisa e faz.

## 7. Critérios de aceitação

**Resposta igual** (obrigatório, em cada tentativa):

- Para os 40 quadros e as 22 hipóteses, compare cada JSON novo com o da linha de base:
  - `achou`, `sinalizado`, `motivo`, `nut_suspeito` e os **números** dos trastes: **idênticos**;
  - toda coordenada (nut, pontos dos trastes, pontas das cordas): diferença **≤ 0,01 px**
    (o ideal é 0; com lotes na GPU pode haver diferença mínima de ponto flutuante);
  - os sinais `S1`, `S2`, `S3`: diferença ≤ 1e-4.
- E a decisão final: `cadeia_sem_tomada(ler_hipoteses(pasta), ler_faixas())` dá, quadro a
  quadro, a **mesma** hipótese entregue (ou o mesmo "sinalizado") que na linha de base: 40 de
  40.
- Escreva um script `data/saida/maos/custo_braco/comparar.py` que faz essas contas e imprime
  "X de 40 quadros iguais; maior diferença de coordenada Y px".

**Mais rápido** (o objetivo):

- Meça o tempo **com a GPU livre**: confira com `host-spawn -no-pty nvidia-smi` que não há
  outro processo grande, ou que `data/saida/gpu.lock` não existe. Rode linha de base e versão
  nova **uma logo depois da outra**, nas mesmas condições.
- **Meta**: ≥ 3× mais rápido no total das 22 hipóteses para os 40 quadros.
- **Aceitável**: ≥ 2×.

**Aceite da tarefa**: resposta igual (40 de 40) **e** ≥ 2× mais rápido, com gate verde no
branch, e o relatório da seção 9.

## 8. Como não se perder (regras contra loop)

- **Meça antes de otimizar.** Não mude nada antes do perfil do passo 6.2.
- **Uma mudança por vez**, sempre comparando com a linha de base. Se uma mudança quebrar a
  igualdade e você não achar o motivo em **2 tentativas**, desfaça e passe para a próxima ideia.
- **No máximo 5 mudanças** no total. Depois da 5ª, pare e entregue.
- **Se depois de 2 mudanças boas o ganho total for < 1,5×**, pare e entregue o perfil e o que
  aprendeu: o gargalo pode estar onde a regra não deixa mexer.
- **Um erro igual duas vezes** (mesma mensagem): pare, escreva no relatório, entregue.
- **Não mexa na resposta.** Se achar que tirar hipóteses ou baixar a resolução resolveria,
  escreva como sugestão, sem medir.
- **Não fique medindo tempo com a GPU ocupada** e tirando conclusão: o número não vale.

## 9. Quando parar e o que entregar

Pare quando:
- o aceite da seção 7 estiver cumprido; **ou**
- bater uma das regras da seção 8; **ou**
- passar de 8 horas.

Entregue `data/saida/maos/custo_braco/relatorio.md`, em português simples:

```text
# Custo da cadeia do braço — relatório
## Resposta curta (3 linhas: quanto mais rápido, se a resposta ficou igual)
## O perfil da linha de base (tabela: etapa, segundos, %)
## As mudanças (uma linha cada: o que, ganho, igualdade "X de 40", mantida ou desfeita)
## Números finais (tempo antes e depois, com a GPU livre; maior diferença de coordenada)
## Branch e commits (nomes e hashes)
## O que não deu certo / sugestões que mudariam a resposta (sem medir)
```

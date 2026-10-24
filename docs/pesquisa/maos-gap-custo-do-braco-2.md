# Tarefa delegada — Custo do braço, parte 2: a decodificação de CPU, com a mesma resposta

**Data**: 2026-10-24. **Trilha**: mãos (rodadas `1NNN`). **Quem escreveu**: a sessão principal das
mãos. **Para quem**: um agente que **não** viu a conversa. Tudo o que você precisa está aqui; se
algo não estiver, **pare e pergunte ao dono**, não suponha.

**Tempo máximo**: 8 horas de trabalho. Passou disso, pare e entregue o que tem.

**Esta tarefa continua outra**: `docs/pesquisa/maos-gap-custo-do-braco.md`. Leia-a **inteira**
primeiro: o problema, o caminho do código, o que pode e o que não pode mudar (seção 4), o
comando do container, o critério de "resposta igual" (seção 7) e as regras contra loop (seção
8). **Tudo aquilo continua valendo aqui.** Leia também o relatório da parte 1:
`data/saida/maos/custo_braco/relatorio.md`.

---

## 1. Onde estamos

- A parte 1 rodou as 22 hipóteses em 4 processos: **2.054 s → 668 s (3,07×)** nos 40 quadros,
  com a resposta **idêntica byte a byte**. Branch `maos/custo-braco`, commits `1f3d8353` e
  `af297bf0`, worktree `/var/home/gabriel/Projects/worktree-tab/custo-braco`.
- O perfil da linha de base: **`decodificar_com_dados` é 93 % do tempo** (1.916 s em 4.168
  chamadas, ~0,46 s por chamada). A GPU é ~2 %. Cada processo continua gastando quase todo o
  tempo nessa função.
- Mesmo com 3×, o vídeo do MVP fica em ~11 h por hora de vídeo, e a meta do projeto é 2 h. Cada
  vez que essa função ficar mais rápida, todo o resto ganha junto.

## 2. A pergunta

Dá para deixar `decodificar_com_dados` (em `tab/maos/braco/localizador.py`) mais rápida **sem
mudar nenhum número que ela devolve**?

## 3. Onde trabalhar

- **A mesma worktree e o mesmo branch** da parte 1:
  `/var/home/gabriel/Projects/worktree-tab/custo-braco`, branch `maos/custo-braco`. Confira
  com `host-spawn -no-pty git -C /var/home/gabriel/Projects/worktree-tab/custo-braco log
  --oneline -3` que o topo é `af297bf0`. Se não for, pare e pergunte.
- O comando do container é o da parte 1, seção 5 (com `W` = essa worktree e os `artefatos/` e
  `data/saida/` da pasta principal montados). Grave em `data/saida/maos/custo_braco/parte2/`.

## 4. O que fazer

1. **Perfil de dentro da função**: rode `cProfile` (ou `time.perf_counter()` em volta de cada
   bloco) em **5 quadros × 1 par**, em série (`trabalhadores=1`), e descubra quais linhas ou
   sub-funções de `decodificar_com_dados` gastam o tempo. Grave
   `parte2/perfil_decodificar.txt`. **Não mude nada antes disto.**
2. **Linha de base da parte 2**: o código de `af297bf0` nos 40 quadros, 4 processos, GPU livre
   (confira `nvidia-smi` e `data/saida/gpu.lock`, como na parte 1). Grave em
   `parte2/base/`. É contra **ela** que você compara.
3. **Uma mudança por vez**, começando pelo bloco que mais gasta. O que costuma ajudar sem mudar
   número:
   - trocar laço Python por operação `numpy` **que faz a mesma conta na mesma ordem**;
   - não recalcular o que é igual entre a 1ª e a 2ª passada ou entre os extras;
   - evitar cópias de matriz grandes.
4. Depois de cada mudança: rode nos 40 quadros em `parte2/tentativa_N/` e compare com
   `parte2/base/` usando `data/saida/maos/custo_braco/comparar.py`, e **também byte a byte**
   (`diff -rq parte2/base parte2/tentativa_N`, ignorando `tempos.json`). Se não for igual,
   desfaça.
5. Gate na worktree antes de cada commit (comando na parte 1, seção 6.5), julgado pelo código de
   saída. Commit no branch `maos/custo-braco`, **nunca** na `main`.

## 5. O que **não** pode (além da lista da parte 1)

- **Dependência nova** (ex.: `numba`, `cython`): **não**. Precisa do aval do dono antes de
  instalar qualquer coisa (`AGENTS.md`, seção 8). Se achar que só assim dá, escreva como
  sugestão, com o ganho estimado, sem instalar.
- Mudar a ordem de soma em ponto flutuante de um jeito que mude o resultado (ex.: `np.sum` no
  lugar de uma soma em laço pode mudar o último bit). A régua é **byte a byte**; se mudar um
  bit, desfaça.
- Mudar a quantidade de processos padrão (4) ou o lote da GPU (1): já foram medidos na parte 1.

## 6. Critérios de aceitação

- **Resposta igual**: os 22 JSONs de hipótese **idênticos byte a byte** aos da `parte2/base/`, e
  40 de 40 decisões finais iguais (`comparar.py`).
- **Mais rápido**, medido com a GPU livre, base e versão nova uma logo depois da outra:
  - **meta**: ≥ 2× sobre a `parte2/base/` (668 s → ≤ 334 s);
  - **aceitável**: ≥ 1,5×.
- Gate verde no branch e o relatório da seção 8.

## 7. Como não se perder (regras contra loop)

- **Meça antes de otimizar** (passo 4.1).
- **No máximo 5 mudanças.** Depois da 5ª, pare e entregue.
- Se uma mudança quebrar a igualdade e você não achar o motivo em **2 tentativas**, desfaça e
  passe para a próxima.
- **Se depois de 2 mudanças mantidas o ganho for < 1,2×**, pare e entregue o perfil: o tempo
  pode estar numa conta que não se acelera sem mudar a resposta.
- **Um erro igual duas vezes**: pare, escreva e entregue.
- Não meça tempo com a GPU ou a CPU ocupadas por outra trilha (veja `nvidia-smi` e `top`): o
  número não vale.

## 8. Quando parar e o que entregar

Pare quando o aceite estiver cumprido, quando bater a seção 7, ou depois de 8 horas.

`data/saida/maos/custo_braco/parte2/relatorio.md`:

```text
# Custo do braço, parte 2 — relatório
## Resposta curta (3 linhas)
## O perfil de dentro de decodificar_com_dados (tabela: bloco, segundos, %)
## As mudanças (o que, ganho, igualdade byte a byte, mantida ou desfeita)
## Números finais (antes e depois, GPU livre)
## Branch e commits
## Sugestões que precisariam de dependência nova ou que mudariam a resposta (sem medir)
```

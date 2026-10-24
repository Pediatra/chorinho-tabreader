# Tarefa delegada — O perfil de capo e afinação por canal

**Data**: 2026-10-24. **Trilha**: tablatura (rodadas `0NNN`). **Quem escreveu**: a sessão
principal da tablatura. **Para quem**: um agente que **não** viu a conversa. Se algo não estiver
aqui, **pare e pergunte ao dono**; não suponha.

**Tempo máximo**: 4 horas de trabalho. Passou disso, pare e entregue o que tem.

**Continuação de**: `docs/pesquisa/tablatura-gap-afinacao-capo.md`. Leia antes o relatório
dela, `data/saida/tablatura/gap_afinacao/RELATORIO.md`, e os arquivos `leitura.json` e
`resumo.json` da mesma pasta.

---

## 1. O projeto em poucas linhas

- O projeto monta uma **base de dados de violão** a partir de vídeos-aula. O rótulo de cada
  nota (corda e casa) vem da **tablatura** da tela.
- A altura que soa é **corda solta + casa da tab + casa do capo** (decisão 1010). Sem o capo e
  a afinação, a nota da base fica com a altura errada, e a conferência com o som falha.
- Leia `AGENTS.md` (na raiz) **inteiro** antes de rodar qualquer coisa. As regras dele valem
  para você.
- Fale em **português simples**, com números e denominadores ("X de Y").
- Você **não commita**, **não grava em `data/gold/`** e **não muda `configs/` nem `tab/`**.
  Você entrega arquivos em `data/saida/tablatura/gap_afinacao_perfil/` e um relatório.

## 2. O que já se sabe

Do estudo anterior (53 vídeos de 19 canais):

- o capo vem escrito em 8 de 53 vídeos, e a afinação diferente da padrão em 4 de 53;
- cada canal escreve num lugar e de um jeito:
  - `kenneth acoustic`: no canto de cima à direita, o vídeo todo;
  - `shin izumi` e `guitarous`: "Capo fret N" acima do 1º sistema;
  - `kimny's guitar`: "Capo : N Flet", repetido por seção;
  - `lonelypicker`: embaixo da pauta;
  - `guitar dell ́arte` e `iwaki`: "⑥=D" acima da pauta;
  - `serge kottelat`: uma caixa "Drop-D Tuning…";
- **não escrever não prova afinação padrão**: no `shin izumi`, 2 de 5 vídeos com capo não
  escrevem nada.

## 3. As perguntas

**P1.** Para cada canal com tab (os 19 do estudo anterior), qual é o **perfil**: **onde** o
texto aparece (uma caixa em fração do quadro: x0, y0, x1, y1), **de que forma** (o modelo do
texto) e **quando** (o vídeo todo, a 1ª página, cada seção)?

**P2.** Com esse perfil, em **quantos vídeos de cada canal** o texto aparece? Conte numa amostra
maior: até 15 vídeos por canal.

**P3.** Quanto custa ao dono **confirmar o valor** (a casa do capo, a afinação) num mosaico de
recortes, um recorte por vídeo?

## 4. O que fazer

### Passo 1 — o perfil (até 1 h)

- A partir de `leitura.json` e dos quadros do estudo anterior (`inteiros/`, `zoom/`), escreva
  `perfil_proposto.json`:
  `{canal: {onde: [x0,y0,x1,y1], forma: "Capo fret N", quando: "video_todo"|"primeira_pagina"|"por_secao"|"desconhecido", fonte: [instantes olhados]}}`.
- Canal sem texto em nenhum dos vídeos olhados: `onde: null`, `quando: "desconhecido"`.
- Isto é uma **proposta** em `data/saida/`. **Não escreva em `configs/canais.yaml`.**

### Passo 2 — a contagem maior (até 2 h)

- Para cada canal com `onde` não nulo: sorteie até 15 vídeos com `random.Random(12)` do
  `data/saida/tablatura/censo/censo_cache.jsonl` (só `tablatura` verdadeiro). **Exclua** os 53
  vídeos já olhados (`gap_afinacao/amostra.json`).
- Para cada vídeo, recorte a caixa `onde` em 2 instantes: o 1º quadro com tab
  (`instantes[*].tab == true` no censo) e o meio do vídeo. Leia com `tab.comum.leitor.quadro_em`.
- Monte um **mosaico por canal** (`mosaicos/<canal>.jpg`) com os recortes, rotulados pelo vídeo
  e pelo instante.
- Olhe os mosaicos e grave `contagem.json`:
  `{canal, arquivo, instante, tem_texto: true|false|"duvida", texto_lido}`.
  O `texto_lido` é o que você lê a olho; quem confirma é o dono, depois.

### Passo 3 — o custo do dono (até 30 min)

- Conte os recortes com `tem_texto` verdadeiro ou "duvida". Estime o tempo do dono a ~5 s por
  recorte num mosaico (ele só confirma ou corrige o número).
- Estime também quanto seria o acervo todo: a fração com texto por canal, vezes os vídeos com
  tab daquele canal no censo.

## 5. O que NÃO fazer

- Não escreva em `configs/`, `tab/`, `tests/` nem em `data/gold/`. Não grave no acervo.
- Não instale OCR nem outra coisa. Não use a GPU. Não commite.
- Não sirva ferramenta nem peça nada ao dono: os mosaicos ficam para a sessão principal
  decidir.
- Não "adivinhe" o capo pelo braço do violão nem pelo som: aqui só conta o **texto da tela**.

## 6. Como rodar

A partir de `/var/home/gabriel/Projects/chorinho-dataset`:

```bash
host-spawn -no-pty -cwd $PWD sh -c 'export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock; docker compose -f compose.yaml -f compose.podman.yaml run --rm --no-deps -e CUDA_VISIBLE_DEVICES= chorinho python data/saida/tablatura/gap_afinacao_perfil/recortes.py' > data/saida/tablatura/gap_afinacao_perfil/recortes.log 2>&1
```

- **Horário do HD**: hoje (2026-10-24) a sessão principal lê o HD a partir das 22:00 (`data/saida/tablatura/recusa/r0217/rodar.log`). Não leia o acervo entre as 22:00 e a linha `FIM` desse log: duas leituras longas ao mesmo tempo dobram o tempo das duas.
- O HD do acervo é lento: leia os quadros **uma vez** e guarde os recortes.
- `ruff check --no-cache` e `ruff format --no-cache --check` nos seus scripts, no container.
- Crie `LEIAME.json` na pasta (`AGENTS.md` §10, regra 4).

## 7. Critérios de aceitação

- [ ] `perfil_proposto.json` com os 19 canais.
- [ ] `contagem.json` e os mosaicos, com até 15 vídeos por canal de perfil conhecido.
- [ ] Por canal: "texto em N de M vídeos", e o total.
- [ ] A estimativa do custo do dono (amostra e acervo).
- [ ] `RELATORIO.md`.

## 8. Anti-loop

- Mantenha `diario.md`: uma linha por tentativa.
- Uma caixa `onde` que não pega o texto em nenhum dos 15 vídeos: **não** a mexa mais de uma
  vez. Na segunda vez sem texto, marque o canal como "perfil não confirmado" e siga.
- O mesmo erro duas vezes: pare e relate.
- No máximo 3 tentativas por script.

## 9. Quando parar

Pare e entregue no **primeiro** destes:

1. Os critérios da seção 7 estão cumpridos.
2. Passaram as **4 horas**.
3. O HD não responde: entregue o passo 1 e o que tiver do passo 2.

## 10. O relatório final

Até 25 linhas, em português:

- P1: quantos canais têm perfil confirmado, e quais;
- P2: "texto em N de M" por canal e no total;
- P3: os minutos do dono na amostra e a estimativa no acervo;
- o que falhou e por quê;
- os caminhos.

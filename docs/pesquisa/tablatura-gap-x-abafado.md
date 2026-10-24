# Tarefa delegada — O X abafado que pega várias cordas: quanto o produto perde?

**Data**: 2026-10-23. **Trilha**: tablatura (rodadas `0NNN`). **Quem escreveu**: a sessão
principal da tablatura. **Para quem**: um agente que **não** viu a conversa. Tudo o que você
precisa está aqui. Se algo não estiver, **pare e pergunte ao dono**; não suponha.

**Tempo máximo**: 3 horas de trabalho. Passou disso, pare e entregue o relatório com o que tem.

---

## 1. O projeto em poucas linhas

- O projeto monta uma **base de dados de violão** a partir de vídeos-aula. Para cada nota
  tocada: corda, casa, **técnica de ataque**, instante, braço e mãos. O rótulo vem da
  **tablatura** da tela.
- Um modelo futuro vai aprender a sair de vídeo e som para tablatura. Toda nota **atacada** que
  some da base é um ataque que o modelo não aprende.
- Leia `AGENTS.md` (na raiz) **inteiro** antes de rodar qualquer coisa. As regras dele valem
  para você.
- Fale com o dono em **português simples**, com números e denominadores ("X de Y").
- Você **não commita** e **não grava em `data/gold/`**. Você entrega arquivos em
  `data/saida/tablatura/gap_x/` e um relatório.

## 2. O que é o X (nota abafada)

- Na tablatura, um **X** no lugar do número quer dizer que a corda é **tocada abafada**: a mão
  encosta, a corda não soa uma altura, mas **há ataque** (um som percussivo). Para a base, X é
  `ataque = "sim"` com `ataque_motivo = "x"`.
- Muitas vezes o X vem **empilhado**: vários X na mesma coluna, um por corda (por exemplo, as
  cordas 4, 5 e 6 abafadas juntas num rasgueado). O dono viu que **esses X empilhados nunca
  foram detectados**.
- A rede do produto tem a classe `"x"` entre os rótulos de casa (`tab/tablatura/leitura/
  detector_tab.py`: 26 classes, "0" a "24" e "x"). Ou seja, ela **pode** dizer X numa corda.
- No ajuste fino, as regiões de X do gabarito foram tratadas como "ignorar"
  (`data/saida/tablatura/n4/treinar_ft.py --ignorar-x`, função `regioes_x`). Por isso a rede
  pode nunca ter aprendido o X real.

## 3. Onde estão os X marcados pelo dono

O dono marca o X de dois jeitos na ferramenta do ouro:

1. **Nota com casa `"x"`**: uma nota comum, com `corda` e `casa == "x"`.
2. **Região de técnica `x`**: um retângulo sobre cordas e colunas, com `"tecnica": ["x"]`.
   - Campos: `cordas` ([corda_min, corda_max]) e `x_quadro` ([x_ini, x_fim], em px do quadro).
   - É o jeito comum para o X empilhado.

Contagem feita pela sessão principal em 2026-10-23:

| arquivo (conferência do dono) | regiões `x` | notas com casa `x` |
| --- | --- | --- |
| `data/gold/ouro_video/end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics.json` | 76 | 0 |
| `data/gold/ouro_video/tabroom_335_larry_carlton_fingerstyle_guitar.json` | 39 | 0 |
| `data/saida/tablatura/t82/ferramenta/conferencia_t82.json` | 9 | 4 |
| `data/saida/tablatura/t83/ferramenta/conferencia_t83.json` | 14 | 2 |
| `data/saida/tablatura/t84/ferramenta/conferencia_t84.json` | 21 | 6 |
| `data/saida/tablatura/t85/ferramenta/conferencia_t85.json` | 20 | 15 |
| `data/saida/tablatura/t86/ferramenta/conferencia_t86.json` | 18 | 1 |

Cada um desses arquivos tem `telas`, e cada tela tem `id`, `notas` (com `corda`, `casa` e
`x_quadro`), `regioes` e `conferida` (bool). **Só conte telas com `conferida: true`.**

**A leitura do produto antes do dono corrigir** está no `pre.json` da ferramenta de cada lote:
`data/saida/tablatura/t8N/ferramenta/pre.json`, com `telas[*].notas`. Para o EOB e o Room 335,
procure o `pre.json` em `data/saida/tablatura/ouro_video/<slug>/`. Se não achar, deixe esses
dois de fora e diga isso.

## 4. As perguntas

**P1.** Das cordas cobertas por uma região de X do dono, **em quantas o produto leu um X**
(nota com casa `"x"` naquela corda, dentro do x da região)? Em quantas leu um **número**
(errado)? Em quantas não leu **nada**?

**P2.** Quantas **notas atacadas** a base perde hoje por causa disso? Conte uma por corda
coberta por cada região, e diga se é por coluna ou por região (seção 5).

**P3.** Dá para montar um **palpite pré-preenchido**, uma nota `x` por corda e coluna em cada
região, para o dono só confirmar? Quantas notas ele teria de conferir, e em quanto tempo?

## 5. O que fazer

### Passo 1 — a medida (até 1,5 h)

Escreva `data/saida/tablatura/gap_x/medir.py`. Para cada arquivo da tabela da seção 3 e cada
tela conferida com região `x`:

1. Para cada região, para cada corda de `corda_min` a `corda_max`:
   - "**X lido**": o `pre.json` tem uma nota naquela corda, com `casa == "x"` e `x_quadro`
     dentro de `[x_ini − 0,5·passo, x_fim + 0,5·passo]`;
   - "**número lido**": tem uma nota com casa numérica nesse intervalo;
   - "**nada**": não tem nenhuma.
   - O `passo` da tela está no `pre.json` (`telas[*].passo`). Se faltar, use 20 px e diga
     isso.
2. **Quantas colunas a região cobre**: estime por `round((x_fim − x_ini) / passo)`, no mínimo 1.
   Grave também a largura em passos, para a sessão principal conferir.
3. Faça o mesmo para as **notas com casa `x`** que o dono digitou: o `pre.json` tinha X ali?
4. Grave `medida.json` (uma linha por região e por corda) e `resumo.json` (os totais por
   arquivo e no geral: X lido, número lido, nada).

### Passo 2 — as imagens (até 30 min; no máximo 10 imagens)

- Sorteie (`random.Random(5)`) **10 regiões** com resultado "nada" ou "número lido".
- Para cada uma, grave o recorte do quadro com a região desenhada em vermelho:
  `exemplos/<arquivo>_t<tela>_r<k>.png`.
  - O instante do quadro está no `pre.json` (`telas[*].quadro_ref_s`) e o vídeo no `video` do
    arquivo. Para os lotes T8.x, o vídeo de cada tela está em `ferramenta/indice.json`.
  - Leia com `tab.comum.leitor.quadro_em`.
- Olhe as 10 e escreva uma linha para cada em `exemplos/notas.md`: como o X está desenhado
  (letra "x" ou "X", tamanho, cor) e se a região do dono cobre mesmo um X.

### Passo 3 — o palpite (até 1 h; só o arquivo, nada é servido ao dono)

Escreva `palpite.py`, que grava `palpite_x.json`:

```json
{"arquivo": "...", "tela": 7, "regiao": 3,
 "notas": [{"corda": 4, "casa": "x", "x_quadro": 812.0, "origem": "palpite_regiao_x"}]}
```

- Uma nota por corda e por coluna dentro de cada região de X conferida.
- O x de cada coluna: use os x das notas **do dono** (no arquivo de conferência) que caem
  dentro da região em outras cordas. Se não houver, use o centro de cada fatia de largura
  `passo`.
- Não crie palpite numa corda em que o dono já tem uma nota naquele x (até 0,5 passo).
- Conte o total de notas do palpite e estime o tempo do dono: ele confere ~1.300 notas
  pré-preenchidas em ~35 min, mas palpite novo pede mais atenção, então use 3 vezes isso.

## 6. O que NÃO fazer

- **Não sirva a ferramenta ao dono, nem peça rótulo a ele.** O palpite é um arquivo. Quem decide
  se e quando ele vai ao dono é a sessão principal.
- **Não grave** nos arquivos de conferência, em `data/gold/` nem no acervo.
- Não mude `tab/`, o treino nem o gerador. **Não treine** nada.
- Não use a GPU. Não instale nada. Não commite.
- Não "corrija" região do dono que pareça errada. Anote-a em `exemplos/notas.md` e deixe como
  está.

## 7. Como rodar

A partir de `/var/home/gabriel/Projects/chorinho-dataset`:

```bash
host-spawn -no-pty -cwd $PWD sh -c 'export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock; docker compose -f compose.yaml -f compose.podman.yaml run --rm --no-deps -e CUDA_VISIBLE_DEVICES= chorinho python data/saida/tablatura/gap_x/medir.py' > data/saida/tablatura/gap_x/medir.log 2>&1
```

- `ruff check --no-cache` e `ruff format --no-cache` no container, nos seus scripts.
- Código no padrão do projeto (`main()`, docstring Google em português, imports no topo).
- Crie `LEIAME.json` na pasta (`AGENTS.md` §10, regra 4).

## 8. Critérios de aceitação (a sessão principal vai conferir)

- [ ] `resumo.json` com P1 por arquivo e no total, em "X de Y cordas cobertas".
- [ ] A soma das regiões no `medida.json` bate com a tabela da seção 3 (só telas conferidas).
      Se não bater, explique a diferença.
- [ ] As 10 imagens de exemplo e o `notas.md`.
- [ ] `palpite_x.json`, com o total de notas e a estimativa de minutos do dono.
- [ ] `RELATORIO.md` com P1, P2 e P3.

## 9. Como não se perder (anti-loop)

- Mantenha `diario.md`: uma linha por tentativa.
- Se o formato de um arquivo não for o descrito na seção 3, **imprima as chaves** e adapte só a
  leitura. Se ainda não fizer sentido, deixe aquele arquivo de fora e diga isso. Não adivinhe
  o significado de um campo.
- A tolerância de 0,5 passo é fixa. Não teste outras para melhorar o número.
- **No máximo 3 tentativas** por script. Mesmo erro duas vezes: pare e relate.
- Não olhe mais do que as 10 imagens.

## 10. Quando parar

Pare e entregue quando acontecer o **primeiro** destes:

1. Os critérios da seção 8 estão cumpridos.
2. Passaram as **3 horas**.
3. Nenhum `pre.json` tem a leitura do produto (as notas não estão lá). Relate e pare.
4. O HD não responde no passo 2. Entregue os passos 1 e 3 sem as imagens.

## 11. O relatório final

Até 25 linhas, em português:

- P1: "das N cordas cobertas por X, o produto leu X em A, número em B e nada em C";
- P2: quantas notas atacadas a base perde;
- P3: o tamanho do palpite e o custo para o dono;
- o que as 10 imagens mostram;
- o que falhou e por quê;
- os caminhos dos arquivos.

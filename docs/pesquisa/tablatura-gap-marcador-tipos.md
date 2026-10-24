# Tarefa delegada — Os tipos de marcador que o produto não lê

**Data**: 2026-10-24. **Trilha**: tablatura (rodadas `0NNN`). **Quem escreveu**: a sessão
principal da tablatura. **Para quem**: um agente que **não** viu a conversa. Se algo não estiver
aqui, **pare e pergunte ao dono**; não suponha.

**Tempo máximo**: 5 horas de trabalho. Passou disso, pare e entregue o que tem.

**Continuação de**: `docs/pesquisa/tablatura-gap-tempo-marcador.md`. Leia o relatório dela
antes de começar: `data/saida/tablatura/gap_tempo/RELATORIO.md`, `eob/diagnostico.md` e
`atraso.json`.

---

## 1. O projeto em poucas linhas

- O projeto monta uma **base de dados de violão** a partir de vídeos-aula. O rótulo de cada
  nota vem da **tablatura** da tela.
- O **tempo** de cada nota (`t_ini`) vem do **marcador** da tela: uma faixa que passa, uma
  linha, um bloco colorido ou uma cor no algarismo, que mostra o que está sendo tocado.
- Leia `AGENTS.md` (na raiz) **inteiro** antes de rodar qualquer coisa. As regras dele valem
  para você.
- Fale em **português simples**, com números e denominadores ("X de Y").
- Você **não commita**, **não grava em `data/gold/`** e **não muda nada em `tab/`**. Você
  entrega arquivos em `data/saida/tablatura/gap_marcador/` e um relatório.

## 2. O que já se sabe

- Nos 35 vídeos da `r2021` (`data/saida/audio/r2021/produtos/*.json`), **só 9 têm `t_ini`**.
  Os outros 26 ficaram sem tempo:
  - 14 com o motivo "coerência abaixo de 0,9 em todos";
  - 12 com "nenhum observador com trocas e cobertura suficientes".
- O motivo de cada vídeo está no produto, nas `exibicoes` (procure o campo do motivo de
  recusa). Imprima as chaves de um produto antes de ler.
- O código do marcador:
  - `tab/tablatura/leitura/cursor.py`: `detectar_cursor` procura uma banda vertical estreita.
    O limite é `largura_max_frac = 0.06` (6 % da largura);
  - `tab/tablatura/produto/destaque.py`: os observadores (`posicao`, `cor`, `cor_acende`) e a
    coerência.
- **No *End of Beginning*** (`eob/`), o marcador é um **bloco amarelo que cobre o compasso**
  e uma **linha ciano fina** (3–5 px) que anda dentro dele. O algarismo não muda de cor.
  - Hipótese do estudo anterior: o detector pega o bloco (o maior grupo de cor), recusa-o por
    ser largo demais, e nunca olha a linha fina.

## 3. As perguntas

**P1.** Que **tipo de marcador** tem cada um dos 26 vídeos sem tempo? Use estes tipos, e
"outro" com uma descrição curta quando nenhum servir:

| tipo | como é |
| --- | --- |
| `linha` | uma linha ou faixa estreita que anda |
| `bloco_compasso` | um bloco colorido cobre o compasso inteiro (com ou sem linha dentro) |
| `bloco_coluna` | um bloco ou realce cobre só a coluna tocada |
| `cor_algarismo` | o algarismo tocado muda de cor |
| `rolagem` | a tab rola de lado e o ponto tocado fica fixo |
| `sem_marcador` | nada na tela indica o que está tocando |

**P2.** Para o tipo **mais comum** entre os 26: um protótipo fora do produto acha o `t_ini`
de cada coluna? E o atraso som − marcador dele fica estável?

## 4. O que fazer

### Passo 1 — o censo dos tipos (até 2 h)

1. Para cada um dos 26 vídeos, escolha 2 exibições com `random.Random(24)` e grave 3 quadros
   de cada uma (no início, no meio e no fim da exibição). Use `tab.comum.leitor.quadro_em`.
2. Grave uma **folha por vídeo** em `gap_marcador/folhas/<slug>.jpg`, com os 6 quadros e o
   painel da tab recortado e ampliado 2×.
3. Olhe as folhas e grave `tipos.json`: `{slug, canal, tipo, descricao, quadros_olhados}`.
   Compare os quadros do mesmo instante de exibição: o que **muda** entre o início e o fim é o
   marcador.
4. Grave `resumo_tipos.json` com a contagem por tipo e por motivo de recusa.

### Passo 2 — o protótipo para o tipo mais comum (até 2,5 h)

- Escreva `gap_marcador/prototipo.py`. Ele **não importa nada privado** (`_f`) e **não muda
  `tab/`**. Pode importar funções públicas de `tab.tablatura.leitura` e de `tab.comum`.
- Para `bloco_compasso` com linha fina, a ideia de partida é:
  1. ache o bloco (o maior grupo de cor saturada no painel);
  2. dentro dele, procure a coluna vertical mais diferente do resto do bloco (a linha);
  3. o x dessa linha ao longo do tempo dá o instante de cada coluna da tab (quando a linha passa
     pelo x da coluna).
- Para outro tipo, escreva em `diario.md` a ideia antes de codar e siga a mesma lógica: achar o
  **x tocado** quadro a quadro.
- Grave, por vídeo do tipo, `t_ini_<slug>.json`: `[{coluna_x, t_ini}]` por exibição.
- **A medida**: rode o `data/saida/tablatura/gap_tempo/atraso.py` (copie-o para
  `gap_marcador/atraso_prototipo.py` e troque só a fonte de `t_ini`). Use as mesmas regras: a
  janela −0,4/+0,6 s, a estabilidade (fração dentro de ±0,15 s da mediana) e os deslocamentos.
- **O teste de sanidade**: rode o protótipo também no vídeo do MVP (*retrato brasileiro*,
  caminho em `data/saida/tablatura/gap_tempo/sanidade_mvp.json`) **só se** ele for do mesmo
  tipo. Se não for, escreva isso.

## 5. O que NÃO fazer

- Não mude `tab/`, `tests/`, `configs/` nem o produto. O protótipo vive em `gap_marcador/`.
- Não grave em `data/gold/` nem no acervo. Não use a GPU. Não instale nada. Não commite.
- Não mude a janela nem a régua de ±0,15 s para melhorar o número.
- Não olhe mais de 6 quadros por vídeo no passo 1.

## 6. Como rodar

A partir de `/var/home/gabriel/Projects/chorinho-dataset`:

```bash
host-spawn -no-pty -cwd $PWD sh -c 'export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock; docker compose -f compose.yaml -f compose.podman.yaml run --rm --no-deps -e CUDA_VISIBLE_DEVICES= chorinho python data/saida/tablatura/gap_marcador/prototipo.py' > data/saida/tablatura/gap_marcador/prototipo.log 2>&1
```

- **Horário do HD**: hoje (2026-10-24) a sessão principal lê o HD a partir das 22:00 (`data/saida/tablatura/recusa/r0217/rodar.log`). Não leia o acervo entre as 22:00 e a linha `FIM` desse log: duas leituras longas ao mesmo tempo dobram o tempo das duas.
- O `atraso.py` usa matplotlib, que só está na imagem `localhost/chorinho-audio:dev`. Veja no
  `gap_tempo/LEIAME.json` o comando que o estudo anterior usou.
- `ruff check --no-cache` e `ruff format --no-cache --check` nos seus scripts, no container.
- Crie `LEIAME.json` na pasta (`AGENTS.md` §10, regra 4).

## 7. Critérios de aceitação

- [ ] `tipos.json` com os 26 vídeos, cada um com tipo e descrição, e `resumo_tipos.json`.
- [ ] Para o tipo mais comum: `t_ini` do protótipo em pelo menos 3 vídeos desse tipo, ou a
      explicação de por que não deu.
- [ ] A estabilidade do atraso por vídeo, com a mesma régua do estudo anterior.
- [ ] `RELATORIO.md`.

**A régua de sucesso do protótipo** (fixa): estabilidade ≥ 0,80 em pelo menos 2 de cada 3
vídeos do tipo. Abaixo disso, o protótipo **não** serve, e você diz isso.

## 8. Anti-loop

- Mantenha `diario.md`: uma linha por tentativa, com o que mudou e o número.
- **No máximo 3 versões** do protótipo. Na terceira sem chegar na régua, pare e relate.
- O mesmo erro duas vezes: pare e relate.
- Um vídeo em que o quadro não abre: anote e siga; não tente outro instante mais de uma vez.

## 9. Quando parar

Pare e entregue no **primeiro** destes:

1. Os critérios da seção 7 estão cumpridos.
2. Passaram as **5 horas**.
3. Nenhum dos 26 é do mesmo tipo de outro (não há tipo comum). Entregue só o passo 1.
4. O HD não responde: entregue o que tem.

## 10. O relatório final

Até 25 linhas, em português:

- P1: a tabela de tipos, "N de 26";
- P2: o tipo escolhido, quantos vídeos, e a estabilidade de cada um;
- se o MVP entrou no teste de sanidade, e o número;
- o que falhou e por quê;
- os caminhos.

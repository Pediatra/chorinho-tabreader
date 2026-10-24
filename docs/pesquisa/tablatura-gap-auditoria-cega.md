# Tarefa delegada — Auditoria cega: o pré-preenchimento esconde erros do gabarito?

**Data**: 2026-10-23. **Trilha**: tablatura (rodadas `0NNN`). **Quem escreveu**: a sessão
principal da tablatura. **Para quem**: um agente que **não** viu a conversa. Tudo o que você
precisa está aqui. Se algo não estiver, **pare e pergunte ao dono**; não suponha.

**Tempo máximo**: 4 horas do seu trabalho, mais **no máximo 40 minutos do dono**. Passou
disso, pare e entregue o relatório com o que tem.

---

## 1. O projeto em poucas linhas

- O projeto monta uma **base de dados de violão** a partir de vídeos-aula. O rótulo (corda e
  casa de cada nota) vem da **tablatura** da tela.
- A qualidade da leitura é medida contra **gabaritos**: telas que o dono conferiu nota a nota.
- Leia `AGENTS.md` (na raiz) **inteiro** antes de rodar qualquer coisa. As seções 8 ("O dono e
  o gabarito") e 6 ("Como uma rodada funciona") são as mais importantes para esta tarefa.
- Fale com o dono em **português simples**, com números e denominadores ("X de Y").
- Você **não commita** e **não grava em `data/gold/`**. Você entrega arquivos em
  `data/saida/tablatura/gap_auditoria/` e um relatório.

## 2. O problema (o viés que esta tarefa mede)

Os gabaritos recentes (T8.2 a T8.6) nasceram assim:

1. o **produto** lê a tela e **pré-preenche** as notas na ferramenta;
2. o **dono** olha e **corrige** o que estiver errado;
3. o resultado vira o gabarito, e o produto é medido contra ele.

O risco: um erro do produto que **parece plausível** (um 8 lido como 6, uma nota inventada que
cabe na música) pode passar pelo olho do dono, porque ele já vê o número escrito. Aí o mesmo
erro está no produto e no gabarito, e **a medida sai otimista**. Hoje, na T8.5 e na T8.6, o
produto erra a casa em 0,8 a 1,3 % e inventa 0,2 a 0,8 % das notas, **medido assim**.

A pergunta é: **quanto desse número é real?**

A forma de medir é uma **auditoria cega**: o dono marca algumas telas **do zero**, sem ver
nenhuma leitura, e a comparação é feita depois.

## 3. O desenho (fixo; não mude sem a sessão principal)

**A amostra: 8 telas.**
- 4 da T8.5 e 4 da T8.6. As duas são lotes que o dono **já conferiu** com o pré-preenchimento:
  - T8.5: `data/saida/tablatura/t85/ferramenta/conferencia_t85.json`;
  - T8.6: `data/saida/tablatura/t86/ferramenta/conferencia_t86.json`.
- Sorteio com `random.Random(21)`, entre as telas com `conferida: true` e com 20 a 60 notas.
- Ficam fora as telas 5 e 27 da T8.5 e as telas 3 e 28 da T8.6: tiveram problema de painel.
- No máximo 1 tela por vídeo. O vídeo de cada tela está em `ferramenta/indice.json` do lote.
- As 8 telas devem ter, somadas, ~250 a 350 notas. Se passar de 400, troque a tela maior pela
  próxima do sorteio.

**As três versões de cada tela:**
- **C (conferida)**: as notas do arquivo de conferência, o que o dono aprovou vendo o
  pré-preenchimento;
- **P (produto)**: as notas do `pre.json` do lote (`ferramenta/pre.json`, `telas[*].notas`),
  a leitura do produto antes do dono;
- **B (cega)**: as notas que o dono vai marcar agora, **sem ver P nem C**.

**O que se compara:**
- B × C mede o **viés do pré-preenchimento**, a pergunta principal.
- B × P mede o erro do produto contra um gabarito cego.

**Como casar duas notas**: mesma `corda` e |x_quadro_a − x_quadro_b| ≤ 0,5 × `passo` da tela.
A casa conta como igual quando as strings são iguais (`"x"` também). É a regra da medida
oficial (`tab.tablatura.ouro.avaliar_video.casar_notas`). **Leia essa função e use-a** se ela
servir; se não servir, reproduza a regra.

## 4. O que já existe

- **A ferramenta de rotular**: `python -m tab.tablatura.ouro.ouro_video servir --pasta <dir>
  --ouro <saida.json> --porta <p> --host 0.0.0.0`. O `<dir>` precisa de:
  - um `pre.json` (veja `data/saida/tablatura/t85/ferramenta/pre.json` como modelo):
    - `telas` com `id`, `arquivo` (`telas/NNN.png`), `quadro_ref_s`, `painel`, `escala`,
      `passo`, `linhas_y`, `notas`…;
    - `estado_inicial` com `telas[*].notas`;
  - a pasta `telas/` com as imagens.
- A ferramenta **grava a cada clique** no `<saida.json>`. Por isso a regra de `AGENTS.md` §8:
  **teste a ferramenta numa cópia, nunca no arquivo que o dono vai usar.**
- **Atalhos da ferramenta** (já existem):
  - **X**: tela conferida;
  - **Tab / Shift+Tab**: próxima / anterior;
  - **Espaço**: desfaz.
  - O modo ataque (**A**) **não entra** nesta tarefa.

## 5. O que fazer

### Passo 1 — o material cego (até 1,5 h)

Escreva `data/saida/tablatura/gap_auditoria/montar.py`. Ele:

1. sorteia as 8 telas (seção 3) e grava `amostra.json`: lote, id original, vídeo e número de
   notas;
2. cria `data/saida/tablatura/gap_auditoria/ferramenta/`:
   - copia as 8 imagens (`telas/NNN.png`) dos lotes, renumeradas de `001` a `008`;
   - escreve um `pre.json` com as 8 telas, **com `notas: []` em `telas` e em
     `estado_inicial.telas`** (a ferramenta abre vazia), e o resto dos campos copiado do
     original;
   - escreve `mapa.json`: id novo → (lote, id original);
3. não copia nada de `conferencia_*.json` para a pasta da ferramenta.

**Teste numa cópia** (obrigatório):

1. Copie `ferramenta/` para `ferramenta_teste/`.
2. Suba a ferramenta apontando para ela, com `--ouro ferramenta_teste/teste.json` e
   `--porta 8139`. Em `podman run` / `compose run`, publique a porta com
   `-p 127.0.0.1:8139:8139`.
3. Confira com `curl -s http://127.0.0.1:8139/ | head` que a página abre, e veja no log se há
   erro.
4. Pare o container de teste (só o seu). Apague `ferramenta_teste/`.
5. Se a ferramenta não abrir com as notas vazias, **pare e relate**. Não mude o código da
   ferramenta.

### Passo 2 — pedir ao dono (você só pergunta)

Mande ao dono uma mensagem **curta**, no formato abaixo, e **espere a resposta**. Sem o "sim"
dele, a tarefa termina aqui, com o relatório.

> Para medir se o pré-preenchimento esconde erros do gabarito, preciso que você marque **8 telas
> do zero** (umas 300 notas), sem nenhuma leitura pré-preenchida. São telas que você já
> conferiu na T8.5 e na T8.6, mas não vou mostrar nada do que foi marcado. Deve levar de 25 a
> 40 minutos. Marque só corda e casa (X para nota abafada), sem regiões de técnica, e aperte X
> em cada tela pronta. Posso subir a ferramenta em http://127.0.0.1:8129/?

Se ele disser sim, suba a ferramenta de verdade:
- `--pasta data/saida/tablatura/gap_auditoria/ferramenta`;
- `--ouro data/saida/tablatura/gap_auditoria/ferramenta/cega.json`;
- `--porta 8129`.

Mantenha o processo vivo como job de fundo gerenciado (o log da ferramenta avisa isso). **Não
reinicie a ferramenta** enquanto o dono marca. Se precisar reiniciar, peça a ele antes.

### Passo 3 — a comparação (até 1 h, depois que o dono disser que terminou)

Escreva `comparar.py`. Ele lê `cega.json` (só as telas com `conferida: true`), `mapa.json`, as
conferências e os `pre.json` originais, e para cada tela e no total calcula:

| comparação | o que contar |
| --- | --- |
| B × C | notas só em B (o dono achou agora e não tinha visto antes), notas só em C (aprovou antes e não marcou agora), casa diferente entre as casadas, e a concordância = casadas com casa igual / notas de B |
| B × P | o mesmo: as inventadas do produto (só em P), as perdidas (só em B) e a casa errada |
| P × C | o mesmo, para comparar com o número oficial |

Grave `comparacao.json` e uma **lista das divergências B × C**, com tela, corda, x, casa em B e
casa em C, em `divergencias.json`.

- Para cada divergência, grave o recorte da tela (a imagem `telas/NNN.png` da ferramenta) com a
  nota circulada: `divergencias/<tela>_<k>.png`.
- **No máximo 30 recortes.**

**Não decida quem está certo.** A divergência B × C vai para o dono olhar, num passo que a
sessão principal monta.

## 6. Critérios de aceitação

- [ ] `amostra.json` com as 8 telas e a soma de notas.
- [ ] O teste da ferramenta na cópia foi feito e registrado no `diario.md`, com o comando e o
      resultado.
- [ ] A pergunta ao dono foi feita **uma vez**, no formato da seção 5, e a resposta está
      registrada.
- [ ] Se o dono marcou: `comparacao.json`, `divergencias.json` e os recortes.
- [ ] `RELATORIO.md` com a concordância B × C, os erros do produto medidos contra B e contra C
      lado a lado, e o número de divergências que precisam de decisão do dono.

## 7. Como ler o resultado (para o relatório)

- Se **B × C concorda em ≥ 99 %** das notas, o pré-preenchimento não esconde erro relevante, e
  os números oficiais valem.
- Se **concorda em 97 a 99 %**, existe viés. Relate de que tipo é a maioria: nota inventada
  aprovada, ou casa trocada aprovada.
- Se **concorda em menos de 97 %**, o viés é grande, e os números de leitura do projeto estão
  otimistas. Diga isso com clareza, com os números.
- Em todo caso, cuidado: o dono marcando do zero também erra. Uma divergência **não prova** que
  C está errado. Por isso as divergências vão para ele decidir.
- Com 8 telas e ~300 notas, 1 nota = ~0,3 %. **Diga isso no relatório**: é uma estimativa, não
  um número fino.

## 8. O que NÃO fazer

- **Nunca mostre ao dono as notas de P ou de C** antes ou durante a marcação cega.
- Não grave em `conferencia_*.json`, em `data/gold/` nem no acervo. Não commite.
- Não mude o código da ferramenta (`tab/tablatura/ouro/ouro_video.py`).
- Não peça ao dono mais do que as 8 telas. Não peça o modo ataque.
- Não use a GPU. Não instale nada.
- Não pare nenhum container que não seja o seu. Outros containers do projeto (portas 8121 a
  8160, e o "maos-gabarito") são de outras trilhas.

## 9. Como rodar

A partir de `/var/home/gabriel/Projects/chorinho-dataset`:

```bash
host-spawn -no-pty -cwd $PWD sh -c 'export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock; docker compose -f compose.yaml -f compose.podman.yaml run --rm --no-deps -e CUDA_VISIBLE_DEVICES= chorinho python data/saida/tablatura/gap_auditoria/montar.py' > data/saida/tablatura/gap_auditoria/montar.log 2>&1
```

A ferramenta, para o dono:

```bash
host-spawn -no-pty -cwd $PWD sh -c 'export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock; docker compose -f compose.yaml -f compose.podman.yaml run --rm --no-deps -e CUDA_VISIBLE_DEVICES= -p 127.0.0.1:8129:8129 chorinho python -m tab.tablatura.ouro.ouro_video servir --pasta data/saida/tablatura/gap_auditoria/ferramenta --ouro data/saida/tablatura/gap_auditoria/ferramenta/cega.json --porta 8129 --host 0.0.0.0' > data/saida/tablatura/gap_auditoria/servir.log 2>&1
```

- `ruff check --no-cache` e `ruff format --no-cache` nos seus scripts.
- Código no padrão do projeto (`main()`, docstring Google em português, imports no topo).
- Crie `LEIAME.json` na pasta (`AGENTS.md` §10, regra 4).

## 10. Como não se perder (anti-loop)

- Mantenha `diario.md`: uma linha por tentativa.
- Se o `pre.json` com notas vazias não abrir na ferramenta, tente **uma** alternativa: deixar
  só `estado_inicial.telas[*].notas` vazio e `telas[*].notas` como no original. Ela só é
  aceitável se você confirmar no navegador que nenhuma nota aparece. Se não der, **pare e
  relate**.
- Enquanto espera o dono, **não fique checando** o arquivo em loop. Ele avisa quando termina.
- **No máximo 3 tentativas** por script. Mesmo erro duas vezes: pare e relate.

## 11. Quando parar

Pare e entregue quando acontecer o **primeiro** destes:

1. Os critérios da seção 6 estão cumpridos.
2. O dono disse **não**, ou não respondeu. Entregue o material pronto e o relatório sem a
   comparação.
3. A ferramenta não abre vazia (passo 1). Relate.
4. Passaram as 4 horas do seu trabalho, ou 40 minutos do dono marcando. Pare a marcação onde
   estiver e compare só as telas conferidas.

## 12. O relatório final

Até 25 linhas, em português:

- a concordância B × C, em "X de Y notas", e de que tipo são as divergências;
- o erro do produto contra B e contra C, lado a lado (inventadas, perdidas, casa);
- a leitura (seção 7);
- quantas divergências esperam decisão do dono;
- o tempo que o dono gastou;
- o que falhou e por quê;
- os caminhos dos arquivos.

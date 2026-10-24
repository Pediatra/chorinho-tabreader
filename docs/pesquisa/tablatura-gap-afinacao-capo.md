# Tarefa delegada — Quantos vídeos escrevem a afinação ou o capotraste na tela?

**Data**: 2026-10-23. **Trilha**: tablatura (rodadas `0NNN`). **Quem escreveu**: a sessão
principal da tablatura. **Para quem**: um agente que **não** viu a conversa. Tudo o que você
precisa está aqui. Se algo não estiver, **pare e pergunte ao dono**; não suponha.

**Tempo máximo**: 4 horas de trabalho. Passou disso, pare e entregue o relatório com o que tem.

---

## 1. O projeto em poucas linhas

- O projeto monta uma **base de dados de violão** a partir de vídeos-aula (o **acervo**: 4.096
  vídeos em 21 canais, num HD externo, **somente leitura**).
- Para cada nota tocada, a base guarda a corda, a casa e a técnica (lidas da **tablatura** que
  aparece na tela), o instante em que ela soa, o braço do violão e as mãos.
- Um modelo futuro vai aprender a sair de **vídeo e som** para tablatura. Por isso o som e a
  tablatura precisam bater.
- Leia `AGENTS.md` (na raiz) **inteiro** antes de rodar qualquer coisa. As regras dele valem
  para você.
- Fale com o dono em **português simples**, com números e denominadores ("X de Y").
- Você **não commita** e **não grava em `data/gold/`**. Você entrega arquivos em
  `data/saida/tablatura/gap_afinacao/` e um relatório. A sessão principal revisa e decide.

## 2. O problema (por que esta tarefa existe)

A tablatura diz **corda e casa**. A **nota que soa** depende também de duas coisas que a
tablatura não mostra nos números:

1. **O capotraste** (capo): uma braçadeira presa numa casa. Com capo na casa 3, a "casa 0" da
   tablatura soa como a casa 3 do violão.
2. **A afinação**: a padrão é E A D G B E (MIDI das cordas soltas, da 1 à 6: 64, 59, 55, 50,
   45, 40, em `tab/comum/violao.py::AFINACAO_MIDI`). Muitos vídeos usam outra:
   - "Drop D" ou "⑥=D": a corda 6 desce 2 semitons;
   - "Whole Step Down" (um tom abaixo): todas as cordas descem 2 semitons;
   - "Half Step Down" (meio tom abaixo): todas descem 1 semitom;
   - afinações abertas (DADGAD, Open G…).

A física é: **altura que soa = corda solta (na afinação do vídeo) + casa da tab + casa do capo**.

Se a base não souber o capo e a afinação, o modelo futuro aprende **som e tablatura
desencontrados**, sem aviso, no vídeo inteiro. É um erro sistemático, o pior tipo.

Muitos vídeos **escrevem** isso na tela. Exemplos que a sessão principal já viu nos quadros
(não são todos, e você deve conferir):

| canal | o que aparece | onde |
| --- | --- | --- |
| kenneth acoustic | "Tuning: Standard / Capo: Fret 3" | canto superior direito, o vídeo todo |
| boywithuke (no canal kenneth acoustic) | "Tuning: Standard / Capo: Fret 4" e "Capo fret 4" no 1º sistema | canto superior direito e começo da tab |
| shin izumi | "Capo fret 4", "♩= 78", "4/4" | começo da partitura, terço de baixo do quadro |
| iwaki | "⑥=D" (sexta corda em ré) | cabeçalho da tablatura |
| vvxofingerstyletab | "CAPO FRET 1" na lateral da tablatura | à esquerda do painel |
| um vídeo da T8.6 | "Whole Step Down Tuning" e "Capo: Fret 2" | no topo da tablatura |
| vídeos japoneses (p.ex. "Capo fret 2") | escrito acima do 1º sistema | começo da tab |

**Regra que não se quebra** (decisão 0011, `AGENTS.md` §1): o rótulo vem **só da tela**.
Ler o capo e a afinação escritos na tela é rótulo legítimo. **Calcular** o capo pelo som não
é: o som pode só **conferir** depois.

## 3. O que já existe (não reescreva)

- `tab/tablatura/censo/afinacao.py` (nome antigo `tab.afinacao`): acha **candidatos** a texto
  (blocos com estrutura de texto) em alguns instantes do vídeo e grava o recorte ampliado 4x
  para leitura humana. **Não há OCR instalado, e não se instala nada sem o OK do dono.** Leia
  a docstring do módulo inteira: ela tem a medição de 2026-10-09 (222 candidatos em 30
  vídeos, 6 canais).
  - Uso: `python -m tab.tablatura.censo.afinacao amostrar --canais "shin izumi" iwaki
    --por-canal 5 --saida data/saida/tablatura/gap_afinacao/candidatos`
  - Ele grava `resumo.json` e um PNG por candidato.
- `data/saida/censo/censo_cache.jsonl`: uma linha por vídeo do acervo, com `canal`,
  `arquivo` (caminho relativo ao acervo), `tablatura` (bool), `frac_tablatura` e
  `instantes` (lista de `{"t", "tab"}`). Use para escolher vídeos **com** tablatura.
- `configs/canais.yaml`: o perfil de cada canal. Alguns já têm `afinacao_na_tela`. Canais com
  `rollout: fora` (hoje o `violaodecria`) ficam **fora**.
- `tab/comum/leitor.py`: `quadro_em(caminho, t)` devolve o quadro BGR no instante `t`. **Use
  sempre ele**: 44 % do acervo é AV1, e o OpenCV puro falha em silêncio.
- `tab/comum/caminhos.py`: `acervo()` dá a raiz do acervo, e `SAIDA` dá `data/saida`.

## 4. O que fazer

### Passo A — a amostra (30 min)

1. Escreva `data/saida/tablatura/gap_afinacao/amostra.py`.
   - Use `random.Random(11)`.
   - Para cada canal do censo, exceto `violaodecria`, `tv cifras` e `raman korshun`, sorteie
     **3 vídeos** com `tablatura == true` e `frac_tablatura >= 0.5`.
   - Grave `amostra.json` com canal, arquivo e 4 instantes por vídeo:
     - 3 s;
     - 10 % da duração;
     - o primeiro instante com `tab == true` no censo;
     - o meio do vídeo.
2. Rode-o e confira: o total deve ser perto de 3 × (número de canais).

### Passo B — os quadros e os candidatos (1 a 1,5 h, quase todo esperando o HD)

1. Para cada vídeo e instante da amostra, grave o **quadro inteiro**, reduzido a 960 px de
   largura, em `quadros/<canal>/<n>_<t>s.jpg`.
2. Rode também o `afinacao amostrar` da seção 3 nesses vídeos, se ele aceitar a lista (leia o
   código). Se ele não aceitar uma lista de arquivos, use só os quadros inteiros.
3. Monte **mosaicos**: 6 quadros por imagem, com o nome do canal e do vídeo escritos em ASCII
   no topo de cada um. Grave em `mosaicos/mosaico_NNN.jpg`.

### Passo C — a leitura humana (você mesmo, olhando os mosaicos)

Para cada vídeo, abra os mosaicos e anote em `leitura.json`:

```json
{"canal": "...", "arquivo": "...",
 "capo_escrito": "sim" | "nao" | "nao_da_para_ver",
 "capo_texto": "Capo: Fret 3" | null,
 "capo_casa": 3 | null,
 "afinacao_escrita": "sim" | "nao" | "nao_da_para_ver",
 "afinacao_texto": "Whole Step Down Tuning" | null,
 "onde": "canto superior direito" | "acima do 1º sistema" | ...,
 "em_que_instantes": [3.0, 45.2],
 "mosaico": "mosaico_007.jpg"}
```

- Escreva **exatamente** o que está na tela em `*_texto`. Não traduza nem interprete.
- `capo_casa` só se o número estiver escrito. Na dúvida, `null`.
- **Não deduza** a afinação pelo nome da música, pela imagem do violão ou pelo som.
- "Tuning: Standard" escrito conta como `afinacao_escrita: "sim"`.
- No máximo **40 mosaicos**. Se a amostra der mais, olhe só os 40 primeiros e diga isso.

### Passo D — o resumo

Escreva `resumo.json` e `RELATORIO.md`, com:

1. **Tabela por canal**: vídeos olhados, com capo escrito, com afinação escrita, o lugar
   típico e a forma do texto (por exemplo "Capo: Fret N", "Capo fret N", "⑥=D").
2. **Total**: X de Y vídeos com capo escrito, X de Y com afinação diferente da padrão.
3. **Quando aparece**: o vídeo todo, só no começo, ou só no 1º sistema da tab. Isso decide
   se basta ler 1 instante por vídeo.
4. **Uma proposta de captura**, sem implementar. Responda:
   - dá para ter uma regra por canal, num campo novo no `configs/canais.yaml`, com o lugar do
     texto? Ou precisa ler vídeo a vídeo?
   - quantos vídeos o dono teria de confirmar, e em quanto tempo? Ele marca ~50 itens por
     hora numa ferramenta.
   - o texto tem poucas formas (~5)? Então um palpite pré-preenchido, que o dono só confirma,
     é viável.

## 5. O que NÃO fazer

- **Não instale OCR** (tesseract, easyocr, paddle) nem nenhum pacote. Se você achar que OCR é
  indispensável, escreva isso no relatório como proposta, com o motivo, e **pare**.
- Não use API externa nem modelo de visão de fora.
- Não grave em `data/gold/` nem no acervo. Não commite.
- Não mude `tab/` nem `configs/`. Você só escreve em `data/saida/tablatura/gap_afinacao/`.
- Não use a GPU: esta tarefa não precisa dela.
- Não deduza o capo pelo som nem pela imagem do braço. A trilha das mãos detecta o capo na
  imagem, mas isso é outra fonte e não entra aqui.

## 6. Como rodar

Tudo roda em container, a partir de `/var/home/gabriel/Projects/chorinho-dataset`:

```bash
host-spawn -no-pty -cwd $PWD sh -c 'export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock; docker compose -f compose.yaml -f compose.podman.yaml run --rm --no-deps -e CUDA_VISIBLE_DEVICES= chorinho python data/saida/tablatura/gap_afinacao/amostra.py' > data/saida/tablatura/gap_afinacao/amostra.log 2>&1
```

- Ler vídeo do HD é lento: conte 5 a 20 s por quadro. Rode os passos longos em segundo plano,
  gravando o log, e leia o log.
- Ao terminar cada script, rode `ruff check --no-cache` e `ruff format --no-cache` nele (no
  container).
- Código no padrão do projeto: `main()`, docstring estilo Google em português, imports no
  topo, aspas duplas, 88 colunas.
- Crie `data/saida/tablatura/gap_afinacao/LEIAME.json` (formato em `AGENTS.md` §10, regra 4).

## 7. Critérios de aceitação (a sessão principal vai conferir)

- [ ] `amostra.json` com pelo menos 2 vídeos por canal elegível, e a lista dos canais sem
      vídeo elegível.
- [ ] `leitura.json` com **todos** os vídeos olhados e os 3 valores possíveis usados de
      verdade (sem campo vazio).
- [ ] Os 3 canais de controle conferem com a tabela da seção 2: kenneth acoustic, shin izumi e
      iwaki. Se um deles der "nao", olhe de novo antes de entregar.
- [ ] `RELATORIO.md` com a tabela por canal, o total "X de Y" e a proposta de captura.
- [ ] Nenhum arquivo fora de `data/saida/tablatura/gap_afinacao/`.

## 8. Como não se perder (anti-loop)

- Mantenha um arquivo `diario.md` na pasta. A cada passo, uma linha: o que tentou, o que deu
  e o próximo passo.
- **Mesmo erro duas vezes seguidas**: pare de tentar. Escreva o erro no diário e passe ao
  próximo vídeo. Se for erro de ambiente (container, HD, import), pare a tarefa e relate.
- **No máximo 3 tentativas** por script. Na 3ª falha, entregue o que tem.
- Não melhore o detector de candidatos. Se ele não ajuda, ignore-o e use só os quadros
  inteiros.
- Não amplie a amostra além de 3 vídeos por canal. Mais dado não é o objetivo; a resposta "em
  quantos vídeos aparece" é.

## 9. Quando parar

Pare e entregue quando acontecer o **primeiro** destes:

1. Os critérios da seção 7 estão cumpridos.
2. Passaram as **4 horas**.
3. O HD do acervo não responde (`/run/media/gabriel/3014CD4714CD1130/chorinho` vazio, ou
   `quadro_em` devolvendo `None` em 5 vídeos seguidos). Relate e pare: o dono precisa ligar o
   HD.
4. Você chegou à conclusão de que só dá com OCR. Relate a proposta e pare.

## 10. O relatório final (o que você devolve)

Até 30 linhas, em português:

- a tabela por canal (ou o caminho dela);
- o total: "capo escrito em X de Y vídeos; afinação diferente da padrão em X de Y";
- quando e onde o texto aparece;
- a proposta de captura e o custo para o dono, em minutos;
- o que falhou e por quê;
- os caminhos de todos os arquivos que você criou.

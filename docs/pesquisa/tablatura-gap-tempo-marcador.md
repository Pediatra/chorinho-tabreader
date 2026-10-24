# Tarefa delegada — O tempo da nota pelo marcador vale fora do vídeo do MVP?

**Data**: 2026-10-23. **Trilha**: tablatura (rodadas `0NNN`). **Quem escreveu**: a sessão
principal da tablatura. **Para quem**: um agente que **não** viu a conversa. Tudo o que você
precisa está aqui. Se algo não estiver, **pare e pergunte ao dono**; não suponha.

**Tempo máximo**: 4 horas de trabalho. Passou disso, pare e entregue o relatório com o que tem.

---

## 1. O projeto em poucas linhas

- O projeto monta uma **base de dados de violão** a partir de vídeos-aula (o **acervo**, num HD
  externo, **somente leitura**). Para cada nota: corda, casa, técnica, **o instante** e as mãos.
- Um modelo futuro vai aprender a sair de **vídeo e som** para tablatura. Um instante errado
  liga a nota ao som e ao movimento errados. Para esse modelo, o tempo importa tanto quanto a
  casa.
- Leia `AGENTS.md` (na raiz) **inteiro** antes de rodar qualquer coisa. As regras dele valem
  para você.
- Fale com o dono em **português simples**, com números e denominadores ("X de Y").
- Você **não commita** e não grava em `data/gold/`. Você entrega arquivos em
  `data/saida/tablatura/gap_tempo/` e um relatório.
- **Esta tarefa não pede tempo do dono.** Não peça rótulo novo a ele.

## 2. Os dois tempos (vocabulário)

- **`t_ini`**: o instante em que a coluna da tablatura é **marcada na tela**. Muitos vídeos
  têm um **marcador**: uma faixa ou cursor que passa sobre a coluna tocada, ou o algarismo que
  muda de cor. O produto da tablatura (`tab.tablatura.produto.video`) mede o `t_ini` olhando
  o marcador, quadro a quadro. Vídeo sem marcador fica com `t_ini = null`, de propósito.
- **`t_audio`**: o instante em que a nota **soa**, medido pelo som (trilha do áudio).
- O atraso entre os dois é **quase fixo dentro de um vídeo** e muda entre canais: de −115 a
  +178 ms na rodada 2016 (`docs/rodadas/2016-lote2-doze-canais-com-marcador.md`).

## 3. O que já foi medido (o ponto de partida)

O **dono clicou** 40 instantes por vídeo em 9 vídeos de gabarito (`data/gold/ouro_video/*.json`,
campo `instantes`). A régua `tab.tablatura.ouro.avaliar_video` compara o `t_ini` do produto com
esses cliques. A última medida (`data/saida/tablatura/fase8/ger/ger/*.regua.txt`):

| vídeo | marcador | resultado |
| --- | --- | --- |
| retrato brasileiro (MVP) | sim | 40 de 40 certos |
| greensleeves | cursor fino | 38 de 40 (1 erro, 1 sem tempo) |
| south american | sim | 38 de 40 (1 erro, 1 sem tempo) |
| **end of beginning (EOB)** | ? | **0 de 12: os 12 instantes estão "json sem tempo"** |
| gymnopédie, pat metheny, room 335 | não | 0 tempo falso: ausência certa em 40, 40 e 8 instantes |

- **Tempo falso** (um `t_ini` afirmado e errado) foi **0** em todos.
- O buraco é o **EOB**: o dono clicou 12 instantes com coluna acesa, e o produto não deu tempo
  a nenhum.
- Fora desses 9 vídeos, **ninguém mediu** se o `t_ini` está certo.

## 4. As duas perguntas desta tarefa

**P1.** Por que o EOB fica sem tempo? É um tipo de marcador que o produto não vê, ou uma falha
pontual?

**P2.** Nos vídeos fora do gabarito, o `t_ini` do produto concorda com o som? A pergunta é sobre
o **marcador**: se o atraso som − marcador for estável dentro do vídeo, o marcador está sendo
lido certo.

## 5. O que já existe (não reescreva)

- **Produtos da tablatura de 35 vídeos** (os da T8.2), feitos pela trilha do áudio em
  2026-10-23: `data/saida/audio/r2021/produtos/<slug>.json`.
  - Cada um tem `notas`, uma lista com `tela`, `coluna`, `corda`, `casa`, `t_ini` (ou `null`),
    `exibicao` e `passagem`.
  - E `telas`, com `exibicoes` (`t0`, `t1`, `tempo.medido`, `tempo.motivo`).
- **O som desses 35 vídeos**: `data/saida/audio/r2021/som/<slug>.json` (esquema
  `chorinho/som@1`).
  - `notas`: uma lista com `t_ini`, `t_fim` e `midi` (a altura), achadas por um transcritor
    que **ouve sozinho**, sem ver a tablatura.
  - Ele foi aferido na rodada 2019: revocação 0,804, precisão 0,877.
  - Isso o torna uma **fonte independente**.
- **A altura de uma nota da tablatura**: `tab/comum/violao.py::AFINACAO_MIDI` dá o MIDI da
  corda solta (corda 1 = 64 … corda 6 = 40). A altura é `AFINACAO_MIDI[corda] + casa +
  deslocamento`. O deslocamento é o **capotraste** e a **afinação** do vídeo, que **não são
  conhecidos** (veja a seção 6).
- **A régua do gabarito**: `python -m tab.tablatura.ouro.avaliar_video --ouro <ouro.json>
  --pred <produto.json> --json <saida>`. Leia o `main()` dela para os outros argumentos.
- A rodada 2021 da trilha do áudio (`docs/rodadas/2021-cruzamento-tela-som-t82.md`) já cruzou
  tela e som nesses 35 vídeos, para outra pergunta. **Leia-a**: ela diz que 2 vídeos têm a tab
  correndo de lado (*what a wonderful world*, *toxic*). Neles o x do produto se desloca, e a
  casa por x falha.

## 6. Cuidado: a altura depende do capo e da afinação

Num vídeo com capo na casa 3, toda nota soa 3 semitons acima do que a tab diz. Você **não sabe**
o capo de cada vídeo. Faça assim:

- Para cada vídeo, teste os deslocamentos de **−5 a +7 semitons** (um valor para o vídeo
  inteiro).
- Escolha o que casa **mais** notas da tab com notas do som (a regra de casar está na seção 7).
- Grave o deslocamento escolhido e quantas notas ele casou. Grave também o 2º melhor e quantas
  ele casou.
- Se o melhor e o 2º diferem por menos de 10 % das notas, marque o vídeo como `deslocamento
  ambíguo` e **não o use** na P2.

**Isto é só para casar as notas nesta medida.** O deslocamento achado **não é rótulo** (a regra
de `AGENTS.md` §1: o som confere, não cria) e não entra no produto. Mas anote-o no relatório:
ele interessa à outra tarefa, `tablatura-gap-afinacao-capo.md`.

## 7. O que fazer

### Passo 1 — P1, o EOB (até 1 h)

1. Leia `data/saida/tablatura/fase8/ger/ger/end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics.regua.txt`
   e o `.regua.json` ao lado.
2. Abra o produto ao lado (`.json`). Para cada tela, veja `exibicoes[*].tempo.medido` e
   `tempo.motivo`. Conte os motivos.
3. Pegue **3 instantes** clicados pelo dono (do ouro em `data/gold/ouro_video/end_of_beginning_...json`,
   campo `instantes`). Grave o quadro inteiro de cada um com `tab.comum.leitor.quadro_em` em
   `eob/quadro_<t>.jpg`. Olhe as 3 imagens: **como é o marcador desse vídeo?** (cor, faixa,
   cursor, nenhum).
4. Escreva em `eob/diagnostico.md`, em 10 linhas no máximo: o motivo que o produto deu, como é
   o marcador, e uma hipótese de por que o observador não o vê. **Não conserte o código.**

### Passo 2 — P2, o atraso som − marcador nos 35 vídeos (até 2 h)

Escreva `data/saida/tablatura/gap_tempo/atraso.py`. Para cada vídeo que tem produto e som:

1. Pegue as notas do produto com `t_ini` não nulo e casa numérica (sem `x`).
2. Escolha o deslocamento (seção 6).
3. **Case** cada nota da tab com uma nota do som:
   - mesmo `midi` (o MIDI da tab mais o deslocamento);
   - com `t_ini_som` entre `t_ini_tab − 0,4 s` e `t_ini_tab + 0,6 s`;
   - se houver mais de uma, fique com a mais perto no tempo;
   - cada nota do som casa no máximo uma vez.
4. Para as casadas, `atraso = t_ini_som − t_ini_tab`.
5. Por vídeo, grave em `atraso.json`:
   - o canal e o slug;
   - as notas com `t_ini`, as casadas e a fração casada;
   - o deslocamento (o 1º, o 2º e se é ambíguo);
   - a mediana do atraso, em ms;
   - a **fração das casadas com |atraso − mediana| ≤ 0,15 s**: é a "estabilidade";
   - o número de colunas fora dessa faixa (as suspeitas).
6. Para os **3 vídeos de menor estabilidade**, grave um gráfico simples (matplotlib está na
   imagem): x = `t_ini_tab` e y = atraso, em `graficos/<slug>.png`. Se o gráfico mostra
   **degraus**, o atraso muda no meio do vídeo. Isso costuma ser troca de tela ou exibição
   repetida (veja `exibicao` e `passagem` nas notas).

### Passo 3 — a leitura (30 min)

Responda no `RELATORIO.md`:

- Em quantos vídeos, de quantos, a estabilidade é ≥ 0,90? E ≥ 0,80?
- A mediana do atraso por canal: ela fica parecida entre os 2 vídeos do mesmo canal?
- Os vídeos instáveis têm algo em comum? (marcador por cor ou por faixa, tab que rola,
  `exibicao` repetida)
- Quantos vídeos ficaram de fora, e por quê? (sem `t_ini`, sem som, deslocamento ambíguo)

## 8. Critérios de aceitação (a sessão principal vai conferir)

- [ ] `eob/diagnostico.md` com o motivo do produto, as 3 imagens e a hipótese.
- [ ] `atraso.json` com uma linha para **cada** um dos 35 vídeos, incluindo os excluídos e o
      motivo de cada exclusão.
- [ ] Os 2 vídeos que correm de lado (*what a wonderful world*, *toxic*) estão marcados à
      parte, sem esconder o resultado deles.
- [ ] `RELATORIO.md` com a resposta das perguntas do passo 3, em "X de Y".
- [ ] **Teste de sanidade**: rode o `atraso.py` no vídeo do MVP (o *retrato brasileiro*) e
      relate a estabilidade. Os insumos estão em `data/saida/audio/` (procure por "retrato").
      Ele teve 40/40 no gabarito, então a estabilidade deve sair alta (≥ 0,85). Se não sair, a
      sua medida tem um defeito: **pare e relate** antes de interpretar os outros vídeos.

## 9. O que NÃO fazer

- **Não mude o produto** (`tab/tablatura/produto/`) nem o observador do marcador. Isto é
  diagnóstico.
- Não use o atraso para "corrigir" `t_ini`. Não grave `t_ini` novo em lugar nenhum.
- Não rode o produto inteiro de novo: os 35 produtos já existem. Só o passo 1 lê quadros do
  HD.
- Não use a GPU.
- Não instale nada. Não grave fora de `data/saida/tablatura/gap_tempo/`. Não commite.

## 10. Como rodar

A partir de `/var/home/gabriel/Projects/chorinho-dataset`:

```bash
host-spawn -no-pty -cwd $PWD sh -c 'export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock; docker compose -f compose.yaml -f compose.podman.yaml run --rm --no-deps -e CUDA_VISIBLE_DEVICES= chorinho python data/saida/tablatura/gap_tempo/atraso.py' > data/saida/tablatura/gap_tempo/atraso.log 2>&1
```

- `ruff check --no-cache` e `ruff format --no-cache` no container, nos seus scripts.
- Código no padrão do projeto (`main()`, docstring Google em português, imports no topo).
- Crie `LEIAME.json` na pasta (`AGENTS.md` §10, regra 4).

## 11. Como não se perder (anti-loop)

- Mantenha `diario.md`: uma linha por tentativa (o que fez, o que deu, o próximo passo).
- Se a fração casada de um vídeo der < 0,2, **não invente** outra regra de casar. Marque o
  vídeo como `pouco casado` e siga. A regra da seção 7 é fixa.
- Não ajuste a janela (−0,4/+0,6 s) nem a faixa (0,15 s) para "melhorar" números. Se achar que
  elas estão erradas, diga isso no relatório, com o motivo.
- **No máximo 3 tentativas** por script. Mesmo erro duas vezes: pare e relate.
- Não abra mais do que as 3 imagens do EOB e os 3 gráficos.

## 12. Quando parar

Pare e entregue quando acontecer o **primeiro** destes:

1. Os critérios da seção 8 estão cumpridos.
2. Passaram as **4 horas**.
3. O teste de sanidade do MVP falhou e você não achou o defeito em 2 tentativas.
4. Os arquivos da seção 5 não existem, ou têm outro formato. Relate o que achou e pare.

## 13. O relatório final

Até 30 linhas, em português:

- P1: por que o EOB fica sem tempo, com as imagens;
- P2: "estabilidade ≥ 0,90 em X de Y vídeos", a mediana do atraso por canal e os instáveis;
- o teste do MVP;
- os deslocamentos achados por vídeo (para a tarefa de afinação e capo);
- o que falhou e por quê;
- os caminhos de todos os arquivos.

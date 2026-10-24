# Tarefa delegada — Quantas vezes a mão esquerda e a direita saem trocadas?

**Data**: 2026-10-23. **Trilha**: mãos (rodadas `1NNN`). **Quem escreveu**: a sessão principal das
mãos. **Para quem**: um agente que **não** viu a conversa. Tudo o que você precisa está aqui; se
algo não estiver, **pare e pergunte ao dono**, não suponha.

**Tempo máximo**: 2 horas de trabalho. Passou disso, pare e entregue o relatório com o que tem.

---

## 1. O projeto em 6 linhas

- O projeto monta uma **base de dados de violão**: para cada nota tocada nos vídeos-aula, guarda
  a nota (corda, casa), o instante em que ela soa, o braço do violão e as duas mãos.
- O **rótulo** vem da tablatura da tela. As mãos e o braço são a **entrada** de um modelo
  futuro.
- Leia `AGENTS.md` (na raiz) **inteiro** antes de rodar qualquer coisa. As regras dele valem
  para você.
- Fale com o dono em **português simples**, com números e denominadores ("X de Y").
- Você **não commita**. Você entrega arquivos em `data/saida/maos/m49/troca_de_maos/` e um
  relatório. A sessão principal revisa e decide.
- O violonista do vídeo é **destro**: a mão **esquerda** pisa as cordas no braço, e a **direita**
  ataca as cordas perto da boca do violão.

## 2. O problema

O detector de mãos (`tab/maos/detector.py` + `tab/maos/combinar.py`) diz o **lado** de cada mão
(`esquerda` ou `direita`). Ele usa dois modelos: o Wholebody (que vê o corpo inteiro e sabe o
lado pelo corpo) e o MediaPipe (que vê só a mão e às vezes **troca** os lados).

A base guarda a mão `esquerda` no índice 0 ("mão do braço") e a `direita` no índice 1 ("mão do
ataque"). Se o lado vier trocado, a checagem K2 procura os dedos na mão errada, e a nota é
recusada sem culpa do braço. Pior: os dados de entrada do modelo futuro ficam com as mãos
trocadas naquele quadro.

## 3. A pergunta

No vídeo do MVP, em quantos quadros a mão de índice 0 (esquerda) **não** é a que está no braço?

**Como saber qual mão está no braço**, sem rótulo humano: o braço vai do **nut** (perto da cabeça
do violão) até o corpo. A mão que pisa fica **mais perto do nut**, ao longo do braço, do que a mão
que ataca. É geometria do instrumento, não o gabarito.

## 4. Os dados (já existem; você só lê)

Pasta: `data/saida/maos/m49/mvp/execucao_1/`

- `retrato brasileiro - tab & lesson.maos.npz`. Abra com `np.load(caminho, allow_pickle=False)`.
  As chaves e formas:
  - `pts` (N,): tempo de cada quadro, em segundos;
  - `maos` (N, 2, 21, 3): x, y e score dos 21 pontos; **índice 0 = esquerda, 1 = direita**; NaN
    se ausente. O ponto 0 é o pulso; os pontos 8, 12, 16 e 20 são as pontas do indicador ao
    mínimo;
  - `maos_origem` (N, 2): 0 = ausente, 1 = Wholebody, 2 = MediaPipe;
  - `braco_trastes` (N, 25, 2): ponto de cada traste; **o índice 0 é o nut**; NaN se não visível;
  - `braco_achou` (N,) bool e `braco_conf` (N,): 1 = entregue, 0 = sinalizado, NaN = sem braço.
    O braço só foi calculado em 1 quadro a cada 10.
- O arquivo tem espaços e `&` no nome: **sempre entre aspas**.
- O JSON irmão (`... .maos.json`) tem `video.arquivo` (o caminho do vídeo no acervo) e
  `video.largura` / `video.altura`.

**Pré-condição**: o `.npz` precisa existir. Ele sai de uma execução longa que termina por volta
de 00h30 de 2026-10-24. Confira **uma vez** com `ls`. Se não existir, **pare** e escreva no
relatório "dados ainda não existem"; não fique esperando em loop.

## 5. Como rodar Python aqui (leia, é diferente do normal)

- O agente roda dentro de um distrobox **sem** `git` nem `podman`. Eles rodam no host por
  `host-spawn`.
- Todo Python do projeto roda **em container**. Para a conta (só numpy), use a imagem base:

  ```bash
  cd /var/home/gabriel/Projects/chorinho-dataset
  host-spawn -no-pty podman run --rm --security-opt label=disable \
      -v "$PWD":/app -w /app -e PYTHONPATH=/app \
      docker.io/library/chorinho:dev python data/saida/maos/m49/troca_de_maos/medir.py
  ```

- Para a folha (passo 6.5), você precisa ler quadros do vídeo: use a imagem
  `localhost/chorinho-maos:dev` e monte o acervo **somente leitura** com
  `-v /run/media/gabriel/3014CD4714CD1130/chorinho:/acervo:ro`. Leia o quadro com
  `tab.comum.leitor.quadro_em("/acervo/" + video_arquivo, t)`. **Nunca** escreva no acervo.

## 6. O que fazer, passo a passo

Escreva **um** script: `data/saida/maos/m49/troca_de_maos/medir.py`. Não edite nada dentro de
`tab/`.

1. **Quadros medidos**: os quadros `i` com braço **entregue** (`braco_achou[i]` e
   `braco_conf[i] == 1`), com o nut (`braco_trastes[i, 0]`) finito e pelo menos mais um traste
   finito.
2. **O eixo do braço** em cada quadro medido: `a` = o nut; `b` = o traste finito de **maior**
   número. `eixo = (b − a) / |b − a|`. A **posição** de um ponto `p` ao longo do braço é
   `s(p) = (p − a) · eixo / |b − a|` (0 no nut, 1 no último traste visto).
3. **A posição de cada mão**: a mediana de `s` sobre os pontos 0, 5, 9, 13 e 17 (pulso e bases
   dos dedos) da mão, só com pontos finitos.
4. **Classifique cada quadro medido**:
   - `duas_maos`: as duas mãos presentes (`maos_origem[i, 0] > 0` e `maos_origem[i, 1] > 0`);
     - `certo` se `s(mão 0) < s(mão 1)`;
     - `trocado` se `s(mão 0) > s(mão 1)`;
   - `so_a_0`: só a mão 0; `so_a_1`: só a mão 1; `nenhuma`.
   - Para `duas_maos`, guarde também a origem (1 ou 2) das duas: a pergunta é se a troca vem do
     MediaPipe.
5. **Folha**: até 12 quadros `trocado` (todos, se forem menos; sorteio com
   `random.Random(20261049)` se forem mais). Em cada um: o quadro; o nut e os trastes em verde;
   a mão 0 em vermelho e a mão 1 em azul (os 21 pontos); o texto com `s(mão 0)`, `s(mão 1)` e a
   origem de cada. Grave `data/saida/maos/m49/troca_de_maos/folha.jpg`. **Olhe a folha** antes
   de concluir: o "trocado" pode ser erro do seu eixo, e não do detector.
6. **Uma segunda conta, sem o braço**: em **todos** os quadros (não só os de braço) com as duas
   mãos, compare o `x` médio das duas mãos. Neste vídeo, olhe 3 quadros quaisquer para saber de
   que lado da imagem fica o braço e escreva isso. Conte quantos quadros têm a mão 0 do lado
   "errado". É só um número de apoio, porque a câmera pode estar espelhada.

## 7. Critérios: o que conta como resposta

A regra de decisão está escrita **antes** de você medir. Não mude depois de ver os números.

- **Taxa de troca** = `trocado` ÷ `duas_maos`.

| taxa de troca | conclusão |
| --- | --- |
| ≤ 2 % | raro: nada a mudar |
| > 2 % | vale uma regra de correção; descreva-a no relatório (não implemente) |

- Se você recomendar uma correção, use **só geometria**: "a mão mais perto do nut é a 0". Diga
  quantos quadros ela mudaria e quantos ela não consegue decidir (sem braço por perto).
- Você **recomenda**; quem muda o código é a sessão principal.

**Aceite da tarefa** (você terminou quando tem tudo isto):

1. `medir.py` roda do zero e grava `data/saida/maos/m49/troca_de_maos/resultado.json` com as
   contagens do passo 6.4 (com denominadores) e a conta do passo 6.6;
2. `folha.jpg`, e você a olhou;
3. `relatorio.md` na mesma pasta (formato na seção 9).

## 8. Como não se perder (regras contra loop)

- **Não edite** nada em `tab/`, `tests/`, `docs/`, `data/gold/` ou o acervo. Nada de `git`.
- **Um erro igual duas vezes**: pare de tentar consertar, escreva no relatório o que tentou e
  entregue.
- **Não troque a definição** de "mão no braço" depois de ver o número. Se achar que ela falha,
  escreva por quê, com um quadro da folha de exemplo.
- **Não rode nada na GPU** e não rode o detector de mãos de novo: os dados já estão no `.npz`.
- **Não espere em loop** por arquivo. Confira uma vez; se faltar, pare.

## 9. Quando parar e o que entregar

Pare quando:
- o aceite da seção 7 estiver completo; **ou**
- bater uma das regras da seção 8; **ou**
- passar de 2 horas.

`relatorio.md`, em português simples:

```text
# Troca de mãos no vídeo do MVP — relatório
## Resposta curta (3 linhas)
## Números (com "X de Y"): duas_maos, certo, trocado, so_a_0, so_a_1, nenhuma; origem nos trocados
## A conta sem o braço (passo 6.6)
## O que vi na folha
## Conclusão pela regra da seção 7
## Limites (ex.: braço só a 1 qps; quadros sem braço não entram)
```

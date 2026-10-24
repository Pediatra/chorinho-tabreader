# Tarefa delegada — A checagem K2 separa a nota certa da nota vizinha?

**Data**: 2026-10-23. **Trilha**: mãos (rodadas `1NNN`). **Quem escreveu**: a sessão principal das
mãos. **Para quem**: um agente que **não** viu a conversa. Tudo o que você precisa está aqui; se
algo não estiver, **pare e pergunte ao dono**, não suponha.

**Tempo máximo**: 3 horas de trabalho. Passou disso, pare e entregue o relatório com o que tem.

---

## 1. O projeto em 6 linhas

- O projeto monta uma **base de dados de violão**: para cada nota tocada nos vídeos-aula, guarda
  a nota (corda, casa), o instante em que ela soa, o braço do violão e as duas mãos.
- O **rótulo** (corda e casa) vem da tablatura que aparece na tela do vídeo. As mãos e o braço são
  a **entrada** de um modelo futuro.
- O maior perigo é ligar uma nota ao **movimento errado** (o da nota anterior ou o da seguinte):
  o modelo aprenderia errado. Por isso cada nota passa por 4 checagens (K1 a K4).
- Leia `AGENTS.md` (na raiz) **inteiro** antes de rodar qualquer coisa. As regras dele valem
  para você.
- Fale com o dono em **português simples**, com números e denominadores ("X de Y").
- Você **não commita**. Você entrega arquivos em `data/saida/maos/m49/k2_vizinha/` e um
  relatório. A sessão principal revisa e decide.

## 2. O que é a K2 (a checagem que você vai testar)

A K2 confere se **algum dedo da mão esquerda** (a mão que pisa as cordas) está na **célula** da
nota, isto é, no lugar do braço onde aquela corda e aquela casa ficam, perto do instante em
que a nota soa.

O código está em `tab/maos/base.py` (leia o arquivo inteiro, ~600 linhas). As peças:

- `janela(pts, t_som)`: os índices dos quadros com tempo entre `t_som − 0,5 s` e `t_som + 0,5 s`
  (`MEIA_JANELA_S = 0.5`).
- `checar_k2(denso, jan, t_som, corda, casa)`:
  1. pega o **quadro de braço entregue** mais perto de `t_som` (a até 0,5 s; o braço só foi
     calculado em 1 quadro a cada 10, ~1 por segundo);
  2. para cada quadro da janela, para cada ponta de dedo (pontos 8, 12, 16 e 20 da mão de
     índice 0), mede `distancia_na_celula(...)`;
  3. passa se a menor distância ≤ `VAOS_CORDA = 1.0` (1 vão entre cordas).
- `distancia_na_celula(trastes, corda1, corda6, corda, casa, ponto)`: infinito se a ponta está
  fora da casa ao longo do braço (entre o traste `casa − 1` e o traste `casa` + ¼ de casa); senão,
  a distância da ponta à reta da corda, em vãos.

**O problema**: a janela tem **1 segundo**. Numa passagem rápida cabem 4 a 8 notas nesse
segundo. Então o dedo pode estar na célula da nota **vizinha** (a anterior ou a seguinte) em
algum quadro da janela, e a K2 da nota de agora passar mesmo assim. Se isso acontece muito, a K2
**não protege** contra o erro que ela devia pegar.

## 3. A pergunta

Com os dados do vídeo do MVP, quantas vezes a K2 **também passa** quando, no lugar da célula da
nota, a gente põe a célula da **nota vizinha no tempo**? E uma janela menor resolve, sem perder
muitas notas certas?

## 4. Os dados (já existem; você só lê)

Pasta: `data/saida/maos/m49/mvp/execucao_1/`

- `retrato brasileiro - tab & lesson.maos.json`: os eventos (uma nota cada), com `corda`, `casa`,
  `t_som`, `janela`, `checagens` e `nivel`. O formato está em
  `docs/decisoes/1007-formato-da-base-das-maos.md`.
- `retrato brasileiro - tab & lesson.maos.npz`: as matrizes, quadro a quadro. Abra com
  `np.load(caminho, allow_pickle=False)`. As chaves e formas:
  - `pts` (N,): tempo de cada quadro, em segundos;
  - `maos` (N, 2, 21, 3): x, y e score dos 21 pontos; índice 0 = mão do braço (esquerda), 1 = mão
    do ataque; NaN se ausente;
  - `maos_origem` (N, 2): 0 = ausente;
  - `braco_trastes` (N, 25, 2): ponto de cada traste (0 = nut), NaN se não visível;
  - `braco_corda1`, `braco_corda6` (N, 2, 2): dois pontos de cada reta;
  - `braco_achou` (N,) bool e `braco_conf` (N,): 1 = entregue, 0 = sinalizado, NaN = sem braço.
- O arquivo tem espaços e `&` no nome: **sempre entre aspas**.

**Pré-condição**: esses dois arquivos precisam existir. Eles saem de uma execução longa que
termina por volta de 00h30 de 2026-10-24. Confira **uma vez** com `ls`. Se não existirem, **pare**
e escreva no relatório "dados ainda não existem"; não fique esperando em loop.

## 5. Como rodar Python aqui (leia, é diferente do normal)

- O agente roda dentro de um distrobox **sem** `git` nem `podman`. Eles rodam no host por
  `host-spawn`.
- Todo Python do projeto roda **em container**. Para este trabalho (só numpy, sem GPU, sem
  vídeo), use a imagem base:

  ```bash
  cd /var/home/gabriel/Projects/chorinho-dataset
  host-spawn -no-pty podman run --rm --security-opt label=disable \
      -v "$PWD":/app -w /app -e PYTHONPATH=/app \
      docker.io/library/chorinho:dev python data/saida/maos/m49/k2_vizinha/medir.py
  ```

- Para a folha de imagens (passo 6.5), você precisa ler quadros do vídeo. Aí use a imagem
  `localhost/chorinho-maos:dev` e monte o acervo **somente leitura**:
  `-v /run/media/gabriel/3014CD4714CD1130/chorinho:/acervo:ro`. Leia o quadro com
  `tab.comum.leitor.quadro_em(caminho, t)` (o caminho é `/acervo/` + o campo
  `video.arquivo` do JSON). **Nunca** escreva no acervo.

## 6. O que fazer, passo a passo

Escreva **um** script: `data/saida/maos/m49/k2_vizinha/medir.py`. Não edite nada dentro de
`tab/`. Importe de lá o que precisar: `from tab.maos.base import distancia_na_celula, PONTAS,
VAOS_CORDA, BRACO_MAX_S`.

1. **Carregue** o JSON e o `.npz`.
2. **Eventos elegíveis**: `casa > 0`, `t_som` não nulo, e com um quadro de braço entregue
   (`braco_achou` verdadeiro e `braco_conf == 1`) a ≤ 0,5 s de `t_som`. Conte quantos são.
3. **As vizinhas** de cada elegível `e`. Ordene todos os eventos com `t_som` por `t_som`.
   - **Vizinha anterior**: o evento mais perto **antes** de `e`, com `t_som < e.t_som − 0,05`,
     `casa > 0` e `(corda, casa)` **diferente** da de `e`.
   - **Vizinha seguinte**: o mesmo, **depois** (`t_som > e.t_som + 0,05`).
   - Notas do mesmo acorde (mesmo instante) **não** são vizinhas; por isso a folga de 0,05 s.
   - A vizinha só empresta a **célula** (corda, casa). A janela, o `t_som` e o quadro de braço
     continuam os de `e`.
4. **A grade de janelas**. Para cada meia-largura `W` em `0.5, 0.3, 0.2, 0.1` e para
   `"so_o_mais_perto"` (só o quadro de `pts` mais perto de `t_som`), calcule, para cada elegível:
   - `real`: passa se alguma ponta (`PONTAS`) da mão 0, em algum quadro com
     `|pts − t_som| ≤ W`, tem `distancia_na_celula(... corda_e, casa_e ...) ≤ VAOS_CORDA`;
   - `anterior` e `seguinte`: o mesmo, com a célula da vizinha.
   - Use **sempre o mesmo quadro de braço** (o entregue mais perto de `t_som`), como em
     `checar_k2`.
   - Com `W = 0.5`, o seu `real` tem que bater com o `K2.passou` do JSON em **todos** os
     elegíveis. Se não bater, o seu script está errado: conserte **antes** de seguir (no máximo
     3 tentativas; ver seção 8).
5. **Separe as vizinhas "inseparáveis por construção"**: mesma `casa` e `|corda − corda_e| = 1`.
   A tolerância de 1 vão faz a célula delas se sobrepor à de `e`. Conte-as à parte.
6. **Tabela** (uma linha por `W`):
   - `real`: X de Y elegíveis;
   - `vizinha_passa`: X de Y vizinhas (sem as inseparáveis);
   - `ambiguas`: dos `real` que passam, quantos têm alguma vizinha (sem as inseparáveis) que
     também passa;
   - `inseparaveis_passa`: X de Y.
7. **Folha**: 12 casos com `W = 0.5` em que `real` passa **e** uma vizinha separável também
   passa (sorteio com `random.Random(20261049)`). Em cada célula: o quadro mais perto de
   `t_som`; o braço (trastes em verde); a célula de `e` em vermelho e a da vizinha em azul; as
   pontas dos dedos em magenta; o texto `corda casa` de `e` e da vizinha. Grave em
   `data/saida/maos/m49/k2_vizinha/folha.jpg`. **Olhe a folha** antes de escrever o relatório.

## 7. Critérios: o que conta como resposta

A regra de decisão está escrita **antes** de você medir. Não mude depois de ver os números.

| resultado com `W = 0.5` | conclusão |
| --- | --- |
| `vizinha_passa` ≤ 10 % | a K2 separa bem; nada a mudar |
| `vizinha_passa` > 10 % | olhe as outras janelas (linha abaixo) |

- **Janela recomendada**: a **maior** `W` com `vizinha_passa` ≤ 10 % **e** `real` ≥ 80 % do
  `real` de `W = 0.5`.
- Se nenhuma `W` cumpre as duas, a conclusão é "**a K2 não separa nota vizinha com janela
  nenhuma**". Isso é uma resposta válida: escreva e pare.
- Você **recomenda**; quem muda `tab/maos/base.py` é a sessão principal, com um pré-registro novo.

**Aceite da tarefa** (você terminou quando tem tudo isto):

1. `medir.py` roda do zero e grava `data/saida/maos/m49/k2_vizinha/resultado.json` com a tabela;
2. com `W = 0.5`, o `real` bate com o JSON em 100 % dos elegíveis (escreva "X de X");
3. `folha.jpg` com 12 casos (ou todos, se forem menos), e você a olhou;
4. `relatorio.md` na mesma pasta (formato na seção 9).

## 8. Como não se perder (regras contra loop)

- **Não edite** nada em `tab/`, `tests/`, `docs/` (exceto criar o seu relatório na pasta de
  saída), `data/gold/` ou o acervo. Nada de `git`.
- **Um erro igual duas vezes** (a mesma mensagem, ou o mesmo número errado): pare de tentar
  consertar, escreva no relatório o que tentou e o erro, e entregue.
- **No máximo 3 tentativas** para fazer o passo 6.4 bater com o JSON. Na 4ª, pare e relate.
- **Não invente grade nova.** As janelas são as 5 da seção 6.4. Se achar que outra seria
  melhor, escreva como sugestão no relatório, sem medir.
- **Não rode nada na GPU.** Esta tarefa não precisa. Se algo pedir GPU, você está no caminho
  errado.
- **Não espere em loop** por arquivo. Confira uma vez; se faltar, pare.
- Se um número parecer bom demais ou ruim demais, **olhe a folha** antes de concluir (regra 4 do
  `AGENTS.md`: olhe o quadro antes de teorizar).

## 9. Quando parar e o que entregar

Pare quando:
- o aceite da seção 7 estiver completo; **ou**
- bater uma das regras da seção 8; **ou**
- passar de 3 horas.

`relatorio.md`, em português simples:

```text
# K2 contra a nota vizinha — relatório
## Resposta curta (3 linhas)
## Números (a tabela, com "X de Y")
## O que vi na folha (o que os 12 casos têm em comum)
## Conclusão pela regra da seção 7 (copie a linha da regra que vale)
## O que não deu certo / limites (ex.: braço só a 1 qps; pontas deslocadas ~1 vão)
## Sugestões (sem medir)
```

# Tarefa delegada — Censo visual dos 417 vídeos do sky guitar (tela dividida, braço, capo)

**Data**: 2026-10-24. **Trilha**: mãos (rodadas `1NNN`). **Quem escreveu**: a sessão principal das
mãos. **Para quem**: um agente que **não** viu a conversa. Tudo o que você precisa está aqui; se
algo não estiver, **pare e pergunte ao dono**, não suponha.

**Tempo máximo**: 4 horas de trabalho. Passou disso, pare e entregue o que tem.

---

## 1. O projeto em poucas linhas

- O projeto monta uma base de dados de violão: para cada nota tocada nos vídeos-aula, a nota
  (da tablatura da tela), o instante do som, o braço do violão e as duas mãos.
- O próximo passo é um **piloto em 20 vídeos do canal sky guitar** (417 vídeos no acervo). Para
  escolher bem os 20, a sessão principal precisa saber como cada vídeo é **por fora**.
- Leia `AGENTS.md` (na raiz) inteiro antes de rodar qualquer coisa: seção 4 (ambiente) e 8
  (o dono e o gabarito).

## 2. Por que importa

No vídeo do MVP (*retrato brasileiro*) descobrimos que a imagem é de **tela dividida**: em cima,
a partitura e a tablatura; embaixo à esquerda, uma câmera com a mão direita; embaixo à direita,
outra câmera com o braço e a mão esquerda. Isso muda o que as mãos significam (as duas mãos não
estão no mesmo espaço). Não sabemos quantos dos 417 vídeos são assim.

## 3. O que fazer

### Passo 1 — os quadros (script, sem olhar)

Crie `data/saida/maos/censo_sky/` e um script `quadros.py` nela:

- liste os `.mp4` de `/acervo/sky guitar/` (ordem alfabética, normalizando o nome com
  `unicodedata.normalize("NFC", nome)`);
- para cada vídeo, pegue **um** quadro em 50 % da duração (`tab.comum.leitor.info(caminho)
  ["duracao_s"]` e `tab.comum.leitor.quadro_em(caminho, t)`). Use sempre o `tab.comum.leitor`
  (44 % do acervo é AV1, que o OpenCV não lê e falha em silêncio);
- reduza para 640 × 360 e monte **folhas de 12 quadros** (3 colunas × 4 linhas), com o número
  do vídeo escrito em cada quadro (`001`, `002`, …), em `folhas/folha_01.jpg`, `folha_02.jpg`…;
- grave `lista.json`: `[{"n": 1, "arquivo": "sky guitar/....mp4", "t": ..., "duracao_s": ...}]`.

Comando (imagem com `ffmpeg` e acervo **somente leitura**):

```bash
cd /var/home/gabriel/Projects/chorinho-dataset
host-spawn -no-pty podman run --rm --security-opt label=disable \
    -v "$PWD":/app -v /run/media/gabriel/3014CD4714CD1130/chorinho:/acervo:ro \
    -w /app -e PYTHONPATH=/app localhost/chorinho-maos:dev \
    python data/saida/maos/censo_sky/quadros.py
```

- O agente roda num distrobox **sem** `podman`: ele roda no host por `host-spawn -no-pty`.
- O HD do acervo é lento: 417 leituras levam uns 20–40 minutos. Rode **uma vez**. Se cair no
  meio, o script deve pular os quadros já gravados ao recomeçar.

### Passo 2 — olhar as folhas

Abra cada folha (ferramenta Read) e, para cada vídeo, preencha:

| campo | valores |
| --- | --- |
| `tela` | `dividida` (duas ou mais câmeras lado a lado), `unica` (uma câmera), `sem_violao` (só partitura, texto, rosto), `nao_sei` |
| `braco_visivel` | `sim`, `nao`, `nao_sei`: dá para ver os trastes do braço? |
| `capo` | `sim` (uma barra presa atravessando as cordas no braço), `nao`, `nao_sei` |
| `tab_na_tela` | `sim`, `nao`, `nao_sei`: a tablatura (6 linhas com números) aparece? |

Na dúvida, `nao_sei`. Um quadro só não diz tudo do vídeo (a tablatura aparece e some, por
exemplo): é **um censo por amostra**, e o relatório precisa dizer isso.

Grave as respostas em `censo.json`: `[{"n": 1, "tela": "...", "braco_visivel": "...", "capo":
"...", "tab_na_tela": "..."}]`.

### Passo 3 — conferência de você mesmo

Sorteie 20 vídeos (`random.Random(20261050)`), gere para eles um **segundo** quadro em 25 % da
duração e uma folha `folhas/conferencia.jpg`. Classifique de novo sem olhar o `censo.json` e
conte quantos dos 20 batem no campo `tela`. Isso mede a firmeza do seu olho.

## 4. Critérios de aceitação

1. `lista.json` com os 417 vídeos (ou diga quantos falharam a leitura e por quê);
2. `censo.json` com um registro por vídeo lido;
3. a conferência do passo 3: "X de 20 batem em `tela`";
4. `relatorio.md` (seção 6).

Não há regra de decisão: é um censo. A sessão principal usa o resultado para escolher os 20 do
piloto.

## 5. Como não se perder (regras contra loop)

- Você só **cria** arquivos em `data/saida/maos/censo_sky/`. Nada de `git`, nada em `tab/`,
  `tests/`, `docs/`, `data/gold/`; **nunca** escreva no acervo.
- Não use a GPU (não precisa).
- **Um erro igual duas vezes**: pare, escreva o que tentou e entregue.
- Não leia o vídeo inteiro nem mais quadros do que o pedido. Não rode detector nenhum.
- Se uma folha não der para ler (quadros pequenos demais), aumente para 6 quadros por folha
  **uma vez** e siga; não fique ajustando.

## 6. Quando parar e o que entregar

```text
# Censo visual do sky guitar — relatório
## Resposta curta (3 linhas)
## Contagens ("X de 417") por campo: tela, braco_visivel, capo, tab_na_tela
## Conferência (passo 3): X de 20
## Exemplos (o número de 2 vídeos de cada tipo de tela)
## Limites (um quadro por vídeo; o que pode estar errado)
```

# Tarefa delegada — Troca de mãos em vídeos de câmera única (11 canais)

**Data**: 2026-10-24. **Trilha**: mãos (rodadas `1NNN`). **Quem escreveu**: a sessão principal das
mãos. **Para quem**: um agente que **não** viu a conversa. Tudo o que você precisa está aqui; se
algo não estiver, **pare e pergunte ao dono**, não suponha.

**Tempo máximo**: 3 horas de trabalho. Passou disso, pare e entregue o relatório com o que tem.

**Esta tarefa continua outra**: `docs/pesquisa/maos-gap-troca-de-maos.md` (leia-a primeiro: o
projeto, o problema, a ideia de "a mão mais perto do nut", como rodar Python aqui). O relatório
dela está em `data/saida/maos/m49/troca_de_maos/relatorio.md`.

---

## 1. Por que repetir

A tarefa anterior deu **0 trocas em 432 quadros** no vídeo do MVP, mas o teste quase não testou:

- o **MediaPipe**, que é quem às vezes troca os lados, entrou em só 2 quadros (o resto veio do
  Wholebody);
- o vídeo do MVP é de **tela dividida**: a mão direita aparece numa câmera (painel da
  esquerda) e o braço noutra (painel da direita). A mão direita fica sempre longe do braço, e a
  regra "a mão mais perto do nut é a esquerda" acerta por construção.

Agora o teste é em **80 quadros de 11 canais diferentes**, em que o **dono marcou o braço à mão**
(nut e trastes). Esse braço é gabarito: use-o, não calcule outro.

## 2. Os dados (você só lê)

| conjunto | índice dos quadros | braço do dono | imagem do quadro |
| --- | --- | --- | --- |
| M44 | `data/saida/maos/m44/indice.json` | `data/gold/maos/braco_m44.json` | `data/saida/maos/m44/` + o campo `png` do índice |
| M47 | `data/saida/maos/m47/indice.json` | `data/gold/maos/braco_m47.json` | **não há PNG**: leia do vídeo com `tab.comum.leitor.quadro_em("/acervo/" + item["arquivo"], item["t"])` |

- `indice.json`: `{"quadros": [{"id": "q06", "arquivo": "canal/video.mp4", "t": 45.4, "png":
  "quadros/q06.png", "largura": 1920, "altura": 1080, ...}, ...]}` (40 itens em cada).
- O gabarito: `{"quadros": {"q06": {...}, ...}}`, chaveado pelo **mesmo `id`** do índice. Em cada
  quadro:
  - `braco`: `"sim"` ou `"nao"`; use **só** `"sim"`;
  - `nut`: `[x, y]`, ou a palavra `"fora"` (o nut não aparece na imagem);
  - `trastes`: lista de `[x, y]`, um ponto por traste marcado, **em ordem ao longo do braço**.
- **Nunca** escreva em `data/gold/` (é contrato do dono) nem no acervo.

## 3. O que fazer

Crie a pasta `data/saida/maos/troca_camera_unica/` e escreva **um** script `medir.py` nela. Não
edite nada em `tab/`.

1. **Para cada quadro com `braco == "sim"` e pelo menos 3 trastes**, leia a imagem (BGR).
2. **Rode o detector de mãos** do jeito que a base faz (copie de `_ler_maos` em
   `tab/maos/base_gpu.py`):

   ```python
   from tab.comum.gpu import trava_gpu
   from tab.maos.base import LADOS, ORIGEM, melhor_mao, pontos_da_mao
   from tab.maos.detector import DetectorMaos

   with trava_gpu("maos", "troca de mãos, 80 quadros, ~2 min"):
       detector = DetectorMaos("cuda")
       for ...:
           achado = detector.detectar(bgr, None)
           for k, lado in enumerate(LADOS):  # k = 0: esquerda, 1: direita
               mao = melhor_mao(achado["maos"], lado)
               # None = ausente; senão pontos_da_mao(mao) -> (21, 3) e ORIGEM[mao["origem"]]
   ```

3. **O eixo do braço, pelo gabarito**: o lado do nut é o lado em que os trastes ficam **mais
   afastados** entre si (as casas encolhem em direção ao corpo do violão).
   - Compare a distância entre os 2 primeiros trastes da lista com a distância entre os 2
     últimos. O lado da maior distância é o lado do nut.
   - Seja `a` o traste da ponta do nut e `b` o da outra ponta. Se `nut` for um ponto, use o
     `nut` como `a`.
   - Posição de um ponto `p`: `s(p) = (p − a) · (b − a) / |b − a|²` (0 no nut, 1 no último
     traste marcado).
4. **Posição de cada mão**: a mediana de `s` nos pontos 0, 5, 9, 13 e 17 que forem finitos.
5. **Classifique** cada quadro: `duas_maos` (`certo` se `s(mão 0) < s(mão 1)`, `trocado` se
   maior), `so_a_0`, `so_a_1`, `nenhuma`. Guarde a origem das duas mãos (1 = Wholebody,
   2 = MediaPipe) e o canal.
6. **Folha**: todos os `trocado` (até 12; se mais, sorteio com `random.Random(20261050)`), e
   mais 4 `certo` sorteados para comparação. Em cada um: os trastes do dono em verde, a mão 0 em
   vermelho, a mão 1 em azul, o texto com `s` e a origem de cada. Grave `folha.jpg`. **Olhe**:
   um "trocado" pode ser um violonista **canhoto** (a mão direita no braço). Canhoto não é erro
   do detector; conte-o à parte.

## 4. Regra de decisão (escrita antes de medir; não mude depois)

- **Taxa de troca** = `trocado` (sem os canhotos) ÷ `duas_maos` (sem os canhotos).

| resultado | conclusão |
| --- | --- |
| taxa ≤ 2 % | "raro: nada a mudar" |
| taxa > 2 % | "vale uma regra de correção pela geometria"; diga quantos quadros ela mudaria e quantos são MediaPipe |
| menos de 5 quadros com alguma mão do MediaPipe | escreva também: "o MediaPipe ficou pouco testado aqui" |

**Aceite da tarefa**: `medir.py` roda do zero e grava `resultado.json` (as contagens com
denominadores, por canal e por origem); `folha.jpg`, olhada; `relatorio.md` (seção 6).

## 5. Como não se perder (regras contra loop)

- Trabalhe na pasta principal; você só **cria** arquivos em `data/saida/maos/troca_camera_unica/`.
  Nada de `git`, nada em `tab/`, `tests/`, `docs/`, `data/gold/` ou no acervo.
- A GPU só dentro da `trava_gpu`. Se a trava esperar mais de 30 minutos, pare e relate (outra
  trilha está usando).
- **Um erro igual duas vezes**: pare, escreva o que tentou e entregue.
- **Não troque a definição** de "mão no braço" depois de ver o número. Se achar que ela falha,
  escreva por quê, com um quadro da folha.
- Não procure outros quadros nem outros vídeos: são esses 80.

## 6. Quando parar e o que entregar

Pare quando o aceite estiver completo, quando bater a seção 5, ou depois de 3 horas.

```text
# Troca de mãos em câmera única — relatório
## Resposta curta (3 linhas)
## Números ("X de Y"): duas_maos, certo, trocado, canhotos, so_a_0, so_a_1, nenhuma
## Por origem (Wholebody × MediaPipe) e por canal
## O que vi na folha
## Conclusão pela regra da seção 4
## Limites
```

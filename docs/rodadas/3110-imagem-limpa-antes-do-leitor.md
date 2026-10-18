# 3110 — A1: imagem limpa antes do leitor (critérios congelados antes da medida)

Frente A (imagem limpa antes do leitor), item A1 de `docs/pesquisa/partitura-frentes.md`,
seção 7. Briefing da onda 1 (`docs/pesquisa/partitura-onda1-briefings.md`). Regra 9 do
AGENTS.md: o recorte é parte da medida, então a limpeza é entrada do modelo.

## CA1 (reproduzido antes de mexer)

`python data/saida/partitura/diag/ca1/ca1.py` no container `docker.io/library/chorinho:dev`,
com a montagem da seção 6.1. As linhas batem com o bloco da seção 5.3, exceto a `E.`
(o `compassos_homr.json` não está no git). Saída em `fa_imagem/ca1/ca1.txt`.

Reprodução do `faixa_amarela/medir.py`: com faixa, **24 leem e 12 falham, de 36**.

## Conjuntos

- **Com faixa (36)**: recortes do piloto sem produto cuja entrada ampliada do `x2_margem`
  tem fração de pixels amarelos > 0,05. Origem: `recortes/<id>.png` (1×).
- Depois, só com a melhor variante: os outros 126 do piloto, e as 19 telas dos produtos e os
  21 do gabarito (R01–R21).

## Variantes (definidas no código, `tab/partitura_imagem.py`)

- **A1b**: o maior dos 3 canais de cada pixel (cinza pelo máximo de R, G e B).
- **A1c**: pixels com saturação > 0,20 e brilho > 0,40 (HSV) viram branco.
- **A1d**: moldura branca de 50 px no recorte 1×, antes de o Audiveris ampliar 2×.
- **A1a** (mediana de N = 15 quadros em [t0, t1]): **não rodada nesta rodada**. Lê vídeo, e
  só entra depois que A1b, A1c e A1d forem medidas, um vídeo por vez.

## Medida e aceite (congelados)

- **Com faixa**: de 24/36 para **30/36 ou mais**.
- **Os 143 que já leem** (piloto, `audiveris/x2_margem`): **nenhum** passa a falhar.
- **CA2**: em R01–R12, com homr confirmado pela tab, certas ≥ 528 e altura errada +
  inventadas ≤ 7; nas 19 telas, certas ≥ 727, inventadas ≤ 7, altura errada ≤ 9. A moldura
  muda as coordenadas, então ela sai antes de comparar com o gabarito.
- **Conferência do dono** dos recuperados: 0,95 ou mais dos símbolos certos. Não chamar o
  dono; a ferramenta fica pronta na porta 8123, numa cópia.
- **Ganho** em pelo menos 2 vídeos. Se o ganho só aparecer no mela, relatar: não passa no CA4.
- **Tinta perdida** dentro da pauta na A1c: medida, com casos olhados.

## Ordem

1. A1b, A1c e A1d sobre os 36 com faixa (não leem vídeo).
2. Melhor variante ou combinação sobre os 126 do piloto e sobre R01–R21 e as 19 telas.
3. A1a, um vídeo por vez, só depois, para não disputar o HD com a D1.

## Resultado

Medido em 2026-10-17, uma variante por vez, nos 36 com faixa (Audiveris x2_margem, uma
execução cada; `fa_imagem/variantes/<v>/resumo.json`):

| variante | lê (de 36) | quebra (lia e não lê mais) | recupera (não lia e lê) |
| --- | ---: | ---: | ---: |
| sem limpeza (base) | 24 | — | — |
| A1b (maior dos 3 canais) | 24 | 0 | 0 |
| A1c (HSV: S > 0,20 e V > 0,40 viram branco) | 23 | 1 | 0 |
| A1d (moldura branca de 50 px) | **25** | 1 | 2 |

Critério de aceite: 30/36 ou mais. **Nenhuma variante passa.** A melhor é a A1d, com
+1 no saldo. Como a A1d quebra 1 recorte que lia, o ganho líquido de leitura é +1.

Não medidos ainda: A1a (mediana de 15 quadros, precisa de vídeo) e a combinação das variantes
(o briefing manda testar a melhor combinação depois das variantes sozinhas). Os outros 126 do
piloto e os gabaritos R01–R21 e as 19 telas não foram rodados, porque a variante não atingiu
o limiar.


## A1a (mediana de 15 quadros) e combinação d + b (2026-10-17)

**A1a.** Rodada com `tab/partitura_imagem_mediana.py --variante a`. Dos 36 recortes com faixa,
**30 não puderam ser avaliados**: o vídeo de origem não existe no acervo com o nome do piloto
(11 do `lonelypicker` e 19 do `mela`, canal ギタロー). `quadro_em` não devolve quadro, e o
registro sai com "nenhum quadro". O acervo mudou desde o piloto. **Isto precisa de você:** onde
estão esses vídeos (ou se foram renomeados ou removidos).

Nos **6 recortes avaliados**: 6 de 6 leem, igual à base. Recuperou 0, quebrou 0. Conclusão: a
A1a não recuperou nada no que foi avaliado. Os outros 30 ficam sem medida.

**Combinação d + b** (a única prevista, uma vez, seguindo a regra do dono: a A1a não recuperou
nada, então d com b). Ordem do código: o maior dos 3 canais (b) e depois a moldura de 50 px
(d). Resultado nos 36 recortes (não depende de vídeo): **25 de 36 leem** (base 24).
Recuperou 2, quebrou 1. Igual à d sozinha: a b não acrescenta nada à d.

**Encerramento.** A A1 fecha com o que der, sem novas combinações. A variante final sem
medida nos 30 vídeos ausentes é um limite declarado, não um zero.


## Encerramento da A1 (2026-10-17)

Critério de aceite: 30 de 36. **Não atingido.** Melhor resultado medido: 25 de 36 (d e d+b).
Pela regra, a A1 fecha aqui. Não houve nova combinação.

Resumo por variante (36 com faixa): base 24; A1b 24; A1c 23; A1d 25 (recupera 2, quebra 1);
A1a 6 avaliados de 6, sem medida em 30 (vídeo ausente no acervo); d+b 25 (recupera 2, quebra 1).

Pendências de você, não da A1: (1) localizar os vídeos ausentes (11 do lonelypicker, 19 do mela)
para medir a A1a nos 30; (2) decidir se a A1d (moldura) vira entrada do leitor ou se a A1
é encerrada sem alteração. Nenhuma das duas mexe no `tab/partitura_*.py` existente.

Sem conferência do dono: a A1d recuperou 2 recortes; a conferência deles (até 6 recortes na
porta 8123) só faz sentido se você decidir que a A1 avança. Nenhum item foi montado.


## Busca dos vídeos ausentes (2026-10-17, depois do encerramento)

- **`lonelypicker` (11 recortes, "[free tab] (everything i do) i do it for you - bryan adams"):**
  o dono apagou esse vídeo do acervo (como fez com outras músicas que não se adequavam). O arquivo
  `sky guitar/(everything i do) i do it for you - fingerstyle lesson + tab.mp4` já estava lá e não é
  o mesmo vídeo: não há candidato. Os 11 recortes ficam sem medida.
- **`ギタロー` / mela (19 recortes, "【無料タブ譜】mela! - 緑黄色社会"):** nenhum arquivo com "mela" ou
  "緑黄色社会" no nome. Sem candidato. Provavelmente removido do acervo.

Os 30 recortes continuam sem medida. A A1 permanece encerrada.

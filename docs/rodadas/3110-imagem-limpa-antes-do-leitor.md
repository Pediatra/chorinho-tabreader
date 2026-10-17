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

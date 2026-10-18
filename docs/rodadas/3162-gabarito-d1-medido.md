# 3162 — D1: o gabarito sorteado, conferido pelo dono

Frente D, item D1 (`docs/pesquisa/partitura-frentes.md`, seção 7). Sorteio na 3160 (commit
`27e40dbf`, lista final `86133016`), leitura e itens na 3161. O dono conferiu os 35 itens na
porta 8121 em 2026-10-18 (`data/gold/partitura/leitura_d1.json`).

## Resultado

- **40 vídeos sorteados, 13 canais.** 5 recortes ficaram sem leitura do Audiveris (12,5 %) e não
  foram à conferência: el choclo P02a, 3 middle eastern P03a, phantom P02a, minuet P03a, mario
  wonder P19a. Contam como falha de leitura, à parte.
- **35 conferidos, 9 canais.**

| conjunto | lidos | certos | figura errada | não existe | faltando | certos/lidos | certos/(certos+faltando) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 35 recortes | 1589 | 1528 | 13 | 48 | 158 | **0,962** | **0,906** |
| sem o 空も飛べるはず P07a | 1563 | 1502 | 13 | 48 | 158 | 0,961 | 0,905 |

- Altura errada: 0. Clave errada em 2 (sargento cabral P05a, 空も飛べるはず P07a); armadura certa
  em todos.
- O 空も飛べるはず P07a tem a observação "praticamente tudo errada", mas as 26 notas ficaram no
  estado padrão (certo): a contagem por nota dele não vale, por isso a segunda linha.

Por canal (35 recortes):

| canal | recortes | lidos | certos | faltando | certos/(certos+faltando) | certos/lidos |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| guitar dell'arte | 7 | 537 | 507 | 100 | 0,84 | 0,94 |
| sky guitar | 8 | 290 | 287 | 8 | 0,97 | 0,99 |
| robert lunn | 7 | 229 | 219 | 24 | 0,90 | 0,96 |
| iwaki | 4 | 138 | 128 | 4 | 0,97 | 0,93 |
| pablo romé | 3 | 103 | 98 | 18 | 0,84 | 0,95 |
| serge kottelat | 2 | 110 | 110 | 3 | 0,97 | 1,00 |
| transcriptor | 2 | 89 | 86 | 0 | 1,00 | 0,97 |
| paolo d'angelo | 1 | 67 | 67 | 1 | 0,99 | 1,00 |
| ギタロー ⧸ guitarous | 1 | 26 | 26 | 0 | 1,00 | 1,00 |

## Comparação com os gabaritos anteriores

| gabarito | recortes | certos/lidos | certos/(certos+faltando) |
| --- | ---: | ---: | ---: |
| P1 (3004), R01–R21 | 21 | 0,976 | 0,916 |
| sem produto (3023) | 3 | 0,989 | 0,815 |
| **D1 sorteado** | 35 | **0,962** | **0,906** |

A amostra sorteada confirma o retrato do P1: o Audiveris quase não inventa, e o que falta é
cobertura. Somando a falha de leitura (5 de 40), cerca de 1 em cada 5 notas do acervo com pauta
não sai do Audiveris.

## Observações do dono

- therru's song P13a: a barra de ligação não aparece nas colcheias de baixo. A régua não mede
  barra de ligação; fica como limite.
- flow my tears P06a: "inventou muito aqui"; a partitura tem fundo transparente. Candidato a
  tratamento de imagem à parte.
- 空も飛べるはず P07a: "praticamente tudo errada" (clave lida como fá).

## Ferramenta

Dois defeitos achados e corrigidos durante a conferência: a imagem dos recortes da frente D não
era servida (`f254a021`), e id com acento ou ideograma não achava a imagem (`1c1689b4`).

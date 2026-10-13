# Rodada 1008: braço pela música fora do MVP

Data: 2026-10-13. Trilha das mãos, M3c (continua a [1007](1007-braco-pela-musica-estabilizado.md)).

## Objetivo

Medir a calibração do braço pela música (consenso estabilizado da 1007) em quadros do
gabarito do braço (`data/gold/maos/braco.json`) fora do vídeo do MVP.

## Quais quadros dão para medir

A calibração precisa de notas com `t_ini` na mesma cena (mesma câmera) do quadro do dono.

| quadro | vídeo | resultado |
| --- | --- | --- |
| q16 | sky guitar, noturno nº 20 de Chopin | medido: 452 notas pisadas na cena 254,5–615,6 s |
| q06 | leonardo ramos, milonga | produto com **0 de 835** notas com tempo (marcador incoerente) |
| q11 | robert lunn, chim chim cher-ee | produto com **0 de 11** notas com tempo |
| q07 | sky guitar, the scientist | quadro da abertura (braço diagonal, tela cheia); as 395 notas pisadas estão em outra câmera (braço horizontal num painel; matchTemplate 0,22) |

Fora do sky guitar, a calibração pela música depende de a trilha da tablatura entregar
tempo naquele canal. Hoje só o q02 e o q16 do gabarito do braço são medíveis.

## q16 contra o dono

`python -m tab.maos_braco_fora --produto data/saida/maos/m3d/q16_cena.json --pontas
data/saida/maos/m3d/pontas_q16.json --quadro q16`. 357 de 452 notas inliers; estabilidade
entre os 3 conjuntos de sementes: mediana 0,17 px, máximo 1,9 px.

| medida | q02 (MVP, 1007) | q16 |
| --- | --- | --- |
| trastes dentro de 1/4 de casa | 14/14 | **10/15** (1–10 bons; 11–15 fora, só 23 notas em casa ≥ 11) |
| fração mediana dos casados | 0,032 | 0,073 |
| nut (fração da casa 1) | 0,036 | **0,49** |
| corda 1 (fração do vão 1–6) | 0,11 | **0,35** |
| corda 6 | 0,07 | 0,19 |

A grade sai estável e errada: comprimida no sentido das cordas e curta no nut.

## Diagnóstico: a ponta do dedo não é o contato

Com uma H montada só dos cliques do dono (reprojeção dos cliques ≤ 2,9 px), cada nota
pisada foi ligada à ponta esquerda mais próxima e convertida para (u, v) do braço do dono.
O dono aqui é só observador.

- **Posição na casa** (0 = traste de baixo, 1 = traste da casa): q16 mediana 0,70; q02
  0,62. O 0,7 da calibração vale no q16, não no q02.
- **Desvio para a corda 6** (passos de corda): q16 +0,85 (cordas agudas ~+1,0), q02 +0,29.
  Com a ponta escolhida pela H da música, o vão 1–6 fica em 4,2 passos (q16) e 4,6 (q02) em
  vez de 5. É a compressão.
- O desvio depende da janela de aceite; o teste não é limpo. Script e figuras:
  `data/saida/maos/m3d/diag/`.

## Recuo da ponta sobre o DIP (reprovado)

Hipótese: contato = ponta + recuo · (DIP − ponta). `--recuo` em `tab.maos_braco_fora`
(padrão 0). Escolha **só no q02**; q16 é teste.

| recuo | q02 trastes | q02 nut | q02 média c1,c6 | q16 trastes | q16 nut | q16 c1 / c6 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 14/14 | 0,036 | 0,090 | 10/15 | 0,49 | 0,35 / 0,19 |
| 0,2 | 14/14 | 0,143 | 0,087 | 10/15 | 0,40 | 0,30 / 0,20 |
| 0,4 | 14/14 | 0,242 | 0,113 | 15/15 | 0,07 | 0,25 / 0,23 |
| 0,6 | 13/14 | 0,312 | 0,184 | 15/15 | 0,04 | 0,20 / 0,23 |
| 0,8 | 0/14 | 0,395 | 0,388 | 11/15 | 0,14 | 0,18 / 0,34 |
| 1,0 | 0/14 | 0,465 | 0,502 | 5/15 | 0,12 | 0,23 / 0,62 |

Pelo q02, o recuo escolhido é **0**: nenhum outro melhora as cordas sem piorar o nut. O
q16 melhora em 0,4–0,6, mas os dois quadros discordam e não há terceiro quadro para
desempatar. Recuo constante não é a correção. Anomalia não investigada: estabilidade de
0,0 px em vários recuos (os 3 conjuntos escolhendo a mesma H).

## Próximo

- Ajuste das 6 cordas pela imagem (pente), com a H da música como ponto de partida: no
  q16 as cordas são linhas claras nítidas sobre a escala escura.
- Mais quadros do dono no layout com tablatura do sky guitar (único canal com tempo hoje),
  para ter mais de dois quadros medíveis.

## Artefatos

- Código: `tab/maos_braco_fora.py`, `tab/maos_medicoes_braco.py` (`gabarito_dono` genérico),
  `tab/maos_calibrar_por_notas.py` (`pontas_com_recuo`). Commits `8e490947` e o desta rodada.
- Saídas: `data/saida/maos/m3d/` (produtos, cenas, pontas, `q16/`, `recuo/`, `diag/`, `q07/`).

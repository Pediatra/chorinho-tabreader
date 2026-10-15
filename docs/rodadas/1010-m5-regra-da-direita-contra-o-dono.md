# 1010 — M5: regra do dedo da direita contra a confirmação do dono

**Data**: 2026-10-14. Decisão de método: [1004](../decisoes/1004-m5-padroes-da-mao-direita.md)
(revisão "regra + confirmação").

## O que foi medido

O dono confirmou os 20 compassos da página (ímpares c01–c39, 5 por vídeo, sky guitar:
retrato brasileiro, noturno nº 20, lacrimosa, glimpse of us). 205 notas; 6 marcadas `l`
(ligada, sem ataque da direita) ficam fora do denominador → 199.

## Regra v1 (a que o dono viu pré-marcada)

154/199 (0,774). Erros concentrados em: corda 4 `p`→`i`, 3 `i`→`m`, 2 `m`→`a` (33 notas: o
i-m-a desce para as cordas 4-3-2 quando a corda 4 vem depois do bordão) e `a`→`m` em nota
repetida na mesma corda (7: o dono escreveu "I-M-A-M-A"). As janelas da v1 (0,25 s / 0,6 s)
quase não disparam no sky guitar, onde os ataques do arpejo vêm a cada 0,6–0,9 s.

## Variantes (`python -m tab.maos_regra_direita_medir`)

Grade de 32: `janela_polegar_s` × `janela_sequencia_s` × `alternar_ma` (depois de `a` na
mesma corda vem `m`). Saída em `data/saida/maos/m5/regra_v2_medicao.json`.

| variante (polegar, sequência, m-a) | acertos | noturno | glimpse | lacrimosa | retrato |
| --- | --- | --- | --- | --- | --- |
| v1 (0,25; 0,6; não) | 154/199 | 31/45 | 27/31 | 70/80 | 26/43 |
| melhor (1,0; 1,0; sim) | 173/199 | 36/45 | 26/31 | 74/80 | 37/43 |

**Deixando um vídeo de fora** (escolhe a variante nos outros 3, mede no quarto): **171/199
(0,859)**, +17 notas sobre a v1. Esse é o número honesto; o 173 é dentro da amostra.

Borda da grade (conferido à parte, dentro da amostra): polegar 1,5 → 173–174; 2,0 → 177–178.
A janela do polegar não acha um ótimo: na prática "corda 4 depois de um bordão vai de `i`"
vale quase sempre nestes vídeos. Não fixei 2,0: sobe dentro da amostra, e o dono avisou que
isso **varia de violonista para violonista** (no lacrimosa e no glimpse a corda 4 foi de
polegar). Essa escolha (corda 4: `p` ou `i`) é a candidata para a visão.

Matriz da melhor (linha dono, coluna palpite): p 45/4/0/0; i 3/40/4/2; m 0/2/47/5;
a 0/0/6/41.

## Não repetir / limites

- 20 compassos, 4 vídeos, um canal: o ganho é indicativo. A validação de verdade são os 20
  compassos pares, confirmados com a regra nova pré-marcada (com o viés de ancoragem de
  qualquer palpite pré-marcado).
- Ligadas (6) não se preveem pela corda: dependem do símbolo da tablatura (`h`, `p`, `/`),
  que o leitor ainda não classifica (`tecnica` é `None` no produto).

## Adendo (2026-10-15): validação nos 20 pares

O dono confirmou os 20 compassos pares (c02–c40) com a v2 pré-marcada. 219 notas, 3 `l` →
216 pontuadas. **v2: 172/216 (0,796); v1 nos mesmos compassos: 149/216 (0,690).** Fora da
amostra a v2 ganha +23 notas, mas fica abaixo do 0,859 estimado (deixando um vídeo de fora):
o noturno cai para 33/65. Erros mais comuns: corda 2 com `i` (dono) onde a regra deu `m`/`a`
(12), e `a`→`m` na sequência (8). Pelas observações do dono, em acordes e notas alternadas
rápidas o violonista prefere i-m "pela coordenação motora", e o polegar repete (p-p-p) por
comodidade conforme a distância ao baixo — preferências do violonista, não da tablatura.

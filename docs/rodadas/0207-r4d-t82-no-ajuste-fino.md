# 0207 — R4d: a T8.2 no ajuste fino, a T8.3 de teste

Segue a [0205](0205-faixa-nao-sei.md) e a [0206](0206-a2-arco-como-objeto.md), em que o piloto
do arco reprovou. Escrito **antes** de treinar.

## Por que

- Fora de amostra, a faixa "não sei" com o `_atqg` deixa passar 15–16 das 76 notas não atacadas
  da T8.3 (20–21 %).
- No R4a, o que mais ajudou foi a técnica real dos ouros no ajuste fino: o "sim" falso nos ouros
  foi de 80 % para 39 %.
- A T8.2 tem 34 telas de 19 canais que nenhum ouro tem, todas conferidas pelo dono.

## A mudança (só esta)

- `data/saida/n4/treinar_ft.py --t82`: as telas da T8.2 (`n4/cache_t82`, de `extrair_t82.py`)
  entram no ajuste fino de **todas** as dobras, com a técnica do gabarito do dono, do mesmo jeito
  que os ouros no R4a.
- O resto é igual ao R4b: `--ataque`, o gerador do R4b (`_atqg`), 3000 passos, as mesmas dobras.
- Notas sem ataque supervisionadas: 87 sem a T8.2, 132 com ela (`h` 30, `p` 31, `orn` 37, `lig`
  16, `/` 13, `\` 5). Atacadas: 2600 → 4093.
- 15 treinos (5 dobras × 3 sementes), com o nome `_atqt_s<semente>`, no roteiro
  `data/saida/tab_rotulo/r4d/rodar.sh`.

**Atenção:** o gerador de hoje não é o do R4b. Ele tem o G8–G10 da 0204, que não foi adotado, e a
gravação dos arcos da 0206, que não muda o sorteio. O treino usa o gerador como está no commit,
então a comparação com o `_atqg` mistura as duas mudanças. Para não misturar, o G8–G10 é desligado
antes de treinar: as chances voltam ao valor do R4b (`P_APERTADO` 0,2, `P_TRACO` 0,
`P_SLIDE_CURTO` 0, `P_ARCO_RASO` 0, `PAR_LONGO_MAX` 4). A distribuição é a do R4b, mas o
sorteio não é idêntico, porque os testes do G8 e do G9 ainda gastam um número aleatório.

## Teste

- **T8.3**: 33 telas, 17 canais, 73 notas não atacadas, em nenhum treino. Lida pela dobra 0.
  É **a** medida.
- **Ouros**: pela dobra fora. Servem só para escolher os limiares, como antes. O da técnica é o
  menor com "não" em atacada até 1 %. O `L` da faixa é o menor com custo até 5 %.
- A T8.2 deixa de ser teste, porque entra no treino.
- **Base**: o `_atqg` com a faixa, na T8.3: 16 · 15 · 16 /76.

## Aceite (o do plano)

Na T8.3:

- "sim" falso **≤ 5 %**;
- "não" ou "não sei" em atacada **≤ 10 %**;
- a casa não piora além da amplitude do `_atqg` (1466–1472 de ~1480).

**Pare se** o "sim" falso na T8.3 não cair abaixo de 15/76. Nesse caso, mais gabarito do mesmo
tipo não paga o treino, e a rota volta ao dono.

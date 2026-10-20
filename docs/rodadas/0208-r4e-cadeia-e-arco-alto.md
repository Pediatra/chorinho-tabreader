# 0208 — R4e: cadeia sob um arco só e arco alto no gerador

Segue a [0207](0207-r4d-t82-no-ajuste-fino.md). Escrito **antes** de treinar.

## Por que

Das 8 notas "não" da T8.3 que escapam sem dúvida de gabarito, 6 têm o arco acima do sistema, e o
sinal da técnica nelas fica abaixo de 0,01. O gerador não desenha esses arcos:

- **G11, cadeia**: um arco só sobre 3 a 5 notas da mesma corda, como `6-8-6-5` com "H P P" em
  cima (Shin Izumi). Hoje cada par h/p tem o seu arco.
- **G12, arco alto**: o arco curto, alto e estreito acima da corda 1 (Transcriptor). Hoje a curva
  vai de 0,15 a 0,7 passo.

## A mudança (só esta)

Em `tab/sintetico_sistema.py`:

- `P_CADEIA = 0,25` por sistema. Metade das cadeias vai para a corda 1 (`P_CADEIA_CORDA_1`).
  - As casas andam de 1 a 3 por nota. Da 2ª nota em diante, a técnica é "orn", porque o conversor
    do gabarito chama de mordente a região de legato com 3 notas ou mais.
  - O arco vai do centro da 1ª nota ao centro da última, de 0,6 a 1,1 passo acima da corda, com
    curva de 0,2 a 0,7 passo.
  - Na corda 1, metade das cadeias tem as letras H/P maiúsculas acima do arco.
- `P_ARCO_ALTO = 0,25`: o arco de h/p/tie/mordente de três notas que não é raso ganha curva de
  0,8 a 1,4 passo.
- Em 300 sementes: 61 sistemas com cadeia, 20 com letras e 66 com arco alto.

O resto é igual ao R4d: `--ataque --t82`, 3000 passos, 15 treinos (5 dobras × 3 sementes), com o
nome `_atqe_s<semente>`, no roteiro `data/saida/tab_rotulo/r4e/rodar.sh`.

## Teste

- **T8.3** pela dobra 0, com os limiares escolhidos só nos ouros, como na 0207.
- **Base**: o `_atqt`, 15 · 15 · 16 /77, casa 1480–1482.
- **Alvo**: as 6 notas de arco acima do sistema. Conta quantas passam a "não" ou "não sei" em 2
  sementes ou mais.

## Aceite e parada

- **Aceita** se o "sim" falso na T8.3 cai na soma das 3 sementes (de 46 para 43 ou menos) e se a
  casa não fica abaixo de 1478 em nenhuma semente.
- **Pare se** nenhuma das 6 notas-alvo muda. Nesse caso, o arco acima do sistema não é falta de
  exemplo no gerador.
- O `DETECTOR_CALIBRADO` só muda se aceitar.

## Resultado (2026-10-20)

15 treinos, de 13h15 a 16h44, em `data/saida/tab_rotulo/r4e/`. Medidas em `r4a/medida_atqe_s*.json`,
`r4c/medida_t83_atqe.json` e `r4e/folha_erros_t83_atqe.log`.

- Limiares escolhidos nos ouros: técnica **0,25** (no `_atqt` era 0,15, porque mais notas atacadas
  passam a "não") e `L` 0,02.
- **T8.3, "sim" falso com a faixa: 15 · 17 · 17 /77–78**, com soma 49 (no `_atqt`, 46). O custo
  sobe para 37–41 /1409 (no `_atqt`, 31–34). A casa fica em 1479–1482.
- **Notas-alvo: nenhuma das 6 muda.** O sinal da técnica segue entre 0,0002 e 0,011.
- **A regra de parada dispara.** O arco acima do sistema não é falta de exemplo no gerador: com
  cadeias e arcos altos no sintético, o modelo continua sem ver esses arcos reais. G11 e G12 ficam
  no código, desligados (`P_CADEIA = 0`, `P_ARCO_ALTO = 0`). O `DETECTOR_CALIBRADO` segue com o
  `_atqt_s1`.
- O que sobra para a rota da técnica (decisão do dono):
  - as 7 dúvidas de gabarito da 0207;
  - um rótulo de ataque que não dependa de ver o arco nesses canais, por exemplo "nao_sei" para
    os canais com arco acima do sistema.

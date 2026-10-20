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

## Resultado (2026-10-20)

15 treinos, de 07h21 a 12h54, em `data/saida/tab_rotulo/r4d/` (de 788 s a 2216 s cada, com a GPU
dividida). Medidas: `r4a/medida_atqt_s{1,2,3}.json` (ouros) e `r4c/medida_t83_atqt.json`
(T8.3, `r4d/medida_t83_atqt.log`).

**Limiares, escolhidos só nos ouros:** técnica 0,15 e `L` 0,02, os mesmos do `_atqg`.

| | `_atqg` | `_atqt` |
| --- | --- | --- |
| ouros, "sim" falso a 0,15 (sem faixa) | 13 · 11 · 15 /85 | 8 · 11 · 7 /85 |
| **T8.3, "sim" falso com a faixa** | 16 · 15 · 16 /76 | **15 · 15 · 16 /77** |
| T8.3, custo (atacada sem "sim") | 37 · 38 · 32 /~1403 | 31 · 34 · 31 /~1410 (2,2–2,4 %) |
| T8.3, casa certa | 1466–1472 /~1480 | **1480–1482 /1486–1487** |
| T8.3, atacada não lida | 11–13 | 5–6 |

- **A regra de parada dispara:** o "sim" falso na T8.3 não cai abaixo de 15/76. A T8.2 no
  treino não ensina as notas não atacadas de canais novos. Mais gabarito do mesmo tipo não paga o
  treino, e a rota da técnica volta ao dono.
- O resto melhora: a casa sai da faixa do `_atqg` para cima, e as notas atacadas que o modelo não
  lê caem para a metade. Os ouros também melhoram, mas eles estão no treino das outras dobras.
- **Produto:** `ataque_rotulo.DETECTOR_CALIBRADO` passa para o `_atqt_s1` da dobra 0. Os limiares
  são os mesmos, o "sim" falso empata e a casa e a leitura melhoram. O `DETECTOR_PADRAO` não muda.

## Onde estão os erros que sobram (2026-10-20)

`data/saida/tab_rotulo/r4d/folha_erros_t83.py`: as notas "não" da T8.3 que a faixa lê como "sim" em
2 sementes ou mais. São 15, as mesmas no `_atqg` e no `_atqt` (`r4d/erros_t83/`, folhas em
`folha_escapa_1.png`, `folha_dono_prolongamento.png` e `folha_resto.png`).

- **7 são dúvida de gabarito.** São `t14-n10`, `t14-n27` e `t32-n7`, `n8`, `n9`, `n10`, `n24`.
  - O dono as mudou no modo ataque para "não, prolongamento".
  - Em todas, o arco **sai** da nota para a direita e não chega em outra nota. Pela regra do
    dono, isso é sustentada, ou seja, atacada.
  - Na Room 335, o dono marcou 25 notas assim como "sim, sustentada". Fica para o dono decidir.
- Sem essas 7: o `_atqg` deixa passar 9 · 8 · 9 /69–70 e o `_atqt` 8 · 8 · 9 /70 (11–13 %).
- **Das 8 que sobram, 6 têm o arco acima do sistema** (sinal da técnica abaixo de 0,01).
  - Em 3 delas, um arco só cobre uma cadeia de 4 notas, com "H P P" em cima (Shin Izumi,
    `t24-n13`, `t24-n14`, `t25-n16`).
  - Em 3 delas, o arco é alto e estreito, acima da corda 1 (Transcriptor, `t28-n17`, `n49`, `n50`).
  - O gerador não tem nenhum dos dois: cada par h/p tem o seu arco, e a curva vai até 0,7
    passo. Isso é testado na [0208](0208-r4e-cadeia-e-arco-alto.md).
- As outras 2:
  - `t13-n20`: um tie que chega numa nota entre parênteses `(1)`.
  - `t22-n56`: um "gliss." cujo slide é lido, mas a regra do slide sem origem o põe como "sim".

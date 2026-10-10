# Rodada 0007: caixa de tablatura por quadro (Fase 7.1)

Data: 2026-10-10. Comando da medição: `python -m tab.presenca_aval` (container).
Gabarito: `data/gold/presenca_quadros.json` (144 quadros, rótulo do dono).

## Pergunta

A Fase 7.0 chamou de falso positivo 41 quadros em que o detector disse "há tablatura".
O dono revisou os 41 e marcou só 9 como não tablatura (FP02, FP03, FP09, FP10, FP11,
FP30, FP31, FP37, FP38). A pergunta que vale para o produto é outra: **a caixa desenhada
cobre tablatura?** Esta rodada mede isso, por quadro, e procura um critério de escolha do
painel que tire os 9 erros sem perder a tablatura certa.

## Gabarito (o que mudou em relação à 7.0)

- 144 quadros: 118 com caixa (109 sobre TAB, 9 não), 26 sem caixa (6 FN, 20 VN).
- `tablatura_no_quadro` = há TAB em alguma região do quadro: 124 quadros.
- Os 9 erros têm TAB no quadro inteiro, numa faixa que a caixa não cobre. Conferido na
  imagem: FP02, FP03, FP09, FP10, FP11 (TAB na faixa `base`) e FP30, FP31, FP37, FP38 (TAB de
  6 cordas embaixo da pauta; a caixa cobre só a pauta). A 7.0 tinha os quatro últimos como
  "sem TAB"; o quadro tem, então o rótulo de quadro foi corrigido para `true`.
- Métrica nova: **precisão de caixa** = caixas sobre TAB / caixas;
  **revocação de caixa** = quadros com TAB que receberam caixa sobre TAB / quadros com TAB.
  A presença por quadro fica como referência.

## Medido no código atual (HEAD + working tree, sem alteração)

| | caixas | corretas | precisão | revocação |
| --- | --- | --- | --- | --- |
| total | 117 | 108 | **0,923** | **0,871** (108/124) |

Por canal (caixas / corretas): guitar dell'arte 5/3 · iwaki 38/34 · kimny's guitar 8/6 ·
leonardo ramos 6/6 · mr. tabs 8/7 · pablo romé 5/5 · paolo d'angelo 3/3 · sky guitar 44/44.

Presença por quadro (só referência): VP 117, FP 0, VN 20, FN 7. Precisão 1,000 e revocação
0,944. Ou seja: **todo quadro com caixa tem TAB em algum lugar**. O erro está na região da
caixa, não na presença. O 0,653 por quadro da 7.0 comparava o quadro com rótulos por recorte
(`portao.json`); por isso parecia pior do que é.

Diferença para a 7.0 (109/118 = 0,924): FP12 perdeu a caixa. A 7.0 desenhava
`[85,290,1835,518]` sobre a TAB; hoje o detector não desenha nada nesse quadro. Não
investiguei o commit que mudou isso; é regressão de código posterior à 7.0.

## O que os 9 erros têm em comum

- Todos caem na **reserva** do `painel.escolher` (`escolher_rapido`, faixas fixas
  topo/meio/base). O localizador de quadro inteiro (`candidatos_quadro`) não acha nada
  nesses quadros.
- Na reserva a escolha é a **uniformidade do fundo**, e ela penaliza a tinta: a TAB densa tem
  mais tinta, então perde para o braço liso. Exemplo, FP02: topo u=0,935 (braço), base
  u=0,795 (TAB).
- Na faixa `base` estava a TAB nos 9 quadros, e o papel branco da faixa (fração de pixels
  com cinza > 200) a separa do braço (FP02: topo 0,137, base 0,688).

## Candidato C1 (medido, NÃO adotado)

C1: na reserva, ordenar as faixas por **fração de papel branco** em vez de uniformidade
(a primeira faixa aceita pelo `criar` ganha). Medido em memória, sem editar `tab/painel.py`,
nos 144 quadros.

| rótulo | caixas | corretas | precisão | revocação |
| --- | --- | --- | --- | --- |
| dono (VN15..20 = não tablatura) | 126 | 120 | **0,952** | 120/124 = **0,968** |
| se VN15..20 tiverem TAB | 126 | 125 | 0,992 | 125/129 = 0,969 |

- Acerta 7 dos 9 erros (FP03, FP09, FP10, FP11, FP30, FP31, FP37 passam para a TAB da faixa
  `base`). Erra FP38: a caixa nova `[727,850]` cai sobre a pauta; a TAB começa perto de y=900.
- Perde a caixa de FP02 (fica sem caixa, uma FN a menos de precisão, uma a mais de revocação).
- Ganha caixa sobre TAB em FN01, FN03, FN04, FN06 e recupera FP12.
- Os 5 VN15, VN17, VN18, VN19 e VN20 viram caixa **sobre TAB visível** embaixo do quadro. O
  `portao.json` os rotulou `nao_tablatura` por recorte. Mantive o rótulo do dono no
  gabarito e os listei em `suspeitas_rotulo_nao`; a decisão é do dono.
- FP10 e FP11 (caixas novas) foram tratados como TAB sem conferência de cada um; FN03, FN04,
  FN06 e FP12 foram conferidos na folha.

**Aceite (precisão de caixa >= 0,98): não atingido (0,952 sob o rótulo do dono).** Por
isso não adotei o C1. Não rodei as checagens do MVP (`tab.telas` retrato, `tab.video` +
`tab.avaliar_video`, `tab.avaliar` oficial 1/2/3): só faz sentido com o aceite de caixa
atingido. Se o dono confirmar que VN15..20 têm TAB, o C1 vai a 0,992 e passa a exigir essas
checagens antes de qualquer adoção.

## Não separa (não repetir)

| tentativa | efeito |
| --- | --- |
| uniformidade do fundo como critério da reserva | erra os 9 (é o critério atual) |
| preenchimento médio dos tokens (área / caixa do token) na faixa | TAB 0,46 a 0,91 contra pauta 0,49 a 0,59: sobrepõe |
| `tab.digito` (P de algarismo por token) | marca as cabeças de nota da pauta como algarismo (p≈1,0 nas 4 pautas) |

## Dúvidas para o dono

1. VN15, VN17, VN18, VN19 e VN20: TAB visível embaixo. Confirmar o rótulo (muda o aceite).
2. FP38: a caixa cobre só a pauta. Confirmar.
3. FP12 perdeu a caixa de 7.0 para 7.1: regressão de código a investigar.

Artefatos (não versionados): `data/saida/presenca_7_1/` (medições JSON, folhas e os
scripts de diagnóstico usados aqui).

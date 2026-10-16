# 0103 — A cabeça de técnica acha o ligado abaixo do limiar? (F0.3)

Frente 0 de `docs/pesquisa/tablatura-frentes.md`, seção 7. Branch `tab/f0-regua-tecnica`.
Pergunta da seção 4 do briefing: o sinal do ligado existe abaixo do limiar, ou o ajuste fino
apagou?

Este documento foi escrito **antes** de rodar a medida. Os parâmetros abaixo são a priori. Se
uma variante for escolhida depois de ver o resultado, ela vale só como diagnóstico.

## Entradas

- **Regiões**: as marcas de ligado do dono, em todas as telas com marca de técnica (os 4 ouros
  e a T8.2), com classe da régua (`tab.tecnica_regua.classe_do_dono`) em `h`, `p`, `mordente` ou
  `prolongamento`. São 139 marcas (regra da rodada 0101). Telas sem marca não entram.
- **Quadro**: o quadro de cada tela, lido como na rodada 0101 (`leitor.quadro_em`,
  `painel.escolher_ou_mascara`).
- **Modelos** (sempre no mesmo quadro e no mesmo recorte do painel):
  - **A**: `artefatos/detector_tab_v3_s1` (só sintético, ponto de partida do ajuste fino).
  - **B**: `artefatos/detector_tab_final_s1_ger` (produto).
  - **C** (só para as fontes de ouro, a dobra que não viu o vídeo, como na régua): LVR →
    `detector_tab_v3ft_d1`; FTP → `detector_tab_v3ft_d3_ger`; EOB e R335 →
    `detector_tab_v3ft_d4_ger`. Telas T8.2 não têm modelo C.
  - Não entra o modelo novo que a sessão principal está retreinando. Sem GPU.

## Escore por região (a medida)

Para cada região e cada modelo:

- Varre-se a cabeça de técnica (sigmóide, 6 cordas, colunas da janela normalizada) e pega-se a
  coluna cujo `x` no quadro cai em `[x0 − 0,5 passo, x1 + 0,5 passo]` (a folga da régua), nas
  cordas `min(cordas)..max(cordas)` da região.
- Três escores por região: `h`, `p` e `lig` (o máximo sobre as colunas e cordas).
- Escore **esperado** da região: `h` → `h`; `p` → `p`; `mordente` → máximo de `h`, `p` e `orn`;
  `prolongamento` → `lig`.
- Escore **ligado** da região: máximo de `h`, `p` e `lig`, qualquer que seja a classe.

Não se usa o limiar de centro (0,5) para casar: a pergunta é justamente se o escore existe antes
desse corte.

## Limiares

**0,5** (o limiar de produção, `tab.detector_tab.LIMIAR`), **0,3** e **0,1**. Conta-se, por
modelo e por limiar, quantas regiões têm o escore esperado (e o ligado) **≥ limiar**, e a
distribuição dos escores (quantas passam de 0,5, de 0,3 e de 0,1).

## Respostas (o que conta como cada uma)

- **Q1: o v3_s1 marca mais ligados que o produto?** Compara-se o número de regiões com escore
  esperado ≥ 0,5 em A e em B. Se A > B, o ajuste fino apagou a técnica (como apagou o X
  abafado).
- **Q2: falta cobertura do gerador?** Se nenhum dos dois modelos tem escore esperado ≥ 0,1 na
  maioria das regiões, o sinal não existe na cabeça de técnica.
- **Q3: é limiar?** Se o escore esperado existe abaixo de 0,5 (≥ 0,1 e < 0,5) em muitas regiões,
  o problema é o corte, não a rede.

A conclusão sai dos três números juntos, por classe e por fonte. Classe com menos de 10 marcas
(harmônico, bend) não entra.

## Gravação

Saída: `data/saida/tab_frentes/f0_tecnica/cabeca_ligado.json` (por região: fonte, tela, classe,
escores A/B/C, limiares passados). Recortes de regiões com escore esperado ≥ 0,5 em A e não em B
(se houver), para olhar.

## Pegadinhas a checar

- O produto viu as notas dos 8 ouros no treino; por isso Q1 se lê com a leitura de C ao lado.
- A técnica nunca foi supervisionada em tela real: declare que o modelo B é o produto, não uma
  medida independente da técnica.
- Dropout: os modelos são carregados em `eval()` (como em `detector_tab.carregar`).

## Resultado

Código: `tab/tecnica_cabeca.py` (testes `tests/test_tecnica_cabeca.py`). Saída:
`data/saida/tab_frentes/f0_tecnica/cabeca_ligado.json`. CPU, sem GPU. Os parâmetros são os
pré-registrados acima, sem mudança. Uma execução (não repeti; a forward em CPU é determinística,
mas não verifiquei por hash).

Marcas de ligado medidas: **139** (EOB 15, FTP 14, R335 72, LVR 1, T82 37). Quadro lido em todas
(nenhuma tela sem quadro). Classes: prolongamento 80, h 29, p 19, mordente 11.

Modelo C (dobra que não viu o vídeo) só existe nas fontes de ouro: **102** regiões (EOB 15,
FTP 14, R335 72, LVR 1). Nas 102, A e B também estão na tabela de mesma população.

### Escore esperado ≥ limiar (regiões que pedem a técnica)

| população | modelo | ≥ 0,5 | ≥ 0,3 | ≥ 0,1 |
| --- | --- | --- | --- | --- |
| 139 | A (v3_s1) | 14 | 36 | 80 |
| 139 | B (produto) | 13 | 26 | 69 |
| 102 (ouros) | A (v3_s1) | 11 | 30 | 66 |
| 102 (ouros) | B (produto) | 9 | 22 | 59 |
| 102 (ouros) | C (dobra) | 20 | 38 | 63 |

Escore **ligado** (h, p ou lig, qualquer classe) ≥ 0,5: A 22, B 20 (139 regiões).

Escore esperado por classe, ≥ 0,5 e ≥ 0,1 (A / B), 139 regiões:
h 29: A 0 / 7, B 1 / 5; p 19: A 0 / 3, B 0 / 2; mordente 11: A 1 / 9, B 3 / 8;
prolongamento 80: A 13 / 61, B 9 / 54.

Escore esperado ≥ 0,5 por fonte (139 regiões): EOB 0 (A, B, C), FTP 0 / 1 (A, B; C 0), R335
11 / 8 (A, B; C 20), LVR 0 (A, B, C), T82 3 / 4 (A, B).

Distribuição do escore esperado (139): mediana A 0,113, B 0,098; percentil 90: A 0,531, B 0,489.
Regiões com A ≥ 0,5 e B < 0,5: 10. Com B ≥ 0,5 e A < 0,5: 9.

### Respostas

- **Q1 (v3_s1 marca mais que o produto?)**: a 0,5 a diferença é de uma região (14 contra 13 na
  população de 139; 11 contra 9 na de 102). A 0,3 a diferença é maior (36 contra 26; 30 contra
  22). Não há base para dizer que o ajuste fino apagou a técnica no limiar de produção. Há um
  sinal a 0,3, que não é a regra do pré-registro. Ela é lida como diagnóstico.
- **Q2 (falta cobertura?)**: não. Com 0,1, B tem escore esperado em 69 de 139 regiões e A em 80.
  O sinal existe na cabeça de técnica dos dois modelos.
- **Q3 (é limiar?)**: em parte. O escore esperado existe abaixo de 0,5 (B tem 56 regiões entre
  0,1 e 0,5). O corte de 0,5 deixa de fora muitas marcas que a cabeça já acha como sinal fraco.
  Mas a mediana do escore é 0,1 nos dois modelos, então o sinal é fraco na maior parte das marcas.
- **Dobra (C)**: na população dos ouros, C marca mais que A e B a 0,5 (20 contra 11 e 9). A
  diferença está toda em R335 (20 contra 11 e 8; em EOB, FTP e LVR, C tem 0 contra A e B). É o modelo que não viu o vídeo e marca
  mais. Isso mostra que o treino do produto não apagou o ligado de forma uniforme.

### Leitura

- O ligado existe na cabeça de técnica dos dois modelos, mas quase sempre abaixo de 0,5.
- A pergunta "apagou ou limiar" tem resposta mista: o corte de 0,5 pesa, e há uma diferença a
  0,3 que favorece o v3_s1. A 0,5 a diferença entre A e B é nula.
- EOB não tem nenhuma marca de ligado acima de 0,5 em nenhum modelo (15 regiões, escore
  "ligado" = 0 nos três). Isso não é limiar: o sinal não passa de 0,5 nessas regiões.
- Por fonte, o escore "ligado" (qualquer classe) ≥ 0,5 em A / B / C: FTP 5 / 6 / 5 (de 14),
  R335 12 / 8 / 21 (de 72), T82 5 / 6 (de 37), LVR 0 / 0 / 0 (de 1).

### Não fiz

- Recortes das regiões com escore A ≥ 0,5 e B < 0,5: não gerados (são só 10). Se a sessão
  principal quiser, olho nesta rodada.
- Segunda execução para verificar o hash: não feita.

# Rodada 0008: casa 13 (par de algarismos sem classe no modelo)

Data: 2026-10-10. Linha de base: HEAD `b5841c27`, medida em árvore limpa (`git archive`).
Medição nova: árvore limpa = HEAD + `tab/reconhecer.py` + `tests/test_casa_dois_digitos.py`.
O HEAD `702fd223` deu as mesmas notas (mesma medição, antes de `b5841c27`); o tempo mudou em `b5841c27`
(`tab/leitor.py`), por isso a linha de base é o HEAD atual.

## Pergunta

No vídeo do MVP (`retrato brasileiro`, ouro `retrato_brasileiro_v2`, 491 notas), sobrava uma
nota inventada: o `13` da tela 8, corda 3 (x≈1244–1267), saía como `1` + `3` separados. O MVP
exige zero inventadas.

## Causa (medida no quadro da tela 8)

- Token `1`: x 1241–1248 (0,32 passo), classe `1` com 0,622.
- Token `3`: x 1255–1267 (0,56 passo), classe `3` com 0,993.
- Vão entre eles: 7 px = 0,324 passo. Dentro de `(0,25; 0,40]`, então `_fundir_pares_de_digitos`
  tentou o par.
- `_casa_das_partes` exigia `13 in rotulos`. O modelo oficial não tem a classe `13` (só 10, 12, 14,
  15, 17, 19, 21, 24 entre as de dois dígitos), então o par nunca fundia.
- O vão não separa: notas distintas vizinhas na mesma corda também têm vão de 0,324 a 0,37 (ESTADO,
  Fase 4). A decisão precisa vir da leitura das partes, não do vão.

Medido com `data/saida/fase4_13/candidatos_pares.py` (13 quadros do ouro, 6 candidatos):

| tela | corda | leitura das partes | concatenação | gabarito | fundido hoje |
| --- | --- | --- | --- | --- | --- |
| 8 | 3 | `1` (0,62), `3` (0,99) | 13 | casa 13 | não (classe ausente) |
| 12 | 1 | `1` (0,70), `2` (0,95) | 12 | casa 12 | sim (token 0,90) |
| 12 | 2 | `1` (0,70), `0` (1,00) | 10 | casa 10 | sim (token 0,91) |
| 5 | 1 | `2`, `7` | 27 | 2 e 7 separados | não (fora de 10–24) |
| 5 | 1 | `7`, `4` | 74 | 4 separado | não (fora de 10–24) |
| 8 | 1 | `5`, `14` | — | 5 separado | não (parte não é dígito) |

## Decisão

1. Casa que o modelo **não tem** como classe sai do par geométrico (dois tokens isolados, vão em
   `(0,25; 0,40]`) quando: a concatenação está entre 10 e 24 e **cada** parte é o algarismo mais
   provável com pelo menos `LIMIAR_PARTE_DIGITO = 0,5` (maioria da massa). O token fundido recebe a
   casa (ex.: `13`).
2. Par de algarismos cuja concatenação é casa possível e que **não** passa na leitura segura não
   vira duas notas: os dois tokens vão como `simbolo` e saem em `nao_notas` com o símbolo cru.
3. Casas que o modelo tem (10, 12, 14...) seguem a regra antiga, sem mudança.

## O que deu errado antes de chegar nisso (não repetir)

A primeira versão aplicou a regra "fora do modelo" também ao caminho de um glifo com dois
componentes. Resultado: na amostra `paolo d'angelo` 3 do gabarito de glifos, um `3` com componentes
lidos como `2` e `0` virou `20`, e `oficial_3` caiu de 68/72 para 67/72. Corrigido: a regra fora do
modelo vale só para o par geométrico. Teste: `test_casa_das_partes_20_de_um_glifo_fora_do_modelo_nao_vira_casa`.
Depois da correção, a comparação amostra a amostra com o HEAD ficou idêntica (`por_amostra.py`).

## Números (ouro `retrato_brasileiro_v2`, `tab.avaliar_video`, árvore limpa)

| medida | HEAD `b5841c27` | depois | aceite |
| --- | --- | --- | --- |
| notas: precisão | 485/486 | **485/485** | inventadas 1 → **0** |
| notas: revocação | 485/491 | 485/491 | ≥ 485/491 |
| perdidas | 6 | 6 | — |
| casa nas casadas | 482/485 | **483/485** | ≥ 482/485 |
| tempo: estado certo | 39/40 (acerto 38, 1 antes 1, erro 1) | 39/40 (igual) | ≥ 39/40 |
| tempo: falso | 0 | 0 | 0 |
| `tab.telas` retrato | 13/13, 40/40 | 13/13, 40/40 | 13/13, 40/40 |
| `tab.avaliar` oficial_1/2/3 | 66, 71, 68 | 66, 71, 68 | 66, 71, 68 |

Diferença de notas (predição HEAD × depois): só a tela 8, corda 3. `1`(x 1244) e `3`(x 1261)
viram `13` (x 1254), nas duas exibições. As casas 10, 12 e 14 do ouro não mudam.

## Limites declarados

- Medido em um vídeo (13 telas, 6 candidatos a dois dígitos). No ouro não há par de **notas
  distintas** com concatenação entre 10 e 24, então o risco de falso positivo da regra fora do
  modelo não foi testado contra negativos reais. O único par que a ativa é o `13`.
- A regra de "inseguro" também pega pares em que o modelo **conhece** a casa, mas o token inteiro dá
  menos de 0,80. Antes esses pares viravam duas notas; agora vão para `nao_notas`. Não aparece no
  ouro nem no gabarito de glifos (saídas idênticas ao HEAD), mas é uma mudança de comportamento em
  outros vídeos, e pode custar revocação onde há duas notas distintas vizinhas e pouco confiáveis.
- O `1` do `13` tem confiança 0,62. Com limiar em 0,5 a casa entra; um limiar acima de 0,62 a
  devolveria a `nao_notas`. O limiar 0,5 é a fronteira da decisão, não um valor ajustado ao caso.

## Artefatos

- Medição no HEAD `b5841c27`: `data/saida/fase4_13/base_b584_*` (HEAD) e `novo_b584_*` (depois):
  `*_702.json`, `*_702_aval.txt`, `*_avaliar.txt`, `*_telas.txt`. Árvores limpas: `base_b584/`, `novo_b584/`.
- Medição no HEAD `702fd223` (mesmas notas): `base_702.json` e `limpo_702*`.
- Diagnóstico: `candidatos_pares.py`, `harness_quadros.py`, `por_amostra.py` (em `data/saida/fase4_13/`).

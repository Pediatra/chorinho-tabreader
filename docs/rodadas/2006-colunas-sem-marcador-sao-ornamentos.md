# 2006 — Áudio: as colunas que o marcador nunca acende são ornamentos (v3 reprovada)

Data: 2026-10-13. Scripts e saídas: `data/saida/audio/a2/v3/` (recortes em `recortes/`).

## Pergunta

Na folha 1 (rodada 2005), o alinhador errou nas colunas que o marcador nunca acende
(tela 2, colunas 17–18). O que são essas colunas, e dá para reconhecê-las sem o
marcador?

## O que são (medido e olhado)

- Das 18 colunas "nunca acesas" listadas, 8 não têm nota no produto (separadores, fora da
  sequência). Ficam **10 com nota**: (2,17), (2,18), (4,9), (4,10), (5,17), (8,8), (11,1),
  (11,2), (12,25), (12,26).
- Recortes da tablatura (6 olhados): são **notas pequenas (ornamento) sob um arco** —
  mordente 2–3–2 que chega à nota normal duas colunas depois (telas 2, 4, 12) e nota de
  deslize 5→7 (tela 8). O marcador não acende ornamento.
- Características no produto, "nunca acesas" (10) × acesas (400):

| característica | nunca acesas | acesas |
| --- | --- | --- |
| só corda 1, nota única | 10 de 10 | 19 de 400 |
| distância à coluna anterior ≤ 1,75 passo | 6 de 10 | 4 de 400 |
| corda 1 + nota única + ≤ 1,75 passo | 6 de 10 | 0 de 400 |
| padrão 2–3–2 na mesma corda | 4 de 10 | 6 de 400 |
| nota repetida / acorde | 0 de 10 | 19 e 59 de 400 |
| `nao_notas` de arco | — | — (o produto não tem classe de arco) |

  A conjunção da terceira linha foi escolhida depois de ver as 10 colunas.
- **"Nunca acesa" não quer dizer "sem ataque"**: a (8,8) foi julgada certa pelo dono (f21):
  o ornamento soa, rápido e ligado.

## v3 = v2 + regra "corda 1, nota única, ≤ 1,75 passo → sem ataque esperado"

| | v2 | v3 |
| --- | --- | --- |
| MVP (régua A1): afirmadas sem par | 16 | 4 |
| MVP: falsos > 200 ms | 3 | 4 |
| gabarito do dono, "certo" que viraram recusa | — | **2 (f06 iwaki, f21 MVP)** |
| gabarito do dono, "errado" resolvidos | — | f20 e f26 recusados; **f11 continua errado e muda +1022 ms**; f14 igual |
| sem marcador (iwaki + kimny) | — | 62 recusas novas sem verificação |

**Reprovada e desfeita** (o código voltou à v2). A regra é geometria por proxy e erra nos
dois sentidos, como as regras de visão da história do projeto.

## Consequência

O que distingue o ornamento é o **tamanho do glifo e o arco**, e isso não está no produto.
Pedido à trilha tablatura em `docs/decisoes/2002-ornamento-no-produto.md`. Enquanto isso,
o alinhador trata ornamento como coluna comum.

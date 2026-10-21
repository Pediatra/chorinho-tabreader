# 0212 — O recorte alto na leitura comum do produto

Escrito **antes** de medir (2026-10-21).

## Por que

- A 0210 achou que o recorte do painel apagava o que fica acima da corda 1. A 0211 trocou o
  recorte só no rótulo de ataque.
- **A leitura comum** (`tab.video` sem `--rotulo-ataque`, pesos `DETECTOR_PADRAO`, família
  `_ger`) **ainda usa o recorte antigo.**
- **O pedido 14 da decisão 2004** é o "10" da corda 1 perdido no *room 335*, tela 20,
  t = 73 s (`diag/pedido14.py`). O leitor do produto, no recorte antigo, lê 3 notas na
  corda 1 e perde os dois "10" (x 336 e 564). No recorte alto, ele lê as 5. O `_atqa` lê as
  5 nos dois recortes.
  - O "10" pequeno do ornamento (x 426) sai como coluna nos quatro casos. Essa metade do
    pedido não é o recorte.

## A pergunta

Os mesmos pesos `_ger`, no recorte alto (`painel.recorte_alto`), leem melhor os 8 ouros?

## A amostra e o método

- **Ouros:** os 8 ouros de vídeo, com todas as telas conferidas. A régua é a da decisão 0010:
  `casar_notas`, `_metricas_par` e `meia = FRACAO_PASSO * passo`, com o quadro em
  `quadro_ref_s`.
- **Pesos:** validação cruzada por vídeo, com os pesos da dobra que não viu o vídeo:
  `detector_tab_v3ft_d<d>_ger`, `_ger_s2` e `_ger_s3`.
- **O que muda:** só o recorte entregue ao `detector_tab.detectar`. São os mesmos quadros, o
  mesmo painel e os mesmos pesos.
- **O que fica de fora:** técnica e ataque (são a 0211) e o tempo.

## O critério, com as 3 sementes somadas

O recorte alto passa se, ao mesmo tempo:

1. as **perdidas** caem;
2. as **inventadas** não sobem;
3. a **casa errada** (casadas − casa certa) não sobe.

## O que fazer em cada resultado

- **Passa:** eu recomendo ao dono trocar o recorte da leitura comum do `tab.video`.
  - Isso muda o produto, então precisa do OK explícito dele.
  - A comparação com o histórico (0,974 · 0,949 · 0,987) deixa de valer e é refeita (regra
    7.6).
- **Não passa:** a leitura comum fica como está e o resultado vai para a tabela "não
  repetir".

## Resultado (2026-10-21)

Script `diag/recorte_comum.py`, que grava `diag/recorte_comum.json`. São 2687 notas do ouro,
por semente.

| semente | recorte | perdidas | inventadas | casa errada |
| --- | --- | --- | --- | --- |
| s1 | antigo | 12 | 42 | 20 |
| s1 | alto | 10 | 45 | 19 |
| s2 | antigo | 13 | 42 | 25 |
| s2 | alto | 11 | 48 | 25 |
| s3 | antigo | 10 | 47 | 27 |
| s3 | alto | 12 | 54 | 26 |
| **soma** | **antigo** | **35** | **131** | **72** |
| **soma** | **alto** | **33** | **147** | **70** |

- **Não passa.** As inventadas sobem 16, e o critério 2 cai.
  - Quase todo o aumento está no *room 335*: o s1 vai de 25 para 28, o s2 de 25 para 29 e o
    s3 de 28 para 33.
  - O s3 ainda perde 2 a mais lá.
- **Leitura:** os pesos `_ger` foram treinados no recorte antigo, e o recorte alto mostra a
  eles o que fica acima da corda 1 (letras, ornamentos, números de compasso), que eles nunca
  viram. O pedido 14 melhora na tela 20, mas no vídeo inteiro o saldo é pior.
- **A leitura comum fica como está.** Entra na tabela "não repetir": recorte alto com os
  pesos `_ger`.

## Seguimento, escrito antes de medir: um modelo treinado no recorte alto

- **A pergunta:** os pesos `_atqa`, treinados no recorte alto (0211), leem os 8 ouros melhor
  que os `_ger` no recorte antigo?
- **O método:** a mesma régua, os mesmos quadros e a validação cruzada:
  `detector_tab_v3ft_d<d>_atqa_s<s>`, só no recorte alto, comparado com a linha "soma,
  antigo" de cima.
- **O critério** é o mesmo: as perdidas caem, e as inventadas e a casa errada não sobem.
- **Se passar,** é uma recomendação ao dono: um modelo só, o `_atqa` no recorte alto, para a
  leitura comum e para o ataque.
  - Isso troca o `DETECTOR_PADRAO`, então só com o OK dele.
  - Antes da troca, refazer a medida do histórico (0010) e o tempo pelo marcador.

## Resultado do seguimento (2026-10-21)

Pesos `detector_tab_v3ft_d<d>_atqa_s<s>`, recorte alto, a mesma régua. O resultado está em
`diag/recorte_comum_atqa.json`.

| semente | perdidas | inventadas | casa errada |
| --- | --- | --- | --- |
| s1 | 9 | 31 | 16 |
| s2 | 9 | 29 | 15 |
| s3 | 10 | 29 | 16 |
| **soma `_atqa`, alto** | **28** | **89** | **47** |
| soma `_ger`, antigo (o produto hoje) | 35 | 131 | 72 |

- **Passa nos três critérios:**
  - as perdidas caem 20 %;
  - as inventadas caem 32 %;
  - a casa errada cai 35 %.
  - As 3 sementes vão no mesmo sentido.
- **O ganho vem de duas mudanças juntas:** o recorte alto e as 34 telas da T8.2, que o
  `_atqa` tem no treino e o `_ger` não tem. Esta medida não separa as duas. Para o produto,
  isso não importa: é o mesmo modelo que já vai para o rótulo de ataque.
- **Por vídeo:**
  - O maior ganho está no *room 335*, com as inventadas indo de 25–28 para 12–14.
  - O *gymnopedie* vai de 11–18 casas erradas para 8–10.
  - O *la vie en rose* piora 1 nota perdida e 2 inventadas por semente.
- **Recomendação ao dono:** trocar a leitura comum pelo `_atqa_s1` com o recorte alto, um
  modelo só para a casa e para o ataque.
  - Isso troca o `DETECTOR_PADRAO`, então espera o OK dele.
  - Antes, refazer a medida do histórico (0010) e o tempo pelo marcador nos 3 vídeos.

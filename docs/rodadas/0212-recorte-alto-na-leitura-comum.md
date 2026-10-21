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

# 2012 — Áudio: rasgueado, colunas abafadas no alinhador (v2.1)

Data: 2026-10-13. Código: `tab/audio_alinhar.py` (`colunas_abafadas`, `e_rasgueado`),
`tab/audio_produto.py` (`tipo`, `rasgueado`, alarme). Medições e recortes:
`data/saida/audio/a4/rasgueado/`. Saídas novas `alinhado_v21_*` e `v21_*.audio.json`; as v2
ficam guardadas.

## Pergunta

No transcriptor *campanitas* (rodada 2010), a leitura está certa, mas a música é rasgueado:
acordes repetidos com batidas abafadas ("X") entre eles. O produto guarda os X como
`nao_notas` de classe `tecnica`. O alinhador não os via, recusava 36 de 52 exibições e
disparava o alarme de leitura à toa (rodada 2011). Dá para pôr as batidas na sequência?

## Regra da coluna abafada (medida antes de mudar o código)

Uma coluna é abafada quando tem **≥ 4 `nao_notas` `tecnica` em cordas distintas**, nenhuma nota
na mesma (tela, coluna) e **≥ 4 desses glifos com top-1 "15"** no classificador. Nos recortes,
o X sai como "15".

| regra | campanitas | 9 vídeos bons | giant steps |
| --- | --- | --- | --- |
| ≥ 3 cordas | 123 | 3 (kimny bach, dream wish, paolo) | 4 |
| ≥ 4 cordas + top-1 "15" (final) | **122** | **0** | **0** |

Recortes olhados:
- campanitas, telas 10, 23 e 49: pilhas de X **confirmadas**;
- as candidatas da regra de 3 cordas nos outros vídeos são acordes de números ou ornamentos,
  **não X** (kimny bach t5, dream wish t22, paolo t12, giant steps t1/t5).

## Alinhador v2.1

- Cada coluna abafada entra na sequência da tela, na ordem, como **ataque sem altura**. Ela casa
  com um pico de fluxo ≥ a mediana dos picos da exibição, com cosseno fixo `COS_ABAFADA = 0,5`,
  constante fixada antes de medir. Não conta no cosseno médio nem no mínimo de 4 colunas casadas.
- Saída: `tipo` por coluna (`nota` | `abafada`); por exibição, `n_abafadas_casadas` e
  `rasgueado`, que vale quando ≥ 20 % das colunas da sequência são abafadas.
- `alarme_leitura` desliga em exibição `rasgueado`.

## Resultado

- **Identidade nos 9 vídeos bons**: 4131 de 4131 colunas e 124 de 124 exibições idênticas
  à v2. Sem abafada, a saída é a mesma por construção.
- Nos 14 vídeos, só o campanitas muda:

| campanitas | v2 | v2.1 |
| --- | --- | --- |
| colunas de nota com tempo | 201 de 935 | **268 de 935** |
| colunas abafadas com tempo | — | 50 de 122 |
| exibições recusadas | 36 de 52 | 32 de 52 |
| alarmes de leitura | 21 | **17** |
| exibições rasgueado | — | 12 (telas 1, 2, 10, 11, 18, 19, 27, 28, 36, 37, 45, 46) |

- As telas 1, 2, 10 e 11 não tinham nenhuma coluna com tempo e passam a ter 9, 15, 15 e 10:
  os X ancoram a grade entre acordes iguais.
- **Não verificado de ouvido.**
- Os 17 alarmes restantes estão em telas sem X ou com poucos: a causa é outra, não investigada.

## Limites

- A regra depende do top-1 "15" do classificador atual. Se o modelo for retreinado, ela tem
  de ser medida de novo (`TOP1_ABAFADA`).
- Setas de batida sem X não viram coluna.
- Um vídeo de rasgueado no lote.

## Nota posterior (2026-10-13)

O dono **descartou o vídeo** transcriptor *campanitas* (Ernesto Cavour) do dataset, por não atender aos padrões dele. Esta rodada fica como registro. A folha 4 (escuta do campanitas) **não** entrou no gabarito; as respostas estão em `data/saida/audio/a2/folha/respostas_folha4.json`. O código do v2.1 fica: nos outros 13 vídeos ele dá saída idêntica à v2.

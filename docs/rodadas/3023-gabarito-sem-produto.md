# 3023 — gabarito do dono sem produto: Audiveris em 3 recortes

Trilha partitura. Data: 2026-10-15. **Gabarito:** `data/gold/partitura/leitura_sem_produto.json`
(formato 3, gravado pelo dono na página `tab.partitura_gabarito servir`). **Leitura
conferida:** Audiveris x2 sobre o recorte com margem 7/7, com a armadura do vídeo
(`x2_margem_herdada`), nos recortes já refeitos pela rodada 3022.

## Pergunta

A leitura de vídeo sem produto (rodada 3019) não tinha medição. Vale o mesmo que o gabarito
R01–R21 (rodada 3004) mediu em vídeos com tab?

## Resultado (3 de 3 recortes confirmados)

Contagem: `data/saida/partitura/diag/medir_sem_produto/medir.txt`.

| recorte | lidos | certos | não existe | faltando (cliques) |
| --- | ---: | ---: | ---: | ---: |
| agua de beber P01a | 78 (68 notas, 10 pausas) | 78 | 0 | 9 |
| athletic theme P01a | 60 | 58 | 2 | 31 |
| canon P06a | 40 | 40 | 0 | 0 |
| **total** | **178** | **176 (98,9%)** | **2** | **40** |

- Clave e armadura certas nos 3. No canon P06a, a armadura de 2 sustenidos veio do vídeo
  (rodada 3020).
- Nenhuma altura errada e nenhuma figura errada.
- Notações: 43 certas e 2 inventadas.
- Cobertura: 176 certos de 216 notas que existem, **81,5%**. Na 3004 foi 852 de 930,
  91,6%.

## O que os números dizem

- **O que o Audiveris lê está certo**, como na 3004: 98,9% aqui, contra 97,6% lá.
- **O problema é a nota que falta**, e ela se concentra num recorte só. No athletic P01a,
  o dono anotou: "perdeu uma parte grande da 2ª metade de cima". Nos compassos 3 e 4, o
  Audiveris leu só a voz de baixo (13 eventos) e descartou a voz de cima, com as
  semicolcheias. Os 31 cliques de faltando estão todos nessa região.
- Nos vídeos com tab, a tab completa as notas que faltam. Sem tab, nada completa. Os
  candidatos para isso são o homr, que já roda no `ler` com produto, e uma segunda leitura
  do Audiveris com outra entrada.

## Correção na ferramenta

O gabarito novo gravou `fonte_itens` apontando para os itens da P1, e não para os itens
servidos (`diag/conferencia_sem_produto/itens.json`). O `gabarito_vazio` usava sempre a
constante `ITENS`. Agora o servidor passa o `--itens` usado, e entrou 1 teste novo. O
arquivo do dono não foi alterado. Esse campo é só informativo.

## Limites

- São 3 recortes, 216 notas. Isso mostra a tendência, mas não dá um número de cadeia.
- Os 3 recortes têm fundo branco. Os de faixa amarela (rodada 3021) nem chegam a ser lidos.

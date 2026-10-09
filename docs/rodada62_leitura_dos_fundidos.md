# Rodada 62 — olhei os 70 tokens fundidos: o proxy estava muito pior do que eu pensava

## 1. A identificação, por leitura da montagem

Gerei o recorte de **cada** token com `partes >= 2` do `raman korshun` (70 de 94), com o índice
desenhado, e li um a um. O que existe ali:

| categoria | quantos (aprox.) | índices (exemplos) |
| --- | --- | --- |
| **algarismo COM marca de técnica** (barra diagonal atravessando) | **~18** | 3, 4, 5, 6, 12, 13, 19, 20, 26, 27, 32, 33, 38, 39, 81, 82, 83 |
| **algarismo limpo** (sem marca) | ~21 | 11, 15, 18, 21, 22, 28, 29, 31, 41, 42, 44, 48, 56, 58, 59, 60, 62, 65, 67, 69, 92 |
| **algarismo entre parênteses** (`(6)`, `(4)`) | 3 | 52, 53, 54 |
| **lixo** (barra vertical, sem algarismo) | **~27** | 8, 9, 10, 16, 17, 24, 30, 36, 49, 50, 51, 61, 63, 68, 70–78, 84, 87–91 |

## 2. O que isso diz sobre a minha "correção" da rodada 60

Eu rotulei **13** tokens como `tecnica` usando `partes >= 2`. A leitura mostra que:

- **~27 dos 70** candidatos são **lixo puro** (barras verticais) — mais candidatos a `junk` do que a
  `tecnica`;
- só **~18** têm, de fato, marca de técnica;
- e há ainda uma categoria que eu **não tinha previsto**: algarismo **entre parênteses** (`(6)`,
  `(4)`), que na notação de tablatura significa **nota ligada/ligadura** — é uma informação musical
  que o meu JSON não representava.

Ou seja, o proxy geométrico que eu usei **não errou por pouco**: ele misturou três categorias
diferentes (técnica, lixo, parênteses) sob um rótulo só. Foi por isso que a métrica caiu de 12/24
para 4/24.

## 3. O que a leitura entrega de graça

1. os **índices exatos** dos tokens com técnica → é a relabelagem correta, feita por leitura;
2. a existência de uma **categoria musical nova** (`(n)` = nota ligada) que o gabarito e o JSON
   precisam representar;
3. a confirmação de que o `raman` tem **muito lixo** entre os tokens — o que reforça que a classe de
   rejeição (removida na rodada 22 por ser uma troca) faz falta **neste** canal.

## 4. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** — casas | **0,875** (modelo atual) · 0,854 média de 3 sementes |
| **canais limpos** | `iwaki` 27/27, `sky` 15/15, `paolo` 30/30 |
| **`raman`** | 12/24 — e agora com a **identificação correta**: ~18 com técnica, ~21 limpos, 3 com parênteses, ~27 lixo |
| **classe `tecnica`** | treinada e estável; a relabelagem **agora tem base visual** |
| **tempo** | faixa (`skyguitar`, 0,16 s) e cor (`cifra club`, 41/41 onsets) |
| **gabarito** | restaurado; a correção certa está identificada token a token |

## 5. Próximo passo (com base na leitura, não em proxy)

1. **relabelar** os ~18 tokens com técnica como `tecnica`, os ~27 lixo como `junk` e os 3 com
   parênteses como categoria própria (`ligada`) — tudo a partir da lista de índices desta rodada;
2. **reaferir com 3 sementes** — agora a métrica consegue distinguir o que o modelo acerta;
3. representar `ligada` no JSON (é informação musical, não ruído);
4. decidir o destino da classe de rejeição **por canal** (no `raman` ela faz falta; nos limpos, não).

A lição das rodadas 14 e 60 está agora demonstrada com imagem: **proxy geométrico erra grosseiro, e
leitura de imagem acerta fino.** Custou duas rodadas para eu aceitar o que já tinha aprendido no
`cifra club`.

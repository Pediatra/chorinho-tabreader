# Rodada 4 — gabarito verificado e dois bugs de extração

Trabalho feito sobre o **acervo real** (`/run/media/.../chorinho/`), não sobre os recortes
herdados.

## 1. Bug grave: o filtro de margem apagava notas reais

O extrator descartava como "rótulo TAB" todo componente à esquerda de
`barlines_x[0] + 2,2 passos`. A premissa era que a primeira barline detectada é a borda
esquerda da pauta. **É falso**: medido no canal `iwaki`, a primeira barline está em
**x=623** (meio da pauta) e há notas reais em **x=236…571** — todas descartadas.

Impacto medido no acervo:

| | |
| --- | --- |
| glifos extraídos hoje | 11.780 |
| glifos que o filtro antigo apagaria | **506 (4,3 %)** |
| linhas afetadas | **60** de 163 |

Correção: o rótulo passou a ser reconhecido **pela forma**, não pela posição —
ele é o **primeiro** agrupamento em x, tem **largura maior que 0,95 passo** (as letras T, A, B
se fragmentam e cobrem mais de um passo) e cobre **≥ 3 cordas**. Um acorde real tem a
largura de um algarismo (~0,6 passo), então não é confundido.

Verificação das duas pontas:

| caso | antes | depois |
| --- | --- | --- |
| `iwaki` (notas na margem) | 19 glifos, perdendo as da esquerda | **27 glifos**, com as da esquerda |
| `-6rawhontyg` linha 1 (gabarito verificado) | 15 na corda 2 | **15 na corda 2** (rótulo removido, notas intactas) |
| `tup` linha 1 (acordes densos) | 107 (regra agressiva anterior) | **127** (nenhum acorde perdido) |

## 2. Segundo bug: glifos mutilados (já corrigido nesta rodada)

A remoção da corda apagava todo traço horizontal longo dentro da faixa, incluindo os do
próprio algarismo (arco do `0`, barra do `4`). Passou a apagar só nas linhas da corda.

Efeito: amostras rotuláveis 741 → **1.072**; acerto no treino 0,82 → **0,94**;
canais novos 0,67 → **0,70**; e o gabarito verificado continua 15/15.

## 3. Gabarito verificado: começou

Método (arquivo `tools/ouro.py`): extrai o quadro do vídeo, acha a grade, salva **cada glifo
isolado e ampliado com um índice**, e eu leio um a um. Ler glifo isolado é bem mais
confiável do que ler a linha inteira.

| canal | glifos rotulados | como |
| --- | --- | --- |
| iwaki | **27** | lidos um a um do acervo real (glifos isolados) |
| sky guitar | **15** | linha 1 dos recortes, verificada pixel a pixel |
| **total** | **42** | `gold/gabarito.json` |

Limitação registrada sem maquiagem: a distribuição é `0:18, 3:12, 1:10, 2:2` — só 4 casas,
e desbalanceada. **Ainda não dá para medir acerto por classe**; serve para saber se o
caminho está andando, não para declarar acurácia final. Para isso o gabarito precisa de
~300 glifos cobrindo 0–24 e as técnicas.

## 4. Onde o goal está

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** (rodada 3: 96 % com tablatura, 95 % com cursor) |
| (b) gabarito verificado | **iniciado** (42 glifos, 2 canais; faltam ~260) |
| (c) classificador multi-classe | pendente — depende de (b) + gerador sintético |
| (d) pipeline ponta a ponta | parcial: grade, corda, coluna e tempo prontos; falta a casa e o compasso |
| (e) escala nos 3.781 | pendente |

Próximo passo, na ordem: (1) completar o gabarito para 0–24 lendo mais linhas de canais
diferentes; (2) **gerador sintético** nas famílias medidas (claro/escuro, tracejado,
passo 15–36 px, acorde empilhado, cor de voz, `<n>` harmônico, ligado, rótulo TAB) — é ele
que ataca o único número ruim do sistema (0,70 em canal novo), porque dá dado ilimitado com
rótulo exato; (3) treinar e aferir contra o gabarito; (4) rodar em escala.

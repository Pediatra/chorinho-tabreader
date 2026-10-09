# Rodada 10 — o gabarito cresceu e a acurácia caiu: 0,818

## 1. O número honesto

Ampliei o gabarito para um terceiro canal (`raman korshun`, casas 4–7 e marcas de slide) e
reaferi tudo com o **mesmo modelo sintético**, sem retreinar nada:

| canal | acerto | erros |
| --- | --- | --- |
| iwaki (tema escuro, tab embaixo) | **27/27 = 1,00** | — |
| sky guitar (recorte legado) | **15/15 = 1,00** | — |
| **raman korshun** (casas 4–7, slides) | **12/24 = 0,50** | 12 |
| **TOTAL** | **54/66 = 0,818** | 12 |

O gabarito passou de 42 para **66 glifos** e de 4 para **9 classes** (`0,1,2,3,4,5,6,7,junk`).

**A acurácia caiu de 1,000 para 0,818 — e isso é a medição melhorando, não o sistema piorando.**
O 1,000 anterior media só as casas 0–3 em dois canais. Este é o primeiro número que inclui
casas altas e um canal com técnica.

## 2. As duas falhas, ambas concretas

**Falha 1 — não existe classe de rejeição.** Erros `(0, junk, '1')` e `(2, junk, '5')`: os
fragmentos verticais (barline/resto de corda) foram classificados como algarismos, porque o
modelo é **obrigado** a escolher uma das 19 classes para qualquer recorte. A verificação de
forma não pega isso (um fragmento estreito "cabe" como `1`).

**Falha 2 — a marca de técnica entra no token e corrompe o algarismo.** Erros
`(3, '7', '24')` e `(5, '7', '24')`: o `7` com a barra de slide é **fundido no mesmo token**
(elas se tocam), o token fica largo, e a verificação de largura então *autoriza* a classe de
2 dígitos `24`. Ou seja: a mesma regra que corrigiu o erro da rodada anterior **validou uma
resposta errada** aqui.

Isso não invalida a verificação de forma — mostra o limite dela: ela decide sobre o que está
dentro do token, e o token estava errado. A técnica precisa ser **detectada e separada antes**
da classificação do algarismo, não deixada dentro dele.

## 3. Consequência para o plano

As duas falhas apontam para o mesmo lugar: falta a **camada de técnica** (detectar slide,
ligado, harmônico e descartar lixo) entre a extração e a classificação. Enquanto ela não
existir, a classificação de algarismo herda erro de duas fontes que não são dela.

Ordem sugerida: (1) classe `junk`/rejeição treinada em sintético com fragmentos de barline e
resto de corda; (2) separação da marca de técnica do token do algarismo (cortar o traço
diagonal/curvo que atravessa o algarismo); (3) reaferir os 3 canais — esperando voltar acima
de 0,95 com 9 classes; (4) só então ampliar para 0–24 e os 12 canais.

## 4. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura, 95 % com cursor |
| (b) gabarito verificado | **66 glifos / 3 canais / 9 classes** |
| (c) classificador multi-classe | funciona (0,818 real, 9 classes) — falta rejeição e separação de técnica |
| (d) pipeline ponta a ponta | corda, casa, técnica, tempo, barlines e confiança |
| (e) escala nos 3.781 | pendente |

O gargalo continua sendo o gabarito: 66 glifos ainda é pouco, e agora sei exatamente quais
casos ele precisa cobrir — lixo (barline/fragmento) e algarismo com marca de técnica.

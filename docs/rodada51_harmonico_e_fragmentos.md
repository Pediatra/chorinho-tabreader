# Rodada 51 — onde o `harmonico` entrou (e um defeito real que apareceu junto)

## 1. O vazamento não está no pipeline

Medindo as caixas dos tokens onde o modelo diz `harmonico` neste painel:

| # | corda | largura | partes | top1 | p1 | top2 | p2 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | 3 | 17 px | 1 | **harmonico** | 0,84 | 6 | 0,10 |
| 9 | 3 | 17 px | 1 | **harmonico** | 0,58 | 6 | 0,22 |
| 17 | 3 | 17 px | 1 | 6 | 0,99 | harmonico | 0,01 |

A regra de forma do `tools/reconhecer.py` exige, para `harmonico`, **≥ 2 componentes OU largura
≥ 1,2 passo (53 px aqui)**. Com 17 px e 1 componente, **a regra rejeita** — e o caminho oficial
(`reconhecer_linha`) nunca produziria `harmonico` nesses casos.

**O `harmonico` do JSON anterior veio do meu script ad-hoc da rodada 46**, que chamou o modelo
direto com `argmax`, sem passar pela verificação de forma. Ou seja: o defeito era do meu atalho,
não do pipeline. Registro isso porque eu havia atribuído o vazamento ao classificador.

## 2. Mas apareceu um defeito real, e ele é de extração

As caixas têm **14–17 px de largura** — e neste painel o passo é 44 px, com algarismos que deveriam
ter ~30–40 px. Ou seja: **o extrator está pegando fragmentos do algarismo, não o algarismo inteiro**
(a máscara de "tinta clara" provavelmente captura só a parte mais brilhante de cada dígito).

Isso explica a confiança alta em `harmonico`: fragmento estreito e alto é exatamente o que a forma
de um `<n>` sugere.

Então a ordem correta é: **consertar a extração primeiro, reclassificar depois** — não treinar o
modelo para acertar fragmentos.

## 3. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, técnica) | **0,805** (3 sementes) nos 4 canais com gabarito |
| **painel e geometria (escuro)** | grade resolvida (6 cordas, passo 44,2); **glifos saem fragmentados** |
| **tempo — marcador por cor** | onset medido (41/41 notas, 8 ataques, 1,80 s) |
| **verificação de forma** | funciona; meu script ad-hoc é que a ignorava |

## 4. Próximo passo

1. **corrigir a extração no painel escuro**: a caixa deve cobrir o algarismo inteiro (a máscara
   clara está com limiar alto, ou o filtro de área corta as bordas) — medir a largura esperada
   (~0,7 passo) e comparar com o que sai;
2. reclassificar e verificar se o `harmonico` desaparece **sem** precisar da regra de forma;
3. usar **sempre** `reconhecer_linha` (com a regra) nos artefatos — nunca `argmax` solto;
4. seguir para a janela maior (reinício de frase) e para a aferição da casa neste canal.

O saldo: um erro que eu atribuí ao classificador era do meu atalho, e a investigação revelou um
defeito de extração que era invisível enquanto eu olhava só as métricas agregadas.

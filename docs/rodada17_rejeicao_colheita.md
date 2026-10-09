# Rodada 17 — classe de rejeição: a colheita falhou, mas provou algo

## 1. O que tentei

A maior fonte de erro no `raman korshun` é lixo virando algarismo (`junk → 1`, `junk → 5`).
Ideia: colher a classe de rejeição **de graça** — todo token que não casa com nenhuma nota
desenhada é, por definição, lixo, então rótulo `junk` em vez de descartar.

## 2. Resultado: zero amostras de lixo

| | |
| --- | --- |
| classes do modelo depois do retreino | **19 — e "junk" não está entre elas** |
| total medido | **82/96 = 0,854** (inalterado) |

O código do `junk` **está no arquivo** (linha 134 do `tools/sintetico.py`), mas **nunca foi
executado** — e disso sai uma prova, não um palpite: se *algum* token sintético tivesse ficado
sem par, a linha seguinte (`rot = alvo[...]`) teria estourado `TypeError` e a geração teria
morrido. Ela terminou normalmente.

Conclusão: **na tablatura sintética, todo token extraído corresponde a uma nota desenhada.**
O extrator está limpo no que eu mesmo desenho. O lixo que aparece no `raman korshun` não é
gerado pelo meu desenho — vem de traços daquela renderização específica (barlines mais grossas,
restos de linha, acidentes da fonte) que o meu gerador não produz.

## 3. O que isso significa

Não dá para treinar rejeição colhendo sobras: **não existem sobras no sintético**. Para a
classe existir, o lixo precisa ser **desenhado de propósito** no gerador — barline sobrevivente,
fragmento de linha, letra do rótulo TAB, ponto de ornamentação — e rotulado `junk`. É o mesmo
remédio que funcionou na rodada anterior: cobrir o dado em vez de mexer na regra.

É também um elogio ao extrator e um alerta: ele filtra tão bem o que eu desenho que o sintético
não ensina o modelo a rejeitar o que **outros** desenham. Esse é exatamente o tipo de ponto cego
que só aparece quando o gabarito real cresce.

## 4. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura, 95 % com cursor |
| (b) gabarito verificado | 96 glifos / 4 canais |
| (c) classificador multi-classe | **0,854 real** — 2 canais em 1,00; erros concentrados em 2 canais |
| (d) pipeline ponta a ponta | corda, casa, técnica, tempo, compasso e andamento |
| (e) escala nos 3.781 | pendente |

Próximo passo, agora com causa medida: **desenhar lixo de propósito no gerador** (barline
sobrevivente, fragmento de linha, letra do rótulo) e rotulá-lo `junk`; depois a **marca de
técnica como classe própria**; depois ampliar o gabarito e escalar.

Nenhuma mudança de código foi deixada pela metade: o patch do `junk` fica no lugar (é inócuo e
é o gancho certo para quando o lixo for desenhado), e o modelo segue em 19 classes / 0,854.

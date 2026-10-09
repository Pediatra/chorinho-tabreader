# Rodada 34 — com a trava de assinatura, o cursor cai de 95 % para 12 %

## 1. A trava implementada

`detectar_cursor` agora exige, além de "coluna com pixels coloridos":

- **largura ≤ 6 % da largura do quadro** (banda estreita);
- **matiz na faixa de banda de playback (85–140, azul/pálido)**.

Motivo medido: sem isso, o detector achava o **corpo do violão** (149 px de largura, matiz 16 =
laranja) e chamava aquilo de cursor — o que contaminou todas as medições de cobertura de tempo.

Verificação de que a trava não é arbitrária: o cursor verdadeiro do `skyguitar` que eu validei na
rodada 2 tem **matiz 109** e **núcleo de 15–22 px** (≈1 % da largura do quadro). **Passa** nas
duas travas.

## 2. O número, antes e depois

| medição | detector | resultado |
| --- | --- | --- |
| inventário (1 quadro por vídeo) | antigo | **95 %** |
| **esta rodada (1 quadro por vídeo)** | **com trava** | **12 % (3/24)** |
| varredura de 120 s (rodada 28) | antigo | 54 % — **contaminada, não vale** |

Por canal, com a trava: 0 % em dez canais; **1 vídeo** com cursor em `raman korshun`,
`tv on guitar` e `guitarous`.

Painel de tablatura: **24/24 = 100 %** (agora exigindo ≥3 glifos centrados nas linhas, o que
também protege contra confundir as **cordas do violão** com uma grade de tablatura — que é o
outro erro que a imagem revelou).

## 3. O que esses 12 % significam — e o que ainda não significam

São **12 % numa tomada única de quadro**, com a exigência de assinatura. Não são comparáveis
diretamente aos 54 % (que eram uma varredura de 120 s): um vídeo pode ter cursor em alguma janela
e não naquele quadro.

Então o que ficou provado é:

- **a medição antiga de 95 % estava errada** — ela media, em boa parte, madeira de violão;
- **a cobertura real de tempo é muito menor** do que eu reportei, e o número que vale exige
  refazer a **varredura de janelas com a trava nova**;
- o painel continua sólido em 100 %, agora com uma trava a mais.

## 4. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, técnica) | **0,805** (3 sementes); robusto em 7 canais |
| **compasso** | funciona onde a barline é limpa |
| **tempo** | **cobertura real desconhecida**, mas muito abaixo dos 95 % que eu reportei; 12 % numa tomada única com assinatura válida |

## 5. Próximo passo

1. **refazer a varredura de janelas com a trava nova** em 2–3 vídeos por canal — é o número que
   substitui o "54 %" contaminado;
2. só então decidir a estratégia dos vídeos sem cursor (áudio/manual).

Nada de código foi deixado pior: a trava **só restringe** o detector, e o único canal com tempo
verificado (`skyguitar`) continua passando. Se a varredura nova ficar perto de 12 %, o anexo de
tempo deixa de ser "metade do acervo" e passa a ser "uma minoria do acervo" — e isso muda o plano,
não a verdade.

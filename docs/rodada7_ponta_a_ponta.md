# Rodada 7 — primeira transcrição ponta a ponta em vídeo real

## 1. O que foi produzido

`saida/skyguitar_linha01.json` — a primeira linha de tablatura transcrita de um vídeo real,
com **corda, casa e tempo de execução por nota**, que é exatamente o formato pedido:

```json
{"ordem": 1, "corda": 2, "casa": "0", "x": 160, "t_ini": 1.84, "t_fim": 2.80}
{"ordem": 2, "corda": 2, "casa": "0", "x": 251, "t_ini": 2.90, "t_fim": 3.80}
...
{"ordem": 15, "corda": 2, "casa": "0", "x": 1593, "t_ini": 15.85, "t_fim": 16.75}
```

Cadeia completa exercitada, sem nenhum passo manual no meio:
quadro do vídeo → grade de 6 cordas → tokens → classificador treinado **só em dado
sintético** → tempo de cada nota pelo **cursor de execução** → JSON.
O artefato foi gerado sem nenhum dado do vídeo no treino (o modelo nunca viu este vídeo).

## 2. Aferição contra o que está no vídeo

| | |
| --- | --- |
| tokens extraídos | **15** (o gabarito tem 15) |
| casas previstas | `0 0 0 0 1 1 1 1 3 3 3 3 1 1 harmonico` |
| casas corretas | `0 0 0 0 1 1 1 1 3 3 3 3 1 1 0` |
| **acerto** | **14/15 = 0,933** |
| tempo da 1ª nota | 1,84 s |
| tempo da 8ª nota | 8,81 s |
| tempo da 15ª nota | 15,85 s |

O tempo veio com ~1 nota por segundo, que é o andamento real do trecho — e a rodada 2 já
tinha mostrado que esse tempo bate com o do pipeline antigo com desvio de 0,16 s.

## 3. O erro, e o que ele ensina

A **única** nota errada é a última: o `0` final foi classificado como `harmonico`. Isso não
é ruído aleatório — é a classe `harmonico` (que no sintético é desenhada como `<n>`) vazando
para um glifo que provavelmente está renderizado de forma incomum no fim da linha (nota
longa/ornamentada, recortada diferente).

Consequência prática: o classificador precisa de uma **classe de rejeição** e de uma
verificação de forma (um `0` e um `<0>` não têm o mesmo número de componentes nem a mesma
largura). Hoje ele é forçado a escolher uma das 19 classes para qualquer entrada — foi essa
a causa do único erro da aferição anterior no `sky guitar` (14/15) e do erro de agora
(mesma linha). É o defeito mais concreto que resta no reconhecimento.

## 4. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura, 95 % com cursor |
| (b) gabarito verificado | 42 glifos / 2 canais |
| (c) classificador multi-classe | **funcionando** — 0,976 no gabarito; falta classe de rejeição |
| (d) pipeline ponta a ponta | **primeira linha transcrita com corda, casa e tempo** |
| (e) escala nos 3.781 | pendente |

O que falta no JSON para ele ser o produto final: **compasso** (as barlines já são
detectadas, falta numerar), **andamento** (sai do intervalo entre onsets do cursor),
**técnica** (a taxonomia está no sintético; falta aferir em dado real), e a **partitura**
(peça separada, precisa de OMR próprio).

Sequência sugerida: (1) classe de rejeição + verificação de forma para matar o vazamento de
`harmonico`; (2) compasso e andamento no JSON; (3) rodar a linha inteira nos 12 canais
amostrados e conferir; (4) ampliar o gabarito para 0–24 e técnicas; (5) escala.

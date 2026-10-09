# Rodada 61 — corrigi o gabarito errado e piorei tudo; revertido

## 1. O que eu fiz e o que aconteceu

Para destravar a medição da classe `tecnica`, rotulei como `tecnica` os tokens do `raman` com
**`partes >= 2`** (mais de um componente) — assumindo que isso significaria "marca de técnica
fundida".

| semente | iwaki | sky | **raman** | paolo | TOTAL |
| --- | --- | --- | --- | --- | --- |
| 0 | 25/27 | 15/15 | **4/24** | 24/30 | **0,708** |
| 1 | 27/27 | 14/15 | **4/24** | 27/30 | **0,750** |
| 2 | 27/27 | 15/15 | **4/24** | 30/30 | **0,792** |

`raman` caiu de **12/24 para 4/24**. A "correção de semântica" piorou tudo.

## 2. Por que — e o erro é o mesmo de sempre

**`partes >= 2` não significa "técnica fundida".** Significa apenas que o token tem mais de um
componente — o que também acontece quando um **resto de linha** divide um algarismo, ou quando o
fragmento de barline encosta nele.

Medido: dos **13 tokens** que eu relabeli, o modelo (que **sabe** detectar a marca, porque a viu no
sintético) concordou em **4**. Os outros 9 eram fusões com lixo, não com técnica — e eu os rotulei
como `tecnica`, transformando acertos em erros.

É a **mesma falha da rodada 14**: eu rotulei pela *geometria* (uma proxy) em vez de confirmar o que
o token **é**. Lá foi "mancha larga = algarismo com slide"; aqui foi "2 componentes = técnica".

## 3. Revertido

Restourei os rótulos lidos à mão na rodada 15 e reaferei:

**84/96 = 0,875** (iwaki 27/27, sky 15/15, raman 12/24, paolo 30/30) — o estado bom de volta, e o
gabarito agora carrega a nota explicando por que `partes>=2` **não** pode ser usado como proxy.

## 4. O que fica do ciclo `tecnica`

| passo | resultado |
| --- | --- |
| produzir o fenômeno no gerador | **feito** (11,7 % dos tokens) |
| treinar a classe | **feito** — estável (amplitude 0,062 → 0,031), sem regressão |
| medir o ganho | **bloqueado**: o gabarito rotula o token fundido com o algarismo |
| corrigir o gabarito por proxy geométrico | **falhou** (esta rodada) e foi revertido |
| corrigir o gabarito **confirmando cada token** | **próximo passo** — e é trabalho de imagem, não de regra |

## 5. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** — casas | **0,875** (modelo atual) · 0,854 média de 3 sementes · 0,955 sobre os alcançáveis |
| **canais limpos** | `iwaki` 27/27, `sky` 15/15, `paolo` 30/30 |
| **classe `tecnica`** | treinada e estável; **medição bloqueada por rótulo**, não por modelo |
| **tempo** | faixa (`skyguitar`, 0,16 s) e cor (`cifra club`, 41/41 onsets) |
| **gabarito** | **restaurado** ao estado lido à mão, com a ressalva registrada |

## 6. Lição registrada

**Não se corrige rótulo por proxy geométrico.** Duas vezes nesta série eu tentei (rodada 14 e agora)
e nas duas o resultado piorou. Rótulo se corrige **olhando o token** — e o caminho é o mesmo que
funcionou no `cifra club`: gerar a imagem com as caixas e conferir.

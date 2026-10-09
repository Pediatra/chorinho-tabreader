# Rodada 6 — tokenização: o gargalo caiu de 0,70 para 0,976

## 1. O que foi feito

Implementado `agrupar_tokens` em `tools/tabseg.py`: componentes na **mesma corda** com
intervalo em x menor que 0,25 do passo viram **um token**. O extrator passou a entregar
tokens (número de 1–2 dígitos, `<n>`, algarismo simples), não componentes soltos.

Efeito imediato no acervo:

| | antes | depois |
| --- | --- | --- |
| `-6rawhontyg` linha 1 (gabarito) | 15 | **15** (intacto) |
| `tup` linha 1 (acordes densos) | 127 | 110 (fragmentos fundidos) |
| acervo (163 linhas) | 11.780 glifos | **9.123 tokens** |

Os ~2.657 a menos eram pedaços de token (`1`+`2` de um `12`, `<`+`7`+`>` de um `<7>`) que
antes entravam como se fossem notas.

## 2. Resultado

Treino **só com dado sintético** (10.686 tokens de 400 linhas, 19 classes), aferição em
glifos **reais** de vídeo, rotulados à mão, **nunca vistos no treino**:

| | |
| --- | --- |
| acurácia no treino sintético | **0,985** (era 0,58 antes de tokenizar) |
| **gabarito real — iwaki** | **27/27 = 1,00** |
| **gabarito real — sky guitar** | **14/15 = 0,93** |
| **TOTAL real** | **41/42 = 0,976** |

Comparação com o estado anterior, medido nas mesmas condições:

| abordagem | acurácia em canal novo |
| --- | --- |
| CNN treinada em rótulos prata (herdados) | 0,63 – 0,70 |
| **sintético + tokenização (esta rodada)** | **0,976** |

## 3. Leitura honesta

O que isso prova: **o caminho sintético resolve o gargalo entre canais.** O modelo treinou
apenas em tablatura desenhada por mim e acertou 41 de 42 glifos de vídeos reais de dois
canais diferentes — inclusive o canal `iwaki`, que é tema escuro e tem a tablatura embaixo.

O que isso **não** prova, e eu não vou inflar:

- o gabarito tem **42 glifos e só 4 classes** (0, 1, 2, 3). As casas 4–24, os números de
  2 dígitos e as técnicas **ainda não foram aferidos em dado real**;
- são **2 canais**; os outros 10 não foram testados;
- a aferição é por glifo isolado, não da linha inteira transcrita.

Ou seja: o número 0,976 é real e é o melhor indicador que existe hoje, mas é medido em uma
faixa estreita do problema. Para virar acurácia do sistema, o gabarito precisa crescer para
~300 glifos cobrindo 0–24 e as técnicas, em mais canais.

## 4. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura, 95 % com cursor |
| (b) gabarito verificado | 42 glifos / 2 canais — **próximo alvo: ~300 glifos, 0–24 + técnicas** |
| (c) classificador multi-classe | **funcionando**: sintético + tokens, 0,976 no gabarito real |
| (d) pipeline ponta a ponta | grade, corda, coluna, token e tempo prontos; falta casa na linha inteira, técnica, compasso |
| (e) escala nos 3.781 | pendente |

Sequência sugerida para a próxima rodada: (1) rodar o classificador na **linha inteira** de
um vídeo real e conferir a transcrição contra o vídeo; (2) ampliar o gabarito para 0–24 e
técnicas; (3) montar o JSON final com compasso (barlines) e andamento; (4) rodar em escala.

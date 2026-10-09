# Rodada 13 — segunda tentativa no slide: também falhou (e agora sei por quê)

## 1. O que tentei

Troquei o critério de **altura** pelo de **orientação** (a rodada anterior tinha mostrado que
altura não separa): passou a contar como "dígito" só o componente que tem **uma coluna com
traço vertical ≥ 60 % da altura** — haste de algarismo. Diagonal de slide, em princípio, não
tem.

## 2. Resultado

| canal | rodada 12 | agora |
| --- | --- | --- |
| iwaki | 27/27 | 27/27 |
| sky guitar | 15/15 | 15/15 |
| raman korshun | 12/24 | **12/24** |
| **TOTAL** | **54/66 = 0,818** | **54/66 = 0,818** |

Não mudou. E o erro voltou a ser `24` (com o critério de altura, era `2`) — ou seja, a marca
de slide **passa** no teste de haste.

## 3. A explicação, que é o resultado real desta rodada

Fui olhar de onde vem o erro, e não é da geometria: é do **sintético não parecer com o real**.

- No meu **gerador**, ligado/slide é desenhado como um **arco curvo embaixo** do algarismo
  (`d.arc(...)`), e o token recebe o rótulo do algarismo.
- No canal `raman korshun`, o slide é uma **barra diagonal que corta o algarismo**.

São duas coisas visualmente diferentes. O modelo aprendeu "algarismo com arco embaixo → é o
algarismo", e quando encontra "algarismo com barra diagonal" — que ele nunca viu — responde a
classe mais parecida com aquela mancha larga, que é um número de 2 dígitos.

Ou seja: **o erro não se conserta no extrator, se conserta no gerador.** Enquanto o sintético
não desenhar slide como o real desenha, nenhuma regra geométrica vai salvar a classificação —
e é por isso que duas tentativas geométricas seguidas falharam.

## 4. Correção certa (próxima rodada)

1. Levantar **como cada canal desenha cada técnica** (barra diagonal, arco acima, arco abaixo,
   `h`/`p` entre algarismos, `<n>` de harmônico) — é o mesmo tipo de levantamento que já fiz
   para a grade, agora para os símbolos;
2. desenhar essas formas no **gerador sintético** (dado, não código de visão);
3. retreinar e reaferir os 3 canais — o esperado é o `raman korshun` subir bem acima de 0,50;
4. só então treinar a **classe de rejeição** (lixo → algarismo), que é o erro restante.

## 5. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura, 95 % com cursor |
| (b) gabarito verificado | 66 glifos / 3 canais / 9 classes |
| (c) classificador multi-classe | **0,818 real** — causa dos erros identificada: sintético ≠ real nas técnicas |
| (d) pipeline ponta a ponta | corda, casa, técnica, tempo, compasso e andamento |
| (e) escala nos 3.781 | pendente |

Duas rodadas gastas em hipóteses geométricas erradas, mas o diagnóstico agora está fechado:
**o gargalo do reconhecimento é cobertura do gerador, não regra de visão.** É um gargalo mais
barato de resolver (é desenhar mais formas), e evita eu continuar mexendo no extrator sem
efeito.

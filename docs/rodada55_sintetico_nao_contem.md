# Rodada 55 — por que o `raman` resiste a todas as tentativas: o sintético não contém o fenômeno

## 1. A medição (a que eu deveria ter feito antes de tentar três correções)

| | sintético (25 linhas) | `raman korshun` real |
| --- | --- | --- |
| tokens extraídos | 683 | 94 |
| notas com técnica (hammer/pull) | 117 | — |
| tokens com ≥2 componentes | 293 | **70 (74 %)** |
| **técnica FUNDIDA no token** | **22 (3,2 %)** | o caso dominante |

**O sintético quase não produz o fenômeno que domina o canal difícil.** 3,2 % contra 74 %.

## 2. O que isso explica

Todas as minhas tentativas no `raman` falharam — regra de altura (rodada 12), regra de orientação
(rodada 13), marca cruzando o algarismo (rodada 14, piorou) — e agora há uma causa medida:

- no meu gerador a marca (arco) é desenhada **com folga**, sem tocar o algarismo → o token sai limpo,
  com o algarismo inteiro;
- no canal real, a barra de slide **cruza** o algarismo e **funde-se** a ele;
- o modelo, portanto, **nunca foi treinado** para o caso que encontra nesse canal — e nenhuma regra
  geométrica conserta um caso que o dado de treino não contém.

É a **terceira confirmação** da mesma lei: o gargalo é cobertura do gerador, não regra de visão.

## 3. O próximo passo, com o número na mão

1. **desenhar a marca cruzando o algarismo** numa fração grande das notas com técnica (em vez de 3 %
   de casos acidentais, tornar isso a regra para hammer/pull/slide);
2. **rotular o token fundido como classe `tecnica`** — não como o algarismo. Isso é a diferença em
   relação à rodada 14 (onde o rótulo continuou sendo o algarismo e a classe `1` se degradou):
   o modelo passa a **sinalizar** o caso, e o algarismo é re-lido do componente dominante;
3. medir a fração de tokens fundidos que o sintético produz **antes** de treinar (lição da rodada 18);
4. treinar e aferir com **3 sementes**, no gabarito real.

## 4. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** — casas | **0,885** bruto · **0,955** sobre os rótulos alcançáveis |
| **canais limpos** | `iwaki` 27/27, `sky` 15/15, `paolo` 30/30 |
| **`raman`** | 13/17 — **causa medida**: o sintético contém o caso em 3,2 %, o canal em 74 % |
| **tempo** | faixa (`skyguitar`, 0,16 s) e cor (`cifra club`, 41/41 onsets) |
| **técnica** | só no sintético, e **quase sempre limpa** — por isso não generaliza |

## 5. O que esta rodada vale

Não mudou código. Mudou **o que eu sei sobre a causa**: o `raman` não resiste por falta de regra, e
sim porque o dado de treino não contém o fenômeno. Duas linhas de medição (683 tokens contados)
substituíram três tentativas de conserto e uma hipótese errada.

E fica registrado o número que faltava desde a rodada 10: **3,2 % contra 74 %**.

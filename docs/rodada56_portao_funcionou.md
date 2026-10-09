# Rodada 56 — o portão de medição funcionou: não treinei

## 1. O que eu ia fazer e o que a medição disse

Plano: desenhar a marca de técnica **cruzando** o algarismo e rotular o token fundido como classe
`tecnica`; treinar; aferir com 3 sementes.

Antes de treinar, medi — a regra que eu estabeleci depois de gastar três retreinos à toa:

| | sintético (25 linhas) | canal real |
| --- | --- | --- |
| tokens | 683 | 94 |
| com ≥2 componentes | 293 (42,9 %) | 70 (74 %) |
| **receberiam o rótulo `tecnica`** | **22 (3,2 %)** | o caso dominante |

**3,2 % está abaixo do meu limiar de 10 % → não treinei.** Um treino aqui só serviria para eu
descobrir, depois, que a classe não nasceu — exatamente o erro da rodada 18.

## 2. Por que ficou em 3,2 % (duas causas, uma delas minha falha)

1. **O patch do "cruzando o algarismo" não aplicou**: o `grep` confirma que o rótulo `tecnica`
   entrou (linha 157), mas a troca de `estilo < 0,45` para a barra cruzando **não** — o texto-alvo
   não bateu. Ou seja: a marca continua sendo desenhada **com folga**, como antes.
2. Ainda assim, alguma fusão acontece: **9 de 23 notas com técnica (39 %)** têm o token fundido —
   mas notas com técnica são só ~17 % dos tokens, então o rótulo `tecnica` fica em 3,2 %.

## 3. Os dois ajustes que faltam (pequenos e medíveis)

1. **consertar o patch** para a marca realmente atravessar o algarismo (verificar o trecho-alvo antes
   de aplicar — a lição de sempre: conferir que a edição pegou);
2. **aumentar a fração de notas com técnica no gerador** (hoje ~10 % harmônico + 8 % hammer/pull):
   o canal real é dominado por elas, e o meu sintético não.
3. medir de novo; só treinar se passar de 10 %.

## 4. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** — casas | **0,885** bruto · **0,955** sobre os rótulos alcançáveis |
| **canais limpos** | `iwaki` 27/27, `sky` 15/15, `paolo` 30/30 |
| **`raman`** | 13/17 — causa medida (3,2 % × 74 %); classe `tecnica` **preparada mas não treinada** |
| **tempo** | faixa (`skyguitar`, 0,16 s) e cor (`cifra club`, 41/41 onsets) |

## 5. O que esta rodada vale

**Um treino evitado.** O portão de medição existe justamente para isso, e desta vez ele funcionou:
gastei uma medição (segundos) em vez de um ciclo de treino e aferição (minutos) para descobrir que a
classe não nasceria.

E fica registrado um erro meu de execução: **um patch não aplicou e eu quase segui adiante** — o
`grep` que fiz no fim é que revelou. A partir daqui, toda edição de gerador vem com verificação do
trecho-alvo na mesma rodada.

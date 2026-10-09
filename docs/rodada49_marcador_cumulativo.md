# Rodada 49 — o marcador por cor é cumulativo: o que é `t_fim` aqui

## 1. O que a janela maior mostrou

Observando ~21 s (amostras de 0,42 a 0,56 da duração):

| | |
| --- | --- |
| notas com tempo | **41/41** |
| duração mediana calculada | **9,1 s** (mín 0,0, máx 20,8) |
| "frases" detectadas | 16 em 24 amostras |

## 2. O que isso significa — e é uma correção de semântica

**9 segundos não é a duração de uma nota.** O marcador do `cifra club` é **cumulativo**: uma vez que
o algarismo fica laranja, ele **continua laranja** (é "já tocado", não "soando agora"). Então:

- o que o marcador dá **de graça e com precisão é o *onset*** — o instante em que o algarismo vira
  laranja. É exatamente o que o goal pede ("o tempo de execução da nota");
- o `t_fim` natural **não é** "quanto a nota soou": é o **começo da próxima nota** (ou o fim da
  frase, quando a tablatura reinicia).

Reportar 9 s como duração seria inventar um dado que o marcador não contém.

## 3. O detector de frase está ruidoso

16 "frases" em 24 amostras é ruído: eu marco reinício quando a coluna máxima laranja cai, e
oscilações de um quadro disparam isso. A regra precisa ser mais dura — por exemplo, reinício quando
a **contagem** de laranja cai abaixo de um limiar **depois de ter passado de um piso** (ex.: cai de
>10 para <3 colunas), em vez de olhar a coluna máxima quadro a quadro.

## 4. O que fica correto

| peça | estado |
| --- | --- |
| painel (escuro, não ocupa o quadro) | resolvido (uniformidade + máscara de tinta clara) |
| grade | resolvida (6 cordas, passo 44,2, 41 tokens) |
| marcador | medido (avanço 1 → 7 → 13 colunas) |
| **`t_ini` por nota** | **41/41 notas** |
| `t_fim` | **redefinido**: *não* é duração da nota; é o onset seguinte / fim de frase |
| detecção de frase | **ruidosa** (16 em 24) — regra a endurecer |

## 5. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, técnica) | **0,805** (3 sementes) nos 4 canais com gabarito |
| **tempo — marcador por faixa** | validado no `skyguitar` (desvio 0,16 s) |
| **tempo — marcador por cor** | **onset por nota medido (41/41)**; `t_fim` a derivar do próximo onset |
| **mecanismo no JSON** | sim (`cor` / `faixa`) |

## 6. Próximo passo

1. no JSON, gravar `t_ini` (= onset, medido) e `t_proxima` (= onset seguinte), **sem chamar de
   duração** o que o marcador não mede;
2. endurecer o **detector de reinício de frase** (queda de contagem após pico, não coluna máxima);
3. matar o vazamento de `harmonico` (verificação de forma já tem o gancho);
4. rodar nos canais de mesmo estilo e medir cobertura por mecanismo.

A correção desta rodada é de **significado**, não de código: eu estava prestes a gravar 9 s como
duração de nota. O marcador dá o instante; a duração tem de sair do próximo instante.

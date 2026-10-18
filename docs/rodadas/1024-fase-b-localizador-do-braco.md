# 1024 — Fase B: o localizador do braço (estágio 1) e o detector de ponta a ponta

**Data**: 2026-10-18. **Estado**: regras a priori. Este documento ganha commit antes de
qualquer treino. **O dono aprovou** ("sim, pode começar a fase B").

**Antecedentes**:
- [1022](1022-decodificador-robusto-e-m11b.md): o detector (estágio 2) acerta a geometria
  quando a faixa vem do gabarito com erro simulado, mas erra ângulos que não viu.
- [1023](1023-o-detector-sabe-quando-erra.md): os sinais S1 e S2 apontam os erros. Na M11b,
  nenhum dos 21 falsos passou sem ser sinalizado.
- Até aqui, a faixa **sempre** vinha do gabarito. Sem o estágio 1, o detector não roda num vídeo
  novo.

## Pergunta

Um localizador treinado só com o que já existe (S, R e G, sem marcação nova) acha a faixa no
quadro inteiro bem o bastante para que a cadeia toda funcione no ciclo de revisão? A cadeia é:
estágio 1 → faixa → estágio 2 (v2) → regra da 1023.

## Estágio 1 (o método)

**Entrada**: o quadro inteiro, reduzido para **640×360** (16:9; outro formato recebe borda preta,
mantendo a proporção).

**Rede**: a mesma U-Net com encoder ResNet18 da 1021 (pesos ImageNet já baixados), com **5**
canais de saída:
- 4 pontos: as pontas das cordas 1 e 6 no nut e as pontas das cordas 1 e 6 no extremo do corpo,
  tal como o `eixo_da_faixa` as usa;
- 1 mapa de presença do braço: a região entre as cordas 1 e 6.

**Alvo**:
- gaussianas de σ = 3 px (na escala 640) nos pontos;
- máscara binária no mapa de presença.

**Treino**:
- **Dados**: R (os quadros `achou` do rastreador) e G. No desenvolvimento, os G e R dos canais
  de validação ficam fora (abaixo).
  - **Sem S**: o S cola um braço sintético sobre quadros reais que já têm um violão de verdade
    sem rótulo (`folha_S.jpg`). No quadro inteiro, isso ensinaria a rede a ignorar o braço
    real. No estágio 2 o problema não aparece, porque a faixa já está centrada no braço
    rotulado.
  - Não há quadros "braço não" rotulados fora da M11b: os 66 de `braco.json` são todos "sim".
- **Aumento**: escala de 0,7 a 1,3, rotação de ±10°, translação de ±15 %, cor (brilho,
  contraste e saturação de ±20 %). **Sem espelhamento**, porque inverteria a mão do violão.
- **Otimização**: BCE com peso positivo, AdamW, AMP, lote 16 e o orçamento de passos da 1021
  (3.000), com a mesma trava de GPU.

**Decodificação**:
- cada ponto é o argmax do seu mapa, refinado pelo centróide 3×3 e levado de volta para o
  quadro;
- **sem braço** quando o máximo do mapa de presença é menor que `P_MIN`, ou quando algum ponto
  tem máximo menor que `P_MIN`;
- as marcas mínimas (nut e pontas das cordas 1 e 6) vão para `eixo_da_faixa` → `matriz_da_faixa`
  → `recortar`, **sem perturbação**.

**Refino (uma passada)**:
1. O estágio 2 roda na faixa do estágio 1.
2. Se ele achou o braço, a faixa é recortada de novo a partir do eixo das marcas que o próprio
   estágio 2 deu (o nut e as pontas das cordas).
3. O estágio 2 roda outra vez, e **a resposta final é a da segunda passada**.

Os sinais da 1023 são medidos na faixa final, com as 4 perturbações extras em torno do eixo
final, e a regra e os limiares ficam **congelados** (fe114eb4).

`P_MIN` fica **fixo em 0,3**, sem ajuste: não há quadros "braço não" para calibrá-lo. A
decisão de verdade sobre o braço fica com o estágio 2 e com a regra da 1023, já que um braço
inexistente tende a sair como "não achou" ou sinalizado. Nenhum limiar do estágio 1 é ajustável.

## Desenvolvimento

- **Validação**: dois canais fora do treino do estágio 1, **kenneth acoustic** e **shin izumi**.
  - Ficam fora todos os R e G desses dois canais.
  - O estágio 2 usado aqui é o da dobra que **também** não viu o canal: `A3_100_3_s1` para o
    kenneth e `A3_100_6_s1` para o shin izumi.
- **Portões**:

| portão | o que mede | passa se |
| --- | --- | --- |
| B1, envelope | Erro do eixo do estágio 1 contra o eixo do rótulo, nos R e G de validação: perpendicular (em larguras), ao longo (em comprimentos), rotação e escala | ≥ 90 % dos quadros dentro do envelope da 1021 (0,3 largura; 5 % do comprimento; 3°; 10 %) |
| B2, cadeia | Cadeia completa (estágio 1 → refino → v2 → regra) nos **G** de validação, contra as marcas do dono | só registro: certos, falsos e falsos não sinalizados |

- Se o B1 reprovar, a rodada para e volta ao dono, antes do treino final.
- O B2 é só registro, porque os G dos dois canais são poucos.

## Prova (M11b)

- **Treino final**: o estágio 1 com todos os canais, 3 sementes, pareadas com as do estágio 2
  (`A3_100_todos_s<k>` com o estágio 1 `s<k>`).
- **Quadros**: os 28 da prova 1022 mais o **q77** (braço "não"), num total de **29 × 3 = 87
  medidas**.
- **Cadeia**: o quadro inteiro, sem nada do gabarito, passa por estágio 1 → refino → v2 → regra
  congelada.
- **Aviso declarado**: a M11b já foi aberta na 1022 e na 1023.
  - Nada do estágio 1 foi escolhido olhando para ela: nem a arquitetura, nem os dados, nem o
    `P_MIN`.
  - Mas ela não é mais um teste virgem. Um teste com canais novos virá do ciclo de revisão.

**Critério** (o mesmo espírito da 1023: o que passa sem revisão tem que estar certo):

| | passa se |
| --- | --- |
| segurança | falsos não sinalizados ≤ 5 % das 87 medidas (no máximo 4). No q77, "braço achado e não sinalizado" conta como falso |
| utilidade | sinalizados (incluindo "não achou") ≤ 50 % das 84 medidas com braço |

| resultado | o que fazer |
| --- | --- |
| passa nos dois | o detector está pronto para o ciclo de revisão: propor ao dono a rodada do ciclo, com uma amostra de vídeos e a ferramenta de conferência |
| passa na segurança e reprova na utilidade | o detector é seguro, mas manda trabalho demais ao dono. Registrar onde ele sinaliza e propor a melhora do estágio 1 |
| reprova na segurança | não serve para o ciclo. Registrar por tipo de erro; a decisão volta ao dono |

**Também reportados**:
- o erro do eixo do estágio 1 na M11b;
- certos não sinalizados;
- a tabela por canal;
- a amplitude entre as sementes.

## Riscos declarados antes

- **A M11b já foi vista** (veja acima).
- **2 canais de validação** dão pouca base para o B1, e o kenneth e o shin izumi podem ser
  fáceis ou difíceis demais.
- **O R vem do rastreador**, e ele erra. Isso pesa no B1.
- **GPU dividida**: o desenvolvimento leva 1 treino e a prova leva 3, de 1 h cada, com a GPU
  livre.
- **Só R e G, de 8 canais**: a diversidade de ângulos do estágio 1 é pequena. Um ângulo novo,
  como o do lonelypicker, deve falhar; a esperança é que a regra da 1023 o sinalize.
- **Tela dividida** (robert lunn): dois braços no mesmo quadro. O rótulo marca um só.

## Desenvolvimento: resultado (2026-10-18) — **B1 reprova**; a rodada para e volta ao dono

**Treino de validação** (`L1_val_s1`, 3.000 passos, 1.374 s):
- 914 quadros no treino: 864 R e 50 G;
- 202 na validação: 188 R e 14 G, de kenneth acoustic e shin izumi.
- A folha de alvos foi conferida: os pontos caem nas pontas das cordas.

**B1, envelope** (`b1_envelope.json`): **68,3 %** dentro, e o exigido era ≥ 90 %. **Reprova.**

| canal | origem | n | dentro |
| --- | --- | --- | --- |
| kenneth acoustic | R | 90 | 87,8 % (7 sem eixo) |
| kenneth acoustic | G | 7 | 85,7 % |
| shin izumi | R | 98 | **48,0 %** |
| shin izumi | G | 7 | 85,7 % |

- **Por critério**:

  | critério | dentro do envelope |
  | --- | --- |
  | perpendicular | 95,5 % |
  | ao longo | 95,0 % |
  | rotação | 94,6 % |
  | **escala** | **68,8 %** |

- **Medianas**: perpendicular 0,064 largura, ao longo 0,004 comprimento, rotação 0,15°, escala
  0,061.
- **De onde vem a reprovação**: quase toda da **escala no shin izumi R**. A largura prevista sai
  de 11 a 20 % maior que a do rótulo R, e o comprimento só de 1 a 2 % maior.
  - Não dá para separar o erro do estágio 1 do erro do rastreador. Nos G do mesmo canal, o
    dentro é 85,7 %.
- **No kenneth**: o vídeo q44 tem 5 quadros com pontos degenerados e 2 sem braço.

**B2, cadeia nos G de validação** (registro, `b2_cadeia.json`), 14 quadros:
- 11 certos, 2 imprecisos, 1 falso;
- 2 sinalizados, e o falso (q44) é um deles;
- **0 falsos não sinalizados**.

### Diagnóstico depois do B1 (não é portão; nada foi ajustado)

**Pergunta**: o erro de escala do B1 importa para a cadeia?

**Como foi medido**: a cadeia completa nos **188 R de validação**, contra o rótulo R
(`b1_diag/cadeia_r.json`). A comparação é com a faixa recortada do próprio rótulo, que é o
mesmo estágio 2 do D2 da 1022.

| | n | certo | impreciso | falso | não achou | sinalizados | falsos não sinalizados |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cadeia a partir do quadro inteiro | 188 | **152** | 25 | **4** | 7 | 36 (19 %) | **1** |
| faixa do rótulo (D2, para comparar) | 188 | 146 | 36 | 6 | 0 | — | — |

| canal | cadeia | faixa do rótulo |
| --- | --- | --- |
| shin izumi | 73 certos e 25 imprecisos | 65 certos e 33 imprecisos |
| kenneth | 79 certos, 4 falsos e 7 não achou | 81 certos e 6 falsos |

- **A cadeia que parte do quadro inteiro vai tão bem quanto a faixa do rótulo, ou melhor.**
- A largura maior no shin izumi **não atrapalha** o estágio 2. O refino (segunda passada) recorta
  de novo a partir das cordas que o próprio estágio 2 encontrou.
- O envelope do B1 era um critério indireto mais severo do que o necessário.

**Decisão pendente com o dono** (pela regra deste pré-registro): seguir ou não para o treino
final e a prova, registrando o B1 como reprovado.

**Desvios de implementação**, onde o pré-registro não dizia:
- tela de 640×384: 360 linhas do quadro mais 24 pretas, porque a U-Net exige múltiplo de 32;
- o quadro inteiro dos G vem de `m3b/quadros`, conferido contra as faixas G (diferença 0,00);
- o nut é a média das pontas das cordas 1 e 6 no nut;
- escala = max(|L'/L − 1|, |w'/w − 1|);
- os pesos das dobras A3_100_k têm 2.000 passos (o piso da 1021).

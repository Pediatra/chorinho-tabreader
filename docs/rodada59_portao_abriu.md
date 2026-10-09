# Rodada 59 — o portão abriu: 11,7 % de tokens com `tecnica`

## 1. A causa era uma linha, e não era a que eu pensava

Meu diagnóstico anterior apontou "a fração de notas com técnica é baixa". Fui corrigir e descobri
que **estava olhando a linha errada**:

| linha no gerador | o que ela controla | valor encontrado |
| --- | --- | --- |
| `elif rng.random() < 0.08:` | **atribui** a técnica à nota | 8 % ← **era esta** |
| `... and rng.random() < 0.6:` | **desenha** a marca na nota que tem técnica | 60 % |

Eu tentei mudar a segunda (que já estava alta) e o `regex` não casou — o que me obrigou a olhar as
duas. É a segunda vez nesta série que um patch silenciosamente não aplica, e a segunda em que a
verificação (aqui, o `regex`/`grep`) é o que salva.

## 2. A correção e a medição

Mudança: **atribuição de técnica de 8 % → 35 %** (`ast.parse` verificado, `import` verificado).

| | |
| --- | --- |
| tokens | 750 |
| **com rótulo `tecnica`** | **88 (11,7 %)** |
| limiar que eu estabeleci | 10 % |
| **portão** | **PASSOU** |

E a geometria já estava certa desde a rodada anterior: **44 % das notas com técnica fundem o token**
(a diagonal atravessando o algarismo funciona). Faltava só haver notas suficientes para o fenômeno
aparecer — o que é exatamente o que o portão existe para revelar.

## 3. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** — casas | **0,885** bruto · **0,955** sobre os rótulos alcançáveis |
| **canais limpos** | `iwaki` 27/27, `sky` 15/15, `paolo` 30/30 |
| **`raman`** | 13/17 — causa medida (3,2 % × 74 %) e **agora o sintético produz 11,7 %** |
| **classe `tecnica`** | **pronta para treinar** (portão aberto); treino com 3 sementes é o próximo passo |
| **tempo** | faixa (`skyguitar`, 0,16 s) e cor (`cifra club`, 41/41 onsets) |
| **gerador** | íntegro; `ast.parse` + `import` verificados; técnica em 35 % das notas |

## 4. Próximo passo (definido, não especulativo)

1. **treinar com 3 sementes** (nunca 1 — a lição da rodada 20) e aferir no gabarito real;
2. verificar se o `raman` sai de 13/17 e se `iwaki`/`sky`/`paolo` **não regridem** (a condição que
   eu imponho a toda mudança desde a rodada 16);
3. se a classe `tecnica` aparecer no JSON, ligar a **releitura do algarismo** pelo componente
   dominante — que é o segundo passo do desenho, ainda não implementado.

Nota: não treinei nesta rodada de propósito. Um treino de **uma** semente seria repetir exatamente o
erro que a rodada 20 me custou a descobrir; e o orçamento desta rodada já foi gasto em descobrir
*qual* das duas linhas mudar. O portão aberto é o resultado — e ele é verificável por qualquer um que
rode a medição de 25 linhas.

# 1016 — O LLM marca o braço? (teste às cegas)

**Data**: 2026-10-17. **Pergunta do dono**: "você conseguiria marcar vários quadros e eu só
revisaria?". **Quem marca**: o coordenador (Opus 5.5), olhando as imagens. Não é um
detector: nenhum algoritmo de visão acha os pontos. Recortes ampliados com grade de
coordenadas são permitidos, porque são só um jeito de olhar.

**Critérios escritos antes de qualquer marca** (este documento é commitado antes).

## Amostra

- 20 quadros sorteados dos 66 do gabarito do braço, com `random.Random(20261017).sample`:
  q04, q08, q12, q22, q31, q32, q33, q34, q36, q38, q43, q49, q51, q53, q56, q57, q58, q63,
  q64, q66.
- Imagens: `data/saida/maos/m3b/quadros/qNN.png`.
- **Às cegas**: o marcador não abre `data/gold/maos/braco.json`, nem as cópias dele em
  `data/saida/maos/m11/`, nem as saídas das medidas (a) molde e (b) cortes, antes de
  gravar as marcas.
- **Contaminação conhecida**: o marcador já leu, na conversa, quais quadros têm capotraste
  e quais tinham a linha de divisão antiga. Por isso capotraste e painéis **não** entram
  como pergunta.

## O que é marcado

Por quadro, em `data/saida/maos/m16/marcas_llm.json`:
- `braco`: `sim`, `parcial` ou `nao`;
- `nut`: ponto, ou `"fora"`;
- `corda1`, `corda6`: 2 pontos cada;
- `trastes`: lista de `{"numero": n, "ponto": [x, y]}`, com o número explícito.

## Medida

Com `tab.maos_braco_tempo.erros` contra o gabarito do dono, nas métricas da 1015:
- nut e cada traste em casas, ao longo do eixo;
- cordas na perpendicular, em vãos.

## Critérios

1. **Pontos (pergunta "marca por mim e eu reviso")**: passa se **≥ 90 %** das medidas de
   ponto ficam abaixo de **0,25**. Uma medida de ponto é: o nut, cada traste em comum com
   o dono, e o `perp_cordas` de cada quadro.
2. **Número do traste**: passa se **nenhum** traste tem erro ≥ **0,5 casa** (casa
   vizinha). É o erro que a revisão do dono enxerga.
3. **Presença do braço**: passa se **nenhum** quadro tem `braco` do LLM em `sim`/`parcial`
   onde o dono diz `nao`, nem o contrário.

O resultado de cada critério é reportado separadamente. Passar em 2 e 3 sem passar em 1
quer dizer: o LLM serve para triagem e numeração, não para os pixels.

## Resultado (2026-10-17)

As marcas foram gravadas antes de abrir o gabarito: `data/saida/maos/m16/marcas_llm.jsonl`,
sha256 `385ce8950b806ee4…`. Um desvio do pré-registro: o relatório do agente do molde (a)
chegou no meio da marcação. Ele traz só estatísticas por canal, sem coordenadas do dono.

| critério | resultado | veredito |
| --- | --- | --- |
| 1. pontos < 0,25 | 222 de 249 = **0,892** (mediana 0,035) | **REPROVA** (limite 0,90) |
| 2. nenhum traste em casa vizinha | **11 trastes em 3 quadros** (q63, q64, q66) | **REPROVA** |
| 3. presença do braço | 0 desacordos em 20 | passa, mas não informa: os 20 quadros têm braço |

**Por quadro:**
- **17 quadros de braço quase horizontal** (sky guitar, kenneth, cifra club, leonardo ramos,
  shin izumi):
  - nut e trastes muito bons, pior traste ≤ 0,18 casa;
  - zero erros de casa vizinha.
  - As cordas são o ponto fraco. O erro perpendicular vai de 0,04 a 0,55 vão, e 10 de 17 ficaram
    acima de 0,25.
- **3 quadros de braço diagonal** (guitar dell'arte: q63, q64, q66): falso grosseiro.
  - Pior traste de 1,2 a 2,9 casas.
  - Cordas de 1,2 a 3,7 vãos fora: as linhas saem do braço.
  - Nesses três eu li mal a grade de coordenadas num recorte diagonal. Depois estendi os
    trastes pela regra das 12 notas a partir de 1 ou 2 pontos lidos, e o erro se propagou
    para todos.

## Conclusão

- O LLM **não serve para marcar pixels sem revisão de ponto a ponto**:
  - em 3 de 20 quadros ele produziu um braço inteiro errado, com convicção;
  - nos outros, as cordas ficam fora do limite em metade dos quadros.
- Nos 17 quadros fáceis, nut e trastes saíram dentro do limite. É o tipo de quadro em que o
  rastreador e o molde já resolvem pela geometria.
- Não há ganho em trocar o clique do dono por marca do LLM. O uso aceitável é de triagem e
  pré-marcação grosseira (caixa do braço, número aproximado do traste), sempre conferida
  pelo dono.

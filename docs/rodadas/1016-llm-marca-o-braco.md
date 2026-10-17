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

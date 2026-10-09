# Rodada 30 — aferição corrigida: os tempos do rollout não valem nada (e por quê)

## 1. O número correto (o que eu deveria ter reportado)

Contei **instantes distintos** nos 5 JSONs do rollout:

| arquivo | notas | instantes distintos | notas por instante |
| --- | --- | --- | --- |
| guitar_del_0 | 30 | **1** | 30,0 |
| serge_kott_1 | 7 | **1** | 7,0 |
| shin_izumi_2 | 145 | **8** | 18,1 |
| sky_guitar_4 | 134 | **3** | 44,7 |
| violaodecr_3 | 7 | **1** | 7,0 |

Ou seja: o JSON do `sky guitar` dá **o mesmo instante para 45 notas**, e o do `guitar dell'arte`
dá **um único instante para 30 notas**. A coluna "323 notas com tempo" que reportei na rodada
anterior é tecnicamente verdadeira e praticamente inútil. Resumo gravado em
`saida/rollout/resumo.json`.

## 2. A causa: existem DOIS comportamentos de cursor, e eu só implementei um

O `skyguitar` dos recortes tem cursor que **salta** de nota em nota e fica parado ~1 s (medido na
rodada 2: 100 saltos, salto mediano de 109 px, patamares de ~1 s). Meu extrator de tempo procura
justamente **patamares** — runs de ≥ 3 amostras com x constante.

Mas os levantamentos dos canais de vídeo (rodadas de análise) descreveram o cursor **deslizando
suavemente**, a 67–166 px/s. A 100 px/s e 30 fps, o x anda ~3,3 px por quadro: ele **nunca fica
dentro de ±4 px por 3 quadros seguidos**. Resultado: o detector de patamar acha 1–8 eventos numa
janela de 20 s, quando deveria achar dezenas.

**A ferramenta de tempo funciona no cursor que salta e falha no cursor que desliza** — e eu não
tinha percebido porque validei o tempo só no canal que salta.

## 3. A correção

Para cursor que desliza, o instante da nota **não é um patamar, é uma travessia**: o tempo em que
`x(t)` cruza o x da coluna da nota (interpolação linear entre amostras). É o mesmo dado, lido de
outra forma:

- **cursor que salta** → o tempo é o início do patamar (já implementado);
- **cursor que desliza** → o tempo é a travessia de x (a implementar).

Detectar qual dos dois é uma linha: se o número de patamares for << número de notas, é travessia.

## 4. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura; 54 % com cursor |
| (b) gabarito verificado | 96 glifos / 4 canais |
| (c) classificador multi-classe | **0,805 (3 sementes)** |
| (d) pipeline ponta a ponta | **tempo correto só em cursor que salta**; falta a travessia |
| (e) escala nos 3.781 | rollout rodado, mas os tempos não são utilizáveis até (d) ser corrigido |

## 5. Próximo passo

1. implementar **tempo por travessia** (cruzamento de x) e escolher automaticamente entre
   travessia e patamar;
2. revalidar no `skyguitar` (que tem gabarito e tempo conhecido: 1 nota/s) **e** num canal que
   desliza;
3. aí sim os 5 JSONs do rollout passam a ter tempo com significado.

Registro o padrão: três rodadas atrás eu validei o tempo num canal e generalizei. Estava errado —
o mesmo tipo de erro que a variância do treino me ensinou, agora na camada de tempo.

# 1006 — Braço calibrado pela música (notas da tablatura + pontas dos dedos)

**Data**: 2026-10-12. Vídeo: `sky guitar/retrato brasileiro - tab & lesson.mp4` (MVP).

## Ideia

Duas tentativas de achar o braço por linhas da imagem foram reprovadas (rodada
[1005](1005-gabarito-do-braco.md): a tablatura e a pauta têm a mesma assinatura de retas
paralelas; a mão esconde as cordas; a numeração dos trastes não sai só dos trastes). Aqui
nenhuma linha da imagem é usada: a cada nota, o produto diz corda, casa e instante
(`data/saida/produto/mvp.json`); o detector de mãos diz onde estão as 4 pontas da mão esquerda
nesse instante; a nota pisada está sob uma delas. O braço é um plano: uma homografia H leva
(u, v) a pixels, com u = posição a 70 % da casa k pela regra das 12 notas e v = (corda − 1)/5.
H por RANSAC (amostras de 4 notas, uma ponta sorteada por nota; inlier se alguma ponta está a
menos de meia casa do ponto previsto), refino por mínimos quadrados nos inliers.

Resolve por construção: tablatura confundida com braço (nenhuma linha é usada), numeração
dos trastes e ordem das cordas (vêm da tablatura), e a mão vira sinal em vez de oclusão.

## Medido

- 526 notas pisadas, 473 instantes; mão encontrada em todos. **Inliers: 465/526 (88,4 %).**
- **Contra a calibração feita à mão** (`data/saida/maos/m3/braco.json`), cordas 1–6 × casas
  1–12: erro mediano 9,3 px (0,119 casa), p90 17,1 px (0,241), máximo 23,0 px (0,390). Ao
  longo do braço os trastes previstos caem sobre os reais (conferido na imagem); o erro é
  ATRAVÉS do braço e sistemático na corda 1 (mediana 17,1 px, 0,22 casa): a grade sai
  comprimida em direção às cordas graves.
- **Dedo** (avaliador oficial, 53 notas / 40 pisadas):

| método | calibração | total | pisadas |
|---|---|---|---|
| visao_ponta | à mão | 42/53 | 29/40 |
| calib_notas_ponta | pela música | 42/53 | 29/40 |
| calib_notas_ponta, **sem os instantes do gabarito** | pela música | **40/53** | **27/40** |
| visao_ponta_voto | à mão | 43/53 | 30/40 |
| calib_notas_voto | pela música | 43/53 | 30/40 |
| calib_notas_voto, **sem os instantes do gabarito** | pela música | **41/53** | **28/40** |

  O gabarito nunca entra na calibração; mesmo assim, tirar os 39 instantes das notas do
  gabarito custa 2 notas. O número honesto é o da linha "sem os instantes".
- **Estabilidade**: a H muda com a semente do RANSAC (inliers 465, 467, 471; grade difere em
  mediana 4–6 px, máximo 54 px nas bordas). Sem os instantes do gabarito, a grade difere da
  principal em mediana 30 px (máximo 198 px). O refino é algébrico (DLT), não pelo erro de
  reprojeção, e a tolerância é larga.

## Conclusão

A música sozinha reproduz a calibração feita à mão no MVP, sem coordenada fixa e sem olhar
linha nenhuma, com o mesmo acerto de dedo (40–41/53 contra 42–43/53 da calibração à mão).
É o primeiro detector do braço que não depende do layout. Falta: estabilizar (refino por erro
de reprojeção, consenso entre sementes), corrigir o erro através do braço (a ponta do dedo
não fica exatamente sobre a corda) e medir fora do MVP contra o gabarito do braço do dono, o
que exige rodar o produto da tablatura nos vídeos desses quadros.

Código: `tab/maos_pontas_notas.py` (pontas por instante, GPU), `tab/maos_calibrar_por_notas.py`
(homografia, RANSAC, medições). Saídas: `data/saida/maos/m3c/`.

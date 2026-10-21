# 1038 — A casa do capo por vídeo, pela imagem

**Data**: 2026-10-21. O pré-registro vem antes de qualquer previsão. **Depende da 1037**: usa
o par novo que ela escolher.

**A pergunta**: dá para achar a casa do capo de um vídeo só pela imagem? A ideia é comparar o
detector antigo, que acha o nut verdadeiro, com o novo, que põe o nut no capo, e votar entre
os quadros do vídeo.

**Direção do dono** (2026-10-20): a detecção do capo não deve depender de cor nem de tamanho, e
sim do objeto sobre o braço. E precisa ser **consistente**, aparecendo em vários quadros.

**Para que serve**:
1. **A casa do capo de cada vídeo vai para `violao.capotraste`** (decisão 1007), com a fonte
   "imagem". Hoje ela vem só da observação do dono. A trilha áudio estuda a mesma casa pelo
   som (2018), e as duas fontes se conferem (decisão 2005).
2. **Saber que o vídeo tem capo** (o mesmo voto), para mandar o vídeo para revisão se o
   detector não for confiável com capo.

## Método (`tab/maos_braco_capo_imagem.py`)

- **Os dois detectores**:
  - antigo: `L3_todos_s3` + `A4_100_todos_s1`, a escolha da 1032;
  - novo: o par escolhido na 1037.
  - Os dois rodam com a regra 1023 e o sinal v2.
- **Voto do quadro**: o número do traste do antigo sobre o qual cai o nut do novo, se estiver a
  menos de **0,3 da largura da casa**. Com capo na casa c, o nut novo fica no traste c (decisão
  1010).
  - O quadro não vota quando um dos dois não acha o braço, quando um dos dois foi sinalizado,
    ou quando o nut novo cai entre dois trastes.
- **Voto do vídeo**: a casa da maioria, com pelo menos **4 quadros válidos** e **60 %** deles.
- **O voto 0 quer dizer "nada visto", e nunca "sem capo".** Com o nut verdadeiro fora da
  imagem, os dois detectores põem o nut no capo e concordam. Por isso a regra **só afirma casa
  ≥ 1**.

## Amostra

- **Os vídeos que ficaram fora do treino da 1037**: os da M11b, da M25 prova (N), da 1036
  (M36) e do lote da 1039.
- **16 quadros por vídeo**, de 0,10 a 0,90 da duração (`amostrar`, lê o acervo).
- **A verdade é a do dono**, por vídeo (`capo_por_video.json`):
  - a casa escrita na observação dos quadros com `k`;
  - 0 nos vídeos cujos quadros não têm `k`.
  - Quando esta rodada foi escrita, eram **9 vídeos com capo e casa conhecida, e 25 sem
    capo**. Os 8 da 1039 entram quando o dono revisar o lote.

## Critério

| resultado | o que fazer |
| --- | --- |
| **0 vídeos com casa errada afirmada** (inclusive capo afirmado em vídeo sem capo) **e** casa certa em ≥ metade dos vídeos com capo | a casa pela imagem vira fonte de `violao.capotraste` ("imagem"), e o voto vira o sinal "vídeo com capo" do ciclo |
| 0 erros, mas casa certa em < metade dos vídeos com capo | segura, mas cobre pouco. Fica como fonte opcional, e o capo segue pela observação do dono e pelo som |
| 1 ou mais erros | não usar. Ver os erros por tipo (nut verdadeiro fora da imagem, tela dividida, dois violões) |

**Se a 1037 não passar**, esta rodada não roda com o par novo. O voto depende de o novo pôr o
nut no capo, e isso fica registrado.

**Também reportado**: quantos quadros votam por vídeo, e quantos votos 0 aparecem nos vídeos
com capo (o tamanho do caso "nut verdadeiro fora da imagem").

## Riscos declarados antes

- **Os dois detectores têm erros próprios.** Um erro de uma casa em qualquer um deles vira voto
  errado. A maioria de 60 % e o mínimo de 4 quadros existem para isso.
- **Os vídeos verticais (violaodecria) quase nunca mostram o nut verdadeiro**: o esperado é
  "sem dado" neles.
- **A M11b foi usada para escolher os pesos da 1037.** Os vídeos dela são vistos, mas não
  entraram no treino.

## Resultado (2026-10-21): não rodou

A 1037 reprovou (critérios 2 e 3), e o par escolhido nela inverte o braço. Pela regra acima
("se a 1037 não passar, esta rodada não roda"), a previsão não foi feita. Os 688 quadros de 43
vídeos ficam em `m38/quadros`, prontos para quando houver um par novo que passe (1041). Nada
desta rodada foi visto, então ela continua valendo como pré-registro.

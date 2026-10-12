# 1005 — Gabarito do braço (M3b)

**Data**: 2026-10-12. **Decisão**: [1003](../decisoes/1003-fases-das-maos.md) (o detector do braço
precisa de gabarito próprio; a calibração do M3 usava coordenadas fixas de um vídeo e
calibrava em 2/30 vídeos).

## O que foi rotulado

`data/gold/maos/braco.json`, pelo dono, com `tab.maos_braco_gabarito` (servidor como o da
ferramenta de dedos, porta 8098, imagem `chorinho-maos:dev`). 20 quadros do cache, 8 canais
com mais vídeos, vídeos distintos, semente 20261012, MVP como controle (q02).

- braço `sim` em 20/20; corda 1 e corda 6 (2 pontos cada) em 20/20;
- nut clicado em 19/20; q09 com nut coberto pela mão (câmera de lado), `fora`;
- trastes por quadro: 13 a 20 (19 ou 20 em 15 dos 20);
- capotraste anotado pelo dono em q04 (casa 2), q10 (casa 2) e q14 (casa 1);
- q19: nut preto ("se tiver procurando por cor pode falhar").

## Correções da ferramenta durante o uso

- a imagem antiga ficava na tela até a nova carregar e aceitava clique (achado no teste
  antes de entregar);
- "clicar perto de um traste marcado remove" apagava o vizinho nos trastes juntos perto do
  corpo (apontado pelo dono): clique comum sempre adiciona, botão direito remove.

## Ideias do dono para o detector (registradas para o próximo passo)

1. **O braço é geometria conhecida.** A posição dos trastes segue a regra das 12 notas
   (distância do nut ao traste n = L·(1 − 2^(−n/12))). Com o nut e um traste, ou dois
   trastes de número conhecido, o resto sai por conta. O que distorce é o ângulo da
   câmera: o braço é um plano, então uma homografia (as duas cordas marcadas dão os 4
   cantos) leva para a vista de frente, onde a regra vale exatamente.
2. **Violão de aço tem ~20 trastes; de náilon, 18 a 19.** Serve para diferenciar o tipo de
   violão (e o timbre) se precisar.
3. **Sem nut à vista, conte a partir da boca do violão**: o último traste fica junto da boca
   e tem número conhecido pelo tipo de violão.

## Próximo

Detector do braço medido contra este gabarito (erro em px das cordas 1/6, do nut e dos
trastes; numeração certa), começando pelas ideias 1 e 3.

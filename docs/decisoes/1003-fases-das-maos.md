# 1003 — Fases da trilha das mãos depois do M3 (gabarito do braço primeiro)

**Data**: 2026-10-12. **Decisão do dono** (chat: "concordo com a ordem, gabarito do braço
primeiro").

## Contexto

O plano original (`docs/guias/contexto-maos.md`, seção 5) tinha M0 censo, M1 detector,
M2 gabarito de dedos, M3 nota → dedo e M4 esquema. No uso, apareceram três lacunas:

1. **Braço do violão sem gabarito próprio.** O M3 precisa saber onde estão cordas, trastes
   e casas em pixels. Na rodada [1004](../rodadas/1004-dedo-por-visao.md) isso foi feito com
   coordenadas fixas do vídeo do MVP: 44/53 lá, mas a calibração passa em 2 de 30 vídeos
   sorteados, e só dá para medir com critérios internos (sem gabarito).
2. **Mão direita nota a nota é fraca.** O dono rotulou o dedo da direita em parte por
   inferência: com poucos quadros por ataque, o dedo que toca não se vê com certeza.
3. **Técnicas e padrões fora do plano.** Ligado, slide, vibrato, harmônico (mão esquerda) e
   arpejo, rasgueado, trêmolo, apoiado/sem apoio (mão direita) não estavam previstos. A
   pestana entrou no M2 a pedido do dono.

## Decisão

Ordem nova, depois do M3 no vídeo do MVP:

- **M3b — Gabarito do braço (próxima).** O dono marca, em ~20 quadros de canais e layouts
  diferentes, o nut, alguns trastes e as cordas 1 e 6. Mede a calibração do braço de
  verdade e permite desenvolvê-la para qualquer layout, sem coordenada fixa. Destrava o M3
  fora do MVP.
- **M5 — Padrões da mão direita, por trecho.** Rótulo por trecho (ex.: "compassos 5–8:
  arpejo p-i-m-a") em vez de dedo por nota. Os tipos a distinguir estão em aberto, com o
  dono; proposta inicial: arpejo (com a sequência), rasgueado, trêmolo, acorde plaqueado,
  melodia com alternância i-m; apoiado ou sem apoio.
- **M6 — Técnicas pela mão, cruzadas com a tablatura.** Ligado, slide, vibrato e harmônico
  vistos na mão esquerda, conferidos com os símbolos que a trilha da tablatura já lê.
- **M4 — Esquema** continua: o bloco `maos` do JSON recebe o que cada fase medir.

## Consequências

- O número do M3 (44/53) fica declarado como de um vídeo só até o M3b medir a calibração
  em outros layouts.
- A direita nota a nota não ganha mais rótulo do dono por ora; o esforço vai para o M5.

## Backlog (anotado pelo dono durante o M3b, 2026-10-12)

- **Detecção de capotraste.** Visto no quadro q04 do gabarito do braço (`kenneth acoustic`;
  o vídeo escreve "Capo: Fret 2" na tela; q14 do mesmo canal diz "Capo: Fret 1"). Importa
  para a ligação nota → dedo: com capotraste na casa N, a "casa 0" da tablatura é a casa N
  física, e a casa k da tablatura fica na casa N + k do braço. Fontes possíveis: o texto na
  tela, o próprio capotraste visto no braço, ou o canal (configs/canais.yaml). No gabarito
  do braço, os trastes são numerados a partir do nut real, não do capotraste.

# 1017 — Violão molde e cortes de câmera (medidas da 1009)

**Data**: 2026-10-17. As duas medidas baratas pedidas pela decisão
[1009](../decisoes/1009-estrategia-do-braco-quadro-a-quadro.md) antes do M11b. São medidas
exploratórias: não há critério de aceite, e nada entra no produto.

## (a) Violão molde nas marcas do dono

`python -m tab.maos_braco_molde` → `data/saida/maos/m11/molde/` (`molde.json` e desenhos).

**Entram 40 dos 66 quadros.** Ficam de fora:
- 24 quadros com painéis, porque nenhuma geometria atravessa uma caixa
  ([1008](../decisoes/1008-partes-do-violao-no-gabarito-do-braco.md)). Todo o sky guitar
  cai aqui.
- 2 quadros com a pestana fora (q09, q63).

**Grandezas** (s é a fração da escala, 0 na pestana e 1 onde a regra das 12 notas com
perspectiva põe o saddle):

| canal | n | retidão (vãos) | s_saddle | s_boca | s_cavalete |
| --- | --- | --- | --- | --- | --- |
| cifra club | 7 | 0,07 | 1,022 [1,008; 1,032] | 0,756 | 0,997 |
| guitar dell'arte | 2 | 0,09 | 1,021 | 0,726 | 1,026 |
| iwaki | 6 | 0,39 (máx 1,02) | 1,029 [1,023; 1,033] | 0,737 | 1,030 |
| kenneth acoustic | 6–7 | 0,12 | 1,024 [1,021; 1,033] | 0,785 | 1,018 |
| leonardo ramos | 3–7 | 0,13 | 1,054 [1,025; 1,065] | 0,736 | 1,022 |
| robert lunn | 2–3 | 0,35 | 1,019 | 0,736 | 1,027 |
| shin izumi | 6–7 | 0,19 | 1,037 [1,032; 1,045] | 0,778 | 1,016 |

Os valores são medianas; os colchetes dão o mínimo e o máximo. O resíduo do ajuste projetivo
nos trastes tem mediana de 2 a 4 px. O máximo é 28 px em q56 e 24 px em q06, ambos nos
trastes 1 e 2.

**Leitura:**
1. **A corda é reta da pestana ao saddle.**
   - O saddle cai a 0,07–0,39 vão da corda prolongada, na mediana por canal.
   - Dois quadros passam de 0,5 vão: q59 (1,02) e q61 (0,56). Olhei o desenho de q59: as
     retas cruzam o rastilho de forma visualmente correta, mas o rastilho aparece pequeno
     e em ângulo, e o vão ali tem poucos pixels.
2. **O saddle cai sempre um pouco depois de s = 1**, entre 1,008 e 1,065, e nunca antes.
   - A compensação física do rastilho é bem menor (cerca de 0,5 % da escala). Uma parte do
     viés vem de levar o ajuste dos trastes 1 a 20 (s ≤ 0,69) até s = 1.
   - Para o molde, o que importa é que o valor é estável dentro de cada canal: amplitude
     de cerca de 0,01 a 0,02, exceto leonardo ramos.
   - Uso: prever o saddle por s ≈ 1,03 e conferir.
3. **A boca dá uma âncora estável.**
   - s_boca vai de 0,73 a 0,79 por canal, com amplitude de cerca de 0,02 dentro de cada
     canal.
   - A elipse de q08 é absurda (razão entre eixos de 10), porque os pontos ficaram num arco
     curto. O código a marca como absurda.
4. **O cavalete fica em s ≈ 1,00–1,03, junto do saddle.** Isso é coerente com a reta do
   cavalete passando pelo rastilho.

## (b) Cortes de câmera numa amostra do acervo

`python -m tab.maos_cortes` → `data/saida/maos/m11/cortes/` (tabelas e folhas).

**Amostra e método:**
- 53 vídeos de 19 canais, 267 min, semente 20261017, até 3 vídeos por canal sorteados do
  censo das mãos.
- Só os quadros-chave são decodificados (`-discard nokey`). Cada um é comparado com o
  seguinte por histograma HSV, fora da tablatura.
- O limiar de 0,30 de Bhattacharyya foi escolhido depois de ver a distribuição (vale raso).

| limiar | trocas de plano | vídeos com troca |
| --- | --- | --- |
| 0,20 | 694 | 47 |
| **0,30** | **483** (1,81/min) | **43** |
| 0,50 | 326 | 42 |

Na conferência visual do agente, 36 trocas sorteadas, 12 por faixa de distância, deram:
- 12 trocas de câmera (33 %);
- 16 trocas de tela, fade ou efeito;
- 6 falsas, todas na faixa de 0,30 a 0,45.

**Minha conferência da folha de quase-cortes** (distância de 0,28 a 0,30, abaixo do limiar):
- A maioria é mesmo o mesmo plano.
- Há trocas reais que o histograma **não vê**:
  - mudança de enquadramento ou zoom na mesma cena (guitar dell'arte V04 650 s e 730 s, V06
    101 s);
  - foto sobreposta (robert lunn, serge kottelat);
  - faixa de texto (pablo romé).
- Por isso, **a contagem é um piso para troca de câmera**, e o histograma não serve como
  detector de corte para o rastreio.

**Por canal** (3 vídeos por canal, então os números são ruidosos):
- de 0 a 0,5 troca por minuto: iwaki, lonelypicker, paolo d'angelo, shin izumi, tv on guitar,
  sky guitar, transcriptor;
- guitar dell'arte chega a 5,2 por minuto;
- 10 dos 53 vídeos não têm nenhuma troca.

**Leitura para o M11b:**
- A impressão do dono, "câmera parada", vale para a maioria dos canais **entre** trocas.
- Mas 43 dos 53 vídeos têm alguma troca, e o canal com mais trocas (guitar dell'arte) é
  justamente o de braço diagonal e de enquadramento variável.
- O rastreio encadeado precisa detectar a troca **pela própria geometria**: queda de
  inliers ou salto da homografia. O histograma de cor perde o zoom na mesma cena.

## Observação lateral

O acervo tem 5.241 mp4, e não os 3.899 que o AGENTS.md cita, porque o dono continua
baixando. O censo das mãos cobre 2.798 vídeos.

# 2003 — Áudio A1b: o "degrau" de 448 s não é degrau

Data: 2026-10-13. Vídeo do MVP (`sky guitar/retrato brasileiro`). Dados: os 636 eventos
da rodada 2002 (`data/saida/audio/a1/atraso_mvp.json`, fluxo, passada 2). Scripts e
saídas: `data/saida/audio/a1b/`.

## Pergunta

A rodada 2002 viu Δ = t_som − t_marcador em ~100 ms até 448 s e ~210 ms depois, com o
salto na troca da tela 6 para a 7. O que causa o salto?

## Hipóteses e o que a medição disse

| hipótese | medição | veredito |
| --- | --- | --- |
| troca de observador do marcador | as exibições dos dois lados usam `posicao` | **descartada** |
| animação e violonista em andamentos diferentes | razão soma(intervalos do som) / soma(intervalos do marcador) por exibição: 0,994 a 1,010 (22 exibições); global **1,0017** em 614 intervalos | **descartada**: o andamento médio bate |
| pausa a mais no som só na troca 6→7 | intervalo som − marcador nas 21 trocas de página: mediana −36 ms; a 6→7 dá +54 ms, e há 5 outras positivas (+162, +96, +54, +32, +5) | **descartada**; e o Δ já sobe para ~200 ms em 444 s, antes da troca |
| corte de edição em ~448 s | vídeo, 270 quadros de 444 a 453 s: único pico fora do painel em **448,515** (×23 a mediana), que é a **troca de página** da partitura e da TAB (compasso 21 → 25), com a mão se movendo logo depois; câmera fixa, sem outro corte. Áudio: RMS de 10 ms sem silêncio, sem clique, sem salto do fundo em 448,5; os 6 degraus de nível caem todos em ataques de nota | **descartada**: não há corte no áudio |

## O que o Δ é, então

- **Dentro de cada página o Δ é quase constante**: inclinação Δ × t com |t| ≥ 2 em só
  3 de 21 exibições (n > 8); resíduo de 30 a 90 ms por exibição.
- **O nível passeia, para cima e para baixo**: a mediana móvel de 15 eventos vai de 60 a
  324 ms e muda mais de 50 ms em 13 pontos do vídeo, 7 subindo e 6 caindo (ex.: cai de
  133 para 61 ms em ~400 s; sobe de 201 para 300 em ~590 s). O salto de 442–467 s
  (76 → 235 ms) é o maior, não o único.
- **Nota a nota, o som não segue a grade da animação**: a diferença entre intervalos
  consecutivos (som − marcador) tem mediana +3 ms e **desvio padrão 90 ms**. Os
  intervalos do marcador são quase todos 0,667 ou 0,734 s; os do som variam livremente.

Leitura: o marcador anda num relógio regular, o do software de partitura; o violonista
toca com o mesmo andamento médio, mas com rubato. A defasagem entre os dois vagueia
na escala de dezenas de segundos (~60–300 ms) e, nota a nota, oscila ±90 ms. Isso
explica o histograma bimodal da 2002 sem precisar de corte nem de evento único.

**Conferência do dono (2026-10-13)**: ouviu os clipes da 2002; o clique no ataque
detectado cai junto com as notas.

## Consequências para a trilha

1. **O marcador não é verdade de tempo do som** neste vídeo, nem com um atraso fixo
   (Δ de 60 a 300 ms, ±90 ms nota a nota). A régua do A3 proposta no contexto
   (`|t_audio − (t_marcador + atraso)| ≤ 50 ms`) **não mede nada útil aqui**.
2. O marcador continua valendo como **identidade da coluna**: ele diz QUAL coluna vem a
   seguir e onde (±0,3 s) procurar. O tempo fino tem de vir do áudio.
3. A régua do tempo do som precisa de verdade de som: ataques conferidos pelo dono (como
   a escuta dos clipes), não derivados do marcador.

## Achado lateral (trilha tablatura, não editado)

`tab.leitor.pts_nativos(video, 444, 453)` devolveu 268 PTS; o ffmpeg decodifica 270
quadros no intervalo, e o ffprobe confirma os PTS 452,9525 e 452,9859 (< t1). O
`-read_intervals` com fim em t1 parece perder os últimos quadros da janela. Repassar à
trilha tablatura.

## Limites

Um vídeo; viés do detector (−28 ms, rodada 2002) não descontado; acorde rolado faz parte
do ±90 ms nota a nota.

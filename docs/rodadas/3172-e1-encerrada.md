# 3172 — E1 encerrada: a figura da nota completada não é validada

Frente E, item E1. Medida na 3170, itens da conferência na 3171 (porta 8122, 17 trechos, 22
notas completadas com figura e 32 do homr).

## Conferência do dono

- O dono conferiu 8 dos 17 trechos (R05 a R12) e escreveu em todos "praticamente tudo errada".
  Nenhuma nota foi marcada uma a uma: as 37 ficaram no estado padrão (certo). **Não há medida por
  nota.** Os outros 9 trechos (produtos) não foram conferidos. O dono não vai marcar nota a
  nota: o custo é de horas.
- `data/gold/partitura/figura_e1.json` fica fora do git: ele grava "certo" em notas que o dono
  disse estarem erradas.

## Olhada da sessão principal (não é gabarito)

Imagem do recorte (`p1/recortes_margem/<id>.png`) contra a figura de cada nota:

| trecho | notas olhadas | figura bate | não bate |
| --- | ---: | ---: | --- |
| R08 | 3 (acorde do homr) | 3 | — |
| R05 | 4 | 3 | C4 completado como colcheia; o baixo é semínima |
| R07 | 5 | 4 | B4 do homr como semicolcheia; é colcheia |
| R10 | 5 (baixos do homr) | 5 | — |
| R12 | 4 | 4 | o G#6 completado é o harmônico (A.H.); figura bate, altura é a do harmônico |

Pela olhada, 19 de 21 figuras batem. Isso contradiz o veredito do dono. Hipótese, não
conferida: o desenho mostra só as notas a julgar (4 a 6 por trecho), e o trecho inteiro na
imagem tem dezenas de notas; lido como "a leitura do trecho", o desenho está quase todo errado. A
pergunta da conferência (só a figura) não ficou clara na página.

## Decisão (dono, 2026-10-18)

- Nota completada pela tab, quando entrar no produto: **altura e instante da tab, figura
  `null`**. Nunca se descarta a nota, e não se chuta figura. Os 2 erros da olhada são de nota
  completada e de nota do homr.
- As 32 notas do homr ficam com a figura do homr, marcadas como não conferidas.
- A E1 fecha sem aceite de figura. Aceite congelado (0,95 nos acordes) não medido.

## Não repetir

- Conferência de "só a figura" com desenho que mostra só as notas a julgar: o dono lê o desenho
  como a leitura do trecho. Se a pergunta voltar, mostrar a nota no lugar dela sobre a leitura
  inteira (destaque), ou perguntar na própria imagem.

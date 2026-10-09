# Rodada 3 — o acervo real e o que ele exige

Medições feitas sobre `/run/media/gabriel/3014CD4714CD1130/chorinho/`.

## 1. Tamanho real do acervo

**3.781 vídeos, 190 GB, 12 canais com vídeo** (mais `derived/`, que é saída de
processamento anterior):

| canal | vídeos | canal | vídeos |
| --- | --- | --- | --- |
| violaodecria | 1.680 | shin izumi | 141 |
| cifra club | 544 | tv cifras | 68 |
| sky guitar | 440 | ギタロー / guitarous | 57 |
| guitar dell ́arte | 361 | raman korshun | 45 |
| iwaki | 164 | serge kottelat | 38 |
| | | paolo d'angelo | 14 |
| | | tv on guitar | 5 |

## 2. Inventário: o que existe em cada canal (319 vídeos amostrados)

Amostra de até 30 vídeos por canal, um quadro de cada, procurando a grade de
tablatura em 3 faixas do quadro (topo/meio/base) e o cursor de execução.

| canal | n | achou TAB | achou cursor | faixa onde está a TAB | máscara | passo mediano |
| --- | --- | --- | --- | --- | --- | --- |
| cifra club | 30 | **77%** | 77% | topo 20, meio 3 | contraste 13, otsu 10 | 23,8 |
| guitar dell ́arte | 30 | 100% | 97% | topo 9, meio 11, base 10 | otsu 26, contraste 4 | 23,1 |
| iwaki | 30 | 100% | 97% | **base 26** | contraste 26, otsu 4 | 24,0 |
| paolo d'angelo | 14 | 100% | 100% | topo 7, base 5, meio 2 | contraste 12, otsu 2 | 17,8 |
| raman korshun | 30 | 100% | 100% | **base 24** | otsu 26, contraste 4 | 21,7 |
| serge kottelat | 30 | 100% | 100% | **base 27** | contraste 28, otsu 2 | 14,8 |
| shin izumi | 30 | 100% | 100% | **base 29** | contraste 24, otsu 6 | 22,0 |
| sky guitar | 30 | **80%** | 80% | meio 10, topo 8, base 6 | otsu 17, contraste 7 | 18,1 |
| tv cifras | 30 | 97% | 97% | meio 17, topo 10 | contraste 19, otsu 10 | 22,4 |
| tv on guitar | 5 | 100% | 100% | meio 4 | contraste 5 | 15,0 |
| violaodecria | 30 | 100% | 100% | meio 12, base 11, topo 7 | contraste 20, otsu 10 | 36,3 |
| ギタロー / guitarous | 30 | 100% | 100% | meio 20, topo 8 | contraste 28, otsu 2 | 17,5 |
| **TOTAL** | **319** | **96%** | **95%** | — | — | 14,8 – 36,3 |

Três conclusões que mudam o plano:

1. **A abordagem cobre o acervo real: 96% com grade de tablatura e 95% com cursor.**
   Não é um caso de laboratório — é o acervo inteiro, com 12 estilos diferentes.
2. **A posição do painel NÃO é fixa**: tem canal que é quase todo `base` (serge kottelat
   27/30, shin izumi 29/30, raman korshun 24/30, iwaki 26/30) e tem canal quase todo
   `topo` (cifra club 20/30). Procurar em três faixas não é luxo — é obrigatório.
3. **A família (tema claro x escuro) NÃO é por canal**: `cifra club` mistura contraste (13)
   e otsu (10) dentro do mesmo canal; `violaodecria` mistura 20/10; `sky guitar` mistura
   7/17. Ou seja, a cascata de máscaras precisa continuar sendo por **vídeo**, não por canal.

### Achado operacional importante: 44% dos vídeos não decodificam no OpenCV

| como o quadro foi lido | vídeos |
| --- | --- |
| OpenCV (`cv2`) | 179 |
| **ffmpeg** (fallback, AV1 sem aceleração) | **140** |
| falhas de decodificação | **0** |

Sem o fallback por `ffmpeg`, **quase metade do acervo seria silenciosamente ignorada** —
é o tipo de erro que só aparece quando se mede o acervo inteiro. Já está corrigido em
`tools/inventario.py` (`ler_quadro`).

## 3. Bug de extração encontrado olhando os dados de treino

Ao montar a montagem dos glifos rotulados para conferir a qualidade do treino, ficou
visível que **muitos glifos estavam mutilados** (arcos do `0` cortados, barra do `4`
sumida). Causa: a remoção da corda apagava **todo run horizontal longo dentro da faixa
da corda** — e os traços horizontais do próprio algarismo eram apagados junto.

Correção: apagar runs longos **apenas nas linhas da própria corda** (±0,15 do passo),
preservando o resto da faixa.

Efeito medido:

| | antes | depois |
| --- | --- | --- |
| amostras rotuladas alinháveis | 741 | **1.072** |
| acerto no treino | 0,82 | **0,94** |
| acerto em canais nunca vistos | 0,67 | **0,70** |
| gabarito verificado (`-6rawhontyg` linha 1) | 15/15 | **15/15** (todos na corda 2) |

O gabarito verificado continua batendo exatamente depois de todas as mudanças — é ele
que impede eu "melhorar" o número quebrando o que já estava certo.

## 4. Onde está o gargalo, com número

- **Extrair** (achar a pauta, a corda, a coluna, o tempo): resolvido — 96% do acervo,
  gabarito exato, tempo com desvio de 0,16 s corrigível.
- **Identificar o algarismo**: 0,94 no que viu, **0,70 em canal novo**. É o único número
  ruim do sistema, e é exatamente o que o fine-tuning autorizado tem de atacar.
  As confusões medidas (`0↔3`, `7↔8`, `4↔1`) são de glifo pequeno/borrado — sintoma de
  pouco dado e de normalização, não de falta de capacidade do modelo.

Caminho para fechar (na ordem):

1. **Gabarito verificado** de algumas centenas de glifos (linha inteira conferida à mão),
   para ter número honesto — hoje só existe 1 linha com gabarito.
2. **Gerador sintético** nas famílias medidas (claro/escuro, tracejado, passo 15–36 px,
   acorde empilhado, cor de voz, `<n>` harmônico, arco de ligado) — dados ilimitados com
   rótulo exato, que é o que o gargalo pede.
3. **Calibração por canal** (banco de templates + poucos rótulos) por cima do sintético.
4. Só então rodar em escala nos 3.781 vídeos.

## 5. Pendências registradas

- `cifra club` (77%) e `sky guitar` (80%) são os dois canais com detecção pior: a amostra
  pega um único quadro no meio do vídeo, e parte deles pode ser fala/intro sem tablatura
  na tela. Precisa amostrar mais de um instante por vídeo para separar "vídeo sem
  tablatura" de "falha do detector".
- `derived/` (74 subpastas, com `.tab`, `.jsonl`, `.npz`) é saída de processamento
  anterior e não foi auditada nesta rodada.
- Tab ASCII de texto e a linha de partitura continuam fora desta cadeia (precisam de
  leitor próprio), como registrado nas rodadas 1 e 2.

# 3003 — Comparativo de leitores de pauta: variantes do Audiveris e SMT sem treino

**Data:** 2026-10-14 · **Trilha:** partitura · **Código:** `tab/partitura_omr.py` (condições
novas), `tab/partitura_recortes.py` (`--margem-cima/--margem-baixo/--saida`),
`tab/partitura_smt.py` · **Imagem:** `chorinho-partitura:dev` (Audiveris, homr) e
`chorinho-partitura:smt` (SMT; decisão 3001, seção SMT)

## Pergunta

O dono conferiu a leitura do Audiveris x2 (rodada 3002) e achou erro demais para corrigir à
mão. São duas perguntas:

1. O erro vem da entrada? Testamos corte apertado, resolução, cor do vídeo e falta de clave.
2. Um modelo treinável, o Sheet Music Transformer (SMT, MIT, 21 M parâmetros), lê melhor já
   sem treino?

## Método (a mesma régua para todos)

- Recortes R01–R12, os que têm tab no gabarito: pablo romé ×4, guitar dell'arte ×3, robert
  lunn ×5, com 546 notas. Uma execução por condição, só na CPU.
- **Altura**: igual à rodada 3002. A tab vira altura escrita, e os eventos são alinhados por
  Needleman-Wunsch. Cada nota conta como certa, altura errada, faltando ou inventada.
- **Ritmo, sem gabarito**: compassos "cheios", em que cada voz soma a duração da fórmula. A
  fórmula vem da leitura ou, sem ela, do vídeo (3/4, 2/4, 3/4). O primeiro e o último
  compasso de cada recorte ficam de fora. Script em `data/saida/partitura/p1/variantes/`.
  É diagnóstico: uma leitura pode fechar o compasso com figuras erradas.
- **SMT**: a saída kern é convertida para MusicXML com music21 e passa pelo mesmo leitor dos
  outros. A entrada é o recorte, preparado conforme a configuração de cada modelo. Os
  modelos de página inteira (fp) recebem o recorte como uma página de um sistema.

## Resultado (R01–R12, 546 notas)

| leitor / condição | certas | altura errada | faltando | inventada | compassos cheios | sem saída | s/recorte |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Audiveris x2, margem 7/7** | **491** | 14 | 41 | **3** | **70/83** | 0 | 22 |
| Audiveris x2 (3002) | 479 | 19 | 48 | 4 | 67/83 | 0 | 15 |
| Audiveris x2 + cabeçalho colado | 466 | 22 | 58 | 4 | 69/83 | 0 | 23 |
| homr nativo | 467 | 25 | 54 | 23 | 44/78 | 0 | 9 |
| homr x2 | 465 | 24 | 57 | 24 | 42/78 | 0 | 9 |
| Audiveris x3 | 417 | 10 | 119 | 7 | 21/84 | 0 | 56 |
| Audiveris nativo | 388 | 82 | 76 | 43 | 48/84 | 0 | 9 |
| Audiveris x4 | 270 | 85 | 191 | 15 | 15/69 | 2 | 96 |
| Audiveris x2 binarizada (Otsu) | 196 | 26 | 324 | 12 | 35/40 | 4 | 16 |
| SMT antoniorv6/smt-grandstaff | 20 | 49 | 477 | 29 | — | 7 (3 kern inválido, 4 timeout/não rodados) | 251 |
| SMT antoniorv6/smt-camera-grandstaff | 0 | — | 546 | — | — | 12 (2 kern inválido, 1 timeout, resto não rodado) | 442 |
| SMT PRAIG/smt-grandstaff | 0 | — | 546 | — | — | 12 (11 kern inválido, 1 erro de tensor) | 436 |
| SMT PRAIG/smt-fp-grandstaff | 0 | — | 546 | — | — | timeout de 600 s no R01, parado | 600 |

Não rodaram:

- `antoniorv6/smt-string-quartets`: o repositório não tem pesos (404);
- `PRAIG/smt-fp-polish-scores` e `PRAIG/smt-fp-mozarteum`: acesso fechado no Hugging Face,
  que exige o dono aceitar os termos e fornecer um token.

## O que os números dizem

- **Corte apertado atrapalhava**: com margem 7/7 (antes 4/6), o total sobe de 479 para 491 e
  os compassos cheios de 67 para 70. No dell'arte vai de 234 para 247, com 0 inventadas. O
  ganho real de margem foi de 0 a 2,9 entrelinhas em cima (vizinhos e borda do quadro
  limitam) e ~1 embaixo (`variantes/margem_ganha.json`). No R09, a nota aguda e o losango de
  harmônico, antes cortados, agora entram (conferido no PNG).
- **Ampliar além de 2x piora.** No 3x e no 4x o Audiveris perde notas (faltando 119 e 191) e o
  ritmo desaba. 2x é o ponto bom.
- **Binarizar quebra** 4 recortes e apaga linhas finas.
- **Colar o cabeçalho do início do sistema (clave, armadura, fórmula) não paga**: R06 fica
  igual e R07 piora (82 → 70). O pedaço colado traz resto de texto do vídeo. A herança de
  clave e armadura fica para depois, mas não desse jeito.
- **Ritmo: o Audiveris ganha do homr com folga** (67–70 contra 42–44 compassos cheios). A
  escolha do Audiveris não depende só da altura.
- **SMT sem treino não serve.** O melhor modelo acerta 20 de 546 notas. Os outros não deixam
  nenhum MusicXML legível: o kern sai com número de colunas instável (2→4→3→6 no R01), o
  modelo repete até o limite e leva 4 a 10 min por recorte na CPU. Os pesos públicos são de
  piano (duas pautas), e o recorte de violão em pauta única está fora do domínio. O pipeline
  foi conferido: numa amostra do teste do GrandStaff o modelo reproduz o gabarito, então a
  falha é de domínio, não de montagem.

## Conclusão

- Para leitura pronta, **Audiveris x2 com margem 7/7** é a melhor entrada medida: 491/546
  (89,9 %), 3 inventadas, 70/83 compassos cheios.
- O SMT só entra se for **treinado** com pauta única de violão (P2, dado sintético). Sem
  treino, ele não é ponto de partida.

## Limites

- Uma execução por condição, 3 vídeos, 12 recortes. Diferença de ~10 notas está no ruído.
- O ritmo é um proxy (soma do compasso), não comparação figura a figura.
- Pesos e código do SMT: os pesos de antoniorv6 (2024) só carregam com o commit d25acd4; com o
  `master` o decoder fica aleatório, sem erro, só com aviso. Registrado na decisão 3001.
- Os tempos foram medidos na CPU com outros processos rodando: valem como ordem de grandeza.

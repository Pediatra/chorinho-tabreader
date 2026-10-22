# Plano — base de treino das mãos (cada nota com as duas mãos, o braço e o som)

**Data**: 2026-10-16. **Trilha**: mãos. **Estado**: proposta; os critérios marcados como
"proposta" são congelados com o dono **antes** de cada medida. Decisão:
[`1006`](../decisoes/1006-maos-viram-base-de-treino.md).

## 0. Resumo em 30 segundos

- **O objetivo do dono.** No futuro, um modelo recebe só o vídeo e o áudio, sem tablatura na
  tela, e devolve a tablatura ou a partitura. Para treinar esse modelo, precisamos de uma base em
  que **cada nota tocada** tenha, juntos:
  - o gabarito: corda, casa, técnica e, quando houver, a nota da partitura;
  - o som;
  - o braço do violão: pestana, trastes e cordas;
  - a mão esquerda e a mão direita: pontos da mão e dos dedos **quadro a quadro**, ou seja, o
    movimento.
- **A tablatura da tela é o gabarito; as mãos e o som são a entrada.** O gabarito sai da trilha da
  tablatura. Esta trilha **não adivinha a corda pela mão**. Ela grava a mão bem gravada, nota por
  nota, e garante que a associação está certa.
- **O risco que o dono apontou é o centro do plano.** Se a base disser que um movimento de mão é
  de uma nota quando é de outra, o modelo aprende errado. Por isso:
  - cada associação passa por checagens independentes (seção 3);
  - a taxa de associação falsa é medida pelo dono antes de escalar.
- **Ordem**:
  1. M10 — esquema e regras;
  2. M11 — braço quadro a quadro, a peça que falta e a mais difícil;
  3. M12 — mãos quadro a quadro;
  4. M13 — tempo do som por nota, que vem da trilha do áudio;
  5. M14 — associação e controle de qualidade;
  6. M15 — piloto no sky guitar, depois os outros canais;
  7. M16 — o modelo, depois da base.
- **Param** as ondas que tentavam tirar a corda da mão por regra (M8, M9, frentes A–D). O
  decodificador só pelas notas (M8, D1: 88 % da corda do professor) fica como **linha de base**
  que o modelo futuro tem de bater.

## 1. O que já existe (não refazer)

| peça | estado medido | onde |
| --- | --- | --- |
| tablatura + `t_ini` por nota | MVP: 485/491 notas, casa 483/485, tempo de marcador 39/40; fase 8 generalizando canais | trilha tablatura, `chorinho/video@1` |
| tempo do som por coluna (`t_audio`) | o som vem 165–275 ms (mediana) **depois** do marcador, vagueando; o alinhador dá `t_audio` em 630/637, 392/464, 317/322 e 323/415 ataques (4 vídeos) | trilha áudio, decisão 2003, `chorinho/audio@1` |
| partitura pareada à coluna da tablatura | ritmo ~99 %; par com a coluna 336/337 | trilha partitura, decisão 3002 |
| detector de mãos | RTMW Wholebody (GPU) + MediaPipe: 86/90 quadros certos (rótulo provisório), 0,2 s por quadro na GPU, determinístico | `tab/maos/detector.py`, decisão 1002 |
| mãos visíveis por canal | 2.366 de 2.798 vídeos "servem" (85 %); sky guitar 100 %, iwaki 100 %, leonardo ramos 99 %, kenneth 99 %, shin izumi 99 % | censo M0, rodada 1001 |
| gabarito do braço | **36 quadros de 28 vídeos**, marcados pelo dono: pestana, trastes, cordas 1 e 6 | `data/gold/maos/braco.json` |
| geometria dos trastes | com pestana + trastes 5 e 12 e o modelo projetivo, 96 % de 327 trastes a < 1/4 de casa | `tab/maos/braco/geometria.py`, rodada 1005 |
| braço que se mexe | com uma marcação só por vídeo: ao longo do braço erra ≤ 0,16 casa; **na direção das cordas, até 2,4 cordas** | rodada 1014, q24–q31 |
| gesto da mão direita × som | pico do movimento entre −0,07 e 0,00 s do `t_audio` (4 vídeos); contra o `t_ini`, +0,10 a +0,23 s | rodadas 1011 e 1012 |
| gabarito de dedos (40 ataques) e padrões da direita (40 compassos) | do dono | `data/gold/maos/` |

**O que falta de verdade:**
- o braço **quadro a quadro**, achado só pela imagem;
- a ligação de cada nota ao seu trecho de mão com o tempo **do som**;
- o controle de qualidade da associação.

## 2. Princípios (o que impede a base de contaminar o modelo)

1. **O gabarito é só rótulo.** Nada do que vira **entrada** do modelo pode ser calculado com a
   tablatura ou a partitura. No dia do uso, o modelo vai receber um vídeo sem tablatura; a base
   precisa ter sido feita do mesmo jeito.
   - Exemplo: a calibração do braço pela música (rodadas 1006–1007) usa as notas da tablatura.
     Ela **não** pode ser a geometria gravada como entrada.
   - Ela **pode** ser usada para criar rótulos que ensinam o detector do braço, ou para validá-lo.
     O detector, depois de pronto, só olha a imagem.
2. **O tempo é o do som, não o do marcador.** O marcador da tela vem 165–275 ms antes do som e
   vagueia. Numa melodia em semicolcheias a 120 bpm, as notas ficam a 125 ms uma da outra. Com o
   tempo do marcador, o movimento gravado seria o da nota **anterior**. Sem `t_audio` confiável,
   a nota não entra no nível ouro.
3. **A tablatura some da imagem.** Para cada quadro, guardar a caixa do painel, para mascarar a
   tablatura no treino. Um recorte de mão não pode conter tablatura. Se contiver, o modelo
   aprende a ler a tablatura em vez das mãos.
4. **Guardar o cru e a confiança; decidir depois.** Mesmo princípio do "símbolo não se
   descarta":
   - pontos e scores do detector como saíram;
   - geometria com a confiança;
   - eventos recusados ficam na base, com o motivo.

   O filtro de qualidade é um **nível** gravado na amostra, não uma exclusão.
5. **Cada associação tem checagens independentes** (seção 3), e o resultado de cada uma fica
   gravado.
6. **A taxa de associação falsa é medida pelo dono, com número, antes de escalar** (M14).
7. **Divisão para o modelo futuro já na base**: por vídeo e por canal. Um canal inteiro fica de
   fora para o teste final.
8. **Reprodutível**: versão do detector, commit, parâmetros e semente por arquivo; duas
   execuções iguais (regra 1 do `AGENTS.md`).

## 3. A associação nota ↔ mãos e as checagens

**O evento** é uma nota do produto, com a chave de evento do `chorinho/video@1`: `(tela,
passagem, exibicao, coluna, corda, t_ini)`.

Para cada evento:

- `t_som` = `t_audio` da coluna (trilha do áudio);
- janela de quadros em torno de `t_som`. Proposta: de −0,5 a +0,5 s, todos os quadros nativos.
  A janela é grande para o modelo ver o **movimento**: a preparação e o ataque;
- índices dos quadros, no arquivo denso da seção 4.

**Checagens** (todas gravadas como verdadeiro/falso + número):

| | checagem | usa | o que pega |
| --- | --- | --- | --- |
| K1 | som: `t_audio` existe e a confiança do alinhador passa | trilha áudio | nota que não soou; marcador fora do som; o professor falando |
| K2 | mão esquerda: nota presa → alguma ponta perto da célula (corda, casa) no braço achado **pela imagem**, em pelo menos um quadro da janela | M11 + M12 | tempo errado; braço errado; capotraste; trecho tocado diferente da tela |
| K3 | mão direita: detectada, com pico de movimento perto de `t_som` | M12 | mão fora do quadro; associação a outro ataque |
| K4 | quadro limpo: sem corte de cena nem transição; caixa da tablatura conhecida; capotraste conhecido | M11 + tablatura | quadro de abertura; troca de câmera |

**Níveis:**
- **ouro**: K1 a K4 passam;
- **prata**: K1 e K3 passam, mas o braço não foi achado com confiança. O tempo está certo, e só
  a geometria da esquerda falta;
- **recusado**: falha em K1 ou K4, com o motivo.

**Cuidado com o viés de seleção.** As checagens usam o gabarito para **filtrar**, não para
calcular a entrada; isso é permitido. Mas filtrar só os casos fáceis ensina o modelo só com
casos fáceis (por exemplo, sem passagens rápidas). O relatório de cada lote mostra o que foi
recusado, por canal, casa, corda e andamento.

## 4. Formato (proposta M10)

Arquivos irmãos, sem mudar o `chorinho/video@1`. É o mesmo desenho das decisões 2003 (áudio) e
3002 (partitura).

- **`<video>.maos.json`** (`chorinho/maos@1`):
  - cabeçalho com o produto usado e o sha256 dele, o detector, o commit e os parâmetros;
  - por vídeo: lado do violonista (canhoto?) e capotraste (casa e fonte);
  - **eventos**: chave do evento, `t_som`, janela, checagens K1–K4, nível e motivo.
- **`<video>.maos.npz`** (denso, numpy, sem dependência nova). Por quadro amostrado:
  - PTS;
  - as duas mãos, com 21 pontos × (x, y, score), a origem (Wholebody ou MediaPipe) e um id de
    trilha estável entre quadros;
  - braço e antebraços do Wholebody;
  - geometria do braço: pestana, trastes visíveis e retas das cordas 1 e 6, com a confiança e
    um "não achou";
  - caixa da tablatura.
- **Recortes de imagem não são gravados.** Eles são refeitos do acervo pelo PTS, com
  `tab/comum/leitor.py` (44 % do acervo é AV1).
- **Custo estimado**, a medir no piloto: cerca de 0,5 kB por quadro em float16. A 15 quadros por
  segundo nas ~171 h de tablatura na tela, são ~9 M de quadros e ~4,5 GB.
- O áudio fica por referência ao FLAC do cache (rodada 2001), com o índice da amostra.

**Aceite do M10:**
- o dono aprova o formato;
- validador `tab/maos/esquema.py` com testes sintéticos no gate;
- decisão escrita.

## 5. As fases

### M10 — Esquema e regras (1 dia)

- Seção 4 vira decisão + validador + testes.
- Nada roda no acervo.

### M11 — Braço quadro a quadro (o coração; 1–2 semanas)

**Pergunta**: em cada quadro, onde estão a pestana, os trastes e as cordas, olhando **só a
imagem**? E o sistema sabe dizer "não achei"?

**Linha de base que tem de ser batida**: uma marcação só por vídeo, sem rastrear o movimento.
Ao longo do braço ela erra ≤ 0,16 casa; na direção das cordas, até 2,4 cordas.

**Caminhos, nesta ordem:**

- **M11a — rastrear a partir de um quadro de referência.**
  - Um quadro-chave por cena: no piloto, a marcação do dono; depois, automático (M11b).
  - Casamento de pontos (ORB ou AKAZE, que estão no cv2) e homografia por RANSAC, **dentro da
    região do braço**.
  - A grade dos trastes é refinada pelo modelo projetivo da rodada 1005.
  - Reinicia na troca de cena e diz "não achou" quando o casamento cai.
  - É determinístico e sem treino.
- **M11b — detector do braço aprendido** (só se o M11a não passar, ou para tirar o quadro-chave
  manual).
  - Rede pequena, no espírito do classificador de glifos, que acha pontos da pestana, dos
    trastes e das cordas.
  - Rótulos de treino automáticos, nos quadros em que o M11a e a calibração pela música
    concordam. Isso é permitido pelo princípio 1: a rede só vê a imagem.
  - Teste **só** no gabarito do dono.

**Gabarito:**
- os 36 quadros do dono, todos de **teste**;
- mais um **gabarito no tempo**, que falta: em 6 vídeos de canais diferentes, o dono marca o
  braço em 5 instantes espalhados. São 30 quadros, ~40 min na mesma ferramenta de q32–q36.
  Isso mede o rastreamento ao longo do vídeo, que é o que o dono apontou.

**Aceite (proposta):**
- nos quadros em que o sistema diz "achei":
  - trastes a < 1/4 de casa em ≥ 95 %;
  - cordas 1 e 6 a < 1/4 do vão entre cordas em ≥ 95 %;
- "achei" falso em ≤ 2 % dos quadros;
- cobertura ("achei") relatada por canal, com denominador;
- duas execuções idênticas.

**Pare se** o M11a ficar abaixo da linha de base na direção das cordas em algum vídeo do
gabarito no tempo. Olhe os quadros antes de mexer.

**Capotraste** (backlog da decisão 1003): a casa k da tablatura fica na casa N + k do braço. A
fonte é, nesta ordem: o texto na tela, o canal (`configs/canais.yaml`) e o capotraste visto na
imagem. Sem capotraste conhecido num vídeo que tem capotraste, a K2 falha (princípio 4).

### M12 — Mãos quadro a quadro (1 semana)

- O detector do M1 em todos os quadros da janela de cada evento, com trilha estável de cada
  mão. A troca esquerda/direita do MediaPipe já foi vista no M0.
- **Ponta do dedo ≠ ponto de contato.** O detector põe a ponta deslocada para a corda 6: ~1 vão
  no q16, ~0,3 no q02. Guardar a ponta crua; a correção, se houver, é um campo à parte e
  medido.
- Velocidade: rodar o detector no recorte em volta da mão do quadro anterior. Medir quanto
  acelera e se muda o resultado (o recorte é parte da medição, regra 9).

**Aceite (proposta):**
- esquerda/direita certas em ≥ 98 % numa amostra auditada;
- mão achada em ≥ 95 % dos eventos dos vídeos que "servem" no M0;
- quadros por segundo de GPU medidos; com a trava `gpu.lock.maos` e ≥ 3 GB livres.

### M13 — Tempo do som por nota (consumir, não fazer)

- Ler o `chorinho/audio@1` da trilha do áudio (decisão 2003).
- Se o vídeo não tiver arquivo de áudio, rodar o alinhador da trilha **sem editá-lo**, como na
  rodada 1012.

**Aceite:**
- cobertura de `t_audio` por vídeo, relatada;
- a precisão é da trilha do áudio: copiar o número e a fonte.

### M14 — Associação e controle de qualidade (1 semana + ~40 min do dono por lote)

- Montar os eventos da seção 3 nos 20 vídeos do piloto.
- **Auditoria do dono** (a medida da contaminação):
  - 100 eventos **ouro** sorteados, estratificados por vídeo;
  - cada um mostra os quadros da janela, com a célula (corda, casa) do gabarito desenhada sobre
    o braço achado, as pontas, e o momento do som marcado;
  - o dono responde "associação certa / errada / não dá para ver", um clique por evento, com
    autosave;
  - a ferramenta é testada numa cópia antes.

**Aceite (proposta):**
- ≤ 2 erradas em 100 eventos ouro. Com 100 eventos, 2 erros ainda deixam a taxa verdadeira
  possivelmente perto de 7 % (limite superior de 95 %); se o dono quiser margem menor, a amostra cresce;
- a fração ouro/prata/recusado relatada por vídeo, com os motivos;
- o viés de seleção relatado (seção 3).

**Pare se** houver > 5 erradas. Olhe quais checagens deixaram passar antes de qualquer
escala.

### M15 — Piloto e rollout (máquina + auditorias)

1. **Piloto**: 20 vídeos do sky guitar (100 % com mãos; tablatura validada lá).
   - Medir o tempo de GPU e de HD por hora de vídeo, e o espaço em disco.
   - Passar no M14.
2. **sky guitar inteiro** (416 vídeos), com uma auditoria de 100 eventos.
3. **Próximos canais**, na ordem em que a trilha da tablatura validar a leitura (fase 8) e com
   mãos visíveis no M0: leonardo ramos, kenneth acoustic, iwaki, shin izumi, guitar dell'arte…
   Uma auditoria de 100 eventos por canal novo, porque o enquadramento muda por canal.

**Custo grosseiro, a medir no piloto**: 0,2 s por quadro na GPU dá ~1 semana de GPU para o sky
guitar a 15 quadros por segundo. A GPU é compartilhada: rodar com a trava e fora do horário da
outra trilha.

### M16 — O modelo (depois da base; fora deste plano)

- Entrada: as mãos e o braço quadro a quadro, e o som. A tablatura é mascarada.
- Saída: corda e casa por nota, ou a partitura.
- Teste final num **canal inteiro fora do treino**, contra a linha de base do decodificador só
  pelas notas (D1 do M8: 88 % da corda do professor).
- Antes de treinar, a base precisa passar no M14 em pelo menos 2 canais.

## 6. O que o dono precisa fazer

| quando | o quê | tempo |
| --- | --- | --- |
| agora | aprovar este plano e os critérios "proposta" (ou mudar) | — |
| M10 | aprovar o formato | 10 min |
| M11 | marcar o braço em 30 quadros (6 vídeos × 5 instantes) | ~40 min |
| M14 / M15 | auditar 100 eventos por lote (piloto, sky guitar, cada canal novo) | ~30–40 min cada |

## 7. Riscos e como perceber cedo

- **O braço não se deixa rastrear em algum canal** (câmera na mão, close que corta a
  pestana, zoom). Aparece como cobertura baixa no M11. O evento fica prata, e nunca com uma
  geometria inventada.
- **A tablatura da tela diferente do que é tocado** (versão lenta, repetição, o professor
  improvisando). Pega na K1 (som sem ataque na altura esperada) e na K2. Relatar quantos.
- **Canhoto, capotraste, violão de 7 cordas.** São campos por vídeo. Na dúvida, o vídeo fica
  recusado com o motivo, e nunca forçado para o padrão.
- **A GPU** é uma só, de 8 GB, e compartilhada. O tempo é medido no piloto antes de prometer
  prazo.
- **O modelo futuro pode não conseguir ler a corda pelas mãos** num vídeo sem tablatura. As
  ondas mostraram que o sinal é fraco com regras simples. A base é o que permite descobrir; ela
  não garante o resultado.

## 8. O que não fazer

- Calcular entrada com o gabarito (princípio 1).
- Associar mão a nota pelo `t_ini` do marcador (princípio 2).
- Tirar uma conclusão de "o braço funciona" com um quadro por vídeo: o braço se mexe.
- Clicar no gabarito ao vivo para testar ferramenta: testar numa cópia.
- Reabrir as ondas de regra para adivinhar a corda pela mão (rodadas 1013–1014 e 1101–1170).

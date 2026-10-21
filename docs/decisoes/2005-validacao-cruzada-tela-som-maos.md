# 2005 — Validação cruzada da nota: tela, som e mãos (triangulação)

**Data**: 2026-10-21. **Estado**: proposta da trilha áudio, a pedido do dono. Ela afeta as
trilhas mãos e tablatura, que não são editadas aqui: o dono é a ponte, e cada trilha decide o
que muda nos seus arquivos.

## Contexto

O pedido do dono, em 2026-10-21, tinha três partes:
1. um **transcritor que ouve sozinho**, sem ver a tela: todas as notas do violão, com o
   instante de cada uma, e só no fim o cruzamento com a tablatura;
2. uma **dependência da trilha mãos**: se as mãos disserem, por quadro, em que corda e casa a
   esquerda pressiona e que corda a direita ataca, com porcentagem e margem de erro, o som
   ganha o que lhe falta, que é saber **qual corda**;
3. usar as trilhas para **validar de forma cruzada** o dataset e o resultado de cada uma.

O que já existe:
- **A decisão [0011](0011-tablatura-vira-rotulo-da-base.md) vale**: o rótulo da base vem só da
  tela, e o som e as mãos conferem.
- **Cada fonte erra de um jeito diferente** (medido):
  - a tela: o leitor `rede` lê "2·3" como 23 e perde "10" na corda 1 (rodada 2017, pedidos 13 e
    14 da [2004](2004-pedidos-de-leitura-a-trilha-tablatura.md));
  - o som: a mesma altura sai de 2 ou 3 cordas, acorde denso perde nota, voz e metrônomo
    atrapalham;
  - as mãos: casa e corda vizinha, dedo escondido, troca de câmera (rodadas 1009 e 1022).
- **Hoje há duas ligações que tiram a independência:**
  - o alinhador do som (`tab/audio_alinhar.py`) parte das notas da tela: um erro de leitura vira
    falha do som;
  - as mãos acham o quadro de cada nota **pelo tempo do som** (`plano-dataset-maos.md`, seção 3 e
    M13: janela em volta de `t_som`). Um tempo errado do som leva a mão errada, e as duas fontes
    concordam no erro.
- **A quarta fonte**: a trilha partitura dá a altura de cada nota por outro caminho (decisão
  3002).

## Opções

1. **Seguir como está**: cada trilha confere a tela sozinha, e o som dá o tempo às mãos.
   - Contra: as fontes não são independentes, e "concordou" não diz quanto vale.
2. **Fundir tudo num modelo só**, que lê tela, som e mãos juntos.
   - Contra: perde a conferência. Não há como saber qual fonte errou, e o rótulo da 0011 vira
     saída do modelo.
3. **Triangulação**: cada fonte calcula sozinha a sua versão da nota, e uma etapa final só
   compara. A fusão, se houver, é uma saída **a mais**, nunca no lugar das separadas.

## Decisão (proposta)

**Opção 3**, com quatro regras.

### Regra 1 — independência

Nenhuma fonte usa a saída de outra para se calcular. As exceções permitidas são **dados de
contexto**, e não respostas:
- a janela de tempo da página (`telas[].exibicoes[].t0/t1`), que vem da imagem;
- a casa do capo por vídeo, desde que a sua fonte fique registrada.

O que muda:
- **Som**: o transcritor livre (rodada 2018) não recebe a tablatura. O alinhador atual fica,
  mas a saída dele não conta como fonte independente da tela.
- **Mãos** (pedido à trilha mãos): uma versão da saída por quadro que **não use o `t_audio`**.
  - A janela de quadros vem da página, e não do som.
  - O instante de ataque vem da própria mão direita (pico de movimento).
  - A janela em volta do `t_som` pode continuar para a base de treino. Ela só não conta como
    conferência independente.

### Regra 2 — o que cada fonte entrega

Cada fonte grava em arquivo irmão, no mesmo desenho das decisões 2003, 3002 e 1007.

| fonte | entrega por nota ou por quadro | incerteza |
| --- | --- | --- |
| tela (`chorinho/video@1`) | corda, casa, coluna, `t_ini` do marcador quando há | `confianca` da leitura |
| som, transcritor livre (**novo**, proposta `chorinho/som@1`) | notas ouvidas: início, fim, altura em semitons, sem corda | probabilidade por nota |
| som, alinhador (`chorinho/audio@1`, já existe) | `t_audio` por coluna da tela | `confianca`, recusa e motivo |
| mãos (**pedido**, campos novos sobre o `.maos.npz`) | por quadro: esquerda, cada (corda, casa) com a probabilidade de estar pressionada; direita, cada corda com a probabilidade de ter sido atacada | probabilidade calibrada, e "não achou" (mão escondida, braço não achado) |
| partitura (decisão 3002) | altura por nota da pauta | a da leitura |

- **Sobre as mãos**: o `.maos.npz` do M10 guarda pontos crus e a geometria do braço. O pedido é
  uma camada derivada (a ponta do dedo vira célula de corda e casa), com probabilidade, para o
  cruzamento não ter de refazer a geometria.
- **Probabilidade calibrada** quer dizer: das células que a fonte dá a 80 %, cerca de 80 % estão
  certas no gabarito do dono. Sem calibração, a porcentagem não pode ser somada à das outras
  fontes.

### Regra 3 — o cruzamento

Uma etapa final lê as fontes e grava, **por nota da tela**:
- o que cada fonte disse, ou "sem dado";
- o **nível de concordância**:
  - **3/3** (tela, som e mãos dizem a mesma nota);
  - **2/3**, dizendo **qual fonte discorda**;
  - **1/3**;
  - **sem dado suficiente**.
- A física é o elo: corda solta + casa + capo tem de dar a altura ouvida. Uma discordância
  sistemática de N semitons em todo o vídeo aponta o capo, e não as notas.
- Discordância de 2 contra 1 vira **alarme para a trilha dona da fonte**: a leitura da tela, o
  transcritor ou as mãos.
- As notas ouvidas pelo som sem nenhuma nota na tela também saem (ornamento, nota que a leitura
  perdeu, ruído), como lista à parte.
- Uma **fusão** (a nota mais provável, juntando as fontes) pode sair como campo a mais. Ela
  nunca substitui o rótulo da 0011, nem entra como fonte de outra checagem.

Proposta: o cruzamento fica num módulo neutro (`tab/cruzar_fontes.py`), que só lê os arquivos
irmãos. Quem o escreve é decisão do dono; a trilha áudio pode escrevê-lo.

### Regra 4 — calibração pelo dono

A concordância só vira número confiável com uma amostra que o dono confere.
- Os gabaritos de tablatura que existem (`data/gold/ouro_video/`: 63 telas conferidas, 2.687
  notas em 8 vídeos) já calibram a parte tela × som.
- Para as mãos, vale o gabarito do braço e das mãos da trilha mãos.
- Medidas, por nível de concordância e por canal: quantas notas, e quantas o gabarito confirma.
  Exemplo do que se quer poder dizer: "3/3 acerta X % (n de N)".
- Os erros **não são independentes**: passagem rápida, acorde cheio e vídeo ruim atrapalham as
  três fontes. Por isso a medida é feita, e não calculada por produto de probabilidades.

## Consequências

- **Trilha áudio**:
  - a rodada 2018 passa a ser o transcritor livre, medido nos gabaritos de tablatura
    (altura e instante);
  - o formato `chorinho/som@1` vira decisão própria quando o transcritor passar;
  - a casa do capo pelo som segue (frente B), agora também pela discordância sistemática;
  - a conferência nota a nota (frente C) vira a parte tela × som do cruzamento.
- **Trilha mãos** (pedido, via dono):
  1. a camada por quadro de (corda, casa) pressionada e corda atacada, com probabilidade
     calibrada e "não achou";
  2. uma saída que não dependa do `t_audio` (Regra 1);
  3. a margem de erro medida no gabarito dela.
  - **Isso não muda a ordem M11–M16**: o pedido entra quando M11 e M12 existirem.
- **Trilha tablatura**: nada novo, além dos alarmes de leitura, que já chegam pela 2004.
- **Base das mãos** (decisão 1007): o nível de concordância pode virar um campo do evento,
  ao lado de ouro/prata. A 1007 não é editada aqui.
- **Limite**: a triangulação não valida o que nenhuma fonte vê, como técnica fina e dedilhado,
  nem as notas que só uma fonte cobre (mão fora do quadro, som abafado). Essas ficam marcadas
  "sem dado suficiente", e não "certas".

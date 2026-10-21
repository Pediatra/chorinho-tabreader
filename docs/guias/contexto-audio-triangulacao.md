# Trilha áudio: o que foi combinado com o dono (2026-10-20/21)

> Resumo da conversa entre o dono e a trilha áudio, depois da retomada
> ([`contexto-audio-retomada.md`](contexto-audio-retomada.md)). Serve ao dono e às próximas
> sessões da trilha.

## 1. O objetivo e a função da trilha

- **O projeto**: uma base em que cada nota tocada tem, juntos:
  - o rótulo: corda, casa e técnica, que vêm da tablatura da tela (decisão 0011);
  - o som;
  - o braço;
  - as duas mãos, quadro a quadro.
  Com ela se treina, no futuro, um modelo que recebe só vídeo e som e devolve tablatura e
  partitura.
- **A trilha áudio** dá, para cada nota, **quando ela soou** (`t_audio`, que a trilha mãos usa
  para achar o quadro) e **se soou certo**. Ela não cria rótulo: confere.

## 2. O que foi feito

**Rodada 2017**: regressão do alinhador com o leitor `rede` da tablatura.
- O alinhador **não piorou**: nas colunas que existem nos dois produtos, 97,2 % mantêm o tempo
  a ≤ 30 ms.
- Colunas com tempo nos 14 vídeos bons: 0,831 → 0,858.
- Gabarito de escuta do dono: 37 de 40 pontos certos mantidos.
- Duas pioras, causadas pela leitura da tela e vistas no quadro (imagens
  `data/saida/audio/r2017/quadros/ver_bach.png` e `ver_room335.png`):
  - o leitor `rede` lê "2·3" como **23** (kimny *bach prelude*);
  - o leitor `rede` perde o "10" da corda 1 e lê ornamento como nota (shin izumi *room 335*).
  - São os pedidos 13 e 14 da decisão 2004, para o dono repassar à trilha tablatura.
- 8 vídeos extras: alarmes de leitura 23 → 14. O *sakura* tem capo na casa 3 e segue com 0
  colunas com tempo; isso fica para a rodada do capo.

**Conserto**: `colunas_abafadas` conta o X de classe `"x"` do leitor `rede` (commit
`d0d0c45c`). Os JSONs antigos não mudam.

## 3. O que o dono pediu, e como fica

1. **Um transcritor que ouve sozinho.** Ele lista todas as notas do violão, com o instante,
   **sem ver a tela**, inclusive os acordes. Só no fim as notas ouvidas são cruzadas com a
   tablatura.
   - Isso substitui, como fonte principal, o alinhador atual, que parte das notas da tela e por
     isso sofre com cada erro de leitura.
   - Candidatos levantados (nada foi baixado):
     - **Basic Pitch** (Spotify): Apache 2.0, pequeno. Roda em Python ≤ 3.11, então precisa de
       imagem própria;
     - **MuScriptor** (Kyutai/IRCAM, 2026): pesos CC BY-NC (não comercial), de 103 M a 1,4 B de
       parâmetros, e pede login no Hugging Face;
     - os modelos de violão com melhor número publicado (Riley et al., GAPS) **não liberaram os
       pesos**.
   - **Baixar precisa de aprovação do dono**, com nome, versão, tamanho, licença e fonte.
2. **Usar os gabaritos de tablatura** (`data/gold/ouro_video/`: 63 telas conferidas, 2.687 notas,
   8 vídeos) como **folha de respostas**.
   - Com as notas que o dono conferiu, o erro que sobra é do som, e não da leitura.
   - O *end of beginning* (kenneth) tem capo na casa 2 e gabarito: é o controle positivo do capo.
3. **Dependência das mãos.** Se as mãos disserem, por quadro, em que corda e casa a esquerda
   pressiona e que corda a direita ataca, com probabilidade, o som ganha o que lhe falta, que é
   **qual corda**. Combinados, os dois chegam perto das notas de fato tocadas.
4. **Validação cruzada (triangulação)** com tela, som e mãos, mais a partitura como quarta fonte.
   - As três concordam: a nota é muito provavelmente certa.
   - Duas contra uma: aponta qual fonte errou. Exemplo: o "23" da tela contra "2 e 3" do som e
     das mãos.
   - O que só uma fonte cobre fica "sem dado suficiente".
   - Detalhes e regras na decisão [2005](../decisoes/2005-validacao-cruzada-tela-som-maos.md).

## 4. As regras da triangulação (resumo da 2005)

- **Independência**: nenhuma fonte usa a resposta de outra.
  - Hoje as mãos acham o quadro **pelo tempo do som**. Para conferir, elas precisam do próprio
    tempo, a mão direita (pedido à trilha mãos).
  - O alinhador atual parte da tela. O transcritor livre não parte.
- **Probabilidade calibrada** em cada fonte, medida no gabarito.
- **Um cruzamento só no fim**, que grava o nível de concordância por nota e manda alarmes à
  trilha dona da fonte que discorda.
- **Calibração com uma amostra conferida pelo dono.** Os erros das fontes não são independentes
  (passagem rápida, acorde cheio), então o valor de "3/3" é medido.

## 5. Próximos passos da trilha áudio

1. **Rodada 2018 — transcritor livre**:
   - pré-registro;
   - pedido de aprovação do download ao dono;
   - medida nos gabaritos de tablatura: notas certas, notas a mais e a menos, instante;
   - pelo menos um caso com acorde cheio.
2. **Casa do capo**: pela discordância sistemática som × tela, contra
   `data/saida/maos/capo_por_video.json`. O *sakura* (casa 3) e o *end of beginning* (casa 2)
   são casos dela.
3. **Cruzamento tela × som**, a primeira perna da triangulação, enquanto as mãos ainda não
   entregam corda e casa por quadro.

## 6. Pendências com o dono

- Repassar à trilha tablatura os pedidos 13 e 14 da decisão 2004.
- Repassar à trilha mãos o pedido da decisão 2005: camada de corda e casa por quadro, com
  probabilidade, e uma saída que não dependa do `t_audio`.
- Aprovar (ou não) o download do transcritor quando o pedido chegar.
- Decidir quem escreve o módulo de cruzamento (proposta: a trilha áudio, num módulo neutro).

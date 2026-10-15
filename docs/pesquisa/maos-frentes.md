# Frentes de teste da pesquisa das mãos

**Data**: 2026-10-15. **Base**: [`maos.md`](maos.md), a revisão de literatura que o dono trouxe
(feita com o Gemini). **Autor**: trilha das mãos, sessão principal, que também revisa o que as
frentes entregarem. **Para quem**: agentes que vão testar as ideias em worktrees separadas.

> **Leia antes de começar**: `AGENTS.md`; `docs/guias/contexto-maos.md` (seções 6 e 7); este
> documento inteiro; a parte de `maos.md` citada na sua frente; as rodadas
> `docs/rodadas/1010` a `1013` e as decisões `docs/decisoes/1004` e `1005`.

**Sumário**

1. Objetivo
2. Onde estamos (o que já foi medido)
3. Triagem da pesquisa: o que serve, o que já temos, o que fica fora
4. Ordem dos testes
5. Régua comum (vale para todas as frentes)
6. Regras para quem trabalha numa worktree
7. As frentes: Frente 0 e Frentes A a E
8. Pegadinhas que valem para todas as frentes
9. O que cada frente entrega
10. Perguntas para o dono (nenhuma bloqueia o começo)

---

## 1. Objetivo

### 1.1 Do projeto

O produto é um JSON por vídeo com **corda, casa, coluna, compasso, técnica e tempo** de cada
nota. O alvo final é um dataset para um modelo futuro que vá do vídeo de alguém tocando à
tablatura e à partitura.

O dono decidiu o papel das mãos na [decisão 1005](../decisoes/1005-mao-direita-serve-a-corda.md):
elas servem para dizer **qual corda soou e quando**. Isso dá precisão à análise da mão esquerda
e do áudio e gera uma tablatura fiel. O dedilhado (p-i-m-a) ficou guardado para um algoritmo
futuro.

### 1.2 Da pesquisa

A revisão cobre três blocos:

- **áudio**: corda pela inarmonicidade, técnica expressiva;
- **decodificação**: escolher corda, casa e dedo por custo biomecânico e Viterbi;
- **visão e fusão**: braço, mão e a combinação com o áudio.

### 1.3 Deste documento

Este documento responde, com medida, a uma pergunta só: **quais ideias da pesquisa diminuem o
número de notas com a corda errada, além do que o M8 já faz?**

O problema é este:

- **A altura não basta.** Pela altura sozinha, 2.280 das 2.437 notas dos 4 vídeos de trabalho
  (93,6 %) têm mais de uma corda possível (rodada 1013).
- **Uma regra simples já resolve muito.** O decodificador sem câmera do M8 (D1) acerta 88,3 % das
  notas e deixa **285 erros**, todos em nota presa.
- **O alvo é a sobra:** as notas que continuam erradas depois da melhor regra que já temos.

**A tablatura da tela é o gabarito grátis** (a corda certa de cada nota), não a entrada.

- Só há uma exceção declarada: a **altura** da nota vem da tablatura. Isso simula um áudio
  perfeito, como no M8.
- Qualquer outra informação tirada da tablatura e usada como entrada é **vazamento**. A seção 8
  lista os caminhos de vazamento já conhecidos.

---

## 2. Onde estamos (o que já foi medido)

| o quê | número | fonte |
| --- | --- | --- |
| notas com mais de uma corda possível pela altura | 2.280/2.437 (93,6 %) | rodada 1013 |
| "casa mais baixa" nas ambíguas | 85,0 % (88 % numa amostra de 120 ataques da 1012) | 1013 |
| visão da mão direita nos empates (M7) | 48–59 %, perde para a regra trivial; **pausada** | 1011, 1012 |
| instante do som | o marcador vem antes do som: 139 ms no MVP; 165–275 ms (medianas) nos 4 vídeos | 2002, 1012 |
| alinhador do áudio (`tab.audio_alinhar`) | 591/636 colunas a ≤ 50 ms do ataque, no MVP | 2004 |
| braço pelo gabarito do dono | 20 quadros, 8 canais; regra das 12 notas, projetiva: 96 % de 327 trastes a < 1/4 de casa | 1005 |
| braço calibrado pela música | **vaza a corda**: proibido como entrada para decidir corda | 1006–1008 |
| braço pela imagem (pente, LSD, Hough) | reprovado 3 vezes: pega a borda do braço ou o outro painel | 1005, 1009, 1012 |
| dedo da mão esquerda (MVP, um vídeo) | 42/53 | 1007 |
| regra do dedo da mão direita (M5) | 172/216 fora da amostra (**guardada**) | 1010 |
| **M8**: corda sem a mão direita, degraus D0–D3 | tabela abaixo | rodada 1013, `tab/maos_corda_sem_direita.py` |

**O M8 é a referência de todas as frentes.** A tabela tem quatro degraus. Acurácia de corda com
os pesos a priori (α = 1, β = 3, γ = 5, δ = 0,5):

| degrau | o que usa | todas (2.437) | ambíguas (2.280) | erros |
| --- | --- | --- | --- | --- |
| D0 | casa mais baixa | 0,860 | 0,850 | 341 |
| D1 | decodificador com polifonia e continuidade, sem câmera | **0,883** | **0,875** | **285** |
| D2 | D1 + janela da mão esquerda pela câmera, só com o gabarito do braço | 0,883 | 0,875 | 285 |
| D3 | D1 + janela das casas das notas vizinhas (± 2): "câmera perfeita" otimista | 0,912 | 0,906 | 214 |

O que esses números dizem para as frentes:

- **Corda solta: 690/690 em todos os degraus.** Todo erro está em nota presa.
- **Por vídeo** (D1): retrato 50 erros, noturno **129**, lacrimosa 60, glimpse 46. O noturno
  carrega quase metade.
- **O D2 não ganha nada por cobertura.** A câmera casa com o quadro do gabarito em só **6,5 %**
  dos ataques com nota presa (96/1.470): a mão dentro do modelo derruba o NCC, e a câmera muda de
  plano. Onde a janela existe, ela contém a casa certa (93–100 %), mas tem 4,3–5,8 casas de
  largura e não desempata.
- **Mesmo com a posição "perfeita" (D3),** 130 notas erram com a casa certa dentro da janela
  (ambiguidade dentro da região da mão) e 66 erram pela posição.
- **Deixando um vídeo de fora:** D1 0,888, D2 0,891, D3 0,915.

---

## 3. Triagem da pesquisa: o que serve, o que já temos, o que fica fora

Critério: a ideia serve se pode diminuir as notas com corda errada **nos nossos vídeos**, com os
dados e as dependências que já temos. Isso quer dizer YouTube, áudio Opus e violão de nylon,
quase sempre no `sky guitar`.

### 3.1 Testar

| ideia (seção de `maos.md`) | frente | por quê |
| --- | --- | --- |
| transições de Hori e Sagayama: Laplace no salto de posição em função de dt, 1/(1+\|Δcorda\|) (§4.2) | A1 | troca o custo δ·\|Δposição\| do M8 por um modelo com tempo; barato |
| Minimax e L_p-Viterbi (§4.2, §7) | A2 | barato; expectativa baixa (seção 7, A2) |
| custo aprendido da tablatura, no espírito do *Path Difference Learning* (§4.1) | A3 | temos milhares de notas com a corda certa grátis; é a aposta mais forte sem sinal novo |
| folga de 10 % do vão do traste em volta das pontas dos dedos (§6.1, baixo) | B1 | mede e melhora a janela da mão esquerda do D2 |
| ocupação de pele por célula corda × casa (§6.1, Paleari) | B2 | alternativa quando a ponta do detector falha; só se a B1 mostrar esse problema |
| rastreio do braço ao longo do vídeo, com restrição de colinearidade e de modelo 12-TET (§5.1, Paleari) | B3 | o gabarito do braço tem **1 quadro por vídeo**; a câmera muda |
| detector de linha de Steger, que distingue barra (corda) de degrau (borda) (§5.2) | B4 | nosso erro foi pegar a borda do braço, não falta de precisão sub-pixel; só depois da B3 |
| inarmonicidade β(s, n) = β(s, 0) · 2^(n/6) (§2, Barbancho) | C1, C2 | física certa; viabilidade em Opus, nylon e reverberação **desconhecida**; teste de ir ou não ir |
| filtro de plausibilidade: ligado e slide na mesma corda (§2) | D1 | restrição dura e barata no decodificador |

### 3.2 Já temos (não refazer)

| ideia | onde já está |
| --- | --- |
| O = {64, 59, 55, 50, 45, 40}, n = O[s] + f | M8 (`AFINACAO_MIDI`) |
| caminho ótimo de Sayegh por programação dinâmica / Viterbi | M8 (D1) |
| no máximo uma nota por corda; abertura máxima das casas presas | M8 (polifonia; γ acima de 4 casas) |
| custo estático do acorde mais custo de transição (§4.1) | M8 (custo do ataque + δ) |
| trastes pela regra de 12 notas a partir de poucas referências (§5.1) | M3b, projetiva 1D (rodada 1005) |
| MediaPipe Hand Landmarks | M1: RTMW como base, MediaPipe como complemento (decisão 1002) |
| ataque do áudio como âncora da sincronia (§6.1) | `tab.audio_alinhar`, saída nos 4 vídeos em `data/saida/maos/m7/audio/` |

### 3.3 Fora agora (com o motivo)

| ideia | motivo |
| --- | --- |
| TART inteiro (transcritor de piano + Transformer) | exige treino e um transcritor que não temos; a parte útil (técnica como classe própria) está na frente D |
| *probabilistic fretboard* treinado no DadaGP; LSTM, Bi-LSTM, Transformer, ShredGP | corpus externo (dependência e licença: perguntar ao dono) e treino. Só faz sentido se o custo aprendido da A3 saturar |
| HandSkeletonNet / PianoVAM | piano e treino com muitos rótulos. É o tipo de modelo que o dataset deste projeto vai alimentar **no futuro**. Ideias aproveitadas: "piso de peso" na fusão (C2) e divisão sem repetir composição entre partes (seção 5) |
| Burns e Wanderley (câmera na cabeça do violão) | outro tipo de gravação |
| marcas circulares do braço + 12-TET (§5.1, baixo) | violão clássico quase nunca tem marcas na escala; a projetiva pelo gabarito do dono já dá 96 % |
| Canny + Hough para o braço | reprovado aqui (1005, 1011); "não repetir" no `ESTADO.md` |
| zonas ergonômicas de Heijink (V–XII "ótimas", §3) como regra | **contraria o dado**: "casa mais baixa" acerta 88 %. Se entrar, entra como atributo aprendido na A3, nunca imposto |
| dedilhado das duas mãos: Yepes, mudança com dedos 1 e 2 (§3.1); dedo de Hori e Sagayama | guardado pela decisão 1005; ver frente E |
| vibrato e *dead notes* (§2) | não detectamos nenhum dos dois hoje |
| transposição de oitava por fluxo, RA, Blender, otimizar capotraste ou afinação (§7) | não é o nosso problema: transcrevemos o que já foi tocado |
| *Playing / Non-Playing* pela mão do arco (§6.1, Dinesh) | equivale à mão direita, que está pausada; a frente D usa o áudio para "tem ataque?" |

**Números da literatura não são meta.** A revisão não traz a lista de referências: os
`[cite: N]` estão soltos. Os números (98,5 % de onset, 89 % do Paleari, 0 % de falso positivo)
foram medidos em outras condições: webcam 640 × 480, nota isolada, estúdio. Não use nenhum deles
como critério de aceite nem como argumento de que "deve funcionar".

---

## 4. Ordem dos testes

O M8 está no `main` (rodada 1013). Crie as worktrees **a partir do commit do M8 ou depois
dele**: todas as frentes importam o decodificador de `tab/maos_corda_sem_direita.py`.

| ordem | teste | frente | depende de | custo |
| --- | --- | --- | --- | --- |
| 1 | anatomia do resíduo do M8 (285 erros do D1, 214 do D3) | 0 | M8 | baixo (CPU, sem vídeo) |
| 2 | custo aprendido da tablatura | A3 | M8 | baixo |
| 3 | rastreio do braço ao longo do vídeo, com a mão mascarada | B3 | M8; quadros novos marcados pelo dono para validar | médio |
| 4 | janela por dedo, mais estreita que a da mão | B1 | M8 (cobertura com limiares mais baixos); B3 para cobertura real | baixo |
| 5 | separabilidade da corda pela inarmonicidade | C1 | nada | médio (áudio, CPU) |
| 6 | ligado = mesma corda | D1 | M8 | baixo |
| 7 | transições de Hori e Sagayama; Minimax / L_p | A1, A2 | M8 | baixo |
| 8 | áudio dentro do decodificador | C2 | C1 aprovada | médio |
| 9 | ocupação de pele | B2 | só se a B1 mostrar falha da ponta | médio |
| 10 | Steger | B4 | só se a B3 precisar de linha por quadro | médio |
| — | dedilhado | E | autorização do dono | **guardada** |

As frentes podem rodar em paralelo, cada uma na sua worktree. A ordem acima é de **prioridade**
(qual resultado muda mais o plano), não de espera. Só a C2 espera a C1, e só a B2 e a B4 esperam
as outras da frente B.

**Por que esta ordem.**

1. **Frente 0.** Diz **onde** estão os 285 erros: em acorde ou em nota solta, na troca de
   posição, entre corda encapada e lisa, ou em ligado. Isso diz quais frentes têm o que ganhar.
2. **A3.** É a mais barata das que podem ganhar muito, porque não precisa de sinal novo.
3. **B3 antes da B1.** O M8 mostrou que o gargalo da câmera é **cobertura** (6,5 %), não
   qualidade. Sem rastreio do braço, qualquer janela melhor vale para poucos ataques.
4. **Os 130 erros do D3.** São ambiguidade **dentro** da região da mão. Só uma janela mais
   estreita (B1), o timbre (C) ou a mão direita resolvem esses.

**Revisão da ordem.** A Frente 0 pode mudar a ordem. Se, por exemplo, menos de 10 % do resíduo
atravessar a fronteira entre corda encapada e lisa, a C3 perde o sentido (seção 7, Frente C).

---

## 5. Régua comum (vale para todas as frentes)

### 5.1 Dados

**Os 4 vídeos de trabalho** são do `sky guitar`. A lista está em `VIDEOS`, em
`tab/maos_padroes_preparar.py`:

| vídeo | produto (tablatura lida) | pontas da mão esquerda | quadro do gabarito do braço |
| --- | --- | --- | --- |
| retrato brasileiro (MVP) | `data/saida/produto/mvp.json` | `data/saida/maos/m3c/pontas_mvp.json` | q02 |
| (chopin) nocturne no.20 | `data/saida/maos/m3d/q16_chopin_nocturne20.json` | `data/saida/maos/m3d/pontas_q16.json` | q16 |
| lacrimosa | `data/saida/maos/m3d/sky_4.json` | `data/saida/maos/m3d/pontas_q21.json` | q21 |
| glimpse of us | `data/saida/maos/m3d/sky_8.json` | `data/saida/maos/m3d/pontas_q23.json` | q23 |

- **"qNN"** é a posição, contada a partir de 1, do quadro na lista `quadros` de
  `data/gold/maos/braco.json`.
- **Instante do som**: `data/saida/maos/m7/audio/alinhado_<slug>.json` e `ataques_audio.json`,
  gerados pelo alinhador da trilha do áudio.
- **Notas com `t_ini`**: 753, 576, 453 e 655, num total de 2.437.

**Mais tablatura, só para as frentes que não precisam de imagem (A e D):**

- `data/saida/maos/m3d/sky_1.json` a `sky_8.json`: 8 produtos do `sky guitar`.
  - **`sky_4` e `sky_8` são vídeos de teste**: nunca entram no treino quando forem testados.
  - `sky_7` (no surprises) também tem quadro no gabarito do braço (q22, instável na 1008).
- `data/gold/ouro_video/*.json`: tablatura conferida pelo dono em 9 vídeos de 7 canais. Esses
  arquivos são da trilha tablatura: **só leitura**.
- Nessa avaliação só de tablatura, o ataque é (tela, coluna) e a sequência é a ordem da página.
  O `dt` entre ataques só existe onde há `t_ini`.

### 5.2 Gabarito, unidade e métricas

- **Gabarito**: a corda da nota no produto (ou no ouro do dono, onde existir).
- **Unidade**:
  - **nota** (para acurácia);
  - **ataque** (notas com o mesmo `t_ini` a 0,02 s, ou a mesma coluna);
  - **(tela, coluna) distinta** (para descontar as exibições repetidas da mesma página).
- **Nota ambígua**: tem 2 ou mais cordas possíveis para a sua altura, com casa de 0 a 19. É a
  mesma definição do M8.
- **Métricas obrigatórias**, por vídeo e no total, sempre com denominador:
  1. acurácia da corda em todas as notas;
  2. acurácia nas ambíguas;
  3. acurácia separada em notas presas e cordas soltas, pela corda **verdadeira**;
  4. **consertadas e quebradas** contra a referência: notas que a referência errava e a frente
     acerta, e o contrário;
  5. o mesmo número contado por (tela, coluna) distinta.
- **Referência de cada frente**: o degrau do M8 que usa as mesmas entradas.
  - A e D comparam com o D1.
  - B compara com o D2 (e com o D1).
  - C compara com o D1 (sem câmera) e com o D2 (com câmera).

### 5.3 Critérios de aceite comuns (CA)

Uma variante só é "aprovada" se cumprir **todos**:

- **CA1 — reprodução.** Antes de mexer em qualquer coisa, a worktree reproduz **exatamente** os
  números do D0 e do D1 do M8 (mesmas notas, mesmos denominadores). Se não bater, pare e
  relate.
- **CA2 — ganho.** Nas notas ambíguas, somando os 4 vídeos:
  - ganho líquido de **≥ +1,0 ponto percentual** sobre a referência;
  - **consertadas − quebradas ≥ 20 notas**.
- **CA3 — sem um vídeo carregando o resultado.** Ganho em **pelo menos 3 dos 4** vídeos, e
  nenhum vídeo piora mais de 0,5 ponto percentual.
- **CA4 — fora da amostra.**
  - Todo peso ou limiar ajustado é escolhido **deixando o vídeo de teste de fora**: escolhe-se
    em 3 vídeos e mede-se no 4º, girando.
  - Os pesos a priori são declarados no documento da rodada **antes** da medida.
  - A calibração dentro de um vídeo (frente C) divide por **blocos de tempo ou por exibição**,
    nunca por nota sorteada (seção 8, item 5).
- **CA5 — determinismo.** Duas execuções dão resultado idêntico. Se houver sorteio: 3
  sementes, média e amplitude, e o ganho tem de ser maior que a amplitude.
- **CA6 — olhar o caso.**
  - 10 notas olhadas no quadro (5 consertadas e 5 quebradas), com recorte anexado (caminho do
    arquivo).
  - Afirmação sobre imagem sem o caminho da imagem não vale.
- **CA7 — gate.** `ruff check`, `ruff format --check` e `pytest` verdes **na worktree**.

---

## 6. Regras para quem trabalha numa worktree

### 6.1 A armadilha principal: a pasta `data/saida/` não está no git

Uma worktree nova tem o código e o `data/gold/`, mas **não tem** os produtos, as pontas, o
áudio alinhado nem nada de `data/saida/`. O container precisa montar a `data/saida/` da cópia
principal **só para leitura**, e só a pasta da sua frente para escrita:

```bash
WT=/caminho/da/sua/worktree
PRINCIPAL=/var/home/gabriel/Projects/chorinho-dataset
FRENTE=fb_esquerda   # f0_residuo | fa_decodificador | fb_esquerda | fc_audio | fd_ligados
host-spawn -no-pty -cwd "$WT" podman run --rm --security-opt label=disable \
  -v "$WT":/app \
  -v "$PRINCIPAL/data/saida":/app/data/saida:ro \
  -v "$PRINCIPAL/data/saida/maos/frentes/$FRENTE":/app/data/saida/maos/frentes/$FRENTE \
  -v /run/media/gabriel/3014CD4714CD1130/chorinho:/acervo:ro \
  -v /run/media/gabriel/3014CD4714CD1130/chorinho_cache:/cache:ro \
  -w /app docker.io/library/chorinho:dev bash -c "<comando>"
```

- **Onde a sessão roda.** Se ela roda direto no host, sem distrobox, tire o
  `host-spawn -no-pty -cwd "$WT"`.
- **Confira as montagens antes de medir.** Se `ls /app/data/saida/maos/m3d` vier vazio dentro
  do container, a montagem está errada: **pare**.
- **Teste de unidade** não pode depender de `data/saida/`. O gate roda sem ela.
- **Aspas.** Comando com aspas aninhadas falha: escreva um `.py` na worktree e rode-o.
- **Gate.** O `ruff` precisa de `--no-cache` e o `pytest`, de `-p no:cacheprovider`, por causa
  da montagem.

### 6.2 Território de cada frente

| frente | pasta de saída (`tab/caminhos.py`) | prefixo de módulo e teste | rodadas | porta |
| --- | --- | --- | --- | --- |
| 0 | `MAOS_FRENTE_0` → `frentes/f0_residuo/` | `tab/maos_residuo*.py` | 1101–1109 | — |
| A | `MAOS_FRENTE_A` → `frentes/fa_decodificador/` | `tab/maos_decod_*.py` | 1110–1129 | 8101 |
| B | `MAOS_FRENTE_B` → `frentes/fb_esquerda/` | `tab/maos_esq_*.py` | 1130–1149 | 8102 |
| C | `MAOS_FRENTE_C` → `frentes/fc_audio/` | `tab/maos_timbre_*.py` | 1150–1169 | 8103 |
| D | `MAOS_FRENTE_D` → `frentes/fd_ligados/` | `tab/maos_ligado_*.py` | 1170–1179 | 8104 |
| E | (guardada) | `tab/maos_dedilhado_*.py` | 1180–1189 | — |

As pastas já existem na cópia principal, e as constantes já estão em `tab/caminhos.py`.

### 6.3 O que é proibido

1. **Escrever fora da sua pasta**, inclusive nas pastas de outras frentes e nas saídas
   `m3*`, `m5`, `m7`, `m8`. A montagem só para leitura existe para isso.
2. **Editar `ESTADO.md`.** Ele é compartilhado e daria conflito entre worktrees. O "não repetir"
   vai no documento da rodada, e a sessão principal consolida no `ESTADO.md`.
3. **Editar arquivos de outra trilha** (lista na seção 6 do `contexto-maos.md`, mais
   `tab/audio_*.py`, `tab/partitura_*.py`, `tab/detector_tab.py`, `tab/ouro_video.py`). Importar
   e rodar é permitido.
4. **Editar módulo de outra frente ou do M8** (`tab/maos_corda_sem_direita.py`). Para reaproveitar
   o decodificador, **importe** as funções. Se precisar mudar o M8, descreva a mudança no
   relatório.
5. **Gravar em `data/gold/`.** Rótulo só do dono, por leitura visual. A frente monta a folha ou
   a lista de quadros, e a sessão principal leva ao dono.
6. **Dependência nova sem o dono.** A imagem `chorinho:dev` **não tem `scipy` nem
   `scikit-image`**. Tem `numpy`, `opencv` e `ffmpeg` (com `libopus` e `flac`). Hessiana,
   ajuste de picos e STFT se fazem com `numpy` e `cv2`.
7. **GPU.** Nenhuma frente deveria precisar: as pontas da mão já estão calculadas. Se precisar,
   pare e peça. A trava da GPU fica na `data/saida/`, que está só para leitura.
8. **Ler vídeo inteiro do HD externo.** É o gargalo de E/S: duas leituras longas ao mesmo tempo
   dobram o tempo das duas. Leia só os quadros de que precisa e registre quantos leu.
9. **Commit em `main`.** Trabalhe no branch da worktree. A integração é da sessão principal,
   **depois de remedir**.

---

## 7. As frentes

Cada teste segue o mesmo molde: **Contexto**, **Hipótese**, **Como**, **Entradas**, **Saída**,
**Aceite**, **Reprova ou para**, **Pegadinhas e falsos positivos**.

---

### Frente 0 — Anatomia do resíduo (F0.1)

**Contexto.** O M8 vai dizer **quantas** notas continuam erradas em cada degrau. Para escolher
a próxima frente, falta saber **onde** elas estão.

**Hipótese.** O resíduo do D1 e do D2 se concentra em poucas categorias, e cada categoria
aponta uma frente.

**Como.**

1. Gere a predição **por nota** de D0, D1, D2 e D3. A saída
   `data/saida/maos/m8/corda_sem_direita.json` só tem contagens.
   - Importe `preparar_video`, `decodar` e `pontuar` de `tab/maos_corda_sem_direita.py`.
   - O cache da câmera já está em `data/saida/maos/m8/camera_*.json`, então nada lê vídeo.
   - Confira que as contagens batem com a rodada 1013 (CA1).
2. Para cada nota errada no D1 e no D2, marque as categorias (não são exclusivas):
   - (a) **fronteira encapada × lisa**: a corda escolhida e a verdadeira estão em lados
     diferentes de 3|4 (violão de nylon: 1–3 lisas, 4–6 encapadas) → frente C;
   - (b) erro **dentro** das lisas ou **dentro** das encapadas;
   - (c) nota de **acorde** × nota **sozinha** no ataque;
   - (d) verdade é **corda solta** × verdade é **presa**;
   - (e) **troca de posição** perto da nota (menor casa presa muda ≥ 3 a menos de 1 s) →
     frentes A e B;
   - (f) **ligado**: só onde o dono marcou `l` em `data/gold/maos/padroes_direita.json` (9 marcas
     em 40 compassos) → frente D;
   - (g) **leitura suspeita**: casa > 7 (fora do que o classificador aferiu), ataque com duas
     notas na mesma corda, casa > 14;
   - (h) **D2 sem câmera** naquele ataque × **D2 com câmera e errado**. É a decomposição que o
     dono pediu: imprecisão da câmera × ambiguidade dentro da janela.
3. Monte a tabela categoria × vídeo e a matriz de interseção entre as categorias.
4. Olhe **10 notas do resíduo** no quadro (recorte do braço no instante do som) e diga, em cada
   uma, se a tablatura parece certa.

**Entradas.** Saída do M8 em `data/saida/maos/m8/`; produtos; `padroes_direita.json`.

**Saída.** `MAOS_FRENTE_0/residuo.json` e a tabela na rodada 1101.

**Aceite.**

- Reproduz os totais do M8 nota a nota (CA1).
- Toda nota errada cai em pelo menos uma categoria ou em "outros".
- A rodada traz uma **recomendação de ordem** para as frentes A–D, com o número de notas do
  resíduo que cada uma pode atacar.

**Reprova ou para.** Se "outros" passar de 30 % do resíduo, as categorias não explicam o erro.
Nesse caso, olhe mais 20 casos e proponha categorias novas, **antes** de recomendar qualquer
frente.

**Pegadinhas e falsos positivos.**

- As categorias se sobrepõem: **não some** as porcentagens.
- O produto também erra: casa > 7 não foi aferida, e há tela com cordas deslocadas de uma (rodada
  3014, Gymnopédie). Parte do "resíduo" pode ser erro do gabarito, não do decodificador. Por isso
  existem a categoria (g) e os 10 casos olhados.
- Exibições repetidas: a mesma página tocada 2 ou 3 vezes repete o mesmo erro. Conte também por
  (tela, coluna) distinta.
- Em violão de aço, a 3ª corda costuma ser encapada. Confira o violão de cada vídeo no quadro
  antes de usar a fronteira 3|4.

---

### Frente A — Decodificador (o que a sequência de notas já diz)

Contexto comum.

- O D1 do M8 tem pesos fixos a priori: α = 1 por casa, β = 3 por casa fora da janela,
  γ = 5 se a abertura passa de 4, δ = 0,5 por casa de mudança de posição.
- Tem também uma grade de pesos avaliada deixando um vídeo de fora.
- O D1 **não usa câmera**. Por isso pode ser avaliado em **toda tablatura** que tivermos, não
  só nos 4 vídeos: 8 produtos `sky_*` e 9 ouros do dono, em 7 canais.

#### A3 — Custo aprendido da tablatura (fazer primeiro na frente A)

**Contexto.** A pesquisa (§4.1) mostra que pesos escritos à mão não generalizam, e que o *Path
Difference Learning* aprende os pesos comparando o caminho ótimo com o caminho anotado. Nós
temos o caminho anotado de graça: é a tablatura.

**Hipótese.** Pesos aprendidos em outras tablaturas acertam mais corda que os pesos a priori
do D1, sem câmera.

**Como.**

1. Use as mesmas features do custo do M8 e acrescente:
   - salto de posição em função de `dt`;
   - mudança de corda entre notas consecutivas da mesma voz;
   - uso de corda solta;
   - casa absoluta (zonas de Heijink como atributo, não como regra).
2. Aprenda os pesos por **perceptron estruturado** (atualize na direção caminho anotado −
   caminho decodificado, só nos trechos onde divergem). É o PDL sem a descida de gradiente
   analítica. Fixe o número de épocas a priori.
3. Treino e teste:
   - para cada vídeo de teste, treine em todas as tablaturas **exceto ele**;
   - relate também um teste **deixando um canal de fora** nos ouros do dono (generalização para
     fora do `sky guitar`).

**Entradas.** Produtos e ouros (seção 5.1); o decodificador do M8, importado.

**Saída.** `MAOS_FRENTE_A/a3_pesos.json` (pesos por dobra) e `a3_medida.json`; rodada 1110.

**Aceite.** CA1–CA7 contra o D1, nos 4 vídeos. Mais:

- a mesma tabela nas outras tablaturas (relatório; não é critério);
- pesos parecidos entre as dobras: relate a amplitude de cada peso.

**Reprova ou para.** Não passa no CA2 ou no CA3. Ou os pesos mudam de sinal entre dobras:
nesse caso, o ganho é ajuste, não regra.

**Pegadinhas e falsos positivos.**

- **`sky_4` e `sky_8` são lacrimosa e glimpse**, dois dos vídeos de teste. Se entrarem no treino
  do próprio teste, o resultado é falso.
- O `sky guitar` é **um arranjador e um violonista**. Um custo aprendido nele aprende o estilo
  dele. O ganho nos 4 vídeos não prova nada fora do canal: por isso o teste deixando um canal de
  fora.
- A tablatura é a escolha do **arranjador**, não necessariamente o que o violonista tocou no
  vídeo. Um prior forte demais aprende a tablatura e passa por cima da evidência da câmera ou do
  áudio. Na fusão (B, C), o prior não pode zerar a evidência.
- Produtos com casa > 7 têm leitura não aferida (`sky_3` tem casa 24). Uma nota com a casa lida
  errada tem a altura errada, e os candidatos ficam errados. Relate a medida também só com
  casa ≤ 7.

#### A1 — Transições de Hori e Sagayama

**Contexto.** §4.2 de `maos.md`. A transição é o produto de três termos:

- uma Laplace centrada em zero no salto da posição da mão, com escala que cresce com o `dt`
  entre ataques;
- 1/(1 + |Δcorda|);
- um termo do dedo.

Sem o dedo da esquerda, a posição da mão é a **menor casa presa** do ataque, como no M8.

**Hipótese.** Com tempo para mudar de posição, saltar custa menos. O δ fixo do M8 trata igual
um salto em 0,1 s e um salto em 2 s.

**Como.**

1. Custo de transição: −log Laplace(Δposição; b(dt)) − log(1/(1 + |Δcorda|)), com
   b(dt) = b₀ + b₁ · dt.
2. Escolha b₀ e b₁ deixando um vídeo de fora. O termo do dedo fica de fora.

**Aceite.** CA1–CA7 contra o D1, e contra a A3 se ela já existir.

**Pegadinhas.**

- O `dt` precisa ser o do **som** (`t_audio`), não o do marcador. O marcador tem atraso que
  vagueia de 60 a 324 ms (rodada 2003), e isso cria `dt` falsos.
- "Δcorda" só faz sentido entre notas da mesma voz. Entre baixo e melodia de um arpejo, a
  mudança de corda é a música, não esforço.

#### A2 — Minimax e L_p-Viterbi

**Contexto.** §4.2 e §7. O Minimax escolhe o caminho cujo **pior** movimento é o mais fácil.
Com L_p (minimizar Σ custoᵖ), a programação dinâmica continua exata para p finito; p = ∞ é o
Minimax.

**Hipótese (fraca).** Um violonista evita o salto impossível mesmo que o resto da frase fique
mais caro.

**Como.** Rode p ∈ {1, 2, 4, ∞} com os pesos do D1 (ou da A3) e meça.

**Aceite.** CA1–CA7.

**Pegadinha.** O Minimax foi feito para **gerar** um dedilhado tocável, não para **adivinhar**
o que foi tocado. Para adivinhar, a soma (p = 1) é a estimativa de máxima verossimilhança. Não
espere ganho: o teste é barato e serve para fechar a pergunta com um número.

#### A4 — Corda solta quando a casa foge da vizinhança (opcional)

**Contexto.** §4.3, refinamento com média das casas vizinhas, sem as cordas soltas. Se uma nota
passa do desvio máximo da vizinhança, troca-se para a corda solta ou para a casa mais próxima da
média.

**Cuidado.** Isso é parente do D3 do M8. A vizinhança tem de excluir a **própria nota e o
próprio ataque**, senão vaza (rodada 1012). Só faça se a Frente 0 mostrar resíduo concentrado em
"corda solta × presa".

---

### Frente B — Mão esquerda (a janela de posição)

Contexto comum.

- O D2 do M8 projeta as pontas 8, 12, 16 e 20 do detector **só** pelo gabarito do braço do
  dono (um quadro por vídeo), e confere ataque a ataque se a câmera ainda casa com esse quadro.
- A janela é [floor(min) − 1, ceil(max) + 1] das casas das pontas sobre o braço.

O que o M8 mediu (rodada 1013):

- **Cobertura de 6,5 %.** O casamento é um NCC por translação de toda a região do braço do quadro
  do dono, com limiar 0,8.
  - A mão fica dentro do modelo e derruba o score mesmo com o mesmo enquadramento (retrato: 0,65).
  - No noturno e na lacrimosa, a câmera muda de plano.
- **Onde a janela existe**, ela contém a casa certa em 93–100 % das notas presas, mas tem
  **4,3–5,8 casas de largura**, e a alternativa de outra corda fica a 4–5 casas.
- **Com limiar 0,6** a cobertura sobe (retrato 358/473), mas o ganho não é consistente: o glimpse
  piora de 46 para 51 erros.
- **As pontas só existem no `t_ini`** do marcador: `pontas_*.json` foi calculado nos instantes
  das notas. Para olhar a mão no instante do som, é preciso rodar o detector de novo no `t_audio`.
  Isso usa GPU (imagem `chorinho-maos:dev`): **peça à sessão principal**, que roda com a trava da
  GPU e grava as pontas novas em `data/saida/maos/m8/`.

#### B1 — Janela por dedo, mais estreita

**Contexto.** A janela da mão inteira do M8 contém a verdade, mas é larga demais (4,3–5,8
casas). Para desempatar corda, a janela precisa:

- **conter** a casa certa;
- deixar **uma** corda candidata.

Uma janela enorme contém sempre a verdade e não ajuda nada.

**Hipótese.** Uma janela por **célula do dedo** (a ponta logo atrás do traste n pisa a casa n),
com folga de 10 % do vão do traste (§6.1, baixo), contém a casa certa quase tanto quanto a do M8
e deixa só 1 candidata muito mais vezes.

**Como.**

1. Para cada nota presa e ambígua, nos ataques em que a câmera casa com o quadro do gabarito,
   calcule:
   - (i) janela do M8;
   - (ii) união das células das pontas com folga de 10 %;
   - (iii) a mesma com 20 %.
   - Meça com o limiar da câmera em 0,8 (o do M8) e em 0,6 e 0,7, para ter mais ataques. Até a
     B3 existir, a cobertura é pequena: relate os denominadores.
2. Para cada janela, meça:
   - contém a casa verdadeira? (%);
   - largura média, em casas;
   - fração das notas ambíguas em que **sobra só 1 corda candidata**;
   - cobertura: ataques com janela / ataques totais.
3. Separe por vídeo e por limiar.
4. Se a janela (ii) ou (iii) passar no aceite abaixo, rode-a no decodificador como D2 e compare
   com o D1 (CA1–CA7).

**Entradas.**

- Pontas (seção 5.1).
- `data/gold/maos/braco.json` e `tab/maos_braco_geometria.py` (`montar_geometria`, `ajustar`),
  importados.
- `t_audio` (seção 5.1).
- Os quadros do acervo, só para os casos olhados.

**Saída.** `MAOS_FRENTE_B/b1_janela.json`; rodada 1130.

**Aceite (a priori; o dono pode ajustar).** Nos ataques cobertos:

- contém a casa certa em **≥ 95 %**;
- sobra 1 candidata em **≥ 70 %** das notas ambíguas presas;
- cobertura relatada com denominador.

Relate as três janelas mesmo que nenhuma passe.

**Reprova ou para.** Contém < 90 % em qualquer janela. Nesse caso, olhe 10 casos e diga se a
falha é da ponta (o detector), do braço (a projeção) ou do instante.

**Pegadinhas e falsos positivos.**

- **Instante.** No `t_ini` da tablatura o som ainda não saiu: o marcador vem 165–275 ms antes. A
  mão pode estar na posição **anterior**. O certo é o quadro no `t_audio` (ou logo antes: o dedo
  da esquerda firma antes do ataque, §3.1). As pontas que existem são do `t_ini`: meça com elas
  e declare. Se o erro "janela errada" aparecer em troca de posição, peça as pontas no `t_audio`
  (contexto da frente B).
- **Dedo levantado.** Dedos parados sobre outras casas alargam a janela. A janela é a posição da
  **mão**, não a de um dedo.
- **Corda solta não tem janela.** Ela custa zero esteja a mão onde estiver. Não conte nota solta
  como acerto da janela.
- **Ponta deslocada.** No q16 a ponta do detector fica cerca de 1 passo para o lado da corda 6
  (rodada 1008). Isso afeta o eixo das cordas, não o das casas. Use só o eixo ao longo do braço.
- **Calibração.** A calibração pela música (`tab/maos_calibrar_por_notas.py`, saídas em `m3c`)
  vaza a resposta: **não use**.

#### B3 — Rastreio do braço ao longo do vídeo

**Contexto.** O gabarito do braço tem 1 quadro por vídeo. Se a câmera muda (corte, zoom,
reenquadramento), o D2 perde cobertura. A pesquisa (§5.1, Paleari) segue os pontos do braço por
fluxo ótico e valida com duas restrições:

- a borda de cima e a de baixo do braço são colineares;
- as distâncias dos trastes seguem a regra das 12 notas a partir do nut.

**Hipótese.** Propagar a grade do quadro do dono para os outros quadros da **mesma cena**,
com teste de "não achou", aumenta a cobertura do D2 sem errar a posição. Hoje ela é de 6,5 %.

**Como.**

0. **Primeiro, o barato.** Refaça o casamento do M8 com a **mão mascarada** nos dois quadros
   (caixa das pontas e da palma, com folga) e meça só a cobertura. No retrato, onde o
   enquadramento não muda, isso deve bastar. Nos outros vídeos, siga para os passos 1–5.
1. Segmente o vídeo em cenas da câmera do braço. Já existem cortes em
   `data/saida/maos/m3d/cenas/*.txt`: confira-os antes de usar.
2. Dentro da cena do quadro do dono, siga pontos do braço (Lucas-Kanade do OpenCV), **com a
   máscara da mão** (pontas e palma do detector) e **sem o painel da mão direita**.
3. Ajuste uma homografia por quadro e valide:
   - colinearidade das bordas;
   - razões dos trastes pela regra das 12 notas, com a mesma tolerância da projetiva da rodada
     1005.
4. Se falhar, emita **"não achou"** (o ataque volta ao D1), nunca uma grade duvidosa.
5. **Validação.** Proponha **2 quadros por vídeo**, longe do quadro do dono e em cenas diferentes,
   para o dono marcar na ferramenta do braço (`tab.maos_braco_gabarito`). A sessão principal
   leva ao dono. A frente não grava no gabarito.

**Aceite.** Nos quadros novos marcados pelo dono:

- trastes 1–12 a < 1/4 de casa em ≥ 90 %, e nut a ≤ 0,25 de casa;
- **zero** quadros aceitos com erro > 0,5 de casa (o "não achou" tem de pegar esses);
- com a grade rastreada, o D2 melhora no CA2 e no CA3 contra o D2 do M8.

**Reprova ou para.** Algum quadro aceito com erro > 0,5 de casa: o "não achou" não está
funcionando. Pare antes de medir no decodificador.

**Pegadinhas e falsos positivos.**

- **Mediana entre cortes.** A mediana temporal de trechos com enquadramento diferente dá uma
  imagem incoerente (rodada 1012). Segmente primeiro. O relatório do agente daquela rodada
  dizia "nítida" e não era: **anexe a imagem**.
- **O outro painel.** O painel da mão direita também tem cordas e trastes, e a grade já foi
  esticada até ele (rodada 1009).
- **"Crista" não valida.** Ela premia qualquer estrutura clara (1012). Só valem as marcas do dono
  ou o olho.
- **A mão é a textura que mais se mexe.** Pontos do LK dentro da mão arrastam a grade junto com
  ela.

#### B2 — Ocupação de pele por célula (só se a B1 mostrar falha da ponta)

**Contexto.** §6.1, Paleari: a célula corda × casa conta como pisada se ≥ 60 % dos pixels forem
de mão.

**Pegadinhas.**

- A mão cobre muitas células que não pisa (dedos atravessam o braço). Ocupação não é pressão.
- Pestana vira "todas as cordas" (a pesquisa admite).
- A cor de pele muda com a luz.
- O "0 % de falso positivo" foi medido em webcam, num cenário controlado: não se transfere.

**Aceite.** Mesmo critério da B1, comparado com a melhor janela da B1.

#### B4 — Steger para cordas e trastes (só se a B3 precisar de linha por quadro)

**Contexto.** §5.2.

- O nosso erro com o pente (1009, 1012) não foi falta de precisão sub-pixel. Foi pegar a
  **estrutura errada** (borda do braço, outro painel).
- O modelo de Steger separa **barra** (linha fina, mesma polaridade dos dois lados: a corda) de
  **degrau** (polaridade diferente: a borda). É essa parte que interessa.

**Como.** Hessiana do gaussiano em `numpy` ou `cv2`, com σ > w/√3 pela largura medida da corda
em px. Classifique cada crista em barra × degrau pela razão dos gradientes laterais.

**Aceite.** Contra `corda1` e `corda6` do gabarito do braço nos 6 quadros do `sky guitar`:

- erro ≤ 0,10 do vão 1–6 em ≥ 5 dos 6 quadros;
- nenhum erro > 0,30, com um critério de "não achou".

**Pegadinha.** Sem `scipy` nem `scikit-image` na imagem; não instale.

---

### Frente C — Áudio: a corda pelo timbre

Contexto comum.

- **O áudio.** O cache da trilha do áudio (`/cache/audio/`, só leitura) é FLAC mono a
  22.050 Hz. A fonte é **Opus a 48 kHz** em todo o acervo medido (rodada 2001).
- **O instante.** `t_audio` dos 4 vídeos em `data/saida/maos/m7/audio/`.
- **A física** (§2): para a mesma altura, a corda de baixo é tocada numa casa 5 acima (4 entre a
  2ª e a 3ª). Logo:
  - β(s+1, n+5) / β(s, n) = [β(s+1, 0) / β(s, 0)] · 2^(5/6);
  - corda diferente, para a mesma altura, deveria dar β diferente.

#### C1 — Separabilidade pela inarmonicidade (pode começar já; teste de ir ou não ir)

**Hipótese.** Num mesmo vídeo, para a mesma altura, o β medido separa as cordas candidatas
melhor que o acaso, com o áudio do YouTube.

**Como.**

1. **Áudio.** Extraia o áudio dos 4 vídeos **a 48 kHz**, sem reamostrar, para
   `MAOS_FRENTE_C/`. Use a regra do `t_amostra0` da rodada 2001: o primeiro frame de áudio
   decodificado, não o `start_time` (com Opus, o `start_time` erra ~7 ms). Pode importar
   `tab.audio_extrair`; não edite.
2. **Controle sintético primeiro.**
   - Gere notas com β conhecido (parciais a k · f₀ · √(1 + β · k²), decaimento exponencial).
   - Codifique em Opus com `libopus`, **na taxa do áudio dos vídeos** (meça com `ffprobe`).
   - Recupere o β.
   - O método só segue se o erro de recuperação for **menor que metade** da diferença de β
     esperada entre duas cordas candidatas.
3. **Notas.** Use notas **isoladas**: nenhum outro ataque de 0,15 s antes até 0,25 s depois.
   Pule o transitório (os primeiros ~25 ms).
4. **Medida do β.**
   - STFT longa (≥ 4.096 amostras) com preenchimento de zeros e ajuste parabólico de 3 pontos
     no pico (§5.2).
   - Picos perto de k · f₀ para k = 2 … K, só abaixo de ~6 kHz.
   - Ajuste por mínimos quadrados de (f_k / k)² = f₀² + f₀² · β · k². É linear em k²: dá f₀ e
     β juntos.
5. **Separação.**
   - Para cada **par de cordas candidatas com a mesma altura**, com ≥ 8 notas de cada lado,
     calcule a AUC do β entre as duas cordas, por vídeo.
   - Calibre o β esperado por corda (β(s, 0)) na **primeira metade** do vídeo, ou nas exibições
     ímpares, e teste na outra.

**Saída.** `MAOS_FRENTE_C/c1_beta.json` (β por nota, com corda, casa e altura), a figura β ×
casa por corda e a rodada 1150.

**Aceite (de ir para a C2).**

- Controle sintético aprovado.
- AUC **≥ 0,80** fora da metade de calibração, em pelo menos metade dos pares com amostra
  suficiente, em pelo menos 3 dos 4 vídeos.
- A curva β(s, n) medida segue 2^(n/6) dentro de cada corda: a inclinação de log β × n
  compatível com log 2^(1/6).

**Reprova ou para.**

- O controle sintético falha: o Opus destrói a informação, e a frente C fecha com esse número.
- Ou AUC < 0,65 na maioria dos pares.

**Pegadinhas e falsos positivos.**

- **Opus em alta frequência.** O Opus (modo CELT) quantiza a energia por banda e preenche
  bandas altas com ruído. A posição fina dos parciais altos pode ser **inventada pelo codec**.
  Por isso: controle sintético e K limitado em frequência.
- **Afinação.** O violão pode não estar em 440 Hz. Estime o f₀ pelo ajuste, não pela altura
  da tablatura.
- **Notas que ainda soam.** Notas anteriores continuam soando, e a corda solta vibra por
  simpatia. Descarte parciais a ±30 cents de qualquer parcial de outra nota que ainda soa (as
  alturas vêm da tablatura).
- **Parciais que somem.** A posição do ataque anula parciais múltiplos de L/d. Exija ≥ 6
  parciais no ajuste.
- **Confusão com a casa.** β cresce com a casa (2^(n/6)). Compare **só dentro da mesma altura**.
  Entre alturas diferentes, o β mistura casa, corda e f₀ e dá separação falsa.
- **Confusão com o dedo.** Timbre por amplitude (centroide, brilho) separa **polegar ×
  dedos**, e o polegar toca os bordões. Um classificador de timbre aprende "polegar" e parece
  aprender "corda". O β, que vem da **frequência** dos parciais, sofre bem menos disso. Por isso
  a C1 usa β, não timbre.
- **Voz e vibrato.** Vídeo-aula tem fala por cima da música em alguns trechos. Vibrato move o
  f₀ durante a nota.
- **Exibições repetidas.** A mesma frase repetida em exibições diferentes cai nas duas metades
  da divisão por nota sorteada: por isso a divisão é por tempo ou por exibição.
- **Rótulos da tablatura.** Usar a tablatura para escolher notas isoladas e calibrar β(s, 0) é
  aceitável **para medir a viabilidade**. Sem tablatura, a calibração teria de vir das notas que
  o decodificador já decide com confiança. Declare isso na rodada como limite superior.

#### C2 — O áudio dentro do decodificador (só se a C1 passar)

**Como.**

1. Some ao custo de cada corda candidata o termo −w · log p(β medido | corda), com p calibrado
   como na C1, e um **piso**: o termo do áudio tem um teto, para nunca zerar as outras evidências
   (é o "*weight floor*" do HandSkeletonNet, §6.2).
2. Escolha w deixando um vídeo de fora.
3. Notas sem β confiável (não isoladas, menos de 6 parciais) ficam sem o termo.

**Aceite.** CA1–CA7 contra o D1 e contra o D2. Relate a cobertura: notas com termo do áudio /
notas ambíguas.

**Pegadinha.** O ganho tende a se concentrar nas notas isoladas, que já são as mais fáceis para
o decodificador. Relate consertadas e quebradas **separando** isoladas e não isoladas.

#### C3 — Encapada × lisa (só se a Frente 0 mostrar que vale)

Classificar só o lado da fronteira 3|4 (nylon) é mais fácil que separar todas as cordas. Mas só
vale se a categoria (a) da Frente 0 for grande, e esbarra na **confusão com o dedo** acima (o
polegar toca as encapadas). Para não aprender "polegar", o teste tem de comparar notas da mesma
altura tocadas com o mesmo dedo. O dono tem esse rótulo em 40 compassos (`padroes_direita.json`).

---

### Frente D — Ligados e técnicas como restrição

#### D1 — Nota ligada = mesma corda de uma nota que ainda soa

**Contexto.** §2, filtro de plausibilidade: *slide* e ligado (*hammer-on*, *pull-off*) acontecem
na **mesma corda** da nota de onde saem. A corda solta pode ser o alvo de um *pull-off*. No
decodificador, isso é uma restrição dura que corta candidatos.

**Hipótese.** Nas notas ligadas, a restrição conserta erros do D1 sem quebrar os acertos.

**Fontes do rótulo "ligada"**, da mais otimista para a mais realista:

1. **Marcas `l` do dono** em `padroes_direita.json`: 9 marcas, um limite superior pequeno.
2. **Símbolos da tablatura**: o produto guarda o glifo cru em `nao_notas` (`h`, `p`, `/`, `\`,
   arco). O significado por canal está em `configs/simbolos.yaml`. É informação da tablatura:
   vale para o cenário "tablatura completa", não para vídeo sem tablatura.
3. **Áudio sem ataque**: a coluna tem nota, mas o fluxo espectral não tem ataque perto do
   `t_audio` esperado. É o cenário realista.

**Como.**

1. Para cada fonte, aplique a restrição: a nota ligada fica na corda de uma nota do ataque
   anterior (ou de até 0,5 s antes), com casa diferente na mesma corda.
2. Meça consertadas e quebradas contra o D1, **por fonte**.

**Saída.** `MAOS_FRENTE_D/d1_ligados.json`; rodada 1170.

**Aceite.** CA1–CA7 contra o D1, por fonte. Relate quantas notas ligadas cada fonte achou, e a
**precisão do rótulo** da fonte 3 contra as fontes 1 e 2.

**Reprova ou para.** A fonte 3 tem precisão < 70 % contra a 2: o detector de "sem ataque"
inventa ligado.

**Pegadinhas e falsos positivos.**

- **Prolongamento não é nota nova.** `(6)` e arco entre notas **iguais** são a mesma nota
  segurada. "Acertar" a corda dela é trivial e infla o ganho. Separe ligado de altura diferente
  de prolongamento.
- **Ornamento tem ataque às vezes.** As notas de ornamento sob arco (mordente 2–3–2) às vezes
  têm ataque no áudio e às vezes não (rodada 2006). A regra "coluna estreita = ornamento" já foi
  reprovada lá.
- **Ligado de mão esquerda "do nada".** Existe *hammer-on* sem nota anterior na corda. É raro no
  violão clássico, mas quebra a restrição: conte esses casos.
- **Erro em cadeia.** Se a nota de origem estiver na corda errada, a ligada vai junto para a
  corda errada. Relate se os erros que sobram vêm em pares origem–ligada.
- **Harmônico.** Harmônico natural (`<12>`, losango) soa uma oitava ou mais acima da corda
  solta. Os candidatos por altura ficam errados. Tire os harmônicos da medida, ou trate a altura
  deles à parte. O produto já confundiu o algarismo `1` com harmônico (Greensleeves, rodada da
  Fase 8).

---

### Frente E — Dedilhado (guardada; não começar sem o dono)

Fica guardada pela decisão 1005: o dono quer **só a corda** agora. Fica registrado como testar
quando ele pedir:

- **Mão direita.** As regras de Yepes (§3.1): m→i subindo de corda é ruim, a→m é bom, ciclos
  a-m-i, m-i-a e i-a-m. Entram como regras extras em `tab/maos_regra_direita.py` e são medidas
  contra os 40 compassos confirmados (`padroes_direita.json`), deixando um vídeo de fora. A
  referência é a v2: 172/216.
- **Mão esquerda.** Os estados de Hori e Sagayama com dedo (ifp = casa − dedo + 1), contra o
  gabarito de dedos do MVP (`dedos_retrato_brasileiro.json`, 53 notas; visão: 42/53).
- **Pegadinhas.**
  - Um violonista só, 4 vídeos e 216 notas.
  - O dono avisou que o dedilhado "varia bem de pessoa para pessoa".
  - O resíduo da v2 já é preferência do violonista (decisão 1005), não falta de regra.

---

## 8. Pegadinhas que valem para todas as frentes

1. **A tablatura é gabarito e entrada ao mesmo tempo.** Só a altura pode entrar, e declarada
   ("áudio perfeito"). Já são caminhos de vazamento conhecidos:
   - a calibração do braço pela música (1006–1008);
   - a janela centrada na casa verdadeira (1012);
   - a vizinhança que inclui a própria nota ou o próprio ataque;
   - o alinhador do áudio (ele usa as alturas da tablatura para casar colunas a ataques). Isso
     é aceitável para o **instante**, mas não use a saída dele como evidência de corda.
2. **O marcador vem antes do som.** São 165–275 ms nos 4 vídeos e não é constante: vagueia de
   60 a 324 ms (rodada 2003). Para olhar a mão ou medir o áudio, use o `t_audio`.
3. **Exibições repetidas inflam o n.** O `sky guitar` toca a mesma página mais de uma vez.
   Relate também por (tela, coluna) distinta. Nunca divida treino e teste por nota sorteada.
4. **Quatro vídeos, um canal, um violonista.** Tudo o que for medido nos 4 vídeos vale para o
   `sky guitar`. A frente A pode e deve medir em outros canais (seção 5.1). As outras devem dizer
   isso explicitamente no resultado.
5. **Calibrar e testar nas mesmas notas** (frente C) dá um número falso. Calibre por tempo ou
   por exibição.
6. **O produto erra.** Casa > 7 não aferida, cordas deslocadas numa tela, `1` lido como
   harmônico. Uma parte do "erro" de qualquer frente pode ser erro do gabarito. Por isso o CA6
   manda olhar os casos.
7. **A acurácia geral esconde.** Com 92–96 % das notas ambíguas e 88 % resolvidas pela casa mais
   baixa, a diferença entre métodos está em poucas centenas de notas. O que conta é consertadas
   e quebradas nas ambíguas, por vídeo (CA2, CA3).
8. **Afinação e capotraste.** O M8 assume afinação padrão e sem capotraste. No MVP o capotraste
   foi medido como 0 (rodada 2002). Num vídeo com afinação baixada (drop D), os candidatos por
   altura ficam errados. Confira no início do vídeo ou na tablatura antes de incluir um vídeo
   novo.
9. **Afirmação sobre imagem precisa da imagem.** Na rodada 1012, o agente descreveu como
   "nítida" uma mediana incoerente. Toda frase sobre o que aparece num quadro vem com o caminho
   do recorte. O revisor vai abrir.
10. **Medida interna não é validação.** "Crista", score do detector e consistência entre
    sementes dizem que o método é estável, não que está certo. Só valem o gabarito do dono, a
    tablatura (com as ressalvas acima) ou o olho.
11. **Pré-processamento é parte da medida** (`AGENTS.md`, regra 9). Mudou o recorte, a taxa de
    amostragem ou a janela de tempo? Remeça a referência com a mudança, antes de comparar.

---

## 9. O que cada frente entrega

1. **Código** com o prefixo da frente e testes de unidade sem `data/saida/` e sem acervo. O gate
   tem de estar verde na worktree.
2. **Saídas** só na pasta da frente.
3. **Documento de rodada** na faixa da frente, com estas partes: pergunta; pesos a priori
   (escritos antes da medida); tabela no formato da seção 5.2; consertadas e quebradas; os 10
   casos olhados, com as imagens; o que deu errado; "não repetir".
4. **Commit no branch da worktree**, com o número medido na mensagem. Não commitar em `main`.
5. **Resumo para o dono** em português, curto. Diga quantas notas a frente conserta e quantas
   quebra nos 4 vídeos, e se passou nos critérios. Diga também o que ela **não** prova.

A sessão principal remede o número antes de integrar e consolida o `ESTADO.md`.

---

## 10. Perguntas para o dono (nenhuma bloqueia o começo)

1. **B3.** Topa marcar 2 quadros a mais por vídeo na ferramenta do braço (8 quadros nos 4
   vídeos)? Sem isso, o rastreio do braço não tem como ser validado.
2. **A3.** Quer considerar um corpus externo de tablatura, como o DadaGP? Ele precisa de pedido
   de acesso e é dependência nova. Só se o custo aprendido na nossa própria tablatura parar de
   melhorar.
3. **Critérios a priori.** Os limiares das seções 5.3 e 7 (+1 ponto percentual, 20 notas, 95 %,
   70 %, AUC 0,80) foram fixados por mim antes de qualquer medida. Se quiser outros, ajuste
   **antes** de as frentes medirem, não depois.

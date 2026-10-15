# Frentes de teste da pesquisa da tablatura

**Data**: 2026-10-15. **Base**: [`tablatura.md`](tablatura.md), a revisão de literatura que o dono
trouxe (feita com o Gemini). **Autor**: trilha tablatura, sessão principal, que também revisa o
que as frentes entregarem. **Para quem**: agentes que vão testar as ideias em worktrees separadas.

> **Leia antes de começar**: `AGENTS.md`; este documento inteiro; a parte de `tablatura.md`
> citada na sua frente; no `ESTADO.md`, as seções "Tablatura — 2026-10-15" (fase 8) e
> "produto troca de leitor"; as decisões `docs/decisoes/0009` (canais fora) e `0010` (leitor
> `rede`); o bloco `regra_do_arco_pelos_numeros` de `configs/simbolos.yaml`.

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
10. Decisões do dono (pendentes)

---

## 1. Objetivo

### 1.1 Do projeto

O produto é um JSON por vídeo com **corda, casa, coluna, compasso, técnica e tempo** de cada
nota, para milhares de vídeos-aula. O alvo final é um dataset vídeo → tablatura + partitura para um
modelo futuro.

### 1.2 Da pesquisa

O pedido ao Gemini cobriu sete perguntas:

1. reconhecimento de tablatura em imagem, com os símbolos de técnica;
2. detecção de símbolos pequenos e de ligaduras na leitura de partitura (OMR);
3. geração sintética de tablatura com técnicas (Guitar Pro, DadaGP, AlphaTab, LilyPond);
4. tablatura que rola na tela e costura de quadros;
5. tablatura em texto (ASCII) a partir de imagem;
6. transcrição por áudio como verificação cruzada da leitura;
7. datasets de vídeo de violão com tablatura alinhada.

### 1.3 Deste documento

A leitura da casa já está perto do teto: **0,996 fora do ouro** (seção 2). Uma frente que só tente
subir esse número disputa décimos. Este documento responde, com medida, a três perguntas:

1. **Técnica.** Quais ideias fazem o campo `tecnica` sair certo? Hoje ele sai **sem validação**
   (decisão 0010).
2. **Cobertura.** Como ler a tablatura que **rola** na tela? São cerca de 16 % dos vídeos com
   tablatura, e o produto não lê nenhum deles.
3. **Resíduo da casa.** Um sinal **independente da imagem** (o som ou outro leitor) acha os erros
   de leitura que sobram?

---

## 2. Onde estamos (o que já foi medido)

**O leitor.** O leitor `rede` (`tab/detector_tab.py`) lê o sistema inteiro de uma vez:

- é treinado no sintético (`tab/sintetico_sistema.py`) e ajustado nos 8 ouros de vídeo, pelo
  script `data/saida/n4/treinar_ft.py`, que **não está no git**;
- o modelo do produto é o `artefatos/detector_tab_final_s1_ger` (commit `599f3c83`).

**A casa, nos 6 vídeos das dobras 2–4.** Cada vídeo é lido pelo modelo da dobra que não o viu,
gerador novo, semente 1 (`data/saida/fase8/ger/tab/ger_*.json`):

| vídeo | notas no ouro | entregues | casadas | casa certa | inventadas | perdidas |
| --- | --- | --- | --- | --- | --- | --- |
| Greensleeves | 106 | 106 | 106 | 106 | 0 | 0 |
| Gymnopédie | 392 | 391 | 391 | 380 | 0 | 1 |
| South American | 269 | 269 | 269 | 269 | 0 | 0 |
| From This Place | 381 | 383 | 375 | 373 | 8 | 6 |
| End of Beginning (páginas conferidas) | 303 | 308 | 303 | 302 | 5 | 0 |
| Room 335 (páginas conferidas) | 323 | 342 | 320 | 317 | 22 | 3 |
| **total** | **1774** | **1799** | **1764** | **1747** | **35** | **10** |

Nas 3 sementes, a amplitude é esta:

- precisão de 0,978 a 0,981;
- revocação de 0,994 a 0,996;
- casa de 0,987 a 0,990.

**A casa fora do ouro (T8.2).** São 35 telas de 18 canais, conferidas pelo dono, que nenhum
modelo viu no treino (`data/saida/fase8/ger/t82_comparar.py`):

- 1573 notas no ouro e 1566 entregues;
- casa certa em **1551/1557**;
- 9 inventadas e 16 perdidas.

**De onde vem o resíduo.** As 31 falhas da T8.2 com o modelo anterior (`data/saida/t82/erros/`)
se dividem assim:

| causa | falhas |
| --- | --- |
| casa de dois algarismos (10, 12, 14) perdida ou lida pela metade | 12 |
| nota encostada em outra | 7 |
| fundo ou cor | 4 |
| símbolo lido como nota | 3 |
| "1" de perna comprida lido como 4 | 3 |
| fora do recorte | 2 |

Com o modelo atual, os erros de dois algarismos continuam.

**Técnica: como a rede aprende hoje.**

- A rede tem uma saída de técnica por nota, com 10 classes: `h`, `p`, `/`, `\`, `harm`, `lig`,
  `bend`, `vib`, `orn` e `enfeite`.
- Ela aprende técnica **só no sintético**: o ajuste fino zera a máscara de técnica nas telas
  reais (`treinar_ft.py`, `perda_ft`). Por isso as marcas do dono são um teste honesto de técnica,
  mesmo para o modelo do produto.
- Rasgueado e arpejo o gerador desenha como **região** (`REGIOES`), mas a rede **não tem saída**
  para eles.
- O gerador marca a técnica do par (h, p, slide) na nota de **destino**.

**Técnica: as marcas do dono.** São 415 regiões, no formato `{"cordas": [a, b], "x_quadro":
[x0, x1], "tecnica": [...], "obs": ...}`:

| fonte | regiões | telas | composição |
| --- | --- | --- | --- |
| End of Beginning | 114 | 7 | x 76, vazio 12, h 9, p 6, rasg 5, `\` 2, arpejo 2, outra 2 |
| La Vie en Rose | 5 | 4 | `/` 2, h 1, outra 2 |
| From This Place | 32 | 5 | arpejo 13, outra 8, vazio 5, h 3, p 2, `/` 1 |
| Room 335 | 177 | 13 | outra 64, vazio 21, `/` 21, x 39, h 10, `\` 9, rasg 7, h+p 4, p 2 |
| T8.2 (`conferencia_t82.json`) | 87 | 24 | vazio 32, x 9, p 9, h 6, arpejo 6, bend 5, `/` 5, h+p 5, harm 4, rasg 3, `\` 2, outra 1 |

- Os "vazio" e os "outra" dizem o que são no campo `obs`:
  - ligadura de prolongamento: cerca de 75;
  - figuras de ritmo (colcheia 36, semicolcheia 8, semibreve 5);
  - compasso e ritornelo: cerca de 11;
  - "ligadura slide": 4.
- Há uma observação do dono: arco sobre o slide quer dizer que a corda não é tocada de novo.
- Os outros 4 ouros (Greensleeves, Gymnopédie, South American e Retrato) não têm marca de técnica.

**Rolagem.** O produto detecta a rolagem (`phaseCorrelate`, campo `modo`), mas não lê o vídeo.
Pelo censo:

- 65 de 405 vídeos com janela medida são rolantes (16 %), em 8 canais: `mr. tabs` 18,
  `leonardo ramos` 14, `kenneth acoustic` 14, `guitar dell'arte` 11 e outros;
- a estimativa é de cerca de 450 vídeos no acervo ativo;
- a classificação "rolante" **não foi conferida** no olho.

**Som e partitura.** Duas trilhas já conferem a leitura de fora:

- **Áudio** (rodada 2011): já existe um alarme de leitura **por exibição**. Das telas com alarme,
  5 de 6 tinham erro de leitura.
- **Partitura** (rodada 3012): a tab desmente trocas de altura do Audiveris.

**ASCII.** A tablatura em texto ficou fora por decisão do dono (0009: `violaodecria` e `tv cifras`).

---

## 3. Triagem da pesquisa: o que serve, o que já temos, o que fica fora

Critério: a ideia serve se pode melhorar a **técnica**, a **cobertura** (rolagem) ou **achar os
erros da casa** nos nossos vídeos, com as dependências que temos ou que o dono aprovar.

### 3.1 Testar

| ideia (seção de `tablatura.md`) | frente | por quê |
| --- | --- | --- |
| régua de técnica: medir o que a rede já entrega contra as 415 marcas | 0 | sem ela nenhuma frente de técnica tem número |
| o arco no topo some quando o painel corta a corda 1 (aviso do dono) | 0 | o recorte é entrada do modelo; precisa de número antes de mexer |
| técnica decidida pelos números sob o arco (§2, "associação semântica"; regra do dono) | A1 | pós-processamento barato; a regra já foi confirmada pelo dono |
| conector como objeto próprio (máscara ou caixa orientada, §2, DeepScoresV2) | A2 | só se a Frente 0 mostrar que a falha é **achar** o arco, não classificá-lo |
| renderizador real de Guitar Pro (AlphaTab) como segunda fonte do sintético (§3) | B1, B2 | o que mais rendeu na história do projeto foi cobertura do gerador (`AGENTS.md`, regra 6) |
| costura da tablatura que rola, ancorada nas barras, com mapa x → t (§4, `score_capture`) | C1 | T8.4 já está no escopo (D7 = sim); cerca de 16 % dos vídeos |
| altura do som conferindo a casa, nota a nota (§6) | D1 | sinal independente da imagem; o alarme por exibição já mostrou que funciona |
| modelo pronto de transcrição de violão (GAPS, FretNet) como fonte da altura (§6) | D2 | só se a D1 passar com o sinal simples |
| `guitar-tab-omr` como segunda leitura no resíduo (§1) | E1 | sonda barata, expectativa baixa |
| máscara de ligadura do `homr` em recorte de tablatura (§2) | E2 | sonda barata, expectativa baixa |

### 3.2 Já temos (não refazer)

| ideia | onde já está |
| --- | --- |
| treino só em sintético com rótulo exato | `tab/sintetico_sistema.py` + `tab/detector_tab.py` |
| leitor de algarismo como âncora espacial, técnica presa à nota | saída de técnica por nota da rede |
| técnica desenhada no sintético (h, p, slide, harmônico, ligada, bend, vibrato, enfeite) | `TECNICAS` em `tab/sintetico_sistema.py` |
| h/p/ligadura/mordente/slide pelos números | `configs/simbolos.yaml`, `regra_do_arco_pelos_numeros` (dono, 2026-10-15) |
| detectar que a tela rola | `phaseCorrelate`, campo `modo` (fase 3) |
| filtrar quadros quase iguais, achar as linhas da tab | segmentação em telas (`tab/telas.py`) e painel (`tab/painel.py`) |
| conferência por altura | alarme de leitura do áudio (2011); tab × partitura (3012) |
| GPU de 8 GB, um modelo por vez | protocolo `data/saida/gpu.lock` |

### 3.3 Fora agora (com o motivo)

| ideia | motivo |
| --- | --- |
| trocar o leitor pelo `guitar-tab-omr` | o README dele mede **76,5 %** de sistemas exatos no próprio dado limpo; o nosso dá 0,996 de casa em vídeo |
| YOLOv8-OBB (Ultralytics) | licença **AGPL-3.0**; se a A2 for necessária, usar a geometria do nosso gerador e uma cabeça própria |
| copiar código do `score_capture` | **GPL-3.0**; aproveitar só a ideia (barras como âncora) |
| leitor ASCII (§5) | fora pela decisão 0009. A ideia fica registrada: fechar os hífens e fazer um estilo monoespaçado no gerador. Só volta se o dono reabrir |
| GAPS e TapToTab como dado de tela | os vídeos filmam o violonista, sem tablatura na tela; servem à trilha das mãos e à D2, não ao leitor |
| `guitar-pro-youtube-sync` (Songsterr) | depende de baixar tablatura de serviço de terceiros; termos de uso |
| LilyPond, VexTab, Crisp Notation, MuseScore como renderizadores | um renderizador novo por vez. Só se a B mostrar que o AlphaTab ajuda e falta estilo |
| Whisper → tokens DadaGP, Noise2Fret, Fretwork | não verificados, e a D2 já tem candidatos mais simples |

### 3.4 O que a checagem já mostrou (2026-10-15)

A revisão do Gemini traz números que **não batem** com a fonte. Conferi três itens:

| item | a pesquisa diz | a fonte diz |
| --- | --- | --- |
| `LIU9293/guitar-tab-omr` | SER 0,852 %, licença aberta | README: core SER **0,02364**, **76,5 %** exato em 200 amostras de validação; pesos no Hugging Face; **licença não declarada** |
| `Carrot-shreds/score_capture` | costura por SSIM e linhas da pauta | existe; **GPL-3.0**; a costura usa as **barras de compasso** como referência; rolagem horizontal de TAB é a prioridade declarada |
| GAPS (`xavriley/GAPS`) | CC BY-NC-SA, MusicXML com tablatura | a página do Hugging Face diz **MIT** e não fala em tablatura; pesos do modelo não confirmados |

**Regra.** Antes de depender de um repositório, a frente confere **que ele existe**, a
**licença** e o **número** na fonte original. O resultado vai no documento da rodada. Os outros
itens da pesquisa não foram conferidos.

---

## 4. Ordem dos testes

Crie as worktrees **a partir do commit `599f3c83` ou depois**: a referência é o modelo
`detector_tab_final_s1_ger` e o gerador do commit `6cd60d78`.

| ordem | teste | frente | depende de | custo |
| --- | --- | --- | --- | --- |
| 1 | régua de técnica e anatomia do erro | F0.1 | nada | baixo (CPU) |
| 2 | arco cortado no topo | F0.2 | nada | baixo (CPU) |
| 3 | técnica pelos números sob o arco | A1 | F0.1 | baixo (CPU) |
| 4 | costura da rolagem + mapa x → t | C1 | gabarito de 1 vídeo rolante (dono) para o aceite | médio (CPU, leitura de vídeo) |
| 5 | altura do som confere a casa | D1 | áudio alinhado da trilha áudio | médio (CPU) |
| 6 | AlphaTab: sonda de estilo | B1 | dependência aprovada pelo dono | médio (CPU) |
| 7 | AlphaTab no treino | B2 | B1 mostrar lacuna; GPU | alto (GPU, 9 treinos de ~20 min) |
| 8 | sondas de modelos prontos | E1, E2 | licença conferida | baixo |
| 9 | conector como objeto | A2 | F0.1 e A1 mostrarem falha de detecção | alto (GPU) |
| 10 | modelo de áudio pronto | D2 | D1 aprovada; dependência | médio |

As frentes podem rodar em paralelo, cada uma na sua worktree. A ordem acima é de **prioridade**
(qual resultado muda mais o plano), não de espera.

**Por que esta ordem.**

1. **A Frente 0 vem primeiro** porque hoje a técnica não tem número. Ela diz se o erro está em
   **achar** a técnica, em **classificar** h, p ou ligadura, ou em classes que a rede nem tem
   (arpejo, rasgueado). Isso decide entre A1, A2 e B.
2. **A A1 é a mais barata das que podem ganhar muito.** Ela aplica a regra do dono sobre o que a
   rede já acha, sem treinar nada.
3. **A C1 é a maior lacuna de cobertura.** Cerca de 450 vídeos ficam de fora sem ela.
4. **A D1 é o único sinal independente da imagem** para o resíduo da casa.
5. **A B custa GPU e dependência nova.** Só vale depois de a Frente 0 mostrar que falta estilo ou
   classe no gerador.

**Revisão da ordem.** A Frente 0 pode mudar a ordem. Por exemplo, se a rede achar menos da metade
dos arcos, a A1 sozinha não basta e a A2 ou a B sobem.

---

## 5. Régua comum (vale para todas as frentes)

### 5.1 Dados

**Ouros de vídeo** (`data/gold/ouro_video/`, **só leitura**; o `retrato_brasileiro.json` antigo
foi substituído pelo `_v2`):

| dobra | vídeos | modelo que não os viu |
| --- | --- | --- |
| 1 | retrato_brasileiro_v2, la_vie_en_rose | `detector_tab_v3ft_d1` (gerador antigo) |
| 2 | greensleeves, gymnopedie | `detector_tab_v3ft_d2_ger`, `_ger_s2`, `_ger_s3` |
| 3 | south_american, tab_from_this_place | `detector_tab_v3ft_d3_ger` (e sementes) |
| 4 | end_of_beginning, tabroom_335 | `detector_tab_v3ft_d4_ger` (e sementes) |

**T8.2.** As 35 telas conferidas pelo dono estão em
`data/saida/t82/ferramenta/conferencia_t82.json`, com o vídeo e o instante de cada uma em
`indice.json`. A tela 33 ainda não foi conferida.

**Marcas de técnica.** Os campos `regioes` dos ouros e da T8.2 (seção 2).

**Referências já gravadas.**

- Leituras das dobras: `data/saida/fase8/ger/ger*/<slug>.json`.
- Notas medidas: `data/saida/fase8/ger/tab/*.json` (`tab.avaliar_video`).

### 5.2 Unidades e métricas

**Casa** (frentes C, D e E, e qualquer frente que mexa no modelo):

- a unidade é a nota, contada pelo `tab.avaliar_video` (ouros) e pelo `t82_comparar.py` (T8.2);
- reporte por vídeo e por canal, sempre com denominador: notas no ouro, entregues, casadas, casa
  certa, inventadas e perdidas;
- reporte também **consertadas e quebradas** contra a referência.

**Técnica** (Frentes 0, A e B):

- **A unidade é a região marcada pelo dono.**
- **Casamento.** Uma nota prevista cai numa região se as duas condições valem:
  - a corda dela está em `cordas`;
  - o centro dela está em `x_quadro`, com folga de 0,5 passo.
- **Uma técnica de par** (h, p, slide, ligadura) casa se qualquer uma das duas notas do par cair
  na região. O gerador marca a de destino; o dono marca o arco inteiro.
- **Classes da régua**, a partir do rótulo do dono:

| classe da régua | rótulo do dono | saída da rede que conta |
| --- | --- | --- |
| hammer-on | `["h"]` | `h` |
| pull-off | `["p"]` | `p` |
| mordente | `["h", "p"]`, ou `obs` "mordente" | 3 ou mais notas com `h`/`p`/`orn` na região |
| prolongamento | `[]` com `obs` "ligadura/arco de prolongamento" | `lig` |
| slide | `["/"]`, `["\\"]`, `obs` "ligadura slide" | `/` ou `\` (o sentido conta à parte) |
| harmônico | `["harm"]` | `harm` |
| bend | `["bend"]` | `bend` |
| arpejo, rasgueado | `["arpejo"]`, `["rasg"]` | a rede não tem saída: conta como perdida |
| abafada | `["x"]` | classe `x` em `nao_notas` (não é técnica; reporte à parte) |
| fora da régua | figuras de ritmo, compasso, ritornelo, `bend release` | não entram; conte quantas são |

**Métricas obrigatórias, por classe e por fonte:**

1. marcas do dono;
2. **achadas**: alguma técnica prevista na região;
3. **certas**: a classe prevista é a do dono;
4. **técnicas previstas fora de qualquer região**: só nas telas onde as marcas forem completas
   (seção 10, item 4); nas outras, olhe uma amostra de 20 e diga quantas são símbolo de verdade.

Classe com menos de 10 marcas (harmônico 4, bend 5, mordente 9) é reportada, mas **não decide**
aceite.

### 5.3 Critérios de aceite comuns (CA)

Uma variante só é "aprovada" se cumprir **todos**:

- **CA1 — reprodução.** Antes de mexer em qualquer coisa, a worktree reproduz **exatamente**:
  - a T8.2 com o `final_s1_ger`: 1551/1557, 1566 entregues, 1573 no ouro;
  - o total das dobras do gerador novo, semente 1: 1747/1764, 1799 entregues, 35 inventadas, 10
    perdidas.

  Se não bater, pare e relate. A régua de técnica da Frente 0, depois de commitada, vira
  referência também.
- **CA2 — a casa não piora.** Toda mudança que toca o modelo, o recorte ou o produto mantém, nas
  dobras, precisão, revocação e casa dentro da amplitude das 3 sementes (seção 2). Na T8.2,
  inventadas + perdidas não pode subir mais de 3.
- **CA3 — ganho.** Cada frente tem o seu, definido na seção 7.
- **CA4 — sem um vídeo carregando o resultado.**
  - O ganho aparece em pelo menos 2 fontes (ouro ou canal).
  - Nenhuma fonte piora além da amplitude.
  - O Room 335 sozinho tem 177 das 415 marcas: reporte **também sem ele**.
- **CA5 — fora da amostra.**
  - Limiar ou peso se escolhe nos ouros e se mede na T8.2, ou o contrário, **declarado antes** no
    documento da rodada.
  - Nunca se ajusta olhando o conjunto de teste.
  - Os critérios desta seção estão congelados depois que o dono aprovar.
- **CA6 — determinismo.**
  - Pós-processamento: duas execuções dão resultado idêntico.
  - Treino: 3 sementes, média e amplitude, e o ganho tem de ser maior que a amplitude.
- **CA7 — olhar o caso.**
  - 10 casos olhados (5 consertados e 5 quebrados), com o caminho do recorte.
  - Afirmação sobre imagem sem o caminho da imagem não vale.
- **CA8 — gate.** `ruff check`, `ruff format --check` e `pytest` verdes **na worktree**.

---

## 6. Regras para quem trabalha numa worktree

### 6.1 A armadilha principal: `data/saida/` e `artefatos/` não estão no git

**O que falta numa worktree nova.** Ela tem o código e o `data/gold/`. Não tem:

- os pesos (`artefatos/`);
- o cache e os scripts de treino (`data/saida/n4/`);
- as leituras de referência, as telas da T8.2 e o áudio alinhado.

**Como montar.** Monte a cópia principal **só para leitura** e, para escrita, só as pastas da sua
frente:

```bash
WT=/caminho/da/sua/worktree
PRINCIPAL=/var/home/gabriel/Projects/chorinho-dataset
FRENTE=f0_tecnica   # f0_tecnica | fa_arco | fb_gerador | fc_rolagem | fd_som | fe_sondas
host-spawn -no-pty -cwd "$WT" podman run --rm --security-opt label=disable \
  -v "$WT":/app \
  -v "$PRINCIPAL/data/saida":/app/data/saida:ro \
  -v "$PRINCIPAL/data/saida/tab_frentes/$FRENTE":/app/data/saida/tab_frentes/$FRENTE \
  -v "$PRINCIPAL/artefatos":/app/artefatos:ro \
  -v "$PRINCIPAL/artefatos/tab_frentes/$FRENTE":/app/artefatos/tab_frentes/$FRENTE \
  -v /run/media/gabriel/3014CD4714CD1130/chorinho:/acervo:ro \
  -w /app docker.io/library/chorinho:dev bash -c "<comando>"
```

- **GPU** (só B2 e A2): acrescente `--device nvidia.com/gpu=all`.
- **Onde a sessão roda.** Se ela roda direto no host, sem distrobox, tire o
  `host-spawn -no-pty -cwd "$WT"`.
- **Confira as montagens antes de medir.** Dentro do container, `ls
  /app/artefatos/detector_tab_final_s1_ger` e `ls /app/data/saida/fase8/ger/tab` têm de listar
  arquivos. Se vierem vazios, a montagem está errada: **pare**.
- **O script de treino grava em `artefatos/detector_tab_v3ft_d*`**, que está só para leitura.
  Copie `data/saida/n4/treinar_ft.py` para a sua pasta e mude **só** o destino (para
  `artefatos/tab_frentes/<frente>/`). Registre o diff no documento da rodada.
- **Teste de unidade** não pode depender de `data/saida/` nem de `artefatos/`. O gate roda sem
  eles.
- **Aspas.** Comando com aspas aninhadas falha: escreva um `.py` na worktree e rode-o.
- **Gate.** O `ruff` precisa de `--no-cache` e o `pytest`, de `-p no:cacheprovider`, por causa
  da montagem.

### 6.2 Território de cada frente

| frente | pasta de saída (`tab/caminhos.py`) | prefixo de módulo e teste | rodadas | porta |
| --- | --- | --- | --- | --- |
| 0 | `TAB_FRENTE_0` → `tab_frentes/f0_tecnica/` | `tab/tecnica_regua*.py` | 0101–0109 | — |
| A | `TAB_FRENTE_A` → `tab_frentes/fa_arco/` | `tab/tecnica_arco*.py` | 0110–0129 | — |
| B | `TAB_FRENTE_B` → `tab_frentes/fb_gerador/` | `tab/gerador_*.py` (e `sintetico_sistema.py` só no branch) | 0130–0149 | — |
| C | `TAB_FRENTE_C` → `tab_frentes/fc_rolagem/` | `tab/rolagem_*.py` | 0150–0169 | 8111 |
| D | `TAB_FRENTE_D` → `tab_frentes/fd_som/` | `tab/som_casa_*.py` | 0170–0179 | — |
| E | `TAB_FRENTE_E` → `tab_frentes/fe_sondas/` | `tab/sonda_*.py` | 0180–0189 | — |

As portas 8098 e 8099 são das ferramentas do dono, e as de 8101 a 8104 são das frentes das mãos.

**A fazer pela sessão principal antes de abrir as worktrees:**

- criar as constantes `TAB_FRENTE_*` em `tab/caminhos.py`;
- criar as pastas em `data/saida/tab_frentes/` e `artefatos/tab_frentes/`.

### 6.3 O que é proibido

1. **Escrever fora da sua pasta**, inclusive nas pastas de outras frentes, em `fase8/`, `t82/` e
   `n4/`. A montagem só para leitura existe para isso.
2. **Editar `ESTADO.md`.** Ele é compartilhado e daria conflito entre worktrees. O "não repetir"
   vai no documento da rodada, e a sessão principal consolida no `ESTADO.md`.
3. **Editar arquivo de outra trilha**: `tab/maos_*`, `tab/audio_*`, `tab/partitura_*` e os testes
   delas. Importar e rodar é permitido.
4. **Trocar o modelo do produto** (`DETECTOR_PADRAO`) ou o recorte do painel no `main`. A
   integração é da sessão principal, **depois de remedir**.
5. **Gravar em `data/gold/`.** Rótulo só do dono, por leitura visual. A frente monta a folha ou a
   lista de telas, e a sessão principal leva ao dono.
6. **Ferramenta do dono.** Para testar a ferramenta de rótulo, use uma **cópia** do ouro, nunca o
   ouro vivo: ela grava a cada clique.
7. **Dependência nova sem o dono.** A imagem `chorinho:dev` tem `torch`, `numpy`, `opencv` e
   `ffmpeg`. Não tem `scipy`, `scikit-image`, Node.js, `alphaTab`, `PyGuitarPro`, `ultralytics`
   nem modelo de áudio. Seção 10.
8. **Copiar código GPL ou AGPL** para o repositório (`score_capture`, Ultralytics). Reimplemente a
   ideia e cite a fonte.
9. **GPU sem a trava.** No host, antes de treinar:
   - confira `data/saida/gpu.lock`; se ela existir e não for sua, espere;
   - grave a sua trava (`<frente>, <data>, <duração>`);
   - ao terminar, apague **só a sua**.
10. **Ler vídeo inteiro do HD externo** sem necessidade. É o gargalo de E/S: duas leituras longas
    ao mesmo tempo dobram o tempo das duas. Leia só os quadros de que precisa e registre quantos
    leu. A Frente C é a exceção: ela precisa de amostras densas, então leia 1 vídeo por vez.
11. **Commit em `main`.** Trabalhe no branch da worktree.

---

## 7. As frentes

Cada teste segue o mesmo molde: **Contexto**, **Hipótese**, **Como**, **Entradas**, **Saída**,
**Aceite**, **Reprova ou para**, **Pegadinhas e falsos positivos**.

---

### Frente 0 — Régua de técnica e o topo cortado

#### F0.1 — O que a rede acerta de técnica hoje

**Contexto.** A rede entrega técnica por nota desde a decisão 0010, sem nenhuma medida em tela
real. O dono marcou 415 regiões (seção 2).

**Hipótese.** Nenhuma: é medida de partida.

**Como.**

1. Escreva `tab/tecnica_regua.py`. Ele lê as regiões do dono e um JSON do produto (ou a leitura
   das telas da T8.2), casa como na seção 5.2 e grava a tabela por classe e por fonte.
2. Rode com o `final_s1_ger` em todas as fontes. Ele é honesto para técnica porque a técnica
   nunca foi supervisionada em tela real.
3. Repita nos ouros com os modelos das dobras, para mostrar que a conta não muda.
4. Monte a **matriz de confusão**: dono × rede, incluindo "nada".
5. Para cada perda, separe a causa:
   - (a) a rede não marcou nada na região;
   - (b) marcou a classe errada;
   - (c) a nota da região nem foi lida.
6. Recorte cada caso: o recorte vai para a pasta da frente, com o caminho na tabela.

**Entradas.** Os ouros, `conferencia_t82.json`, `indice.json` e os modelos da seção 5.1.

**Saída.** `TAB_FRENTE_0/regua_tecnica.json` e os recortes; rodada 0101.

**Aceite.**

- As contagens por fonte batem com a tabela da seção 2: 415 regiões.
- Duas execuções dão o mesmo resultado.
- Há 5 casos olhados por classe com 10 marcas ou mais.
- O documento diz, por classe, quanto da perda é (a), (b) e (c).

**Reprova ou para.** Se mais de 10 % das regiões casarem com mais de um par de notas
possível, a regra de casamento não serve. Pare e descreva.

**Pegadinhas e falsos positivos.**

- **Marca não é exaustiva.** Ausência de marca não prova ausência de símbolo. As técnicas
  previstas fora de região só contam onde o dono disser que marcou tudo (seção 10, item 4).
- **O dono marca o arco; a rede marca uma nota.** Um par certo pode cair "fora" por causa de uma
  folga mal escolhida. Escolha a folga nos ouros, declare-a e aplique-a igual na T8.2.
- **Abafada (`x`) não é técnica.** São 124 das 415. Se entrar na conta de técnica, ela infla o
  acerto: reporte à parte.
- **Ligadura que atravessa a troca de tela.** "Um número e vazio do outro lado" (regra do dono) é
  um prolongamento cuja outra nota está na tela seguinte. Não é falha de par.
- **Arco acima e arco abaixo** valem o mesmo (dono). Não separe por posição.
- **Símbolo lido como nota.** 3 das falhas da T8.2 são isso. Uma técnica "perdida" pode ter
  virado uma nota inventada: cruze com a régua de casa.

#### F0.2 — O arco da corda 1 sai do recorte?

**Contexto.** O dono avisou que algumas tablaturas cortam o topo e o arco da corda 1 some. O
recorte do produto (`painel.escolher_ou_mascara`) é a entrada da rede. A ferramenta de
conferência já ganhou folga de 1,5 passo acima da corda 1, mas o produto não.

**Hipótese.** Uma parte mensurável das marcas na corda 1 fica acima do recorte do produto.

**Como.**

1. Para cada região do dono que inclui a corda 1, e para cada símbolo marcado acima dela (arpejo,
   harmônico), compare a altura do símbolo no quadro com o topo do recorte do produto.
2. A altura do arco não está na marca. Meça-a no recorte: tinta entre a corda 1 e o topo, na
   faixa `x_quadro` da região.
3. Conte quantas ficam inteiras, cortadas ou fora.

**Saída.** `TAB_FRENTE_0/topo.json` e uma folha com os casos cortados; rodada 0102.

**Aceite.** O número, com o denominador e a folha.

**O que vem depois** não é desta frente:

- se 5 % ou mais das marcas da corda 1 estiverem cortadas, a sessão principal decide a folga no
  painel;
- mudar o recorte é mudar a entrada do modelo (`AGENTS.md`, regra 9): exige remedir a casa
  inteira (CA2).

**Pegadinhas.**

- **O recorte da ferramenta não é o do produto.** Meça no recorte do produto.
- **Texto acima da tab** (letra da música, nome de acorde, "let ring") pode parecer arco. Olhe.

---

### Frente A — O arco e a regra dos números

#### A1 — Classe da técnica pelos números

**Contexto.**

- O dono definiu a regra (`configs/simbolos.yaml`, `regra_do_arco_pelos_numeros`):
  - números iguais, ou um número e vazio do outro lado: prolongamento;
  - o primeiro maior que o segundo: pull-off;
  - o primeiro menor: hammer-on;
  - 3 números ou mais: mordente;
  - barra entre os números: slide.
- A pesquisa propõe o mesmo (§2): achar o conector e decidir pelos números.
- A rede hoje decide h, p ou ligadura **pela imagem**. A letra nem sempre está desenhada: o
  gerador já desenha legato só com o arco.

**Hipótese.** Boa parte dos erros de técnica é **classe** (h × p × ligadura), não detecção. Se a
rede achou um ligado, a regra acerta a classe.

**Como.**

1. Escreva `tab/tecnica_arco.py`, que recebe as notas do produto e devolve as notas com a técnica
   reclassificada. Ele não muda corda, casa nem x.
2. Para cada nota marcada pela rede com `h`, `p`, `lig` ou `orn`:
   - ache o par na mesma corda: a nota anterior e a seguinte até N passos (declare N antes, a
     partir dos ouros);
   - aplique a regra do dono;
   - 3 notas ou mais seguidas sob marcas de legato viram mordente.
3. Slide (`/` e `\`) fica como a rede disse. A regra só confirma que há duas notas.
4. Meça com a régua da F0.1, contra a referência F0.1.

**Saída.** `TAB_FRENTE_A/a1.json`; rodada 0110.

**Aceite.**

- Nas classes hammer-on + pull-off + prolongamento + mordente juntas, **consertadas − quebradas
  ≥ 8 regiões**.
- Nenhuma classe perde mais de 2 regiões.
- Há ganho em pelo menos 2 fontes (CA4).
- A casa fica **idêntica**: confira que corda, casa e x de todas as notas não mudam.

**Reprova ou para.** Se a F0.1 mostrar que a rede **acha** menos da metade das regiões de
legato, a A1 tem pouco a ganhar: relate e recomende A2 ou B.

**Pegadinhas e falsos positivos.**

- **Casa errada contamina a regra.** Um 8 lido no lugar de 0 vira pull-off falso. Relate quantas
  quebras vêm de casa errada; elas são erro da casa, não da regra.
- **Acorde.** Duas notas na mesma coluna em cordas diferentes não formam par. O par é sempre
  **na mesma corda**.
- **Arco entre cordas diferentes.** Pode aparecer no desenho, mas não é técnica de mão esquerda.
  Conte e deixe de fora.
- **Slide com arco** quer dizer "não tocar de novo" (`obs` do dono). Continua slide, não vira h
  ou p.
- **Harmônico ao lado** (`<12>`) não entra no par.
- **Bend** (`6b7`, `b9r8`) é lido hoje como várias notas. Não é legato: deixe fora da regra e
  conte.

#### A2 — O conector como objeto próprio (condicional)

**Só comece se** a F0.1 mostrar que a perda principal é (a), a rede não marca nada onde há arco,
e a A1 não resolver.

- **Ideia** (§2, DeepScoresV2): o arco e o traço de slide são longos, finos e curvos. Uma caixa
  comum engole os algarismos.
- **Como.** O gerador já sabe onde desenhou cada arco e cada traço. Uma cabeça nova da rede
  (máscara do conector por corda, ou extremos esquerdo e direito) aprende isso, e a A1 classifica.
- **Sem Ultralytics** (AGPL).
- **Custo.** É treino: 3 dobras × 3 sementes, com CA2 e CA6.

---

### Frente B — Gerador: AlphaTab e arquivos Guitar Pro

#### B1 — Sonda: o modelo atual num renderizador que ele nunca viu

**Contexto.**

- §3: o AlphaTab renderiza Guitar Pro e AlphaTex sem tela (Node.js) e sabe a posição de cada
  nota.
- Nosso gerador desenha com as fontes Liberation e um estilo próprio.
- O que mais rendeu na história do projeto foi **cobertura do gerador**.

**Hipótese.** Se o modelo atual erra no AlphaTab bem mais do que nas telas reais, o estilo do
AlphaTab traz algo que o nosso gerador não tem. Se não erra, a B2 não vale o custo.

**Como.**

1. Confira primeiro a fonte: o AlphaTab dá a caixa de cada nota renderizada
   (`boundsLookup` ou equivalente)? E a de cada técnica? Se não der, **pare**: sem rótulo exato a
   ideia não serve.
2. Escreva 20 trechos em AlphaTex à mão, com as técnicas da régua (h, p, slide, ligadura,
   harmônico, bend, arpejo, rasgueado) e casas de 0 a 19, **pelo menos 30 % de dois algarismos**.
   Não use música de terceiros nesta sonda.
3. Renderize, aplique as degradações de vídeo que o nosso gerador já usa e rode o
   `final_s1_ger`.
4. Meça casa e técnica contra o rótulo do AlphaTab.

**Saída.** `TAB_FRENTE_B/b1/`; rodada 0130.

**Aceite (sonda).** A sonda não tem aceite: reporte o número. A **B2 só abre** se uma das duas
condições valer:

- casa abaixo de 0,98 no AlphaTab;
- uma classe de técnica da régua com acerto 0,2 abaixo do acerto dela nas marcas do dono (F0.1).

**Pegadinhas.**

- **AlphaTab limpo demais.** Sem degradação, o modelo pode ir bem por ser fácil, não por
  generalizar.
- **Estilo padrão não é estilo de canal.** O AlphaTab tem um visual; os canais usam Guitar Pro,
  Sibelius, MuseScore e editores próprios. Um renderizador novo é **uma** fonte de estilo, não
  todas.

#### B2 — AlphaTab no treino (condicional, GPU)

- **Como.** Misture sistemas do AlphaTab ao sintético atual, numa fração declarada antes (por
  exemplo 20 %). Depois faça o ajuste fino das dobras 2–4 × 3 sementes, como em
  `data/saida/fase8/ger/` (regua_ger.py, tabela.py), mas com o seu destino.
- **Fonte de música:** DadaGP ou arquivos próprios, conforme o dono decidir (seção 10). Para
  injetar técnica com PyGuitarPro (§3), a dependência é do dono.
- **Aceite.**
  - CA2 (casa não piora), CA6 (3 sementes).
  - Em técnica: ganho maior que a amplitude das sementes em pelo menos 2 classes com 10 marcas ou
    mais, e nenhuma classe pior.
- **Reprova.** Ganho em técnica com perda na casa é **troca, não ganho** (rodada 22): não adote.

**Pegadinhas.**

- **Distribuição das casas.** Música real tem poucas casas altas, e o nosso gerador sorteia cerca
  de 33 % de dois algarismos de propósito. Misturar música real pode **diminuir** os dois
  algarismos no treino e piorar justamente o resíduo da casa. Meça a fração antes e depois.
- **Licença do corpus.** O DadaGP é para pesquisa, com acesso pedido, e os arquivos Guitar Pro
  têm direitos das músicas. Decisão do dono.
- **Tempo de GPU.** São 9 treinos de cerca de 20 min, com a GPU dividida com outros agentes.
  Respeite a trava.

---

### Frente C — Tablatura que rola na tela

#### C1 — Costura ancorada nas barras e mapa x → t

**Contexto.**

- T8.4 do plano: o deslocamento por amostra (`phaseCorrelate`), acumulado, vira uma coordenada
  "da partitura", `x_partitura = x_quadro + deslocamento(t)`.
- §4: o `score_capture` costura usando as **barras de compasso** como âncora. É GPL-3.0: use a
  ideia, não o código.
- A pesquisa lembra que, se a velocidade varia, o mapa x → t não é linear: precisa de um mapa
  **monotônico por amostra**.

**Hipótese.** Com o deslocamento por amostra ancorado nas barras, dá para montar o panorama do
sistema inteiro e o instante de cada coluna, sem duplicar nem perder compasso.

**Como.**

1. **Escolha 3 vídeos rolantes** do censo (`mr. tabs`, `leonardo ramos`, `kenneth acoustic`) e
   **confirme no olho** que rolam: a classificação nunca foi conferida. Guarde 4 quadros de cada
   como prova.
2. **Meça o deslocamento** entre amostras consecutivas da faixa do painel por dois caminhos:
   - `phaseCorrelate` puro;
   - ancorado nas barras (o x das barras casado entre quadros).

   Compare com 20 pares medidos à mão por vídeo.
3. **Monte o panorama** e o mapa `x_partitura → t`. O instante de uma coluna é quando ela passa
   pelo marcador fixo da tela (na rolagem, quem anda é a tab).
4. **Leia o panorama** com o detector, em janelas do tamanho de um sistema, com sobreposição.
   Junte as notas pelo `x_partitura` sem duplicar.
5. **Peça ao dono o gabarito** de 1 vídeo rolante (seção 10), na ferramenta do ouro, com o
   panorama em telas. Teste antes numa cópia (6.3, item 6).

**Saída.** `TAB_FRENTE_C/`; rodadas 0150 em diante; porta 8111 para servir o material.

**Aceite.**

- **Deslocamento:** erro mediano de 1 px ou menos contra os pares medidos à mão, nos 3 vídeos.
- **Panorama:** nenhum compasso duplicado ou faltando nos 3 vídeos, olhado e com a folha anexada.
- **No gabarito do dono:**
  - casa + corda 0,99 ou mais nas casadas;
  - revocação 0,98 ou mais;
  - inventadas 2 % ou menos;
  - instante na coluna certa em 0,95 ou mais das colunas, com o mesmo critério da régua de tempo
    da fase 5.
- **Os 8 ouros paginados ficam idênticos.** O caminho novo só entra com `modo = rolante`.

**Reprova ou para.** Se o deslocamento não chegar a 1 px nem com a âncora nas barras, pare antes
de montar o panorama e descreva os casos.

**Pegadinhas e falsos positivos.**

- **Período da música.** Compassos repetidos são iguais na imagem, e o `phaseCorrelate` pode
  casar com o compasso vizinho. O erro é exatamente um compasso, e a soma parece certa.
  Confira a continuidade (o deslocamento entre amostras próximas é pequeno).
- **Coisas paradas na faixa.** Marcador, mão, logo e legenda sobre a tablatura puxam o
  deslocamento para zero. Mascare o que não anda.
- **Rolagem e página no mesmo vídeo.** A introdução pode ser paginada e o resto rolar. O `modo`
  hoje é por vídeo: meça por trecho.
- **Velocidade que muda e pausa** (o professor para o Guitar Pro). O mapa tem de ser monotônico,
  com degraus.
- **Rolagem vertical** (sistemas empilhados) é outro problema. Conte quantos são e deixe de fora.
- **AV1** (44 % do acervo) só decodifica pelo `ffmpeg` do leitor do projeto. Não use o
  `cv2.VideoCapture` direto.

---

### Frente D — O som confere a casa

#### D1 — Altura esperada contra o espectro, nota a nota

**Contexto.**

- O alarme de leitura do áudio (rodada 2011) funciona **por exibição**.
- A pesquisa (§6) propõe a conferência **por nota**: corda + casa dão a altura MIDI, que o som
  confirma ou desmente.
- Os erros que sobram têm assinatura de altura:
  - "1" lido como 4: +3 semitons;
  - 10 lido como 1 + 0: duas notas inventadas;
  - 12 perdido: uma altura que soa sem nota.

**Hipótese.** No instante do som de cada coluna, a energia na altura lida separa as notas certas
das erradas. E a energia numa altura **sem nota** acusa uma perdida.

**Como.**

1. Use os vídeos que já têm áudio alinhado pela trilha do áudio (`data/saida/` da trilha;
   confira a lista). Os ouros com alinhamento são a base de ajuste.
2. Use STFT ou CQT feitas com `numpy`: sem dependência nova. Para cada nota, meça a energia na
   fundamental e nos 2 primeiros parciais, contra a mediana da janela.
3. Escolha o limiar nos ouros e **congele**. Meça nos vídeos da T8.2 que tiverem áudio alinhado,
   ou alinhe-os com a ferramenta da trilha áudio, sem editar o código dela.
4. Para cada nota sinalizada, diga se é erro de verdade (régua de casa) e olhe 10.

**Saída.** `TAB_FRENTE_D/d1.json`; rodada 0170.

**Aceite**, no conjunto de teste, com o limiar congelado:

- precisão do alarme 0,5 ou mais (metade das notas sinalizadas são erro de verdade);
- revocação 0,4 ou mais dos erros de casa + inventadas;
- alarme falso em 1 % ou menos das notas certas.

**Reprova ou para.** Se nos ouros a precisão ficar abaixo de 0,3, o sinal simples não serve:
relate e diga se a D2 vale.

**Pegadinhas e falsos positivos.**

- **O alinhador usa as alturas da tab** para casar colunas e ataques. O instante é aceitável, mas
  o alinhamento pode ter sido puxado pela nota errada. Relate quantas notas sinalizadas estão
  em trechos de alinhamento fraco.
- **O professor não toca o que está na tela**: fala por cima, toca outra versão, repete trecho,
  ornamenta. A tela parada com o professor explicando não tem som de nota.
- **Harmônico** soa uma oitava ou mais acima. **Capotraste e afinação baixada** deslocam tudo.
  Confira a afinação do vídeo antes (`tab/afinacao.py` não foi aferido).
- **Nylon e reverberação**: parciais fracos e notas anteriores ainda soando. A energia de uma nota
  presa pode vir da nota anterior na mesma altura.
- **Ligado e slide não têm ataque.** A energia existe, mas o pico de ataque não.
- **Abafada (`x`) não tem altura.** Tire da conta.
- **O marcador vem antes do som**: de 165 a 275 ms no `sky guitar`, variando de 60 a 324 ms. Use o
  instante do som, não o do marcador.

#### D2 — Modelo pronto de transcrição (condicional)

- **Só comece** se a D1 aprovar, ou se reprovar por falta de resolução de altura (e não por
  alinhamento).
- **Candidatos** (§6): o modelo do GAPS, treinado em violão de nylon, e o FretNet.
- **Antes de tudo:** confira se os pesos existem, a licença (a pesquisa e a página do GAPS
  discordam) e o uso de GPU.
- **Dependência do dono.**
- **Aceite:** o da D1, contra a D1.

---

### Frente E — Sondas de modelos prontos (expectativa baixa)

#### E1 — `guitar-tab-omr` como segunda leitura no resíduo

- **Antes:** confira a licença dos pesos no Hugging Face (o README não declara). Sem licença
  clara, **pare**.
- **Como.**
  1. Recorte o sistema das 35 telas da T8.2 no formato do modelo (1200 × 224, cinza).
  2. Rode o modelo e converta os tokens em corda e casa.
  3. Pareie com as nossas notas **pela ordem na corda**: os tokens não trazem x.
  4. Meça **só** onde importa: nas 31 falhas e em 100 notas certas sorteadas com semente fixa.
- **Aceite**, para virar candidata a segunda leitura:
  - acerta a casa em pelo menos 1/3 das nossas falhas de dois algarismos;
  - discorda em 1 % ou menos das notas certas.
- **Pegadinhas.**
  - O número dele é de exportação digital limpa: 76,5 % de sistemas exatos no próprio dado.
  - Um modelo de sequência inventa nota com confiança.
  - Sem x, o pareamento erra em acordes. Pareie por (coluna, corda) quando a ordem for ambígua e
    relate quantos pares ficaram ambíguos.

#### E2 — Máscara de ligadura do `homr` em recorte de tablatura

- **Antes:** confira onde o `homr` está instalado (trilha partitura) e se ele expõe a máscara de
  ligadura. Não edite `tab/partitura_*`.
- **Como.** Rode em 20 telas com arcos marcados pelo dono. Conte os arcos que acendem e as
  marcas falsas por tela.
- **Aceite**, para virar entrada da A2: 70 % dos arcos do dono ou mais, com 1 marca falsa por tela
  ou menos.
- **Pegadinhas.**
  - O `homr` foi treinado em pauta de 5 linhas; a tab tem 6 e números no lugar de cabeças.
  - Acender perto da corda não basta: o arco tem de casar com o par de números certo.

---

## 8. Pegadinhas que valem para todas as frentes

1. **Número da pesquisa não é meta.**
   - O `guitar-tab-omr` aparece com SER 0,852 % na pesquisa e 2,4 % no README.
   - A licença do GAPS aparece de dois jeitos.
   - Nenhum número de `tablatura.md` serve de critério de aceite nem de argumento de que "deve
     funcionar".
2. **Referência não conferida não existe.** Só três itens foram conferidos (seção 3.4). Confira o
   resto antes de depender.
3. **O recorte é parte da medida** (`AGENTS.md`, regra 9). Mudou painel, folga, escala ou
   binarização? Remeça a referência com a mudança antes de comparar.
4. **Ouro parcial.** No End of Beginning e no Room 335, só algumas páginas foram conferidas. Nota
   e técnica fora delas não contam: nem como acerto, nem como invenção.
5. **Quem viu o quê.**
   - O modelo do produto viu as notas dos 8 ouros: **casa** nos ouros só com o modelo da dobra.
   - A **técnica** nunca foi supervisionada em tela real. Mesmo assim, declare qual modelo mediu.
6. **Uma semente é ruído.** A mesma semente já variou 0,052 sem determinismo. Treino sempre com 3
   sementes, média e amplitude.
7. **Um vídeo carregando.** O Room 335 tem 43 % das marcas de técnica e 22 das 35 inventadas.
   Reporte com e sem ele.
8. **Troca não é ganho.** Melhorar a técnica e piorar a casa, ou melhorar um canal e piorar outro,
   não se adota (rodada 22).
9. **Afirmação sobre imagem precisa da imagem.** Toda frase sobre o que aparece numa tela vem com
   o caminho do recorte. O revisor vai abrir.
10. **Símbolo não se descarta** (`AGENTS.md`). Uma frente que classifica técnica guarda a região
    crua (corda, x, recorte) junto da classe. Perder o símbolo é o único erro inaceitável.
11. **Medida interna não é validação.** Perda do treino, confiança da rede e consistência entre
    sementes dizem que o método é estável, não que está certo. Valem o gabarito do dono, a régua
    ou o olho.

---

## 9. O que cada frente entrega

1. **Código** com o prefixo da frente e testes de unidade sem `data/saida/`, sem `artefatos/` e
   sem acervo. O gate tem de estar verde na worktree.
2. **Saídas** só na pasta da frente. Pesos só em `artefatos/tab_frentes/<frente>/`, com comando e
   semente.
3. **Documento de rodada** na faixa da frente, com estas partes:
   - a pergunta;
   - limiares e pesos a priori, escritos antes da medida;
   - a checagem da fonte (existe, licença, número);
   - a tabela no formato da seção 5.2, com consertadas e quebradas;
   - os 10 casos olhados, com as imagens;
   - o que deu errado e o "não repetir".
4. **Commit no branch da worktree**, com o número medido na mensagem. Não commitar em `main`.
5. **Resumo para o dono** em português, curto:
   - o que a frente acha, conserta ou quebra, e se passou nos critérios;
   - o que ela **não** prova.

A sessão principal remede o número antes de integrar e consolida o `ESTADO.md`.

---

## 10. Decisões do dono (pendentes)

1. **Dependências novas.** Recomendação: liberar só o que a sonda precisa e decidir o resto pelo
   resultado.

| dependência | frente | licença | recomendação |
| --- | --- | --- | --- |
| Node.js + `alphaTab` | B1, B2 | MPL-2.0 | liberar para a B1 (sonda) |
| `PyGuitarPro` | B2 | LGPL-3.0 | só se a B2 abrir |
| pesos do `guitar-tab-omr` | E1 | não declarada | só com licença clara |
| modelo do GAPS ou FretNet | D2 | a conferir | só se a D1 pedir |
| Ultralytics (YOLO) | — | AGPL-3.0 | não usar |

2. **Música para o gerador (B2).** DadaGP (o dono pede o acesso; já aprovado como fonte na
   trilha das mãos) ou arquivos próprios?
3. **Gabarito de 1 vídeo rolante (C1).** Cerca de 30–60 min do dono, na ferramenta do ouro. A
   frente escolhe o vídeo e prepara o material.
4. **As marcas de símbolo estão completas?**
   - Nas 24 telas da T8.2 e nas páginas conferidas dos 4 ouros, o dono marcou **todos** os
     símbolos ou só alguns?
   - Sem marcas completas, não dá para medir técnica inventada (seção 5.2, métrica 4).
5. **ASCII continua fora** (decisão 0009)?
6. **Critérios de aceite.** Os da seção 5.3 e os de cada frente ficam **congelados** depois de
   aprovados. Mudar um limiar depois de ver o resultado invalida a frente.

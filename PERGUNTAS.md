# PERGUNTAS.md — levantamento de requisitos

**Para o dono do projeto.** Responda o que puder; onde não souber, escreva "não sei"
(é resposta válida e eu decido por medição). Onde eu tenho opinião, marquei com **⭐** —
se você concordar com a ⭐, basta escrever **"ok"** na linha.

Objetivo: **não interromper o goal no meio**. Tudo que eu precisaria perguntar depois
está aqui.

Como responder (escolha o jeito que for mais rápido):

- escreva direto neste arquivo e me avise; **ou**
- responda só as que têm ⭐ e as que você discordar; **ou**
- responda por bloco (A, B, C...).

---

## Respostas já recebidas (2026-10-08, 2ª rodada)

| pergunta | resposta |
| --- | --- |
| **A1** ambiente | **Docker + Compose com GPU** (feito e verificado: `cuda True` no container) |
| **B1** versionamento | **`git init`**, ignorando `.venv` e `parts/` (feito) |
| **B2** `parts/` | derivado de B1: só o índice, não os 656 MB de clipe |
| **B3** os 65 docs | **consolidar num único `HISTORICO.md`** (feito, com as 11 contradições registradas) |
| **B4** estado | **unificar em `ESTADO.md`** e apagar o resumo (feito) |
| **B5** layout | **pacote flat `tab/` na raiz** (feito — sem `src/`) |
| **D3** licença | pode **treinar e validar** com frames reais e **publicar recortes** |
| **F1** técnicas | **não descartar o símbolo**: guardar o glifo cru e dar o significado depois, por canal |
| **J4** prioridade | seguir minhas recomendações, na direção do objetivo |
| **noite** | **inventariar o acervo novo + ampliar o gabarito + símbolos/técnicas** |
| **gabarito** | eu posso rotular glifos novos **lendo as montagens**, salvando cada PNG para auditoria |
| **HD** | varrer tudo durante o download e **revarrer no fim** |
| **saída** | **JSON no projeto**, frames/imagens temporárias no **HD** |
| **áudio** | **autorizado** instalar librosa/aubio e usar áudio como fonte de tempo |
| **partitura** | **fora de escopo agora**, mas **marcar quais vídeos têm** |
| **canais prioritários** | **sky guitar, guitar dell'arte, cifra club, iwaki** (mais os do gabarito atual) |
| **autonomia** | **decidir, registrar e seguir** durante a noite |
| **janela** | até ~8h da manhã |

### Respostas da 3ª rodada (2026-10-08, antes da noite)

| pergunta | resposta |
| --- | --- |
| **E5** instrumentos | **Violão 6 cordas**, mas **a afinação varia**: procurar no **começo do vídeo** um texto de *tuning* / afinação — às vezes aparece afinação diferente (ou "standard") escrita na tela |
| **E6** afinação | **há variação (drop D, DADGAD) e/ou capotraste** |
| **J5** vídeo de ouro | não tem um específico; **`sky guitar` tem as melhores tablaturas e vídeos explicativos** |
| **J1** MVP | **um vídeo inteiro correto já serve** (corda + casa + tempo, sem nota inventada) |
| **F8** ornamentos | **sim, aparecem** (sobretudo nos eruditos) |
| **G2** tempo | **só o onset** |
| **extra** no JSON | **confiança por nota**, **símbolo cru** (confirmado), **técnicas**, e **nomes de acorde se estiverem no vídeo** |

#### O formato de saída passa a ser MusicXML

O dono do projeto entregou o esqueleto desejado: `score-partwise`, versão **4.0**,
`part-name` "Guitarra (Tab)", `clef` **TAB linha 5**, `staff-details` com
`staff-lines: 6` e `staff-tuning` por linha, e cada `note` com
`notations/technical/{string, fret}` — mais `duration`, `voice` e `type`.

Consequências, que passam a valer:

1. **`duration` tem de ser inferida, não medida.** Só medimos **onset** (G2). A duração
   de uma nota passa a ser o **intervalo até o próximo onset**, e isso precisa estar
   declarado no arquivo/relatório — não é duração medida;
2. **precisa de BPM/`divisions`** para converter segundos em ticks do MusicXML. O
   andamento já sai da mediana entre onsets; onde não houver, o exportador tem de
   declarar a hipótese em vez de inventar;
3. **`staff-tuning` exige a afinação**, que agora é item de medição: procurar o texto de
   *tuning*/afinação no começo do vídeo e registrar `standard`/`drop D`/… por vídeo;
4. **técnicas** entram como `notations/technical` (`hammer-on`, `pull-off`, `slide`,
   `harmonic`, `bend`, …), o que dá destino natural ao mapa de símbolos por canal;
5. **nomes de acorde** (se visíveis) podem ir como `harmony`.

Isto vira decisão registrada em `docs/decisoes/`.

> "Praticamente todos os vídeos do canal contém tablatura em algum momento do vídeo,
> novamente são vários formatos, tipos, cores, marcadores diferentes e além disso eles
> **aparecem ou desaparecem em certos momentos** da tela do vídeo."

Consequências de desenho, que passam a valer:

1. **A tablatura não está o tempo todo na tela.** O que existe é um conjunto de
   **intervalos de presença** por vídeo, não "o painel do vídeo". A varredura tem de
   medir presença **ao longo do tempo** e devolver intervalos, não um recorte único;
2. **o formato pode mudar dentro do mesmo vídeo** (tema claro/escuro, cor de voz,
   marcador por faixa ou por cor). Portanto a decisão é **por trecho**, não por canal;
3. "tem tablatura" é propriedade do **vídeo em algum momento**, não de todo quadro —
   inventário que lê 1 quadro por vídeo **subestima** a cobertura.

Isto muda a pergunta **D2** (prioridade de canais) e a **G** (tempo), e vira decisão
registrada em `docs/decisoes/`.

---

## A. Ambiente e execução

**Contexto:** o `AGENTS.md` que estava aqui mandava rodar tudo em Docker. **Esse
Dockerfile não existe** — era um template de outro projeto. A realidade é que todo o
trabalho até agora rodou no `.venv` do host, que é o único lugar com CUDA funcionando
(RTX 3060 Ti, torch 2.14.1+cu130, CUDA ativa).

- **A1.** Execução continua no **`.venv` do host** ⭐, ou você quer um **Compose com
  GPU** (isolamento, mas exige `nvidia-container-toolkit` e mais setup)?
  → resposta: ____
- **A2.** O daemon do Docker já está rodando (tem outro projeto nele). Posso usar
  Docker nesta máquina, ou prefere que eu **não mexa**? → ____
- **A3.** Deixo o `.venv` na raiz do projeto mesmo (5,8 GB)? → ____
- **A4.** Onde guardar **modelos treinados e derivados**? O `/var/home` tem 92 GB
  livres e o HD externo tem 725 GB livres. Sugestão: derivados no HD, modelo no
  projeto (`artefatos/`). Concorda? → ____
- **A5.** Posso instalar **`ruff` e `pytest`** no venv (para o lint/teste virar gate de
  verdade)? Posso usar o **`ffmpeg` do host**? → ____
- **A6.** Há **limite de tempo/uso da GPU** que eu deva respeitar (você usa a máquina
  para outra coisa)? → ____

## B. Versionamento e organização

**Contexto: este diretório NÃO é um repositório git.** Foram 65 rodadas de trabalho sem
nenhum versionamento — se eu tivesse quebrado algo, não havia como voltar.

- **B1.** Faço **`git init`** + commit inicial de tudo (exceto `.venv`)? ⭐ → ____
- **B2.** Versionar `parts/` (656 MB de clipes) ou ignorar? Sugestão: versionar só o
  **índice** (nomes + o que cada clipe contém), não o vídeo. → ____
- **B3.** Os **65 documentos** de rodada em `docs/`: (a) manter todos, movidos para
  `docs/rodadas/` ⭐; (b) consolidar num `HISTORICO.md` único; (c) apagar? → ____
- **B4.** `ESTADO.md` e `RESUMO_PAUSA.md` **se contradizem** (0,851 vs 0,892 — o
  `ESTADO.md` está velho). Unifico num só `ESTADO.md` e apago o resumo? ⭐ → ____
- **B5.** Layout: (a) **um pacote flat na raiz, `tab/`** ⭐; (b) manter `tools/` como
  está e só arrumar o resto (menos mudança); (c) outro nome que você prefira
  (`motor/`, `transcricao/`...). → ____
- **B6.** Nomes de código: **manter português** (`binarizar`, `achar_cordas`) ⭐, ou
  migrar para inglês? → ____
- **B7.** Documentos e comentários em **português** ⭐? → ____

## C. Produto e objetivo

- **C1.** O que significa **"pronto"** para você? (descreva o dia em que o projeto está
  terminado e você está usando) → ____
- **C2.** Formato de saída: **um JSON por vídeo** ⭐, um por música, ou um banco único
  (sqlite/parquet) com tudo? → ____
- **C3.** Precisa exportar **MusicXML / MIDI / Guitar Pro** para tocar em outro
  programa, ou o JSON basta? → ____
- **C4.** Precisa **tocar junto com o vídeo** (abrir o vídeo e a nota acender no tempo
  certo), ou só o dado estruturado? → ____
- **C5.** Quem consome esse JSON depois — um app seu, outro modelo, ou você lendo? → ____
- **C6.** Volume: transcrever os **3.781 vídeos inteiros**, ou só os **trechos onde
  aparece tablatura**? → ____
- **C7.** Interface: **linha de comando + processamento em lote** ⭐, ou você quer uma
  **tela de revisão** para conferir/corrigir? → ____

## D. Acervo

- **D1.** O acervo está fechado ou você ainda vai baixar mais vídeos? → ____
- **D2.** Prioridade entre os 13 canais (`cifra club`, `guitar dell'arte`, `iwaki`,
  `paolo d'angelo`, `raman korshun`, `serge kottelat`, `shin izumi`, `sky guitar`,
  `tv cifras`, `tv on guitar`, `violaodecria`, `ギタロー ⧸ guitarous`, `derived`).
  Quais os **3 que mais importam**? → ____
- **D3.** Licença: os vídeos são de terceiros. Posso (a) usar **frames reais** para
  treinar e validar; (b) **publicar** resultados/recortes? → ____
- **D4.** Posso **copiar recortes** para dentro do projeto, ou mantenho só ponteiros
  para o HD externo? → ____
- **D5.** Os 18 clipes de `parts/` representam bem o acervo? Posso ampliar a amostra? → ____
- **D6.** Quantos vídeos têm **partitura de 5 linhas**? Isso entra no escopo ou é
  assunto separado? → ____
- **D7.** Canais eruditos (`guitar dell'arte`, `serge kottelat`) são prioridade ou
  podem ficar para depois? → ____

## E. Música e escopo musical

- **E1.** **Só tablatura**, ou partitura também (exige um OMR separado)? → ____
- **E2.** **Tablatura em texto ASCII** (estilo Ultimate Guitar) entra? → ____
- **E3.** Os **nomes de acorde** no topo da cifra (`C`, `Am7`, `G/B`) entram na
  transcrição? → ____
- **E4.** **Cifra e letra** da música entram? → ____
- **E5.** Instrumentos: **violão 6 cordas** ⭐, ou também 7 cordas / cavaquinho /
  baixo / outros? → ____
- **E6.** Afinação: sempre **padrão (EADGBE)**, ou preciso registrar variações
  (drop D, DADGAD)? → ____
- **E7.** **Capotraste** deve ser registrado? → ____
- **E8.** **Mão direita** (dedilhado, palhetada, qual dedo) interessa? → ____

## F. Símbolos e técnicas

**Contexto:** hoje o modelo lê **o número** e **descarta o símbolo em volta**. Um `7`
com barra de slide vira `{"casa": "7"}`, sem registrar o slide. Isso é a maior lacuna
conhecida — e você mesmo avisou que **o símbolo muda de canal para canal**.

- **F1.** Quais técnicas **importam** (marque todas): ligado (`h`/`p`) · slide
  (`/` `\`) · harmônico (`<n>`, losango, `NH`) · nota presa/ligada (`(6)`) · bend ·
  vibrato · trêmolo · palm mute · nota abafada (`x`) · tapping (`T`) · slide de
  chegada/saída · outra: ____
- **F2.** No JSON: guardo **nome canônico + símbolo cru como está na tela**
  (`"tecnica": "hammer_on", "simbolo": "h"`) ⭐, só o canônico, ou só o cru? → ____
- **F3.** Confirmo que o **mesmo símbolo pode significar coisas diferentes em canais
  diferentes**, e por isso preciso de um **mapa por canal** (`configs/simbolos.yaml`)?
  → ____
- **F4.** Símbolo desconhecido: guardar **cru e marcar como não mapeado** ⭐, ignorar
  em silêncio, ou parar e te avisar? → ____
- **F5.** Confirma: **`(6)` = nota ligada/presa** (ligada, não atacada de novo)? → ____
- **F6.** Confirma: **`<7>` = harmônico**? → ____
- **F7.** Confirma: **`/` = slide subindo**, **`\` = slide descendo**? → ____
- **F8.** **Trêmolo e ornamentos eruditos** aparecem no seu acervo? → ____
- **F9.** **`x` (abafada)** e **`T` (tapping)** te interessam? → ____
- **F10.** Falta alguma técnica que você vê nos vídeos e eu não listei? → ____

## G. Tempo e execução

**Contexto:** achei **dois mecanismos** de marcador — faixa vertical que passa
(`sky guitar`) e algarismo que **fica laranja** (`cifra club`, cumulativo: mede-se o
**onset**, não a duração). Parte do acervo **não tem marcador nenhum**.

- **G1.** Precisão exigida no tempo: **1 quadro (33 ms)** ⭐, 0,1 s, 0,5 s, ou "tanto
  faz"? → ____
- **G2.** Basta o **onset** (quando a nota é atacada) ⭐, ou precisa **duração** também
  (exige áudio)? → ____
- **G3.** Vídeos **sem marcador**: aceito extrair o tempo **do áudio**
  (librosa/aubio) ⭐, deixo sem tempo, ou você marca à mão? → ____
- **G4.** "Tempo do trecho" é a **minutagem dentro do vídeo** ⭐ ou o **tempo musical**
  (batida 1, 2, 3...)? → ____
- **G5.** **BPM/andamento** (já sai hoje) — você usa? → ____
- **G6.** **Compasso** (já sai hoje) — você usa? → ____
- **G7.** Vídeo de aula tem fala antes/depois: o tempo é **absoluto do vídeo** ⭐ ou
  relativo ao trecho? → ____
- **G8.** Se a música **repete o mesmo trecho** várias vezes no vídeo: uma entrada por
  passagem ⭐, ou deduplicar? → ____

## H. Avaliação e qualidade

- **H1.** Métrica oficial: acerto **glifo a glifo** (o que meço hoje) ⭐, acerto **por
  nota com tempo**, ou **música inteira**? → ____
- **H2.** Qual número te faz dizer "serve"? (hoje: 0,892 em 96 glifos) → ____
- **H3.** Tolerância de tempo aceitável por nota: ± ____ ms
- **H4.** Você vai **validar à mão**? Quanto tempo por semana pode dedicar? → ____
- **H5.** Quer **revisão humana assistida** — o JSON marca o que está incerto para
  você conferir só isso? ⭐ → ____
- **H6.** Campo de **confiança por nota** no JSON te interessa? → ____
- **H7.** Quantos vídeos precisam sair certos antes de você considerar que dá para
  rodar em escala? → ____

## I. Modelo e ML

- **I1.** Posso **baixar pesos de terceiros** (HuggingFace)? Algum limite de tamanho
  ou de licença? → ____
- **I2.** Fico no **caminho leve (CNN de ~74 mil parâmetros)** ⭐, ou você quer que eu
  tente um **fine-tune de VLM** também? → ____
- **I3.** Precisa rodar **sem GPU** depois (CPU)? → ____
- **I4.** Licença do modelo precisa ser **permissiva** (MIT/Apache) para você
  distribuir? → ____
- **I5.** Treino **só em dado sintético** ⭐, ou posso usar **frames reais** como
  treino também (semiautomático)? → ____
- **I6.** Orçamento de GPU por rodada de treino: minutos? horas? → ____
- **I7.** **OMR de partitura** (5 linhas) entra em algum momento do projeto? → ____

## J. Prioridades e regras do jogo

- **J1.** Qual o **MVP** que já te serve? (o menor resultado que você usaria amanhã)
  → ____
- **J2.** Urgência: tem prazo, ou é projeto de fundo? → ____
- **J3.** O que **mais te incomoda** hoje no resultado? → ____
- **J4.** Onde gasto as próximas rodadas: **cobertura** (mais canais e casas 8–24) ·
  **profundidade** (símbolos/técnicas) · **tempo** (áudio para os sem marcador)?
  → ____
- **J5.** Existe um vídeo **"ouro"** — aquele que, se sair perfeito, prova que o
  projeto funcionou? (cole o nome/ID) → ____
- **J6.** Você quer **relatório a cada rodada** ou prefere só o resultado no fim? → ____
- **J7.** **Deal-breakers** — o que não pode acontecer de jeito nenhum? (perder dados,
  escrever no acervo, publicar algo, demorar demais...) → ____

---

## Respostas rápidas

Se preferir, responda só esta linha — eu preencho o resto por medição e marco o que
ficou como suposição:

```
A1=host  A5=sim/sim  A6=____  B1=sim  B2=ignorar  B3=a  B4=sim  B5=a  B6=pt  B7=pt
C2=json-por-video  C3=____  C6=____  C7=cli  D2=____,____,____  D3=____
E1=____  E5=6-cordas  F1=____  F2=ambos  F4=marcar  F5=sim  F6=sim  F7=sim
G1=33ms  G2=onset  G3=audio  G7=absoluto  H1=glifo  H4=____  I5=sintetico
J1=____  J4=____  J5=____  J7=____
```

---

## 4ª rodada — decisões do plano do produto (D1–D7)

> **Origem**: `docs/guias/plano-do-produto.md`, §5. Estas são as perguntas que **só o dono** responde.
> **Enquanto ele não responder, o executor segue o ⭐ e registra no `ESTADO.md` que foi SUPOSIÇÃO** ✓
> (não invente resposta nem trate suposição como decisão).

| # | pergunta | ⭐ padrão que o executor usa se não houver resposta |
| --- | --- | --- |
| **D1** | Os limiares do §1 do plano (casa ≥ 0,97 · inventada ≤ 0,5 % · tempo ≥ 0,95) servem? (H2/H3/H7 nunca foram respondidas) | os do §1 |
| **D2** | Se a aula **repete** um trecho, o JSON traz **uma entrada por passagem** ou deduplica? | uma entrada por passagem, com `tela` e `passagem` para o consumidor deduplicar |
| **D3** | Qual vídeo é o do MVP? | `sky guitar/retrato brasileiro - tab & lesson.mp4` (já explorado; H.264; paginado; faixa **e** cor) |
| **D4** | Vídeo **sem marcador**: entrega as notas com o tempo **da tela** (início/fim da exibição) declarado, ou sem tempo nenhum? | notas + `exibicoes` da tela; `t_ini` por nota fica `null` com motivo; áudio fica para depois |
| **D5** | Canal cuja casa não passar no CA-4: não entrega a casa, ou entrega com bandeira? | entrega com `casa_validada: false` |
| **D6** | Tempo do dono para rotular: o plano estima **~2 h** até o MVP e **~8 h** até o fim | — (só informar) |
| **D7** | Tablatura **rolante** (contínua) entra no escopo agora? | só se o censo (Fase 7) mostrar **≥ 10 %** do acervo |

**Observação do executor (para o cérebro, não é pergunta ao dono)**: há uma **inconsistência de estimativa**
entre o D6 e o §9 do plano — o D6 diz **~2 h** do dono até o MVP, enquanto a tabela do §9 soma, até o MVP,
Fase 0 (**10 min**) + Fase 2 (**~40 min**) + Fase 6 (**5 min**) ≈ **55 min** ✓. O executor segue o §9 para
planejamento e **não** usa o D6 como compromisso ✓.

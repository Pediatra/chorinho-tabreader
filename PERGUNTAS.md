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

# Escolha do modelo para transcrever tablatura/partitura de vídeo-aulas

**Rodada 1 — decisão fundamentada em medições nos seus arquivos, não em opinião.**

Hardware de referência (medido nesta máquina): **NVIDIA RTX 3060 Ti, 8 GB de VRAM**,
driver CUDA 13.4, 15 GB de RAM, 102 GB livres em disco.

Dados analisados:

- `parts/clipes*/` — 13 clipes de vídeo (1920×1080, 30/60 fps), 163 recortes de linha
  de tablatura, 14 conjuntos de metadados (`quality.json`, `tab_tokens.json`,
  `tablatura.tab`) herdados de um pipeline anterior;
- `parts/clipes/diferentes/` — 5 capturas com **outras famílias** de tablatura
  (player escuro, livro impresso, tab tracejada, tab ASCII).

---

## 1. Resposta curta

**Não existe modelo pronto, aberto e leve que leia tablatura de violão.** Não é uma
questão de procurar melhor: o formato simplesmente não está coberto pela literatura
de OMR (que é toda para partitura em pauta de 5 linhas).

O que existe e o que foi medido:

| Caminho | Situação real (medida) | Veredito |
| --- | --- | --- |
| **GOT-OCR2.0** (580 M, apache-2.0, "suporta sheet music") | Rodado nos seus recortes: numa linha limpa devolveu `"A B"`; em outra devolveu 12 números soltos sem corda; na tab escura leu os acordes (`G7M A7 A#° D`) e **degenerou em repetição** (`555555…` por 1024 tokens) | **Reprovado** para tablatura |
| **Audiveris** (OMR maduro, Java) | Engine para pauta de 5 linhas (`MusicXML`); **não lê tablatura**. Útil como *inspiração de arquitetura* e para a linha de partitura | Não resolve TAB |
| **oemer / homr / Polyphonic-TrOMR** | OMR de partitura (segmentação + transformer). homr roda até em CPU | Só partitura, não TAB |
| **Tesseract / OCR genérico** | Lê o algarismo, mas joga fora a estrutura (corda, coluna, símbolo). Foi o que você já viu custar caro | Não resolve sozinho |
| **VLM grande (Qwen2.5-VL-7B etc.)** | 7 B em fp16 não cabe confortavelmente em 8 GB para treinar; e erraria o que é justamente o difícil: manter 6 cordas × colunas consistentes | Custo alto, ganho duvidoso |
| **Rede pequena dedicada + CV determinístico** | Medido nesta rodada: ~**74 mil parâmetros**, treina em segundos na 3060 Ti | **Escolhido** |

**Decisão: pipeline próprio de duas camadas — geometria determinística + classificador
minúsculo de glifos — e nada de VLM para a tablatura.** Se quiser usar um modelo
aprendido maior, o lugar justificado é a **linha de partitura** (aí sim homr/Audiveris
ou um detector), nunca a linha de TAB.

---

## 2. Por que: o problema se decompõe em duas coisas muito diferentes

### 2.1 Estrutura (linhas, cordas, colunas, cursor) — é geometria, não semântica

Medições desta rodada, com `tools/tabseg.py` (nenhum modelo, só visão computacional):

- **161 de 163** recortes de tablatura tiveram as **6 cordas** detectadas, com passo
  estimado por linha. Os 2 que falharam eram **recortes errados** (linha 10 de `tup-*`
  e `jmny*` são, na verdade, partitura — o pipeline antigo recortou a região errada).
- O passo entre cordas **varia por canal**: 12,0 / 14,2 / 15,4 / 17,8 / 18,0 / 21,6 /
  22,0 / 24,4 / 30,0 px. Por isso a detecção de linha **não pode ter constante fixa** —
  a versão final estima a progressão aritmética das 6 linhas a cada imagem.
- Foi detectada a polaridade do tema (fundo claro *e* fundo escuro), linhas **sólidas
  e tracejadas**, e rejeitados automaticamente: rótulo `T A B`, barlines, fragmentos
  de corda e cabeçalhos.

**O cursor de execução** (o "marcador que passa sobre a nota") também é geometria.
Medições em `-6rawhontyg` (2398 quadros, quadro a quadro, `tools/cursor.py`):

- banda azul (matiz 109 em HSV), detectada em **99,9 %** dos quadros;
- a posição x do cursor **coincide com a coluna da nota**: erro **0,0 px** no quadro de
  t=5 s e 9,7 px em t=9 s (dentro da largura do algarismo);
- **o cursor não desliza: ele salta de nota em nota e fica parado enquanto a nota
  dura.** Medido: **100 saltos** em 80 s, salto mediano de **109 px** (≈ o espaçamento
  entre notas), intervalo mediano de **0,70 s** entre saltos, x constante por ~1 s entre
  eles. Consequência prática: cada nota tem uma **janela de tempo fechada** (início e
  fim do patamar), e a precisão do instante é a do quadro (33 ms) — melhor que qualquer
  estimativa por áudio;
- **18 retrocessos** em 80 s = trocas de sistema (o cursor volta à margem esquerda).
  Detectar isso é obrigatório, senão a nota é associada ao lugar errado;
- a notação é **estática** dentro do sistema (nada de rolagem): confirmado
  independentemente em 6 clipes, com banda visual de **32 a 58 px** (o núcleo saturado
  que o `cursor.py` mede tem 15–22 px).

Ou seja: **a pergunta "como saber em que minutagem cada nota é tocada" está resolvida
sem modelo algum** — x(t) do cursor → coluna da grade → (corda, casa) → tempo. E a
mesma varredura resolve o fim do sistema (o cursor volta para a margem esquerda: 18
retrocessos medidos no clipe de 80 s).

### 2.2 Identidade do glifo — é aqui que entra um modelo (pequeno)

Inventário real, extraído de 163 linhas (**6.882 glifos válidos** após filtro de lixo;
530 componentes descartados):

- o alfabeto é **algarismos 0–9** (e números de 2 dígitos: `11`, `12`, `14`);
- **o mesmo desenho reaparece entre canais**: o cluster de forma mais frequente tem
  327 glifos vindos de **11 canais diferentes** — ou seja, o alfabeto é comum, o que
  muda é escala, contraste e anti-aliasing;
- mais um punhado de **símbolos de técnica** que apareceram nas linhas de TAB:
  - arco de **ligado** (curva acima ou abaixo do par de algarismos);
  - harmônico natural escrito como **`<7>`** (com os próprios sinais de menor/maior);
  - **acordes empilhados** (até 4 algarismos na mesma coluna vertical);
  - barline e rótulo `T A B` (ruído a descartar);
- **cor é classe, não enfeite**: as vozes são azul (`#2959C5`/`#3457AB`), verde
  (`#17945F`/`#389655`), vermelha, e preto — e o algarismo colorido é o que **está
  soando** naquele instante. Um mesmo frame tem preto, azul e verde na mesma linha.

Isso é um problema de **classificação de dezenas de classes num recorte de 16×24 px**,
não de compreensão de imagem. Uma CNN de ~74 k parâmetros resolve; um VLM de 7 B é
duas ordens de grandeza de desperdício.

---

## 3. O que foi medido com modelos aprendidos

### 3.1 GOT-OCR2.0 (580 M) — reprovado com números

`transformers 5.19`, `GotOcr2ForConditionalGeneration`, GPU: pico de **3,3 GB**, 1–17 s
por linha. Saídas literais:

| Entrada | Modo | Saída |
| --- | --- | --- |
| linha TAB limpa (MuseScore) | OCR | `A B` |
| linha TAB limpa (MuseScore) | formato | alucinou um `tikzpicture` de régua em LaTeX |
| linha TAB limpa (MuseScore) | caixa à esquerda | `T A B` |
| linha TAB outra escala | OCR | `8 5 4 7 1 2 2 0 5 6 3 3` (sem corda, faltando metade) |
| linha TAB outra escala | caixa | `TBA555555…` (degenerou) |
| tab escura (tracejada) | OCR | `G7M A7 A#° D` (leu os acordes; **não** a tablatura) |
| tab escura | caixa | 1024 tokens de `5` repetido |

Conclusões objetivas: não devolve `(corda, casa)`; perde algarismos; entra em loop
degenerativo; inventa formato. **A linha 1 tinha gabarito verificado pixel a pixel**
(15 manchas de tinta, todas na corda 2, depois de remover as 6 cordas):
`0 0 0 0 | 1 1 1 1 | 3 3 3 3 | 1 1 0`. O GOT acertou **0 de 15** algarismos em todos os
modos — no modo "formato" ele interpretou as 6 linhas de corda como um **eixo de
números** (`tikzpicture` com ticks de −5 a 5). Ou seja: OCR genérico não é o caminho —
exatamente o que você suspeitava, agora com evidência.

Nota de implementação (útil para não repetir o trabalho): em `transformers 5.19` é
preciso usar `AutoModelForImageTextToText` (`GotOcr2ForConditionalGeneration`);
`AutoModel` carrega uma classe **sem** `.generate`. O `pixel_values` sai em fp32 e tem de
ser convertido para o dtype do modelo (bf16), não existe argumento `ocr_type` (os modos
são `format=True`, `box=[...]` e `text=<prompt>`), e o prompt livre exige **exatamente
um** marcador `<imgpad>`.

### 3.1.1 Contraprova: a camada própria acerta onde o GOT falha

Na mesma linha 1 com gabarito verificado, o `tools/tabseg.py` devolveu **15 glifos, todos
na corda 2**, com x dentro de **1 px** das posições verificadas independentemente
(161/252/342/433, 561/658/754/850, 979/1075/1172/1268, 1402/1499, 1594).
É validação cruzada do extrator estrutural: 15/15 notas, corda correta, posição correta.

### 3.2 CNN minúscula treinada nos seus dados

`tools/glyph_bench.py` (74.382 parâmetros, treino na GPU em segundos):

- 1.944 glifos rotulados automaticamente casando os tokens de prata (`tab_tokens.json`)
  por corda e ordem;
- **acurácia nos canais vistos: 0,88**;
- **acurácia em 2 canais nunca vistos: 0,64** (`n_3jb8ekqnq`, `p87amzjak-m`).

Leitura honesta desse número: **generalizar entre canais é o elo fraco**, não a
capacidade do modelo. A correção não é um modelo maior — é **calibração por canal**
(um banco de templates/alguns rótulos verificados por canal), porque dentro de um canal
o desenho do glifo é praticamente idêntico: a distância intra-cluster medida ficou em
**~1 % dos pixels** em todos os 12 canais.

### 3.3 Aviso importante sobre os rótulos herdados

Os `tab_tokens.json` são **prata, não ouro**: o pipeline antigo aceitou 46,7 %–93,0 %
dos glifos, recortou região errada em pelo menos 2 linhas, **perdeu os harmônicos
visíveis** (`jmny` mostra `<7>` no vídeo e `tecnica=None` em 679 notas) e transformou
`5/7/5` empilhado em `575` corrido. Medir acurácia contra eles **mede consistência, não
verdade**. Por isso a próxima rodada precisa de um **gabarito pequeno e verificado à
mão** (umas 300–500 amostras já bastam para aferir).

---

## 4. Arquitetura recomendada

```
vídeo (1080p, 30/60 fps)
        │
        ├─(1) localizar o painel de notação (topo OU base, varia por canal)   [CV]
        │
        ├─(2) achar a pauta de 6 cordas (progressão aritmética, passo variável) [CV]
        │        e a pauta de 5 linhas da partitura, quando existir
        │
        ├─(3) rastrear o cursor (banda colorida vertical) -> x(t)              [CV]
        │
        ├─(4) grade corda × coluna; mascarar a coluna sob o cursor             [CV]
        │
        ├─(5) classificar cada célula:                                        [CNN ~10^5 params]
        │        dígito 0–24 | número de 2 dígitos | <n> harmônico |
        │        arco de ligado | barline | rótulo | acorde (pilha)
        │        + atributo de cor/voz (azul, verde, vermelho, preto)
        │
        └─(6) montar o JSON: nota = (corda, casa, t_instante, tecnica, voz)
                 com t_instante = instante em que o cursor cruza a coluna
```

Papéis de cada peça:

1. **Camada geométrica (`tools/tabseg.py`, `tools/cursor.py`)** — já implementada e
   medida. É ela que garante **estrutura correta** (corda certa, ordem certa, coluna
   certa), que é onde OCR/VLM falham.
2. **Camada de reconhecimento** — rede minúscula multi-classe (não uma CNN de 10
   dígitos: precisa das classes de técnica e da cor). Treina na 3060 Ti em minutos.
3. **Partitura (quando houver)** — se você quiser também a partitura estruturada, aí
   sim vale um OMR de verdade (`homr`, leve e roda em CPU; `Audiveris` como referência
   de arquitetura e para edição). A tablatura continua sendo lida pela camada própria —
   **o Audiveris não lê TAB**.
4. **Dados de treino** — o caminho barato e escalável é **gerar sintético** nas 5
   famílias observadas (MuseScore/Guitar Pro claro, player escuro, tab tracejada,
   livro impresso, tab ASCII) com fontes reais, variando passo, contraste, cor de voz,
   posição do cursor e presença de símbolos; e **afinar com poucas centenas de recortes
   reais verificados por canal**. Isso é *fine-tuning* de verdade — mas de um modelo de
   10^5 parâmetros, não de um VLM.

### Ajuste à sua placa

| Item | Custo real medido |
| --- | --- |
| CNN de glifos (74 k parâmetros) | treino em **segundos**, inferência em lote trivial |
| GOT-OCR2.0 (580 M) | pico de **3,3 GB** de VRAM (cabe, mas reprovado em qualidade) |
| VLM 7 B em fp16 | ~14 GB de pesos — **não cabe** para treinar em 8 GB |
| VLM 3 B com LoRA | cabe (quantizado), mas exigiria 1–2 mil linhas rotuladas e ainda seria mais lento e menos auditável que a opção escolhida |

---

## 5. Ferramentas entregues nesta rodada

| Arquivo | O que faz | Situação |
| --- | --- | --- |
| `tools/tabseg.py` | segmenta a linha de TAB em grade (6 cordas × colunas + glifos + barlines); trata tema claro/escuro, linha sólida/tracejada, escala variável | funcionando, 161/163 linhas |
| `tools/cursor.py` | rastreia o cursor de execução e devolve x(t) com estatísticas (cobertura, retrocessos, velocidade) | funcionando, 93,8 % de cobertura |
| `tools/glyphset.py` | inventário de glifos: extrai, filtra lixo e agrupa por forma | funcionando (7.300 glifos) |
| `tools/glyph_bench.py` | monta o conjunto rotulado a partir dos tokens de prata, treina e afere a CNN (inclusive em canais novos) | funcionando |

Reprodução:

```bash
.venv/bin/python tools/tabseg.py parts/clipes/-6rawhontyg_000120_000200/linha_01_tablatura.png --debug /tmp/saida.png
.venv/bin/python tools/cursor.py parts/clipes/-6rawhontyg_000120_000200/clip.mp4 --roi 0 470 --json /tmp/cursor.json
.venv/bin/python tools/glyph_bench.py --epocas 30
```

---

## 6. Próximas rodadas (ordem de maior retorno)

1. **Gabarito verificado** de ~300–500 glifos + 20 linhas (corrige o problema de fundo:
   hoje não existe verdade para medir).
2. **Gerador sintético** nas 5 famílias (com as fontes do sistema e as cores de voz
   medidas), para o classificador multi-classe.
3. **Alinhamento nota×tempo** de ponta a ponta: para cada coluna, o instante de
   travessia do cursor → `t_instante`; validar contra os `t_instante` prata
   (1 nota/s em `-6rawhontyg`).
4. **Detector de fim de sistema / troca de página** (o cursor volta à margem) para não
   associar a nota errada quando a música re-pagina.
5. **Símbolos de técnica**: `h`, `p`, `/`, `\`, `<n>`, diamante, `~` — hoje o pipeline
   herdado simplesmente os perde.
6. Só depois: avaliar se vale um OMR de partitura (`homr`) para o par
   partitura+tablatura e para o canal `xc18bl-ya4w`, que **não tem recorte nem metadados**.

## 7. Ressalvas registradas

- `parts/clipes/xc18bl-ya4w_000228_000518/` tem só o `clip.mp4`: não foi processado
  pelo pipeline antigo.
- As linhas `linha_10_tablatura.png` de `tup-ygpv7uo` e `jmnybboxcuy` são recortes de
  **partitura**, não de tablatura (erro de recorte herdado).
- O cursor **salta** de nota em nota (100 saltos em 80 s no canal de referência, salto
  mediano de 109 px, patamar de ~1 s), e a música **re-pagina por sistema inteiro**
  (18 retrocessos em 80 s): a detecção de troca de sistema é obrigatória para não trocar
  a nota. A largura da banda varia de 32 a 58 px entre canais (o núcleo medido pelo
  `cursor.py` fica em 15–22 px).
- Os números de acurácia da seção 3.2 usam rótulos prata como gabarito; servem para
  comparar caminhos, não como acurácia absoluta do sistema.

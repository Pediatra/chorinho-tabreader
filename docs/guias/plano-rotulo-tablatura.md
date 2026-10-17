# Plano — a tablatura como rótulo da base (o ataque de cada nota)

**Data**: 2026-10-16. **Trilha**: tablatura. **Estado**: aprovado pelo dono em 2026-10-16, com os critérios "proposta" e o
piloto de marcar arcos em 3 a 5 vídeos do sky guitar. Decisão:
[`0011`](../decisoes/0011-tablatura-vira-rotulo-da-base.md). Plano irmão:
[`plano-dataset-maos.md`](plano-dataset-maos.md).

## 0. Resumo em 30 segundos

- **O objetivo é o mesmo das mãos.** Queremos uma base em que cada nota tocada tenha, juntos:
  - o gabarito;
  - o som;
  - o braço;
  - as duas mãos.

  **A tablatura da tela é o gabarito.** Um rótulo errado contamina o modelo futuro tanto quanto
  uma associação errada entre mão e nota.
- **A casa já está boa: 0,996 fora do ouro.** O que falta no rótulo é o **ataque**: dizer se a
  nota foi tocada pela mão direita ou não.
  - h, p, slide ligado e ligadura de prolongamento: a nota soa **sem ataque** da mão direita.
  - X: **ataque sem altura**.
  - Harmônico: ataque com **outra altura**, e a mão esquerda só encosta na corda.

  Se a base disser "atacada" numa nota ligada, ela grava o movimento da mão direita de outra
  nota e espera um som que não existe.
- **Hoje o produto erra isso quase sempre.**
  - A rede acha o arco do ligado em **25 de 139** marcas do dono, e a classe sai certa em 4
    (rodada 0104).
  - Ela nunca viu um arco real: o ajuste fino zera a técnica nas telas reais.
- **Escopo (decisão do dono):** só os símbolos que **mudam o ataque**. São eles: h, p, mordente,
  ligadura de prolongamento, slide, X e harmônico. Todo o resto fica fora agora (seção 5).
- **Ordem**:
  1. R1 — esquema do rótulo;
  2. R2 — gabarito do ataque nota a nota;
  3. R3 — linha de base do produto atual;
  4. R4 — detector de arco, a peça que falta e a mais difícil;
  5. R5 — X e harmônico;
  6. R6 — auditoria e piloto, junto com o M14/M15 das mãos.
- **Param**: a onda 2 como estava (B1 completa, E1, E2), a C1 (rolagem) e a D2. A B1 volta só
  se o R4 precisar de arcos de outro estilo.

## 1. O que já existe (não refazer)

| peça | estado medido | onde |
| --- | --- | --- |
| casa e corda | fora do ouro (T8.2, 35 telas, 18 canais): casa 1551/1557, 9 inventadas, 16 perdidas; dobras 1744/1761 | decisão 0010, rodada da fase 8, `ESTADO.md` |
| marcas de técnica do dono | 415 regiões em 5 fontes; legato (h, p, mordente, prolongamento) 139; X 124 (76 EOB, 39 Room 335, 9 T8.2); slide `/` `\` 42; harmônico 4 | `data/gold/ouro_video/*.json`, `conferencia_t82.json`; contagem em `tablatura-frentes.md` §2 |
| regra do arco pelos números | mesmo número = prolongamento; maior→menor = p; menor→maior = h; 3 ou mais = mordente; barra = slide. **Confirmada pelo dono** | `configs/simbolos.yaml`, `regra_do_arco_pelos_numeros` |
| técnica na rede | 10 classes, aprendidas **só no sintético**; arco achado em 25/139, classe certa em 4/139; não é limiar nem ajuste fino | rodadas 0101–0104 |
| X | ignorar o X no ajuste fino (3 sementes) **não mudou** a casa na T8.2 (1546 contra 1547 de 1553). A folha de palpites de X está aberta (EOB: 93 + 1; Room 335: 39), esperando o dono | `data/saida/tab_frentes/integracao/x_abafada/` |
| o que as outras trilhas pedem | áudio: classe `arco` e nota de ornamento (decisão 2002); X com classe própria (2004, item 9). Mãos: K1 (som) e K3 (mão direita) dependem de saber se houve ataque (1006) | `docs/decisoes/` |
| ouro do piloto | sky guitar: só o Retrato Brasileiro (v2), **sem marca de técnica** | `data/gold/ouro_video/retrato_brasileiro_v2.json` |

**O que falta de verdade:**
- o ataque de cada nota no gabarito, nota a nota;
- um leitor que ache o arco;
- a taxa de ataque errado nas notas que entram na base, medida pelo dono.

## 2. Princípios (o que impede o rótulo de contaminar o modelo)

1. **O rótulo vem só da tela.** O som e as mãos **conferem** o rótulo e mandam para auditoria o
   que não bate, mas nunca **criam** rótulo. Se o som decidisse o ataque, o modelo futuro
   aprenderia a nossa regra em vez do que foi tocado.
2. **Na dúvida, "não sei"; nunca "sim".**
   - Uma nota com tinta sem explicação perto, que pode ser um arco, não entra no nível ouro.
   - Errar para "não sei" custa cobertura; errar para "sim" contamina a base.
3. **Achar o arco primeiro, a classe depois.** O ataque depende quase só de uma pergunta: "esta
   nota é o fim de um arco?". A classe (h, p, prolongamento, mordente) sai dos números, pela regra
   que o dono confirmou.
4. **Guardar o cru.** O arco é gravado como objeto: corda, x de início e de fim, e confiança. O
   ataque é **derivado** dele e pode ser refeito. Isso atende o pedido 2002 da trilha do áudio.
5. **A taxa de ataque errado é medida pelo dono, com número, antes de escalar** (R6).
6. **Teste separado de treino.**
   - As telas da T8.2 nunca entram no ajuste fino.
   - As dobras são por vídeo, como na casa.
   - Técnica medida numa tela que o modelo viu no treino não conta.
7. **Reprodutível**: no mínimo 3 sementes, com média e amplitude (regra 1 do `AGENTS.md`).

## 3. O rótulo por nota (proposta R1)

Os campos são novos e opcionais em cada nota, sem mudar o que já existe:

- `ataque`: `"sim"` | `"nao"` | `"nao_sei"`;
- `ataque_motivo`: `normal` | `h` | `p` | `mordente` | `prolongamento` | `slide_ligado` | `slide_entrada` | `x` | `rasgueado` | `arpejo` |
  `harmonico` | `arco_sem_par` | `tinta_sem_explicacao`;
- `nivel_rotulo`: `ouro` | `prata` | `recusado`.

O arco entra em `nao_notas` como classe `arco`, com corda, `x_ini`, `x_fim` e confiança.

| o que está na tela | `ataque` | `ataque_motivo` |
| --- | --- | --- |
| número sem marca | sim | normal |
| começo de um arco | sim | normal |
| fim de arco, número maior que o anterior | nao | h |
| fim de arco, número menor | nao | p |
| fim de arco, mesmo número (ou nada do outro lado) | nao | prolongamento |
| dentro de um arco de 3 ou mais números, depois do primeiro | nao | mordente |
| letra `h` ou `p` entre os números (canal que escreve em vez de desenhar) | nao | h / p |
| destino de slide, com ou sem arco (o arco é só estilo de canal; dono, 2026-10-16) | nao | slide_ligado |
| slide que **começa sem nota** (entra deslizando de fora) | sim, com o ataque no começo do deslize | slide_entrada |
| slide que **termina sem nota** (sai deslizando) | a nota de origem é sim; não há destino | normal |
| X | sim | x |
| harmônico (`<7>` ou losango) | sim | harmonico |
| arco achado sem um par claro de números | nao_sei | arco_sem_par |
| tinta que não é algarismo nem símbolo conhecido, encostada no par | nao_sei | tinta_sem_explicacao |

**Níveis:**
- **ouro**: corda e casa lidas, e `ataque` diferente de `nao_sei`;
- **prata**: corda e casa lidas, mas `ataque` é `nao_sei`;
- **recusado**: a tela ou o painel têm problema conhecido (pedidos da decisão 2004).

**Como as outras trilhas usam:**
- **Mãos**: a K1 (som) e a K3 (pico da mão direita) só exigem ataque quando `ataque = sim`. Com
  `nao`, a nota entra com a janela da mão esquerda, e a K3 não se aplica.
- **Áudio**: uma coluna só com notas `nao` não precisa de ataque próprio no alinhador (2002).

**Aceite do R1:**
- o dono aprova os campos (o slide sem arco já está decidido: é igual ao com arco);
- o validador em `tab/esquema.py` aceita os campos novos, com testes no gate;
- a decisão diz se os campos ficam no `chorinho/video@1` (opcionais) ou se o esquema sobe para
  `@2`.

## 4. As fases

### R1 — Esquema do rótulo (1 dia)

- Seção 3 vira decisão + validador + testes.
- Nada roda no acervo.

### R2 — Gabarito do ataque, nota a nota (máquina + tempo do dono)

**Pergunta**: em cada tela do ouro, qual é o `ataque` de cada nota?

- **Converter o que o dono já marcou.**
  - Cada uma das 415 regiões vira o ataque das notas que ela cobre: as cordas e o x da região
    dizem quais notas são.
  - A classe sai da regra dos números.
  - É automático, e o dono confere na ferramenta (`tab.ouro_video servir`, numa **cópia**).
- **A folha de X que já está aberta entra aqui.**
- **Telas sem nenhuma marca contam.**
  - Os 4 ouros sem marca (Greensleeves, Gymnopédie, South American e Retrato) precisam de um
    "conferi, não há arco" por tela.
  - Sem isso, não dá para medir o "não" falso.
- **Piloto.** O sky guitar tem só o Retrato, sem marca de técnica. O dono marca os arcos em
  telas de 3 a 5 vídeos do sky guitar. O palpite vem do produto, e o dono corrige: regra antes de
  gabarito.

**Aceite (proposta):**
- toda nota das telas conferidas tem `ataque` do dono;
- a contagem por motivo e por canal é relatada, com o denominador;
- a lista de telas de teste fica escrita antes de qualquer treino.

### R3 — Linha de base (sem treino, CPU)

- Rodar o produto atual contra o R2 e montar a matriz de `ataque` (previsto × ouro), por canal.
- O número que importa é o **"sim" falso**: das notas que o dono diz não atacadas, quantas o
  produto chama de atacadas. Esperado: perto de 80 %, pelos 25/139 da rodada 0104.
- Medir também uma regra simples, que serve de chão para o R4: "tinta que não é algarismo entre
  dois números da mesma corda" vira `nao_sei`.

**Aceite**: não tem. É a régua; os números entram na rodada antes do R4.

### R4 — Detector de arco (o coração; 1–2 semanas, GPU)

**Pergunta**: entre duas notas vizinhas da mesma corda, há um arco ligando? Onde ele começa e
onde termina?

**Caminhos, nesta ordem:**

- **R4a — o arco real no ajuste fino.**
  - Hoje o ajuste fino zera a técnica nas telas reais. Com o R2, as telas de treino passam a
    ensinar o arco, com as mesmas dobras por vídeo da casa.
  - É o mesmo passo que fizemos com o X, só que com supervisão positiva.
  - É o caminho mais barato.
- **R4b — o arco como objeto próprio** (era a A2), se o R4a não passar.
  - Uma saída à parte, de começo e fim de arco por corda, no lugar da classe por nota.
  - O gerador sintético desenha arcos em vários estilos, inclusive o arco acima da corda 1, que o
    recorte pode cortar (rodada 0102; o aviso do dono em `simbolos.yaml`).
- **R4c — outro renderizador** (o AlphaTab da B1), só se o R4b mostrar que falta estilo de arco no
  gerador.

**Aceite (proposta), nas telas de teste:**
- "sim" falso **≤ 5 %** das notas não atacadas;
- "não" ou "não sei" em nota atacada ≤ 10 %. Esse é o custo em cobertura;
- a casa não piora: 1551/1557 na T8.2, dentro da amplitude das sementes;
- 3 sementes, com média e amplitude.

**Pare se** o R4a achar menos da metade dos arcos de teste. Olhe a folha inteira antes de mexer
no gerador.

### R5 — X e harmônico (junto com o R4 ou logo depois)

- **X.**
  - O X do dono (a folha aberta + a T8.2) entra no ajuste fino com supervisão **positiva**: casa
    `x`.
  - Aceite (proposta): X achado ≥ 95 %; X inventado ≤ 1 por tela; a casa das outras notas não
    piora.
  - Avisar a trilha do áudio antes, porque ela depende do top-1 do X (pedido 2004, item 9).
- **Harmônico.**
  - Só há 4 marcas no ouro. Antes de gastar, contar quantos harmônicos o piloto e os ouros têm,
    pelo `nao_notas` `harmonico` que o produto já guarda.
  - Se forem raros, o harmônico entra pelo glifo cru e vira `nao_sei` quando a leitura for
    duvidosa.

### R6 — Auditoria e piloto (com o M14/M15 das mãos)

- Os mesmos 20 vídeos do sky guitar do piloto das mãos.
  - Se o sky guitar quase não tiver arcos, junta-se um segundo canal que tenha, com ouro de
    técnica (shin izumi ou kenneth acoustic).
- **Auditoria do dono**:
  - 100 notas **ouro** sorteadas, estratificadas por vídeo e por motivo, com o recorte da tela e
    a nota destacada;
  - o dono responde "certo / errado / não dá para ver", um clique por nota, com autosave, numa
    ferramenta testada numa cópia;
  - se der, a mesma sessão audita o evento das mãos (M14).

**Aceite (proposta):**
- ≤ 2 erradas em 100;
- a fração ouro/prata/recusado relatada por vídeo;
- o viés relatado: quais notas caem em prata (passagens rápidas? ligados?).

**Pare se** houver mais de 5 erradas.

## 5. O que fica fora agora (com o motivo)

- **Bend, vibrato e setas de palhetada**: a nota é atacada do mesmo jeito. Fica o glifo cru,
  como hoje.
- **Rasgueado e arpejo** entram como **informação**, não como pergunta (dono, 2026-10-17): a
  nota é `sim`, com motivo `rasgueado` ou `arpejo`, porque o movimento da mão e o tempo do som
  mudam. Sai das regiões que o dono já marcou (a coluna logo à direita do símbolo), sem
  conferência a mais.
- **Figuras de ritmo, compasso e ritornelo**: não são da nota.
- **Tablatura que rola (C1)**: a base começa sem esses 16 %, como no piloto das mãos.
- **Sondas de modelos prontos (E1, E2) e o som conferindo a casa (D2)**: a casa já está em
  0,996.
- **Resíduo da casa (dois algarismos)**: segue na fila normal de pedidos, sem frente própria.

## 6. O que o dono precisa fazer

| quando | o quê | tempo |
| --- | --- | --- |
| feito (2026-10-16) | aprovou o plano, os critérios e o piloto; decidiu o slide | — |
| R1 | aprovar o formato | 10 min |
| R2 | conferir o ataque nos ouros já marcados; "não há arco" nos 4 ouros sem marca; marcar arcos em 3–5 vídeos do sky guitar | a medir no R2; estimativa de 1–2 h |
| R5 | a folha de X (já aberta) | ~30 min |
| R6 | auditar 100 notas por lote, junto com as mãos se der | ~30–40 min |

## 7. Riscos e como perceber cedo

- **Arco cortado pelo recorte** (corda 1, arco acima da linha). Aparece como "sim" falso
  concentrado na corda 1 no R3. A rodada 0102 tentou medir isso e não valeu, porque o texto acima
  da tab entra como tinta.
- **Arco longo sobre muitas notas** (frase ou mordente) e arcos que se cruzam: viram
  `arco_sem_par` e ficam prata, nunca chute.
- **Canal que escreve h/p em letra** em vez do arco: a rede tem as classes `h` e `p`. Conferir no
  R2 quantos canais fazem isso.
- **Tablatura diferente do que é tocado.** A K1 das mãos e o alarme do áudio pegam. Relatar
  quantos.
- **Poucos arcos no piloto** (o sky guitar tem melodia de choro, mas ainda não foi contado): o R2
  conta antes, e o R6 junta outro canal se for preciso.

## 8. O que não fazer

- Criar rótulo de ataque pelo som ou pela mão (princípio 1).
- Dizer "sim" quando há tinta sem explicação (princípio 2).
- Medir técnica numa tela que entrou no ajuste fino.
- Clicar no ouro ao vivo para testar ferramenta: testar numa cópia.
- Reabrir a A1 (classe pela regra dos números sem achar o arco): a rodada 0104 fechou.

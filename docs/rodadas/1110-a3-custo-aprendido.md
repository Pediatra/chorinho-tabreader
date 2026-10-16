# 1110: A3, custo aprendido da tablatura (perceptron estruturado)

**Frente**: A3 de [`docs/pesquisa/maos-frentes.md`](../pesquisa/maos-frentes.md) (seção 7).
**Código**: `tab/maos_decod_dados.py` (sequências), `tab/maos_decod_aprendido.py` (custo,
decodificador, perceptron), `tab/maos_decod_medir.py` (medida e CLI). Importa o D1 do M8
(`tab/maos_corda_sem_direita.py`), sem editar.
**Saída**: `data/saida/maos/frentes/fa_decodificador/a3_pesos.json` e `a3_medida.json`.

## Pergunta

Pesos do custo do decodificador (α, γ, δ e as características novas) aprendidos da
tablatura por perceptron estruturado acertam mais corda que o D1 do M8, que usa pesos
escritos à mão, sem câmera e sem tempo além do `t_ini`?

## Pré-registro (escrito antes da medida)

Nada abaixo muda depois de ver número. Se mudar, a frente é invalidada (seção 5.3, CA4).

### Dados

- **Produtos (10 sequências)**: `sky_1` a `sky_8` (`data/saida/maos/m3d/`), `mvp.json`
  (retrato) e `q16_chopin_nocturne20.json` (noturno). Notas com `t_ini`, tela, compasso e
  exibição, com os mesmos filtros e o mesmo agrupamento por `t_ini` (tolerância de 0,02 s)
  do M8. O produto de cada teste: retrato = `mvp`, noturno = `q16_chopin_nocturne20`,
  lacrimosa = `sky_4`, glimpse = `sky_8`.
- **Ouros do dono (8 arquivos com nota conferida)**: `data/gold/ouro_video/*.json`, só
  leitura. O gabarito de uma página é a página com `conferida == true` (é a marca do dono,
  inclusive nas páginas cuja `origem` ainda diz "modelo — a rotular"; essas foram
  conferidas por ele). O ataque é a **coluna**: notas da mesma página com `x_centro_quadro`
  a até 5 px. Sem tempo: o `dt` é desconhecido.
  - O `retrato_brasileiro.json` (v1) não tem página conferida: fica de fora.
  - O `retrato_brasileiro_v2.json` é o vídeo de teste retrato: sai da dobra do retrato.
  - Ouros: 2.690 notas conferidas em 8 vídeos e 8 canais; 7 canais fora do `sky guitar`.
    O `maos-frentes.md` (5.1) fala em 9 vídeos de 7 canais: são 9 arquivos, 8 vídeos e 8 canais.
- **Fora do domínio**: nota com corda fora de 1–6 ou casa fora de 0–19 sai, como no M8.
  Casa acima de 7 **entra** no treino e na medida principal; a medida secundária só com
  casa ≤ 7 (seção 5.2 da frente).

### Características (dez, `NOMES_PESOS`)

De ataque (somadas sobre as notas do acorde):

1. `casa_soma`: Σ casa das presas (α do M8);
2. `abertura`: 1 se max − min das presas passa de 4 (γ do M8);
3. `soltas`: número de cordas soltas;
4. `faixa_baixa`: presas de 1 a 4;
5. `faixa_alta`: presas de 13 para cima (zonas de Heijink como atributo, não como regra).

De transição entre ataques consecutivos:

6. `salto_curto`: |Δ posição| quando `dt` < 0,5 s (`dt` do `t_ini`);
7. `salto_medio`: |Δ posição| quando 0,5 s ≤ `dt` < 2 s;
8. `salto_longo`: |Δ posição| quando `dt` ≥ 2 s;
9. `salto_sem_dt`: |Δ posição| no ouro (sem tempo);
10. `troca_corda`: Σ, sobre as notas do ataque atual, da distância à corda mais próxima do
    ataque anterior. É o proxy de "mesma voz": a voz não é anotada.

A posição é a do M8 (menor casa presa; ataque só com soltas carrega a posição anterior).
O decodificador é o Viterbi do M8, com estado `(combinação, posição)`.

### Pesos iniciais, épocas e taxa (fixados)

- **Pesos iniciais** `w₀` = D1 a priori do M8: `casa_soma` 1; `abertura` 5; `salto_*` 0,5
  (os quatro bins); as demais 0. Com `w₀`, o decodificador reproduz o D1 do M8 em todos os
  ataques (verificado: caminho idêntico nos 4 vídeos, em 2.437 ataques).
- **Épocas**: 5. **Taxa**: η = 0,1.
- **Atualização** (perceptron estruturado): depois de cada sequência, se o caminho
  decodificado diverge do da tablatura, `w ← w − η·(φ(tablatura) − φ(decodificado))`. A
  diferença zera fora dos trechos divergentes.
- **Média**: o peso final é a média de `w` depois de cada sequência, em todas as épocas
  (perceptron médio; declarado aqui, não é ajuste).
- **Ordem**: sequências em ordem de nome, sem sorteio. Sem semente, sem variância de
  treino: duas execuções têm de dar o mesmo arquivo (CA5).

### Dobras

- **CA (4 dobras, fora da amostra)**: para cada vídeo de teste, treino em todas as outras
  sequências, exceto as que têm o mesmo `video` (cobre `sky_4` e `sky_8` nas próprias
  dobras, e os dois ouros do retrato na dobra do retrato). Mede-se no vídeo de fora.
- **Canal de fora**: para cada um dos 7 canais dos ouros fora do `sky guitar`, treino sem o
  canal e medida nele. Os produtos `sky_*` continuam no treino.
- **Relatório (não é critério)**: `sky_1`, `sky_2`, `sky_3`, `sky_5`, `sky_6` e `sky_7`,
  deixando o próprio vídeo de fora.

### Referência

D1 do M8 sobre as mesmas notas e ataques: α = 1, β = 0, γ = 5, δ = 0,5. CA1 confirma que o
D0 e o D1 refeitos batem com `data/saida/maos/m8/corda_sem_direita.json`: **verificado** (ver
abaixo).

### Critérios congelados (seção 5.3)

- **CA1**: reproduz D0 e D1 do M8 (mesmas notas, mesmos denominadores).
- **CA2**: nas ambíguas, somando os 4 vídeos, ganho líquido ≥ +1,0 pp **e**
  consertadas − quebradas ≥ 20.
- **CA3**: ganho (acurácia nas ambíguas) em pelo menos 3 dos 4 vídeos, e nenhum vídeo piora
  mais de 0,5 pp.
- **CA4**: fora da amostra. Feito pelas dobras; os pesos não olham o vídeo de teste.
- **CA5**: duas execuções idênticas (sem sorteio; a conferência é o hash do JSON).
- **CA6**: 10 notas olhadas no quadro (5 consertadas, 5 quebradas), com o caminho do recorte.
- **CA7**: gate verde na worktree.
- **Reprova ou para**: não passa em CA2 ou CA3, **ou** algum peso muda de sinal entre as 4
  dobras (nesse caso o ganho é ajuste, não regra). Relatar a amplitude de cada peso.

## Resultados

**Veredito: REPROVADA** pelo pré-registro. Falha em CA2 e CA3. Nenhuma variante de taxa,
épocas ou pesos foi testada nas dobras depois disso. A medida foi feita uma vez, com a
configuração acima.

Números: `data/saida/maos/frentes/fa_decodificador/a3_medida.json` e `a3_pesos.json`.

### CA1: reprodução do M8

Refeito a partir das mesmas notas: D0 e D1 batem com `data/saida/maos/m8/corda_sem_direita.json`
nos 4 vídeos (acertos iguais). Totais: D0 com 341 erros e D1 com 285, como na rodada 1013.
Com `w₀`, o caminho do decodificador é idêntico ao do D1 em todos os 1.838 ataques dos 4
vídeos. **CA1 passa.**

### Medida principal (4 dobras fora da amostra, notas ambíguas)

| vídeo | ambíguas | D1 | aprendido | consertadas | quebradas | ganho (pp) |
| --- | --- | --- | --- | --- | --- | --- |
| retrato | 692 | 0,9277 | 0,9220 | 0 | 4 | −0,58 |
| noturno | 540 | 0,7611 | 0,7333 | 0 | 15 | −2,78 |
| lacrimosa | 418 | 0,8565 | 0,8349 | 0 | 9 | −2,15 |
| glimpse | 630 | 0,9270 | 0,9222 | 0 | 3 | −0,48 |
| **total** | **2.280** | **0,8750** | **0,8614** | **0** | **31** | **−1,36** |

- **CA2: falha.** Ganho −1,36 pp (exige ≥ +1,0). Consertadas − quebradas = −31 (exige ≥ 20).
- **CA3: falha.** Nenhum vídeo ganha; o pior piora 2,78 pp (limite: −0,5).
- Medida só com casa ≤ 7 (ambíguas): retrato 0,9410 → 0,9351; noturno 0,8110 → 0,8000;
  lacrimosa 0,8624 → 0,8428; glimpse 0,9231 → 0,9231. Mesmo sentido.
- Unidades distintas `(vídeo, tela, coluna, corda, casa)`, ambíguas: retrato 402 → 400 (2
  quebradas); noturno 411 → 396 (15); lacrimosa 340 → 333 (7); glimpse 349 → 348 (1).
- Mudança de decisão: o aprendido mudou só **2, 8, 6 e 3 ataques** nos 4 vídeos (19 de 1.838).

### Pesos por dobra e amplitude (4 dobras de teste)

| peso | retrato | noturno | lacrimosa | glimpse | amplitude | muda sinal |
| --- | --- | --- | --- | --- | --- | --- |
| casa_soma | 213,3 | 267,8 | 287,8 | 269,1 | 74,5 | não |
| abertura | 18,8 | 24,9 | 21,7 | 21,7 | 6,2 | não |
| soltas | 51,2 | 46,3 | 54,3 | 54,6 | 8,3 | não |
| faixa_baixa | −0,9 | −24,1 | −17,3 | −10,5 | 23,2 | não |
| faixa_alta | 59,8 | 41,2 | 56,3 | 58,3 | 18,5 | não |
| salto_curto | 25,9 | 12,1 | 6,9 | 17,7 | 19,0 | não |
| salto_medio | 53,0 | 102,9 | 104,5 | 119,9 | 66,9 | não |
| salto_longo | −7,9 | −9,2 | −8,7 | −5,6 | 3,6 | não |
| salto_sem_dt | 2,5 | 13,0 | 0,4 | 6,6 | 12,5 | não |
| troca_corda | −48,4 | −30,3 | −60,1 | −69,2 | 38,9 | não |

Nenhum peso muda de sinal entre dobras, mas **todos cresceram de escala**: `casa_soma` foi de
1 para cerca de 270, e `w₀` tem ordem 1. Os pesos ficaram nessa escala, não num ajuste fino.

### Diagnóstico do fracasso (não é critério; não muda o veredito)

- **O decodificador é consistente.** Em todas as 18 sequências, o caminho decodificado tem
  custo `w·φ` ≤ o da tablatura, com `w₀` e com o `w` aprendido. Não há erro de Viterbi nem de
  φ (checado por código, não por medida).
- **O passo é grande demais.** A atualização é somada sobre a sequência inteira. A norma de
  `φ(tablatura) − φ(decodificado)` vai de 5 a 677 por sequência; `w₀` tem ordem 1. Com η = 0,1,
  o primeiro passo já domina e os pesos sobem para a escala de centenas. Foi má escolha a priori
  de taxa, feita antes da medida.
- **Por isso quase nada muda.** O aprendido muda 19 ataques nos 4 vídeos e nenhum nas seis
  sequências do relatório. Com `w` grande, a decisão fica perto da do D1 e as consertadas não
  aparecem.

### Canal de fora nos ouros do dono (7 canais fora do `sky guitar`, notas ambíguas)

| canal | n | D1 | aprendido | consertadas | quebradas |
| --- | --- | --- | --- | --- | --- |
| robert lunn | 335 | 0,8149 | 0,8567 | 14 | 0 |
| kimny's guitar | 345 | 0,8696 | 0,8754 | 6 | 4 |
| shin izumi | 319 | 0,4859 | 0,4796 | 1 | 3 |
| iwaki | 394 | 0,9188 | 0,8731 | 0 | 18 |
| guitar dell'arte | 208 | 1,0000 | 1,0000 | 0 | 0 |
| kenneth acoustic | 267 | 0,9925 | 0,9925 | 0 | 0 |
| pablo romé | 90 | 1,0000 | 1,0000 | 0 | 0 |
| **total** | **1.958** | | | **21** | **25** |

Fora do `sky guitar` o efeito não tem sinal: ganha em um canal e perde em outro (robert lunn
+14, iwaki −18). Líquido −4 notas em 1.958. Não há generalização consistente.

### Relatório (não é critério)

Deixando o próprio vídeo de fora, nas notas ambíguas: `sky_1`, `sky_2`, `sky_3`, `sky_5`,
`sky_6` e `sky_7`: o aprendido é **igual** ao D1 (0 consertadas, 0 quebradas). Nenhuma decisão
muda nessas seis.

### Consistência (CA5 e CA7)

- **CA5**: duas execuções da medida geraram os mesmos hashes (md5) de `a3_pesos.json` e
  `a3_medida.json`.
- **CA7**: `ruff check .` e `ruff format --check .` passam; `pytest tests/` com as montagens do
  briefing: 1238 passam, 2 pulados, 2 xfail, 4 deselecionados (integração). Testes novos em
  `tests/test_maos_decod_aprendido.py` e `tests/test_maos_decod_medir.py`.

### CA6 (10 notas no quadro): não executado

Só se aplica a variante aprovada. Reprovada a frente, não há caso a olhar para aceitar.

## Não repetir

- **Taxa η = 0,1 com φ somado por sequência** (passo de centenas sobre `w₀` de ordem 1): os
  pesos sobem de escala e a decisão não muda. Qualquer retentativa precisa de taxa escolhida só
  com treino interno (CA4), ou de φ normalizado por ataque ou por nota.
- **Perceptron sem normalização, com `w₀` = D1 e η = 0,1**: nesta medida, não gerou ganho nas
  dobras de teste e mudou pouquíssimas decisões. Não diz nada sobre o perceptron com outra escala.
- **Relatar "ganho" em canais de fora sem o líquido**: robert lunn (+14) e iwaki (−18) se
  cancelam.
- O `docs/pesquisa/maos-frentes.md` (seção 5.1) diz "9 vídeos de 7 canais" para os ouros. São
  9 arquivos, 8 vídeos (o retrato tem duas versões), 8 canais (7 fora do `sky guitar`).
- **Pergunta ao dono (não bloqueia)**: o marcador `conferida == true` vale como gabarito nas
  8 ouros, mesmo com `origem` "modelo — a rotular" em todas as páginas? Foi o que usei.

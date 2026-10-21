# 0211 — Recorte alto no rótulo de ataque

Segue a [0210](0210-diagnostico-recorte-do-painel.md). Escrito **antes** de medir e de treinar.
O dono pediu o caminho curto em 2026-10-20.

## A mudança de código (só esta)

- `painel.recorte_alto(quadro, c)`: o recorte do candidato aumentado no quadro até 2,5 passos
  acima da corda 1 e abaixo da 6 (`FOLGA_DETECTOR_PASSOS`, igual a
  `detector_tab.MARGEM_PASSOS`).
  - As colunas e as cordas são as mesmas.
  - Se o `roi` não é um recorte cru do quadro, ele fica como está.
- Usam o recorte alto:
  - `ataque_r4.ler_tela`, com `recorte="alto"` como padrão e `"painel"` para refazer o antigo;
  - `ataque_r4 medir --recorte`, que grava em `medida_<v>_s<s>_alto.json` sem apagar as antigas;
  - `tab.video` **só** com `--rotulo-ataque`. A leitura comum (`DETECTOR_PADRAO`) não muda.
- Conferido: com o `_atqt`, a T8.3 dá 5 · 5 · 5 /71, igual ao `diag/recorte_alto.py`.

## Fase 1 — sem treino

`_atqt` e `_atqe`, 3 sementes, recorte alto, nos ouros (pela dobra fora) e na T8.2 (dobra 0).

- Os limiares são escolhidos nos ouros, como sempre (`escolher_limiar` e `escolher_nao_sei`).
- A casa dos ouros com o recorte alto é comparada com a do recorte antigo, porque o recorte é
  entrada do modelo (regra 9).

## Fase 2 — treino com o recorte alto

- O cache real (ouros, T8.2) é refeito com o recorte alto, em pastas novas (`n4/*_alto`). O cache
  antigo fica.
- `treinar_ft.py --recorte-alto` lê essas pastas.
- O G11–G12 volta a ligar (`P_CADEIA` 0,25, `P_ARCO_ALTO` 0,25), porque a 0210 mostrou que ele
  ajuda quando o arco chega ao modelo.
- São 15 treinos `--ataque --t82 --recorte-alto`, com o nome `_atqa_s<semente>`. A medida é a da
  fase 1.

## Decisão do produto

- Entre `_atqt`, `_atqe` e `_atqa`, todos com o recorte alto, fica o de menor "sim" falso nos
  ouros, na faixa com os limiares escolhidos nos ouros e somadas as 3 sementes.
- Desde que:
  - o custo nos ouros fique ≤ 10 %;
  - a casa dos ouros não caia abaixo do pior `_atqt` com o recorte antigo.
- Muda o `ataque_rotulo.DETECTOR_CALIBRADO` e os limiares, se for o caso.
- A T8.3 é só informada: ela foi usada na 0210.
- **A validação é a T8.4**, um lote novo que o dono confere. O aceite é o do plano: "sim" falso
  ≤ 5 % e custo ≤ 10 %.

## Resultado da fase 1 (2026-10-20)

Medidas em `r4a/medida_{atqt,atqe}_s{1,2,3}_alto.json`. Os limiares escolhidos nos ouros não
mudam com o recorte: `_atqt` com técnica 0,15 e `L` 0,02; `_atqe` com técnica 0,25 e `L` 0,02.

| pesos | recorte | ouros, "sim" falso | ouros, custo | ouros, casa | T8.2, "sim" falso |
| --- | --- | --- | --- | --- | --- |
| `_atqt` | antigo | 4 · 5 · 4 /85 | 100–108 /2593 | 2660–2665 | 2 · 2 · 2 /45 |
| `_atqt` | alto | 4 · 4 · 4 /85 | 99–104 /2593 | 2661–2667 | 2 · 2 · 2 /45 |
| `_atqe` | antigo | 3 · 3 · 3 /85 | 109–122 /2593 | 2659–2663 | 2 · 2 · 2 /45 |
| `_atqe` | alto | 2 · 2 · 2 /85 | 104–123 /2593 | 2659–2664 | 2 · 2 · 2 /45 |

- **A casa não piora com o recorte alto.** Nos ouros ela fica em 2659–2667, contra 2660–2665 no
  antigo.
- Nos ouros e na T8.2 quase não há arco acima do sistema, então eles mudam pouco. A diferença
  aparece na T8.3, na 0210.
- O custo nos ouros fica em 4–5 %, dentro dos 10 %.

## Emenda antes de medir o `_atqa` e a T8.4 (2026-10-21, 15:25)

Escrita com os 15 treinos `_atqa` prontos e **antes** de ler qualquer medida do `_atqa`
(nos ouros ou na T8.4).

### Leitura do critério da casa

- "A casa dos ouros não cai abaixo do pior `_atqt` com o recorte antigo" se lê **semente a
  semente**: a pior semente da versão precisa dar casa ≥ 2660.
- Com essa leitura, o `_atqe` (alto) sai da disputa por 1 nota: as sementes dele dão
  2659–2664.
  - A diferença é do tamanho do ruído entre sementes (regra 7.1). Mesmo assim, o critério
    escrito vale, e o limiar não se muda depois de ver o resultado.
- O script da decisão é `data/saida/tab_rotulo/r4g/decidir.py`. Ele reproduz a tabela da
  fase 1 e só lê os ouros e a T8.2.

### O lote T8.4

- **Sorteio:** `data/saida/t84/gerar.py`, cópia do da T8.3 com `random.Random(2)`.
  - Ficam de fora os vídeos do ouro, da T8.2 e da T8.3.
  - São 2 vídeos por canal, em 16 canais, num total de 32 telas.
- **Telas que saíram:**
  - uma, porque o quadro não abriu (ギタロー);
  - uma, porque era o braço do violão, sem tablatura (cifra club). Nela o produto leu 14
    notas, e isso fica registrado como erro do produto.
  - Ficam **29 telas**.
- **Conferência:** o dono conferiu tudo em 2026-10-21, a casa e as regiões dos símbolos,
  sem ver a leitura do modelo de ataque.
- **Gabarito:** `data/saida/tab_rotulo/r2/conferir_t84/ataque_t84.json`, gerado por
  `novos_t84.py`. São **1270 notas, das quais 87 não atacadas**.
- **Correções ditas pelo dono no chat**, aplicadas numa cópia (a conferência dele fica
  intacta):
  - a região "(n)" do `0 → 2` na tela 9 é hammer;
  - o 2º par `<12>` da tela 21 faltava na lista e entra como não atacado, por ligadura de
    prolongamento.
- **Regiões sem nota embaixo:** sobram 3 ligaduras. Elas não mudam nenhum rótulo.

### A medida na T8.4 (uma vez só)

- **O que se mede:** só a versão escolhida pelo `decidir.py`, com os pesos da dobra 0 (o
  mesmo uso do produto), as 3 sementes, o recorte alto e o `L` escolhido nos ouros.
- **"Sim" falso:** `nao|sim` / (`nao|sim` + `nao|nao`), com a regra do slide sem origem.
  Nota não lida fica fora do denominador.
- **Custo:** `sim|nao` / (`sim|nao` + `sim|sim`).
- **Aceite (o do plano):** com as 3 sementes somadas, "sim" falso ≤ 5 % e custo ≤ 10 %.
  - Por semente, os números saem informados.
- **Se passar:**
  - o `ataque_rotulo` passa a usar a versão escolhida (`DETECTOR_CALIBRADO` e limiares);
  - a etapa do rótulo de ataque fecha.
- **Se reprovar:**
  - a T8.4 fica registrada como gasta;
  - os erros dela viram o diagnóstico seguinte;
  - o `DETECTOR_CALIBRADO` não muda por causa dela.
- **Em nenhum caso** o `DETECTOR_PADRAO` (a leitura comum) muda sem o OK do dono.

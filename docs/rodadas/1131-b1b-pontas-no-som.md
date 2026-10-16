# 1131 — B1b: D2 com grade fixa e pontas no instante do som

**Data**: 2026-10-16. Frente B1b da onda 2 ([`maos-frentes.md`](../pesquisa/maos-frentes.md),
seção 4.2; briefing em [`maos-onda2-briefings.md`](../pesquisa/maos-onda2-briefings.md)).
Referência R1 = D1 do M8 (285 erros). Linha de base do revisor = D2 fixo com as pontas do `t_ini`
(36 / 104 / 52 / 50 erros; 242 no total; `data/saida/maos/m8/d2_fixo.json`).

## Pergunta

Com a janela da mão do M8 (`janela_da_mao_esquerda`), a grade fixa do quadro do dono (sem teste
de câmera) e as pontas tiradas no instante do som (`t_audio`), em vez do `t_ini`, o D2 erra
menos ataques com nota presa, e o ganho aparece nas notas ambíguas sem piorar um vídeo?

## Regras e pesos a priori (escritas antes de qualquer medida desta rodada)

**Decodificador.** M8 sem alteração: `tab.maos_corda_sem_direita` importado (`decodificar`,
`pontuar`, `_ponta_valida` com `SCORE_MIN` = 0,3). Sem grade de pesos. Pesos a priori do M8:
α = 1, β = 3, γ = 5, δ = 0,5 (`PESOS_PRIORI`).

**Janela.** `janela_da_mao_esquerda(maos, ref, (0, 0))` para todo ataque com nota presa, sem o
teste de câmera (`LIMIAR_CAMERA` não entra). Só o eixo ao longo do braço; a grade é a do quadro
do gabarito de cada vídeo (`QUADRO_DO_BRACO`).

**Instante do som.** `t_audio` de `data/saida/maos/m7/audio/ataques_audio.json`, casado com o
ataque pelo `t_ini` (tolerância 0,02 s).
- Regra do alinhador: se `t_audio − t_ini` estiver fora de [−0,1 s; 1,0 s], usa-se o `t_ini` e o
  ataque é contado à parte (há saltos de −9,6 s e +18 s).
- **Variante principal**: quadro em `t_audio` (3 casas). Esta é a única que vale para aprovação.
- **Secundária (só diagnóstico)**: quadro em `t_audio − 0,1 s`. Só é rodada se a principal couber
  no orçamento de CPU; não entra nos CA.

**Detector.** `DetectorMaos` (rtmlib), mesmo quadro (`quadro_bgr`), mesmo `mao_para_registro`,
`rect_tab` nulo, sem deslocamento. Nenhuma mudança de limiar de score.
- Desvio registrado: `chorinho:dev` não tem `rtmlib` nem `onnxruntime`. Usa-se
  `localhost/chorinho-maos:dev` (já existente, sem instalar nada), em CPU.
- **Orçamento**: se o total estimado em CPU (medido com 20 quadros) for ≤ 2 h, roda-se em CPU.
  Se passar disso, PARE e peça à sessão principal a GPU, com a lista de instantes gravada.

**Cobertura (parada).** Com as pontas do som, se a fração de ataques com nota presa que têm
janela cair abaixo de 90 % em algum vídeo, PARE e relate. Não mexo no limiar.

**Aprovação (CA1–CA7 congelados).** Todos precisam passar, contra R1 (D1):
- **CA1**: D0 = 341 e D1 = 285 reproduzidos exatamente (mesmos denominadores); D2 fixo com t_ini
  = 36 / 104 / 52 / 50 reproduzido (antes de qualquer medida nova).
- **CA2**: nas ambíguas, somando os 4 vídeos (2.280 ambíguas), ganho líquido de acertos de pelo
  menos +1,0 pp sobre D1 (≥ +23 acertos), e consertadas − quebradas ≥ 20.
- **CA3**: ganho em pelo menos 3 dos 4 vídeos (ambíguas) e nenhum vídeo piora mais de 0,5 pp.
- **CA4**: nenhum peso é ajustado; não há calibração, então o CA4 é cumprido por construção e
  declarado como tal.
- **CA5**: duas execuções da decodificação dão o mesmo sha256 do JSON de saída.
- **CA6**: 10 casos, 5 consertadas e 5 quebradas (em relação a D1), com pelo menos 4 do glimpse.
  Escolha determinística: por vídeo e ordem de tempo, com passo regular. Recorte do braço no
  `t_ini` e no `t_audio` lado a lado, com o caminho anexado.
- **CA7**: gate verde na worktree (`ruff check`, `ruff format --check`, `pytest`).

**Métricas e relato.** Acurácia em todas as notas, nas ambíguas, em presas e soltas; erros
decompostos em janela errada / janela certa / sem janela; cobertura com denominador; consertadas e
quebradas por vídeo; contagem por (vídeo, tela, coluna) distinta, só como relato (não aprova).
Contra o D2 fixo do `t_ini` também.

**O que não aprova.** Variante secundária, leitura de subconjunto e qualquer escolha feita depois
de ver o resultado (diagnóstico, nunca aprovação).

## Resultado

**Não aprovada.** CA1, CA2, CA4, CA5 e CA6 passam; **CA3 reprova** (lacrimosa, −0,72 pp contra
o limite de −0,5 pp). A variante com pontas no som não ganha do D2 com pontas no `t_ini` no total:
242 erros no `t_ini`, 243 no som.

**Execução.** Pontas no som: 1.470 ataques com nota presa (473 + 394 + 256 + 347), todos com
mãos lidas (0 sem mão). Detector em CPU na imagem `localhost/chorinho-maos:dev` (1,5 a 1,8 s por
quadro; cerca de 40 min no total). Os 170 ataques (11,6 %) sem `t_audio` dentro da faixa
[−0,1 s; 1,0 s] usaram o quadro do `t_ini`: retrato 8, noturno 62, lacrimosa 14, glimpse 86.
Esses ataques não foram separados por motivo (ausência de casamento ou fora da faixa). Cobertura
com janela no som: 469/473 (retrato), 393/394 (noturno), 255/256 (lacrimosa), 342/347 (glimpse);
mínimo 98,6 %, acima da parada de 90 %.

**Erros por vídeo** (pesos a priori, grade fixa):

| vídeo | D1 (R1) | D2 `t_ini` | D2 som |
| --- | --- | --- | --- |
| retrato | 50 | 36 | 37 |
| noturno | 129 | 104 | 99 |
| lacrimosa | 60 | 52 | 63 |
| glimpse | 46 | 50 | 44 |
| **total** | **285** | **242** | **243** |

**Ambíguas** (2.280 notas; acertos D1 1.995 = 87,50 %; D2 `t_ini` 2.038 = 89,39 %; D2 som
2.037 = 89,34 %):

| vídeo | ganho som vs D1 (pp) | ganho `t_ini` vs D1 (pp) | som vs `t_ini` (acertos) |
| --- | --- | --- | --- |
| retrato | +1,88 | +2,02 | −1 |
| noturno | +5,56 | +4,63 | +5 |
| lacrimosa | −0,72 | +1,91 | −11 |
| glimpse | +0,32 | −0,63 | +6 |
| total | **+1,84** (42 líquidas) | +1,89 (43) | −1 |

- Consertadas − quebradas, som vs D1: **63 − 21 = 42**. Vs `t_ini`: 60 − 17.
- (tela, coluna) distintas: 52 consertadas e 14 quebradas.

**Decomposição dos erros de nota presa** (janela errada / janela certa / sem janela):

| vídeo | `t_ini` | som |
| --- | --- | --- |
| retrato | 2 / 30 / 4 | 0 / 33 / 4 |
| noturno | 5 / 98 / 1 | 5 / 94 / 0 |
| lacrimosa | 5 / 46 / 1 | **16 / 47 / 0** |
| glimpse | 15 / 33 / 1 | 9 / 33 / 1 |

O erro "janela errada" caiu no glimpse (15 → 9), que é a suspeita da hipótese, mas subiu na
lacrimosa (5 → 16). Esse aumento é o que reprova o CA3.

**CA1–CA7 contra o D1 (R1):**

- **CA1 passa.** D0 = 341 e D1 = 285. D2 `t_ini` = 36 / 104 / 52 / 50, igual ao diagnóstico do
  revisor.
- **CA2 passa.** Ganho líquido de +1,84 pp (≥ +1,0) e consertadas − quebradas = 42 (≥ 20).
- **CA3 reprova.** Ganho em 3 de 4 vídeos (retrato, noturno e glimpse), mas a lacrimosa cai
  −0,72 pp (limite −0,5 pp).
- **CA4 passa por construção.** Nenhum peso ajustado; pesos a priori α 1, β 3, γ 5, δ 0,5.
- **CA5 passa.** A decodificação repetida dentro da mesma execução dá o mesmo resultado, e
  duas execuções completas do script dão o mesmo sha256 (`42c84ee0...072e09`).
- **CA6 passa.** Dez casos: 5 consertadas e 5 quebradas, com 4 do glimpse. Recortes com o
  caminho do PNG no relatório, lado a lado no `t_ini` e no som:
  `data/saida/maos/frentes/fb_esquerda/casos_b1b/C01...C10`. O sorteio do CA6 (glimpse 2 + 2,
  outros 3 + 3, passo regular por vídeo e tempo) está no código, definido antes de ver o
  resultado. Esta seção não o repete.
- **CA7** (gate): ver o commit final.

**Desvios declarados.**

- O detector roda em `localhost/chorinho-maos:dev` em CPU, não em `chorinho:dev` (sem `rtmlib` e
  sem `onnxruntime`). Nenhuma dependência foi instalada.
- Variante secundária (`t_audio − 0,1 s`) não rodada. Seria diagnóstico, e a aprovação já
  reprovou no CA3.
- Não houve parada: cobertura ≥ 98,6 %, e a medida em CPU coube no orçamento de 2 h.

**Não repetir.**

- Trocar o `t_ini` pelo `t_audio` como quadro da janela, sem separar os ataques em que o som cai
  fora da faixa (170 de 1.470). Nesses, o quadro continua o do `t_ini`, e a mistura mascara o
  efeito. Antes de repetir, medir quantos dos 170 são casamento ausente e quantos são fora da
  faixa.

**O que esta medida NÃO prova.**

- Não prova que a janela do som é melhor. No total, o som empata com o `t_ini` (−1 acerto).
- Não separa o efeito do quadro do som do efeito dos 170 quadros de fallback.
- Usa 4 vídeos de um canal (`sky guitar`) e um violonista. A casa é a do gabarito do produto.
- A "janela errada" da lacrimosa subiu; a causa (quadro do som, mão borrada, grade do braço) não
  foi investigada além de olhar os recortes.

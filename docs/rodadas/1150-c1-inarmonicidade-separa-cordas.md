# 1150 — C1: a inarmonicidade do áudio separa as cordas candidatas de mesma altura?

**Data**: 2026-10-16. Frente C1 (`docs/pesquisa/maos-frentes.md`, seção 7), onda 1, worktree
`chorinho-wt-c1`, branch `maos/c1-inarmonicidade`. Código: `tab/maos_timbre_beta.py`,
`tab/maos_timbre_controle.py`, `tab/maos_timbre_c1.py`. Testes: `tests/test_maos_timbre_beta.py`,
`tests/test_maos_timbre_c1.py`. Saída: `data/saida/maos/frentes/fc_audio/`.

## Pergunta

Num mesmo vídeo, para a mesma altura, o coeficiente de inarmonicidade β medido no áudio do
YouTube separa as cordas candidatas (teste de ir ou não ir para a C2)?

## Limite declarado

A altura, a corda verdadeira e a escolha das notas isoladas vêm da tablatura do produto. Isso é o
**limite superior** de viabilidade: o que se mede aqui é o que um decodificador com áudio perfeito
e gabarito poderia usar, não um decodificador.

## Pré-registro (escrito antes de medir nos vídeos)

- **Áudio**: FLAC mono a 48 kHz sem reamostrar (`tab.audio_extrair.extrair`, `taxa=48000`).
  `t_amostra0` pela regra da rodada 2001 (1º frame decodificado: 0,0 s nos 4 vídeos).
- **Controle sintético** (`tab/maos_timbre_controle.py`): notas com parciais
  `k·f0·sqrt(1+β k²)`, decaimento `exp(-t/(0,8/(1+0,15k)))`, ruído a −56 dBFS, trilho estéreo,
  Opus `libopus` a 121 e 161 kb/s (os extremos medidos com ffprobe nos vídeos: 121 a 161 kb/s,
  Opus 48 kHz, estéreo), decodificado a mono como na extração.
- **Premissa de β(s, 0)** (cenário central): `{1: 2e-5, 2: 3e-5, 3: 5e-5, 4: 1e-4, 5: 2e-4,
  6: 3e-4}`. É uma premissa de ordem de grandeza, não uma medida. Cenários de sensibilidade:
  β três vezes menor e três vezes maior.
- **Critério do controle**: por nota, `r = |β̂ − β| / Δ`, com `Δ` a menor diferença de β para as
  outras cordas candidatas da mesma altura. Aprovado no central se, em cada bitrate, pelo menos
  90 % das notas são medidas e a mediana de `r` é menor que 0,5.
- **Estimador** (`tab/maos_timbre_beta.py`): quadros de Hann de 4.096 amostras dentro de
  `[t+0,025 s, t+0,25 s]` (passo 1.024, 7 quadros); FFT com 16.384 pontos; pico parabólico em
  log-magnitude; razão pico/piso ≥ 3; ≥ 3 quadros por parcial; ≥ 6 parciais; parciais até 6 kHz e
  ordem 16. Rodada 1: parciais 2 a 8 com busca nominal de ±3 %. Rodadas 2 e 3: busca centrada na
  posição prevista pelo modelo, ±2 %. Ajuste linear de `(f_k/k)²` contra `k²`, com `β = b/a`.
  β ≤ 0 não é medida.
- **Isolamento**: o ataque tem uma nota só, tem `t_audio` do alinhador (M7), e nenhum outro som
  cai entre −0,15 s e +0,25 s do ataque. Sem `t_audio`, a faixa do som é +0,05 a +0,33 s de `t_ini`
  (P10 a P90 da diferença medida na rodada 2001 e no M7).
- **Parciais que soam**: o pico medido é descartado se cai a menos de 30 cents de um parcial de uma
  nota de outro ataque que começa até **2,0 s antes** do ataque (valor escolhido por mim: o plano
  não fixa o intervalo, ver "Desvios").
- **Divisão**: primeira metade do vídeo (por `t_audio`) calibra; segunda testa. Para cada par de
  cordas com a mesma altura e ≥ 8 notas medidas de cada lado no vídeo: média de `ln β` de cada
  corda na calibração, escore `sinal·(ln β − ponto médio)`, AUC só na segunda metade.
- **Aceite**: AUC ≥ 0,80 em pelo menos metade dos pares elegíveis, em pelo menos 3 dos 4 vídeos.
  Reprova: AUC < 0,65 na maioria dos pares.

## Desvios e correções (declarados)

1. **Estimador, rodada 1 com busca fixa.** A primeira versão procurava todos os parciais com
   busca de ±3 %. Em nota grave com inarmonicidade alta, o parcial 15 cai a 3,3 % do nominal e
   o 16 fica fora. Corrigido (rodadas 2 e 3, centradas no modelo) **antes** do controle. Nota limpa:
   β recuperado a menos de 0,3 % (E2, β = 3e-4, com afinação aproximada).
2. **Exclusão de parciais, versão 1 (corrigida depois de ver a contagem).** A primeira versão
   descartava a **busca inteira** do parcial quando qualquer parcial de outra nota caía na janela
   ampliada. Isso derrubou as medidas: em retrato, 5 de 150 notas isoladas mediam sem a exclusão
   cair para 148 de 150 de medir. A regra do plano é a de **pico**: descarta-se o pico medido a
   menos de 30 cents de um parcial alheio. Corrigi para a regra literal. Declaro porque o ajuste foi
   feito depois de ver a contagem; a regra corrigida é a que o plano escreve.
3. **β negativo.** A primeira execução quebrou no `log` com β < 0 (ajuste em ruído). Passou a ser
   "não medido" (22 notas). Corrigido antes da medida final.
4. **Valor de "ainda soa".** O plano não diz o intervalo. Escolhi 2,0 s. Essa escolha domina o
   resultado (ver sensibilidade). Não mudei o valor primário depois de ver os números.

## Controle sintético (aprovado no central)

| cenário | bitrate | notas medidas | mediana r | P90 r | aprovado |
| --- | --- | --- | --- | --- | --- |
| central | 121 kb/s | 117/117 | 0,00055 | 0,0019 | sim |
| central | 161 kb/s | 117/117 | 0,00047 | 0,0013 | sim |
| β÷3 | 121 / 161 kb/s | 117/117 | 0,0020 / 0,0012 | 0,0048 / 0,0030 | sim |
| β×3 | 121 / 161 kb/s | 117/117 | 0,00019 / 0,00013 | 0,0010 / 0,0008 | sim |

Exploratório, **fora do pré-registro** (β÷10, script de rascunho sem commit; não usado no veredito): mediana r de 0,005
(121) e 0,004 (161), 117/117 medidas. O controle é **otimista**: sinal sem reverberação, sem
ressonância simpática, com notas isoladas e relação sinal-ruído alta nos parciais. Não prova que o
método mede β de nota real no nível observado.

## Medida nos 4 vídeos

Áudio lido: retrato 11,32 min; noturno 10,34 min; lacrimosa 7,70 min; glimpse 11,23 min
(**40,6 min** de áudio decodificado). Bytes percorridos pelo ffmpeg para extrair o stream de áudio:
**no máximo 563 MB**, o tamanho dos 4 arquivos (o contêiner é percorrido para pegar só o áudio). Nenhum vídeo
foi lido de novo depois da extração a 48 kHz.

| vídeo | notas | com `t_audio` | isoladas | medidas (β > 0) | "poucos parciais" |
| --- | --- | --- | --- | --- | --- |
| retrato | 753 | 745 | 535 | 142 | 391 |
| noturno | 576 | 457 | 323 | 90 | 232 |
| lacrimosa | 453 | 448 | 214 | 45 | 156 |
| glimpse | 655 | 478 | 213 | 43 | 164 |
| **total** | **2.437** | **2.128** | **1.285** | **320** | **943** |

- **Mediana de β por corda** (cenário primário, 320 medidas): corda 1, 2,5e-5 (n = 51); corda 2,
  3,6e-5 (85); corda 3, 6,7e-5 (108); corda 4, 2,2e-5 (48); corda 5, 1,5e-5 (15); corda 6, 1,8e-5
  (13). As cordas graves **não** ficam acima das agudas, ao contrário da premissa. Os valores graves
  ficam abaixo da faixa que o controle testou para elas.
- **Pares elegíveis (≥ 8 por lado)**: **0** em retrato, noturno, lacrimosa e glimpse. Sem pares, a AUC
  não é avaliada.
- **Inclinação de ln β × casa** (efeito fixo por corda, 320 medidas): m = 0,109, EP 0,013,
  IC95 [0,084; 0,134], razão com ln2/6 = 0,94. **Compatível** com ln 2/6 = 0,1155.
  **Ressalva**: dentro de uma corda, casa e altura são a mesma variável (altura = afinação + casa).
  A inclinação não separa o modelo `β(s,n) = β(s,0)·2^(n/6)` de um viés do estimador que depende da
  altura. Só a comparação entre cordas na mesma altura é livre disso, e é ela que não foi possível.

Figura: `data/saida/maos/frentes/fc_audio/c1_beta_por_casa.png` (β em log × casa, por corda).

## Sensibilidade e exploração (não são o critério)

Arquivo: `data/saida/maos/frentes/fc_audio/c1_sensibilidade.json`.

- **Vizinhança de 0,5 s em vez de 2,0 s** (escolhida depois de ver o primário; exploratório): 1.167
  medidas (492, 294, 185, 196). Aparece **1 par com 8 por lado** em cada vídeo, e a AUC só sai em
  lacrimosa (0,948) e glimpse (0,938). Com 3 por lado, 5, 12, 3 e 3 pares. A inclinação deixa de ser
  compatível (m = 0,129; razão 1,12). **Não passa o aceite**: AUC em 2 vídeos, não 3.
- **Juntando os 4 vídeos** (exploratório, fora do critério por vídeo): com 8 por lado, 0 pares; com
  4 por lado, 1 par (altura 62, cordas 2 e 3, n = 13 e 5, AUC 0,80).

## Veredito

**Inconclusivo.** Nem "ir" nem "parar" pela regra pré-declarada: o critério de AUC não pôde ser
aplicado (0 pares elegíveis), e a AUC não ficou abaixo de 0,65 em nenhum par avaliado. **A C2 não
entra.** O gargalo é a quantidade de notas com β medível e isoladas em pares de mesma altura, não o
controle nem a física.

## O que a medida NÃO prova

- Que as cordas se separam pelo β (não houve pares suficientes para o critério).
- Que β é medível nas cordas graves no nível observado (valores medidos abaixo da faixa do controle
  nessas cordas).
- Que o controle é representativo: é otimista (sem reverberação, sem notas sobrepostas, alto SNR).
- Nada sobre técnica, ligados, dedilhado, nem sobre outros canais: só `sky guitar`, 4 vídeos, 1
  violonista.
- O efeito de a tablatura escolher as notas isoladas e fornecer a altura (limite superior).

## Não repetir

- Excluir a **busca inteira** de um parcial por causa de um parcial alheio (derruba ~95 % das
  medidas). Descartar só o pico, a menos de 30 cents.
- Busca fixa de ±3 % para parciais altos: perde o parcial 15 e 16 com inarmonicidade média.
- Deixar β ≤ 0 entrar no `log`.
- Tirar conclusão de controle sintético limpo sem reverberação para o áudio de vídeo.

## Pergunta para o dono

1. O que é "ainda soa"? O produto não tem duração. Sem um corte de duração (ou um envelope do
   áudio), o intervalo de 2 s é arbitrário e decide quantos pares existem.
2. Vale reabrir a C1 com um detector de decaimento e mais notas? Hoje há 1.285 notas isoladas e 320
   medidas.
3. As cordas graves medidas (β ~ 1,5e-5) estão no piso do método? Um controle com β na faixa medida
   diria.

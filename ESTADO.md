# ESTADO.md — número oficial, o que está medido e o que falta

Documento de entrada do projeto. **Todo número aqui é média de ≥3 sementes**, nunca
execução única — sem isso o mesmo código já deu 0,729 e 0,854. O histórico completo
das 65 rodadas está em [`docs/HISTORICO.md`](docs/HISTORICO.md).

## Atualizar o censo do acervo (comando único)

O acervo cresce. Para censar só o que é novo, rode:

```bash
docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho \
    python -m tab.censo --cache --janelas-por-canal 30 \
    --saida data/saida/censo/censo_cache.jsonl
```

- Vídeo já censado (chave `caminho|tamanho|mtime`) não é refeito. Vídeo novo em canal
  existente, ou canal novo, é censado.
- Canais com `rollout: fora` em `configs/canais.yaml` (hoje `violaodecria` e `tv cifras`,
  decisão 0009) são **pulados**. `--incluir-fora` os censa. Com `--canal`/`--canais`, o
  pedido explícito vale e nada é pulado.
- Canal sem entrada no yaml entra e aparece no log como `canal novo`. **Hoje o yaml cadastra
  7 dos 21 canais do acervo**, então 14 aparecem como novos em toda execução até o perfil de
  cada um ser escrito.
- Estratificação (`--janelas-por-canal 30`): vídeo novo ganha janela se cair na amostra
  espalhada do canal atual. Canal com até 30 vídeos dá janela a todos; acima disso o vídeo
  novo ganha janela só se cair na amostra recalculada (os extremos sempre caem). Vídeo já
  censado não é refeito, então mantém o que ganhou na época.
- Ao fim, o resumo diz quantos vídeos novos foram censados, por canal, e quantos canais são
  novos. Medido sem processar nada: 2.799 vídeos ativos, 1 pendente no instante da checagem.

## Número oficial

**0,889 de acerto no gabarito real** — média de 3 sementes (**0,865 / 0,917 / 0,885**),
amplitude **0,052**, sobre **96 glifos rotulados à mão em 4 canais, casas 0–7**.
**Reprodutível**: cada semente dá o mesmo total em execuções repetidas (medido 2× cada).

```bash
python -m tab.sintetico --n-linhas 320 --epocas 22 --seed S --saida artefatos/oficial_S
python -m tab.avaliar --modelo artefatos/oficial_S/glifo_sint.pt
```

| canal | acerto nas 3 sementes | observação |
| --- | --- | --- |
| iwaki (tema escuro) | **27/27 nas três** | |
| sky guitar | 14–15 de 15 | |
| **raman korshun** (slides, lixo) | **17/24 nas três** | estável; composição abaixo |
| paolo d'angelo | 25–29 de 30 | passo 16 px, o painel mais denso |

### O que a remedição corrigiu

O número anterior (**0,892**) acabou ficando a **0,003** de distância — ou seja, ele
estava certo *por sorte*, dentro de um ruído de até 0,05 que ninguém controlava. O ganho
desta rodada não é o número: é ele **agora ser reprodutível**. Quatro correções:

1. **A mesma semente variava 0,052 no treino** (0,927 / 0,896 / 0,948): o cuDNN usa
   `atomicAdd` e não é determinístico por padrão. Agora
   [`tab.sintetico.fixar_semente`](tab/sintetico.py) desliga isso e duas execuções da
   mesma semente dão perda idêntica até a 4ª casa. Ver
   [`docs/decisoes/0001-determinismo-do-treino.md`](docs/decisoes/0001-determinismo-do-treino.md);
2. **a aferição feita dentro do treino avaliava o modelo em modo `train()`**, com o
   `Dropout(0.15)` ligado: os MESMOS pesos davam **0,812 em `train()` e 0,865 em
   `eval()`**, e o treino reportava 0,771 enquanto o disco dava 0,865. Havia duas
   implementações de aferição e a do treino estava quebrada de três modos (índices
   contíguos, imagem errada para `raman`/`paolo`, modo de treino). Agora é uma só;
3. **`raman` é 17/24 nas três sementes, mas não é "17/17 nos algarismos"**: a composição
   medida é **12/17 algarismos + 5/7 acertos de `junk`**. Os 5 `junk` são acertados pela
   **regra de assinatura** (token estreito recusado), não pelo classificador. Total
   igual, erro diferente — o total sozinho não descreve o sistema;
4. **as 5 falhas de algarismo são todas `7`→`5` ou `7`→`15`** (posições 3, 5, 12, 19 e 26
   do `raman`): o `7` daquele canal carrega o traço de técnica e a confusão é
   sistemática, não aleatória. É o alvo mais concreto para a próxima rodada.

Números medidos antes de 2026-10-08 têm **ruído de até ~0,05 embutido**: ganhos históricos
de +0,038 e +0,046 estão dentro desse ruído e não deveriam ter sido tratados como ganho.

## CORREÇÃO (2026-10-09): o "96,5 % com tablatura" está inflado

Gerando montagem para os canais novos, o detector escolheu **piano**
(`violaodecria`), **cabeça do violão com tarraxas** (`shin izumi`) e **corpo do violão**
(`cifra club`) — e chamou os três de tablatura. Os números por canal daquela varredura
**não são medida de tablatura** até o portão ser corrigido: ver
[`docs/decisoes/0005-portao-de-tablatura-aprendido.md`](docs/decisoes/0005-portao-de-tablatura-aprendido.md).
Quatro discriminadores feitos à mão foram testados e **os quatro falharam** (uniformidade,
fração de algarismos, confiança do classificador, espessura de linha).

## Noite de 2026-10-08/09

O acervo cresceu para **3.993 vídeos / 183 GB / 17 canais** (ainda baixando). O que
mudou, com o número que sustenta cada item:

| o que | resultado medido |
| --- | --- |
| **varredura do acervo novo** | **96,5 % com tablatura** (3.855/3.993), em 69,5 min |
| **`sky guitar` (corrigido pelo dono)** | ele apagou os vídeos especiais **sem tutorial**: restaram **417, todos com tablatura**. A varredura dizia 348/440 |
| **por que eu errei os 14 %** | dos vídeos que o scan de **1 instante** chamou de "sem tablatura", **20 de 20 têm tablatura em algum instante** (7 instantes conferidos). O padrão é nítido: nas frações 0,08/0,22/0,36 do vídeo ela quase nunca está; de **0,50 para o fim** está quase sempre. O instante único do scan caía justamente na primeira metade |
| **cursor no quadro inteiro** | 69 de 3.993 — dois erros somados: o portão exige faixa de ≥50 % da **imagem** (540 px) e o cursor tem a altura do painel (~150 px), **e** o portão de matiz fixo (85–140, azul) rejeitava a faixa **laranja** do `sky guitar` (medido: matiz 13–14) — ver [`docs/decisoes/0006`](docs/decisoes/0006-marcador-sem-suposicao-de-cor.md) |
| **cursor no ROI da faixa** | muda onde o detector olha, mas **não basta**: no mesmo vídeo as detecções eram **artefato** (banda parada em x=0–99 por 5 s na borda do painel e bandas em x≈900–1084, fora do painel, que é 0–594). Aquele vídeo **não tem marcador** |
| **`iwaki` tem marcador? (corrigido pelo dono)** | **não**. Amostra de 6 vídeos × 7 instantes: **0 detecções**. O dono está certo; o canal mostra a partitura/tablatura e vai trocando |
| **escolha do painel** | o critério antigo (glifos centrados) escolhia o **braço do violão**; com uniformidade do fundo (0,888 × 0,842) escolhe a tablatura — `tab/painel.py`, implementação única |
| **recorte em x** | exigir 4+ das 6 cordas na mesma coluna estreita o painel ao retângulo real |
| **efeito do recorte na máscara** | mesmo quadro: recorte de 570 px → máscara `otsu` → **3 algarismos reais**; recorte de 1920 px → `contraste_k31_d25` → 36 tokens, **33 de lixo** |
| **ponta a ponta (`sky guitar`)** | **3 notas, corda 5, casas 0 / 2 / 3**, confiança 0,996 / 0,931 / 0,999 — exatamente o que está no quadro |
| **símbolo cru** | implementado: PNG deduplicado por hash, caixas dos componentes, larguras em passo, top-3 de classes |
| **recuperar a casa de dentro do símbolo** | medido e **reprovado**: 0,889 → 0,687 |
| **MusicXML** | exportador pronto (score-partwise 4.0, clef TAB, `staff-tuning`, `technical`), com a duração inferida **declarada** |

**Tempo por travessia (`tab/tempo.py`) — método sim, evidência não.** Eu havia concluído
que o marcador do `iwaki/henze` desliza (~65 px/s) e que isso dava **8 instantes distintos**.
**O dono do projeto corrigiu, e a medição confirmou:** ao longo dos 342 s daquele arquivo as
detecções estão **espalhadas** (x = 230, 285, 341, 548, 638, 690, 844, 1184, 1491, 1527…),
**sem progressão** — um movimento suave de 4 s dentro disso me enganou. Marcador de execução
anda para **um lado**; `tab/tempo.resumo` agora classifica isso como **`erratico`** e o
pipeline não atribui tempo. O método (inverter uma série monotônica) segue correto e testado;
o que faltava era **provar que existe série**, e isso agora é condição de aceitação.

**O inventário de 1 instante é um PISO, não um retrato.** Medido: a tablatura do `sky guitar`
aparece da metade para o fim, então amostrar a **segunda metade** detecta quase tudo com 1–2
instantes, enquanto amostrar cedo subestima. O "96,5 % com tablatura" do acervo inteiro foi
medido com 1 instante em 0,35 da duração: é **piso**. Para presença, `tab.varredura` agora
aceita `--frac-inicio/--frac-fim`.

**Bloqueio do MVP:** o **tempo por nota**, e o obstáculo real é anterior ao código:
**a presença e a semântica do marcador são POR VÍDEO, não por canal**. No vídeo do
`sky guitar` medido, a série `x(t)` do "cursor" é uma banda PARADA na borda do painel
por 5 s mais bandas fora do painel — não há marcador nenhum ali. O que existe de
confiável para esse caso é **áudio** (autorizado pelo dono do projeto) ou a marcação
manual. O MusicXML sai hoje com duração constante **declarada** — honesto, e é o teto
do que se pode afirmar sem marcador.

## O que o JSON entrega

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, coluna, compasso) | 0,892; corda e coluna robustas |
| **técnica** | classe treinada e estável; **sem ganho de acerto** (o modelo já lê o algarismo com o slide junto) |
| **símbolo cru** | **implementado**: todo token não numérico (e todo token fundido) sai com recorte em PNG deduplicado por hash, caixas dos componentes, larguras em passo e top-3 de classes |
| **tempo** | **dois mecanismos**, um medido em cada caso (abaixo) |
| **partitura** (5 linhas) | **fora** desta cadeia — exige OMR próprio |

### Tempo — o marcador VARIA por canal

| mecanismo | canal verificado | resultado |
| --- | --- | --- |
| **faixa vertical** que passa | `sky guitar` | 1 nota/s, desvio **0,16 s** (corrigível para ~33 ms) |
| **algarismo fica laranja** (cumulativo) | `cifra club` | **41/41 onsets**, 8 instantes distintos, intervalo mediano 1,80 s |
| **sem marcador** | ~46% dos vídeos | tempo teria de vir de áudio ou de marcação manual |

O JSON **declara o mecanismo**. No marcador por cor mede-se o **onset**, não a
duração: `t_fim` é o **próximo onset** — o algarismo continua laranja depois de tocado.

## Geometria — o que destravou canais

- **painel claro**: máscara de tinta escura. **painel escuro** (estilo `cifra club`):
  máscara de tinta **clara** (`contraste_claro_k21_d12`);
- **uniformidade de fundo** para achar o painel **e rejeitar o violão** — o braço tem
  6 cordas e engana o detector (medi: caixa de 149 px, matiz 16, era o corpo do violão);
- 5 famílias de renderização tratadas; passo entre cordas de **14 a 45 px**;
- algarismos de **0,38 passo** (cifra club) a 0,6 passo (sky guitar).

## O que funcionou (medido)

| mudança | efeito |
| --- | --- |
| tokenização (juntar componentes da mesma corda) | 0,70 → 0,85 em canal novo; treino 0,58 → 0,985 |
| tamanho de fonte variável no gerador | 0,805 → 0,851 e estabilidade |
| **rejeição de lixo por assinatura do vídeo** | `raman` 12 → 17/24; média 0,854 → **0,892** |
| extração por faixa de corda | 6.882 → 11.594 glifos (os ~4.700 a mais eram acordes fundidos) |
| fallback `ffmpeg` para AV1 | **140 de 319** quadros só eram legíveis por ele |

## O que foi tentado e falhou (não repetir)

| tentativa | efeito |
| --- | --- |
| regra de altura no extrator | 0 (0,818 → 0,818) |
| regra de orientação no extrator | 0 (0,818 → 0,818) |
| trocar arco por barra no gerador | **−0,166** (revertida) |
| relabelar gabarito por proxy geométrico (`partes>=2`) | **−0,1**, duas vezes (revertida) |
| classe `junk` no treino | troca entre canais, não ganho (0,805 = 0,805) |
| `lim_x` por margem de barline | apagaria **506 glifos (4,3%)** em 60 linhas |
| **recuperar a casa de dentro do símbolo fundido** (`casa_recuperada`) | **−0,20** (0,889 → 0,687), pior nas 3 sementes; `paolo` 25→10 |
| margem simétrica no recorte do classificador | **−0,02** com os MESMOS pesos (0,865 → 0,844): pré-processamento é entrada do modelo |
| contar notas que **receberam algum tempo** sem gabarito de tempo | número inflado: "sky 40/44" **não é** tempo certo — não existe gabarito de tempo (T0.3) |
| associar a série do marcador do **vídeo inteiro** às notas de **um** quadro | onsets de **outra página**: no `sky2.json` a nota da coluna 2 recebeu **266,1 s**, quando a tela mostrava o compasso 5 (T0.3) |
| misturar `x` da **ROI recortada** com `x` do **quadro** | coluna errada: no `retrato brasileiro` o recorte começa em **x0 = 70 px** e o marcador de 245,5 s caiu na **coluna 3** em vez da 1 (T0.3) |
| `cv2.VideoCapture` fora do leitor | **falha calada em 44 %** do acervo (AV1): **abre**, informa `FRAME_COUNT` e **não decodifica** — `rastrear` devolve 0 amostras, indistinguível de "sem marcador" (T0.3) |
| pareamento da tela do legado por instantes, com exibição = vídeo inteiro | escolheu a tela com mais instantes (5), não a página lida; instante fora da janela contava como erro. Corrigido: pareamento por conteúdo e exibição = `janela_s` |
| fundir componentes da mesma corda com vão <= 0,39 passo (limiar entre algarismos e notas) | **não separa**: algarismos de dois dígitos vão 0,23 a 0,32 passo, e notas diferentes vizinhas chegam a 0,32 e 0,37 (mesmo vão de 7 px do `13` da pág. 8). Página 5 perde 3 notas, casa certa 39 → 37 (revertida; ver `docs/rodadas/0005-casa-dois-algarismos-vao.md`) |
| `--escala larga` (algarismo de 1,0 a 1,4 passo em metade das linhas do gerador) para o `0` perdido nas cordas internas | **0,940** (64/68/71 = 203/216), contra 0,949 dos `oficial_*`: semente 1 cai 2, semente 2 cai 3. Altura ficou mais perto do real (mediana 0,75 contra 0,93), mas dobrou os glifos partidos em 2 componentes (0,30 contra 0,00 no real). Não adotado (ver `docs/rodadas/0009-zero-nas-cordas-internas.md`) |
| `_glifos_por_faixa` só descartar componente em coluna de barline se for fino (w <= 0,25 passo), para recuperar os algarismos que o sakura perde em barline falsa | **pior em tudo**: inventadas MVP 0 → 113, South American 1 → 133, EOB 471 → 588; métrica oficial quebra (contagem muda). Pedaços de barline real passam a virar `1`/`0` (revertida; `data/saida/barline_fina/`) |
| separar barline real × falsa por geometria da coluna (cobertura, trecho contínuo, tinta acima/abaixo do sistema) | **não separa**: 14 falsas × 335 reais em 41 quadros; a melhor regra (abaixo > 0,4 passo ou cobre < 0,85) pega as 14 mas marca **36 reais** como falsas; barline real do retrato desce ~0,46 passo. Falsas concentradas no sakura (8 de 11 colunas); nos ouros, 6 de 338 (`data/saida/barline_coluna/`) |
| salto > 40 px tratado como troca de página, sem conferir sobreposição (C1, rodada 0150) | **errado**: `mr. tabs` e `kenneth` rolam em saltos com sobreposição; a triagem contou 66 rolantes como "não rola" (correção na 0150) |
| mediana do erro como critério de aceite da rolagem (C1, rodada 0153) | **esconde erro grosso**: mediana 0,32 px passa, mas 6 de 13 definidos erram mais de 5 px. Exigir pior caso |
| medir o salto só entre quadros parados (C1, rodadas 0152 e 0153) | **perde a animação** e cria aliasing de período: erros de 690, 779 e 1557 px no `mr. tabs` (compassos alternados de ~340 e 439 px) |
| ajuste fino que trata tudo que não é nota do ouro como fundo (integração, n4 `treinar_ft.py`) | **apaga o X**: no End of Beginning o produto dá ~1 X para 76 regiões marcadas; o modelo da dobra que não viu o vídeo dava 93 |
| abrir a ferramenta do ouro (`tab.ouro_video servir`) com estado desatualizado | **desfaz edições feitas fora dela**: sobe por cima do estado. Corrigido em `bc431c0f`: não sobe se o ouro diverge |
| **braço, nut fora: numerar pelos quadros vizinhos (V) ou pela junção braço-corpo (J)** | **reprova** (1031): 0 e 1 acerto em 16; a regra "nut visível" é enganada pelo próprio erro (o detector põe o nut no 1º traste longe da borda), e a junção por cor pula entre quadros (k = 4 e k = 1 no mesmo vídeo de 12 s) |
| **braço, estágio 2 retreinado com os 8 quadros de nut fora (A5)** | ganho pequeno e instável entre sementes (2 a 4 erros que passam, contra 4 do A4, fora do treino); não ganha na M11b (1031) |
| **braço, conferir a numeração pelas marcações com limiar 4 × mediana** | **0/6** (1034): o tampo claro e a mão sobem a mediana e apagam as marcações, que eram detectadas |
| **braço, marcações com mancha compacta e limiar 4 × Q25** | seguro (510 decisões sem rótulo, 0 disparo), mas **não decide no 1027:q56** (1035): não ajustar de novo nos mesmos 6 falsos |
| **braço, numerar sem o nut pela régua largura do braço ÷ abertura** | **reprova** (1040): 316/382 (82,7 %) calibrada por vídeo, contra 95 %; sem calibração, 36,7 %. Só a câmera fixa do sky guitar fecha (63/63) |
| **braço, escolher o par só por "menos falsos que passam" (critério da 1029)** | **escolhe o modelo que sinaliza tudo** (1037): o `L4_capo_s2` inverte o braço (nut na boca do violão), erra 28 de 32 na M36, sinaliza 28 de 33 na escolha e por isso "vence" com 0 falsos. A escolha precisa de piso de entregues certos |
| **braço, retreino L4 + A6 com a regra do capo, sem sobreamostrar o capo** | **reprova** (1037): nenhum dos 9 pares passa os três critérios. Os pares sãos levam o capo de 4 para 1–2 falsos que passam e de 6 para 9 certos, mas perdem 1 a 3 certos sem capo |
| **braço, escolher o par só na M11b (sem vídeo vertical), mesmo com piso de certos** | **escolhe um par que inverte o braço nos verticais** (1041): 7 de 28 na M36, e o critério 3 reprova (9 certos sem capo contra 15). A escolha precisa de vídeo vertical ou de checagem de orientação |
| **braço, capo sobreamostrado 3× sem exemplos de capo nas casas 4 e 5** | **reprova na 1039** (1041): 15 de 64 falsos que passam; com capo na casa 4 o modelo volta ao nut verdadeiro (14 de 16) e 12 passam sem sinal. O treino tinha ~13 quadros na casa 4 e 1 na 5 |
| **braço, retreino com as marcas de capo de um canal (1039) para outro canal** | **reprova na 1043** (1042): no kimny's guitar, 1 certo e 2 falsos que passam em 40; o nut vai ao nut verdadeiro (17 de 39) ou ao capo (7). Pôr marcas canal a canal não generaliza o capo |
| **braço, capo pelo Grounding DINO tiny sem treino** | **para no desenvolvimento** (1046): 18 de 64 capos da 1039 com ≤ 2 % de falsos; a caixa "capo" cobre 75–99 % do quadro (o violão inteiro) |
| **braço, memória do capo por vídeo (ORB + homografia só no braço)** | **ganho reprova** (1048): 21 certos contra 20 da 1045, 1 falso que passa; o capo levado cai no lugar, mas a conta do nut erra um traste quando o ponto escorrega para o lado do corpo |
| **braço, sinal S4b da tomada com 5 quadros por vídeo** | **tira certos** (1044): na M44, 6 dos 8 certos perdidos pela cadeia vieram da tomada; com poucos quadros por vídeo a referência da tomada erra |
| **tablatura, recorte alto com os pesos `_ger` da leitura comum** | **reprova** (0212): nos 8 ouros, as perdidas vão de 35 para 33, mas as inventadas sobem de 131 para 147 (quase todas no *room 335*); os pesos nunca viram o que fica acima da corda 1 |
| **tablatura, rótulo de ataque `_atqa` (recorte alto + G11–G12) na prova lacrada T8.4** | **reprova** (0211): "sim" falso 33/266 (12,4 %) com o limite de 5 %; custo 131/3477 (3,8 %). Recontado com 4 notas corrigidas pelo dono, 21/254 (8,3 %), ainda reprova. Escapam a nota entre parênteses depois da ligadura, a ligadura desenhada embaixo da corda e o harmônico ligado: o gerador não cobre esses casos |
| **tablatura, rótulo de ataque `_atqr` (gerador com as ligaduras G13–G15 + T8.3 e T8.4 no treino, rótulos revisados) na prova lacrada T8.5** | **reprova** (0214) por custo: 454/3909 (11,6 %) com o teto de 10 %; o "sim" falso passa, 6/138 (4,3 %). Com o `L` 0,01 escolhido nos ouros, o mordente com 1 a 5 % de probabilidade derruba nota comum; mais ligadura no gerador não resolve isso |
| **áudio, casar a tela conferida com o produto só por x (≤ 0,5 passo) na tab que corre de lado** (2021) | 61 das 64 "erradas confirmadas" eram a régua: o quadro do dono e a tela do produto vêm de instantes diferentes, deslocados 80–140 px, e as notas não casam. K1 deu 5,8 % por isso. Alinhar a tela ao quadro antes de casar |

## Lições metodológicas (custaram rodadas)

1. **Semente fixa + determinismo + ≥3 execuções**, reportando média e amplitude. Sem o
   segundo item o primeiro não significa nada (medido: 0,052 de variação na mesma semente).
2. **Meça a amostra antes de gastar treino.**
3. **Confira o significado do número**: "323 notas com tempo" eram **3 instantes**.
4. **Olhe o quadro antes de teorizar** — duas vezes medi o violão achando que era a tablatura.
5. **Rótulo de gabarito só por leitura visual**, nunca por proxy geométrico.
6. **O gargalo é cobertura do gerador, não regra de visão** — medido 6 vezes.

## Ferramentas e artefatos

| caminho | o que é |
| --- | --- |
| `tab/tabseg.py` | grade: 6 cordas, barlines, tokens, 5 famílias + painel escuro |
| `tab/cursor.py` | marcador por faixa (x(t), saltos, sistemas) |
| `tab/sintetico.py` | gerador sintético + treino (`--seed`) |
| `tab/reconhecer.py` | linha → corda, casa, técnica, compasso, tempo |
| `tab/transcrever.py` | vídeo → JSON (painel, grade, marcador, tempo) |
| `tab/avaliar.py` | aferição padronizada — é o número oficial |
| `tab/inventario.py` | varre o acervo (família, painel, marcador) + fallback ffmpeg |
| `tab/caminhos.py` | acervo, gabarito, artefatos: **caminho em um lugar só** |
| `data/gold/gabarito.json` | 96 glifos rotulados à mão, 4 canais |
| `artefatos/` | pesos treinados (**nunca** em `/tmp`) |
| `configs/` | mapa por canal e mapa de símbolos (**a criar**) |
| caixa de presença pela **uniformidade do fundo** na reserva (critério atual) | erra os 9 erros de caixa: 5 braço e 4 pauta, todos com TAB na faixa base; a TAB densa tem mais tinta e perde para o braço liso (Fase 7.1, rodada 0007) |
| caixa pela **fração de papel branco** na reserva (C1) | precisão de caixa **0,976** (123/126) com o gabarito de 7.1 + rótulos visuais do agente (aceite 0,98): não adotado; as 3 caixas erradas são sobre a pauta (VN18, VN20, FP38); MVP sem regressão (Fase 7.1, rodada 0007) |
| separar pauta de TAB pelo **preenchimento médio** dos tokens | sobrepõe: TAB 0,46 a 0,91 contra pauta 0,49 a 0,59 (Fase 7.1) |
| separar pauta de TAB pelo **`tab.digito`** (P de algarismo por token) | marca as cabeças de nota da pauta como algarismo, p≈1,0 nas 4 pautas (Fase 7.1) |
| regra "5 linhas fortes + 1 fraca = pauta" **sozinha**, sobre o recorte re-segmentado do `refinar` | não pega a VN18: no recorte estreitado as 6 linhas da pauta são todas fortes (espaçamento 14); a caixa continuava na pauta (Fase 7.1 C1b) |
| `refinar` que re-segmenta o recorte sem conferir as cordas em y | a re-segmentação troca a TAB pelas linhas da pauta (VN18, FP38); só vale se as cordas em y forem as do candidato (Fase 7.1 C1b) |
| casa de dois algarismos fora da classe do modelo também no glifo de dois componentes (`_casa_das_partes` sem o caminho do par) | um `3` lido como `2`+`0` virou `20`; `oficial_3` caiu 68 → 67/72 (amostra paolo 3). **Revertido**: a casa fora do modelo vale só para o par geométrico de dois tokens isolados (rodada 0008) |

## Próximo passo

1. **símbolos e técnicas por canal** — hoje o extrator **descarta** o símbolo em volta
   do número. Decisão nova: **guardar o glifo cru** e classificar depois, com mapa por
   canal (`configs/simbolos.yaml`);
2. **ampliar o gabarito** para casas 8–24 e mais canais — é o que limita a medição;
3. **tempo onde não há marcador** (~46% do acervo) via áudio;
4. **rodar em escala** nos 3.781 vídeos, com decisão por vídeo;
5. representar **nota ligada `(6)`** e conferir a semântica de cada símbolo por canal.

## Ressalvas (não prometa além disto)

- 96 glifos, 4 canais, **casas 0–7**; aferição **glifo a glifo**, não da música inteira;
- a **casa** dos canais fora do gabarito (ex.: `cifra club`) **não foi aferida** — há
  corda e tempo, casa não;
- **tab ASCII** (Ultimate Guitar) e **partitura de 5 linhas** exigem leitor próprio;
- a métrica **não** cobre técnica nem símbolo: eles são gravados, não aferidos.


## Onde está cada seção (decisão 9001, fase 5)

Em 2026-10-22 as seções foram movidas inteiras, na mesma ordem, para
`docs/estado/`. Aqui ficam só as seções que valem para todas as trilhas (acima),
com a tabela "não repetir". **Seção nova de uma trilha vai no fim do arquivo
dela.** Uma citação antiga ("ver ESTADO.md, Fase 4", "T0.3") se acha pelo título
nesta lista.

### [Tablatura](docs/estado/tablatura.md) — 12 seções

- Tablatura — 2026-10-12 — censo: painel por máscara (TAB de fundo rosa, transparente, escuro)
- Tablatura — 2026-10-12 — censo v2 (com painel por máscara), refeito do cache
- Tablatura — 2026-10-13 — Fase 8 (T8.1): ouro v2 inicial de 7 vídeos novos
- Tablatura — 2026-10-13 — Fase 8: primeiro vídeo fora do sky guitar (pablo romé, Greensleeves) e régua de tempo
- Tablatura — 2026-10-13 — painel: o braço do violão deixa de ganhar da TAB
- Tablatura — 2026-10-13 — gerador: fonte serifada fina (robert lunn), candidato `fina3`
- Tablatura — 2026-10-13 — régua de tempo: cursor em trânsito vale a última coluna passada (decisão do dono)
- Tablatura — 2026-10-13 — marcador pulado: limiar de tinta 0,02 → 0,01
- Tablatura — 2026-10-14 — detector neural de sistema (N1–N4): medido nos 8 ouros
- Tablatura — 2026-10-14 — produto troca de leitor: `rede` é o padrão (decisão 0010)
- Tablatura — 2026-10-15 — fase 8: linhas sob faixa de destaque, e régua com ouro parcial
- Tablatura — 2026-10-16 — onda 1 das frentes (F0, C1, D1)

### [Mãos e braço](docs/estado/maos.md) — 17 seções

- Mãos — 2026-10-12 — M0: censo de mãos (2.798 vídeos, 12 quadros cada)
- Mãos — 2026-10-12 — M1: detector de mãos (Wholebody GPU + MediaPipe)
- 2026-10-12 — Mãos — M2: gabarito de dedos do dono
- 2026-10-12 — Mãos — M3: nota → dedo (esquerda)
- 2026-10-12 — Mãos — M3: abrangência da visão (um vídeo só)
- 2026-10-12 — Mãos — M3: região do braço pelas pontas da mão (reprovada)
- 2026-10-12 — Mãos — M3b: gabarito do braço e geometria (dono)
- 2026-10-12 — Mãos — M3c: braço calibrado pela música
- 2026-10-12 — Mãos — M3c: braço pela música estabilizado (adotado)
- 2026-10-13 — Mãos — M3c: braço pela música fora do MVP (rodada 1008)
- 2026-10-13 — Mãos — M3c: correção do braço pela imagem em pente (rodada 1009, reprovada)
- 2026-10-15 — Mãos — M8: corda sem a mão direita (rodada 1013)
- 2026-10-16 — Mãos — Frentes da pesquisa: ondas 1 e 2 (rodadas 1101–1170)
- 2026-10-16 — Mãos — M9: confirmação fora da amostra da janela fixa (rodada 1014)
- 2026-10-16 — Mãos — nova direção: base de treino das mãos (decisão 1006)
- 2026-10-17 — Mãos — M11a: braço rastreado do quadro-chave (rodada 1015): reprova no CA2
- Mãos — 2026-10-21 — braço: estado consolidado (rodadas 1016–1036, decisões 1009 e 1010)

### [Áudio](docs/estado/audio.md) — 22 seções

- Áudio — 2026-10-13 — A0: áudio em cache e sincronia (rodada 2001)
- Áudio — 2026-10-13 — A1: atraso marcador → som no MVP (rodada 2002)
- Áudio — 2026-10-13 — A1b: o "degrau" de 448 s não é degrau (rodada 2003)
- Áudio — 2026-10-13 — A2: alinhador sem marcador, v1 e v2 (rodada 2004)
- Áudio — 2026-10-13 — folha 1: primeiro gabarito de tempo do som, por escuta (rodada 2005)
- Áudio — 2026-10-13 — colunas que o marcador não acende são ornamentos; v3 reprovada (rodada 2006)
- Áudio — 2026-10-13 — folha 2: vídeos sem marcador; a escuta separa coluna, não ms (rodada 2007)
- Áudio — 2026-10-13 — folha 3 A/B: o tempo do áudio está a ~100 ms (rodada 2008)
- Áudio — 2026-10-13 — A4: o shin izumi falha porque o produto perde a corda 1 (rodada 2009)
- Áudio — 2026-10-13 — A4: alinhador em 10 vídeos sem marcador (rodada 2010)
- Áudio — 2026-10-13 — alarme de leitura no arquivo de áudio (rodada 2011)
- Áudio — 2026-10-13 — rasgueado: colunas abafadas no alinhador v2.1 (rodada 2012)
- Áudio — 2026-10-13 — campanitas: os 17 alarmes restantes; pedidos consolidados à tablatura (rodada 2013, decisão 2004)
- Áudio — 2026-10-13 — campanitas descartado pelo dono
- Áudio — 2026-10-13 — por que o alinhador fica com trecho curto (rodada 2014)
- Áudio — 2026-10-13 — alarme de leitura ignora trecho fora da página (rodada 2014)
- Áudio — 2026-10-13 — andamento com lacunas: não adotado (rodada 2015)
- Áudio — 2026-10-13 — lote 2: 12 canais novos (rodada 2016)
- Áudio — 2026-10-20 — regressão do alinhador com o leitor `rede` (rodada 2017)
- Áudio — 2026-10-21 — transcritor livre Basic Pitch (rodada 2018): reprova
- Áudio — 2026-10-21 — transcritor de violão do Riley (rodada 2019): passa
- Áudio — 2026-10-21 — cruzamento tela × som (rodada 2020): K1 passa só na soma, K2 reprova

### [Partitura](docs/estado/partitura.md) — 25 seções

- Partitura — 2026-10-13 — P0: quantos vídeos têm pauta (rodada 3001)
- Partitura — 2026-10-13 — P1: qual biblioteca lê a pauta (rodada 3002)
- Partitura — 2026-10-14 — comparativo: variantes do Audiveris e SMT sem treino (rodada 3003)
- Partitura — 2026-10-14 — gabarito do dono: o que o Audiveris erra (rodada 3004)
- Partitura — 2026-10-14 — homr completando o Audiveris (rodada 3005)
- Partitura — 2026-10-14 — P3 liberada: homr confirmado pela tab (rodada 3006)
- Partitura — 2026-10-14 — armadura do vídeo automática (rodada 3009)
- Partitura — 2026-10-14 — P3: pareamento partitura × tab (rodada 3010)
- Partitura — 2026-10-14 — saída única da partitura (rodada 3011)
- Partitura — 2026-10-15 — troca de altura desmentida pela tab (rodada 3012)
- Partitura — 2026-10-15 — harmônico não é troca (rodada 3013)
- Partitura — 2026-10-15 — pareada com o produto, em todas as telas (rodada 3014)
- Partitura — 2026-10-15 — armadura, compassos e x de reserva (rodada 3015)
- Partitura — 2026-10-18 — documento final por vídeo com a nota que a tab tem (rodadas 3026, 3027)
- Partitura — 2026-10-18 — onda 1 das frentes fechada (rodadas 3101–3103, 3110, 3160–3162, 3170–3172, 3026)
- Partitura — 2026-10-15 — homr troca o compasso em vídeo sem produto (rodada 3025)
- Partitura — 2026-10-15 — o homr nas notas que faltam, sem tablatura (rodada 3024)
- Partitura — 2026-10-15 — gabarito do dono sem produto: Audiveris em 3 recortes (rodada 3023)
- Partitura — 2026-10-15 — fileira de vigas não corta mais o topo do recorte (rodada 3022)
- Partitura — 2026-10-15 — piloto sem produto: 11 vídeos lidos (rodada 3021)
- Partitura — 2026-10-15 — armadura do vídeo também para leitura com clave e sem armadura (rodada 3020)
- Partitura — 2026-10-15 — `ler --pasta`: partitura de vídeo sem produto (rodada 3019)
- Partitura — 2026-10-15 — pauta com uma linha apagada ganha a 5ª linha (rodada 3018)
- Partitura — 2026-10-15 — paginar resiste a destaque colorido e tira a tablatura (rodada 3017)
- Partitura — 2026-10-15 — páginas de pauta sem o produto da tab (rodada 3016)

### [Histórico antes das trilhas](docs/estado/historico-antes-das-trilhas.md) — 181 seções

- 2026-10-09 — primeira saída COM TEMPO, e a ressalva que vem junto
- 2026-10-09 — o tempo por marcador foi CONFERIDO no vídeo
- 2026-10-09 — o canal mais difícil: `shin izumi`
- 2026-10-09 — a faixa do `sky guitar` existe em 8 de 8; o gargalo virou o MOVIMENTO
- 2026-10-09 — o inventário de símbolos: encanamento certo, coleta poluída
- 2026-10-09 — o portão de tablatura: números fechados (item 2 do objetivo)
- 2026-10-09 — julgamento do movimento consertado: patamares, não passos
- 2026-10-09 — levantamento de marcador: tabela FINAL (regra e recorte consertados)
- 2026-10-09 — escopo do gabarito: 3 canais / 72 glifos (o `raman korshun` saiu)
- 2026-10-09 — delimitador: a coleta de símbolos refeita (antes × depois)
- 2026-10-09 — REGRA DE CURVATURA: medida e REPROVADA antes de entrar no código
- 2026-10-09 — delimitador COMPLETO (tamanho + extensão horizontal): número final
- 2026-10-09 — algarismo × símbolo: medido, e o limiar de confiança está DESCARTADO
- 2026-10-09 — o discriminador "isto é algarismo?" funciona: 0,879–0,940 no canal deixado fora
- 2026-10-09 — discriminador ligado no pipeline: recupera os algarismos, mas tem preço
- 2026-10-09 — limiar do discriminador: varrido, e o conservador DOMINA
- 2026-10-09 — coleta final com o discriminador ligado (e por que a comparação não é direta)
- 2026-10-09 — o dono do projeto auditou o gabarito de símbolos: 48/48 de concordância
- 2026-10-09 — segunda folha de símbolos (17 canais): o lixo se confirma, e a cruz é 15%
- 2026-10-09 — classificador de LIXO: medido e REPROVADO (0,665 de média)
- 2026-10-09 — a regra da "cruz": testada contra os rótulos e REPROVADA (0 de 6)
- 2026-10-09 — primeira vitória real contra o lixo: a HASTE FINA entrou no delimitador
- 2026-10-09 — o delimitador medido no acervo: 1.119 recusas em 33 quadros
- 2026-10-09 — segunda regra que passa: NITIDEZ (o `nada` é borrado, não tem traço)
- 2026-10-09 — as quatro travas medidas juntas: 43 % do que entraria é recusado
- 2026-10-09 — o inventário passa a declarar o que o delimitador recusou (furo fechado)
- 2026-10-09 — coleta com as QUATRO travas: 37 % barrado, e um sinal ruim aberto
- 2026-10-09 — CORREÇÃO minha: o "sinal ruim" do `mr. tabs` era leitura errada de campo
- 2026-10-09 — partitura: terceira hipótese REPROVADA, e o diagnóstico muda o alvo
- 2026-10-09 — a origem dos recortes de partitura: DOIS painéis errados, com prova visual
- 2026-10-09 — apertar a tolerância de espaçamento: MEDIDO e REPROVADO (custa 21 % dos painéis)
- 2026-10-09 — validar o painel pelo CONTEÚDO: quinta hipótese REPROVADA
- 2026-10-09 — folha 3 (coleta JÁ com as 4 travas): o lixo caiu de 60 % para 56 %, e as CRUZES ficaram
- 2026-10-09 — o dono marcou 46 símbolos e me deu o vocabulário e as REGRAS
- 2026-10-09 — o aviso do dono CONFIRMADO por medição: a janela corta o arco apagado
- 2026-10-09 — o aviso do dono CONSERTADO: janela larga, recall 123/123 nas três sementes
- 2026-10-09 — o filtro positivo LIGADO (e um bug meu de contagem, corrigido na hora)
- 2026-10-09 — o detector separa no gabarito e FALHA no pipeline: o que já eliminei
- 2026-10-09 — o dono identificou o falso positivo: BARRA VERTICAL não é símbolo (e virou regra)
- 2026-10-09 — coleta com filtro positivo + regra da barra: 2.242 → 934 símbolos, e a precisão medida
- 2026-10-09 — recorte do componente: implementado, medido, e NÃO resolveu os 58 %
- 2026-10-09 — decisão por componente: também REPROVADA, e a hipótese que sobra é sobre os DADOS
- 2026-10-09 — hipótese dos DADOS REFUTADA com prova direta (IoU 1,00): o bloqueio é outro
- 2026-10-09 — o dono me corrigiu: eu lia só os significados MAIS FREQUENTES das marcas
- 2026-10-09 — A CAUSA: a coleta amostra vídeos que o dono NUNCA marcou (interseção = 1 de 51)
- 2026-10-09 — tablaturas dos vídeos DA COLETA, prontas para marcar (27, todos os 17 canais)
- 2026-10-09 — a coleta passa a DECLARAR se treino e teste falam da mesma distribuição
- 2026-10-09 — TRÊS bugs meus no mesmo campo, e o número que ele passou a mostrar
- Tentativa de trava de FORMA (sem o dono), medida e NÃO conclusiva
- 2026-10-09 — o número que resume o goal: precisão 77–91 % no treino, 27 % na coleta
- 2026-10-09 — as marcas nos vídeos DA COLETA: precisão 89–91 % (era 27 %)
- 2026-10-09 — coleta com o modelo alinhado: precisão no olho 29 %, e o motivo é o RECORTE SALVO
- 2026-10-09 — conserto do recorte salvo: salvar a JANELA JULGADA (e a amostra mudou de cara)
- 2026-10-09 — coleta LIMPA com a janela julgada: 1.018 símbolos, precisão no olho 27 %
- 2026-10-09 — o que faltava medir: os recortes da coleta são MISTURA (e o modelo aprova negativo)
- 2026-10-09 — teste fim a fim: NÃO deu 1 de 256 por bug MEU de coordenada (não registrado como medida)
- 2026-10-09 — o bug do `1 de 256` era MEU (y somado duas vezes), achado DESENHANDO
- 2026-10-09 — o modelo é CONSISTENTE, e ele aprova a região do SÍMBOLO (y acima da 1ª corda)
- 2026-10-09 — ENCONTRADO: os meus NEGATIVOS foram recortados do LUGAR ERRADO do quadro
- 2026-10-09 — negativos corrigidos: o LOCA CAIU como previsto (0,77–0,79) e o número é esse
- 2026-10-09 — fim a fim com o espaço CERTO: 0,10 — e a pista de onde ele aprova errado
- 2026-10-09 — trava da FAIXA DAS CORDAS: medida antes de adotar, 523 de 523 dentro, zero colateral
- 2026-10-09 — com a trava da faixa: fim a fim vai de 0,10 para 0,15 (e a distância segue)
- 2026-10-09 — OLHANDO: o modelo aprova ESPAÇO VAZIO (e isso explica a distância inteira)
- 2026-10-09 — a classe da janela vazia no treino: falso positivo cai 30 % e o fim a fim sobe a 0,19
- 2026-10-09 — OLHANDO os 108: ainda é espaço vazio, e agora em pontos específicos
- 2026-10-09 — zoom de 5×: os aprovados são VAZIO mesmo — e a diferença é a POSIÇÃO na lacuna
- 2026-10-09 — vazio com deslocamentos múltiplos: hipótese REFUTADA (o fim a fim não se move)
- 2026-10-09 — OLHANDO (modelo atual, metade direita): ele aprova a FAIXA VAZIA ENTRE AS PAUTAS
- 2026-10-09 — os DOIS erros de extração que o dono apontou: CORRIGIDOS e conferidos no olho
- 2026-10-09 — FECHAMENTO: três variações de negativo vazio, e a precisão da coleta fica em 0,17
- 2026-10-09 — FECHAMENTO DO DETECTOR: os números finais, com o custo declarado
- 2026-10-09 — LOVO refuta "generalização entre vídeos" e revela a causa REAL: o símbolo não é candidato
- 2026-10-09 — ACHEI a condição que escondia o símbolo (e ela é o mesmo erro de sempre)
- 2026-10-09 — o arco se FUNDE com a linha: a medição que fecha o diagnóstico
- 2026-10-09 — retirada das linhas de corda: implementada, medida e NEUTRA (desligada)
- 2026-10-09 — retirada das linhas de corda: implementada, medida e NEUTRA (desligada)
- 2026-10-09 — associação apertada: 5 % dentro de token, 56 % com componente fora — e o alarme refutado
- 2026-10-09 — motivos por componente: gigantes (60-86 passos) — com uma RESSALVA declarada
- 2026-10-09 — CORREÇÃO DE INTEGRIDADE: a minha "reversão" da rodada 2 NÃO pegou
- 2026-10-09 — apagar as FAIXAS das cordas: implementado (com leitura do arquivo), medido e REPROVADO
- 2026-10-09 — A CAUSA RAIZ, vista na máscara: o arco NÃO ESTÁ na máscara que o pipeline escolhe
- 2026-10-09 — união das máscaras para os glifos: gabarito INTACTO, marcas paradas
- 2026-10-09 — crua vs união, lado a lado: no C16 o arco ESTÁ na máscara; a perda é DEPOIS
- 2026-10-09 — o rastreamento de UM caso, e a combinação que dobra o recall (e quebra o gabarito)
- 2026-10-09 — SEPARAR OS DOIS CAMINHOS: o símbolo acha 149 de 163 marcas, com a forma de arco
- 2026-10-09 — FECHAMENTO DO GOAL: o diagnóstico está fechado; a ligação dos dois caminhos é o que falta
- 2026-10-09 — SEGUNDA PASSADA LIGADA: gabarito fica (0,917/0,986/0,944) — e o recall sobe pouco
- 2026-10-09 — O RECALL ALVO FOI ATINGIDO (0,40) — e a minha medição escondia isso
- 2026-10-09 — varredura do limiar: NÃO é a alavanca (as distribuições se sobrepõem)
- 2026-10-09 — filtro de FORMA antes do modelo: melhora precisão E recall (ganho de Pareto)
- 2026-10-09 — varredura da FORMA: a largura decide, a altura é inerte, e o ponto fica em 1,5
- 2026-10-09 — terceira alavanca (entre cordas): MEDIDA E REPROVADA; as três alavancas estão esgotadas
- 2026-10-09 — AUDITORIA: a discrepância 30 x 178 NÃO EXISTE (erro meu de leitura) e a tolerância inflava o "149"
- 2026-10-09 — OS 170 BURACOS TÊM NOME: o meu filtro de forma é quem os cria
- 2026-10-09 — dedupe por janela: ligado, medido e INERTE na quantização fina
- 2026-10-09 — dedupe com quantização GROSSA: também NÃO resolve (a hipótese está morta)
- (C) página de auditoria — FEITO a pedido do dono
- 2026-10-09 — A AUDITORIA DO DONO: o modelo acertou 30 de 30. O errado é o meu gabarito.
- 2026-10-09 — (a) PARAR DE MEDIR ERRADO: três gabaritos, medidos lado a lado
- 2026-10-09 — (c) AUDITORIA DO POOL ABERTO montada: 1.869 candidatos, 1.258 aprovados pelo modelo
- 2026-10-09 — ferramenta nova: `python -m tab.auditoria` (e o bug que eu peguei nela antes de commitar)
- 2026-10-09 — (b) adiantado pelo lado seguro: metade dos buracos tem TINTA, então a perda é no delimitador/agrupamento
- 2026-10-09 — CORREÇÃO: no pixel exato os buracos NÃO têm tinta — a perda é a máscara, não o delimitador
- 2026-10-09 — (b): 39 % dos buracos TÊM sinal (5× a taxa-base) e são consertáveis por limiar local
- 2026-10-09 — contraste local: recupera 39 % dos buracos, custa menos — e é NEUTRO no fim a fim
- 2026-10-09 — o rastreamento do componente: os "buracos" NÃO são buracos, são o MEU FILTRO DE FORMA
- 2026-10-09 — a tabela da decisão, na régua honesta (`_6`), com a precisão declarada como PISO
- 2026-10-09 — MULTI-CORDA: 1 %, não 75 % — e a imagem mostra o que é (slides, dígitos fundidos, chaves cortadas)
- 2026-10-09 — TAMANHO DO PROBLEMA no acervo da coleta: o corte na borda (8 %) é 8x o multi-corda (1 %)
- 2026-10-09 — OLHEI a folha da borda: o corte é de DÍGITO e de LINHA, não de símbolo (14ª correção)
- 2026-10-09 — os GLIFOS não são cortados (1 em 1.455) — e a queixa do dono é a JANELA do símbolo (15ª correção)
- 2026-10-09 — varrer a JANELA: crescer é neutro-para-pior — porque o modelo foi TREINADO na janela pequena
- 2026-10-09 — o gabarito TEM as coordenadas: o retreino na janela nova é tarefa conhecida e pequena
- 2026-10-09 (pós-reboot) — infraestrutura, conjunto novo e modelos treinados na janela 3,0x2,5
- 2026-10-09 — GPU/CDI fora do ar depois do reboot, `torch.load` sem `map_location`, e uma medição que NÃO vale
- 2026-10-09 — o conserto da captura (janela 3,0x2,5 + RETREINO) NÃO muda nada: 78 acertos nos dois lados
- 2026-10-09 — FOLHA DO SÍMBOLO INTEIRO: o "corte" era a minha exibição, e ele se resolve de graça
- 2026-10-09 — O DONO ROTULOU A FOLHA 0: só C06_008, C06_009 e C06_010 não são símbolos — e são DÍGITOS DE ACORDE
- 2026-10-09 — O ARPEJO: o dono apontou que o TAMANHO do símbolo É A INFORMAÇÃO (e a imagem confirma o corte)
- 2026-10-09 — (a) RECORTE DO SÍMBOLO: componente + janela fixa — e o arpejo aparece INTEIRO com as cordas
- 2026-10-09 — recorte: lateral estreito (o dono achou largo) e a causa REAL do arco largo
- 2026-10-09 — o arco largo: apagar as faixas a 0,12 passo NÃO muda nada (a faixa é mais fina que a linha)
- 2026-10-10 — PILOTO de ponta a ponta: a cadeia estava QUEBRADA (2 bugs) e o MARCADOR não aparece
- 2026-10-10 — DISTRIBUIÇÃO DE FORMAS DO MARCADOR (17 canais, 1 vídeo cada) — o número que define o desenho
- 2026-10-10 — OLHEI os "ausente": o grupo se DIVIDE, e há marcador por COR NO ALGARISMO (com imagem)
- 2026-10-10 — O SEGUNDO OBSERVADOR É VIÁVEL: um algarismo colorido (22,7) e TODOS os outros em ZERO
- 2026-10-10 — A REGRA DO ESTADO FUNCIONA: sky 0 -> 29 de 38, e o sem-marcador continua 0 COM MOTIVO
- 2026-10-10 — OS DOIS OBSERVADORES FUNCIONAM, com a MESMA regra
- 2026-10-10 — LINHA DE BASE LIMPA: o gabarito de algarismo está intacto ANTES da integração
- 2026-10-10 — DESCOBERTA QUE MUDA A INTEGRAÇÃO: a regra dos patamares JÁ EXISTIA
- 2026-10-10 — A REGRA ÚNICA EM CINCO VÍDEOS: 96 % no `salta`, e DUAS FORMAS AINDA SEM EXPLICAÇÃO
- 2026-10-10 — OS DOIS CASOS SEM EXPLICAÇÃO: a série explica, e NENHUM é a regra
- 2026-10-10 — o "pisca" da minha distribuição está ERRADO: é quase-ausência, não forma
- 2026-10-10 — INTEGRAÇÃO FEITA: o `sky guitar` saiu de 0 para 40 de 44 notas datadas
- 2026-10-10 — CRITÉRIO DUPLO CUMPRIDO: o gabarito NÃO caiu e o sem-marcador continua DECLARADO
- 2026-10-10 — a ÚLTIMA incógnita da integração de cor: a duração JÁ é obtida (e não é devolvida)
- 2026-10-10 — OBSERVADOR DE COR LIGADO NO PRODUTO: mr. tabs de 0 para 16, e o gabarito segue INTACTO
- 2026-10-10 — FASE 0 / T0.4: `make gate` que BARRA (e o plano derrubava o gate da árvore limpa)
- 2026-10-10 — FASE 0 / T0.2: `MODELO_PADRAO` passa a `oficial_3` (68/72) — e o antigo dava 72/72 = 1,000
- 2026-10-10 — FASE 0 / T0.3: os números de TEMPO de 2026-10-10 ficam NÃO VALIDADOS (com as quatro evidências)
- 2026-10-10 — FASE 1 / T1.1 (passo 1: LER antes de escrever): o que o `tab/leitor.py` vai REAPROVEITAR
- 2026-10-10 — FASE 1 / T1.1 FEITO: `tab/leitor.py` — e o AV1 passa a decodificar (60 quadros em 10 s)
- 2026-10-10 — FASE 1 / T1.2 (começo): `inventario` delega ao leitor — e `tab.avaliar` deu IGUAL
- 2026-10-10 — FASE 1 / T1.2: `varredura.Leitor` vira SUBCLASSE do leitor único (9 usos restantes em 5 arquivos)
- 2026-10-10 — FASE 1 / T1.2: o esqueleto do `cursor.rastrear` (para o patch ser cirúrgico, não reescrita)
- 2026-10-10 — FASE 1 / T1.2 (cursor): `rastrear` agora lê pelo leitor único
- 2026-10-10 — FASE 1 / T1.2 (fim): zero `VideoCapture` fora do leitor
- 2026-10-10 — Fase 1 / T1.3: um espaço de coordenadas (o do quadro)
- 2026-10-10 — Fase 1 / T1.4: colunas (o acorde é uma coluna). A Fase 1 fecha.
- 2026-10-10 — FASE 2 / T2.3: `tab.avaliar_video` — a régua do produto
- 2026-10-10 — Fase 2 / T2.1+T2.2: ferramenta do ouro de vídeo (`tab/ouro_video.py`)
- 2026-10-10 — Fase 2 / conciliação de x: régua e transcrever comparam pelo CENTRO do token
- 2026-10-10 — relato do dono: caixa do ARCO de ligadura não cobre o símbolo inteiro (dívida da Fase 10)
- 2026-10-10 — LINHA DE BASE do produto contra o ouro de vídeo (corrigida: fase 2, correção da régua)
- 2026-10-10 — FASE 3: `tab/telas.py` (telas = páginas de tablatura no tempo)
- 2026-10-10 — FASE 2: ouro v2 (páginas pelo `tab.telas`, notas do dono herdadas do v1)
- 2026-10-10 — FASE 3 (conserto): transição/oclusão não vira página; `quadro_ref_s` no meio da maior exibição
- 2026-10-10 — ouro v2 e medições com ele
- 2026-10-10 — Fase 4: casa de dois algarismos. Limiar de fusão por vão NÃO separa (revertido)
- 2026-10-10 — Fase 4: casa de dois algarismos pela forma (aceita, 481 -> 484)
- 2026-10-10 — Fase 7.0: precisão do detector de presença no `portao.json` (só medição, detector intacto)
- 2026-10-10 — Fase 7.1: gabarito de caixa por quadro (dono) e candidato de reserva C1 NÃO adotado (aceite 0,976 < 0,98)
- 2026-10-10 — Fase 7.1 (C1b): C1 ADOTADO com regra de pauta (5 x 6 linhas) e `refinar` que mantém as cordas
- 2026-10-10 — Fase 4: `tab/video.py` (todas as telas, JSON v1) e a régua que pareia tela sem instante
- 2026-10-10 — GPU no podman: `devices: nvidia.com/gpu=all` (CDI por device)
- 2026-10-10 — Gerador: casas 11,13,16,18,20,22,23 (cobertura do sintético; NÃO adotado)
- 2026-10-10 — Fase 4: arco de ligadura não vira nota (inventadas 21 -> 1; casa e revocação mantidas)
- 2026-10-10 — FASE 5 / T5.1–T5.5: tempo por exibição. Estado 33 de 40, tempo falso 0. CA de estado (≥ 38/40) NÃO cumprida; D2 em impasse
- 2026-10-10 — FASE 5 (continuação): a causa do atraso era do QUADRO, não do carimbo. Estado 33 → 37 de 40, tempo falso 0
- 2026-10-10 — FASE 5 (fechamento do estado): régua aceita o rótulo até 1 quadro antes da coluna. Estado 37 → 39 de 40, tempo falso 0
- 2026-10-10 — FASE 6: a folha estava certa, o JSON estava 2 a 3 quadros cedo. Conserto no tempo: folha 30 de 30
- 2026-10-10 — Fase 4: casa 13 (par de algarismos sem classe no modelo). Inventadas 1 → 0
- 2026-10-10 — MVP APROVADO pelo dono em 2026-10-10
- 2026-10-10 — Fase 5: marcador falso da moldura verde REJEITADO por aparência (faixa translúcida)
- 2026-10-10 — Fase 7.1: piloto do censo e painel escuro (teto de passo 45 → 55 px)
- 2026-10-11 — Fase 7.1: FN05 rotulado pelo dono e caixa aparada à TAB (aceite de caixa 0,984)
- 2026-10-11 — Fase 7.1 (cifra club): TAB escura pelo caminho aditivo, e gabarito do dono sobre VN05/VN06/VN12/VN16
- 2026-10-11 — Cache de quadros do censo (T-cache): medido, e a passada densa fica como pendência
- 2026-10-11 — violaodecria e tv cifras FORA da Fase 8 (decisão do dono)
- 2026-10-11 — Fase 7 (T7.1–T7.3): censo completo, tabela por canal, D7 e conferência de 30


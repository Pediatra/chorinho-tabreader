# ESTADO.md — número oficial, o que está medido e o que falta

Documento de entrada do projeto. **Todo número aqui é média de ≥3 sementes**, nunca
execução única — sem isso o mesmo código já deu 0,729 e 0,854. O histórico completo
das 65 rodadas está em [`docs/HISTORICO.md`](docs/HISTORICO.md).

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

## Noite de 2026-10-08/09

O acervo cresceu para **3.993 vídeos / 183 GB / 17 canais** (ainda baixando). O que
mudou, com o número que sustenta cada item:

| o que | resultado medido |
| --- | --- |
| **varredura do acervo novo** | **96,5 % com tablatura** (3.855/3.993), em 69,5 min |
| **cursor no quadro inteiro** | 69 de 3.993 — o portão exige faixa de ≥50 % da **imagem** (540 px) e o cursor tem a altura do painel (~150 px) |
| **cursor no ROI da faixa** | muda onde o detector olha, mas **não basta**: no mesmo vídeo as detecções eram **artefato** (banda parada em x=0–99 por 5 s na borda do painel e bandas em x≈900–1084, fora do painel, que é 0–594). Aquele vídeo **não tem marcador** |
| **escolha do painel** | o critério antigo (glifos centrados) escolhia o **braço do violão**; com uniformidade do fundo (0,888 × 0,842) escolhe a tablatura — `tab/painel.py`, implementação única |
| **recorte em x** | exigir 4+ das 6 cordas na mesma coluna estreita o painel ao retângulo real |
| **efeito do recorte na máscara** | mesmo quadro: recorte de 570 px → máscara `otsu` → **3 algarismos reais**; recorte de 1920 px → `contraste_k31_d25` → 36 tokens, **33 de lixo** |
| **ponta a ponta (`sky guitar`)** | **3 notas, corda 5, casas 0 / 2 / 3**, confiança 0,996 / 0,931 / 0,999 — exatamente o que está no quadro |
| **símbolo cru** | implementado: PNG deduplicado por hash, caixas dos componentes, larguras em passo, top-3 de classes |
| **recuperar a casa de dentro do símbolo** | medido e **reprovado**: 0,889 → 0,687 |
| **MusicXML** | exportador pronto (score-partwise 4.0, clef TAB, `staff-tuning`, `technical`), com a duração inferida **declarada** |

**Tempo por travessia (novo, `tab/tempo.py`):** medido no `iwaki/henze`, o marcador
**desliza** ~17 px por 0,25 s (65 px/s, banda de 6 px, matiz 102) — então o onset é
**invertível**: a nota começa quando ele cruza o `x` dela. Em diagnóstico controlado isso
deu **8 instantes distintos** onde o método antigo dava 1. A integração no pipeline ainda
não fecha: na janela 113–153 s daquele vídeo o detector devolve uma banda **parada**
(deslocamento 38 px em 65 amostras), e o pipeline declara `tempo.medido: false` —
conservador de propósito, porque tempo errado é pior que tempo ausente. 8 testes cobrem o
método (interpolação, x fora da série, marcador parado, salto entre trechos).

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

# tools/ — camada de visão computacional da transcrição

Todos os comandos rodam com o interpretador do projeto:

```bash
cd /var/home/gabriel/Projects/chorinho-dataset
.venv/bin/python tools/<script>.py ...
```

O ambiente (`.venv`, Python 3.14) já tem `torch 2.14.1+cu130` com CUDA funcionando na
RTX 3060 Ti, `transformers 5.19`, `opencv 5.0` e `numpy 2.5`. Para recriar:

```bash
python3 -m venv .venv
.venv/bin/pip install torch torchvision opencv-python-headless numpy pillow transformers accelerate einops safetensors
```

## `tabseg.py` — grade da tablatura (estrutura)

Transforma um recorte (ou um quadro de vídeo) com uma pauta de tablatura em uma grade
determinística: linhas de corda, barlines, passo e caixas de glifos com corda e coluna.

```bash
.venv/bin/python tools/tabseg.py parts/clipes/-6rawhontyg_000120_000200/linha_01_tablatura.png \
    --debug /tmp/seg.png --json /tmp/seg.json
# linhas_y=[16, 46, 76, 106, 136, 166] passo=30.00 barlines=[2, 519, 939, 1360, 1744] glifos=15 avisos=[]
```

O que ele já trata, por ter sido medido nos dados reais: fundo claro **e** escuro (cascata
de máscaras validada pelo resultado), linhas sólidas **e** tracejadas, passo entre cordas de
12 a 45 px, rótulo `T A B`, barlines, fragmentos de corda e **acorde empilhado** (os glifos
são extraídos dentro da faixa de cada corda, porque algarismos de cordas vizinhas se tocam
e viram um componente só).

Desempenho: **163 de 163** recortes com as 6 cordas detectadas e **11.594 glifos** (contra
6.882 antes da extração por faixa: os ~4.700 a mais são notas de acorde que estavam sendo
fundidas, não erro de contagem).

**Cuidado conhecido:** o teste de "6 linhas regulares" sozinho **aceita partitura de 5
linhas** (medido em 4 recortes do acervo) e, num quadro com partitura em cima e TAB embaixo,
pode escolher a pauta errada. A escolha hoje é feita pelo conteúdo (glifo centrado na
linha), o que resolve a maioria dos casos, mas ainda erra numa das capturas. O portão
definitivo "isto é tablatura?" deve ser um classificador pequeno sobre a linha inteira.

## `cursor.py` — cursor de execução (tempo)

Rastreia a banda vertical colorida que percorre a partitura e devolve `x(t)`.

```bash
.venv/bin/python tools/cursor.py parts/clipes/-6rawhontyg_000120_000200/clip.mp4 \
    --roi 0 470 --json /tmp/cursor.json
```

A `--roi` é a faixa que contém pauta + tablatura (varia por canal: 0–470/0–505 quando a
notação está no topo; ~719–1080 quando está na base). Saída: cobertura, x mínimo e
máximo, largura do núcleo da banda, matiz, **número de saltos**, salto mediano,
retrocessos (trocas de sistema) e intervalo mediano entre saltos.

Ponto medido e importante: o cursor **não desliza**, ele **salta de nota em nota** e fica
parado durante a nota (100 saltos em 80 s, salto mediano de 109 px, patamar de ~1 s).
Logo, o instante de cada nota é o início do patamar, com precisão de um quadro (33 ms).

## `glyphset.py` — inventário de glifos

Extrai todos os glifos do acervo, filtra lixo (fragmento de corda, barline, rótulo) e
agrupa por forma.

```bash
.venv/bin/python tools/glyphset.py --saida /tmp/glifos --montagem /tmp/clusters.png
```

Resultado de referência: 163 linhas → **6.882 glifos válidos** e 530 componentes
descartados (restos de corda e ruído). O alfabeto é algarismos 0–9 (e números de 2
dígitos) mais os símbolos de técnica descritos na documentação. O cluster de forma mais
frequente reúne 327 glifos de **11 canais diferentes**: o alfabeto é comum entre canais.

## `inventario.py` — o que existe no acervo real

Varre uma raiz de vídeos, procura a grade de tablatura em 3 faixas do quadro
(topo/meio/base) e tenta achar o cursor; agrega por canal.

```bash
.venv/bin/python tools/inventario.py --raiz "/run/media/gabriel/3014CD4714CD1130/chorinho" \
    --por-canal 30 --saida /tmp/inventario.json
```

Resultado de referência (319 vídeos, 12 canais): **96 % com tablatura, 95 % com cursor,
0 falhas de decodificação**. Detalhe que importa: **140 dos 319 quadros só foram lidos
pelo `ffmpeg`** (AV1 sem aceleração no OpenCV) — sem esse fallback quase metade do acervo
seria ignorada em silêncio.

## `ouro.py` — gabarito verificado a partir do acervo real

Extrai um quadro do vídeo, acha a grade, recorta a TAB ampliada e salva **cada glifo
isolado com índice** para leitura humana.

```bash
.venv/bin/python tools/ouro.py --saida /tmp/ouro --n 10 --por-canal 1
```

Os rótulos lidos à mão ficam em `gold/gabarito.json` (42 glifos em 2 canais até agora).
Rotular glifo isolado é bem mais confiável do que ler a linha inteira.

## `glyph_bench.py` — aferição do classificador

Monta um conjunto rotulado casando os glifos segmentados com os tokens de prata
(`tab_tokens.json`, por corda e ordem), treina uma CNN de ~74 mil parâmetros e afere
**inclusive em canais que não entraram no treino**.

```bash
.venv/bin/python tools/glyph_bench.py --epocas 30 --saida /tmp/glyphbench
```

Resultado de referência: acurácia **0,87** nos canais vistos e **0,63–0,64** em 2 canais
novos. O gargalo é generalizar entre canais, não a capacidade do modelo — daí a
recomendação de calibrar por canal (banco de templates) em vez de aumentar o modelo.

**Ressalva metodológica:** os tokens de prata são gabarito fraco (o pipeline antigo
aceitou 46,7 %–93,0 % dos glifos, perdeu harmônicos visíveis e recortou região errada em
2 linhas). Esses números servem para **comparar caminhos**, não como acurácia absoluta.
O passo nº 1 da próxima rodada é um gabarito pequeno verificado à mão.

# 3160 — D1: amostra sorteada para o gabarito novo

Frente D (amostra para um gabarito que vale para o acervo), item D1 de
`docs/pesquisa/partitura-frentes.md`, seção 7. Briefing da onda 1
(`docs/pesquisa/partitura-onda1-briefings.md`).

**Sorteio feito antes de qualquer leitura de vídeo.** Feito na cópia isolada
`chorinho-partitura-env/repo`. Módulo: `tab/partitura_amostra.py`. Saída:
`data/saida/part_frentes/fd_gabarito/amostra.json` (com `escolhidos`, `reservas`, `semente`,
`estratos` e a população por canal).

**Sem commit:** esta máquina não tem git. O `amostra.json` é o registro, mas não está
commitado. O briefing manda commitar antes do `paginar`; isso não foi possível aqui.

## Método (no código)

- **Peso**: `extrapolacao` de `data/saida/partitura/p0/resumo.json`.
- **Fortes** (≥ 5): 10 canais, 1 vídeo cada: sky guitar, robert lunn, guitar dell'arte, iwaki,
  pablo romé, serge kottelat, transcriptor, paolo d'angelo, ギタロー ⧸ guitarous e tv on guitar.
- **Proporcionais** (0 < extrapolação < 5): kimny's guitar (3,6), lonelypicker (1,0) e mr. tabs
  (1,0). Dividem 30 vídeos pelo método do maior resto. Quando um canal tem menos vídeos que a
  cota, o excedente vai para os outros canais, na mesma proporção (por isso lonelypicker ficou
  com 2 e não com a cota inicial de 5).
- **População**: vídeos de cada canal no acervo de hoje, menos os gabaritos (`itens.json` de
  `p1` e de `conferencia_sem_produto`) e os vídeos do piloto sem produto (campo `video` do
  `.partitura.json` de cada pasta).
- **Semente**: `random.Random(f"{semente}:{canal}")`, com a semente do P0 (`0`). Reservas: os
  10 seguintes de cada canal, na ordem do sorteio.
- **Canais fora do P0**, listados e fora do sorteio: `tv cifras`, `violaodecria`.

## Resultado do sorteio

- 40 vídeos escolhidos, 13 canais (10 fortes + kimny's guitar 22, mr. tabs 6, lonelypicker 2).
  Cada cota foi cumprida. Nenhum canal ficou com cota faltando.
- Determinismo: duas execuções dão o mesmo `amostra.json` (`cmp`).

## Leitura: bloqueada em parte (AV1)

Teste de leitura do primeiro quadro de cada um dos 40 vídeos escolhidos (`cv2`):

- **25 lidos**, **15 falham**. A falha é `Your platform doesn't support hardware accelerated
  AV1 decoding`: o OpenCV não decodifica AV1.
- `ffmpeg` não está instalado nesta máquina e não dá para instalar sem `sudo`. O AGENTS.md diz
  que `ffmpeg` é dependência de trabalho: 44 % do acervo é AV1, e sem ele quase metade do acervo
  fica em branco.
- Consequência: o `paginar` não roda nos 15 vídeos AV1 sorteados. Os 25 legíveis poderiam ir ao
  `paginar`, mas não foi feito nesta rodada.

O briefing manda parar se o `paginar` não achar página em mais de 25 % dos vídeos sorteados.
Com 15 de 40 (37,5 %) sem leitura possível, a condição de parada já vale para o conjunto
completo, antes mesmo de tentar a página.

## Não feito

- `paginar`, `ler_pasta`, Audiveris e homr nos vídeos sorteados (depende de `ffmpeg` para AV1 e
  de container para o Audiveris).
- Itens da conferência do dono e servidor na porta 8121: não montados.
- Commit do `amostra.json` antes da leitura: sem git.


## Tentativa de paginar (2026-10-17)

`python -m tab.partitura_video paginar --video "kimny's guitar/[ tab ] libertango ...mp4"` (um
dos 25 legíveis pelo `cv2`) falha antes de ler qualquer quadro: `_verificar_video` chama
`ffprobe` para a duração e levanta `RuntimeError: ffprobe não leu a duração`.

O mesmo vale para o caminho de leitura inteiro: `tab.leitor.quadro_em` e `quadros` usam `ffmpeg`
em software (o docstring diz que lê 100 % do acervo). Só `quadros_cv2` não depende de `ffmpeg`,
e ele não lê AV1. Trocar o leitor por `cv2` mudaria a medida (a regra 9 do AGENTS.md diz que a
leitura é parte da medida). Por isso a D1 não foi continuada.

**Bloqueio real: sem `ffmpeg` e `ffprobe`, o `paginar` não roda em nenhum vídeo da amostra.**

## Revisão da sessão principal (2026-10-17)

Rodado de novo no container, na `main`: a saída deu igual byte a byte à da cópia (`cmp`).

O `amostra.json` vai no mesmo commit desta rodada, antes de qualquer `paginar`. No container há `ffmpeg`, então os 15 vídeos AV1 decodificam lá. O bloqueio era só da cópia, e a leitura segue na D1.


## Revisão 2 (2026-10-17): sorteio corrigido, lista antiga inválida, paginar da lista nova

**Lista antiga (commit `d55857f7`): inválida.** O sorteio usava as 30 vagas proporcionais só
nos canais kimny's guitar, lonelypicker e mr. tabs. Decisão do dono: a proporção vale para
**todos os canais com pauta no P0**. Nada mais é lido da lista antiga; o log dela foi
arquivado como `*_v1_INVALIDA`.

**Sorteio corrigido: commit `27e40dbf`** (branch `part/d1-amostra`), semente 0, maior resto,
reservas na ordem. 40 vídeos em 13 canais, nenhuma cota faltando. Committed antes do paginar.

**Paginar da lista nova** (primeira passada, 40 sorteados): 5 sem página com pauta
(12,5 %, abaixo do limite de 25 %, a rodada continua):
- `five beautiful` (guitar dell arte): só o violonista, sem pauta em nenhum instante amostrado.
  Trocado.
- `milonga` (transcriptor): só tablatura. Trocado.
- `小さな恋のうた` (ギタロー): só tablatura. Trocado (9 reservas sem pauta, a 10ª tinha).
- `5 miniatures` e `garden of bliss` (robert lunn): **têm pauta visível**. O `paginar` deu
  erro `zero-size array` em `_forca_de_linha`. Trocados por engano na primeira rodada.

**Causa do erro:** a 6ª linha abaixo da pauta cai abaixo da borda do quadro. A faixa de linhas
fica vazia, e o `min` do numpy falha. **Correção:** o runner `tab/partitura_amostra_paginar.py`
troca `_forca_de_linha` em tempo de execução por uma cópia que só retorna 0 nesse caso. O
`tab/partitura_video.py` não foi editado. Quando a faixa não é vazia, o resultado é igual ao
original. Com a correção: `5 miniatures` 30 páginas (29 com pauta); `garden of bliss` 12 páginas
(12 com pauta).

**Lista final** (`data/saida/part_frentes/fd_gabarito/amostra_final.json`): 40 vídeos. Os dois
robert lunn voltam ao sorteio. As três trocas, todas de vídeo sem pauta, são:
- five beautiful → `la vita è bella` (guitar dell arte): pauta visível a partir de ~1000 s.
- milonga → `quiero ser tu sombra` (transcriptor): pauta visível.
- 小さな恋のうた → `空も飛べるはず` (ギタロー): pauta visível.

Olhadas de confirmação: `olho_sem_pauta.jpg`, `olho_five_beautiful.jpg`,
`olho_reservas_entrada.jpg`, `olho_la_vita.jpg` (na pasta da frente).

**Limite de 25 %:** na primeira passada, 3 de 40 sem pauta real (7,5 %). Os 2 erros do paginar
foram corrigidos e não contam como "sem pauta".

**Não feito ainda:** a escolha de 1 recorte por vídeo com a semente, o `ler_pasta` (Audiveris e
homr) e a montagem dos itens de conferência. A sessão principal leva ao dono.

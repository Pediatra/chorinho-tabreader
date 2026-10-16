# Onda 1 das frentes da partitura — briefings

**Data**: 2026-10-16. **Plano**: [`partitura-frentes.md`](partitura-frentes.md), seção 4 ("Ondas de
execução"). **Para quem**: o dono, que abre uma worktree e um agente por frente e cola o briefing
da frente.

## Como abrir cada worktree

Uma worktree por frente, a partir do `main` atual (o commit que trouxe este arquivo ou depois).
Os nomes não colidem com os das frentes das mãos (`../chorinho-wt-f0` etc.) nem com os da
tablatura (`../chorinho-wt-tab-*`):

| ordem | frente | worktree | branch |
| --- | --- | --- | --- |
| 1 | 0 — régua por compasso, troca do homr e tempo pelo par | `../chorinho-wt-part-f0` | `part/f0-regua` |
| 1 | D1 — amostra para o gabarito novo | `../chorinho-wt-part-d1` | `part/d1-amostra` |
| 1 | E1 — completar pela tab | `../chorinho-wt-part-e1` | `part/e1-completar` |
| 2 | A1 — imagem limpa antes do leitor | `../chorinho-wt-part-a1` | `part/a1-imagem` |

```bash
git worktree add ../chorinho-wt-part-f0 -b part/f0-regua main
```

```bash
git worktree add ../chorinho-wt-part-d1 -b part/d1-amostra main
```

```bash
git worktree add ../chorinho-wt-part-e1 -b part/e1-completar main
```

```bash
git worktree add ../chorinho-wt-part-a1 -b part/a1-imagem main
```

- **No máximo 3 ao mesmo tempo.** Abra F0, D1 e E1 já. A A1 entra na primeira vaga, de
  preferência **depois** que o `paginar` da D1 terminar: as duas leem vídeo do HD externo.
- Nenhuma usa GPU. A F0 e a E1 não leem vídeo. A D1 lê (o `paginar`, 1 vídeo por vez), e a frente
  C1 da tablatura também lê vídeo denso: se as duas rodarem juntas, cada uma leva o dobro do tempo.
- Quando uma frente terminar, avise a sessão principal com o nome do branch. Ela remede na `main`,
  integra e consolida o `ESTADO.md`. A onda 2 (B1, B2) tem briefing próprio, escrito depois que a
  régua da F0 for remedida na `main`.

## Regras comuns (todas as frentes)

Estão no `partitura-frentes.md` e valem inteiras. As que mais pegam:

- **Montagem** (seção 6.1): `data/saida/` e `artefatos/` da cópia principal só para leitura, e só
  as pastas da frente para escrita (`data/saida/part_frentes/<frente>/` e
  `artefatos/part_frentes/<frente>/`, que já existem). Antes de medir, dentro do container,
  `ls /app/data/saida/partitura/p1/omr/audiveris/x2_margem_herdada` e
  `ls /app/data/saida/partitura/sem_produto` têm de listar arquivos. Se vierem vazios, pare.
- **CA1 primeiro**, antes de mudar qualquer coisa, na imagem `docker.io/library/chorinho:dev`:
  `python data/saida/partitura/diag/ca1/ca1.py`. Leva cerca de 4 s, só lê e não grava nada. A
  saída tem de bater, linha a linha, com o bloco da seção 5.3 do plano. As linhas que mais
  importam:
  - `com homr confirmado pela tab:         [546, 528, 4, 14, 3]`;
  - `total partitura (19 telas): [767, 727, 9, 31, 7]`;
  - `C. leitura_p1: ... lidos 873, certos 852, ... faltando 78, cobertura 852/930`;
  - `D. leitura_sem_produto: ... lidos 178, certos 176, ... faltando 40, cobertura 176/216`.

  A linha `E.` não sai na worktree (o `compassos_homr.json` não está no git) e não conta. Se o
  resto não bater, pare e relate.
- **Critérios congelados** (seção 5.3 e seção 10, item 7): limiares, regras e conjuntos de escolha
  e de teste escritos no documento da rodada **antes** da medida. Mudar depois de ver o resultado
  invalida a frente.
- **Proibido** (seção 6.3):
  - escrever fora da pasta da frente;
  - editar `ESTADO.md` ou `data/gold/`;
  - editar os `tab/partitura_*.py` que já existem e os testes deles (importar e rodar pode; para
    mudar uma função, copie-a para o módulo da frente e mude só o destino);
  - editar arquivo de outra trilha;
  - dependência nova;
  - commit em `main`.
- **Leituras gravadas**: na pasta `x2_margem_herdada/<id>/` só existe `saida.musicxml`. O `.omr`,
  com as barras e as marcas, fica em `x2_margem/<id>/entrada.omr` (vale para `p1/omr/`,
  `video/<stem>/omr/` e `sem_produto/<slug>/omr/`). O homr fica em `homr/nativo/<id>/saida.musicxml`.
- **Entrega** (seção 9): código com o prefixo da frente e testes sem `data/saida/`, sem
  `artefatos/` e sem acervo; gate verde na worktree (`ruff --no-cache`, `pytest -p
  no:cacheprovider`); documento de rodada na faixa da frente; commit no branch com o número na
  mensagem; resumo curto em português.

---

## Briefing — Frente 0 (régua por compasso, troca do homr e tempo pelo par)

```text
Você trabalha na worktree da Frente 0 da partitura do projeto chorinho. Leia inteiro, antes de
rodar qualquer coisa: AGENTS.md; docs/pesquisa/partitura-frentes.md (seções 1 a 6, a Frente 0
na seção 7, e as seções 8, 9 e 10); docs/pesquisa/partitura-onda1-briefings.md (regras comuns);
no ESTADO.md, as seções "Partitura —" de 2026-10-14 e 2026-10-15; docs/decisoes/3002;
as rodadas 3004, 3015, 3024 e 3025 em docs/rodadas/; data/saida/partitura/diag/ca1/ca1.py
(modelo de como ler o pareamento e contar); data/saida/partitura/diag/homr_sem_produto/regra.py
(como pôr um clique num compasso pelo x das barras do .omr e num degrau pelo y).

Tarefa: F0.1, F0.2 e F0.3, nessa ordem. Siga o "Como" de cada uma à risca. Faça o CA1 primeiro
(regras comuns). Tudo em CPU, na imagem docker.io/library/chorinho:dev; nenhuma lê vídeo.

F0.1 (régua por compasso):
- Escreva tab/partitura_regua.py. Gabaritos: data/gold/partitura/leitura_p1.json (21 recortes,
  itens em data/saida/partitura/p1/conferencia/itens.json) e leitura_sem_produto.json (3
  recortes, itens em data/saida/partitura/diag/conferencia_sem_produto/itens.json). Os itens
  ficam na lista "itens" de cada arquivo.
- Use a leitura que o dono conferiu, dada pelo campo "fonte" do gabarito: audiveris/x2_margem
  em R01–R20, homr/nativo no R21 e audiveris/x2_margem_herdada nos 3 sem produto. O .omr está
  sempre em .../audiveris/x2_margem/<id>/entrada.omr.
- Os cliques de faltando ("faltando": [{x, y}]) estão nas coordenadas do PNG do item (campo
  "png"; largura em "largura_png"). O .omr é da imagem ampliada 2x: confira a escala em 3 casos
  antes de contar, com o recorte salvo na pasta da frente.
- Duração esperada de duas fontes, separadas: a do .omr e a da fórmula de compasso do item
  ("compasso_formula", "compassos"). R20 entra só na precisão; R21 não tem .omr: os dois à parte.
- Faça o mesmo no gabarito de tab: R01–R12 e as 7 telas novas da Gymnopédie (telas 2, 4, 6, 8,
  10, 11 e 12; as telas 1, 3, 5, 7 e 9 são R08–R12). As leituras do produto estão em
  data/saida/partitura/video/<stem>/omr/, com recortes T01–T12.
- Tabela compasso com erro × marca (abnormal; déficit; excesso; grade < 0,5; nenhuma), com o
  denominador, e 5 casos olhados por marca.

F0.2 (troca do homr julgada pela tab):
- Escreva tab/partitura_regua_troca.py. Importe trocar_compassos_pelo_homr e RAZAO_TROCA_HOMR
  de tab.partitura_pareamento (não mude a razão). Aplique a regra SEM a tab: Audiveris de
  x2_margem_herdada, homr de homr/nativo, números de compasso de ler_partitura (tab.
  partitura_gabarito), como em _pauta_sem_produto de tab/partitura_video.py.
- Julgue COM a tab, com contar(..., "exato") de tab.partitura_avaliar e
  referencia_do_recorte. Referência em R01–R12: só Audiveris, [546, 496, 9, 41, 3] (não 528).
  Nas 7 telas novas da Gymnopédie, grave antes a referência só Audiveris.
- Por tela e por vídeo: consertadas, quebradas, inventadas novas, compassos trocados e recortes
  em que o número de compassos difere (a regra não troca nada neles). Reporte também sem a
  Gymnopédie. Nota trocada não tem x: conte por sequência, como o ca1.py.

F0.3 (tempo pelo par):
- Escreva tab/partitura_regua_tempo.py. Para cada evento com "par" nos 3
  data/saida/partitura/video/<stem>/<stem>.partitura.json, ache no produto
  data/saida/fase8/rede/<stem>.json as notas com a mesma "tela" e "coluna" e o "t_ini" de cada
  "exibicao". Conte por vídeo e por exibição: par (evento, exibição) com tempo, evento sem par,
  par sem t_ini. Eventos com par.metodo == "x" à parte.
- Inversões: dentro de cada exibição, eventos na ordem (compasso, t) com tempo que volta. Olhe
  cada uma e diga se é erro de par ou do tempo da tab. Acorde (mesma coluna) não é inversão.
- Não mude o formato do produto e não escreva "tempo certo": o tempo da tab não foi validado.

Território: módulos tab/partitura_regua*.py e tests/test_partitura_regua*.py; saída só em
PART_FRENTE_0 (tab/caminhos.py, data/saida/part_frentes/f0_regua/); rodadas 3101–3109. Sem
porta.

Pare e relate se: o CA1 não bater; as contagens por gabarito não baterem com o CA1 (873 lidos,
852 certos, 78 faltando; 178, 176, 40); mais de 10 % dos cliques de faltando não couberem em
nenhum compasso.

Entregue: regua_compassos.json, troca.json, tempo.json, os recortes, as rodadas 3101 (F0.1),
3102 (F0.2) e 3103 (F0.3), gate verde, commit no branch, resumo curto em português. O resumo tem
de dizer: por marca, quantos compassos com erro ela acusa e quantos alarmes falsos dá; quantos
compassos com nota faltando têm déficit calculável (isso decide a B1); na F0.2, consertadas −
quebradas − inventadas novas, por vídeo; na F0.3, quantos eventos têm segundo e quantas
inversões. Não proponha mudar o produto nem a regra 3025: isso é da sessão principal.
```

## Briefing — D1 (amostra para o gabarito novo)

```text
Você trabalha na worktree da frente D1 da partitura do projeto chorinho. Leia inteiro, antes de
rodar qualquer coisa: AGENTS.md; docs/pesquisa/partitura-frentes.md (seções 1 a 6, a Frente D
na seção 7, e as seções 8, 9 e 10); docs/pesquisa/partitura-onda1-briefings.md (regras comuns);
a §6 de docs/pesquisa/partitura.md; as rodadas 3001 (censo P0), 3016 a 3018 (paginar), 3021
(piloto sem produto) e 3004 (gabarito do dono) em docs/rodadas/.

Tarefa: a D1 — sortear 40 recortes, 1 por vídeo, ler com Audiveris e homr e montar a
conferência do dono. Siga o "Como" da D1. Faça o CA1 primeiro (regras comuns).

Sorteio (ANTES de ler qualquer vídeo):
- Escreva tab/partitura_amostra.py. Peso por canal: "extrapolacao" de cada canal em
  data/saida/partitura/p0/resumo.json (lista "canais"; semente do P0 em "semente"). Os 10 canais
  com extrapolação ≥ 5 levam 1 vídeo cada: sky guitar (417), robert lunn (356,7), guitar
  dell ́arte (312,9), iwaki (164), pablo romé (110,7), serge kottelat (38), transcriptor (28),
  paolo d'angelo (14), ギタロー ⧸ guitarous (7,3) e tv on guitar (5). Use o nome do canal
  exatamente como está no resumo.json (acento, ⧸ e espaços). Os outros 30, proporcionais à
  extrapolação (kimny's guitar, lonelypicker e mr. tabs também entram no sorteio
  proporcional).
- População: os vídeos desses canais no acervo de hoje (/acervo), fora os 14 vídeos dos
  gabaritos (campo "video" dos itens em data/saida/partitura/p1/conferencia/itens.json e em
  data/saida/partitura/diag/conferencia_sem_produto/itens.json) e fora os 11 do piloto
  (pastas de data/saida/partitura/sem_produto/). Canal que não está no P0 fica fora: liste-o.
- Semente fixa. Grave amostra.json com a lista ordenada, as reservas na ordem do sorteio, a
  semente e os estratos, e COMMITE-A antes de rodar o paginar. O hash do commit vai na rodada.

Leitura:
- paginar: python -m tab.partitura_video paginar --video "<canal>/<arquivo>" --pasta
  data/saida/part_frentes/fd_gabarito/videos/<slug>. Um vídeo por vez (lê 1 quadro por
  segundo do HD externo); registre o tempo e quantos quadros leu de cada.
- Escolha 1 recorte por vídeo com a mesma semente, entre os recortes do recortes/indice.json.
  Não escolha "o mais legível". Vídeo só se troca se NÃO tiver pauta (paginar e olho), pela
  próxima reserva, e isso vai registrado. Recorte sem leitura fica, com cobertura 0.
- Audiveris (condição x2_margem e a armadura herdada) e homr (nativo), na imagem
  localhost/chorinho-partitura:dev, com rodar_um(..., pasta_base=<pasta da frente>) de
  tab/partitura_omr.py. ler_pasta(pasta) de tab/partitura_video.py faz Audiveris + herdada +
  homr numa pasta de vídeo; confira que ele grava só dentro da pasta passada.
- Itens da conferência: preparar --sem-produto lê de data/saida/partitura/sem_produto/ (só
  leitura). Copie _item_sem_produto e preparar_sem_produto de tab/partitura_gabarito.py para o
  seu módulo e mude SÓ a pasta de origem para a sua. Registre o diff na rodada.
- Sirva com python -m tab.partitura_gabarito servir --itens <seus itens> --ouro <cópia vazia>
  --porta 8121 --host 0.0.0.0, acrescentando -p 127.0.0.1:8121:8121 ao podman run. Teste os
  cliques numa CÓPIA, nunca no arquivo que o dono vai rotular (a ferramenta grava a cada
  clique). Não chame o dono: deixe a pasta e o comando prontos e avise a sessão principal.

Território: módulos tab/partitura_amostra*.py e tests/test_partitura_amostra*.py; saída só em
PART_FRENTE_D (data/saida/part_frentes/fd_gabarito/); rodadas 3160–3169. Porta 8121.

Aceite (congelado): lista sorteada e commitada antes de qualquer leitura; 40 recortes de 8
canais ou mais, 1 por vídeo; nenhum recorte trocado por ter saído ruim; ferramenta testada numa
cópia; estimativa do tempo do dono (cerca de 3 min por recorte no R01–R21). Pare se o paginar
não achar página em mais de 25 % dos vídeos sorteados: descreva antes de seguir.

Entregue: amostra.json (commitado antes), itens.json, os recortes, as leituras, a rodada 3160,
gate verde, commit no branch, resumo curto em português com a tabela por canal (sorteados,
trocados e por quê, com leitura, sem leitura) e quantos vídeos são de pauta que rola.
```

## Briefing — E1 (completar pela tab)

```text
Você trabalha na worktree da frente E1 da partitura do projeto chorinho. Leia inteiro, antes de
rodar qualquer coisa: AGENTS.md; docs/pesquisa/partitura-frentes.md (seções 1 a 6, a Frente E
na seção 7, e as seções 8, 9 e 10); docs/pesquisa/partitura-onda1-briefings.md (regras comuns);
a §5 de docs/pesquisa/partitura.md; docs/decisoes/3002; as rodadas 3006, 3010, 3012 a 3015 em
docs/rodadas/; tab/partitura_pareamento.py e tab/partitura_video.py (leia, não edite).

Tarefa: a E1 — para cada nota da tab que a partitura não leu, pôr a nota na partitura com a
altura da tab e, quando der, a figura e a voz. Siga o "Como" da E1. Faça o CA1 primeiro (regras
comuns). Tudo em CPU, na imagem docker.io/library/chorinho:dev; não lê vídeo.

- Escreva tab/partitura_completar.py. Dois conjuntos:
  - as 19 telas dos 3 produtos: data/saida/partitura/video/<stem>/<stem>.partitura.json contra
    a tab do produto data/saida/fase8/rede/<stem>.json (notas com "tela", "coluna",
    "x_centro_quadro", "corda", "casa"); eventos da tab por eventos_do_produto;
  - R01–R12: o pareamento em memória, como bloco_a do ca1.py (_parear_recorte de
    tab.partitura_pareamento), contra a tab do gabarito.
- Coluna da tab sem nota da partitura com aquela altura:
  - acorde: há evento da partitura no mesmo x (par com confere_x verdadeiro) → a nota entra
    nele, com a figura e a voz do evento (voz 2 para as cordas 4 a 6 só se o compasso já tem
    duas vozes);
  - ataque isolado: sem evento → déficit do compasso (fórmula em "compassos"/"fracao" menos a
    soma da voz) e proporção do x entre os vizinhos; se o déficit cabe numa figura só, ela
    entra;
  - nada decide → a nota entra com a altura e "figura": null. Nunca descarte.
- Nota completada sai com "origem": "tab_completada". Os símbolos que já existem ficam
  idênticos: compare todos os campos antes e depois. Grave o resultado na pasta da frente, num
  arquivo novo; não reescreva o .partitura.json.
- Fora da conta: harmônico (rodada 3013; uma oitava acima da tab no mesmo evento), casa entre
  parênteses (nota ligada), tela 10 da Gymnopédie (cordas deslocadas no produto, rodada 3014;
  use o par pelo x e conte à parte). Conte quantas saíram.
- Nas 19 telas a tab do produto tem 21 alturas erradas (ca1.py, linha "so a tab do produto"):
  conte quantas notas completadas herdam um erro da tab.
- Conferência do dono: as notas completadas e as 32 notas do homr de R01–R12 (as que o ca1.py
  conta em "notas do homr"). A pergunta é só: a figura está certa? Monte os itens copiando a
  função de item de tab/partitura_gabarito.py para o seu módulo (mude só a origem e o
  destino), sirva na porta 8122 com -p 127.0.0.1:8122:8122 e --host 0.0.0.0, e teste numa
  CÓPIA do gabarito. Não chame o dono: avise a sessão principal.

Território: módulos tab/partitura_completar*.py e tests/test_partitura_completar*.py; saída só
em PART_FRENTE_E (data/saida/part_frentes/fe_completar/); rodadas 3170–3179. Porta 8122.

Aceite (congelado), na conferência do dono: figura certa em 0,95 ou mais das notas de acorde, em
0,80 ou mais das notas por déficit e em 0,95 ou mais das 32 do homr; nenhum compasso passa da
duração esperada; símbolos existentes idênticos; CA2 vale (as completadas contam à parte). Pare
se mais da metade das notas que faltam não tiver nem evento no mesmo x nem déficit calculável.

Entregue: e1.json, os itens da conferência testados numa cópia, a rodada 3170 com 10 casos
olhados (recorte e nota), gate verde, commit no branch, resumo curto em português com a tabela
por vídeo: notas que faltavam, completadas por acorde, por déficit, sem figura, fora da conta.
Lembre no resumo: em R01–R12 a altura completada é certa por construção; o que a E1 mede é a
figura.
```

## Briefing — A1 (imagem limpa antes do leitor)

```text
Você trabalha na worktree da frente A1 da partitura do projeto chorinho. Leia inteiro, antes de
rodar qualquer coisa: AGENTS.md (regra 9: o recorte é parte da medida); docs/pesquisa/
partitura-frentes.md (seções 1 a 6, a Frente A na seção 7, e as seções 8, 9 e 10);
docs/pesquisa/partitura-onda1-briefings.md (regras comuns); a §3 de docs/pesquisa/partitura.md;
as rodadas 3003, 3017, 3021 e 3022 em docs/rodadas/; data/saida/partitura/diag/faixa_amarela/
medir.py (define "com faixa"); tab/leitor.py.

Tarefa: a A1 — limpar a imagem antes do Audiveris e medir quantos recortes voltam a ler sem
quebrar os outros. Siga o "Como" da A1. Faça o CA1 primeiro (regras comuns).

- Conjuntos:
  - os 36 recortes "com faixa" do piloto, pela regra do medir.py (fração de pixels amarelos
    > 0,05 no entrada.png de sem_produto/<slug>/omr/audiveris/x2_margem/<id>/); hoje 24 leem e
    12 falham. Reproduza esses números antes de mudar qualquer coisa;
  - os 21 recortes do gabarito (data/saida/partitura/p1/recortes_margem/);
  - depois, só com a melhor variante: os outros 126 do piloto e as 19 telas dos produtos.
  Na pasta sem_produto, a ólafur_... é uma cópia vazia: use a o_lafur_....
- Variantes, cada uma sozinha e depois a melhor combinação, com N e limiares escritos na rodada
  ANTES de medir:
  - A1a: mediana de N = 15 quadros espaçados em [t0, t1] da exibição, na mesma caixa
    ("exibicoes" e "caixa_recorte" de sem_produto/<slug>/recortes/indice.json; nos produtos,
    "exibicoes" das "telas" de data/saida/fase8/rede/<stem>.json e a caixa do .partitura.json);
  - A1b: o maior dos 3 canais;
  - A1c: saturação > 0,20 e brilho > 0,40 (HSV) viram branco;
  - A1d: moldura branca de 50 px antes de ampliar 2x.
- Quadros só por tab.leitor.quadro_em(caminho, t) (44 % do acervo é AV1; nada de
  cv2.VideoCapture direto). Um vídeo por vez; registre quantos quadros leu. Se a mediana não
  bater com o quadro estável (página que muda dentro de [t0, t1]), pare e descreva.
- Audiveris na imagem localhost/chorinho-partitura:dev, condição x2_margem, por
  rodar_um("audiveris", "x2_margem", item, pasta_base=<pasta da frente>/<variante>,
  origem=<png limpo>) de tab/partitura_omr.py. Confira antes, lendo o código, o que o rodar_um
  espera em "item" e em "origem". São cerca de 18 s por recorte: siga a ordem dos conjuntos.
- Medida como no CA1 (pareamento e contar nas 19 telas e em R01–R12) e CA2: R01–R12 certas
  ≥ 528, altura errada + inventadas ≤ 7; 19 telas certas ≥ 727, inventadas ≤ 7, altura errada
  ≤ 9. A moldura muda as coordenadas: tire-a antes de comparar com o gabarito.
- Meça a tinta perdida dentro da pauta na A1c (nota pintada vira branco) e olhe os casos.
- Dos recortes recuperados, prepare até 6 para a conferência do dono (porta 8123,
  -p 127.0.0.1:8123:8123, --host 0.0.0.0), testando numa CÓPIA do gabarito. Não chame o dono:
  avise a sessão principal.

Território: módulos tab/partitura_imagem*.py e tests/test_partitura_imagem*.py; saída só em
PART_FRENTE_A (data/saida/part_frentes/fa_imagem/); rodadas 3110–3129. Porta 8123.

Aceite (congelado): com faixa, de 24/36 para 30/36 ou mais; dos 143 que já leem, nenhum passa a
falhar; CA2; nos recortes recuperados, 0,95 ou mais dos símbolos certos na conferência do dono;
ganho em pelo menos 2 vídeos. Se o ganho só aparecer no mela, relate: não passa no CA4.

Entregue: a1.json, os recortes limpos e as folhas antes/depois, a rodada 3110, gate verde,
commit no branch, resumo curto em português com a tabela por variante (com faixa ok/36, piloto
ok/162, R01–R12 e 19 telas no formato do CA1) e quantos quadros leu.
```

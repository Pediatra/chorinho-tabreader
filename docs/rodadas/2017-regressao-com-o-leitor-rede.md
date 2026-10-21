# 2017 — Áudio: o alinhador v2.1 com o produto do leitor `rede` (regressão)

**Data**: 2026-10-20. **Estado**: pré-registro. Este documento ganha commit **antes** de
qualquer produto novo ser alinhado ou comparado. O resultado entra depois, numa seção nova,
sem mexer nas regras abaixo.

## Por que

- Desde a decisão [0010](../decisoes/0010-leitor-rede.md) (2026-10-14), o produto
  (`tab.video`) usa por padrão o leitor `rede`. Todos os números de áudio, das rodadas 2001 a
  2016, são do leitor de glifos.
- A trilha mãos vai consumir o `t_audio` (M13 do `plano-dataset-maos.md`, checagem K1), e ele
  vai sair de produtos do leitor `rede`.
- Antes de construir alguma coisa nova sobre o alinhador (o transcritor livre, o capo, a
  conferência), preciso saber se o tempo do som continua bom com a leitura nova.

## Pergunta

Com o produto gerado de novo (leitor `rede`, código atual) e o **alinhador sem mudança
nenhuma** (v2.1, commit `c5ac7f05`), o tempo do som piora nos vídeos em que era bom?

## Amostra (fixada agora)

**Principal, com critério: 15 vídeos.**

| grupo | vídeos | número antigo |
| --- | --- | --- |
| MVP | sky guitar *retrato brasileiro* | rodadas 2004, 2008 |
| com gabarito de escuta (folhas 1 a 3) | iwaki *la vie en rose*, kimny *from this place*, shin izumi *room 335* | rodadas 2005, 2007, 2008 |
| lote 1, bons | iwaki *michelle*, iwaki *fly me to the moon*, kimny *gunjo*, kimny *bach prelude*, shin izumi *a dream is a wish*, paolo d'angelo *those who wait* | rodada 2010 |
| lote 2, bons | sky guitar *exercise 3*, yunus *first love*, lonelypicker *it's a heartache*, robert lunn *5 easy pieces*, guitar dell'arte *summertime* | rodada 2016 |

- O shin izumi *room 335* era fraco (114 de 552 colunas, rodada 2009). Ele entra por causa do
  gabarito de escuta, e só vale o critério do gabarito para ele.

**Secundária, só descritiva (sem critério), se o tempo couber:** os fracos e os do meio dos
lotes 1 e 2: guitarous *sakura*, shin izumi *giant steps*, transcriptor *charagua*, mr. tabs,
serge kottelat, leonardo ramos, violaodecria *bela rosa*, tv on guitar. A pergunta aqui é se a
leitura nova muda os alarmes de leitura da decisão 2004.

**Ficam de fora:** o *campanitas* (descartado pelo dono), o kenneth *believer* (ritmo sem
casa) e o vvxofingerstyletab (1 tela só, troca de página não detectada).

## Cadeia

1. `python -m tab.video VIDEO --json …`: código atual, padrões (leitor `rede`), na CPU
   (`CUDA_VISIBLE_DEVICES` vazio), imagem base.
2. `python -m tab.audio_alinhar --metodo onsets`: v2.1, sem mudança. Áudio do cache
   (`tab.audio_extrair`), o mesmo das rodadas antigas.
3. `python -m tab.audio_produto`, na imagem `chorinho-audio:dev`.

Antigo (referência, já em disco):
- MVP: `data/saida/conserto_v2/mvp.json` + `data/saida/audio/a2/alinhado_v21_mvp.json`;
- folhas: `data/saida/audio/a2/produtos/<apelido>.json` + `alinhado_v21_<apelido>.json`;
- lote 1: `data/saida/audio/a4/lote1/<apelido>.json` + `alinhado_v21_<apelido>.json`;
- lote 2: `data/saida/audio/a4/lote2/<apelido>.json` + `alinhado_<apelido>.json` (já v2.1).

**Determinismo**: o produto de 1 vídeo (sky guitar *exercise 3*) é gerado 2 vezes; os dois
JSONs têm de ser iguais, fora o carimbo de hora. O alinhador não tem sorteio.

## Correspondência de colunas antigo ↔ novo

O número de uma coluna pode mudar entre os produtos (a rede lê mais notas). Por isso:
- **tela**: a tela nova cujas exibições mais se sobrepõem no tempo (`t0..t1`) às da tela
  antiga, com sobreposição ≥ 50 % da exibição antiga;
- **coluna**: a coluna nova da tela correspondente cujo centro (mediana de
  `x_centro_quadro` das notas) está mais perto do centro da antiga, a até 0,5 `passo`;
- **exibição**: a mesma ordem dentro da tela, se as janelas se sobrepõem.

## Medidas (por vídeo, antigo e novo, com denominador)

1. **Colunas com tempo**: colunas com `t_audio`, sobre as colunas de todas as exibições.
   Também as exibições recusadas e os alarmes de leitura (`chorinho/audio@1`).
2. **Pares de colunas correspondentes**: quantos pares; dos pares com tempo nos dois, a fração
   com |Δt| ≤ 30 ms; quantos perderam o tempo (antigo sim, novo não) e quantos ganharam.
3. **Som × marcador**, onde o produto novo tem `t_ini` (o MVP e os vídeos de canal com
   marcador que o produto ler): a mesma medida da rodada 2016 (mediana de `t_audio − t_ini`
   do vídeo; fração a ≤ 100 ms dessa mediana).
4. **Gabarito de escuta** (folhas 1 a 3; só leitura, nada se grava em `data/gold/`):
   - **pontos certos**: item não controle com resposta `certo` (folhas 1 e 2), ou item da
     folha 3 em que o dono escolheu o alinhador com |d| ≥ 100 ms. O instante clicado é tomado
     como verdade, à resolução de escuta de 100 ms (rodada 2008). Itens repetidos entre folhas
     contam uma vez;
   - para cada ponto, a coluna nova correspondente sai como **mantida** (≤ 50 ms do clique),
     **movida** (de 50 a 100 ms), **fora** (> 100 ms), **recusada** (sem tempo) ou **sem
     par**;
   - os 4 itens `errado` não controle: o tempo novo ainda cai a ≤ 100 ms do clique errado?
5. **X do rasgueado**: quantos `nao_notas` de classe `"x"` há nos produtos novos. O conserto
   de `colunas_abafadas` (contar `"x"`, manter top-1 `"15"` para os JSONs antigos) vai num
   commit à parte, com teste unitário, e roda **depois** desta medida.

## Critério (fixado agora)

Nos 14 vídeos bons da amostra principal (todos menos o *room 335*):
1. a fração de colunas com tempo não cai mais de **2 pontos percentuais** em nenhum vídeo;
2. onde houver par som × marcador nos dois produtos, a fração a ≤ 100 ms não cai mais de
   **5 pontos percentuais**.

No gabarito de escuta (os 4 vídeos das folhas):
3. **0 pontos certos "fora"** sem causa achada. Recusada e sem par são contados e
   relatados, mas não reprovam sozinhos.

**Se reprovar**: rodar o mesmo vídeo com `tab.video --leitor glifos` (código atual) para
separar o efeito do leitor do efeito das outras mudanças do produto desde 2026-10-13, olhar os
recortes das colunas que pioraram, e achar a causa antes da rodada 2018.

## Limites

- O denominador muda entre os produtos: a rede lê mais notas, e coluna nova pode ser nota que
  o leitor antigo perdia ou nota inventada. A comparação por pares cobre só as colunas que
  existem nos dois.
- Em `data/saida/maos/capo_por_video.json`, nenhum vídeo da amostra principal tem capo: o
  MVP, paolo d'angelo, lonelypicker e yunus estão em `sem_capo`, e os outros 11 não aparecem.
  Na secundária, o guitarous *sakura* tem **capo na casa 3**. Tudo continua alinhado com
  `transposicao = 0`, como antes: o erro é igual nos dois lados, e a casa do capo é a rodada
  2018.

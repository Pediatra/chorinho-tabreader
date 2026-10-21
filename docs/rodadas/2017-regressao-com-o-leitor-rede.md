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

---

## Resultado (2026-10-20, depois do commit do pré-registro `91581049`)

Os 15 vídeos principais rodaram sem erro. O produto levou de 49 a 896 s por vídeo na CPU, quase
o mesmo que o leitor antigo. **Determinismo**: o produto do *exercise 3* gerado 2 vezes saiu
igual, fora o carimbo de hora. Tudo em `data/saida/audio/r2017/` (`rodar.sh`, `comparar.py`,
`comparacao.json`, `comparacao.txt`, `diagnostico.py`, `quadros/`, `glifos/`).

### Colunas com tempo

| vídeo | antigo | novo | Δ pp | exibições recusadas | alarmes |
| --- | --- | --- | --- | --- | --- |
| MVP | 645/699 | 648/702 | +0,0 | 0 → 0 | 0 → 0 |
| iwaki *la vie en rose* | 245/273 | 304/337 | +0,5 | 2 → 0 | 0 → 0 |
| kimny *from this place* | 158/222 | 154/218 | −0,5 | 0 → 0 | 0 → 0 |
| iwaki *michelle* | 116/120 | 120/128 | **−2,9** | 0 → 0 | 0 → 0 |
| iwaki *fly me to the moon* | 346/372 | 349/383 | −1,9 | 1 → 1 | 1 → 1 |
| kimny *gunjo* | 531/650 | 546/664 | +0,5 | 1 → 1 | 0 → 0 |
| kimny *bach prelude* | 550/690 | 516/669 | **−2,6** | 0 → 0 | 0 → 0 |
| shin izumi *dream is a wish* | 205/274 | 332/374 | +14,0 | 2 → 0 | 2 → 0 |
| paolo d'angelo | 651/831 | 676/853 | +0,9 | 0 → 0 | 0 → 0 |
| sky guitar *exercise 3* | 158/161 | 157/161 | −0,6 | 0 → 0 | 0 → 0 |
| yunus | 343/384 | 480/517 | +3,5 | 0 → 0 | 0 → 0 |
| lonelypicker | 211/277 | 445/482 | +16,1 | 2 → 1 | 1 → 0 |
| robert lunn | 377/483 | 407/476 | +7,5 | 4 → 1 | 1 → 0 |
| guitar dell'arte | 171/230 | 203/256 | +4,9 | 0 → 0 | 0 → 0 |
| **14 bons, total** | **4707/5666 (0,831)** | **5337/6220 (0,858)** | +2,7 | | |
| shin izumi *room 335* (só gabarito) | 114/552 | 357/603 | +38,5 | 23 → 7 | 16 → 6 |

**Pares de colunas correspondentes** (15 vídeos): 4648 com tempo nos dois, **4516 a ≤ 30 ms
(97,2 %)**; 98 perderam o tempo e 357 ganharam.

**Som × marcador**: MVP 0,661 → 0,654 (629 → 632 pares); *exercise 3* 0,954 → 0,966 (87 → 87);
guitar dell'arte 0,878 → 0,862 (164 → 196). A mediana muda menos de 2 ms em cada vídeo.

**Gabarito de escuta** (40 pontos certos e 4 errados, dos 4 vídeos das folhas): 37 certos
**mantidos** (≤ 50 ms), 1 recusado (kimny), **2 fora** (*room 335*, g18 a 116 ms e g30 a 104
ms). Dos 4 errados, 3 continuam no mesmo instante errado e 1 (MVP, f11) saiu dele.

**X do rasgueado**: 0 `nao_notas` de classe `"x"` nos 15 produtos novos.

### Veredito pelos critérios

1. **Reprovado em 2 de 14 vídeos**: *michelle* −2,9 pp e *bach prelude* −2,6 pp. Os outros 12
   ficam a no máximo −1,9 pp, e 9 sobem.
2. **Aprovado**: a maior queda é de 1,6 pp (guitar dell'arte).
3. **2 pontos fora**, com causa achada (abaixo).

### Causas (olhadas no quadro, como manda o pré-registro)

O leitor de glifos com o código atual (`glifos/`) dá *michelle* 116/120 e *room 335* 118/552,
iguais ao antigo, e *bach* 533/678 (0,786, entre o antigo 0,797 e o novo 0,771). Quase toda a
mudança vem do leitor, não das outras mudanças do produto.

- ***michelle***: a leitura nova acha o **acorde final** (cordas 1 e 2 soltas, corda 3 na
  casa 1), que o leitor antigo perdia. Com essa coluna a mais, o alinhador encurta o trecho da
  tela 5 e larga as 3 notas anteriores, em *ritardando* (intervalos de 1,4 e 0,7 s). É a
  fraqueza do termo de andamento já medida na rodada 2014: leitura melhor, alinhador limitado.
- ***bach prelude***: o leitor `rede` **junta dois algarismos ligados por tracinho num número
  só** ("2·3" → 23, "2·4" → 24). A coluna fica com uma altura que não soa, e o alinhador a
  recusa (`sem_ataque_casado`). É **casa errada afirmada pela leitura**. Pedido 13 da
  decisão 2004.
- ***room 335***, tela 20: a leitura nova **perde dois "10" da corda 1** (x ≈ 365 e 595) e
  **lê como coluna o 10 pequeno de ornamento** antes dos ligados. Sem a coluna em x ≈ 595, o
  alinhador puxa a coluna seguinte (g18) para o ataque da nota que faltou; o g30 anda 104 ms
  na mesma tela. A leitura antiga também errava ali ("10" lido como "1", "11" como "14",
  pausa como "7"). Pedido 14 da decisão 2004.

### Consequência

- O alinhador v2.1 **não piorou**: onde a coluna é a mesma, 97,2 % dos tempos ficam a ≤ 30 ms.
  As duas reprovações e os dois pontos fora vêm da leitura, uma vez para melhor (*michelle*) e
  duas para pior (*bach*, *room 335*).
- **Segue para a 2018**, com dois avisos:
  1. a junção de algarismos do leitor `rede` produz casa errada. Para a base das mãos, essas
     notas não podem entrar como ouro. A conferência pelo som (frente C) deve pegar isso: a
     nota esperada não soa;
  2. o *ritardando* no fim da peça segue sendo limite do alinhador (rodada 2014).
- O conserto de `colunas_abafadas` (classe `"x"`) entra num commit à parte. Ele não muda nenhum
  dos 15 produtos, que têm 0 X.

### Limites

- A secundária (8 vídeos) está no anexo abaixo, só descritiva.
- "Mantido" no gabarito é a ≤ 50 ms do clique, e a escuta separa ~100 ms (rodada 2008).

## Anexo: amostra secundária (descritiva, sem critério)

Os 8 vídeos rodaram sem erro. Os alinhamentos rodaram depois do commit `d0d0c45c`
(`colunas_abafadas` com classe `"x"`). Os produtos têm 1 X (sakura) e 2 X (violaodecria), e
nenhuma coluna chega a 4 X: a regra não muda nada aqui.

| vídeo | notas a/n | colunas com tempo antigo → novo | recusadas | alarmes |
| --- | --- | --- | --- | --- |
| guitarous *sakura* | 94/405 | 0/62 → **0/269** | 10 → 10 de 10 | 6 → 8 |
| shin izumi *giant steps* | 354/611 | 75/263 (0,285) → **283/381 (0,743)** | 10 → 1 de 20 | 7 → 1 |
| transcriptor *charagua* | 362/401 | 124/334 (0,371) → 138/363 (0,380) | 4 → 3 de 18 | 2 → 2 |
| mr. tabs | 1306/1705 | 439/857 (0,512) → 571/1129 (0,506) | 2 → 0 de 32 | 2 → 0 |
| serge kottelat | 492/511 | 152/304 (0,500) → 173/303 (0,571) | 1 → 0 de 10 | 1 → 0 |
| leonardo ramos | 209/303 | 70/149 (0,470) → 142/191 (0,744) | 3 → 2 de 11 | 1 → 0 |
| violaodecria | 115/180 | 41/97 (0,423) → 98/136 (0,721) | 4 → 3 de 10 | 3 → 2 |
| tv on guitar | 1253/1267 | 326/796 (0,409) → 340/800 (0,425) | 6 → 6 de 22 | 1 → 1 |

- Alarmes de leitura nos 8: **23 → 14**. O *giant steps* (pedido 4 da decisão 2004) passa de
  7 alarmes para 1.
- O *sakura* agora tem notas (94 → 405: o pedido 1 parece resolvido pela leitura), mas segue
  com **0 colunas com tempo**. O vídeo tem **capo na casa 3** (`capo_por_video.json`) e foi
  alinhado com `transposicao = 0`: todas as alturas esperadas estão 3 semitons abaixo. É a
  hipótese mais provável, e não foi testada aqui: o *sakura* é um caso da rodada 2018 (casa do
  capo), e testá-lo antes do pré-registro dela contaminaria a amostra.
- Som × marcador no serge kottelat: 0,769 → 0,704 (52 → 71 pares). Sem critério nesta amostra;
  fica anotado.

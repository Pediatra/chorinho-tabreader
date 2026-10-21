# 2020 — Cruzamento tela × som, nota a nota, calibrado no gabarito do dono

**Trilha**: áudio. **Pré-registro**: 2026-10-21, antes de comparar qualquer leitura da tela
com o gabarito nesta rodada. **Decisões**: [2005](../decisoes/2005-validacao-cruzada-tela-som-maos.md)
(Regras 3 e 4) e [2006](../decisoes/2006-formato-som-transcritor-livre.md) (`chorinho/som@1`).

## Pergunta

Quando a leitura da tela (`chorinho/video@1`, leitor `rede`) e o som livre (Riley,
`guitar-fl`, rodada 2019) dizem a mesma nota, ela está certa? E quando o som não confirma,
a leitura da tela está errada com que frequência?

É a primeira perna da triangulação: tela × som, enquanto as mãos ainda não entregam corda
e casa por quadro.

## O cruzamento (congelado aqui)

Módulo neutro `tab/cruzar_fontes.py`, que só lê o produto da tela e o `chorinho/som@1`. O
capo entra como dado de contexto, com a fonte (`capo_por_video.json`).

Por tela do produto e por exibição (`t0`, `t1` do produto):
1. **Colunas da tela**: as notas do produto, distintas por (tela, coluna, corda), agrupadas
   pela `coluna` do produto. A altura é corda solta + casa + capo, e só entra casa numérica.
2. **Eventos do som** na janela `[t0 − 0,25, t1 + 0,25]`, inícios encadeados a ≤ 60 ms.
3. **O mesmo pareamento monotônico da 2018/2019** (`tab.audio_som_medir.parear`).
4. Por tela, vale a exibição com mais alturas pareadas.

**Veredito por nota da tela:**
- `confirma`: a altura dela está no evento pareado com a coluna;
- `nao_confirma`: a coluna pareou com um evento, mas a altura dela não está nele;
- `coluna_sem_par`: a coluna não pareou com nenhum evento, numa exibição em que outras
  colunas parearam;
- `sem_dado`: a tela não tem nenhuma coluna pareada (sem som na janela, ou som que não tem
  nada a ver com a tela), ou a casa não é numérica.

## Como se mede (a verdade é o gabarito)

As notas do produto nas telas conferidas pelo dono são casadas com o gabarito pela régua
da trilha tablatura (`tab.avaliar_video`: telas por instantes, notas por corda e x ≤ 0,5
passo). Cada nota do produto vira:
- `certa`: casou com uma nota do gabarito de mesma casa;
- `errada`: casou com casa diferente, ou não casou (nota inventada).

As notas do gabarito que o produto perdeu ficam fora desta medida, que é sobre o que a tela
**afirma**.

**Amostras:**
- **Fora do treino do leitor (principal)**: as 4 telas de `acordes_2018`, com os produtos da
  rodada 2017. O leitor `final_s1_ger` não viu esses 4 vídeos. O casamento com o gabarito é
  direto: o material foi feito desses produtos (`indice.json`), na mesma tela e com x ≤ 0,5
  passo.
- **Dentro do treino do leitor (secundária)**: os 8 vídeos do gabarito de tablatura, com
  produtos novos do mesmo leitor. O leitor foi treinado nesses 8 (dobra 0, ESTADO), então
  os erros dele ali são **menos e mais fáceis** que no acervo. O número é relatado, mas é
  otimista.

**Medidas:**
- **K1**: das notas com `confirma`, a fração `errada`. É o erro do nível "tela + som
  concordam".
- **K2**: das notas `errada` com veredito (fora `sem_dado`), a fração com `nao_confirma` ou
  `coluna_sem_par`. São os erros da tela que o som acusa.
- **Descritivas**: a precisão do alarme (das notas não confirmadas, quantas estão
  erradas), a fração `sem_dado` e o veredito por tipo de erro (casa errada, inventada).

## Critérios

| # | passa se | então |
| --- | --- | --- |
| K1 | **≤ 1 %** de `errada` entre as `confirma`, nas duas amostras somadas | o cruzamento grava o nível "tela + som" por nota (decisão 2005, Regra 3) |
| K2 | **≥ 50 %** dos erros da tela com veredito saem não confirmados, nas duas amostras somadas | a lista de não confirmadas vai como alarme à trilha tablatura (via 2004), ordenada |

- **Mínimo de dados**: com menos de 20 notas `errada` com veredito, K2 é relatado e não
  decide; a amostra cresce numa rodada nova (T8.2, abaixo).
- **Se K1 reprovar**: olham-se as notas erradas confirmadas, antes de qualquer ajuste no
  cruzamento. Ajuste é rodada nova.

## Fora desta rodada

- **As telas da T8.2** (35 telas de 18 canais fora do gabarito, conferidas pelo dono): é a
  amostra fora do treino maior que existe. Ela precisa de produto, áudio e transcrição de 35
  vídeos, um lote no HD que se combina com o dono.
- As mãos, a partitura e a casa sugerida pelo som (por exemplo, "23" na tela contra "2" e
  "3" no som).
- As notas do som sem nota na tela (ornamento, nota perdida, repetição de rasgueado): elas
  são contadas, mas não julgadas.

## Resultado (medido em 2026-10-21)

- **Código**: `tab/cruzar_fontes.py` de 7daccef0; medida no commit 0f713333
  (`data/saida/audio/r2020/medir.py`, saída `medida.json` e `medida.txt`).
- **Produtos**: os da rodada 2017, mais 4 novos do mesmo leitor para os 8 do gabarito
  (commit 738f8e8e, `data/saida/audio/r2020/produtos/`).
- **Som**: `data/saida/audio/r2019/som_fl/` (Riley `guitar-fl`, rodada 2019).
- Nenhuma tela ficou `sem_dado`.

| amostra | notas da tela julgadas | `confirma` (erradas) | não confirmadas (erradas) | K1 | K2 |
| --- | --- | --- | --- | --- | --- |
| fora do treino (principal) | 214 | 184 (7) | 30 (0) | 7/184 = 3,8 % | 0/7 |
| dentro do treino | 2.692 | 2.225 (7) | 467 (7) | 7/2.225 = 0,31 % | 7/14 |
| **somadas (critério)** | 2.906 | 2.409 (14) | 497 (7) | **14/2.409 = 0,58 %** | **7/21 = 33 %** |

- **K1 passa** pela regra pré-registrada (somadas, ≤ 1 %).
- **K2 reprova**: 33 % < 50 %, com 21 erros (≥ 20, então decide).
- Precisão do alarme: **7/497 = 1,4 %**. Quase toda nota não confirmada está certa, e foi o
  som que não a ouviu.

## Leitura

1. **O K1 passa só na soma.** A amostra principal, fora do treino, dá **7/184 = 3,8 %**. A
   soma é puxada pela amostra dentro do treino (2.225 das 2.409 confirmadas), que este
   pré-registro já chamava de otimista. Pôr o critério na soma foi um erro do pré-registro.
   O limiar não muda depois da medida, mas o "confirma" **não sobe nota a ouro**: o veredito
   por nota segue gravado no `chorinho/cruzamento@0`, e o nível só vale depois de uma rodada
   nova com o critério só na amostra fora do treino (T8.2).
2. **As 7 erradas confirmadas da amostra principal, olhadas na imagem da tela:**
   - **paolo, 4 notas** (tela 4 do produto, colunas 45, 46, 47 e 49, corda 2). O produto lê
     casa 3, e o gabarito diz 0.
     - A tela mostra "3" na corda 2 nos 5 rasgueados do fim
       (`data/saida/audio/r2020/paolo_tela1_final.png`).
     - O som ouve 62 (ré = corda 2, casa 3) nos 5 e nunca 59 (si = corda 2 solta).
     - Na coluna 48, o gabarito tem duas notas na corda 2 (casa 3 em x 1829 e casa 0 em
       x 1833).
     - Parece deslize de marcação no gabarito. O gabarito é do dono: vai para ele rever, e o
       agente não muda nada. Mesmo que o dono confirme, o K1 principal fica em 3/184 = 1,6 %,
       ainda acima de 1 %.
   - **charagua, 3 notas** (tela 6, colunas 2, 4 e 7, corda 1, casa 4). O leitor `rede` leu a
     ponta da seta de rasgueado como "4" na corda 1 (3 das 6 setas;
     `data/saida/audio/r2020/charagua_tela3_setas.png`).
     - O som "confirma" porque o violonista repete o rasgueado, e 68 (corda 1, casa 4) está
       no acorde de dó# menor que soa (corda 2, casa 9).
     - **A confirmação não é independente.** Uma coluna de nota única, encostada num acorde
       cheio, pareia com a repetição desse acorde. É um furo do cruzamento, não acaso.
3. **Dentro do treino**: 7 notas inventadas confirmadas (end of beginning 2, from this place
   2, room 335 2, la vie en rose 1), ainda não olhadas.
4. **K2**: o som perde nota de verdade (a revocação da 2019 é 0,804, e os bordões caem mais).
   Por isso "não confirma" quase sempre é nota certa que o som não ouviu: 490 das 497. Os 7
   erros acusados incluem 2 do *retrato*, em que o som ouviu 42 (corda 6, casa 2) onde a tela
   leu 0.

## Consequências

- **K1**: o veredito por nota continua sendo gravado, mas o `confirma` não promove nota.
- **A próxima rodada** usa a amostra da T8.2, com o critério só nela. Ela leva uma regra
  contra a confirmação por rasgueado repetido: o evento pareado que repete o acorde da coluna
  vizinha vira `ambigua`, não `confirma`.
- **K2 reprovado**: a lista de não confirmadas **não** vai à tablatura como alarme. Entra no
  "não repetir".
- **Para a tablatura**: pedido 15 na decisão 2004 (a seta de rasgueado lida como "4").
- **Para o dono**: rever a corda 2 dos 5 rasgueados do fim da tela 1 do `acordes_2018`
  (paolo).

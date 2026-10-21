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

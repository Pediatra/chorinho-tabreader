# 2021 — Cruzamento tela × som fora do treino do leitor (T8.2), com a regra do rasgueado

**Trilha**: áudio. **Pré-registro**: 2026-10-22, antes de cruzar qualquer vídeo desta amostra
e antes de olhar os produtos dela. **Rodada anterior**: [2020](2020-cruzamento-tela-som.md).
**Decisões**: [2005](../decisoes/2005-validacao-cruzada-tela-som-maos.md) e
[2006](../decisoes/2006-formato-som-transcritor-livre.md).

## Pergunta

Quando a leitura da tela e o som livre dizem a mesma nota, ela está certa, **numa amostra que o
leitor da tela nunca viu**? A 2020 mediu isso em 184 notas confirmadas fora do treino e deu
3/184 = 1,6 % depois da correção do gabarito (o critério dela estava na soma com a amostra de
dentro do treino, que dominava).

## O que muda desde a 2020 (congelado aqui)

- **Regra nova, `ambigua`** (`tab/cruzamento/cruzar_fontes.py`, `marcar_ambiguas`): uma nota
  que seria `confirma` vira `ambigua` quando a coluna dela tem menos notas que uma coluna
  vizinha (anterior ou seguinte) com **≥ 3 notas**, e todas as alturas dela estão nesse
  acorde. Motivo: na 2020, as 3 erradas confirmadas que sobraram eram pontas de seta de
  rasgueado lidas como "4", "confirmadas" pela repetição do acorde vizinho.
- `ambigua` **não** conta como confirmação: o nível "tela + som" vale só para `confirma`.
- O resto é a 2020: pareamento monotônico, janela ±0,25 s, inícios encadeados a ≤ 60 ms,
  melhor exibição por tela, capo de `capo_por_video.json`.

## Amostra

- **A T8.2 da tablatura**: 36 vídeos de 18 canais fora do ouro de tablatura (2 por canal,
  sorteio com semente 0), uma tela por vídeo. O dono conferiu 35 telas
  (`data/saida/tablatura/t82/ferramenta/conferencia_t82.json`, 1.573 notas). A tela 33 fica
  de fora: não foi conferida.
- **Fora por ausência no acervo**: 1 dos 36 vídeos não está mais no HD (lonelypicker, *everything
  i do*), visto antes de qualquer cruzamento. Ficam 35 vídeos; as telas conferidas que sobram
  são contadas no resultado.
- **Produtos novos** do leitor do produto (`detector_tab_final_s1_ger`) e **som novo** (Riley
  `guitar-fl`), feitos para esta rodada (`data/saida/audio/r2021/rodar.sh`).
- O leitor `s1_ger` não foi treinado nesses vídeos. A T8.2 já foi usada pela tablatura para
  medir a leitura (casa 0,996), mas nunca para o cruzamento: para esta pergunta ela é prova
  nova.

## Como se mede

- A tela conferida é casada com a tela do produto cuja exibição contém o instante dela
  (`indice.json`, campo `t`). Sem tela que contenha o instante: fica fora, e se conta.
- Notas do produto × gabarito: a régua da 2020 (`tab.avaliar_video.casar_notas`, mesma corda
  e x ≤ 0,5 passo). `certa` = mesma casa; `errada` = casa diferente ou nota inventada.
- As notas do gabarito que o produto perdeu ficam fora: a medida é sobre o que a tela afirma.

## Critérios

| # | passa se | então |
| --- | --- | --- |
| K1 | **≤ 1 %** de `errada` entre as `confirma`, com **≥ 300** confirmadas | o nível "tela + som" vale como sinal por nota no cruzamento (ainda não promove nota a ouro sozinho: a 2005 pede as 3 fontes) |
| K2 | **≥ 50 %** dos erros da tela com veredito saem `nao_confirma` ou `coluna_sem_par` | a lista de não confirmadas vai à tablatura como alarme |

- **Mínimo de dados**: com menos de 300 confirmadas, K1 não decide. Com menos de 20 erros
  com veredito, K2 é relatado e não decide (a T8.2 tem ~14 erros de leitura; o mais provável
  é K2 não decidir).
- **Custo da regra**, relatado: quantas notas `certa` viram `ambigua`.
- **Se K1 reprovar**: olham-se as erradas confirmadas, na imagem, antes de qualquer ajuste.
  Ajuste é rodada nova.

## Descritivo, sem decidir

- A amostra da 2020 (`acordes_2018`, já vista) recalculada com a regra `ambigua`: só para
  conferir que a regra pega as 3 setas do *charagua*. Não é prova.

## Fora desta rodada

- As mãos (a terceira fonte) e a altura sugerida pelo som para corrigir a casa.

## Resultado (2026-10-23, commit 93598e7c)

Lote: 35 de 35 vídeos com produto e som (`rodar.log`, todas as etapas com RC=0; o PC caiu
no meio e o lote retomou sem refazer o que estava salvo). Medida:
`data/saida/audio/r2021/medir.py` → `medida.json` e `medida.txt`.

- **Telas medidas**: 34 de 36 (tela 33 não conferida; tela 14, vídeo ausente). Todas acharam
  a tela do produto que contém o instante.
- **Notas do produto casadas**: 1.519.

| veredito | certa | casa errada | inventada |
| --- | ---: | ---: | ---: |
| confirma | 1.042 | 4 | 60 |
| nao_confirma | 110 | 2 | 8 |
| coluna_sem_par | 242 | 4 | 26 |
| ambigua | 25 | 0 | 5 |

- **K1: reprova.** 64 erradas entre 1.106 confirmadas = **5,8 %** (limite 1 %).
- **K2: reprova.** 40 dos 109 erros com veredito acusados = **37 %** (limite 50 %).
- **Custo da regra `ambigua`**: 25 notas certas viraram `ambigua` (2,3 % das 1.067
  certas que seriam confirmadas).
- **Descritivo, `acordes_2018`**: a regra pega as **3 setas** do *charagua* (as 3 erradas
  confirmadas da 2020 saem como `ambigua`). Confirmadas: 0 erradas em 176. Custo: 5 certas
  viraram `ambigua`.

### Leitura (olhada na imagem, como o pré-registro manda)

- **61 das 64 erradas confirmadas vêm de 2 vídeos**, e nos dois o erro é da **régua**, não da
  tela nem do som:
  - *what a wonderful world* (tela 19): 56 de 62. A tab corre de lado sob um cursor fixo, e
    o produto chamou o vídeo de `estatico` (uma tela de 0 a 323 s). Os x do produto vêm de
    outro instante, ~140 px deslocados do quadro do dono. A sequência corda:casa é quase a
    mesma, e a régua por x (≤ 0,5 passo) não casa as notas.
  - *toxic* (tela 7): 5 de 5. Também deslocado, ~80 px, com a mesma sequência.
- **Sem esses 2 vídeos** (corte feito depois de ver; **não decide**): 3 erradas confirmadas
  em 1.039 = 0,29 %, e 13 erros com veredito (abaixo do mínimo de 20 para K2). As 3 são
  `inventada` (casa 10 na corda 2 do *群青*, casa 5 na corda 3 do *emily*, casa 10 na corda 1
  do *all of me*), ainda não olhadas na imagem.
- As 5 erradas pegas pela `ambigua` na T8.2 também são do *what a wonderful world* (a mesma
  falha da régua). Na T8.2, a regra não tem acerto medido.

### O que fica decidido

- Pela regra da rodada, K1 e K2 reprovam, e o nível "tela + som" **não** vale como sinal por
  nota.
- A causa achada é a medida: a régua por x supõe que o quadro do dono e a tela do produto
  estão alinhados. Em tab que corre de lado, isso falha. Corrigir a régua e medir de novo é
  **rodada nova** (2022), com pré-registro e a T8.2 declarada como já vista.

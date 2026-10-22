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

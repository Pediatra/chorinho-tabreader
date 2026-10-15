# 3025 — homr troca o compasso em vídeo sem produto (sem confirmação)

Trilha partitura. Data: 2026-10-15. Regra adotada pelo dono a partir da rodada 3024.
Scripts e saídas em `data/saida/partitura/diag/troca_homr/`.

## Regra

Num recorte de vídeo sem produto, para cada compasso: se o homr lê **pelo menos o dobro**
das notas do Audiveris (e mais notas que ele), o compasso do homr entra no lugar do
compasso do Audiveris. As notas do homr saem com `origem` **`homr_sem_confirmacao`**, para
poder filtrar depois. A leitura do Audiveris continua em disco (`omr/audiveris/...`). Se as
duas leituras têm número de compassos diferente, nada é trocado.

## Mudanças

- `tab/partitura_pareamento.py`: `RAZAO_TROCA_HOMR = 2.0` e
  `trocar_compassos_pelo_homr(audiveris, numeros_audiveris, homr, numeros_homr)`. A nota
  trocada fica com o número de compasso do Audiveris e `x_quadro` None (o homr não tem
  `.omr`). A função não altera a entrada.
- `tab/partitura_video.py`:
  - `ler_pasta` roda o Audiveris e depois o homr (`omr/homr/nativo/`, com
    `execucao.json`);
  - `_pauta_sem_produto` aplica a troca, e a pauta ganha `compassos_homr` (números
    trocados). Sem homr, ou com homr ilegível, segue só com o Audiveris, sem erro;
  - `gerado_por.completar` descreve a regra. O `resumo` ganha `compassos_homr` e
    `notas_homr`.
  - A CLI mostra `homr ok X/Y` e os compassos trocados.
- 9 testes novos (7 da função, 2 da pauta). O teste de `ler_pasta` agora exige Audiveris e
  depois homr.

Gate: 1173 passados (sem o teste da trilha mãos, `test_maos_direita_cordas.py`).

## Execução nos 11 vídeos do piloto

O homr rodou de verdade em todos os 162 recortes (`rodar.py`): 160/162 ok, 7–9 s cada, CPU.
As 2 falhas são do giant steps (P02a, P13a). O Audiveris **não** rodou de novo: o registro
saiu do `execucao.json` da rodada 3022, que já é dos recortes atuais.

| vídeo | pautas | compassos trocados |
| --- | ---: | ---: |
| amores hallaras | 12 | 11 |
| blackbird | 20 | 10 |
| mela | 41 | 4 |
| athletic theme | 8 | 2 |
| agua de beber | 10 | 1 |
| everything i do | 23 | 1 |
| happiness does not wait | 10 | 1 |
| beam of light, amazing grace, giant steps, canon | 38 | 0 |
| **total** | **162** | **30, em 17 recortes** |

Lista por recorte em `conferencia.txt`. O amores hallaras chama atenção: 11 compassos com
**1 nota do homr cada**, onde o Audiveris não leu nota. Pode ser nota longa de verdade ou
invenção. Vai para o dono.

## O que a troca perde (medição nova)

A 3024 mediu só o que o homr **acrescenta**. Trocar o compasso inteiro também **tira** as
notas do Audiveris que o homr não leu. No gabarito, só o athletic P01a foi trocado
(compassos 3 e 4, `perdas.py`):

- compasso 3: Audiveris 6 notas, homr 26; nenhum degrau do Audiveris some;
- compasso 4: Audiveris 7, homr 18; **somem 2 fá#3** do Audiveris.

Conta no athletic: +25 recuperadas, 8 inventadas (3024) e **2 perdidas**. A 3024 mediu o
degrau, não o acidente, então a altura exata das notas do homr não está medida.

## Conferência

A página é `tab.partitura_gabarito servir`, porta 8097, e mostra os 17 recortes. Cada um
desenha a leitura que entrou no documento: o MusicXML do Audiveris com os compassos do homr
fundidos (`conferencia.py`, saída em `fusao/`). As `divisions` do homr são declaradas no
compasso trocado e as do Audiveris restauradas no seguinte. O título do item diz quais
compassos da pauta vieram do homr. O teste foi feito numa cópia, `teste_ouro.json`, que não
foi gravada. O gabarito é `data/gold/partitura/compassos_homr.json`, e só o dono grava
nele.

## Limites

- Antes da conferência do dono, a qualidade da troca está medida só no athletic P01a.
- As notas do homr não têm x no quadro.
- O homr usa a própria leitura de armadura. A armadura do vídeo não é aplicada às notas
  trocadas.

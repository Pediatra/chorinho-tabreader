# 0206 — A2: o arco como objeto próprio

Fase R4b do plano (`plano-rotulo-tablatura.md`, a A2 antiga). Segue a
[0205](0205-faixa-nao-sei.md). Escrito **antes** de qualquer código e de treinar.

## Por que

Na 0205, com a faixa "não sei", sobram 7 ou 8 das 45 notas não atacadas da T8.2 lidas como
"sim". O sinal da técnica nelas fica abaixo de 0,01, sobretudo no mordente e no h/p de arco
longo.

A técnica é uma classe **por nota**: o modelo precisa decidir, no bin da nota de chegada, se um
arco que começa longe termina ali. Um arco longo, ou um arco sobre três notas, fica fora do que
a cabeça vê em volta da nota.

## A mudança

1. **Cabeça `arco`** no `DetectorTab`: 1 logit por corda e por bin, para "este bin está debaixo
   de um arco desta corda".
   - O alvo vai de 1 entre o centro da nota onde o arco começa e o centro da nota onde ele
     termina, e de 0 no resto.
   - A supervisão é total no sintético, porque o gerador sabe onde desenhou cada arco.
   - A perda é BCE, somada às de hoje.
   - Os pesos antigos carregam sem a cabeça (`strict=False`). O `DETECTOR_PADRAO` não muda.
2. **Gerador**: cada arco desenhado entra em `info["arcos"]` (corda, x do começo, x do fim).
   - Entram os arcos de h/p, o tie, o mordente de três notas e o arco do enfeite.
   - A letra sem arco não entra.
3. **Regra de ataque pelo arco**: entre duas notas vizinhas da mesma corda, a média da
   probabilidade de `arco` nos bins entre elas. Acima de `T_arco`, a nota da direita é "nao"
   (motivo pelos números, como no `converter.py`: h, p, prolongamento ou mordente).
   - Junta-se à faixa da 0205: "sim" só com técnica abaixo de 0,02 **e** arco abaixo de
     `T_arco_baixo`.
4. **Ajuste fino** com o arco real: as regiões de legato do dono, nas telas conferidas, dão o
   começo e o fim de cada arco (a primeira e a última nota do grupo do `converter.py`).

## Ordem, com parada cedo

1. Gerador e cabeça, com testes e o gate.
2. **Piloto, sem o arco real**: só a dobra 0, semente 1, partindo do `detector_tab_v3_s1`. Mede-se
   na T8.2 a probabilidade de `arco` entre as notas das 7 ou 8 que escapam na 0205.
   **Pare se** o arco não passar de 0,5 em pelo menos metade delas. Nesse caso, o problema não é
   ver o arco, e o próximo passo é mais gabarito de canais novos (T8.3).
3. Com o arco real no ajuste fino: 15 treinos (5 dobras × 3 sementes), com o nome `_arco`.
4. `T_arco` e `T_arco_baixo` são escolhidos **só nos ouros**, como na 0205. Depois valem sem
   mudança na T8.2 e na T8.3, quando ela existir.

## Aceite (o do plano)

Nos ouros e na T8.2, separados:

- "sim" falso **≤ 5 %**;
- "não" ou "não sei" em atacada **≤ 10 %**;
- a casa não piora além da amplitude do `_atqg`.

**Pare se** o "sim" falso na T8.2 não cair além da faixa do `_atqg` com a faixa "não sei" (7–8/45).

## Piloto (2026-10-19)

Treino: `--ataque --arco`, dobra 0, semente 1, 3000 passos, 788 s
(`data/saida/tab_rotulo/a2/treino_arcop_d0_s1.log`). A perda do arco no sintético cai de 0,17
para 0,014. Medida: `a2/medir_piloto.py`, saída em `a2/piloto.json`, na T8.2.

As 7 notas "não" que a faixa da 0205 lê como "sim", com o `arco_esq` do piloto:

| canal | nota | motivo | arco |
| --- | --- | --- | --- |
| guitar dell'arte | t4-n47 | p | 0,02 |
| kenneth acoustic | t8-n10 | p | 0,04 |
| lonelypicker | t13-n8 | prolongamento | 0,50 |
| robert lunn | t22-n6 | mordente | 0,03 |
| shin izumi | t26-n7 | mordente | 0,75 |
| sky guitar | t28-n8 | slide | 0,50 |
| yunus guitarist | t34-n13 | slide | 0,25 |

- O arco passa de 0,5 em **2 das 7** notas. Contando só as que não são slide, são 1 ou 2 das 5.
- O arco também não separa os dois grupos. Nas 45 notas "não", a mediana é 0,82. Nas 1287
  notas "sim", a mediana é 0,38, e 34 % delas passam de 0,5.

**A regra de parada dispara.** O piloto não vê o arco nessas notas, e ainda acende em um terço
das notas atacadas. Os 15 treinos não são feitos. Pelo pré-registro, o próximo passo é mais
gabarito de canais novos: a T8.3 (33 telas, 17 canais, em `data/saida/t83/`), que o dono está
conferindo. A cabeça de arco fica no código, sem uso no produto.

# 0205 — A faixa "não sei" na técnica

Segue a [0204](0204-r4c-traco-slide-curto-arco-raso.md). Lá a regra de parada disparou: mais
estilo de arco no gerador não baixou o "sim" falso da T8.2 (14–16/45). Escrito **antes** de
medir.

## Por que

O aceite do plano (`plano-rotulo-tablatura.md`, R4) conta **"não" ou "não sei"** em nota
atacada até 10 % como custo de cobertura. Hoje o produto só diz "sim" ou "não".

No `_atqg`, o "não" em atacada fica em 0,9 % no limiar 0,15. Quase todo o orçamento de 10 %
está sobrando. Uma nota com um pouco de sinal de técnica sem ataque, abaixo do limiar, é uma
nota duvidosa. Para a base de treino das mãos, "não sei" é melhor que um "sim" errado: a regra
da rota é "na dúvida, `nao_sei`, nunca sim".

## A regra

- O "não" continua no limiar da técnica da 0203: 0,15 para o `_atqg`.
- O "sim" só vale com **todas** as 7 técnicas sem ataque abaixo de um limiar baixo `L`.
  Entre `L` e o limiar da técnica, a nota é **"não sei"**.
- A regra do slide sem origem continua valendo antes de tudo.
- `L` sai da grade 0,01, 0,02, 0,03, 0,05, 0,07, 0,10, 0,15 e assim por diante
  (`LIMIARES_MEDIDOS`).
- `L` é escolhido **só nos 8 ouros**, pela dobra fora, com as 3 sementes somadas: o **menor** `L`
  com "não" ou "não sei" em atacada até **5 %**. É a metade do teto do plano, para sobrar margem
  fora da amostra (`escolher_nao_sei`).
- Depois, `L` vale **sem mudança** na T8.2, que é a medida.

## Medida

- `tab.ataque_r4 medir`, de novo, para o `_atqg` (base adotada) e o `_atqc`, nas 3 sementes, com
  os limiares baixos.
- Para cada nota: o "sim" falso é a nota "não" do gabarito lida como "sim". O custo é a nota
  atacada lida como "não" ou "não sei".

## Aceite (o do plano)

Nos ouros e na T8.2, separados:

- "sim" falso **≤ 5 %**;
- "não" ou "não sei" em atacada **≤ 10 %**;
- a casa não muda: a regra só mexe no rótulo de ataque.

**Pare se** a T8.2 passar de 10 % de custo com o `L` dos ouros. Isso quer dizer que a faixa não
generaliza, e o próximo passo volta a ser o arco como objeto próprio (R4b do plano, a A2).

## Resultado (2026-10-19)

Os 6 modelos foram medidos de novo (`r4c/medir_nao_sei.sh`). O `L` escolhido nos ouros é
**0,02** nas duas versões: o custo, somado nas 3 sementes, fica em 4,2 %. Sementes
`s1 · s2 · s3`.

| teste | medida | `_atqg` 0,15 (0203) | `_atqg` L = 0,02 | `_atqc` L = 0,02 |
| --- | --- | --- | --- | --- |
| 8 ouros | "sim" falso | 13 · 11 · 15 /85 | **5 · 4 · 5 /85** (5–6 %) | 3 · 4 · 2 /85 (2–5 %) |
| 8 ouros | "não"/"não sei" em atacada | 29 · 21 · 23 (~1 %) | 110 · 114 · 101 (3,9–4,4 %) | 114 · 116 · 98 (3,8–4,5 %) |
| T8.2 | "sim" falso | 14 · 16 · 14 /45 | **7 · 8 · 8 /44–45** (16–18 %) | 7 · 7 · 7 /44–45 (16 %) |
| T8.2 | "não"/"não sei" em atacada | 6 · 10 · 9 | 26 · 30 · 31 (1,8–2,1 %) | 30 · 27 · 33 (1,8–2,2 %) |

A casa não muda: a regra só mexe no rótulo de ataque.

Diagnóstico, que não escolhe nada: com `L = 0,01`, a T8.2 do `_atqg` dá 6 · 8 · 7 /45, com um
custo de 42–47 (~3 %). Os 7 ou 8 que sobram têm sinal abaixo de 0,01. O modelo não vê nada ali.

## Leitura

- **O "sim" falso cai à metade** na T8.2 (14–16 → 7–8 de 45), com um custo de cerca de 2 %, longe
  dos 10 %. Nos ouros, ele fica em 5–6 %, perto do aceite.
- **O aceite ainda não passa na T8.2**: 16–18 % contra a meta de 5 %. A regra de parada (custo
  acima de 10 % na T8.2) não dispara.
- O `_atqc` dá o mesmo na T8.2. Fica de fora pela casa (0204).
- Para a base das mãos, isso já muda o quadro. A nota duvidosa sai do "sim", e o "sim" errado
  passa de cerca de 1 nota não atacada em 3 para 1 em 6 nos canais novos.
- O que sobra é sinal zero, sobretudo o mordente. Só o arco como objeto próprio (A2), ou mais
  gabarito de canais novos, ataca isso.
- A faixa ainda **não está no produto** (`tab.video` só grava a técnica). Pô-la no rótulo de
  ataque da base é o próximo passo barato. Ela vale com os pesos `_atqg`, que não são o
  `DETECTOR_PADRAO`.

## No produto (2026-10-19)

- `tab.ataque_rotulo.rotular` aplica a regra.
- `python -m tab.video ... --leitor rede --detector artefatos/detector_tab_final_atqg_s1/modelo.pt
  --rotulo-ataque` grava `ataque`, `ataque_motivo` e `nivel_rotulo: "prata"` em cada nota. O
  "não sei" sai com o motivo `tinta_sem_explicacao`.
- Sem o flag, nada muda. Com outros pesos, o flag é recusado, porque os limiares só valem para
  o `_atqg`.
- O `DETECTOR_PADRAO` não muda.
- Prova de fumaça num vídeo da T8.2 (Serge Kottelat, *The Winner Takes It All*): 238 notas, o
  esquema sem erro, 219 "sim" (3 delas por slide de entrada), 13 "não" e 6 "não sei".

## Fora de amostra: a T8.3 (2026-10-19)

A T8.3 tem 33 telas de 17 canais, de vídeos que não estão na T8.2 nem nos ouros
(`data/saida/t83/`, semente 1). O dono marcou as regiões e conferiu o ataque nas 33. O
conversor deu 1491 notas, 73 delas não atacadas (`r2/conferir_t83/`). Leitura pela dobra 0
(`r4c/medir_t83.py`), com os mesmos limiares, sem mudança.

| versão | medida | L = 0,02 (faixa) | 0,15 | 0,5 |
| --- | --- | --- | --- | --- |
| `_atqg` | "sim" falso | **16 · 15 · 16 /76** (20–21 %) | 24 · 21 · 23 | 46 · 44 · 42 |
| `_atqg` | custo | 37 · 38 · 32 /~1403 (2,3–2,7 %) | 18 · 18 · 11 | 8 · 8 · 8 |
| `_atq` | "sim" falso | 36 · 34 · 37 /78 | 45 · 41 · 44 | 53 · 50 · 48 |
| `_atq` | custo | 31 · 30 · 31 | 12 · 15 · 16 | 6 · 9 · 11 |

- A faixa se mantém fora de amostra: 20–21 % na T8.3, contra 16–18 % na T8.2. O custo fica
  abaixo de 3 %.
- O gerador do R4b (`_atqg`) pesa muito fora de amostra: com a mesma faixa, o `_atq` deixa
  passar mais que o dobro.
- O aceite (≤ 5 %) continua longe.

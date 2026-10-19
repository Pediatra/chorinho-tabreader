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

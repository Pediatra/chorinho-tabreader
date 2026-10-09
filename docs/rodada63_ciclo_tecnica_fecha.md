# Rodada 63 — o ciclo da técnica termina: o problema do `raman` é LIXO, não técnica

## 1. O teste decisivo (relabelagem por leitura)

Relabeli como `tecnica` **apenas os 7 tokens que eu confirmei na imagem** terem marca de técnica
(índices 3, 4, 5, 6, 12, 19, 20 — todos com barra diagonal atravessando o algarismo):

| semente | raman | TOTAL |
| --- | --- | --- |
| 0 | **9/24** | 0,771 |
| 1 | **9/24** | 0,823 |
| 2 | **10/24** | 0,802 |

**Piorou** (era 12/24; 0,844–0,875). E o motivo é a descoberta importante:

**O modelo já acerta o ALGARISMO nesses tokens.** Ao trocar o rótulo de `7` para `tecnica`, eu
transformei **7 acertos em 7 erros** — porque ele responde `7`, que é o que o JSON precisa.

## 2. A conclusão do ciclo (rodadas 55–63)

| hipótese | veredito |
| --- | --- |
| o `raman` erra por causa da marca de técnica fundida | **falsa** — o modelo lê esses tokens certo |
| o problema é regra de visão | **falsa** (3 tentativas) |
| o sintético não continha o fenômeno | **verdadeira** (3,2 % × 74 %), corrigida para 11,7 % |
| a classe `tecnica` melhora a acurácia | **falsa** — melhora a *estabilidade* (amplitude 0,062→0,031), não o acerto |
| **o que resta no `raman` é LIXO** | **verdadeira** |

Evidência do lixo: no `raman`, dos **70 tokens com ≥2 componentes**, ~**27 são barras verticais** sem
algarismo. E no gabarito, **7 dos 24 rótulos são `junk`** — e o modelo **não tem** essa classe
(removida na rodada 22 por ser uma troca entre canais).

## 3. Onde o trabalho deve ir agora

**A classe de rejeição, por canal.** Na rodada 22 eu medi que ela era uma troca (ganhava 6 notas no
`raman`, perdia 5 em `sky`+`paolo`). Mas isso foi medido com um mecanismo só. Agora eu sei:

- no `raman` há **muito mais lixo** que nos canais limpos;
- o `sky guitar`, `iwaki` e `paolo` estão em 27/27, 27/27 e 30/30 — **não têm o problema**;
- logo a rejeição deve ser **por canal**, não global: ligada para canais com lixo, desligada nos
  limpos. É o tipo de decisão que o inventário do acervo (rodada 3) já permitiria tomar por medição:
  contar a fração de tokens sem algarismo por canal.

## 4. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** — casas | **0,875** melhor seed · **0,854** média de 3 sementes · 0,955 sobre os alcançáveis |
| **canais limpos** | `iwaki` 27/27, `sky` 15/15, `paolo` 30/30 |
| **`raman`** | 12/24 — **causa final identificada: lixo**, não técnica |
| **classe `tecnica`** | treinada, estável, **sem ganho de acerto** — mantida por estabilidade, não por mérito |
| **gabarito** | restaurado (rótulos = algarismo), com a observação registrada |
| **tempo** | faixa (`skyguitar`, 0,16 s) e cor (`cifra club`, 41/41 onsets) |

## 5. Próximo passo

1. **medir a fração de tokens-lixo por canal** (barato: tokens cujo recorte não tem algarismo);
2. **classe de rejeição condicionada ao canal** — ligada onde há lixo, desligada onde não há;
3. reaferir com 3 sementes, verificando que os canais em 1,00 **não regridem**;
4. ampliar o gabarito para casas 8–24.

O ciclo custou oito rodadas e terminou com uma resposta clara: **o que eu pensava ser o problema não
era.** O modelo já lê algarismos com slide; o que ele não sabe é **recusar lixo** — e isso só apareceu
quando eu parei de inferir e li os 70 tokens.

# Rodada 52 — hipótese testada e derrubada: não é fragmentação

## 1. O que eu supus e o que medi

**Hipótese:** a faixa de remoção da corda (±0,15 passo = ±6,6 px neste painel) estaria comendo as
barras horizontais dos algarismos, partindo-os em fragmentos de 14–17 px.

**Teste:** refiz a extração com faixa de ±0,15, ±0,08 e ±0,05 passo:

| faixa | glifos | largura mediana | largura/passo |
| --- | --- | --- | --- |
| ±0,15 passo | 57 | **17 px** | 0,38 |
| ±0,08 passo | 57 | **17 px** | 0,38 |
| ±0,05 passo | 57 | **17 px** | 0,38 |

**Idêntico nos três.** A faixa de remoção **não** é a causa — hipótese derrubada.

## 2. O que isso provavelmente significa

17 px neste painel (passo 44) é **0,38 passo**. E eu tinha assumido que o algarismo deveria ter
~0,7 passo. Comparando com o canal que eu já validei (`skyguitar`, passo 30): algarismos de 17–18 px
= **0,6 passo**. Ou seja, este painel usa um **algarismo menor em relação ao passo** — o que é
plausível para um layout de vídeo, com fonte pequena e cordas espaçadas.

Então os glifos **não estão fragmentados**: eles são pequenos *de verdade*.

E aí a explicação do `harmonico` muda: **não é fragmento, é incompatibilidade de forma com o meu
treino sintético**, que desenha algarismos a ~0,95 passo de fonte. Um algarismo estreito e alto
(0,38 passo de largura) parecido com um `<n>` — e o modelo escolhe `harmonico`.

## 3. A correção certa muda de lugar

- **não** é consertar extração (ela está correta);
- é **variar o tamanho da fonte no gerador sintético** (hoje fixo em ~0,95 passo) para cobrir
  algarismos de 0,35 a 0,8 passo de largura — que é o que o acervo real contém.

É a mesma lição das rodadas anteriores: o gargalo é **cobertura do gerador**, não regra de visão.

## 4. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, técnica) | **0,805** (3 sementes) nos 4 canais com gabarito |
| **painel escuro** | grade e extração **corretas** (6 cordas, 57 glifos de 0,38 passo): a extração não estava quebrada |
| **tempo — marcador por cor** | onset medido (41/41 notas, 8 ataques, 1,80 s) |
| **classificador** | erra `harmonico` em algarismo pequeno — **cobertura de tamanho no sintético** |

## 5. Próximo passo

1. **sortear o tamanho da fonte** no `tools/sintetico.py` (0,35–0,85 passo, em vez de 0,95 fixo);
2. retreinar e medir com **3 sementes** (a regra que eu estabeleci) no gabarito real;
3. só então reclassificar o painel do `cifra club` e conferir se o `harmonico` some;
4. seguir para a janela maior (reinício de frase) e a aferição da casa neste canal.

Registro a hipótese derrubada de propósito: eu ia "consertar" uma extração que estava certa. Duas
linhas de medição evitaram que eu mexesse no lugar errado — e a causa real está no dado de treino.

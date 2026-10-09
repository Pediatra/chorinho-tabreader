# Rodada 58 — patch correto, fenômeno ainda ausente: o portão segue fechado

## 1. O que foi feito, com as travas que eu passei a exigir

1. **`ast.parse` antes de escrever**: a primeira tentativa de inserção caiu no meio da chamada do
   `d.arc` (que ocupa 4 linhas) e o `ast.parse` **rejeitou** — o arquivo **não foi escrito**;
2. segunda tentativa, inserindo **depois** da chamada completa: `ast.parse` **OK**, arquivo escrito;
3. **`import` verificado** em seguida: **OK**;
4. só então medi.

O gerador está íntegro e agora desenha, em 80 % das notas com técnica, uma **diagonal que atravessa
o algarismo** (o caso do canal real).

## 2. A medição — e ela não mudou

| | |
| --- | --- |
| tokens | 740 |
| receberiam o rótulo `tecnica` | **24 (3,2 %)** |
| limiar | 10 % |
| **treinar?** | **não** |

**O patch está aplicado e o fenômeno continua ausente.** Ou seja: desenhar a diagonal atravessando o
algarismo **não** faz o token fundir (a condição medida é `partes ≥ 2`).

## 3. As duas leituras possíveis (a medir na próxima rodada)

1. **a contagem de notas com técnica não subiu** — a troca de `rng.random() < 0.08` para 0.30 pode
   não ter aplicado (é o tipo de edição que eu já vi falhar silenciosamente nesta série);
2. **a fusão não acontece de fato** — as duas formas se cruzam na imagem, mas no raster podem não
   compartilhar pixels; ou a remoção da corda corta a diagonal antes da rotulagem.

Medir qual das duas é barato: contar (a) quantos tokens correspondem a notas com técnica e (b)
quantos desses têm `partes ≥ 2`. Se (b) for alto e (a) baixo, a culpa é da fração de técnicas; se
(b) for baixo, a marca não está tocando o algarismo.

## 4. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** — casas | **0,885** bruto · **0,955** sobre os rótulos alcançáveis |
| **canais limpos** | `iwaki` 27/27, `sky` 15/15, `paolo` 30/30 |
| **`raman`** | 13/17 — causa medida (3,2 % × 74 %) |
| **classe `tecnica`** | rótulo e geometria prontos; **fenômeno ainda não produzido** |
| **tempo** | faixa (`skyguitar`, 0,16 s) e cor (`cifra club`, 41/41 onsets) |
| **gerador** | íntegro; `ast.parse` + `import` verificados |

## 5. O que esta rodada vale

**Nenhum treino queimado** — o portão fez o trabalho duas vezes seguidas — e o **hábito novo
funcionou**: o `ast.parse` barrou uma edição que quebraria o arquivo, antes de eu medir qualquer
coisa. É a diferença entre a rodada 57 (quebrei) e esta (a trava pegou).

O que falta é uma medição de duas linhas (fração de notas com técnica × taxa de fusão) para saber
qual dos dois lados ajustar. Não é uma tentativa às cegas: é escolher entre duas causas já
formuladas.

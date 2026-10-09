# Rodada 16 — a correção certa: 0,802 → 0,854

## 1. O que foi corrigido

A rodada anterior localizou o modo de falha: em parte dos canais **a corda passa por cima do
algarismo**, acrescentando um traço horizontal que fazia o modelo ler `1` como `4`. O gerador
sempre desenhava o **buraco** na corda (estilo MuseScore).

Mudança: o buraco na corda passou a ser **sorteado** — metade das linhas sintéticas com buraco,
metade com a corda por cima. É uma linha de código, e **soma** variedade em vez de substituir
(por isso não repetiu o estrago da rodada 14, em que troquei uma forma por outra).

## 2. Resultado medido

| canal | antes | **depois** |
| --- | --- | --- |
| iwaki | 27/27 = 1,00 | **27/27 = 1,00** |
| sky guitar | 15/15 = 1,00 | **15/15 = 1,00** |
| raman korshun | 12/24 = 0,50 | 12/24 = 0,50 |
| paolo d'angelo | 23/30 = 0,77 | **28/30 = 0,93** |
| **TOTAL** | 77/96 = 0,802 | **82/96 = 0,854** |

Os dois canais que estavam em 1,00 **continuaram em 1,00** — a mudança não custou nada. O canal
que motivou a correção subiu 0,16. Os erros `1 → 4` caíram de 3 para 2.

Comparando as abordagens, todas medidas no mesmo gabarito:

| tentativa | efeito |
| --- | --- |
| rodada 12 — regra de altura no extrator | 0 (não mudou) |
| rodada 13 — regra de orientação no extrator | 0 (não mudou) |
| rodada 14 — trocar arco por barra no gerador | **−0,166** (revertida) |
| **rodada 16 — somar variação de corda no gerador** | **+0,052** |

Três tentativas de consertar na **geometria** falharam; a que funcionou foi a que **cobriu o
dado**. Isso é o registro mais útil desta série: o gargalo deste sistema é cobertura de
renderização, não regra de visão.

## 3. Erros que restam (19 → 14)

- **raman korshun, 12 erros**: `junk → 1`, `junk → 5` (lixo virando algarismo — falta classe de
  rejeição) e `7 → harmonico` (marca de técnica ainda dentro do token);
- **paolo d'angelo, 2 erros**: `1 → 4` ainda em dois casos (a variação de corda ajuda, mas não
  cobre todas as formas);
- os dois canais MuseScore: **zero erros**.

## 4. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura, 95 % com cursor |
| (b) gabarito verificado | 96 glifos / 4 canais |
| (c) classificador multi-classe | **0,854 real** — 2 canais em 1,00; falhas concentradas em 2 canais |
| (d) pipeline ponta a ponta | corda, casa, técnica, tempo, compasso e andamento |
| (e) escala nos 3.781 | pendente |

Próximo passo, seguindo o que agora tem evidência: **classe de rejeição** para o lixo
(elimina a maior parte dos 12 erros do `raman korshun`), depois a **marca de técnica como
classe própria**, depois ampliar o gabarito e escalar.

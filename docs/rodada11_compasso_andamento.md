# Rodada 11 — compasso e andamento no JSON

## 1. O que foi acrescentado

`tools/reconhecer.py` ganhou `completar()`: numera o **compasso** pelas barlines já
detectadas e calcula o **andamento** a partir dos onsets do cursor.

Saída do artefato `saida/skyguitar_linha01.json`:

```json
{"ordem": 1, "corda": 2, "casa": "0", "tecnica": null, "x": 160,
 "confianca": 0.85, "compasso": 1, "t_ini": 1.84, "t_fim": 2.80}
```

```json
"notas_por_compasso": {"1": 4, "2": 4, "3": 4, "4": 3},
"andamento": {"notas_por_minuto": 59.9, "intervalo_mediano_s": 1.001,
              "notas_por_compasso_medido": 3.75, "bpm_se_1_nota_por_tempo": 59.9}
```

## 2. Verificação que vale mais que o número

O compasso **não foi dado**: foi deduzido das barlines, e deu **4/4/4/3 notas**. O gabarito
lido do vídeo é `0 0 0 0 | 1 1 1 1 | 3 3 3 3 | 1 1 0` — **exatamente 4, 4, 4 e 3 notas**.
Ou seja, a segmentação de compasso reproduziu sozinha a estrutura da música. É a terceira
verificação independente da mesma linha (as outras: 15 tokens com corda certa, e as casas
15/15).

Sobre o andamento, fui deliberadamente conservador: o que a imagem e o cursor permitem
**medir** é notas por minuto (59,9) e o intervalo mediano (1,001 s). BPM só sai disso com uma
suposição de figura, então ele vai num campo separado com o nome dizendo qual é a suposição
(`bpm_se_1_nota_por_tempo`) — não misturado com o medido.

## 3. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura, 95 % com cursor |
| (b) gabarito verificado | 66 glifos / 3 canais / 9 classes |
| (c) classificador multi-classe | 0,818 real — faltam classe de rejeição e separação de técnica |
| (d) pipeline ponta a ponta | corda, casa, técnica, tempo, **compasso e andamento** |
| (e) escala nos 3.781 | pendente |

Falta para o produto: **classe de rejeição** (lixo virando algarismo), **separação da marca
de técnica** do algarismo (o `7` + slide virando `24`), e a **partitura** em pauta (peça
separada, exige OMR próprio). Depois disso: ampliar o gabarito para 0–24 e rodar em escala.

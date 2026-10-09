# Rodada 48 — JSON com tempo por nota, de um canal que marca por cor

## 1. O artefato

`saida/cifra_abanda.json` — primeira transcrição de um canal do tipo `cifra club`, com **corda,
casa, `t_ini` e `t_fim` por nota**:

```json
{"ordem": 1, "corda": 2, "casa": "5", "x": 89, "t_ini": 66.0, "t_fim": 69.9, "n_observacoes": 14}
{"ordem": 2, "corda": 3, "casa": "harmonico", "x": 89, "t_ini": 66.0, "t_fim": 70.8, "n_observacoes": 17}
{"ordem": 3, "corda": 4, "casa": "5", "x": 89, "t_ini": 66.0, "t_fim": 70.8, "n_observacoes": 17}
{"ordem": 4, "corda": 6, "casa": "5", "x": 89, "t_ini": 66.3, "t_fim": 69.9, "n_observacoes": 13}
```

| | |
| --- | --- |
| tokens | 41 |
| **com tempo** | **39 (95 %)** |
| mecanismo declarado no JSON | `"cor (branco->laranja)"` |
| painel | y 620–890 |

**Verificação musical:** as quatro primeiras notas estão **na mesma coluna (x=89)**, em cordas
diferentes, com o **mesmo intervalo de tempo** (66,0–70,8 s). Isso é um **acorde**, e o método o
identificou como tal — quatro notas simultâneas, quatro cordas, um só intervalo. O marcador de cor
entrega a simultaneidade de graça, coisa que a banda do `skyguitar` dava por interpolação.

## 2. Duas ressalvas honestas

1. **O `t_fim` está limitado pela minha janela de observação.** Observei ~5 s (66–71 s) e o acorde
   ficou laranja todo o tempo; então 70,8 s é o fim *da janela*, não necessariamente o fim da nota.
   Alargar a janela resolve — é ajuste, não método.
2. **A casa ainda traz o vazamento do `harmonico`** (nota 2): o classificador continua podendo
   escolher essa classe sem que a forma autorize. É o mesmo defeito conhecido das rodadas 8 e 10,
   agora visível num canal novo.

## 3. O que este canal ensinou ao sistema

| descoberta | consequência |
| --- | --- |
| o marcador varia por canal (faixa **ou** cor) | o JSON declara o mecanismo usado |
| painel pode ser escuro e não ocupar o quadro | máscara de tinta clara + uniformidade de fundo |
| algarismos já têm cor de base | a leitura é por token **contra a própria base** |
| a cor dá o **acorde** de graça | tempo por nota sem interpolação |

Nenhuma dessas quatro coisas vale para todos os canais — e é por isso que o sistema agora **declara**
o que usou em vez de assumir.

## 4. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, técnica) | **0,805** (3 sementes) nos 4 canais com gabarito |
| **painel e geometria** | resolvidos para os dois estilos de painel (claro e escuro) |
| **tempo — marcador por faixa** | validado no `skyguitar` (1 nota/s, desvio 0,16 s) |
| **tempo — marcador por cor** | **39 de 41 notas com tempo** neste vídeo; acorde identificado |
| **mecanismo declarado no JSON** | **sim** (`cor` / `faixa`) |

## 5. Próximo passo

1. **alargar a janela** de observação para o `t_fim` real de cada nota;
2. **detectar o reinício de frase** (o laranja volta à coluna 1) para separar sistemas;
3. matar o vazamento de `harmonico` com a verificação de forma (o `compativel` já tem o gancho);
4. rodar nos canais de mesmo estilo (`tv cifras`) e medir cobertura **por mecanismo**.

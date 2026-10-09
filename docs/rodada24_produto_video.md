# Rodada 24 — o comando de produto existe (e o que ele expôs)

## 1. O que foi criado

`tools/transcrever.py`: **vídeo → JSON** em um comando. Faz painel (3 faixas) → grade de 6
cordas → tokens → classificador sintético → compasso → tempo pelo cursor → JSON.

```bash
.venv/bin/python tools/transcrever.py VIDEO --inicio 0.4 --janela 25 --json saida/video_completo.json
```

Rodou num vídeo real do acervo (`shin izumi/canon in d`, lido **via ffmpeg** — o fallback dos
44 % que o OpenCV não abre):

| campo | valor |
| --- | --- |
| painel | base |
| passo entre cordas | 21,6 px |
| notas | **76** |
| barlines detectadas | 10 |
| notas por compasso | `{1:12, 4:5, 8:26, 9:33}` |

## 2. Duas lacunas que a execução expôs

**1. O tempo não veio.** As notas saíram sem `t_ini`/`t_fim` — o cursor não foi encontrado na
janela rastreada deste vídeo/canal. O código prevê o caso (devolve `None` em vez de valor
errado, o que é correto), mas na prática significa que **o produto ainda não entrega tempo em
todos os canais**, e sim nos que têm banda colorida bem destacada.

**2. A numeração de compasso não é confiável neste canal.** `{1:12, 4:5, 8:26, 9:33}` é
implausível: há barlines não detectadas (o salto de x=722 para x=1280) e o número de notas por
compasso explode. O compasso 4/4/4/3 verificado no `skyguitar` continua válido **naquele** canal;
aqui a detecção de barline falhou.

Isso é o esperado de um primeiro rollout honesto: a **geometria da grade** generaliza (76 notas
extraídas, 6 cordas, painel localizado em 3 faixas), mas os **dois anexos** — tempo e compasso —
dependem de condições que este canal não satisfaz.

## 3. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura, 95 % com cursor |
| (b) gabarito verificado | 96 glifos / 4 canais |
| (c) classificador multi-classe | **0,805 (3 sementes)** |
| (d) pipeline ponta a ponta | **comando único `transcrever.py`**; tempo e compasso funcionam em parte dos canais |
| (e) escala nos 3.781 | pré-requisito cumprido; rollout não iniciado |

## 4. Próximos passos, por ordem de impacto

1. **barline robusta**: hoje é o elo mais frágil do anexo de compasso (o `skyguitar` funciona
   porque as barlines são limpas);
2. **cursor**: medir em quantos dos 12 canais ele é detectável — o inventário já deu 95 % ao
   longo do vídeo, mas a janela de 25 s e a exigência de patamar podem estar apertadas;
3. **gabarito maior** (casas 8–24, mais canais) — o que limita a acurácia medida;
4. **marca de técnica como classe própria**.

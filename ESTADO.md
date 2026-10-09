# Estado do projeto — índice e próximo passo

Documento de entrada. **Números medidos com repetição (3 sementes)**, nunca em execução única.

## Número oficial

**0,851 de acerto no gabarito real** (média de 3 sementes: 0,844 / 0,823 / 0,885), sobre **96 glifos
rotulados à mão em 4 canais**, casas 0–7.

| canal | situação |
| --- | --- |
| iwaki (tema escuro) | **27/27 nas três sementes** |
| sky guitar | **15/15 nas três sementes** |
| paolo d'angelo | 26–30 de 30 |
| raman korshun (slides/harmônicos) | 11–13 de 24 — o canal difícil |

Número anterior: 0,805 (fonte fixa no gerador). O ganho veio de **variar o tamanho da fonte** no
sintético, não de mexer na visão.

## Os três anexos do JSON

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa) | **0,851**; corda/coluna/compasso robustos |
| **técnica** | taxonomia existe no sintético; **aferição em dado real pendente** |
| **tempo** | dois mecanismos identificados e um medido em cada caso (abaixo) |
| **partitura** | fora desta cadeia — exige OMR próprio |

### Tempo — os dois mecanismos (o marcador VARIA por canal)

| mecanismo | canal verificado | resultado |
| --- | --- | --- |
| **faixa vertical** que passa | `skyguitar` | 1 nota/s, desvio **0,16 s** (corrigível para ~33 ms) |
| **algarismo fica laranja** (cumulativo) | `cifra club` | **onset por nota, 41/41**, 8 ataques distintos, intervalo 1,80 s |

O JSON **declara o mecanismo** usado. No marcador por cor, o que se mede é o **onset** — não a
duração (o algarismo continua laranja depois de tocado).

## Geometria e localização do painel

- **5 famílias** de renderização tratadas; 163/163 linhas nos recortes herdados;
- **painel claro**: máscara de tinta escura;
- **painel escuro** (estilo `cifra club`): **máscara de tinta clara** + **uniformidade de fundo**
  para achar o painel e **rejeitar o vídeo do violão** (o braço tem 6 cordas — parece uma tablatura);
- painel do `cifra club`: 6 cordas, **passo 44,2 px**, 41 tokens, algarismos de **0,38 passo**.

## Lições metodológicas (custaram rodadas)

1. **Fixar a semente do PyTorch** e medir ≥3 vezes. Antes disso o mesmo código dava 0,729 e 0,854 —
   e eu reportei ruído como ganho.
2. **Medir a amostra antes de gastar o treino** (três retreinos foram gastos descobrindo que a classe
   de rejeição não nascia).
3. **O gargalo é cobertura do gerador, não regra de visão** — medido seis vezes: três regras
   geométricas deram 0, uma deu −0,166, e as duas mudanças de dado deram +0,052 e +0,046.
4. **Olhar o quadro antes de teorizar.** Duas vezes medi o violão achando que era a tablatura
   (o corpo, rodada 33; o braço, rodada 39) — e a resposta estava numa imagem de um segundo.
5. **Conferir o significado do número.** "323 notas com tempo" eram 3 instantes; "41 notas com
   duração" eram 8 ataques sem duração. Contar **instantes distintos** e perguntar o que o dado
   contém, sempre.

## Ferramentas

| arquivo | o que faz |
| --- | --- |
| `tools/tabseg.py` | grade: 6 cordas, tokens, rótulo TAB; 5 famílias + painel escuro |
| `tools/cursor.py` | cursor por faixa (x(t), saltos, sistemas) |
| `tools/inventario.py` | varre o acervo (família, painel, marcador) + fallback ffmpeg |
| `tools/ouro.py` | glifos isolados do acervo para rotular à mão |
| `tools/sintetico.py` | gerador sintético + treino (`--seed`) |
| `tools/reconhecer.py` | ponta a ponta: linha → corda, casa, técnica, compasso, tempo |
| `tools/transcrever.py` | vídeo → JSON (painel, grade, marcação, tempo) |
| `tools/avaliar.py` | aferição padronizada no gabarito (3 sementes) |
| `gold/gabarito.json` | 96 glifos rotulados à mão, 4 canais |
| `saida/` | artefatos: `skyguitar_linha01.json`, `cifra_abanda.json`, `rollout/` |

## Próximo passo

1. **marca de técnica como classe própria** — é o único erro grande que resta (`raman`, 11–13 de 24;
   o `7` com barra de slide é fundido no token do algarismo);
2. **ampliar o gabarito real** para casas 8–24 e mais canais — é o que limita a medição;
3. **janela maior** no marcador por cor, para o reinício de frase;
4. **rodar em escala** nos canais com gabarito e nos de mesmo estilo.

## Ressalvas

- 96 glifos, 4 canais, **casas 0–7**; as casas 8–24 e a maioria das técnicas **não foram aferidas em
  dado real**;
- a aferição é glifo a glifo, não da música inteira;
- **tab ASCII** (Ultimate Guitar) precisa de leitor próprio;
- a casa dos canais fora do gabarito (como o `cifra club`) **não foi aferida** — neles há corda,
  coluna e tempo, mas a casa ainda não tem validação.

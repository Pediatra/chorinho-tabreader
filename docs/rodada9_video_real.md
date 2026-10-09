# Rodada 9 — aferição em vídeo real: 42/42

## 1. O que foi medido

Até agora o 15/15 tinha sido medido num **recorte herdado** (arquivo do pipeline antigo).
Esta rodada mediu num **quadro de vídeo real**, extraído direto do acervo, num canal
diferente e mais difícil:

| | skyguitar (recorte legado) | **iwaki (vídeo real)** |
| --- | --- | --- |
| tema | claro | **escuro** |
| onde está a tablatura | topo | **base** |
| passo entre cordas | 30 px | 30 px |
| tokens | 15 | **27** |
| acerto | **15/15 = 1,000** | **27/27 = 1,000** |
| confiança média | — | **0,958** |

**Total: 42/42 = 1,000**, com o modelo treinado **exclusivamente em dado sintético** — ele
nunca viu nenhum dos dois vídeos, nenhum dos dois canais e nenhum dos dois temas.

Detalhe que dá confiança no número: a lista prevista e a correta são idênticas posição a
posição, sem erro esporádico escondido por média:

```
previsto: 0 3 2 0 1 3 0 3 0 3 3 0 1 0 0 0 2 0 1 3 0 3 0 0 3 1 0
correto : 0 3 2 0 1 3 0 3 0 3 3 0 1 0 0 0 2 0 1 3 0 3 0 0 3 1 0
```

## 2. O que isso prova, e o que não prova

**Prova:** o método (geometria determinística + tokens + classificador minúsculo treinado em
sintético + verificação de forma) funciona em vídeo real, em canal novo, tema escuro e
tablatura na parte de baixo do quadro. Não é um resultado de laboratório.

**Não prova**, e continua registrado sem maquiagem:

- o gabarito tem **42 glifos e 4 classes** (0, 1, 2, 3). As casas **4–24**, os números de
  2 dígitos e as **técnicas** não foram aferidos em dado real;
- são **2 canais** de 12;
- é uma linha por canal, não a música inteira.

Ou seja: o acerto de 1,000 é verdadeiro, mas num recorte estreito do problema. Ele sustenta
que o **método** está certo; não sustenta que o sistema tem 100 % de acerto no acervo.

## 3. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura, 95 % com cursor |
| (b) gabarito verificado | 42 glifos / 2 canais — **é o que limita a medição agora** |
| (c) classificador multi-classe | **funcionando** — 42/42 em vídeo real, verificado por forma |
| (d) pipeline ponta a ponta | corda, casa, técnica, tempo, barlines e confiança |
| (e) escala nos 3.781 | pendente |

O gargalo mudou de lugar: antes era o modelo (0,70 entre canais), agora é o **gabarito**.
Enquanto ele tiver 4 classes, qualquer número que eu reportar mede só essas 4 classes.

Próxima rodada, na ordem: (1) ampliar o gabarito para cobrir **0–24 e as técnicas** em mais
canais — é o único caminho para uma medição honesta do sistema; (2) compasso numerado e
andamento no JSON; (3) rodar a música inteira de ponta a ponta num vídeo; (4) escala.

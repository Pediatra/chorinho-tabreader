# 3024 — o homr nas notas que faltam, sem tablatura

Trilha partitura. Data: 2026-10-15. Sem mudança de código: é medição. Scripts e saídas em
`data/saida/partitura/diag/homr_sem_produto/`.

## Pergunta

No gabarito sem produto (rodada 3023) faltaram 40 notas, 31 delas no athletic P01a. Sem
tablatura não há como confirmar uma nota nova. Quantas o homr recupera, e quantas inventa?

## Método

1. homr nativo nos 3 recortes (`rodar.py`, CPU, 8–12 s cada; 3/3 ok).
2. Primeiro, o método da 3005 (`fusao.py`): alinhamento de eventos, com a posição do
   acréscimo pela coluna de cabeças do `.omr`. Deu 13 de 40 recuperadas e 36 acréscimos
   sem clique. No athletic, porém, o `.omr` tem 50 colunas para 37 eventos, e a posição
   cai no lugar errado.
3. Por isso medi **por compasso** (`regra.py`):
   - **acréscimo** é cada degrau que sobra no homr em relação ao Audiveris, no mesmo
     compasso;
   - **clique do dono** é localizado no compasso pela posição x entre as barras do `.omr`
     e no degrau pela posição y;
   - **recuperado** é um clique com acréscimo no mesmo compasso e degrau;
   - **inventado** é um acréscimo aceito que não tem clique.

   Testei também uma **regra**: aceitar os acréscimos de um compasso só se o homr tem pelo
   menos `razão` vezes as notas do Audiveris nele. A ideia é usar o homr só onde o
   Audiveris claramente perdeu uma voz.
4. A mesma conta foi feita no gabarito antigo (R01–R20, rodada 3004), para não ajustar a
   regra a 3 recortes. 6 recortes antigos ficam fora porque o homr e o Audiveris têm número
   de compassos diferente (24 cliques). O R20 só conta nas recuperadas, como no adendo da
   3005.

## Resultado

Sem produto (3 recortes, 40 cliques):

| regra | recuperadas | inventadas |
| --- | ---: | ---: |
| união cega | 30 | 15 |
| razão 1,25 | 30 | 11 |
| razão 1,5 | 27 | 10 |
| **razão 2** | **25** | **8** |
| razão 3 | 15 | 5 |

Gabarito antigo (14 recortes comparáveis, 50 cliques):

| regra | recuperadas | inventadas |
| --- | ---: | ---: |
| união cega | 27 | 11 |
| razão 1,25 | 20 | 5 |
| razão 1,5 | 7 | 2 |
| **razão 2** | **5** | **2** |

Por recorte:

- **athletic P01a:** com razão 2, o homr recupera 25 dos 31 cliques. Nos compassos 3 e 4,
  o homr leu 26 e 18 notas, contra 6 e 7 do Audiveris. A voz de cima existe na leitura do
  homr.
- **agua P01a:** as faltas são notas soltas em acorde (Audiveris 7 contra homr 11 notas no
  compasso 1). A razão 2 não aceita nada ali.
- **canon P06a:** nada faltando, nada acrescentado.

## O que os números dizem

- **Onde o Audiveris perde uma voz inteira, o homr a tem.** É o caso do athletic e, no
  gabarito antigo, de R08 e R19. A razão 2 pega exatamente esse caso. Somando os dois
  gabaritos: 30 recuperadas e 10 inventadas, **3 certas para cada inventada**.
- **Nota solta em acorde não tem solução assim.** Para aceitá-la é preciso a união cega
  ou uma razão baixa, e aí as inventadas sobem.
- **A medida por compasso é mais branda que a por evento** (3005: 31 recuperadas contra
  133 inventadas na união cega). Ela confere se a altura existe no compasso, não se a nota
  entrou no tempo certo. Para entrar no produto, a nota do homr precisa de tempo. O mais
  limpo é trocar o compasso inteiro do Audiveris pelo do homr quando a razão passa de 2,
  em vez de juntar nota a nota.

## Recomendação (decisão do dono)

Nenhuma regra zera as inventadas sem tablatura. Proposta:

- quando o homr tem pelo menos 2× as notas do Audiveris num compasso, usar o compasso do
  homr;
- cada nota sai com `origem: "homr"` e marcada **"sem confirmação"**, para quem consome
  poder filtrar;
- nada é jogado fora: a leitura do Audiveris continua gravada.

Antes de valer, o dono confere esses compassos trocados.

## Limites

- São 3 recortes sem produto e 14 antigos. A razão 2 aceitou 33 + 7 notas no total, então
  é amostra pequena.
- "Inventada" é estimativa: um acréscimo sem clique pode ser um símbolo que o dono marcou
  com altura errada, ou um clique que caiu no compasso vizinho.
- 6 recortes antigos ficaram fora porque o homr junta ou separa compassos.

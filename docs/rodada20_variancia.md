# Rodada 20 — achado que invalida parte das minhas comparações

## 1. A descoberta

Rodei o **mesmo código** duas vezes (mesmo gerador, mesmas 320 linhas, mesmas 22 épocas, mesmo
gabarito) e obtive:

| execução | total | sky guitar | raman | paolo |
| --- | --- | --- | --- | --- |
| 1 | **0,854** | 0,67 | 0,75 | 0,90 |
| 2 | **0,729** | 0,27 | 0,75 | 0,83 |

**Variação de 0,125 no total e de 0,40 num canal — sem mudar uma linha de código.**

Causa: eu fixei a semente do **gerador** de dados (`random.Random(1)`), mas **nunca fixei a
semente do PyTorch**. A inicialização da rede e a ordem dos lotes mudam a cada execução.

## 2. O que isso invalida — e eu preciso dizer

Todas as comparações que fiz rodada a rodada foram de **execução única**. Com uma variância de
0,12, diferenças como:

- 0,802 → 0,854 (rodada 16, a correção da corda-por-cima) — **pode ser ruído**;
- 0,854 → 0,865 (classe de rejeição) — **está dentro do ruído**;
- 0,854 → 0,729 — **é o mesmo código**.

Ou seja: **as melhorias de +0,05 que eu reportei não estão demonstradas.** O efeito da
corda-por-cima (que subiu o `paolo` de 0,77 para 0,93 de forma consistente em duas medições
seguidas) é o candidato mais forte a ser real, mas nem ele foi medido com repetição.

O que continua sólido, porque não depende de treino estocástico:

- a **geometria** (96 % do acervo, 15/15 e 27/27 nos canais verificados, compasso 4/4/4/3);
- os **modos de falha identificados** (lixo → algarismo; `1` → `4` com corda por cima);
- a **taxa de fragmentação** (1,44 glifos por nota antes da tokenização).

O que precisa ser refeito com rigor: **toda comparação de acurácia entre versões do modelo.**

## 3. Correção metodológica (próxima rodada, primeiro item)

1. `torch.manual_seed(s)` e semente nos lotes;
2. rodar **no mínimo 3 sementes** por configuração e reportar **média e amplitude**;
3. só considerar ganho o que ficar acima da amplitude medida.

Sem isso, continuo otimizando ruído — e pior: escolhendo configurações por sorte.

## 4. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** |
| (b) gabarito verificado | 96 glifos / 4 canais |
| (c) classificador multi-classe | **número atual não é confiável** — varia 0,73–0,87 entre execuções |
| (d) pipeline ponta a ponta | corda, casa, técnica, tempo, compasso e andamento |
| (e) escala nos 3.781 | pendente |

O modelo em `/tmp/sint/glifo_sint.pt` neste momento é o de 0,729 — deve ser retreinado com
semente fixa antes de qualquer nova medição. O código está íntegro.

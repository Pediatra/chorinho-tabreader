# 1039 — Ciclo de capo: shin izumi (a prova lacrada da 1037)

**Data**: 2026-10-21 (janela autônoma). O pré-registro vem antes da triagem e do sorteio.

**A pergunta**: num canal que o retreino da [1037](1037-retreino-com-capo.md) quase não viu, e
em vídeos que nunca entraram em nada, o detector numera a partir do capo sem deixar passar erro
calado?

**Por que o shin izumi**:
- **Não foi ciclado.** Do canal, só entraram no treino da 1037 os R de 4 chaves da M3b sem
  capo. A chave com capo (q10) ficou fora.
- **Tem capo com frequência**: 4 de 11 vídeos nos gabaritos (`capo_por_video.json`).
- **Tem vídeo horizontal**, com a cabeça do violão às vezes visível: é o caso "nut e capo juntos"
  da decisão 1010.
- Os outros canais com muito capo já entraram no treino da 1037: kenneth (M32 e M3b) e guitarous
  (M27). O violaodecria é a medida da própria 1037.

## Lote

1. **Triagem** (`maos_braco_ciclo triar --rodada 1039`):
   - 40 vídeos do canal, sorteados com a semente `20261039:triagem`, fora de todas as amostras
     anteriores (M3b, R, C, N, M11b, 1026, 1027, 1029, 1032 e 1036);
   - um quadro no meio de cada um, numa folha (`m39/triagem.jpg`);
   - eu olho a folha e marco `capo_visto` em cada candidato. **Não é rótulo**: é só a escolha da
     amostra. A marca de cada candidato fica registrada aqui antes do sorteio, e quem confirma o
     capo é o dono, na revisão.
2. **Sorteio** (`maos_braco_ciclo sortear --rodada 1039`): 8 vídeos entre os marcados com capo,
   com a semente 20261039, e 8 quadros por vídeo, de 0,15 a 0,85 da duração. São 64 quadros.
   - **Se houver menos de 8 com capo**, o lote fica com os que houver, todos com 8 quadros. O
     número fica registrado.
   - **Os vídeos sem capo não entram**: o desempenho sem capo já foi medido nos ciclos 1026,
     1029 e 1032, e no critério 3 da 1037.

## Detector

- **Se a 1037 passar nos três critérios**: o par escolhido nela (L4 + A6), com a regra de
  revisão da 1023 e o sinal de nut suspeito v2 (1033).
- **Se não passar**: o par antigo da 1032 (`L3_todos_s3` + `A4_100_todos_s1`), com a mesma regra
  e o mesmo sinal. Nesse caso, o ciclo mede o tamanho do problema do capo num canal novo, e o
  lote vira dado de treino da próxima tentativa.
- P2 e P3 ficam desligados.

## O que o dono faz

O protocolo da 1036, com a regra do capo (decisão 1010):
- os sinalizados aparecem primeiro;
- **com capo**: o nut no traste à frente do capo, o `k` no corpo do capo e a casa do capo na
  observação ("capo 2");
- nut fora com o traste de referência;
- 7 cordas com o botão.

## Medidas e critério

São as do ciclo (`maos_braco_ciclo medir --rodada 1039`), mais o recorte dos quadros com capo,
pela marca `k` do dono.

| resultado | o que fazer |
| --- | --- |
| falsos que passam ≤ 5 % (no máx. 3 de 64) **e** no máx. 1 nos quadros com capo | o capo está resolvido para o ciclo. As marcas da 1036 e da 1039 entram no retreino seguinte |
| falsos que passam ≤ 5 %, mas 2 ou mais nos quadros com capo | o ciclo é seguro no geral, mas o capo não. Vídeo com capo vai para revisão inteira até a 1038 (detecção do capo) |
| falsos que passam > 5 % | parar e investigar por tipo de erro |

**Também reportado**:
- quantos dos quadros com capo têm o nut verdadeiro visível;
- a calibração (decisão 2005): certos entre os sem sinal e entre os sinalizados.

## Riscos declarados antes

- **A triagem olha um quadro só.** Um vídeo em que o capo aparece no meio pode não ter capo em
  outro trecho, ou o contrário. O dono marca quadro a quadro, e a medida usa a marca dele.
- **O canal tem tela com tablatura grande**: o braço pode ficar pequeno, e o estágio 1 não
  achar o braço. Isso é "sem braço", e não erro.

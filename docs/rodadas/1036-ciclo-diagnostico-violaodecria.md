# 1036 — Ciclo diagnóstico: violaodecria (nut fora em cortes verticais)

**Data**: 2026-10-20. O pré-registro vem antes de qualquer previsão no lote.
**Estado**: regras a priori. **O canal foi escolhido pelo dono**, que guardava esses vídeos "pro
final": são cortes verticais (formato tiktok), e na maioria o nut aparece em poucos quadros, ou
nem aparece.

**A pergunta**: com o nut fora da imagem, o detector erra a numeração sem avisar, ou o sinal de
nut suspeito (v2, [1033](1033-sinal-de-nut-suspeito-v2.md)) manda esses quadros para revisão?

**Antecedentes**:
- [1029](1029-ciclo-de-revisao-pablo-rome.md): 4 falsos que passam, todos com o nut fora da
  imagem. O padrão é o 1º traste visível tomado por nut, e a numeração desloca 1 casa.
- [1031](1031-nut-fora-por-vizinhos-e-juncao.md): os métodos V e J e o A5 reprovaram.
- [1032](1032-ciclo-de-revisao-kenneth-acoustic.md): 63 de 64 entregues certos, mas o nut
  estava quase sempre visível.

**Nota**: o canal está com `rollout: fora` para a **tablatura** (`configs/canais.yaml`; a tab é
texto ASCII). Isso não vale para o braço: aqui só se mede o violão do vídeo.

## Lote (sorteado depois deste texto; `m36/sorteio.json`)

- **8 vídeos do violaodecria**, sorteados com a semente 20261036.
  - Entram só os títulos de aula, ou seja, o nome do arquivo contém `violão`, `violao`, `tab`,
    `solo`, `aprenda` ou `fingerstyle`, sem diferença de caixa. São 986 dos 1 680 vídeos.
  - O canal também tem vlogs sem violão ("agora a neném vem…"), e o filtro só poupa o tempo
    do dono.
  - Ficam de fora os vídeos de todas as amostras anteriores, como na 1032.
- **4 quadros por vídeo**, de 0,15 a 0,85 da duração (0,15, 0,383, 0,617 e 0,85), num total de
  **32**. É um lote diagnóstico, menor que o dos ciclos (64), porque a pergunta é o tipo de
  erro e não a taxa fina.

## Detector (fixado agora, sem mudança)

1. **Pesos**: os da escolha da 1032 (`m32/escolha_pesos.json`, `L3_todos_s3` +
   `A4_100_todos_s1`). Não há escolha nova.
2. **Regra de revisão**: a da 1023, congelada.
3. **Sinal de nut suspeito v2** (1033, limiar 2 %): é o mesmo que entrou na 1032.
4. P2 e P3 ficam desligados.

## O que o dono faz

O protocolo da 1029:
- os sinalizados aparecem primeiro;
- capo com a tecla `k`;
- **nut fora**: o traste de referência, com o botão direito no traste e o número;
- 7 cordas com o botão.

## Medidas e critério

São as do ciclo (`maos_braco_ciclo medir --rodada 1036`), mais o recorte dos quadros com o nut
fora (o dono marcou o traste de referência).

| resultado | o que fazer |
| --- | --- |
| falsos que passam ≤ 5 % (no máx. 1 de 32) | o sinal v2 protege neste formato; as marcas de nut fora entram no retreino (A5 com dado de verdade) |
| falsos que passam > 5 % | parar e investigar por tipo de erro; o formato vertical não está protegido |
| sinalizados > 50 % | **esperado** neste canal: seguro, mas caro. Registrar quantos são de nut fora; isso mede o ganho possível de um estágio 2 que numere sem nut |

**Também reportado**:
- quantos quadros têm o nut fora (pela marca do dono) e quantos desses o v2 sinalizou;
- quantos o v2 sinalizou estando certos, ou seja, o custo do sinal.

## Riscos declarados antes

- **Vídeo vertical, braço curto na imagem.** O estágio 1 pode nem achar o braço, como no
  marigold da 1031 (11 de 16). Isso é "sem braço" e não conta como erro.
- **Tela dividida, com cifra ou tab escrita em cima ou embaixo.** É o caso que o v2 cobre
  (linhas de painel).
- **O nut pode estar fora sem que a corda encoste numa borda**, por exemplo com a mão na frente
  ou com capo. Esse é o caso que o v2 não pega, e é a fonte provável de um falso que passa.

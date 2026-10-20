# 1032 — Quarto ciclo de revisão: kenneth acoustic

**Data**: 2026-10-20 (janela autônoma; o pré-registro vem antes de qualquer previsão no lote).
**Estado**: regras a priori. **O canal foi escolhido pelo dono** ("pode ser kenneth acoustic").

**Antecedentes**:
- [1029](1029-ciclo-de-revisao-pablo-rome.md): 54 de 60 entregues certos, mas 4 falsos que
  passam (6,3 %), todos com o nut fora da imagem.
- [1031](1031-nut-fora-por-vizinhos-e-juncao.md): métodos para o nut fora (V, J e A5).

## Lote (já sorteado; `m32/sorteio.json`)

- **8 vídeos do kenneth acoustic**, sorteados com a semente 20261032, entre os 515 do canal.
  Ficam de fora os vídeos de todas as amostras anteriores (M3b, R, C, N, M11b, 1026, 1027 e 1029).
- **8 quadros por vídeo**, de 0,15 a 0,85 da duração, num total de 64.
- **Vídeos**:
  - redbone;
  - canon in d;
  - a thousand miles;
  - apt.;
  - merry go round of life;
  - smooth criminal;
  - bad romance;
  - interstellar.
- **Visto numa folha de 16 quadros** (`m32/amostra.jpg`), antes da previsão:
  - o canal mostra quase sempre o braço inteiro, com a cabeça do violão;
  - muitas vezes usa capotraste, e a casa do capo aparece escrita na tela ("Capo: Fret N").

## Detector (fixado agora)

1. **Pesos**: a escolha da 1029 na M11b, com o mesmo critério e o mesmo desempate.
   - Os candidatos do estágio 2 são `A4_100_todos_s{1,2,3}` e também os `A5_100_todos_s{1,2,3}`
     que existirem quando a escolha rodar. O A5 é o estágio 2 com os quadros de nut fora, da
     1031.
   - Se nenhum A5 existir, a escolha fica entre os A4, como na 1029.
2. **Regra de revisão**: a da 1023, congelada.
3. **Mais o sinal de nut suspeito**: a regra de borda da 1030, que pré-registrei na 1031 para o
   caso de nenhum método passar.
   - Um quadro com braço é sinalizado quando não tem nut, ou quando a ponta das cordas do lado
     do nut fica a até 2 % da borda menor.
   - Na 1030, esse sinal disparou em 30 % dos quadros bons. Ele custa revisão, mas não deixa
     passar falso.
4. **Métodos V e J**: entram só se passarem no critério da 1031.
   - Mesmo assim, eles exigem rodar inteiros os 8 vídeos, cerca de 3 600 quadros, e na GPU
     dividida desta janela isso leva mais de 6 h.
   - Se passarem e não houver tempo, ficam para a revisão seguinte, e isso fica registrado.
5. P2 e P3 ficam desligados, como na 1029.

## O que o dono faz

O protocolo da 1029:
- os sinalizados aparecem primeiro;
- capo com a tecla `k`;
- nut fora com o traste de referência (botão direito no traste e o número);
- 7 cordas com o botão.

## Medidas e critério

Os da 1026, da 1027 e da 1029 (`maos_braco_ciclo medir --rodada 1032`).

| resultado | o que fazer |
| --- | --- |
| falsos que passam ≤ 5 % e sinalizados ≤ 50 % | o ciclo segue; as marcas entram no próximo retreino |
| falsos que passam > 5 % | parar e investigar por tipo de erro |
| sinalizados > 50 % | seguro, mas caro: propor a melhora que mais reduz os sinalizados |

**Também reportado**: quantos quadros o sinal de nut suspeito mandou para revisão, e quantos
deles estavam certos. Essa é a medida do custo do sinal.

## Riscos declarados antes

- **O capotraste é comum neste canal.** O detector já confundiu capo com nut antes. A tecla `k`
  e a regra "casa contada do nut" valem.
- **O braço é longo na imagem e a cabeça aparece.** O nut quase sempre está visível, e por
  isso este lote quase não testa o nut fora.

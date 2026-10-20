# 1033 — Sinal de nut suspeito v2: borda do painel e limiar

**Data**: 2026-10-20 (janela autônoma). **Estado**: regras a priori, escritas antes de medir.
Esta rodada é **só de desenvolvimento**: ela usa os ciclos já revisados.

## Por quê

O sinal v1 (a regra de borda da 1030, 2 % da borda menor) pegaria 4 dos 6 falsos que passaram
na 1027 e na 1029 ([1032](1032-ciclo-de-revisao-kenneth-acoustic.md), verificação retroativa).
Olhando os 2 que escapam (`m31/escapam.jpg`):
- **1029:q46**: a tela é dividida, com a partitura em cima e o violão embaixo. O braço sai pela
  **borda do painel**, uma linha reta horizontal que atravessa o quadro, e não pela borda do
  quadro.
- **1027:q56**: o "nut" fica a cerca de 30 px da borda (2,4 % de 1280), logo depois do capo.
  O limiar de 2 % (14 px) não pega.

## Regra v2

- **Bordas** = as 4 bordas do quadro + as **linhas de painel**.
  - Uma linha de painel é uma linha (ou coluna) em que o gradiente vertical (ou horizontal) é
    forte em pelo menos 80 % da largura (ou da altura).
  - "Forte" quer dizer diferença de intensidade ≥ 25 entre os pixels vizinhos, na imagem em
    cinza suavizada.
  - Ficam de fora as linhas a menos de 2 % da borda do quadro, que já é borda.
- **Nut suspeito** = sem nut, ou a ponta das cordas do lado do nut (corda1 ou corda6) a até
  f × (borda menor) de qualquer borda.
- **f** é escolhido entre 2, 3, 4 e 5 %: o **menor f que pega ≥ 5 dos 6 falsos**. Se nenhum
  pegar 5, vale o que pega mais (e, no empate, o menor f).

## Medida e critério

**Dados**:
- os quadros dos ciclos 1026, 1027 e 1029, com a previsão do ciclo (`previsto.json`) e as
  marcas do dono (`medida.json`);
- mais o lote da 1032, só para contar quantos quadros o sinal dispara (sem rótulo).

**Contagens**:
- dos 6 falsos que passaram, quantos o sinal pega;
- dos quadros certos e não sinalizados, quantos ele manda para revisão a mais;
- quantos ele dispara na 1032.

| resultado | o que fazer |
| --- | --- |
| pega ≥ 5 dos 6 e manda ≤ 10 % dos certos a mais (somando os três ciclos) | o v2 substitui o v1 na 1032, com o lote preenchido de novo antes de o dono abrir (como na emenda 1 da 1029) |
| senão | a 1032 fica com o v1 |

## Riscos declarados antes

- **6 falsos, todos já vistos**: é direção, não prova. A medida de verdade é a 1032.
- **Tablatura, legenda e logotipo também fazem linhas retas.** O sinal só olha a linha perto da
  ponta das cordas, mas pode disparar quando o violão encosta numa delas.

## Resultado (2026-10-20; `m31/medida_1033.json`) — **passa com f = 2 %**

Nos 3 ciclos revisados há **6 falsos que passaram** e **150 certos não sinalizados**.

| f | falsos pegos | certos a mais | disparos na 1032 (64) |
| --- | --- | --- | --- |
| 2 % | **5** (1027:q51; 1029:q19, q20, q24 e **q46**) | **10 (6,7 %)** | 0 |
| 3 % | 5 | 12 | 0 |
| 4 % | 6 (mais o 1027:q56) | 14 | 0 |
| 5 % | 6 | 16 | 0 |

- Pela regra, vale o menor f que pega ≥ 5, que é **2 %**. Ele manda 6,7 % dos certos a mais,
  dentro do limite de 10 %. **O v2 passa e substitui o v1 na 1032.**
- **A linha de painel é que pega o 1029:q46**. Com só as bordas do quadro (v1), ele passava.
- O que ainda escapa é o 1027:q56: o nut no 1º traste depois do capo, a 2,4 % da borda.
- **Na 1032, o v2 dispara 0 vezes**, igual ao v1. O lote foi preenchido de novo com o v2 antes
  de o dono abrir (64 com braço, 1 sinalizado, o mesmo q43), e nada mudou.
- **Com o v2, os ciclos passados teriam**:
  - 1027: 1 falso que passa (era 2);
  - 1029: 0 falsos que passam (eram 4).
  - Os dois ficam abaixo de 5 %. Os 6 falsos já tinham sido vistos, então isso é direção, não
    prova.

**Código**: `tab/maos_braco_sinal_nut.py`, ligado no `prever` por `RODADAS_SINAL_NUT_V2`.

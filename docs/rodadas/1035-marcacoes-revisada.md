# 1035 — Conferência pelas marcações, revisada (depois da reprovação da 1034)

**Data**: 2026-10-20 (janela autônoma). **Estado**: regras a priori, escritas antes de medir.

## O que muda em relação à 1034

O diagnóstico da [1034](1034-conferencia-pelas-marcacoes.md) mostrou que as marcações eram
detectadas, mas o tampo claro e a mão subiam a mediana e apagavam tudo. Duas mudanças, e só
elas:
1. **Mancha compacta**: um espaço só conta se a mancha clara em volta do máximo for pequena:
   - a mancha é o componente conexo, no resíduo ≥ metade do máximo, que contém o máximo;
   - altura ≤ 18 px, ou seja, ≤ 35 % da escala;
   - largura ≤ 60 % do espaço.
   - O tampo e a mão são regiões largas e saem.
2. **Limiar pelo quartil inferior**: pontuação ≥ max(20, F × Q25) das pontuações compactas do
   quadro.

O padrão, os deslocamentos e a decisão (≥ 3 marcações, com a 12 entre elas; empate não decide)
são os da 1034.

## Desenvolvimento (sem rótulo) e teste (com rótulo)

- **F é escolhido entre 2, 3 e 4** só nos **quadros densos** dos vídeos de aço do guitarous
  (v09 a v16 da 1030, menos o v15, que tem casos), nos quadros com nut visível com confiança.
  - Nesses quadros, a numeração é tomada como certa (k = 0).
  - Vale o F com **mais decisões em k = 0**, desde que os disparos (k ≠ 0) fiquem em ≤ 2 % das
    decisões. Sem nenhum F assim, a rodada para aqui.
- **Teste**: os ciclos 1026, 1027 e 1029, com o critério da 1034.
  - Precisa pegar o 1027:q56 e disparar em ≤ 3 % dos 150 certos.
  - Se passar, vai ao ciclo seguinte à 1032, junto com o v2.

## Resultado (2026-10-20; `m31/medida_1035.json`) — **reprova no teste**

**Desenvolvimento sem rótulo** (1 095 quadros densos de aço com nut visível):

| F | decisões | k = 0 | disparos |
| --- | --- | --- | --- |
| 2 | 72 | 72 | 0 |
| 3 | 380 | 380 | 0 |
| **4** | **510** | **510** | **0** |

- F = 4 é o escolhido. A regra revisada é **segura**: decide em 47 % dos quadros e nunca dispara
  em falso.

**Teste nos ciclos**:
- Nos 150 certos, decide em 16 e dispara em 0.
- Nos 6 falsos, não decide em nenhum, **e o 1027:q56 também fica sem decisão**.
- Pelo critério, não vai a ciclo.

**Leitura**:
- Como sinal, a regra não erra, mas decide pouco onde importa.
- O padrão exige que todas as casas marcadas caiam no padrão. No 1027:q56, alguma casa marcada
  a mais (por exemplo, perto da junção) basta para nenhum k caber.
- Não ajusto de novo nos mesmos 6 falsos: isso seria ajustar no teste.
- **Daqui em diante**, ela pode ser medida nas marcas que o dono fizer na 1032 (kenneth, aço).

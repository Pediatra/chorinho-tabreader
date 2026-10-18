# 1027 — Segundo ciclo de revisão: guitarous (um canal que o detector não treinou)

**Data**: 2026-10-18. **Estado**: regras a priori. Este documento ganha commit antes de rodar o
detector. **O dono escolheu o canal**: "pode ser o guitarous".

## Mudança de ordem em relação à 1026 (decidida antes de rodar)

O pré-registro da [1026](1026-ciclo-de-revisao-sky-guitar.md) dizia que a próxima rodada
retreinaria os dois estágios e depois mediria num lote novo. **A ordem fica invertida: primeiro
o ciclo no guitarous, com o detector da 1026 sem mudança, e o retreino na 1028.**

Por quê:
- O ganho de dado da 1026 é pequeno e redundante: são 63 quadros de um canal que já está no
  treino.
- Um ciclo num canal **fora do treino** responde agora a pergunta que importa para o produto:
  quanto o ciclo rende num canal novo.
- Esse ciclo também produz marcas de um canal novo, que valem mais para o retreino.
- O retreino da 1028 usa as marcas das duas rodadas.

## Pergunta

Num canal que nenhum estágio treinou, quanto o ciclo entrega certo sem revisão, quanto escapa e
quanto trabalho sobra para o dono?

## Lote

- **8 vídeos do guitarous**, sorteados com a semente 20261027.
- Ficam de fora os vídeos já usados em qualquer amostra:
  - M3b, R e C;
  - o teste N da 1025: os 6 quadros do guitarous;
  - a 1026.
- **8 quadros por vídeo**, igualmente espaçados entre 0,15 e 0,85 da duração, num total de 64.
- Vídeo de 7 cordas sai do lote: o dono escreve `7 cordas` na observação.

## Detector e protocolo

O mesmo da 1026, sem nenhuma mudança: `L2_todos_s1` com a decodificação conjunta,
`A3_100_todos_s1` (v2) com refino, e a regra da 1023.

**O que o dono faz**: a mesma ferramenta, já preenchida e com os sinalizados primeiro.
- O dono corrige os sinalizados e confere os não sinalizados.
- Os trastes previstos fora da imagem são cortados antes de abrir. A previsão completa fica em
  `previsto.json`.
- **"Braço sim"**: o dono pode apertar `x` em cada quadro, ou dizer no fim que conferiu tudo.
  No segundo caso, o "sim" é gravado em lote a pedido dele e registrado na observação, como na
  1026.

**Medidas e critério**: os da 1026.

| resultado | o que fazer |
| --- | --- |
| falsos que passam ≤ 5 % e sinalizados ≤ 50 % | o ciclo funciona num canal novo: a 1028 retreina os dois estágios com as marcas da 1026 e da 1027 e roda o próximo ciclo |
| falsos que passam > 5 % | parar o ciclo e investigar por tipo de erro |
| sinalizados > 50 % | seguro, mas caro: registrar e propor a melhora que mais reduz os sinalizados |

## Riscos declarados antes

- **O guitarous já foi visto como teste** na 1025, em 6 quadros e 18 medidas, com 12 certos e
  nenhum falso que passou. Nenhum estágio treinou com ele, então o canal continua fora do
  treino.
- **A auditoria parte de marcas já preenchidas**, e o dono pode aceitar uma marca quase certa.
- **64 quadros de um canal** dão a direção, não uma taxa firme.

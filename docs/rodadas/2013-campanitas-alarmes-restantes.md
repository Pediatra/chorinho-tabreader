# 2013 — Áudio: os 17 alarmes que sobram no campanitas (v2.1)

Data: 2026-10-13. Só medição. Saídas: `data/saida/audio/a4/campanitas_alarmes/` (tabelas
CSV, `gemeas.csv`, `causas.csv`, recortes em `quadros/`, figuras de janela em `figuras/`).

## Pergunta

Depois do rasgueado (rodada 2012), o campanitas ainda tem 17 exibições com alarme de leitura.
Em todas, 1 a 3 colunas casam com cos 0,70–0,94, e quase todo o resto da página fica
`fora_do_trecho`. Qual é a causa?

## Medição

- **Páginas gêmeas.** A música repete seções. Das 17 telas com alarme, **14 têm uma
  gêmea** (sequência corda/casa com semelhança ≥ 0,82) que foi **aceita**, quase sempre
  com 20 ou mais colunas casadas. A tela 38 e a tela 20 têm sequências **idênticas** no
  produto: a 38 casa 1 coluna e a 20 casa 5. Mesma leitura com resultado diferente: nesses
  pares, a leitura sozinha não explica a recusa.
- **Janela.** Nas 4 telas com figura, a música é densa e tocada dentro de [t0, t1]. Nenhuma é
  "página mostrada sem tocar". Picos de fluxo por coluna: mediana 1,65 nas telas com alarme,
  contra ~1,0 nas aceitas, ou seja, mais ataques no som do que colunas no produto.
- **Recortes** (8 telas olhadas):
  - tela 3: leitura certa, rasgueado com **setas sem X**; só 2 pilhas de X em 21
    colunas, abaixo dos 20 % que marcam rasgueado;
  - telas 7 e 16: rótulos "12" lidos como casa, e blocos de setas sem coluna no produto;
  - tela 5: o painel pegou a **partitura**, não a TAB;
  - telas 13, 38 e 47: **nota faltando** (c1/k0; coluna 3/0, 4/2, 6/3; um "10" lido como
    `tecnica`). A gêmea 20 tem a mesma falta da 38;
  - tela 17: leitura quase certa (início de slide como `tecnica`). Sem causa clara.

## Causa por tela

| causa | telas | X de 17 |
| --- | --- | --- |
| método: setas de rasgueado sem X | 3, 7, 16 | 3 |
| leitura (nota faltando ou errada) | 13, 38, 47 | 3 |
| outra: painel na partitura (5); alinhador casa 1 coluna com a música tocada (17) | 5, 17 | 2 |
| não olhadas; todas com gêmea aceita | 4, 8, 12, 15, 39, 40, 43, 48, 49 | 9 |

## Leitura

Não há causa dominante. O sinal mais forte é o das **gêmeas**: com a mesma página no
produto, o alinhador casa 20 colunas numa passagem e 1–2 na outra. Isso aponta para o
**alinhador**, porque ele escolhe um trecho mínimo quando o som tem mais ataques que colunas
(setas de rasgueado, ressonância). Não foi provado: o DP não foi instrumentado.

## Próximos passos (não feitos)

1. Instrumentar o DP num par de gêmeas (38 × 20, 4 × 21) e ver qual termo derruba o trecho
   longo: pular pico, andamento ou cosseno.
2. Contar as setas de rasgueado, não só os X, para marcar `rasgueado` (tela 3).
3. Leitura: pedidos 8b da decisão 2004.

## Limites

8 de 17 telas olhadas; a tela 47 só pela metade; nada ouvido.

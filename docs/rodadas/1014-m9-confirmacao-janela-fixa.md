# 1014 — M9: confirmação fora da amostra da janela da mão esquerda com grade fixa

**Data**: 2026-10-16. **Estado**: regras a priori. Este documento ganha commit **antes** de
qualquer medida da janela nos vídeos novos. A medida só roda depois de duas coisas:

- o dono marcar os quadros do braço q32–q36;
- o dono decidir o CA3 dos vídeos pequenos (seção "Pendente").

## Pergunta

A janela da mão esquerda com a grade fixa do quadro do dono, sem o teste de câmera, tirou
285 → 242 erros nos 4 vídeos de trabalho (+1,9 pp nas ambíguas, saldo 43). Mas reprovou no CA3
por 3 a 4 notas num vídeo, e o vídeo que perde muda com o instante da mão (glimpse no `t_ini`,
lacrimosa no som; rodadas 1131 e 4.2 do plano). O ganho se repete em vídeos que **nunca** foram
usados para escolher nada?

## Método (fixo, sem nenhum ajuste)

- Exatamente o diagnóstico `data/saida/maos/m8/d2_fixo.py`:
  - janela do D2 do M8 (`janela_da_mao_esquerda`) com deslocamento (0, 0), sem o teste de câmera;
  - pesos a priori do M8: α = 1, β = 3, γ = 5, δ = 0,5;
  - ponta válida pelo critério do M8;
  - pontas no `t_ini` (a 1131 mostrou que o som não melhora).
- Referência: D1 do M8 nos mesmos vídeos.
- Altura e gabarito tirados da tablatura do produto, como no M8.

## Vídeos (nenhum usado no M8 nem nas ondas para escolher parâmetro)

| vídeo | produto | quadro do braço | pontas | notas | ambíguas | erros do D1 |
| --- | --- | --- | --- | --- | --- | --- |
| take five | `m3d/sky_1.json` | q32 (110,344 s) | `m9/pontas_sky_1.json` | 219 | 184 | 16 |
| spanish tango | `m3d/sky_2.json` | q33 (122,723 s) | `m9/pontas_sky_2.json` | 232 | 217 | 14 |
| für elise | `m3d/sky_3.json` | q34 (307,274 s) | `m9/pontas_sky_3.json` | 158 | 150 | 19 |
| ghostbusters | `m3d/sky_5.json` | q35 (122,656 s) | `m9/pontas_sky_5.json` | 115 | 99 | 1 |
| annie laurie | `m3d/sky_6.json` | q36 (100,167 s) | `m9/pontas_sky_6.json` | 140 | 138 | 1 |
| no surprises | `m3d/sky_7.json` | q22 (já marcado) | `m3d/pontas_q22.json` | 469 | 443 | 102 |
| **total** | | | | **1.333** | **1.231** | **153** |

- Os erros do D1 foram contados antes de existir qualquer janela nesses vídeos
  (`data/saida/maos/m9/contar.py`).
- Os quadros q32–q36 foram escolhidos numa folha de 6 candidatas por vídeo
  (`m9/quadros_braco/candidatas.jpg`), em instantes de nota presa, sem sobreposição gráfica e
  com a mão pouco à frente do braço.
- As pontas vêm de `tab.maos_pontas_notas` em CPU (`m9/rodar_pontas.sh`).
- A A3 usou esses produtos como treino do custo aprendido. Isso não toca este método: ele não
  tem nenhum parâmetro aprendido.

## Critérios (os da seção 5.3 do plano)

- **CA1**: reproduzir D0 e D1 do M8 e o diagnóstico de 242 erros nos 4 vídeos de trabalho.
- **CA2**: somando os 6 vídeos novos, nas ambíguas, ganho ≥ +1,0 pp **e** consertadas −
  quebradas ≥ 20.
- **CA3**: ver "Pendente".
- **CA5**: execução determinística (duas execuções idênticas).
- **CA6**: 10 casos olhados (5 consertados, 5 quebrados), com recorte.
- **CA7**: gate verde.
- O CA4 não se aplica, porque não há nada ajustado.

**Poder do teste, declarado antes.**

- Nos 4 vídeos de trabalho, a janela consertou 15 % dos erros do D1 (43 de 285).
- Aplicado aos 153 erros do D1 dos vídeos novos, isso dá cerca de 23 notas de saldo. Fica perto
  do mínimo de 20.
- Ou seja: o teste pode reprovar com o efeito sendo real. Ele não foi desenhado para passar
  com folga.

## Pendente: CA3 nos vídeos pequenos (decisão do dono antes da medida)

O CA3 foi escrito para 4 vídeos de 400–750 notas: ganho em ≥ 3 de 4 vídeos, nenhum perdendo
mais de 0,5 pp. Nos vídeos novos ele fica impossível de cumprir:

- ghostbusters e annie laurie têm **1 erro** do D1 cada;
- nesses dois vídeos, "ganhar" exige consertar exatamente essa nota, e quebrar 1 nota já passa
  de 0,5 pp.

Opções, a decidir antes de rodar:

- **(a) Literal.** Ganho em ≥ 5 de 6 vídeos (a proporção de 3 de 4), nenhum pior que 0,5 pp. É
  quase certo reprovar por causa dos dois vídeos com 1 erro, com qualquer efeito.
- **(b) Recomendada.** Mantém a forma do CA3 nos vídeos com ≥ 10 erros do D1 (take five,
  spanish tango, für elise, no surprises): ganho em ≥ 3 de 4, nenhum pior que 0,5 pp. Nos vídeos
  com < 10 erros (ghostbusters, annie laurie), exige só não perder: saldo ≥ −1 nota em cada um.

## Relatório além do aceite

- Os 10 vídeos juntos (4 de trabalho + 6 novos).
- A decomposição dos erros (janela errada, janela certa, sem janela) e a cobertura por vídeo.
- O no surprises tem uma casa 21 (leitura errada, descartada como fora do domínio) e um quadro
  do braço com ajuste instável na rodada 1008. Relate esse vídeo também à parte.

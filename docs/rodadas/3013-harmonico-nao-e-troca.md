# 3013 — Harmônico não é troca

**Data:** 2026-10-15 · **Trilha:** partitura (P3) · **Código:** `tab/partitura_pareamento.py`
(`_desmentida`, usada em `completar_com_homr`), `tests/test_partitura_pareamento.py`

**Imagem conferida:** `data/saida/partitura/diag/r11_zoom.png` (recorte R11, x 1350–1600,
ampliado 3x).

## Pergunta

A rodada 3012 trocou, no R11 compasso 6, o G#5 do Audiveris pelo A3 do homr. O faltando
subiu de 14 para 15. A troca estava certa?

## O que a imagem mostra

É um harmônico artificial, marcado "A.H." embaixo.

- A pauta desenha a nota presa: G#5, cabeça mínima pontuada logo acima da pauta.
- Quatro linhas suplementares acima, um losango. É o som do harmônico, uma oitava acima.
- Embaixo, o A3 do baixo.

A tab escreve corda 1, casa 16 (MIDI escrito 92 = G#6). Esse é o som do harmônico.
Também escreve corda 5, casa 0 (A3).

Ou seja: o Audiveris leu certo. A tab e a pauta diferem por uma oitava, não por erro de
leitura.

## Regra

- Uma nota do Audiveris só é trocada se nem a altura nem a classe de altura
  (`midi % 12`) estão na coluna da tab.
- Nota igual à da tab em outra oitava (harmônico, 8va) fica.

## Resultado (R01–R12, 546 notas da tab)

| | certas | altura errada | faltando | inventada | notas erradas (altura errada + inventada) | trocas |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| troca pela tab (3012) | 526 | 5 | 15 | 3 | 8 | 6 |
| **+ sem troca na oitava (3013)** | **526 (96,3 %)** | 6 | 14 | 3 | **9** | 5 |

## O que os números dizem

- As 5 trocas que ficam são os bemóis inventados do R06 (compassos 7 e 11).
- A nota errada a mais (8 → 9) é o G#5 do harmônico. A conta contra a tab a chama de
  altura errada, porque a tab escreve o som do harmônico. Na imagem, a leitura está certa.
- Harmônico precisa virar notação. O dono já tinha pedido isso no R19 (rodada 3004).
  Quando virar, a conta contra a tab pode comparar o som do harmônico.
- Pareamento sem mudança: 336 de 337 pares no mesmo x.
- Gate: 1031 testes passam, ruff limpo.

## Limites

- **Erro de oitava real:** a regra também deixa passar um erro de oitava de verdade do
  Audiveris (mesma classe, oitava errada). Nos 12 recortes não apareceu nenhum além do
  harmônico.
- **Amostra:** 3 vídeos e 12 recortes.

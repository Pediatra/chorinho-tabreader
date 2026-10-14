# 3007 — Armadura herdada de outro recorte do mesmo vídeo

**Data:** 2026-10-14 · **Trilha:** partitura · **Código:** `tab/partitura_omr.py`
(`herdar_armadura`), `tests/test_partitura_omr.py` · **Script:**
`data/saida/partitura/diag/medir_armadura.py`

## Pergunta

R06 e R07 (south american music) começam no meio do sistema, sem clave nem armadura na tela, e
o Audiveris lê fá natural onde a música tem fá#. O R05, do mesmo vídeo, mostra 1 sustenido.
Aplicar essa armadura à leitura corrige as alturas?

## Regra

`herdar_armadura(musicxml, fifths)` grava a armadura e soma a alteração em cada nota alterada
pela armadura, desde que a nota:

- não tenha acidente próprio;
- não seja precedida, no mesmo compasso, por uma nota de mesmo degrau e oitava com acidente
  explícito. Nesse caso a nota herda o acidente.

Se a leitura já tem armadura, a função não muda nada.

## Resultado (tab, régua da rodada 3003)

| recorte | certas antes | certas depois | altura errada antes → depois |
| --- | ---: | ---: | --- |
| R05 (já tem armadura) | 80/85 | 80/85 | 0 → 0 (texto idêntico) |
| R06 | 79/88 | 81/88 | 7 → 5 |
| R07 | 88/96 | 89/96 | 1 → 0 |

## Limites

- **Origem da armadura:** nesta rodada ela veio à mão, do R05. Em produção, ela tem de vir do
  quadro do mesmo vídeo em que a clave aparece. Esse código ainda não existe.
- **Erros que sobram no R06:** as 5 alturas erradas restantes não foram investigadas.

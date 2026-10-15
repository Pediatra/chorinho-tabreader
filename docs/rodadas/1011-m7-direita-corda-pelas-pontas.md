# 1011 — M7: corda atacada pelas pontas da mão direita (sem sinal)

**Data**: 2026-10-15. Objetivo: [decisão 1005](../decisoes/1005-mao-direita-serve-a-corda.md)
(a direita serve para dizer a corda atacada). Gabarito: a tablatura da tela (produto), sem
rótulo do dono. 4 vídeos do sky guitar (retrato brasileiro, noturno nº 20, lacrimosa,
glimpse of us), 30 ataques por vídeo, semente 20261015.

Código: `tab/maos_direita_cordas.py` (puro) e `tab/maos_direita_trajetorias.py` (detector).
Saídas: `data/saida/maos/m7/`.

## Fase A — painel, cordas, trajetórias

- Painel da direita (câmera da boca): x 0–655, y 522–1080, igual nos 4 vídeos.
- Cordas: filtro de linha girado + picos de projeção, casados entre quadros; 6 cordas em 5/5
  quadros nos 4 vídeos; 6 em cima, 1 embaixo (espessura). Precisão medida por "crista"
  (contraste na reta contra ±meio espaçamento) e refino local: cordas 1–3 do noturno com
  crista 6–24 e vários refinos no limite da busca; 5–6 do noturno e do glimpse ainda acima das
  cordas no cavalete. **Cordas aproximadas, não confiáveis em todos os vídeos.**
- Mão direita detectada no painel em 120/120 ataques, nos 5 quadros (−0,20 … +0,07 s).

## Fase B — sinal × ruído e preditor

Deslocamento das pontas (−0,13 → +0,07 s), ataque × 30 controles sem nota a ±0,30 s.
AUC do deslocamento máximo: retrato 0,49, noturno 0,36, lacrimosa 0,66, glimpse 0,70.
**Em 2 de 4 vídeos o movimento nos ataques não se separa do movimento fora deles.**

Preditor (ponta que mais se moveu → reta mais próxima) contra a base (corda mais frequente):

| vídeo | preditor | base |
| --- | --- | --- |
| retrato | 15/30 | 6/30 |
| noturno | 7/30 | 9/30 |
| lacrimosa | 9/30 | 8/30 |
| glimpse | 16/30 | 17/30 |
| total | 47/120 | 40/120 |

## Conclusão / não repetir

Pontas do detector em 5 quadros esparsos **não** dizem a corda atacada. Causas candidatas,
não separadas: tremor do detector da ordem do movimento do dedo; pontas ocultas pelas
cordas; e o `t_ini` da tablatura pode não coincidir com o ataque real (marcador da tela, não
áudio) — com 5 quadros em −0,20…+0,07 s, um atraso de ~0,1–0,3 s esconde o gesto. Antes de
outro preditor: medir o **alinhamento temporal** (energia de movimento quadro a quadro no
painel × tempos das notas) para saber se o gesto aparece e com que atraso.

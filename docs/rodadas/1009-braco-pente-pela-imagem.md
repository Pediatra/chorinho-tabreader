# Rodada 1009: correção do braço pela imagem, em pente (reprovada)

Data: 2026-10-13. Trilha das mãos, M3c. Continua a [1008](1008-braco-pela-musica-fora-do-mvp.md).

## Ideia

A correção da 1007 procurava cada corda e cada traste numa janela pequena em volta da
posição da música; com erro maior que a janela, pulava para a linha vizinha. Aqui o pente
inteiro é ajustado por busca global, sobre a mediana de 15 quadros da cena (mãos somem):

- **cordas**: 6 linhas igualmente espaçadas, v'_j = a + b·(j−1)/5, em 3 faixas de casas
  (1–4, 5–8, 9–12), com a e b lineares em u;
- **trastes**: nut e trastes 1–12 pela regra de 12 notas sob projetiva 1D,
  u'_n = (α·s_n + β)/(γ·s_n + 1);
- nova H ajustada aos 78 cruzamentos (`ajustar_pontos`).

Constantes fixadas antes da medida (`tab/maos_pente_braco.py`), sem mudança depois.
Desenvolvimento: q02 e q16. Teste: q21 e q23. Robustez: q22.

## Resultado (contra o dono)

c1/c6 = fração do vão 1–6; nut = fração da casa 1; trastes = dentro de 1/4 de casa.

| quadro | método | c1 | c6 | nut | trastes |
| --- | --- | --- | --- | --- | --- |
| q02 (dev) | música | 0,112 | 0,069 | 0,036 | 14/14 |
| | pente | 0,048 | 0,063 | 0,093 | 14/14 |
| | só cordas | 0,044 | 0,059 | 0,027 | 14/14 |
| | só trastes | 0,112 | 0,073 | 0,102 | 14/14 |
| q16 (dev) | música | 0,346 | 0,194 | 0,490 | 10/15 |
| | pente | 0,647 | 0,479 | 0,017 | 2/15 |
| | só cordas | 0,641 | 0,489 | 0,490 | 10/15 |
| | só trastes | 0,373 | 0,195 | 0,011 | 2/15 |
| q21 (teste) | música | 0,142 | 0,063 | 0,295 | 14/14 |
| | pente | 0,415 | 0,299 | 0,122 | 14/14 |
| | só cordas | 0,393 | 0,312 | 0,296 | 14/14 |
| | só trastes | 0,161 | 0,047 | 0,121 | 14/14 |
| q23 (teste) | música | 0,061 | 0,151 | 0,050 | 9/14 |
| | pente | 0,069 | 0,064 | 0,663 | 0/14 |
| | só cordas | 0,093 | 0,061 | 0,038 | 9/14 |
| | só trastes | 0,054 | 0,101 | 0,672 | 0/14 |
| q22 | música | 0,155 | 0,248 | 0,199 | 4/14 |
| | pente | 0,237 | 0,147 | 0,240 | 5/14 |

**Reprovado.** Cada metade acerta num quadro e erra em outro: as cordas pelo pente
melhoram q02 e q23 e pioram muito q16 e q21; os trastes pelo pente acertam o nut em q16 e
q21 e destroem os trastes em q16 e q23. No q16 as faixas de cordas dão (a, b)
inconsistentes entre si (o pente pegou a borda do braço) e os trastes com γ = −0,31
esticam a grade até o painel da mão direita, que também tem cordas e trastes.

Limite medido: a família (Möbius em u, cordas lineares em u) não é homografia quando
γ ≠ 0; a H ajustada aos cruzamentos só a aproxima (4 px no sintético com γ = 0,1).

## Lições

- Perfil somado de linhas claras não separa cordas da borda do braço nem do outro painel
  no layout do sky guitar; busca global com faixa larga troca o erro pequeno da música por
  saltos grandes.
- Sem critério de "não achou" (consistência entre faixas, score contra o da música), a
  correção pela imagem não pode substituir a H da música.

## Artefatos

- Código (opcional, padrão desligado): `tab/maos_pente_braco.py`,
  `tab/maos_braco_fora.py --pente/--pente-componentes/--mediana`,
  `tab/maos_medicoes_braco.py` (mediana por cena, `--gerar-mediana-cena`).
- Saídas: `data/saida/maos/m3d/<quadro>/{mediana.png, conferencia_pente.png, medicao.json,
  so_cordas/, so_trastes/}`.

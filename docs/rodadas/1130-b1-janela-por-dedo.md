# 1130 — B1: janela de casas pelas células das pontas (janela por dedo)

**Data**: 2026-10-16. Frente B1 da onda 1 ([`maos-frentes.md`](../pesquisa/maos-frentes.md), seção 7).
Código: `tab/maos_esq_janela.py` (`python -m tab.maos_esq_janela --casos 10`). Testes:
`tests/test_maos_esq_janela.py` (15, sem dados). Saída: `data/saida/maos/frentes/fb_esquerda/`
(`b1_janela.json`, `casos_b1/`).

## Pergunta

A janela da mão inteira do M8 (`floor(min) - 1` a `ceil(max) + 1`, pontas 8, 12, 16, 20) tem 4 a
6 casas. Uma janela feita de células, uma por ponta, com folga de 10 % ou 20 % do vão, contém a
casa verdadeira quase tanto e deixa uma corda candidata com mais frequência?

## Definições (declaradas antes da medida)

- **Casa contínua**: inversa do modelo projetivo do quadro do gabarito (`casa_do_ponto`). A casa
  `n` ocupa `(n - 1, n]`; uma ponta em `c` pisa `ceil(c)`.
- **Célula com folga `f`** (em vãos de traste): ponta em `c` cabe nas casas `ceil(c - f)` a
  `floor(c + 1 + f)`. Janela = envelope das células das pontas 8, 12, 16 e 20 com score >= 0,3.
  Variantes: (ii) `f = 0,10`; (iii) `f = 0,20`.
- **Cenário principal**: grade fixa do quadro do gabarito do vídeo (q02, q16, q21, q23), sem
  deslocamento de câmera, em todos os ataques. Só o eixo ao longo do braço; a faixa
  perpendicular não é checada (o desvio chega a 2,4 cordas). q24 a q31 não foram usados.
- **Subconjunto com câmera**: ataques com NCC >= 0,8 (limiar do M8), com o deslocamento da câmera
  e a seleção de mão do M8.
- **Aceite congelado**: contém >= 95 % e 1 candidata em >= 70 % das ambíguas presas cobertas.
- **"1 candidata"**: pares `(corda, casa)` com casa > 0 dentro da janela. A versão estrita soma as
  cordas soltas, que janela nenhuma exclui (custam zero com a mão em qualquer lugar).
- **Pontas só existem no `t_ini`**; a janela é medida nesse instante. O som vem 165 a 275 ms
  depois. Não há calibração pela música (`tab/maos_calibrar_por_notas.py` não é importado).
- Denominadores: 1.470 ataques com nota presa; 1.724 notas presas; 1.669 ambíguas presas
  (1.648 em ataques cobertos). Cobertura: 1.449 / 1.470.

## Resultado (cenário principal, grade fixa, 4 vídeos)

| janela | contém (presas cobertas) | largura média (casas) | 1 candidata (ambíguas cobertas) | 1 candidata e certa | 1 candidata, estrita | aceite |
| --- | --- | --- | --- | --- | --- | --- |
| (i) M8 | 1.681/1.724 = 97,5 % | 5,08 | 1.498/1.648 = 90,9 % | 89,8 % | 84,0 % | passa |
| (ii) célula 10 % | 1.592/1.724 = 92,3 % | 2,32 | 1.547/1.648 = 93,9 % | 91,9 % | 86,4 % | **não** (contém < 95 %) |
| (iii) célula 20 % | 1.623/1.724 = 94,1 % | 2,57 | 1.576/1.648 = 95,6 % | 93,5 % | 88,2 % | **não** (contém < 95 %) |

Por vídeo, contém (presas) e 1 candidata (ambíguas cobertas):

| vídeo | (i) M8 | (ii) 10 % | (iii) 20 % |
| --- | --- | --- | --- |
| retrato (cobertura 469/473) | 517/522 = 99,0 %; 96,5 % | 508/522 = 97,3 %; 97,5 % | 512/522 = 98,1 %; 98,0 % |
| noturno (392/394) | 442/450 = 98,2 %; 86,1 % | **399/450 = 88,7 %**; 90,4 % | 413/450 = 91,8 %; 93,0 % |
| lacrimosa (251/256) | 316/321 = 98,4 %; 91,2 % | 295/321 = 91,9 %; 93,5 % | 306/321 = 95,3 %; 97,4 % |
| glimpse (337/347) | 406/431 = 94,2 %; 89,2 % | 390/431 = 90,5 %; 93,6 % | 392/431 = 91,0 %; 94,3 % |

**Subconjunto com câmera** (96 ataques, 101 presas, 94 ambíguas): (i) 99/101 = 98,0 % contém,
largura 4,80, 1 candidata 96,8 %; (ii) 97/101 = 96,0 %, largura 1,96, 1 candidata 95,7 %; (iii)
97/101 = 96,0 %, largura 2,19, 1 candidata 95,7 %. A janela (i) reproduz a do M8 em 96 de 96
ataques (conferência no próprio JSON). O subconjunto é pequeno demais para decidir qualquer coisa.

**Aceite.** Só (i) passa, com a grade fixa. (ii) e (iii) ficam abaixo de 95 % de contenção. Nenhuma
janela ficou abaixo de 90 % no total, então a parada do aceite não disparou no total. Mas o
noturno, sozinho, ficou em 88,7 % na variante (ii), e a regra de parada manda olhar 10 casos.

## Olhada em 10 casos (noturno, variante ii)

Escolhidos por espalhamento no tempo entre as 132 ambíguas presas que a célula de 10 % deixa de
fora. Folhas com dois instantes: `t_ini` e `t_ini + 0,22 s` (perto do som), com o gabarito da
grade fixa e as pontas (`casos_b1/folha_0.png` a `folha_4.png`):

- **Falha da ponta, do lado do corpo, na borda do traste** (5): casos 0, 3, 4, 5 e 6. A ponta do
  indicador (8) fica de 0,04 a 0,4 casa do lado do corpo do traste que a nota pisa. Caso 0 é o
  limite (8,14 contra o corte de 8,10).
- **Sem dedo visível pisando a casa verdadeira** (5): casos 1, 2, 7, 8 e 9. Em 1, 7, 8 e 9, a mão
  fica a 2 ou mais casas da nota nos dois instantes; em 2, o dedo que pisa não é nenhuma das
  pontas 8, 12, 16 e 20. Não separo instante de falha de detecção só com esses dois quadros.
- Braço: nenhum caso mostra a grade fora do braço (a grade fixa do q16 acompanha os trastes).

Os números desta olhada são 10 casos, não a população. O viés da ponta é o padrão dominante:
a mediana do deslocamento da ponta mais próxima da casa verdadeira é **+0,22 casa**, com 71 de 78
desvios do lado do corpo (quartis 0,12 e 0,65).

## Diagnóstico (todas as 132 falhas de 10 %)

| categoria | n |
| --- | --- |
| ponta mais próxima do lado do corpo | 71 |
| ponta mais próxima do lado da pestana | 7 |
| nenhuma ponta a 1,5 casa da casa verdadeira | 54 |
| recuperada pela mão do ataque seguinte (0,1 a 0,4 s) | 1 |

A recuperação pelo ataque seguinte (só como diagnóstico, nunca como janela) quase não acontece.
Isso não confirma nem refuta o atraso do instante: os quadros de `t_ini + 0,22 s` mostram a mão
no mesmo lugar nos casos sem dedo visível.

## Decodificador (D2) e CA1–CA7

**Não rodado.** O protocolo manda rodar o D2 só se (ii) ou (iii) passarem no aceite do cenário
principal. Nenhuma passou. O CA1 foi conferido sem o D2: D0 reproduz 341 erros e D1 reproduz 285,
vídeo a vídeo (`ca1_reproducao_m8`). O CA5 (determinismo): duas execuções geram o mesmo sha256.

## Ponto em aberto para o dono

O aceite do subconjunto com câmera passa para (ii) e (iii) (96,0 % e 95,7 %), mas o protocolo lê
o aceite no cenário principal. Se a leitura for o subconjunto, a D2 com (ii) ou (iii) cobre só 96
ataques e no máximo 94 ambíguas: o efeito possível é pequeno. Não rodei por causa da regra.

A janela (i) do M8 com grade fixa passa no aceite (97,5 %, 1 candidata 90,9 %). Ela não foi
rodada no D2 porque o protocolo não manda; é a medida barata que `maos-frentes.md` (B3, passo 0)
pede, e pode ser rodada se o dono quiser.

## Pergunta sobre a corda das pontas

B1 não precisa da corda de cada ponta: a janela usa só a casa, sobre o eixo do braço. Por isso a
B3 **não entra na onda 2 por causa da B1**. A B3 corrige o desvio perpendicular; o viés medido aqui
é ao longo do braço (ponta do lado do corpo, ~0,2 casa). Esse viés não é coberto pela B3.

Pela regra da B2 (entra se a B1 falhar pela ponta), há indício de falha de ponta (71 de 132 do
lado do corpo, e 5 de 10 casos olhados). Esse indício justificaria a B2 na onda 3, mas não foi
testado.

## O que esta medida NÃO prova

- Não prova ganho na decodificação: o D2 não foi rodado com nenhuma janela nova.
- Não separa instante de falha de detecção nos 54 casos sem ponta perto.
- Usa 4 vídeos de um canal (`sky guitar`); as pontas são do `t_ini`; a casa é a do gabarito da
  tablatura.
- A "1 candidata" não é "candidata certa": a versão "1 candidata e certa" é a que conta, e ela fica
  em 89,8 % (i) a 93,5 % (iii).

## Não repetir

- Célula de 10 % ou 20 % de vão como janela de casa com as pontas do `t_ini`: falha por viés da
  ponta do lado do corpo. Antes de repetir, medir esse viés e a falha de borda.
- Contar cordas soltas como candidatas da janela: a janela nunca as exclui, e a contagem fica
  inútil (versão estrita ~84 a 88 %).
- Ler um aceite de subconjunto (96 ataques) como aceite do cenário principal.

## Arquivos

- Código: `tab/maos_esq_janela.py`; testes: `tests/test_maos_esq_janela.py`; rodada: este documento.
- Saída: `data/saida/maos/frentes/fb_esquerda/b1_janela.json`, `casos_b1/noturno_caso_*.png` e
  `folha_0.png` a `folha_4.png`.
- Há um `b1_run.log` de 15/10 nessa pasta, de uma tentativa anterior cujo módulo não está neste
  branch. Não foi usado nem apagado.

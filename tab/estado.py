"""O ESTADO do marcador ("qual nota está acesa") e o ONSET dela — uma regra, sem estilo.

Formulação acordada com o dono: **o marcador é um estado**, não um movimento. Em cada instante existe UMA
nota atual, e o **onset** dela é o **primeiro instante em que ela passa a ser a atual**. Isso não menciona
estilo nenhum.

A regra que implementa isso é uma **partição do eixo x pelas notas** (as fronteiras ficam no meio entre
notas consecutivas): a nota atual é a **cujo intervalo contém o x do marcador**:

- **patamares** (o marcador pula e para): ele **cai dentro** da célula da nota ✓;
- **varredura** (o marcador desliza): ele **entra** na célula ✓;
- **quebra de linha** (o x volta ao início): a célula é definida pelo x **lido no quadro**, não por um x
  absoluto — então o retorno não gera onset falso por si só, porque quem manda é a nota ✓.

O onset é o **primeiro instante de cada passagem** pela célula — e o módulo também conta quantas notas
**não** receberam nenhuma (o silêncio é declarado, nunca escondido).

Uso:

    python -m tab.estado --video "<caminho>" --inicio 0.5 --janela 60
"""

import argparse
import sys

from .caminhos import MODELO_PADRAO
from .cursor import rastrear
from .inventario import ler_quadro
from .painel import escolher
from .pipeline import roi_das_cordas
from .reconhecer import carregar_modelo, reconhecer_linha


def nota_do_x(x: float, xs: list[int]) -> int:
    """Devolve o índice (na ordem dada) da nota cuja célula contém ``x``.

    A célula é o intervalo entre as fronteiras vizinhas, com as fronteiras no **meio** entre notas
    consecutivas (em ordem de x). É isso que faz a MESMA regra valer para os dois estilos: no salto o
    marcador **cai dentro** da célula, na varredura ele **entra** nela.

    Args:
        x: x do marcador.
        xs: x das notas, na ordem em que aparecem.

    Returns:
        Índice da nota atual, ou ``-1`` se não houver notas.
    """
    if not xs:
        return -1
    ordem = sorted(range(len(xs)), key=lambda i: xs[i])
    for pos in range(len(ordem) - 1):
        a, b = xs[ordem[pos]], xs[ordem[pos + 1]]
        if x < (a + b) / 2:
            return ordem[pos]
    return ordem[-1]


def onsets(amostras: list[dict], xs: list[int]) -> dict[int, float]:
    """Devolve o instante do primeiro quadro em que cada nota passou a ser a atual.

    Args:
        amostras: série do `rastrear` (com ``t`` e ``x``).
        xs: x das notas.

    Returns:
        ``{índice da nota: t do onset}``.
    """
    achados: dict[int, float] = {}
    for a in amostras:
        if a.get("x") is None:
            continue
        atual = nota_do_x(float(a["x"]), xs)
        if atual >= 0 and atual not in achados:
            achados[atual] = float(a["t"])
    return achados


def main() -> int:
    """Mede, num vídeo, quantas notas ganham onset pela regra do ESTADO."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--inicio", type=float, default=0.5)
    ap.add_argument("--janela", type=float, default=60.0)
    ap.add_argument("--passo", type=int, default=30)
    args = ap.parse_args()

    modelo, rotulos, dev = carregar_modelo(str(MODELO_PADRAO))
    quadro, _ = ler_quadro(args.video, args.inicio)
    if quadro is None:
        print("quadro ilegível", file=sys.stderr)
        return 2
    cand = escolher(quadro)
    if cand is None:
        print("sem painel", file=sys.stderr)
        return 3
    y0, y1 = roi_das_cordas(cand)
    r = reconhecer_linha(cand.roi, modelo, rotulos, dev)
    notas = [
        n for n in r["notas"] if isinstance(n.get("casa"), str) and n["casa"].isdigit()
    ]
    xs = [int(n["x"]) for n in notas]
    amostras = rastrear(args.video, (y0, y1), passo=args.passo).get("amostras") or []
    if args.janela:
        t0 = amostras[0]["t"] if amostras else 0.0
        amostras = [a for a in amostras if t0 <= a["t"] <= t0 + args.janela]
    achados = onsets(amostras, xs)
    com_x = [a for a in amostras if a.get("x") is not None]
    print(
        f"notas (algarismos)={len(notas)} | amostras={len(amostras)} (com x: {len(com_x)}) | "
        f"ONSETS={len(achados)} de {len(notas)}"
    )
    if achados:
        primeiros = sorted(achados.items(), key=lambda kv: kv[1])[:6]
        print("primeiros onsets (nota -> t):", [(i, round(t, 2)) for i, t in primeiros])
    if not com_x:
        print(
            "MOTIVO: nenhuma amostra com x (marcador ausente na janela) — tempo NAO medido"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

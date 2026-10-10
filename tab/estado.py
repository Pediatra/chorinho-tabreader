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
from .destaque import coloracao
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


def estado_por_cor(
    video: str,
    cand,
    xs: list[int],
    n_amostras: int,
    frac_ini: float = 0.5,
    frac_fim: float = 0.6,
) -> dict:
    """Lê o estado pela COR DO ALGARISMO — o segundo observador, para quem não tem faixa vertical.

    O `mr. tabs` mostrou o sinal limpo: **um** algarismo com coloração 22,7 e a **mediana em 0,0**. A regra
    é a mesma da posição, só troca o observador: a nota atual é a do algarismo **aceso** (o outlier de
    coloração), e o onset é o primeiro instante em que ele passa a ser o aceso.

    **Usa `ler_quadro`, não `cv2.VideoCapture`**: 44 % do acervo é AV1 e o OpenCV não decodifica — foi o que
    fez a primeira versão ler ZERO quadros. Além disso, amostra por **fração** (não por índice de quadro),
    que é como o resto do projeto lê.

    Args:
        video: caminho do vídeo.
        cand: painel escolhido (dá a origem da ROI em ``y0``).
        xs: x das notas (a célula de x mapeia o token aceso para a nota).
        n_amostras: quantas frações amostrar entre ``frac_ini`` e ``frac_fim``.
        frac_ini: fração inicial.
        frac_fim: fração final.

    Returns:
        ``{"onsets": {índice: fração}, "amostras": n, "com_destaque": n, "motivo": str|None}``.
    """
    onsets: dict[int, float] = {}
    amostras = com = 0
    for k in range(max(1, n_amostras)):
        frac = frac_ini + (frac_fim - frac_ini) * k / max(1, n_amostras - 1)
        quadro, _ = ler_quadro(video, frac)
        if quadro is None:
            continue
        amostras += 1
        melhor, melhor_c, outras = -1, 0.0, []
        # O DESTAQUE ESTA NO TOKEN DA GRADE (nao no `caixa_token` da nota, que so existe quando o filtro
        # de simbolo roda — foi esse engano que deu denominador ZERO na primeira tentativa).
        for i, tk in enumerate(cand.grade.glifos):
            rec = quadro[cand.y0 + tk.y0 : cand.y0 + tk.y1, tk.x0 : tk.x1]
            c = coloracao(rec)
            outras.append(c)
            if c > melhor_c:
                melhor, melhor_c = i, c
        mediana = sorted(outras)[len(outras) // 2] if outras else 0.0
        if melhor >= 0 and melhor_c >= 5.0 and melhor_c >= 3.0 * max(mediana, 0.5):
            com += 1
            # A MESMA REGRA do outro observador: qual NOTA esta acesa — aqui, a nota cuja celula de x
            # contem o token colorido.
            tk = cand.grade.glifos[melhor]
            atual = nota_do_x(float((tk.x0 + tk.x1) / 2), xs)
            if atual >= 0 and atual not in onsets:
                onsets[atual] = frac
    motivo = None
    if amostras == 0:
        motivo = "nenhum quadro lido na janela (leitor falhou)"
    elif com == 0:
        motivo = "nenhum algarismo em destaque de cor (nao ha marcador por cor)"
    return {
        "onsets": onsets,
        "amostras": amostras,
        "com_destaque": com,
        "motivo": motivo,
    }


def main() -> int:
    """Mede, num vídeo, quantas notas ganham onset pela regra do ESTADO."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--inicio", type=float, default=0.5)
    ap.add_argument("--janela", type=float, default=60.0)
    ap.add_argument("--passo", type=int, default=30)
    ap.add_argument(
        "--por-cor", action="store_true", help="usa o destaque de cor como observador"
    )
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
    if args.por_cor:
        cor = estado_por_cor(
            args.video,
            cand,
            xs,
            max(4, int(args.janela / 2)),
            args.inicio,
            min(0.99, args.inicio + args.janela / 600.0),
        )
        print(
            f"[COR] amostras={cor['amostras']} com_destaque={cor['com_destaque']} "
            f"ONSETS={len(cor['onsets'])} de {len(notas)}"
        )
        if cor["motivo"]:
            print(f"MOTIVO: {cor['motivo']}")
        return 0
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

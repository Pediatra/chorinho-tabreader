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
import itertools
import sys
from collections.abc import Callable
from dataclasses import dataclass, field

from . import leitor
from .caminhos import MODELO_PADRAO
from .colunas import Coluna, agrupar_colunas
from .cursor import detectar_cursor, rastrear
from .destaque import coloracao
from .inventario import ler_quadro
from .painel import escolher
from .pipeline import roi_das_cordas
from .reconhecer import carregar_modelo, reconhecer_linha

#: Largura mínima, em px, da banda do marcador. Abaixo disso é ruído (no AV1 do
#: ``mr. tabs`` aparece detecção de 1 px que fica parada por vários quadros).
LARGURA_MINIMA_MARCADOR = 3

#: Amostras seguidas com o mesmo estado para ele ser aceito (anti-ruído, T5.2).
ESTAVEL_MINIMO = 2

#: Quanto (em passos) o marcador pode ficar além da primeira ou da última coluna e
#: ainda contar como o estado da coluna de borda.
MARGEM_PASSOS = 1.0

#: Coloração mínima para uma coluna contar como acesa (critério de ``estado_por_cor``).
COR_MINIMA = 5.0

#: Razão mínima entre a coluna acesa e a mediana das colunas (critério de ``estado_por_cor``).
COR_RAZAO_MINIMA = 3.0

#: Coloração de referência para a razão, para não dividir por quase zero.
COR_MEDIANA_PISO = 0.5

#: Saturação mínima da faixa do marcador no detector de posição. A faixa do `retrato brasileiro`
#: tem saturação mediana 38 (62 em um quadro) e o fundo da partitura 3; com o corte 60 do cursor
#: a faixa clara some de vários quadros e a régua lia uma coluna antiga como estado atual
#: (medido na Fase 5, t = 394, 480 e 512 s: a faixa estava lá, no quadro de seek).
SATURACAO_MARCADOR = 20


@dataclass
class Amostra:
    """Uma leitura de um quadro dentro de uma exibição.

    Attributes:
        t: instante, em segundos (o mesmo do ``tab.leitor``).
        x: x do marcador no espaço do QUADRO, ou ``None`` se não há faixa válida.
        cores: coloração máxima de cada coluna, na ordem das colunas da tela.
    """

    t: float
    x: float | None
    cores: list[float]


@dataclass
class Corrida:
    """Um trecho contínuo em que o observador afirma a mesma coluna atual.

    Attributes:
        coluna: índice (0-based, na ordem de x) da coluna atual.
        t_ini: instante da primeira amostra do trecho.
        n: amostras do trecho (ao menos ``ESTAVEL_MINIMO`` depois do filtro).
    """

    coluna: int
    t_ini: float
    n: int


@dataclass
class Observacao:
    """O que um observador disse sobre uma exibição.

    Attributes:
        observador: nome do observador (``posicao``, ``cor`` ou ``cor_acende``).
        corridas: trechos aceitos, em ordem de tempo, já fundidos.
        passagens: uma lista por passagem: ``{índice da coluna: t do onset}``.
        transicoes: quantas trocas de coluna entre trechos consecutivos.
        avancos: trocas de +1 ou +2 colunas.
        coerencia: ``avancos / transicoes`` (0,0 sem transição).
        cobertura: fração das amostras que caem num trecho aceito.
    """

    observador: str
    corridas: list[Corrida] = field(default_factory=list)
    passagens: list[dict[int, float]] = field(default_factory=list)
    transicoes: int = 0
    avancos: int = 0
    coerencia: float = 0.0
    cobertura: float = 0.0


def nota_do_x(x: float, xs: list[float]) -> int:
    """Devolve o índice (na ordem dada) da nota cuja célula contém ``x``.

    A célula é o intervalo entre as fronteiras vizinhas, com as fronteiras no **meio** entre notas
    consecutivas (em ordem de x). É isso que faz a MESMA regra valer para os dois estilos: no salto o
    marcador **cai dentro** da célula, na varredura ele **entra** nela.

    Args:
        x: x do marcador.
        xs: x das notas (ou das colunas), na ordem em que aparecem.

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


def onsets(amostras: list[dict], xs: list[float]) -> dict[int, float]:
    """Devolve o instante do primeiro quadro em que cada nota passou a ser a atual.

    Args:
        amostras: série do `rastrear` (com ``t`` e ``x``).
        xs: x das notas (ou das colunas).

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


def onsets_por_coluna(amostras: list[dict], colunas: list[Coluna]) -> dict[int, float]:
    """Onset de cada COLUNA: o 1º instante em que ela é a coluna atual do marcador.

    Args:
        amostras: série do `rastrear` (com ``t`` e ``x`` no espaço do quadro).
        colunas: colunas de `tab.colunas.agrupar_colunas`.

    Returns:
        ``{índice da coluna: t do onset}``.
    """
    return onsets(amostras, [c.x_quadro for c in colunas])


def expandir_para_notas(
    onsets_colunas: dict[int, float], colunas: list[Coluna]
) -> dict[int, float]:
    """Dá a cada NOTA o onset da sua coluna (todas as notas do acorde recebem o mesmo).

    Args:
        onsets_colunas: ``{índice da coluna: t}``, como devolvido por `onsets_por_coluna`.
        colunas: as mesmas colunas usadas para gerar ``onsets_colunas``.

    Returns:
        ``{índice da nota: t}``. Notas de colunas sem onset ficam de fora.
    """
    por_nota: dict[int, float] = {}
    for k, col in enumerate(colunas):
        if k in onsets_colunas:
            for i in col.indices:
                por_nota[i] = onsets_colunas[k]
    return por_nota


def estado_por_cor(
    video: str,
    cand,
    colunas: list[Coluna],
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
        cand: painel escolhido (dá a origem da ROI em ``y0`` e ``x0``).
        colunas: colunas de `tab.colunas.agrupar_colunas` (``x_quadro`` no espaço
            do QUADRO; a célula de x mapeia o token aceso para a coluna).
        n_amostras: quantas frações amostrar entre ``frac_ini`` e ``frac_fim``.
        frac_ini: fração inicial.
        frac_fim: fração final.

    Returns:
        ``{"onsets": {índice da coluna: fração}, "amostras": n, "com_destaque": n,
        "motivo": str|None}``.
    """
    xs = [c.x_quadro for c in colunas]
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
            rec = quadro[
                cand.y0 + tk.y0 : cand.y0 + tk.y1, cand.x0 + tk.x0 : cand.x0 + tk.x1
            ]
            c = coloracao(rec)
            outras.append(c)
            if c > melhor_c:
                melhor, melhor_c = i, c
        mediana = sorted(outras)[len(outras) // 2] if outras else 0.0
        if melhor >= 0 and melhor_c >= 5.0 and melhor_c >= 3.0 * max(mediana, 0.5):
            com += 1
            # A MESMA REGRA do outro observador: qual COLUNA esta acesa — a cuja celula de x
            # contem o token colorido.
            tk = cand.grade.glifos[melhor]
            atual = nota_do_x(cand.x0 + float((tk.x0 + tk.x1) / 2), xs)
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


def ler_amostras(
    video: str,
    t0: float,
    t1: float,
    qps: float,
    recorte_y: tuple[int, int],
    caixas: list[list[tuple[int, int, int, int]]],
) -> list[Amostra]:
    """Lê a exibição ``[t0, t1]`` uma vez e mede posição e cor em cada quadro.

    É a ÚNICA leitura dos observadores: posição e cor saem do mesmo quadro, então não há
    dois caminhos de tempo para comparar. O recorte é só em y (a faixa da tela), então o x
    do marcador e as caixas já saem no espaço do quadro.

    Args:
        video: caminho do vídeo (lido por ``tab.leitor``).
        t0: início da exibição, em segundos.
        t1: fim da exibição, em segundos.
        qps: quadros por segundo (T5.1: ~6).
        recorte_y: ``(y0, y1)`` da faixa da tela, no quadro.
        caixas: para cada coluna, as caixas ``(x0, y0, x1, y1)`` dos algarismos, com
            ``x`` no quadro e ``y`` relativo ao recorte.

    Returns:
        Uma ``Amostra`` por quadro lido, em ordem de tempo.
    """
    amostras: list[Amostra] = []
    for t, quadro in leitor.quadros_pts(video, t0, t1, qps, recorte_y=recorte_y):
        det = detectar_cursor(quadro, sat_min=SATURACAO_MARCADOR)
        x = None
        if det is not None and det[1] - det[0] + 1 >= LARGURA_MINIMA_MARCADOR:
            x = (det[0] + det[1]) / 2.0
        cores = []
        for cx in caixas:
            melhor = 0.0
            for x0, y0, x1, y1 in cx:
                rec = quadro[max(0, y0) : max(0, y1), max(0, x0) : max(0, x1)]
                melhor = max(melhor, coloracao(rec))
            cores.append(melhor)
        amostras.append(Amostra(t=t, x=x, cores=cores))
    return amostras


def estados_posicao(
    amostras: list[Amostra], centros: list[float], passo: float
) -> list[int | None]:
    """Estado (coluna) em cada amostra, pelo x do marcador.

    Args:
        amostras: leituras da exibição.
        centros: x (no quadro) de cada coluna, em ordem crescente.
        passo: passo entre cordas, em px; define a margem além das colunas de borda.

    Returns:
        Índice da coluna atual por amostra, ou ``None`` sem marcador ou fora da faixa.
    """
    if not centros:
        return [None] * len(amostras)
    lo = centros[0] - MARGEM_PASSOS * passo
    hi = centros[-1] + MARGEM_PASSOS * passo
    estados: list[int | None] = []
    for a in amostras:
        if a.x is None or not lo <= a.x <= hi:
            estados.append(None)
        else:
            estados.append(nota_do_x(a.x, centros))
    return estados


def estados_cor(amostras: list[Amostra], modo: str) -> list[int | None]:
    """Estado (coluna acesa) em cada amostra, pela cor do algarismo.

    Dois modos, porque a cor tem duas formas (ver ``ESTADO.md``):

    - ``destaque``: o algarismo que se destaca AGORA (coloração >= ``COR_MINIMA`` e >=
      ``COR_RAZAO_MINIMA`` vezes a mediana). Serve à cor que só existe enquanto tocada;
    - ``acende``: a coluna que ACENDEU desde a amostra anterior (maior subida de coloração
      >= ``COR_MINIMA``). Serve à cor cumulativa (o algarismo fica colorido depois de tocado):
      o estado segue a última coluna que acendeu.

    Args:
        amostras: leituras da exibição, em ordem de tempo.
        modo: ``"destaque"`` ou ``"acende"``.

    Returns:
        Índice da coluna acesa por amostra, ou ``None``.

    Raises:
        ValueError: se ``modo`` não for conhecido.
    """
    if modo not in ("destaque", "acende"):
        raise ValueError(f"modo de cor desconhecido: {modo!r}")
    estados: list[int | None] = []
    if modo == "destaque":
        for a in amostras:
            if not a.cores:
                estados.append(None)
                continue
            maior = max(a.cores)
            mediana = sorted(a.cores)[len(a.cores) // 2]
            ok = maior >= COR_MINIMA and maior >= COR_RAZAO_MINIMA * max(
                mediana, COR_MEDIANA_PISO
            )
            estados.append(a.cores.index(maior) if ok else None)
        return estados
    atual: int | None = None
    anterior: list[float] | None = None
    for a in amostras:
        if anterior is not None and a.cores:
            subida = [c - p for c, p in zip(a.cores, anterior, strict=False)]
            if subida and max(subida) >= COR_MINIMA:
                atual = subida.index(max(subida))
        estados.append(atual)
        anterior = a.cores
    return estados


def corridas_estaveis(
    estados: list[int | None], ts: list[float], minimo: int = ESTAVEL_MINIMO
) -> list[Corrida]:
    """Trechos contínuos com a mesma coluna, filtrados pela estabilidade (T5.2).

    Um trecho é uma sequência de amostras seguidas com a mesma coluna, sem ``None`` no
    meio. Trechos com menos de ``minimo`` amostras são ruído e saem. Trechos da mesma
    coluna separados só por ``None`` (ou por ruído descartado) são fundidos.

    Args:
        estados: coluna atual por amostra (``None`` = indefinido).
        ts: instante de cada amostra, na mesma ordem.
        minimo: amostras mínimas para aceitar um trecho.

    Returns:
        Os trechos aceitos, em ordem de tempo.
    """
    brutos: list[Corrida] = []
    colado = False  # a amostra anterior tinha estado definido
    for estado, t in zip(estados, ts, strict=True):
        if estado is None:
            colado = False
            continue
        if colado and brutos[-1].coluna == estado:
            brutos[-1].n += 1
        else:
            brutos.append(Corrida(coluna=estado, t_ini=t, n=1))
        colado = True
    aceitos = [c for c in brutos if c.n >= minimo]
    fundidos: list[Corrida] = []
    for c in aceitos:
        if fundidos and fundidos[-1].coluna == c.coluna:
            fundidos[-1].n += c.n
        else:
            fundidos.append(Corrida(c.coluna, c.t_ini, c.n))
    return fundidos


def passagens_de(corridas: list[Corrida]) -> list[list[Corrida]]:
    """Separa os trechos em passagens: uma passagem termina quando o estado volta para trás.

    Args:
        corridas: trechos aceitos, em ordem de tempo.

    Returns:
        Lista de passagens, cada uma com trechos de coluna crescente.
    """
    passagens: list[list[Corrida]] = []
    for c in corridas:
        if not passagens or c.coluna < passagens[-1][-1].coluna:
            passagens.append([c])
        else:
            passagens[-1].append(c)
    return passagens


def refinar_inicios(
    corridas: list[Corrida],
    amostras: list[Amostra],
    ler_fino: Callable[[float, float], list[Amostra]],
    estados_de: Callable[[list[Amostra]], list[int | None]],
    fps: float,
) -> None:
    """Põe o início de cada trecho no quadro nativo em que a coluna nova aparece pela 1ª vez.

    O trecho começa na 1ª amostra (6 qps) que já mostra a coluna nova, então o início fica até
    1/6 s depois da transição real: é o instante da AMOSTRA, não do quadro. Aqui a transição é
    procurada nos quadros nativos entre a amostra anterior e essa amostra, e o início vira o
    tempo (PTS) do primeiro quadro que mostra a coluna. Trecho sem amostra anterior (início da
    exibição) fica como está.

    Args:
        corridas: trechos aceitos (``corridas_estaveis``); os ``t_ini`` são trocados in place.
        amostras: leituras da exibição, em ordem de tempo.
        ler_fino: ``ler_fino(t_a, t_b)`` lê os quadros nativos de ``t_a`` a ``t_b``.
        estados_de: estado (coluna) de cada leitura, com o observador do trecho.
        fps: taxa nativa do vídeo, em quadros por segundo.
    """
    indice = {a.t: i for i, a in enumerate(amostras)}
    for c in corridas:
        k = indice.get(c.t_ini)
        if k is None or k == 0:
            continue
        t_ant = amostras[k - 1].t
        fino = ler_fino(t_ant, c.t_ini + 1.0 / fps)
        for a, estado in zip(fino, estados_de(fino), strict=True):
            if estado == c.coluna and t_ant < a.t:
                c.t_ini = round(a.t, 3)
                break


def observar(
    observador: str,
    amostras: list[Amostra],
    estados: list[int | None],
    minimo: int = ESTAVEL_MINIMO,
) -> Observacao:
    """Resume um observador numa exibição: trechos, passagens, coerência e cobertura.

    Args:
        observador: nome do observador.
        amostras: leituras da exibição (dão os instantes e o total).
        estados: coluna atual por amostra, já produzida pelo observador.
        minimo: amostras mínimas por trecho.

    Returns:
        A ``Observacao``. Sem trechos, a coerência e a cobertura são zero.
    """
    ts = [a.t for a in amostras]
    corridas = corridas_estaveis(estados, ts, minimo)
    passagens = passagens_de(corridas)
    pares = list(itertools.pairwise(corridas))
    avancos = sum(1 for a, b in pares if 1 <= b.coluna - a.coluna <= 2)
    transicoes = len(pares)
    coberto = sum(c.n for c in corridas)
    return Observacao(
        observador=observador,
        corridas=corridas,
        passagens=[{c.coluna: c.t_ini for c in p} for p in passagens],
        transicoes=transicoes,
        avancos=avancos,
        coerencia=avancos / transicoes if transicoes else 0.0,
        cobertura=coberto / len(amostras) if amostras else 0.0,
    )


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
    xs = [cand.x0 + int(n["x"]) for n in notas]
    colunas = agrupar_colunas(xs, r["passo"])
    amostras = rastrear(args.video, (y0, y1), passo=args.passo).get("amostras") or []
    if args.janela:
        # A JANELA VEM DE ONDE O MARCADOR ESTA ATIVO, nao do `t` da PRIMEIRA amostra. Medido no
        # `leonardo ramos`: a primeira amostra caiu em t=2,4 s, a janela varreu 2,4-62,4 s — um trecho
        # MORTO onde o marcador aparece UMA vez — e o resultado foi 1 onset de 45, que eu quase atribui
        # a regra. O cursor e INTERMITENTE (AGENTS.md): se a janela pedida tem pouca coisa, ela cede
        # lugar a serie inteira, e isso e DECLARADO.
        com_x = [a for a in amostras if a.get("x") is not None]
        t0 = com_x[0]["t"] if com_x else (amostras[0]["t"] if amostras else 0.0)
        recorte = [a for a in amostras if t0 <= a["t"] <= t0 + args.janela]
        if len([a for a in recorte if a.get("x") is not None]) < 5 and len(com_x) >= 5:
            print(
                f"AVISO: a janela de {args.janela:.0f}s a partir de {t0:.1f}s tem poucas amostras com "
                f"marcador; usando a SERIE INTEIRA ({len(com_x)} amostras com x)"
            )
            recorte = amostras
        amostras = recorte
    if args.por_cor:
        cor = estado_por_cor(
            args.video,
            cand,
            colunas,
            max(4, int(args.janela / 2)),
            args.inicio,
            min(0.99, args.inicio + args.janela / 600.0),
        )
        print(
            f"[COR] amostras={cor['amostras']} com_destaque={cor['com_destaque']} "
            f"ONSETS={len(expandir_para_notas(cor['onsets'], colunas))} de {len(notas)} "
            f"(colunas={len(colunas)})"
        )
        if cor["motivo"]:
            print(f"MOTIVO: {cor['motivo']}")
        return 0
    achados = expandir_para_notas(onsets_por_coluna(amostras, colunas), colunas)
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

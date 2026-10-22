"""Censo de mãos (M0): regras puras sobre as detecções, sem detector e sem acervo.

O detector (``tab.maos_censo``) grava, por quadro de presença, as mãos e os rostos achados.
Este módulo decide o que conta: funde a mesma mão achada no quadro inteiro e nos blocos,
descarta mão desenhada DENTRO da tablatura (o ``sky guitar`` tem diagrama de mão no
painel), classifica a vista do quadro e resume por vídeo e por canal.

Separado do detector de propósito: o gate roda sem MediaPipe, e estas regras são o que
precisa de teste.
"""

from __future__ import annotations

import statistics
from collections import Counter

#: Duas detecções são a MESMA mão quando a interseção cobre esta fração da caixa menor.
#: O bloco costuma ver a mão inteira ou cortada; a caixa cortada fica dentro da inteira.
SOBREPOSICAO_MESMA_MAO = 0.5

#: Vídeo "serve para mãos" quando as duas mãos aparecem em pelo menos esta fração dos
#: quadros lidos (proposta para o M0; o número que decide é a tabela, não este limiar).
FRACAO_VIDEO_COM_MAOS = 0.5

#: Vistas possíveis de um quadro: rosto no quadro, mão sem rosto, nenhuma mão.
#: (A pose do MediaPipe foi medida e REPROVADA para isto: marcou "rosto" em 5 de 12
#: quadros de close das mãos do ``sky guitar``, onde não há rosto.)
VISTAS: tuple[str, ...] = ("rosto", "sem_rosto", "sem_mao")


def area(caixa: list[float]) -> float:
    """Área de uma caixa ``[x0, y0, x1, y1]`` (zero se degenerada).

    Args:
        caixa: caixa em pixels.

    Returns:
        A área em pixels quadrados.
    """
    return max(0.0, caixa[2] - caixa[0]) * max(0.0, caixa[3] - caixa[1])


def sobreposicao(a: list[float], b: list[float]) -> float:
    """Fração da caixa MENOR coberta pela interseção das duas.

    Args:
        a: primeira caixa ``[x0, y0, x1, y1]``.
        b: segunda caixa.

    Returns:
        Valor em [0, 1]; 0 quando uma das caixas é degenerada.
    """
    inter = [max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])]
    menor = min(area(a), area(b))
    if menor <= 0:
        return 0.0
    return area(inter) / menor


def fundir_maos(maos: list[dict]) -> list[dict]:
    """Funde detecções da mesma mão (quadro inteiro e blocos), ficando com a de maior score.

    Args:
        maos: detecções com ``caixa`` e ``score``.

    Returns:
        As detecções mantidas, em ordem decrescente de score.
    """
    mantidas: list[dict] = []
    for mao in sorted(maos, key=lambda m: -m["score"]):
        if all(
            sobreposicao(mao["caixa"], m["caixa"]) < SOBREPOSICAO_MESMA_MAO
            for m in mantidas
        ):
            mantidas.append(mao)
    return mantidas


def dentro_da_tab(caixa: list[float], rect: list[int] | None) -> bool:
    """Se o centro da caixa da mão cai dentro do painel da tablatura.

    Args:
        caixa: caixa da mão ``[x0, y0, x1, y1]``.
        rect: caixa do painel ``[x0, y0, x1, y1]`` do censo, ou None (sem TAB).

    Returns:
        True quando a mão é, quase certamente, desenho do painel.
    """
    if rect is None:
        return False
    cx, cy = (caixa[0] + caixa[2]) / 2, (caixa[1] + caixa[3]) / 2
    return rect[0] <= cx <= rect[2] and rect[1] <= cy <= rect[3]


def vista_do_quadro(n_rostos: int, n_maos: int) -> str:
    """Classe de enquadramento do quadro a partir do rosto e das mãos.

    Args:
        n_rostos: rostos achados pelo detector de rosto.
        n_maos: mãos válidas no quadro.

    Returns:
        ``rosto`` (há rosto), ``sem_rosto`` (há mão e nenhum rosto: tronco cortado ou
        close do braço) ou ``sem_mao`` (nem rosto nem mão).
    """
    if n_rostos > 0:
        return "rosto"
    if n_maos > 0:
        return "sem_rosto"
    return "sem_mao"


def resumo_do_quadro(registro: dict) -> dict:
    """Decisões de um quadro: mãos válidas por lado e vista.

    Espera as mãos já fundidas por ``fundir_maos`` (o censo funde antes de gravar).

    Args:
        registro: quadro gravado pelo censo (``maos``, ``rostos``, ``rect``, ``tab``).

    Returns:
        ``{"esquerda", "direita", "duas", "duas_qualquer", "n_maos", "vista",
        "palma_px", "tab"}``. O lado é o rótulo do detector (``L``/``R``), que troca a
        mão do braço vista de costas; ``duas_qualquer`` (2+ mãos, qualquer lado) não
        depende dele.
    """
    validas = [m for m in registro["maos"] if not m.get("na_tab")]
    lados = Counter(m["lado"] for m in validas)
    esquerda, direita = lados["L"] > 0, lados["R"] > 0
    return {
        "esquerda": esquerda,
        "direita": direita,
        "duas": esquerda and direita,
        "duas_qualquer": len(validas) >= 2,
        "n_maos": len(validas),
        "vista": vista_do_quadro(len(registro.get("rostos", [])), len(validas)),
        "palma_px": [m["palma_px"] for m in validas],
        "tab": bool(registro.get("tab")),
    }


def resumo_do_video(registro: dict) -> dict:
    """Frações por vídeo sobre os quadros lidos.

    Args:
        registro: linha do censo de mãos (``quadros`` com os registros por quadro).

    Returns:
        Contagens e frações; ``serve`` diz se as duas mãos aparecem em pelo menos
        ``FRACAO_VIDEO_COM_MAOS`` dos quadros lidos (2+ mãos, qualquer lado).
    """
    quadros = [resumo_do_quadro(q) for q in registro["quadros"]]
    n = len(quadros)
    com_tab = [q for q in quadros if q["tab"]]
    palmas = [p for q in quadros for p in q["palma_px"]]
    vistas = Counter(q["vista"] for q in quadros)
    duas = sum(q["duas"] for q in quadros)
    duas_qualquer = sum(q["duas_qualquer"] for q in quadros)
    return {
        "canal": registro["canal"],
        "n": n,
        "esquerda": sum(q["esquerda"] for q in quadros),
        "direita": sum(q["direita"] for q in quadros),
        "duas": duas,
        "uma_ou_mais": sum(q["n_maos"] > 0 for q in quadros),
        "duas_qualquer": duas_qualquer,
        "n_tab": len(com_tab),
        "tab_e_duas": sum(q["duas_qualquer"] for q in com_tab),
        "mais_de_duas": sum(q["n_maos"] > 2 for q in quadros),
        "vistas": dict(vistas),
        "palma_px": statistics.median(palmas) if palmas else None,
        "altura": registro.get("altura"),
        "serve": n > 0 and duas_qualquer / n >= FRACAO_VIDEO_COM_MAOS,
    }


def _pct(parte: int, todo: int) -> str:
    """Porcentagem inteira, ou travessão quando o todo é zero."""
    return f"{round(100 * parte / todo)} %" if todo else "—"


def tabela_por_canal(videos: list[dict]) -> list[dict]:
    """Agrega os resumos por vídeo em uma linha por canal (e uma linha TOTAL no fim).

    Args:
        videos: saídas de ``resumo_do_video``.

    Returns:
        Linhas com contagens brutas (denominadores incluídos), em ordem decrescente de
        número de vídeos.
    """
    por_canal: dict[str, list[dict]] = {}
    for v in videos:
        por_canal.setdefault(v["canal"], []).append(v)
    linhas = [_linha(canal, vs) for canal, vs in por_canal.items()]
    linhas.sort(key=lambda r: (-r["videos"], r["canal"]))
    linhas.append(_linha("TOTAL", videos))
    return linhas


def _linha(canal: str, vs: list[dict]) -> dict:
    """Soma os vídeos de um canal (ou de todos) numa linha da tabela."""
    vistas: Counter[str] = Counter()
    for v in vs:
        vistas.update(v["vistas"])
    palmas = [v["palma_px"] / v["altura"] for v in vs if v["palma_px"] and v["altura"]]
    return {
        "canal": canal,
        "videos": len(vs),
        "quadros": sum(v["n"] for v in vs),
        "esquerda": sum(v["esquerda"] for v in vs),
        "direita": sum(v["direita"] for v in vs),
        "duas": sum(v["duas"] for v in vs),
        "uma_ou_mais": sum(v["uma_ou_mais"] for v in vs),
        "duas_qualquer": sum(v["duas_qualquer"] for v in vs),
        "n_tab": sum(v["n_tab"] for v in vs),
        "tab_e_duas": sum(v["tab_e_duas"] for v in vs),
        "mais_de_duas": sum(v["mais_de_duas"] for v in vs),
        "servem": sum(v["serve"] for v in vs),
        "vistas": dict(vistas),
        "palma_altura": statistics.median(palmas) if palmas else None,
    }


def markdown(linhas: list[dict]) -> str:
    """Tabela por canal em Markdown, com denominadores à vista.

    As colunas principais (alguma mão, 2+ mãos) não dependem do rótulo de lado; as
    colunas por lado (L, R, L e R) usam o rótulo do detector e são secundárias.

    Args:
        linhas: saída de ``tabela_por_canal``.

    Returns:
        O texto da tabela.
    """
    cab = (
        "| canal | vídeos | quadros | alguma mão | 2+ mãos | 2+ mãos nos quadros com "
        "TAB | vídeos que servem | L | R | L e R | > 2 mãos | rosto / sem rosto / "
        "sem mão | palma / altura |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    )
    saida = [cab]
    for r in linhas:
        q = r["quadros"]
        vistas = " / ".join(_pct(r["vistas"].get(v, 0), q) for v in VISTAS)
        palma = f"{r['palma_altura']:.3f}" if r["palma_altura"] else "—"
        nome = f"**{r['canal']}**" if r["canal"] == "TOTAL" else r["canal"]
        saida.append(
            f"| {nome} | {r['videos']} | {q} | {_pct(r['uma_ou_mais'], q)} | "
            f"{_pct(r['duas_qualquer'], q)} | "
            f"{_pct(r['tab_e_duas'], r['n_tab'])} ({r['tab_e_duas']}/{r['n_tab']}) | "
            f"{r['servem']} ({_pct(r['servem'], r['videos'])}) | "
            f"{_pct(r['esquerda'], q)} | {_pct(r['direita'], q)} | "
            f"{_pct(r['duas'], q)} | {_pct(r['mais_de_duas'], q)} | {vistas} | "
            f"{palma} |"
        )
    return "\n".join(saida)

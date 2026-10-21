"""Confere ``paginar`` contra os produtos de tablatura de três vídeos conhecidos.

Para cada vídeo, compara as páginas achadas por ``tab.partitura_video paginar`` (pasta
``diag/paginar_validacao/<stem>/recortes/indice.json``) com as telas do produto
(``data/saida/fase8/rede/<stem>.json``) e com os recortes que o produto gerou
(``data/saida/partitura/video/<stem>/recortes/indice.json``).

Regras:
- o instante de cada tela do produto é o ponto médio da primeira exibição com ``t1 > t0``
  (o mesmo de ``instante_da_tela``);
- a página casada com a tela é a que tem uma exibição contendo esse instante;
- ``sobreposicao`` é o total, em segundos, em que a primeira exibição da tela cobre
  as exibições da página casada;
- a caixa comparada é a da pauta mais baixa da página e a da entrada do produto para a
  mesma tela; as duas podem vir de quadros em instantes diferentes (o produto usa o meio
  da primeira exibição; a página, o meio da mais longa).

Uso:
    python data/saida/partitura/diag/conferir_paginas.py
"""

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[4]
PRODUTOS = RAIZ / "data" / "saida" / "fase8" / "rede"
PRODUTO_RECORTES = RAIZ / "data" / "saida" / "partitura" / "video"
PAGINAS = RAIZ / "data" / "saida" / "partitura" / "diag" / "paginar_validacao"

VIDEOS = (
    "greensleeves_guia_de_estudio_partitura_tab_pdf",
    "south_american_music_easy_guitar_tutorial_with_sheet_and_tab",
    "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar",
)


def primeira_exibicao(tela: dict) -> tuple[float, float] | None:
    """Primeira exibição com ``t1 > t0`` de uma tela do produto.

    Args:
        tela: tela do produto, com ``exibicoes``.

    Returns:
        ``(t0, t1)`` ou ``None``.
    """
    for exibicao in tela.get("exibicoes", []):
        t0, t1 = float(exibicao["t0"]), float(exibicao["t1"])
        if t1 > t0:
            return t0, t1
    return None


def paginas_do_indice(indice: list[dict]) -> dict[int, dict]:
    """Agrupa o índice de ``paginar`` por página.

    Args:
        indice: entradas de ``recortes/indice.json`` (pauta e página sem pauta).

    Returns:
        ``{pagina: {"exibicoes", "pautas", "t"}}``, com ``pautas`` as entradas com pauta,
        de cima para baixo.
    """
    paginas: dict[int, dict] = {}
    for entrada in indice:
        numero = entrada["pagina"]
        pagina = paginas.setdefault(
            numero, {"exibicoes": entrada["exibicoes"], "pautas": [], "t": entrada["t"]}
        )
        if not entrada["sem_pauta"]:
            pagina["pautas"].append(entrada)
    for pagina in paginas.values():
        pagina["pautas"].sort(key=lambda e: e["ys"][4])
    return paginas


def sobreposicao(a: tuple[float, float], exibicoes: list[dict]) -> float:
    """Segundos em que o intervalo ``a`` cobre as exibições dadas.

    Args:
        a: ``(t0, t1)``.
        exibicoes: exibições ``{"t0", "t1"}``.

    Returns:
        A soma das sobreposições, em segundos.
    """
    total = 0.0
    for e in exibicoes:
        total += max(0.0, min(a[1], float(e["t1"])) - max(a[0], float(e["t0"])))
    return total


def conferir(stem: str) -> None:
    """Imprime a conferência de um vídeo.

    Args:
        stem: nome do produto (sem extensão), que é também a pasta de ``diag``.
    """
    produto = json.loads((PRODUTOS / f"{stem}.json").read_text(encoding="utf-8"))
    telas = produto["telas"]
    indice_produto = json.loads(
        (PRODUTO_RECORTES / stem / "recortes" / "indice.json").read_text(
            encoding="utf-8"
        )
    )
    recorte_produto = {e["tela"]: e for e in indice_produto}
    indice_paginas = json.loads(
        (PAGINAS / stem / "recortes" / "indice.json").read_text(encoding="utf-8")
    )
    paginas = paginas_do_indice(indice_paginas)

    print(f"== {stem}")
    print(f"telas do produto: {len(telas)} | paginas achadas: {len(paginas)}")
    casadas: dict[int, list[int]] = {}
    for tela in telas:
        numero = int(tela["id"])
        exibicao = primeira_exibicao(tela)
        if exibicao is None:
            print(f"tela {numero}: sem exibicao valida no produto")
            continue
        meio = (exibicao[0] + exibicao[1]) / 2
        exibicao_txt = f"({exibicao[0]:.2f},{exibicao[1]:.2f})"
        achadas = [
            numero_pagina
            for numero_pagina, pagina in paginas.items()
            if any(
                float(e["t0"]) <= meio <= float(e["t1"]) for e in pagina["exibicoes"]
            )
        ]
        if not achadas:
            print(
                f"tela {numero}: 1a exibicao {exibicao_txt} meio {meio:.2f}"
                " -> nenhuma pagina cobre esse instante"
            )
            continue
        for numero_pagina in achadas:
            casadas.setdefault(numero_pagina, []).append(numero)
            pagina = paginas[numero_pagina]
            overlap = sobreposicao(exibicao, pagina["exibicoes"])
            base = pagina["pautas"][-1] if pagina["pautas"] else None
            produto_recorte = recorte_produto.get(numero)
            print(
                f"tela {numero}: 1a exibicao {exibicao_txt} meio {meio:.2f}"
                f" -> pagina P{numero_pagina:02d}, sobreposicao {overlap:.2f} s"
            )
            if base is None:
                print("   pagina sem pauta: nada a comparar")
                continue
            if produto_recorte is None or produto_recorte["sem_pauta"]:
                motivo = produto_recorte["motivo"] if produto_recorte else "sem entrada"
                print(f"   produto sem recorte ({motivo}); pauta P: {base['caixa_recorte']}")
                continue
            caixa_pagina = base["caixa_recorte"]
            caixa_produto = produto_recorte["caixa_recorte"]
            diff = [a - b for a, b in zip(caixa_pagina, caixa_produto, strict=True)]
            print(
                f"   caixa pagina {base['id']} {caixa_pagina}"
                f" | caixa produto T{numero:02d} {caixa_produto}"
                f" | diferenca {diff}"
            )
            print(
                f"   pautas da pagina: {len(pagina['pautas'])}"
                f" | t pagina {pagina['t']:.2f} t produto {produto_recorte['t']:.2f}"
            )

    print("paginas sem nenhuma tela:")
    sem_tela = [n for n in paginas if n not in casadas]
    if not sem_tela:
        print("  nenhuma")
    for numero_pagina in sem_tela:
        pagina = paginas[numero_pagina]
        exibicoes = ", ".join(
            f"({float(e['t0']):.2f},{float(e['t1']):.2f})" for e in pagina["exibicoes"]
        )
        print(f"  P{numero_pagina:02d} exibicoes [{exibicoes}] pautas {len(pagina['pautas'])}")
    repetidas = {n: t for n, t in casadas.items() if len(t) > 1}
    for numero_pagina, telas_da_pagina in repetidas.items():
        print(f"pagina P{numero_pagina:02d} casada com varias telas: {telas_da_pagina}")
    print()


def main() -> None:
    """Confere os três vídeos, na ordem fixa de ``VIDEOS``."""
    for stem in VIDEOS:
        conferir(stem)


if __name__ == "__main__":
    main()

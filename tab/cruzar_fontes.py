"""Cruzamento das fontes da nota: tela × som (decisão 2005, Regra 3; rodada 2020).

Módulo **neutro**: só lê o produto da tela (``chorinho/video@1``) e o som livre
(``chorinho/som@1``, decisão 2006). Não calcula nenhuma fonte, e nenhuma fonte usa o que ele
grava. O capo entra como dado de contexto, com a fonte declarada (Regra 1 da 2005).

Por tela do produto e por exibição, as colunas da tela (altura = corda solta + casa + capo)
são pareadas com os eventos do som pelo mesmo pareamento monotônico da régua do transcritor
(``tab.audio_som_medir``). Vale a exibição com mais alturas pareadas. Cada nota da tela
recebe um veredito:

- ``confirma``: a altura dela está no evento pareado com a coluna;
- ``nao_confirma``: a coluna pareou com um evento, mas a altura dela não está nele;
- ``coluna_sem_par``: a coluna não pareou, numa tela em que outras colunas parearam;
- ``sem_dado``: a tela não tem nenhuma coluna pareada.

Uso (container base)::

    python -m tab.cruzar_fontes --produto P.json --som S.som.json --saida C.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from .audio_som_medir import (
    ALTURA_SOLTA,
    CAPO,
    FOLGA_S,
    capo_do_video,
    eventos_do_som,
    midi_da_nota,
    parear,
)

#: Formato provisório da saída (vira decisão quando a rodada 2020 for lida).
ESQUEMA = "chorinho/cruzamento@0"

#: Vereditos possíveis, na ordem do relatório.
VEREDITOS = ("confirma", "nao_confirma", "coluna_sem_par", "sem_dado")


def colunas_do_produto(produto: dict, capo: int) -> dict[int, list[list[dict]]]:
    """As colunas de cada tela do produto, com notas distintas e altura.

    O produto repete a nota por passagem e exibição; aqui cada (tela, coluna, corda) conta
    uma vez, pela primeira entrada. Só entra casa inteira e corda de 1 a 6.

    Args:
        produto: JSON ``chorinho/video@1``.
        capo: casa do capo (dado de contexto).

    Returns:
        ``{tela: [coluna, ...]}``, colunas em ordem de x; cada nota é ``{tela, coluna,
        corda, casa, midi, x}``.
    """
    vistas: set[tuple[int, int, int]] = set()
    por_tela: dict[int, dict[int, list[dict]]] = {}
    for n in produto.get("notas", []):
        casa = n.get("casa")
        if not isinstance(casa, int) or isinstance(casa, bool):
            continue
        if n.get("corda") not in ALTURA_SOLTA:
            continue
        chave = (int(n["tela"]), int(n["coluna"]), int(n["corda"]))
        if chave in vistas:
            continue
        vistas.add(chave)
        por_tela.setdefault(chave[0], {}).setdefault(chave[1], []).append(
            {
                "tela": chave[0],
                "coluna": chave[1],
                "corda": chave[2],
                "casa": casa,
                "midi": midi_da_nota(chave[2], casa, capo),
                "x": float(n.get("x_centro_quadro") or n.get("x_quadro") or 0.0),
            }
        )
    saida = {}
    for tela, colunas in por_tela.items():
        ordem = sorted(
            colunas.values(),
            key=lambda c: (sum(n["x"] for n in c) / len(c), c[0]["coluna"]),
        )
        saida[tela] = [sorted(c, key=lambda n: n["corda"]) for c in ordem]
    return saida


def vereditos(
    colunas: list[list[dict]],
    eventos: list[list[dict]],
    pares: list[tuple[int, int, int]],
) -> list[dict]:
    """O veredito de cada nota da tela, dado o pareamento de uma exibição.

    Args:
        colunas: colunas da tela.
        eventos: eventos do som na janela.
        pares: ``(i_coluna, j_evento, alturas_iguais)`` do pareamento.

    Returns:
        As notas da tela, cada uma com ``veredito`` e, quando confirmada, ``t_som``.
    """
    por_coluna = {i: j for i, j, _ in pares}
    saida = []
    for i, coluna in enumerate(colunas):
        j = por_coluna.get(i)
        restante = (
            Counter(n["midi"] for n in eventos[j]) if j is not None else Counter()
        )
        inicio = {}
        if j is not None:
            for n in eventos[j]:
                inicio.setdefault(n["midi"], n["t_ini"])
        for nota in coluna:
            item = dict(nota)
            if not pares:
                item["veredito"] = "sem_dado"
            elif j is None:
                item["veredito"] = "coluna_sem_par"
            elif restante[nota["midi"]] > 0:
                restante[nota["midi"]] -= 1
                item["veredito"] = "confirma"
                item["t_som"] = inicio[nota["midi"]]
            else:
                item["veredito"] = "nao_confirma"
                item["ouvidas_no_evento"] = sorted(n["midi"] for n in eventos[j])
            saida.append(item)
    return saida


def cruzar_tela(
    colunas: list[list[dict]], som: list[dict], exibicoes: list[tuple[float, float]]
) -> dict:
    """Cruza uma tela com o som: escolhe a exibição e dá o veredito de cada nota.

    Args:
        colunas: colunas da tela.
        som: notas do ``chorinho/som@1`` (``t_ini``, ``midi``).
        exibicoes: janelas ``(t0, t1)`` da tela no produto.

    Returns:
        ``{exibicao, t0, t1, notas, som_sem_tela}``. ``som_sem_tela`` conta as notas ouvidas
        no trecho pareado que nenhuma nota da tela explicou. Sem exibição: tudo ``sem_dado``.
    """
    melhor = None
    for k, (t0, t1) in enumerate(exibicoes):
        eventos = eventos_do_som(som, t0 - FOLGA_S, t1 + FOLGA_S)
        pares = parear(colunas, eventos)
        g = sum(p[2] for p in pares)
        if melhor is None or g > melhor[0]:
            melhor = (g, k, t0, t1, eventos, pares)
    if melhor is None:
        notas = [dict(n, veredito="sem_dado") for c in colunas for n in c]
        return {
            "exibicao": None,
            "t0": None,
            "t1": None,
            "notas": notas,
            "som_sem_tela": 0,
        }
    _, k, t0, t1, eventos, pares = melhor
    notas = vereditos(colunas, eventos, pares)
    sobra = 0
    if pares:
        j0, j1 = pares[0][1], pares[-1][1]
        ouvidas = sum(len(eventos[j]) for j in range(j0, j1 + 1))
        sobra = ouvidas - sum(p[2] for p in pares)
    return {"exibicao": k, "t0": t0, "t1": t1, "notas": notas, "som_sem_tela": sobra}


def cruzar(produto: dict, som: dict, capo: int, fonte_capo: str) -> dict:
    """Cruza um produto da tela com o som livre do mesmo vídeo.

    Args:
        produto: JSON ``chorinho/video@1``.
        som: JSON ``chorinho/som@1``.
        capo: casa do capo.
        fonte_capo: de onde veio a casa do capo.

    Returns:
        O documento ``chorinho/cruzamento@0``: notas com veredito e resumo.

    Raises:
        ValueError: se o produto e o som forem de vídeos diferentes.
    """
    video = (produto.get("video") or {}).get("arquivo")
    if video != som.get("video"):
        raise ValueError(f"vídeos diferentes: {video!r} e {som.get('video')!r}")
    colunas = colunas_do_produto(produto, capo)
    telas = []
    for tela in produto.get("telas", []):
        tid = int(tela["id"])
        exib = [(float(e["t0"]), float(e["t1"])) for e in tela.get("exibicoes", [])]
        r = cruzar_tela(colunas.get(tid, []), som["notas"], exib)
        r["tela"] = tid
        telas.append(r)
    contagem = Counter(n["veredito"] for t in telas for n in t["notas"])
    return {
        "esquema": ESQUEMA,
        "video": video,
        "capo": {"casa": capo, "fonte": fonte_capo},
        "fontes": {
            "tela": (produto.get("gerado_por") or {}).get("modelo"),
            "som": (som.get("transcritor") or {}).get("pesos"),
        },
        "resumo": {v: contagem.get(v, 0) for v in VEREDITOS}
        | {"som_sem_tela": sum(t["som_sem_tela"] for t in telas)},
        "telas": telas,
    }


def main() -> int:
    """Ponto de entrada da CLI.

    Returns:
        Código de saída.
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--produto", type=Path, required=True)
    ap.add_argument("--som", type=Path, required=True)
    ap.add_argument("--saida", type=Path, required=True)
    args = ap.parse_args()
    produto = json.loads(args.produto.read_text(encoding="utf-8"))
    som = json.loads(args.som.read_text(encoding="utf-8"))
    capos = json.loads(CAPO.read_text(encoding="utf-8"))
    video = (produto.get("video") or {}).get("arquivo", "")
    doc = cruzar(produto, som, capo_do_video(video, capos), str(capos.get("fonte")))
    args.saida.write_text(
        json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(json.dumps(doc["resumo"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

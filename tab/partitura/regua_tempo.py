"""F0.3 da partitura: quantas notas da partitura ganham tempo pelo par (rodada 3103).

Para cada evento com ``par`` nos ``.partitura.json`` dos 3 produtos com pauta, acha no
produto da tab (``data/saida/fase8/rede/<stem>.json``) as notas da mesma ``tela`` e
``coluna`` e, para cada exibição, o ``t_ini``. Conta por vídeo e por exibição, separa o
par por ``x`` de reserva, e lista as inversões: dentro de uma exibição, eventos na ordem
(``compasso``, ``t``) em que o tempo volta.

Só lê o que já está gravado e só grava o JSON na pasta da frente 0. Não muda o formato do
produto e não diz que o tempo está certo: o tempo da tab não foi validado por gabarito.

Uso (na raiz do projeto)::

    python -m tab.partitura_regua_tempo
"""

from __future__ import annotations

import argparse
import collections
import itertools
import json

from tab.comum.caminhos import FASE8_REDE, PART_FRENTE_0, PARTITURA_VIDEO

#: Os 3 vídeos com pauta (mesma lista do CA1).
STEMS = [
    "greensleeves_guia_de_estudio_partitura_tab_pdf",
    "south_american_music_easy_guitar_tutorial_with_sheet_and_tab",
    "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar",
]

PASTA_PRODUTO = FASE8_REDE
PASTA_PARTITURA = PARTITURA_VIDEO
SAIDA_JSON = PART_FRENTE_0 / "tempo.json"


def _notas_por_coluna(produto: dict) -> dict[tuple[int, int], dict[int, float | None]]:
    """Mapa ``(tela, coluna)`` -> ``{exibicao: t_ini}`` das notas do produto.

    Args:
        produto: documento de ``data/saida/fase8/rede/<stem>.json``.

    Returns:
        Para cada coluna da tab, o ``t_ini`` (ou None) de cada exibição que a tem.
    """
    mapa: dict[tuple[int, int], dict[int, float | None]] = collections.defaultdict(dict)
    for nota in produto["notas"]:
        chave = (nota["tela"], nota["coluna"])
        mapa[chave][nota["exibicao"]] = nota.get("t_ini")
    return mapa


def _contagem_zerada() -> dict[str, int]:
    """Contadores de um recorte ou de um vídeo, todos em zero."""
    return {
        "eventos": 0,
        "evento_sem_par": 0,
        "par_sem_nota": 0,
        "pares_exibicao": 0,
        "par_com_tempo": 0,
        "par_sem_t_ini": 0,
        "eventos_com_tempo": 0,
    }


def _tempos_do_evento(
    par: dict, mapa: dict[tuple[int, int], dict[int, float | None]]
) -> dict[int, float | None] | None:
    """Exibições da coluna pareada e o ``t_ini`` de cada uma; None se a coluna não tem nota.

    Args:
        par: campo ``par`` do evento (``tela``, ``coluna``, ``metodo``...).
        mapa: saída de ``_notas_por_coluna``.

    Returns:
        ``{exibicao: t_ini}`` da coluna, ou None se o produto não tem nota nela.
    """
    return mapa.get((par["tela"], par["coluna"]))


def _analisar_video(stem: str) -> dict:
    """Conta os pares de um vídeo e lista as inversões de tempo dentro de cada exibição.

    Args:
        stem: nome do vídeo (pasta em ``data/saida/partitura/video/``).

    Returns:
        Dicionário com os contadores ``total``, ``x`` e ``altura``, por método do par, e a
        lista ``inversoes``.
    """
    produto = json.loads((PASTA_PRODUTO / f"{stem}.json").read_text(encoding="utf-8"))
    doc = json.loads(
        (PASTA_PARTITURA / stem / f"{stem}.partitura.json").read_text(encoding="utf-8")
    )
    mapa = _notas_por_coluna(produto)
    por_metodo: dict[str, dict[str, int]] = collections.defaultdict(_contagem_zerada)
    # (tela, exibicao) -> lista de (compasso, t, coluna, t_ini, recorte)
    sequencias: dict[tuple[int, int], list[tuple[int, float, int, float, str]]] = (
        collections.defaultdict(list)
    )
    for pauta in doc["pautas"]:
        for evento in pauta["eventos"]:
            par = evento.get("par")
            if not par:
                por_metodo["sem_par"]["evento_sem_par"] += 1
                continue
            metodo = par.get("metodo", "desconhecido")
            cont = por_metodo[metodo]
            cont["eventos"] += 1
            tempos = _tempos_do_evento(par, mapa)
            if tempos is None:
                cont["par_sem_nota"] += 1
                continue
            com_tempo = False
            for exibicao, t_ini in sorted(tempos.items()):
                cont["pares_exibicao"] += 1
                if t_ini is None:
                    cont["par_sem_t_ini"] += 1
                    continue
                cont["par_com_tempo"] += 1
                com_tempo = True
                sequencias[(par["tela"], exibicao)].append(
                    (
                        int(evento["compasso"]),
                        float(evento["t"]),
                        par["coluna"],
                        float(t_ini),
                        pauta["recorte"],
                    )
                )
            cont["eventos_com_tempo"] += com_tempo
    inversoes = []
    for (tela, exibicao), lista in sorted(sequencias.items()):
        lista.sort(key=lambda item: (item[0], item[1]))
        for anterior, atual in itertools.pairwise(lista):
            if atual[2] == anterior[2]:
                continue  # acorde: mesma coluna, não é inversão
            if atual[3] < anterior[3]:
                inversoes.append(
                    {
                        "tela": tela,
                        "exibicao": exibicao,
                        "anterior": {
                            "compasso": anterior[0],
                            "t": anterior[1],
                            "coluna": anterior[2],
                            "t_ini": anterior[3],
                            "recorte": anterior[4],
                        },
                        "atual": {
                            "compasso": atual[0],
                            "t": atual[1],
                            "coluna": atual[2],
                            "t_ini": atual[3],
                            "recorte": atual[4],
                        },
                    }
                )
    total = _contagem_zerada()
    for cont in por_metodo.values():
        for chave in total:
            total[chave] += cont[chave]
    return {
        "video": stem,
        "total": total,
        "por_metodo": {m: dict(c) for m, c in sorted(por_metodo.items())},
        "inversoes": inversoes,
    }


def main(argv: list[str] | None = None) -> int:
    """Roda a F0.3 nos 3 vídeos e grava ``tempo.json`` na pasta da frente 0.

    Args:
        argv: argumentos da linha de comando (não há opções; aceito por padrão).

    Returns:
        Zero em caso de sucesso.
    """
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    videos = [_analisar_video(stem) for stem in STEMS]
    documento = {
        "frente": "F0.3",
        "rodada": 3103,
        "videos": videos,
    }
    SAIDA_JSON.parent.mkdir(parents=True, exist_ok=True)
    SAIDA_JSON.write_text(
        json.dumps(documento, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for v in videos:
        t = v["total"]
        print(
            f"{v['video'][:22]}: eventos {t['eventos']}, sem par {t['evento_sem_par']},"
            f" par sem nota {t['par_sem_nota']}, pares (evento, exibicao) {t['pares_exibicao']},"
            f" com tempo {t['par_com_tempo']}, sem t_ini {t['par_sem_t_ini']},"
            f" eventos com segundo {t['eventos_com_tempo']}, inversoes {len(v['inversoes'])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

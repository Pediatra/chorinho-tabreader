"""D1 da partitura: itens da conferência do dono, servidos na porta 8121 (rodada 3161).

Cópia de ``tab.partitura_gabarito._item_sem_produto`` e ``preparar_sem_produto``. A única
mudança é a pasta de origem: os recortes e as leituras são os de ``videos/<slug>/`` da pasta
da frente D, e não os do piloto em ``sem_produto/``. O resto do item é o mesmo, para o servidor
``partitura_gabarito servir`` aceitar o arquivo sem mudança.

Um item por vídeo sorteado, com o recorte escolhido por ``partitura_amostra_ler``
(``escolha_recortes.json``, estado ``lido``). Grava ``itens_d1.json`` e a cópia vazia do
gabarito (``ouro_d1_copia.json``) na pasta da frente. O gabarito real não é tocado.

Uso (dentro do container, na raiz do projeto)::

    python -m tab.partitura_amostra_itens
"""

from __future__ import annotations

import argparse
import json

from .caminhos import PART_FRENTE_D
from .partitura_gabarito import (
    CONDICAO_HERDADA,
    FONTE_HERDADA,
    _conferir_png,
    _montar_item,
    _relativo_a_raiz,
    gabarito_vazio,
)
from .video import _slug

ESCOLHA = PART_FRENTE_D / "escolha_recortes.json"
ITENS = PART_FRENTE_D / "itens_d1.json"
OURO_COPIA = PART_FRENTE_D / "ouro_d1_copia.json"
SEM_LEITURA = PART_FRENTE_D / "sem_leitura_d1.json"


def _item_frente(video: str, id_: str) -> dict:
    """Item de conferência de um recorte de vídeo sorteado (pasta da frente D).

    Args:
        video: ``canal/arquivo`` do vídeo.
        id_: id do recorte no índice (``P01a``).

    Returns:
        Item no formato de ``_item_sem_produto``, com ``pasta`` (relativa à raiz) e
        ``recorte``.

    Raises:
        ValueError: se o recorte não está no índice do vídeo, ou o PNG não bate com ele.
        FileNotFoundError: se o recorte não tem leitura herdada do Audiveris.
    """
    pasta = PART_FRENTE_D / "videos" / _slug(video)
    indice = json.loads(
        (pasta / "recortes" / "indice.json").read_text(encoding="utf-8")
    )
    casam = [e for e in indice if e.get("id") == id_]
    if not casam:
        raise ValueError(f"{video}: recorte {id_} não está em recortes/indice.json")
    entrada = casam[0]
    caminho = pasta / "omr" / "audiveris" / CONDICAO_HERDADA / id_ / "saida.musicxml"
    if not caminho.exists():
        raise FileNotFoundError(f"{video}:{id_}: sem leitura herdada em {caminho}")
    png = pasta / "recortes" / f"{id_}.png"
    largura, altura = _conferir_png(png, entrada)
    item = _montar_item(
        id_=f"{_slug(video)[:16]}_{id_}",
        origem="sem_produto",
        canal=video.split("/", 1)[0],
        video=video,
        tela=entrada["pagina"],
        fonte=FONTE_HERDADA,
        caminho=caminho,
        png=png,
        largura=largura,
        altura=altura,
        eventos_homr=None,
        referencia=None,
    )
    item["pasta"] = _relativo_a_raiz(pasta)
    item["recorte"] = id_
    return item


def main(argv: list[str] | None = None) -> int:
    """Gera os itens dos recortes lidos e a cópia vazia do gabarito.

    Args:
        argv: sem argumentos.

    Returns:
        Zero.
    """
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    escolhas = json.loads(ESCOLHA.read_text(encoding="utf-8"))
    itens = []
    sem_leitura = []
    for e in escolhas:
        pasta = PART_FRENTE_D / "videos" / _slug(e["video"])
        herdada = (
            pasta
            / "omr"
            / "audiveris"
            / CONDICAO_HERDADA
            / e["recorte"]
            / "saida.musicxml"
        )
        if e["estado"] != "lido" or not herdada.exists():
            sem_leitura.append({"video": e["video"], "recorte": e["recorte"]})
            continue
        itens.append(_item_frente(e["video"], e["recorte"]))
    ids = [it["id"] for it in itens]
    if len(set(ids)) != len(ids):
        raise ValueError(f"ids repetidos: {ids}")
    ITENS.write_text(
        json.dumps(
            {"formato": 1, "gerado_por": "tab.partitura_amostra_itens", "itens": itens},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    OURO_COPIA.write_text(
        json.dumps(gabarito_vazio(ITENS), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    SEM_LEITURA.write_text(
        json.dumps(sem_leitura, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"itens {len(itens)} de {len(escolhas)} escolhidos; sem leitura {len(sem_leitura)}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

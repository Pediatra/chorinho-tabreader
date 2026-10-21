"""Gera os pedidos da demo da folha: 4 colunas do MVP e 1 controle deslocado.

Os tempos vêm de ``passada2.fluxo.t_som`` do atraso MVP (telas 1, 5, 7 e 12, exibição 0,
coluna 5). O controle é a tela 7 com +0,33 s. O campo ``controle`` NÃO vai para a página:
o gerador de página ignora-o.
"""

import json
from pathlib import Path

RAIZ = Path("/var/home/gabriel/Projects/chorinho-dataset")
VIDEO = "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4"
ROTULO = "retrato brasileiro"
COLUNA = 5
EXIBICAO = 0
DESLOCAMENTO_CONTROLE_S = 0.33

atraso = json.loads((RAIZ / "data/saida/audio/a1/atraso_mvp.json").read_text("utf-8"))
mvp = json.loads((RAIZ / "data/saida/conserto_v2/mvp.json").read_text("utf-8"))


def evento(tela: int) -> dict:
    """Evento do atraso MVP da tela, coluna 5, exibição 0.

    Args:
        tela: número da tela.

    Returns:
        O evento correspondente.
    """
    return next(
        e
        for e in atraso["eventos"]
        if e["tela"] == tela and e["coluna"] == COLUNA and e["exibicao"] == EXIBICAO
    )


def pedido(id_: str, tela: int, t_audio: float, controle: bool) -> dict:
    """Pedido de clipe com painel, passo, x e notas lidos do MVP.

    Args:
        id_: id do pedido.
        tela: número da tela.
        t_audio: instante do clique, na linha do tempo do vídeo.
        controle: se é um pedido de controle (não vai para a página).

    Returns:
        O pedido.
    """
    tela_mvp = next(t for t in mvp["telas"] if t["id"] == tela)
    notas = [
        n
        for n in mvp["notas"]
        if n["tela"] == tela and n["coluna"] == COLUNA and n["exibicao"] == EXIBICAO
    ]
    x = sum(n["x_centro_quadro"] for n in notas) / len(notas)
    return {
        "id": id_,
        "video": VIDEO,
        "t_audio": round(t_audio, 6),
        "tela": tela,
        "coluna": COLUNA,
        "exibicao": EXIBICAO,
        "x_centro_quadro": round(x, 2),
        "painel": tela_mvp["painel"],
        "passo": tela_mvp["passo"],
        "rotulo": ROTULO,
        "notas": sorted([[n["corda"], n["casa"]] for n in notas]),
        "controle": controle,
    }


pedidos = []
for i, tela in enumerate([1, 5, 7, 12], start=1):
    pedidos.append(pedido(f"d{i}", tela, evento(tela)["passada2"]["fluxo"]["t_som"], False))
base = evento(7)["passada2"]["fluxo"]["t_som"]
pedidos.append(pedido("d5", 7, base + DESLOCAMENTO_CONTROLE_S, True))

# Ordem da página: o controle não fica ao lado do pedido original da tela 7.
pedidos = [pedidos[i] for i in (2, 0, 4, 3, 1)]

destino = RAIZ / "data/saida/audio/a2/folha/demo/pedidos.json"
destino.write_text(json.dumps(pedidos, ensure_ascii=False, indent=2), encoding="utf-8")
for p in pedidos:
    print(p["id"], p["tela"], p["t_audio"], p["x_centro_quadro"], p["passo"], p["notas"], p["controle"])

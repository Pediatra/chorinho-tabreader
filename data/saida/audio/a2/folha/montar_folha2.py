"""Monta a FOLHA 2 (roda no container, PYTHONPATH=/app). Semente 2002.

- iwaki, kimny e shin izumi: 9 colunas afirmadas cada (alinhado v2 em produtos/), espalhadas
  pelo vídeo (sortear_espalhado), sem as colunas que já estão na folha 1 (gold folha1.json);
- 1 controle por vídeo: par (c, c+1) consecutivo afirmado, t(c+1)-t(c) >= 0,40 s, clique no
  ponto médio, sem pico de fluxo a menos de 80 ms; a coluna não aparece em outro clipe;
- 30 clipes, embaralhados com a semente, ids g01..g30.

Saídas FORA da pasta servida: folha/folha2_pedidos.json e folha/folha2_chave.json.
O gabarito folha1.json é só lido.
"""

import json
import random
from collections import Counter
from pathlib import Path

from tab import audio_folha as af

RAIZ = Path("/app")
A2 = RAIZ / "data/saida/audio/a2"
FOLHA = A2 / "folha"
SEMENTE = 2002
POR_VIDEO = 9
APELIDOS = {
    "iwaki": "la vie en rose",
    "kimny": "from this place",
    "shin": "room 335",
}
PRODUTOS = {
    "iwaki": "iwaki_la_vie_en_rose",
    "kimny": "kimny_from_this_place",
    "shin": "shin_izumi_room_335",
}

gold = json.loads((RAIZ / "data/gold/audio/folha1.json").read_text("utf-8"))
ja_na_folha1 = {
    (af.PREFIXO_ACERVO + i["video"], i["tela"], i["exibicao"], i["coluna"])
    for i in gold["itens"]
}
colunas_folha1_tc = {
    (af.PREFIXO_ACERVO + i["video"], i["tela"], i["coluna"]) for i in gold["itens"]
}
rng = random.Random(SEMENTE)
entradas: list[dict] = []
resumo: dict = {}

for apelido in ("iwaki", "kimny", "shin"):
    alin = af.ler_alinhamento(str(A2 / f"produtos/alinhado_{PRODUTOS[apelido]}.json"))
    prod = json.loads(
        (A2 / f"produtos/{PRODUTOS[apelido]}.json").read_text("utf-8")
    )
    video = alin["video"]["arquivo"]
    assert video == af.PREFIXO_ACERVO + prod["video"]["arquivo"]

    # 1) controle: pares consecutivos sobre TODAS as colunas (inclui recusadas, que bloqueiam)
    por_exib: dict[tuple[int, int], list[dict]] = {}
    for c in alin["colunas"]:
        por_exib.setdefault((c["tela"], c["exibicao"]), []).append(c)
    pares = []
    for chave in sorted(por_exib):
        colunas = sorted(por_exib[chave], key=lambda c: c["coluna"])
        pares += af.pares_vizinhos_validos(colunas)
    pares = [
        (a, b)
        for a, b in pares
        if (video, a["tela"], a["exibicao"], a["coluna"]) not in ja_na_folha1
        and (video, a["tela"], a["coluna"]) not in colunas_folha1_tc
        and (video, b["tela"], b["coluna"]) not in colunas_folha1_tc
    ]
    audio = af.carregar_audio(video)
    escolha = af.escolher_controle(pares, audio, rng, proibidas=set())
    assert escolha is not None, f"sem controle válido em {apelido}"
    a, b = escolha["a"], escolha["b"]
    controle_tc = {(a["tela"], a["coluna"]), (b["tela"], b["coluna"])}

    # 2) afirmadas para o sorteio: sem as da folha 1 e sem as colunas do controle
    itens = [
        it
        for it in af.itens_afirmados(alin)
        if (video, it["tela"], it["exibicao"], it["coluna"]) not in ja_na_folha1
        and (it["tela"], it["coluna"]) not in controle_tc
    ]
    amostra = af.sortear_espalhado(itens, POR_VIDEO, rng)
    assert len(amostra) == POR_VIDEO, (apelido, len(amostra))
    assert len({(i["tela"], i["exibicao"], i["coluna"]) for i in amostra}) == POR_VIDEO

    for it in amostra:
        p = af._pedido_do_item(it, prod, 0)
        p["rotulo"] = APELIDOS[apelido]
        entradas.append(
            {**p, "categoria": f"{apelido}/afirmada_espalhada", "controle": False,
             "distancia_pico_s": None}
        )

    item_c = {**a, "video": video, "t_audio": round(escolha["clique"], 6)}
    p = af._pedido_do_item(item_c, prod, 0)
    p["rotulo"] = APELIDOS[apelido]
    entradas.append(
        {**p, "categoria": f"{apelido}/controle", "controle": True,
         "t_audio_original": a["t_audio"], "t_audio_c1": b["t_audio"],
         "distancia_pico_s": round(escolha["distancia_pico_s"], 4)}
    )
    resumo[apelido] = {
        "pares_candidatos": len(pares),
        "afirmadas_disponiveis": len(itens),
        "controle": {
            "tela": a["tela"], "exibicao": a["exibicao"], "coluna": a["coluna"],
            "t_c": a["t_audio"], "t_c1": b["t_audio"], "clique": escolha["clique"],
            "distancia_pico_s": escolha["distancia_pico_s"],
        },
    }

entradas.sort(key=lambda e: (e["categoria"], e["video"], e["tela"], e["coluna"]))
random.Random(SEMENTE).shuffle(entradas)
for n, e in enumerate(entradas, start=1):
    e["id"] = f"g{n:02d}"

(FOLHA / "folha2_pedidos.json").write_text(
    json.dumps(entradas, ensure_ascii=False, indent=2), encoding="utf-8"
)
chave = [
    {
        "id": e["id"],
        "categoria": e["categoria"],
        "controle": e["controle"],
        "video": e["rotulo"],
        "tela": e["tela"],
        "coluna": e["coluna"],
        "exibicao": e["exibicao"],
        "t_audio": e["t_audio"],
        "t_audio_original": e.get("t_audio_original"),
        "t_audio_c1": e.get("t_audio_c1"),
        "distancia_pico_s": e["distancia_pico_s"],
    }
    for e in entradas
]
(FOLHA / "folha2_chave.json").write_text(
    json.dumps(chave, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(resumo, ensure_ascii=False, indent=1, default=float))
print("clipes:", len(entradas), dict(Counter(e["categoria"] for e in entradas)))

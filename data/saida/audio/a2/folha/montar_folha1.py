"""Monta a FOLHA 1: pedidos, chave e categorias (roda no container, com PYTHONPATH=/app).

Composição (semente 2001):
- MVP: 4 afirmadas que concordam com a régua (<= 50 ms do ataque de fluxo), 4 afirmadas
  sem par na régua (sorteadas entre as que não têm par), as 3 falsas (> 200 ms dos dois
  ataques da régua) e a coluna 25 da tela 12, exibição 0;
- iwaki, kimny e shin izumi: 4 afirmadas sorteadas de cada, estratificadas por exibição;
- 2 controles errados (iwaki e kimny): coluna afirmada que não está em nenhum outro clipe,
  com t_audio + 0,5 x T_usado da sua exibição.

Saídas (FORA da pasta servida, que só pode ter index.html e .mp4):
- folha/folha1_pedidos.json (pedidos com categoria e controle);
- folha/folha1_chave.json (id -> categoria, t_audio, t_som da régua, controle).
"""

import json
import random
from pathlib import Path

from tab import audio_folha as af
from tab.audio_alinhar_avaliar import ler_regua

RAIZ = Path("/app")
A2 = RAIZ / "data/saida/audio/a2"
FOLHA = A2 / "folha"
SEMENTE = 2001
POR_VIDEO = 4
TAG_CONCORDA = 0.050
TAG_FALSA = 0.200
COLUNA_CASO = (12, 0, 25)

APELIDOS = {
    "mvp": "retrato",
    "iwaki": "la vie en rose",
    "shin": "room 335",
    "kimny": "from this place",
}

regua, _ = ler_regua(str(RAIZ / "data/saida/audio/a1/atraso_mvp.json"))

prod_mvp = json.loads((RAIZ / "data/saida/conserto_v2/mvp.json").read_text("utf-8"))
alin_mvp = af.ler_alinhamento(str(A2 / "alinhado_v2_r1.json"))
assert alin_mvp["video"]["arquivo"] == af.PREFIXO_ACERVO + prod_mvp["video"]["arquivo"]
video_mvp = alin_mvp["video"]["arquivo"]

classes = {"concorda": [], "sem_par": [], "falsa": [], "outro": []}
caso = None
for item in af.itens_afirmados(alin_mvp):
    chave = (item["tela"], item["exibicao"], item["coluna"])
    t = item["t_audio"]
    if (item["tela"], item["exibicao"], item["coluna"]) == COLUNA_CASO:
        caso = item
    if chave not in regua:
        classes["sem_par"].append(item)
        continue
    ref = regua[chave]
    refs = [r for r in (ref["fluxo"], ref["alturas"]) if r is not None]
    if not refs:
        classes["outro"].append(item)
        continue
    if ref["fluxo"] is not None and abs(t - ref["fluxo"]) <= TAG_CONCORDA:
        classes["concorda"].append(item)
    elif min(abs(t - r) for r in refs) > TAG_FALSA:
        classes["falsa"].append(item)
    else:
        classes["outro"].append(item)

assert caso is not None, "coluna 25 da tela 12 exib 0 não está afirmada"
print("MVP categorias:", {k: len(v) for k, v in classes.items()}, "caso t12c25 t_audio", caso["t_audio"])

rng = random.Random(SEMENTE)


def ordenar(lista: list[dict]) -> list[dict]:
    """Ordem canônica (tela, exibição, coluna) antes de sortear."""
    return sorted(lista, key=lambda i: (i["tela"], i["exibicao"], i["coluna"]))


def tirar(lista: list[dict], n: int) -> list[dict]:
    """Sorteia ``n`` itens sem reposição com o rng da folha."""
    pool = ordenar(lista)
    return [pool.pop(rng.randrange(len(pool))) for _ in range(n)]


concorda = tirar(classes["concorda"], 4)
sem_par = tirar(classes["sem_par"], 4)
falsas = ordenar(classes["falsa"])
assert len(falsas) == 3, len(falsas)

entradas: list[dict] = []
for item, cat in (
    *[(i, "mvp/concorda_regua") for i in concorda],
    *[(i, "mvp/sem_par_regua") for i in sem_par],
    *[(i, "mvp/falsa_regua") for i in falsas],
    (caso, "mvp/caso_t12c25"),
):
    p = af._pedido_do_item(item, prod_mvp, 0)
    p["rotulo"] = APELIDOS["mvp"]
    t_som = regua.get((item["tela"], item["exibicao"], item["coluna"]), {})
    entradas.append(
        {
            **p,
            "categoria": cat,
            "controle": False,
            "t_som_fluxo": t_som.get("fluxo"),
            "t_som_alturas": t_som.get("alturas"),
        }
    )

# Clipes do MVP usados; os demais vídeos entram por sorteio da própria ferramenta.
usados = {(e["video"], e["tela"], e["exibicao"], e["coluna"]) for e in entradas}
mais: list[dict] = []
produtos = {video_mvp: prod_mvp}
for apelido, arq_alin, arq_prod in (
    ("iwaki", "produtos/alinhado_iwaki_la_vie_en_rose.json", "produtos/iwaki_la_vie_en_rose.json"),
    ("kimny", "produtos/alinhado_kimny_from_this_place.json", "produtos/kimny_from_this_place.json"),
    ("shin", "produtos/alinhado_shin_izumi_room_335.json", "produtos/shin_izumi_room_335.json"),
):
    alin = af.ler_alinhamento(str(A2 / arq_alin))
    prod = json.loads((A2 / arq_prod).read_text("utf-8"))
    video = alin["video"]["arquivo"]
    assert video == af.PREFIXO_ACERVO + prod["video"]["arquivo"]
    produtos[video] = prod
    itens = af.itens_afirmados(alin)
    pedidos = af.sortear_pedidos(itens, {video: prod}, POR_VIDEO, SEMENTE)
    for p in pedidos:
        p["rotulo"] = APELIDOS[apelido]
        mais.append({**p, "categoria": f"{apelido}/afirmada_sorteada", "controle": False,
                     "t_som_fluxo": None, "t_som_alturas": None})
    if apelido in ("iwaki", "kimny"):
        ocupados = {(e["video"], e["tela"], e["coluna"]) for e in mais} | {
            (u[0], u[1], u[3]) for u in usados
        }
        candidatos = [
            i for i in ordenar(itens)
            if i["T_usado_s"] is not None and (video, i["tela"], i["coluna"]) not in ocupados
        ]
        escolhido = candidatos[rng.randrange(len(candidatos))]
        t_orig = escolhido["t_audio"]
        t_novo = round(t_orig + 0.5 * escolhido["T_usado_s"], 6)
        p = af._pedido_do_item({**escolhido, "t_audio": t_novo}, prod, 0)
        p["rotulo"] = APELIDOS[apelido]
        mais.append({**p, "categoria": f"{apelido}/controle_errado", "controle": True,
                     "t_audio_original": t_orig, "t_som_fluxo": None, "t_som_alturas": None})

entradas += mais
# Ordem: canônica por categoria e id depois do embaralhamento com a semente.
entradas.sort(key=lambda e: (e["categoria"], e["video"], e["tela"], e["coluna"]))
random.Random(SEMENTE).shuffle(entradas)
for n, e in enumerate(entradas, start=1):
    e["id"] = f"f{n:02d}"

(FOLHA / "folha1_pedidos.json").write_text(
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
        "t_som_fluxo": e["t_som_fluxo"],
        "t_som_alturas": e["t_som_alturas"],
    }
    for e in entradas
]
(FOLHA / "folha1_chave.json").write_text(
    json.dumps(chave, ensure_ascii=False, indent=2), encoding="utf-8"
)
from collections import Counter  # noqa: E402

print("clipes:", len(entradas), dict(Counter(e["categoria"] for e in entradas)))

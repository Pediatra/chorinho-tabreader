"""Escolhe os videos do lote 2 da rodada A4 a partir do censo (leitura).

Grava lista.json (caminhos relativos ao acervo) e apelidos.json (apelido -> caminho).
"""

import json
import random
import re
import unicodedata
from pathlib import Path

RAIZ = Path("/var/home/gabriel/Projects/chorinho-dataset")
L = RAIZ / "data/saida/audio/a4/lote2"
CENSO = RAIZ / "data/saida/censo/censo_cache.jsonl"

CANAIS = [
    "leonardo ramos",
    "robert lunn",
    "serge kottelat",
    "kenneth acoustic",
    "mr. tabs",
    "guitar dell ́arte",
    "sky guitar",
    "tv on guitar",
    "lonelypicker",
    "violaodecria",
    "yunus guitarist",
    "vvxofingerstyletab",
]

PROIBIDOS_CANAIS = {
    "raman korshun",
    "iwaki",
    "kimny's guitar",
    "shin izumi",
    "transcriptor",
    "guitarous",
    "paolo d'angelo",
}


def ascii_slug(texto):
    """Converte texto em slug ascii curto, com underscores."""
    norm = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    palavras = re.findall(r"[a-z0-9]+", norm.lower())
    return "_".join(palavras)


def candidatos(rows, canal):
    """Candidatos do canal, ordenados por arquivo, pelo filtro da rodada."""
    lista = []
    for r in rows:
        if r.get("canal") != canal:
            continue
        arq = r.get("arquivo", "")
        if "campanitas" in arq.lower():
            continue
        if r.get("tablatura") is not True:
            continue
        if (r.get("frac_tablatura") or 0) < 0.8:
            continue
        dur = (r.get("info") or {}).get("duracao_s")
        if dur is None or not (60 <= dur <= 360):
            continue
        if r.get("forma") != "paginado":
            continue
        if r.get("marcador") not in ("faixa", "cor"):
            continue
        lista.append(r)
    return sorted(lista, key=lambda r: r["arquivo"])


def main():
    """Sorteia um video por canal e grava lista.json e apelidos.json."""
    rows = [json.loads(linha) for linha in CENSO.read_text("utf-8").splitlines() if linha.strip()]
    rng = random.Random(2015)
    escolhidos = []
    sem_candidato = []
    for canal in CANAIS:
        if any(p in canal for p in PROIBIDOS_CANAIS):
            raise SystemExit(f"canal proibido: {canal}")
        cand = candidatos(rows, canal)
        if not cand:
            sem_candidato.append(canal)
            continue
        escolha = rng.choice(cand)
        escolhidos.append((canal, escolha["arquivo"], len(cand)))

    lista = [arq for _, arq, _ in escolhidos]
    apelidos = {}
    for canal, arq, _ in escolhidos:
        nome = arq.split("/", 1)[1].rsplit(".mp4", 1)[0]
        palavras = ascii_slug(nome).split("_")[:3]
        base = ascii_slug(canal) + "_" + "_".join(palavras)
        apelido = base
        n = 2
        while apelido in apelidos:
            apelido = f"{base}_{n}"
            n += 1
        apelidos[apelido] = arq

    (L / "lista.json").write_text(json.dumps(lista, ensure_ascii=False, indent=1) + "\n", "utf-8")
    (L / "apelidos.json").write_text(json.dumps(apelidos, ensure_ascii=False, indent=2) + "\n", "utf-8")
    for canal, arq, n in escolhidos:
        print(f"{canal} ({n} candidatos) -> {arq}")
    print("sem candidato:", sem_candidato)


if __name__ == "__main__":
    main()

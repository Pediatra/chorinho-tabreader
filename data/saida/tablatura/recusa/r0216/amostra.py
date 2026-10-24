"""Amostra da prova lacrada da rodada 0216 (recusa do painel), emenda 1.

Lê o censo_cache (emenda 1; antes era o censo v2), exclui canais fora do rollout e vídeos já usados, e sorteia até
30 vídeos com no máximo 3 por canal. Grava amostra.json e lista.tsv nesta pasta.
"""

from __future__ import annotations

import json
import random
import sys
import unicodedata
from collections import Counter
from pathlib import Path

from tab.comum.acervo import canais_fora, ler_rollout
from tab.comum.arquivos import gravar_atomico, slug

RAIZ = Path("/var/home/gabriel/Projects/chorinho-dataset")
SAIDA = RAIZ / "data/saida/tablatura/recusa/r0216"
CENSO = RAIZ / "data/saida/tablatura/censo/censo_cache.jsonl"
CENSO_V2 = RAIZ / "data/saida/tablatura/censo/censo_v2.jsonl"
LISTA_R2021 = RAIZ / "data/saida/audio/r2021/lista.tsv"
PRODUTOS_R2017 = RAIZ / "data/saida/audio/r2017/produtos"
OURO = RAIZ / "data/gold/ouro_video"
T8 = [
    RAIZ / f"data/saida/tablatura/t8{n}/ferramenta/indice.json" for n in (2, 3, 4, 5, 6)
]
DESCARTADOS = {"raman korshun", "campanitas"}
N_ALVO = 30
TETO_CANAL = 3
SEMENTE = 16


def nfc(texto: str) -> str:
    """Normaliza um caminho para NFC, para comparar.

    Args:
        texto: caminho relativo ao acervo.

    Returns:
        O mesmo texto em NFC.
    """
    return unicodedata.normalize("NFC", texto)


def usados() -> dict[str, str]:
    """Vídeos já usados, com o motivo de cada um.

    Returns:
        Caminho NFC -> nome da fonte que já o usou.
    """
    usado: dict[str, str] = {}
    for linha in LISTA_R2021.read_text(encoding="utf-8").splitlines():
        partes = linha.split("\t")
        if len(partes) >= 2 and partes[1]:
            usado.setdefault(nfc(partes[1]), "r2021")
    for caminho in sorted(PRODUTOS_R2017.glob("*.json")):
        dado = json.loads(caminho.read_text(encoding="utf-8"))
        video = dado.get("video")
        arq = video.get("arquivo") if isinstance(video, dict) else video
        if arq:
            usado.setdefault(nfc(arq), "r2017")
    for caminho in sorted(OURO.glob("*.json")):
        dado = json.loads(caminho.read_text(encoding="utf-8"))
        video = dado.get("video")
        arq = video.get("arquivo") if isinstance(video, dict) else video
        if arq:
            usado.setdefault(nfc(arq), "ouro_video")
    for caminho in T8:
        for item in json.loads(caminho.read_text(encoding="utf-8")):
            if item.get("video"):
                usado.setdefault(nfc(item["video"]), caminho.parent.parent.name)
    return usado


def main() -> None:
    """Monta a amostra e grava amostra.json e lista.tsv."""
    valores = Counter()
    linhas = []
    for linha in CENSO.read_text(encoding="utf-8").splitlines():
        if linha.strip():
            d = json.loads(linha)
            valores[repr(d.get("tablatura"))] += 1
            linhas.append(d)
    print("valores distintos de 'tablatura':", dict(valores))
    if any(not isinstance(d.get("tablatura"), bool) for d in linhas):
        sys.exit("campo 'tablatura' nao e bool: parar")

    fora = canais_fora(ler_rollout(RAIZ / "configs/canais.yaml"))
    usado = usados()
    sem_tab_v2 = set()
    for linha in CENSO_V2.read_text(encoding="utf-8").splitlines():
        if linha.strip():
            d2 = json.loads(linha)
            if d2.get("canal") == "cifra club" and d2.get("tablatura") is False:
                sem_tab_v2.add(nfc(d2["arquivo"]))
    motivos: Counter = Counter()
    candidatos = []
    for d in linhas:
        if not d["tablatura"]:
            motivos["sem_tablatura"] += 1
            continue
        canal = d["canal"]
        arq = d["arquivo"]
        if canal in fora:
            motivos["rollout_fora"] += 1
            continue
        if canal in DESCARTADOS:
            motivos["canal_descartado"] += 1
            continue
        if canal == "cifra club" and nfc(arq) in sem_tab_v2:
            motivos["cifra_club_sem_tab_censo_v2"] += 1
            continue
        fonte = usado.get(nfc(arq))
        if fonte:
            motivos[f"ja_usado_{fonte}"] += 1
            continue
        candidatos.append(d)

    candidatos.sort(key=lambda d: d["arquivo"])
    rng = random.Random(SEMENTE)
    rng.shuffle(candidatos)
    escolhidos = []
    por_canal: Counter = Counter()
    pulados_teto = 0
    for d in candidatos:
        if len(escolhidos) >= N_ALVO:
            break
        if por_canal[d["canal"]] >= TETO_CANAL:
            pulados_teto += 1
            continue
        por_canal[d["canal"]] += 1
        escolhidos.append(d)

    amostra = {
        "linhas_censo": len(linhas),
        "valores_tablatura": dict(valores),
        "canais_fora_rollout": sorted(fora),
        "excluidos_por_motivo": dict(motivos),
        "candidatos": len(candidatos),
        "pulados_pelo_teto_por_canal": pulados_teto,
        "alvo": N_ALVO,
        "teto_por_canal": TETO_CANAL,
        "semente": SEMENTE,
        "amostrados": len(escolhidos),
        "por_canal": dict(por_canal),
        "videos": [
            {
                "nome": slug(d["arquivo"])[:60],
                "arquivo": d["arquivo"],
                "canal": d["canal"],
            }
            for d in escolhidos
        ],
    }
    gravar_atomico(SAIDA / "amostra.json", amostra)
    tsv = "".join(f"{v['nome']}\t{v['arquivo']}\n" for v in amostra["videos"])
    (SAIDA / "lista.tsv").write_text(tsv, encoding="utf-8")
    print(
        json.dumps(
            {k: v for k, v in amostra.items() if k != "videos"}, ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()

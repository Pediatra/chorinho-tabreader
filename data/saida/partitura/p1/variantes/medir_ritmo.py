"""Diagnostico (fora do gate): preenchimento de compasso, sem gabarito de ritmo.

Para cada condicao e recorte R01-R12, le o MusicXML com ``tab.partitura_gabarito.ler_partitura``.
Em cada compasso (sem o primeiro e o ultimo do recorte), para cada voz, soma-se a duracao
das notas e pausas que nao sao acorde nem graca. O compasso esta cheio se todas as vozes
somam a duracao esperada: beats * 4 / beat_type (em semineiras). Sem formula lida, usa-se a
do video (pablo rome 3/4, dell'arte 2/4, robert lunn 3/4).

Executar dentro do container base, com PYTHONPATH=/app:
    python /app/data/saida/partitura/p1/variantes/medir_ritmo.py
Grava ``variantes/resultado.json``.
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from tab.partitura_gabarito import ler_partitura

PASTA = Path("/app/data/saida/partitura/p1")
IDS = [f"R{n:02d}" for n in range(1, 13)]
CONDICOES = [
    ("homr", "nativo"),
    ("homr", "x2"),
    ("audiveris", "nativo"),
    ("audiveris", "x2"),
    ("audiveris", "x3"),
    ("audiveris", "x4"),
    ("audiveris", "x2_binaria"),
    ("audiveris", "x2_margem"),
    ("audiveris", "x2_cabecalho"),
]
FORMULA_PADRAO = [("pablo", (3, 4)), ("guitar dell", (2, 4)), ("robert lunn", (3, 4))]


def formula_padrao(canal: str) -> tuple[int, int]:
    """Fórmula do vídeo quando o recorte não traz a sua.

    Args:
        canal: nome do canal (início do campo ``canal`` do índice).

    Returns:
        ``(beats, beat_type)`` do vídeo.

    Raises:
        ValueError: se o canal não está na tabela.
    """
    for prefixo, formula in FORMULA_PADRAO:
        if canal.lower().startswith(prefixo):
            return formula
    raise ValueError(f"sem fórmula padrão para o canal {canal}")


def avaliar_recorte(caminho: Path, canal: str) -> dict:
    """Conta compassos cheios de um MusicXML.

    Args:
        caminho: ``saida.musicxml`` do recorte.
        canal: canal do recorte (para a fórmula padrão).

    Returns:
        Dict com ``compassos_avaliados``, ``cheios``, ``formula``, ``fonte_formula``,
        ``partes`` e ``vozes_por_compasso`` (só para conferência).
    """
    lido = ler_partitura(caminho)
    formula = lido["compasso_formula"]
    if formula and formula.get("beats") and formula.get("beat_type"):
        beats, beat_type = int(formula["beats"]), int(formula["beat_type"])
        fonte = "musicxml"
    else:
        beats, beat_type = formula_padrao(canal)
        fonte = "video"
    esperado = beats * 4 / beat_type
    compassos = lido["compassos"][1:-1]
    cheios = 0
    detalhes = []
    for compasso in compassos:
        somas: dict[str, float] = defaultdict(float)
        for simbolo in compasso["simbolos"]:
            if simbolo["acorde"] or simbolo["graca"]:
                continue
            somas[simbolo["voz"]] += simbolo["duracao"]
        cheio = bool(somas) and all(
            abs(soma - esperado) < 1e-3 for soma in somas.values()
        )
        cheios += cheio
        detalhes.append({"numero": compasso["numero"], "cheio": cheio,
                         "somas": {v: round(s, 3) for v, s in somas.items()}})
    return {
        "compassos_avaliados": len(compassos),
        "cheios": cheios,
        "formula": f"{beats}/{beat_type}",
        "fonte_formula": fonte,
        "partes": lido["partes"],
        "compassos": detalhes,
    }


def main() -> None:
    """Roda a medida em todas as condições e grava ``variantes/resultado.json``."""
    indice = {i["id"]: i for i in json.loads(
        (PASTA / "recortes/indice.json").read_text(encoding="utf-8")) if i.get("id")}
    resultado = {"gerado_em": datetime.now().isoformat(timespec="seconds"),
                 "ids": IDS, "regra": "compasso cheio = todas as vozes somam beats*4/beat_type",
                 "condicoes": {}}
    for biblioteca, condicao in CONDICOES:
        chave = f"{biblioteca}/{condicao}"
        pasta = PASTA / "omr" / biblioteca / condicao
        execucao = {r["id"]: r for r in json.loads(
            (pasta / "execucao.json").read_text(encoding="utf-8"))}
        por_id: dict[str, dict] = {}
        sem_saida = []
        for id_ in IDS:
            reg = execucao.get(id_)
            if reg is None or not reg["ok"]:
                sem_saida.append(id_)
                continue
            por_id[id_] = avaliar_recorte(PASTA.parent.parent.parent / reg["saida"]
                                          if False else Path("/app") / reg["saida"],
                                          indice[id_]["canal"])
        total_av = sum(v["compassos_avaliados"] for v in por_id.values())
        total_ch = sum(v["cheios"] for v in por_id.values())
        video: dict[str, dict] = defaultdict(lambda: {"avaliados": 0, "cheios": 0})
        for id_, v in por_id.items():
            rotulo = indice[id_]["canal"].split("/")[0][:14]
            video[rotulo]["avaliados"] += v["compassos_avaliados"]
            video[rotulo]["cheios"] += v["cheios"]
        resultado["condicoes"][chave] = {
            "total": {"avaliados": total_av, "cheios": total_ch},
            "por_video": dict(video),
            "sem_saida": sem_saida,
            "por_recorte": {k: {x: y for x, y in v.items() if x != "compassos"}
                            for k, v in por_id.items()},
        }
        print(chave, f"{total_ch}/{total_av} compassos cheios", flush=True)
    (PASTA / "variantes/resultado.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

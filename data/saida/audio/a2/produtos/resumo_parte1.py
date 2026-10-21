"""Resumo dos 3 produtos da Parte 1 (leitura apenas; compara com o gabarito não conferido)."""

import json
import re
from pathlib import Path

RAIZ = Path("/var/home/gabriel/Projects/chorinho-dataset")
PRODUTOS = RAIZ / "data/saida/audio/a2/produtos"
OURO = RAIZ / "data/gold/ouro_video"
VIDEOS = {
    "iwaki_la_vie_en_rose": "la_vie_en_rose_edith_piaf_tab.json",
    "shin_izumi_room_335": "tabroom_335_larry_carlton_fingerstyle_guitar.json",
    "kimny_from_this_place": "tab_from_this_place_pat_metheny_fingerstyle_guitar_cover.json",
}


def chaves(obj, acc):
    """Coleta chaves e valores de texto que mencionam afinação ou capotraste.

    Args:
        obj: objeto JSON.
        acc: lista onde os achados entram.

    Returns:
        A lista ``acc``.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            if re.search(r"afin|capo|tuning|tune", k, re.I):
                acc.append(f"chave:{k}={str(v)[:60]}")
            chaves(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            chaves(v, acc)
    elif isinstance(obj, str) and re.search(r"capo|afinac|afinaç", obj, re.I):
        acc.append(f"texto:{obj[:60]}")
    return acc


for apelido, ouro_nome in VIDEOS.items():
    d = json.loads((PRODUTOS / f"{apelido}.json").read_text("utf-8"))
    g = json.loads((OURO / ouro_nome).read_text("utf-8"))
    notas = d["notas"]
    colunas = {(n["tela"], n["coluna"]) for n in notas}
    com_t = [n for n in notas if n.get("t_ini") is not None]
    exib_none = sum(1 for n in notas if n.get("exibicao") is None)
    ouro_notas = sum(len(t.get("notas", [])) for t in g["telas"])
    print(f"== {apelido}")
    print(f"  duracao_s={d['video']['duracao_s']} codec={d['video']['codec']}")
    print(
        f"  telas={len(d['telas'])} exibicoes={d['resumo']['exibicoes']} "
        f"colunas_distintas={len(colunas)} notas={len(notas)} "
        f"notas_com_t_ini={len(com_t)} instantes_distintos={len({n['t_ini'] for n in com_t})}"
    )
    print(
        f"  maior_casa={max(n['casa'] for n in notas)} "
        f"exibicao_None={exib_none} nao_notas={len(d['nao_notas'])}"
    )
    print(
        f"  gabarito_ouro (nao conferido): telas={len(g['telas'])} notas={ouro_notas}"
    )
    achados = chaves(d, []) + chaves(d.get("gerado_por", {}), [])
    print(f"  afinacao/capotraste no produto: {achados if achados else 'nenhum'}")

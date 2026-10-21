"""Diagnostico (fora do gate): tabela final da rodada p1, so R01-R12.

Le ``omr/avaliacao.json`` (altura), ``omr/<lib>/<cond>/execucao.json`` (tempo, falhas) e
``variantes/resultado.json`` (ritmo). Grava ``variantes/tabela.json`` e imprime as tabelas.
"""

import json
from pathlib import Path

PASTA = Path("/var/home/gabriel/Projects/chorinho-dataset/data/saida/partitura/p1")
IDS = {f"R{n:02d}" for n in range(1, 13)}
COMBOS = [
    "audiveris/x2",
    "homr/nativo",
    "homr/x2",
    "audiveris/nativo",
    "audiveris/x3",
    "audiveris/x4",
    "audiveris/x2_binaria",
    "audiveris/x2_margem",
    "audiveris/x2_cabecalho",
]
GRUPOS = {"greensleeves": "pablo romé", "south american": "dell'arte", "gymnopédie": "robert lunn", "pablo romé": "pablo romé", "guitar dell": "dell'arte", "robert lunn": "robert lunn"}


def grupo_do_video(rotulo: str) -> str:
    """Nome do grupo (vídeo) a partir do rótulo curto da avaliação."""
    for chave, nome in GRUPOS.items():
        if rotulo.lower().startswith(chave):
            return nome
    return rotulo


def main() -> None:
    """Monta e imprime as tabelas."""
    aval = json.loads((PASTA / "omr/avaliacao.json").read_text(encoding="utf-8"))
    ritmo = json.loads((PASTA / "variantes/resultado.json").read_text(encoding="utf-8"))
    tabela: dict = {"total": {}, "por_video": {}}
    linhas = []
    for combo in COMBOS:
        if combo not in aval["combinacoes"]:
            continue
        lib, cond = combo.split("/")
        bloco = aval["combinacoes"][combo]
        exato = bloco["exato"]["total"]
        classe = bloco["classe"]["total"]
        ids_ref = set(bloco["exato"]["por_recorte"])
        assert ids_ref <= IDS, ids_ref - IDS
        execucao = {r["id"]: r for r in json.loads(
            (PASTA / f"omr/{lib}/{cond}/execucao.json").read_text(encoding="utf-8"))}
        ids12 = sorted(IDS)
        falhas = [i for i in ids12 if not execucao[i]["ok"]]
        tempo = sum(execucao[i]["segundos"] for i in ids12) / len(ids12)
        rit = ritmo["condicoes"].get(combo, {}).get("total", {})
        linha = {
            "combo": combo,
            "certas_exato": exato["certas"], "referencia": exato["referencia"],
            "altura_errada": exato["altura_errada"], "faltando": exato["faltando"],
            "inventada": exato["inventada"],
            "certas_classe": classe["certas"], "referencia_classe": classe["referencia"],
            "compassos_cheios": rit.get("cheios"), "compassos_avaliados": rit.get("avaliados"),
            "falhas": falhas, "tempo_medio_s": round(tempo, 1),
        }
        tabela["total"][combo] = linha
        linhas.append(linha)
        por_video = {}
        for rotulo, cont in bloco["exato"]["por_video"].items():
            por_video.setdefault(grupo_do_video(rotulo), {"certas": 0, "referencia": 0,
                                 "altura_errada": 0, "faltando": 0, "inventada": 0})
            for k in ("certas", "referencia", "altura_errada", "faltando", "inventada"):
                por_video[grupo_do_video(rotulo)][k] += cont[k]
        rit_v = ritmo["condicoes"].get(combo, {}).get("por_video", {})
        for g, v in por_video.items():
            ch = {}
            for k, val in rit_v.items():
                if grupo_do_video(k) == g:
                    ch = val
            v["compassos_cheios"] = ch.get("cheios")
            v["compassos_avaliados"] = ch.get("avaliados")
        tabela["por_video"][combo] = por_video
    (PASTA / "variantes/tabela.json").write_text(
        json.dumps(tabela, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("| combinação | certas (exato) | altura errada | faltando | inventada | "
          "certas (classe) | compassos cheios | falhas | s/recorte |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for l in linhas:
        print(f"| {l['combo']} | {l['certas_exato']}/{l['referencia']} | {l['altura_errada']} | "
              f"{l['faltando']} | {l['inventada']} | {l['certas_classe']}/{l['referencia_classe']} | "
              f"{l['compassos_cheios']}/{l['compassos_avaliados']} | {len(l['falhas'])} "
              f"{l['falhas'] if l['falhas'] else ''} | {l['tempo_medio_s']} |")
    for combo, por in tabela["por_video"].items():
        print(f"\n{combo}")
        for g, v in por.items():
            print(f"  {g}: certas {v['certas']}/{v['referencia']}, errada {v['altura_errada']}, "
                  f"faltando {v['faltando']}, inventada {v['inventada']}, "
                  f"compassos cheios {v['compassos_cheios']}/{v['compassos_avaliados']}")


if __name__ == "__main__":
    main()

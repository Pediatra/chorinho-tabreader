import collections
import json
import subprocess
import sys

sys.path.insert(0, "/app")
from tab.som_casa_medida import tarefas_ouros  # noqa: E402
from tab.som_casa_notas import rotular  # noqa: E402

for t in tarefas_ouros():
    prod = t["produto"]
    notas = rotular(prod, t["ouro"], t["instantes"], t["audio"], recortado=t["recortado"])
    cont = collections.Counter(n.rotulo for n in notas)
    tecs = collections.Counter(
        n["tecnica"] for n in prod["notas"]
    )
    casadas = cont["certa"] + cont["erro_casa"]
    casa_certa = cont["certa"]
    print(
        t["nome"],
        "MEU: casadas",
        casadas,
        "casa_certa",
        casa_certa,
        "inventadas",
        cont["inventada"],
        "perdidas",
        cont["perdida"],
    )
    print("   tecnica distintas no produto:", dict(tecs))
    # oficial: avaliar_video no mesmo par produto x ouro
    ouro_path = {
        "retrato_mvp": "/app/data/gold/ouro_video/retrato_brasileiro_v2.json",
        "la_vie_en_rose": "/app/data/gold/ouro_video/la_vie_en_rose_edith_piaf_tab.json",
        "from_this_place": "/app/data/gold/ouro_video/tab_from_this_place_pat_metheny_fingerstyle_guitar_cover.json",
        "room_335": "/app/data/gold/ouro_video/tabroom_335_larry_carlton_fingerstyle_guitar.json",
    }[t["nome"]]
    prod_path = (
        "/app/" + t["audio"]["produto"]
    )
    r = subprocess.run(
        [sys.executable, "-m", "tab.avaliar_video", "--ouro", ouro_path, "--pred", prod_path,
         "--json", "/app/data/saida/tab_frentes/fd_som/scratch/aval_" + t["nome"] + ".json"],
        cwd="/app", capture_output=True, text=True,
    )
    rel = json.load(open("/app/data/saida/tab_frentes/fd_som/scratch/aval_" + t["nome"] + ".json"))
    if "total" not in rel["notas"]:
        print("   OFICIAL nao avalia:", rel["notas"].get("motivo"))
        continue
    tot = rel["notas"]["total"]
    print(
        "   OFICIAL: ouro",
        tot["notas_ouro"],
        "entregues",
        tot["entregues"],
        "casadas",
        tot["casadas"],
        "casa_certa",
        tot["casa_certa"],
        "inventadas",
        tot["inventadas"],
        "perdidas",
        tot["perdidas"],
    )

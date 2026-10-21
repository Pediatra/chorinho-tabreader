import json
from tab.maos_braco_ciclo import nut_suspeito_previsto
for pasta in ("m29","m27","m26"):
    ix={i["id"]:i for i in json.load(open(f"data/saida/maos/{pasta}/indice.json"))["quadros"]}
    pv=json.load(open(f"data/saida/maos/{pasta}/previsto.json"))["quadros"]
    s=[q for q,p in pv.items() if nut_suspeito_previsto(p,(ix[q]["largura"],ix[q]["altura"])) and not p["sinalizado"]]
    print(pasta, "achou", sum(p["achou"] for p in pv.values()), "novos sinalizados:", len(s), s)

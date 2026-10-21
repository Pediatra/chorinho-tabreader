import json
import pathlib

RAIZ = pathlib.Path("/app/data/saida/audio")
arquivos = []
for pasta in ["a5", "a4/lote1", "a4/lote2"]:
    arquivos += sorted((RAIZ / pasta).glob("*.audio.json"))
for arq in arquivos:
    d = json.loads(arq.read_text())
    ex = d.get("exibicoes", [])
    col = d.get("colunas", [])
    rec = sum(1 for e in ex if e.get("recusada"))
    print("==", arq.relative_to(RAIZ))
    print("   produto:", d["produto"], "| video:", d["video"]["arquivo"][-70:])
    print("   exibicoes:", len(ex), "recusadas:", rec, "| colunas:", len(col))
    if col and arq.name.startswith("iwaki_la"):
        print("   col0:", json.dumps(col[0], ensure_ascii=False)[:600])
        print("   chaves col:", list(col[0].keys()))
    if "afericao" in d:
        print("   afericao:", json.dumps(d["afericao"], ensure_ascii=False)[:400])
    print("   gerado_por:", str(d.get("gerado_por"))[:200])

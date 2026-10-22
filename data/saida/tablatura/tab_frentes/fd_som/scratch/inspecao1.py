import json
import pathlib

RAIZ = pathlib.Path("/app/data/saida/audio")
for pasta in ["a5", "a4/lote1", "a4/lote2"]:
    for arq in sorted((RAIZ / pasta).glob("*.audio.json")):
        d = json.loads(arq.read_text())
        chaves = list(d.keys())
        print("==", arq.relative_to(RAIZ), "chaves:", chaves)
        for k in ["produto", "video", "fonte", "metodo", "versao", "produto_arquivo"]:
            if k in d:
                print("   ", k, "=", str(d[k])[:160])
        telas = d.get("telas") or d.get("exibicoes") or []
        print("    n_telas:", len(telas))
        if telas:
            t0 = telas[0]
            print("    tela0 chaves:", list(t0.keys()))
            print("    tela0:", json.dumps(t0, ensure_ascii=False)[:700])
        break

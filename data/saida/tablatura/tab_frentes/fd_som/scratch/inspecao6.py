import collections
import json

aval = json.load(open("/app/data/saida/tab_frentes/fd_som/scratch/aval_la_vie_en_rose.json"))
print("notas:", json.dumps(aval["notas"], ensure_ascii=False)[:500])
print("tempo:", json.dumps(aval["tempo"], ensure_ascii=False)[:300])
for nome in ["iwaki_la_vie_en_rose", "mvp", "kimny_from_this_place", "shin_izumi_room_335"]:
    p = {
        "iwaki_la_vie_en_rose": "/app/data/saida/audio/a2/produtos/iwaki_la_vie_en_rose.json",
        "mvp": "/app/data/saida/conserto_v2/mvp.json",
        "kimny_from_this_place": "/app/data/saida/audio/a2/produtos/kimny_from_this_place.json",
        "shin_izumi_room_335": "/app/data/saida/audio/a2/produtos/shin_izumi_room_335.json",
    }[nome]
    d = json.load(open(p))
    nn = d.get("nao_notas", [])
    print("==", nome, "nao_notas:", len(nn))
    print("   classes:", collections.Counter(x.get("classe") for x in nn))
    chaves = collections.Counter()
    for x in nn:
        chaves.update(x.keys())
    print("   chaves:", dict(chaves))
    # simbolos crus: campos de interesse
    exemplos = [x for x in nn if x.get("classe") == "tecnica"][:2]
    for e in exemplos:
        print("   ex:", json.dumps({k: v for k, v in e.items() if k != "simbolo_cru"}, ensure_ascii=False)[:300])
        print("      cru:", json.dumps(e.get("simbolo_cru"), ensure_ascii=False)[:300])

import json

P = "/app/data/saida/audio/a2/produtos/iwaki_la_vie_en_rose.json"
p = json.load(open(P))
print("produto chaves:", list(p.keys()))
print("telas[0]:", json.dumps(p["telas"][0], ensure_ascii=False)[:500])
print("notas[0]:", json.dumps(p["notas"][0], ensure_ascii=False)[:500])
print("notas[1]:", json.dumps(p["notas"][1], ensure_ascii=False)[:500])
print("nao_notas[0]:", json.dumps(p["nao_notas"][0], ensure_ascii=False)[:300] if p.get("nao_notas") else None)
print("resumo:", json.dumps(p["resumo"], ensure_ascii=False)[:400])
print("gerado_por:", json.dumps(p["gerado_por"], ensure_ascii=False)[:600])

O = json.load(open("/app/data/gold/ouro_video/la_vie_en_rose_edith_piaf_tab.json"))
print("ouro chaves:", list(O.keys()))
print("ouro video:", json.dumps(O.get("video", {}), ensure_ascii=False)[:300])
for k in O:
    if k not in ("telas", "video"):
        print(" ouro.", k, "=", json.dumps(O[k], ensure_ascii=False)[:250])
print("ouro telas[0] keys:", list(O["telas"][0].keys()))
print("ouro telas[0]:", json.dumps(O["telas"][0], ensure_ascii=False)[:500])

R = "/app/data/saida/tab_frentes/fd_som/ca1/tab_from_this_place_pat_metheny_fingerstyle_guitar_cover.aval.json"
r = json.load(open(R))
print("aval keys:", list(r.keys()))
print("aval notas keys:", list(r["notas"].keys()))
for k in r["notas"]:
    if k != "por_tela":
        print(" aval.notas.", k, "=", json.dumps(r["notas"][k], ensure_ascii=False)[:600])

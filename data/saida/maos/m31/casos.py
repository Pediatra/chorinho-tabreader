import json
from tab.caminhos import *
fontes={"1027":(GABARITO_BRACO_M27,MAOS_M27),"M11B":(GABARITO_BRACO_M11B,MAOS_M11B),"1029":(GABARITO_BRACO_M29,MAOS_M29),"1031":(GABARITO_BRACO_M31,MAOS_M31)}
for nome,(g,p) in fontes.items():
    ouro=json.load(open(g))
    reg=ouro.get("respostas",ouro.get("quadros",ouro))
    print(nome, type(reg).__name__, list(ouro)[:6])
    itens = reg.items() if isinstance(reg,dict) else enumerate(reg)
    for k,r in itens:
        if isinstance(r,dict) and (r.get("nut")=="fora" or r.get("nut_fora") or r.get("traste_referencia")):
            print(" ",k,{c:r.get(c) for c in ("nut","traste_referencia","braco")}, str(r.get("arquivo",""))[:60])

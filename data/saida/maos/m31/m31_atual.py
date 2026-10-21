# roda o detector atual (1029/1032) nos 17 quadros do lote m31 com nut visível e confere o v2
import json, cv2, numpy as np
from pathlib import Path
from tab.maos_braco_detector import PASSOS, _carregar_pesos, _trava_gpu
from tab.maos_braco_localizador import _carregar_localizador, cadeia, sinalizado
from tab.maos_braco_ciclo import previsto_do_resultado
from tab.maos_braco_sinal_nut import linhas_de_painel, distancia_da_ponta, suspeito
lote=json.load(open("data/saida/maos/m31/lote.json"))["quadros"]
out={}
with _trava_gpu():
    loc=_carregar_localizador("L3_todos_s3"); dois,_=_carregar_pesos("A4_100_todos_s1",PASSOS)
    for r in lote:
        v=r["denso"].split("_")[0]
        im=cv2.imread(f"data/saida/maos/m31/denso/{v}/{r['denso']}.jpg")
        res=cadeia(loc,dois,im,r["id"],conjunta=True); p=previsto_do_resultado(r,res,sinalizado(res))
        dims=(im.shape[1],im.shape[0])
        s2=suspeito(distancia_da_ponta(p,dims,linhas_de_painel(im)),dims,0.02) if p["achou"] else None
        out[r["id"]]={"achou":p["achou"],"sinalizado":p["sinalizado"],"S1":p["S1"],"v2":s2,"previsto":p}
        print(r["id"],p["achou"],p["sinalizado"],p["S1"] and round(p["S1"],2),"v2",s2,flush=True)
json.dump(out,open("data/saida/maos/m31/m31_atual.json","w"))

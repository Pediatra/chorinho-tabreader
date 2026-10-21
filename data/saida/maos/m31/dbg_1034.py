import json, numpy as np, cv2
from tab.maos_braco_marcacoes import residuo_claro, LINHAS_ESCALA
from tab.maos_braco_juncao import faixa_do_quadro
from tab.maos_braco_faixa import recortar
from tab.maos_braco_detector import _imagem
for pasta,i in (("m27","q56"),("m27","q10")):
    p=json.load(open(f"data/saida/maos/{pasta}/previsto.json"))["quadros"][i]
    m,xs=faixa_do_quadro(p); f=recortar(_imagem(__import__("pathlib").Path(f"data/saida/maos/{pasta}/quadros/{i}.png")),m)
    r=residuo_claro(f)
    pares=sorted(zip([t["numero"] for t in p["trastes"]],xs))
    sc=[]
    for (na,xa),(nb,xb) in zip(pares,pares[1:]):
        a,b=sorted((xa,xb)); g=0.2*(b-a); sc.append((nb, round(float(r[70:122,int(a+g):int(b-g)+1].max()),0)))
    print(i, sc)
    cv2.imwrite(f"data/saida/maos/m31/dbg_{i}.jpg", np.vstack([f, cv2.cvtColor(np.clip(r*4,0,255).astype(np.uint8),cv2.COLOR_GRAY2BGR)]))

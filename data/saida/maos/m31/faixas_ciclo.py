import cv2, json, sys, numpy as np
from tab.maos_braco_juncao import faixa_do_quadro
from tab.maos_braco_faixa import recortar
# uso: faixas_ciclo.py saida pasta:id ...
out=[]
for arg in sys.argv[2:]:
    pasta,i=arg.split(":")
    p=json.load(open(f"data/saida/maos/{pasta}/previsto.json"))["quadros"][i]
    m,xs=faixa_do_quadro(p)
    f=recortar(cv2.imread(f"data/saida/maos/{pasta}/quadros/{i}.png"),m)
    for x,t in zip(xs,p["trastes"]):
        cv2.line(f,(int(x),180),(int(x),191),(0,0,255),2); cv2.putText(f,str(t["numero"]),(int(x)-5,178),0,0.4,(0,0,255),1)
    cv2.putText(f,arg,(5,15),0,0.5,(0,255,255),1)
    out.append(f)
cv2.imwrite(sys.argv[1],np.vstack(out))

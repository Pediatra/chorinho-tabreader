import cv2, json, sys, numpy as np
from tab.maos_braco_juncao import faixa_do_quadro, achar_juncao
from tab.maos_braco_faixa import recortar
# uso: faixas_j.py jsonl pasta saida id...
rs={}
for l in open(sys.argv[1]):
    r=json.loads(l); rs[r["id"]]=r
out=[]
for i in sys.argv[4:]:
    p=rs[i]["previsto"]; m,xs=faixa_do_quadro(p)
    im=cv2.imread(f"data/saida/maos/m31/denso/{sys.argv[2]}/{i}.jpg")
    j=achar_juncao(im,p); f=recortar(im,m)
    for x,t in zip(xs,p["trastes"]):
        cv2.line(f,(int(x),180),(int(x),191),(0,0,255),2); cv2.putText(f,str(t["numero"]),(int(x)-5,178),0,0.4,(0,0,255),1)
    if j: cv2.line(f,(j["x"],0),(j["x"],191),(0,255,0),2); cv2.putText(f,f"{i} c={j['contraste']} n={j['numero']}",(5,15),0,0.5,(0,255,255),1)
    out.append(f)
cv2.imwrite(sys.argv[3],np.vstack(out))

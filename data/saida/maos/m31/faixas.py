import cv2, json, sys, numpy as np
from tab.maos_braco_faixa import matriz_da_faixa, recortar, aplicar_matriz
# uso: faixas.py jsonl pasta saida id1 id2 ...
rs={}
for l in open(sys.argv[1]):
    r=json.loads(l); rs[r["id"]]=r
out=[]
for i in sys.argv[4:]:
    p=rs[i]["previsto"]; c1=np.array(p["corda1"]); c6=np.array(p["corda6"]); n=np.array(p["nut"])
    a=(c1[0]+c6[0])/2; b=(c1[1]+c6[1])/2
    if np.linalg.norm(a-n)>np.linalg.norm(b-n): a,b=b,a
    L=np.linalg.norm(b-a); u=(b-a)/L; w=max(np.linalg.norm(c1[0]-c6[0]),np.linalg.norm(c1[1]-c6[1]))
    m=matriz_da_faixa((a,u,L,w))
    im=cv2.imread(f"data/saida/maos/m31/denso/{sys.argv[2]}/{i}.jpg")
    f=recortar(im,m)
    for t in p["trastes"]:
        x,y=aplicar_matriz(m,[t["ponto"]])[0]; cv2.line(f,(int(x),180),(int(x),191),(0,0,255),2); cv2.putText(f,str(t["numero"]),(int(x)-5,178),0,0.4,(0,0,255),1)
    cv2.putText(f,i,(5,15),0,0.5,(0,255,255),1)
    out.append(f)
cv2.imwrite(sys.argv[3],np.vstack(out))

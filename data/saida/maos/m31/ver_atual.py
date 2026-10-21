import cv2, json, sys, numpy as np
d=json.load(open("data/saida/maos/m31/m31_atual.json")); lote={r["id"]:r for r in json.load(open("data/saida/maos/m31/lote.json"))["quadros"]}
out=[]
for i in sys.argv[2:]:
    x=d[i]["previsto"]; r=lote[i]; v=r["denso"].split("_")[0]
    im=cv2.imread(f"data/saida/maos/m31/denso/{v}/{r['denso']}.jpg")
    for c in ("corda1","corda6"):
        a,b=x[c]; cv2.line(im,tuple(map(int,a)),tuple(map(int,b)),(0,255,0),2)
    if x["nut"]: cv2.circle(im,tuple(map(int,x["nut"])),7,(0,0,255),-1)
    for t in x["trastes"]:
        a,b=map(int,t["ponto"]); cv2.circle(im,(a,b),3,(255,0,0),-1); cv2.putText(im,str(t["numero"]),(a-5,b-8),0,0.5,(0,255,255),2)
    cv2.putText(im,i,(10,30),0,1,(0,0,255),2)
    out.append(cv2.resize(im,(640,int(640*im.shape[0]/im.shape[1]))))
h=max(o.shape[0] for o in out); out=[cv2.copyMakeBorder(o,0,h-o.shape[0],0,0,0) for o in out]
while len(out)%2: out.append(np.zeros_like(out[0]))
cv2.imwrite(sys.argv[1],np.vstack([np.hstack(out[k:k+2]) for k in range(0,len(out),2)]))

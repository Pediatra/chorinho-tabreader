import cv2, json, numpy as np
lote=json.load(open("data/saida/maos/m31/lote.json"))["quadros"]
out=[]
for r in lote:
    if r["id"] in ("q13","q14","q15"): continue
    v=r["denso"].split("_")[0]; n=int(v[1:])
    reg=None
    for l in open(f"data/saida/maos/m30/video_{n:02d}.jsonl"):
        x=json.loads(l)
        if x["id"]==r["denso"]: reg=x; break
    p=reg["previsto"]
    im=cv2.imread(f"data/saida/maos/m31/denso/{v}/{r['denso']}.jpg")
    for c in ("corda1","corda6"):
        a,b=p[c]; cv2.line(im,tuple(map(int,a)),tuple(map(int,b)),(0,255,0),1)
    if p["nut"]: cv2.circle(im,tuple(map(int,p["nut"])),6,(0,0,255),-1)
    for t in p["trastes"]:
        x,y=map(int,t["ponto"]); cv2.circle(im,(x,y),3,(255,0,0),-1); cv2.putText(im,str(t["numero"]),(x-4,y-6),0,0.45,(0,255,255),1)
    h=int(im.shape[0]*640/im.shape[1]); im=cv2.resize(im,(640,h))[: int(h*0.62)]
    cv2.putText(im,f"{r['id']} S1={p['S1'] and round(p['S1'],2)} sin={p['sinalizado']}",(5,20),0,0.6,(0,0,255),2)
    out.append(cv2.resize(im,(640,int(640*im.shape[0]/im.shape[1]))))
for k in range(0,len(out),6):
    grupo=out[k:k+6]; hmax=max(i.shape[0] for i in grupo)
    grupo=[cv2.copyMakeBorder(i,0,hmax-i.shape[0],0,0,0) for i in grupo]
    while len(grupo)%2: grupo.append(np.zeros_like(grupo[0]))
    cv2.imwrite(f"data/saida/maos/m31/inv_{k//6}.jpg",np.vstack([np.hstack(grupo[j:j+2]) for j in range(0,len(grupo),2)]))

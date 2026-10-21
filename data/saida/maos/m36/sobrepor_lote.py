import cv2, json, numpy as np, sys
p=json.load(open("data/saida/maos/m36/previsto.json"))["quadros"]
ids=sys.argv[2:]
out=[]
for i in ids:
    x=p[i]; im=cv2.imread(f"data/saida/maos/m36/quadros/{i}.png")
    for c in ("corda1","corda6"):
        a,b=x[c]; cv2.line(im,tuple(map(int,a)),tuple(map(int,b)),(0,255,0),2)
    if x["nut"]: cv2.circle(im,tuple(map(int,x["nut"])),9,(0,0,255),-1)
    for t in x["trastes"]:
        a,b=map(int,t["ponto"]); cv2.circle(im,(a,b),4,(255,0,0),-1); cv2.putText(im,str(t["numero"]),(a-6,b-10),0,0.7,(0,255,255),2)
    cv2.putText(im,i,(10,40),0,1.2,(0,0,255),3)
    h=im.shape[0]; out.append(cv2.resize(im[: int(h*0.6)],(800,int(800*0.6*h/im.shape[1]))))
cv2.imwrite(sys.argv[1],np.vstack([np.hstack(out[k:k+2]) for k in range(0,len(out),2)]))

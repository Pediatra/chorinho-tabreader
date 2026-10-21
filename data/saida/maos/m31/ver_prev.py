import cv2, json, sys, numpy as np
# uso: ver_prev.py saida pasta:id ...
out=[]
for arg in sys.argv[2:]:
    pasta,i=arg.split(":")
    x=json.load(open(f"data/saida/maos/{pasta}/previsto.json"))["quadros"][i]
    im=cv2.imread(f"data/saida/maos/{pasta}/quadros/{i}.png")
    for c in ("corda1","corda6"):
        a,b=x[c]; cv2.line(im,tuple(map(int,a)),tuple(map(int,b)),(0,255,0),2)
    if x["nut"]: cv2.circle(im,tuple(map(int,x["nut"])),9,(0,0,255),-1)
    for t in x["trastes"]:
        a,b=map(int,t["ponto"]); cv2.circle(im,(a,b),4,(255,0,0),-1); cv2.putText(im,str(t["numero"]),(a-6,b-10),0,0.7,(0,255,255),2)
    cv2.putText(im,arg,(10,40),0,1.2,(0,0,255),3)
    out.append(cv2.resize(im,(960,int(960*im.shape[0]/im.shape[1]))))
cv2.imwrite(sys.argv[1],np.vstack(out))

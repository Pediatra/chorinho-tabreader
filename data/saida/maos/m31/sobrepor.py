import cv2, json, sys
# uso: sobrepor.py jsonl id saida
rs={json.loads(l)["id"]:json.loads(l) for l in open(sys.argv[1])}
r=rs[sys.argv[2]]; p=r["previsto"]
pasta=sys.argv[4] if len(sys.argv)>4 else None
im=cv2.imread(f"data/saida/maos/m31/denso/{pasta}/{r['id']}.jpg")
for c in ("corda1","corda6"):
    a,b=p[c]; cv2.line(im,tuple(map(int,a)),tuple(map(int,b)),(0,255,0),2)
if p["nut"]: cv2.circle(im,tuple(map(int,p["nut"])),8,(0,0,255),-1)
for t in p["trastes"]:
    x,y=map(int,t["ponto"]); cv2.circle(im,(x,y),4,(255,0,0),-1); cv2.putText(im,str(t["numero"]),(x,y-8),0,0.5,(255,255,0),1)
cv2.imwrite(sys.argv[3],im)

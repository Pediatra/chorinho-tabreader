import json, random, subprocess, sys, cv2, numpy as np
canal, alvo, n = sys.argv[1], sys.argv[2] == "1", int(sys.argv[3])
L = [json.loads(l) for l in open("data/saida/censo/censo_cache.jsonl")]
L = [d for d in L if d["canal"] == canal and bool(d.get("tablatura")) == alvo]
random.seed(7); sel = random.sample(L, min(n, len(L)))
rows = []
for d in sel:
    row = []
    for ins in d["instantes"][1::3]:
        subprocess.run(["ffmpeg","-y","-loglevel","quiet","-ss",str(ins["t"]),"-i","/acervo/"+d["arquivo"],"-frames:v","1","/tmp/o.png"])
        im = cv2.imread("/tmp/o.png"); H, W = im.shape[:2]
        if ins.get("rect"):
            x0,y0,x1,y1 = ins["rect"]; cv2.rectangle(im,(x0,y0),(x1,y1),(0,255,0),6)
        im = cv2.resize(im,(400,225))
        cv2.putText(im, f"{ins['t']:.0f}s {ins['tab']}", (5,22), cv2.FONT_HERSHEY_SIMPLEX, 0.6,(0,0,255),2)
        row.append(im)
    rows.append(np.hstack(row))
cv2.imwrite(f"data/saida/censo/olhar/{canal.replace(' ','_')}_{int(alvo)}.jpg", np.vstack(rows))

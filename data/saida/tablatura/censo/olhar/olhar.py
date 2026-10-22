import json, subprocess, cv2, numpy as np
L = [json.loads(l) for l in open("data/saida/censo/censo.jsonl")]
sel = [L[i] for i in (5, 40, 80, 120)]
ims = []
for d in sel:
    row = []
    for ins in d["instantes"][2::3]:
        out = "/tmp/o.png"
        subprocess.run(["ffmpeg","-y","-loglevel","error","-ss",str(ins["t"]),"-i","/acervo/"+d["arquivo"],"-frames:v","1",out],check=True)
        im = cv2.resize(cv2.imread(out),(480,270))
        cv2.putText(im, f"{ins['t']:.0f}s tab={ins['tab']}", (5,25), cv2.FONT_HERSHEY_SIMPLEX, 0.7,(0,0,255),2)
        row.append(im)
    ims.append(np.hstack(row))
cv2.imwrite("data/saida/censo/olhar/cifra.jpg", np.vstack(ims))
print([d["arquivo"] for d in sel])

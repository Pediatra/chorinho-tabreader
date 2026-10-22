import json
from pathlib import Path
import cv2
B=Path("/app/data/saida/tablatura")
pre={int(t["id"]):t for t in json.loads((B/"t84/ferramenta/pre.json").read_text())["telas"]}
erros=json.loads((B/"tab_rotulo/r4g/erros_t84/erros.json").read_text())
A={n["nota"]:n for n in json.loads((B/"tab_rotulo/r2/conferir_t84/ataque_t84.json").read_text())["notas"]}
por={}
for e in erros: por.setdefault(e["tela"],[]).append(e)
for t,es in por.items():
    p=pre[t]; im=cv2.imread(str(B/"t84/ferramenta"/p["arquivo"])); e_=p["escala"]; px,py=p["painel"][:2]
    for e in es:
        n=A[e["nota"]]; x=int((n["x_centro_quadro"]-px)*e_); y=int((p["linhas_y"][n["corda"]-1]-py)*e_)
        cv2.circle(im,(x,y),int(p["passo"]*e_*0.5),(255,0,255),3)
    cv2.imwrite(str(B/f"tab_rotulo/r4g/erros_t84/tela_{t}.jpg"),im)
print(sorted(por))

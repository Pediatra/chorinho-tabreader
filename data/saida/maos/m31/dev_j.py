# desenvolvimento da regra J nos vídeos da 1030 (fora o v15, que tem casos): sem casos
import json, sys, collections, cv2
from pathlib import Path
from tab.caminhos import MAOS_M30, MAOS_M31
from tab.maos_braco_juncao import achar_juncao
from tab.maos_braco_vizinhos import nut_confiante
from tab.maos_braco_video import ler_jsonl, nome_jsonl
res={}
for n in range(1,17):
    nome=f"v{n:02d}"; dim=MAOS_M31/f"dimensoes_{nome}.json"
    if n==15 or not dim.exists(): continue
    d=json.loads(dim.read_text()); regs=ler_jsonl(MAOS_M30/nome_jsonl(n))
    linhas=[]
    for r in regs:
        r["dimensoes"]=d.get(r["id"])
        if not nut_confiante(r): continue
        im=cv2.imread(str(MAOS_M31/"denso"/nome/f"{r['id']}.jpg"))
        if im is None: continue
        j=achar_juncao(im,r["previsto"])
        if j: linhas.append((r["id"],j["numero"],j["contraste"],j["x"]))
    res[nome]=linhas
    c=collections.Counter(x[1] for x in linhas)
    for lim in (0,2,3,4,6):
        cc=collections.Counter(x[1] for x in linhas if x[2]>=lim)
        tot=sum(cc.values())
        print(nome,f"c>={lim}",tot, cc.most_common(4))
json.dump(res,open(MAOS_M31/"dev_j.json","w"))

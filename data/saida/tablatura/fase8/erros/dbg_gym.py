import subprocess, sys
import cv2
sys.path.insert(0, "/app")
from tab import painel as P
from tab.tabseg import mascaras_candidatas, picos_de_linha
import json
V = "/acervo/" + json.load(open(f"/app/data/gold/ouro_video/{sys.argv[1]}.json"))["video"]
subprocess.run(["ffmpeg","-loglevel","error","-y","-ss",sys.argv[2],"-i",V,"-frames:v","1","/tmp/f.png"],check=True)
img = cv2.imread("/tmp/f.png")
for nome, m in mascaras_candidatas(img):
    for fr in (0.30, 0.15):
        print(nome, fr, [int(y) for _v, y in picos_de_linha(m, fracao_min=fr) if y > 800])
for c in P.candidatos_quadro(img):
    print("cand", c.nome, c.y0, c.y1, c.grade.linhas_y, c.passo, round(P.uniformidade(img[c.y0:c.y1]),3))
m = P.escolher_ou_mascara(img); print("escolhido", m.nome, m.y0, m.grade.linhas_y)

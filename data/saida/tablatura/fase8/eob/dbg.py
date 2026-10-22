import subprocess, sys
import cv2, numpy as np
sys.path.insert(0, "/app")
from tab import painel as P
V = "/acervo/kenneth acoustic/end of beginning - djo ｜ fingerstyle guitar ｜ tab + chords + lyrics.mp4"
subprocess.run(["ffmpeg","-loglevel","error","-y","-ss","52","-i",V,"-frames:v","1","/tmp/f.png"],check=True)
img = cv2.imread("/tmp/f.png")
m = P.escolher_ou_mascara(img)
print("escolhido", m.nome, m.x0, m.y0, m.roi.shape, m.passo)
faixa = img[m.y0:m.y0+m.roi.shape[0]]
print("fundo na faixa inteira", P.extensao_por_fundo(faixa))
print("linhas na faixa inteira", P.extensao_das_linhas(faixa, m.grade.linhas_y))
L=40
print([round(P.uniformidade(faixa[:, i*L:(i+1)*L]),3) for i in range(faixa.shape[1]//L)])

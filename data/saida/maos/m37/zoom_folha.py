import sys
import cv2
import numpy as np
img = cv2.imread("data/saida/maos/m37/l4_folha_capo.jpg")
# células 640x384 (3 colunas x 4 linhas); recorta em volta dos pontos azul/vermelho
celulas = [(0,0,(540,80)),(1,0,(1220,100)),(2,0,(1830,150)),(0,1,(400,480)),(1,1,(1160,420)),(2,1,(1720,430)),(0,2,(440,820)),(1,2,(1240,880)),(2,2,(1790,880)),(0,3,(500,1260)),(2,3,(1880,1250))]
crops=[]
for c,l,(x,y) in celulas:
    x0,y0=max(0,x-110),max(0,y-60); cr=img[y0:y0+130, x0:x0+220]
    cr=cv2.resize(cr,(440,260),interpolation=cv2.INTER_CUBIC); crops.append(cr)
while len(crops)%4: crops.append(np.zeros_like(crops[0]))
linhas=[np.hstack(crops[i:i+4]) for i in range(0,len(crops),4)]
cv2.imwrite("data/saida/maos/m37/l4_folha_zoom.jpg", np.vstack(linhas))

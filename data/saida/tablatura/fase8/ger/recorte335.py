import json, sys
sys.path.insert(0, "/app")
import cv2
from tab import caminhos, leitor
g = json.load(open("/app/data/gold/ouro_video/tabroom_335_larry_carlton_fingerstyle_guitar.json"))
q = leitor.quadro_em(str(caminhos.acervo() / g["video"]), 14.0)
r = q[846:998, 1150:1420]
cv2.imwrite("/app/data/saida/fase8/ger/r335_t4.png", cv2.resize(r, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC))

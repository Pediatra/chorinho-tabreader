"""Uma tela: painel com ouro (verde, acima) e predição (vermelho, abaixo). Uso: SLUG PRED TELA."""
import json, subprocess, sys
from pathlib import Path
import cv2
sys.path.insert(0, "/app")
from tab.avaliar_video import casar_telas, casar_sem_instante, ler_predicao, so_conferidas
slug, pred_path, tid = sys.argv[1], sys.argv[2], int(sys.argv[3])
ouro = so_conferidas(json.loads(Path(f"/app/data/gold/ouro_video/{slug}.json").read_text()))
dados = json.loads(Path(pred_path).read_text()); pred = ler_predicao(dados)
mapa = casar_telas([int(t["id"]) for t in ouro["telas"]], ouro.get("instantes", []), pred.telas)
mapa, _ = casar_sem_instante(ouro["telas"], mapa, pred.telas)
tela = [t for t in ouro["telas"] if int(t["id"]) == tid][0]; pid = mapa[tid]
tp = [t for t in dados["telas"] if t["id"] == pid][0]
subprocess.run(["ffmpeg","-loglevel","error","-y","-ss",str(tela["quadro_ref_s"]),"-i","/acervo/"+ouro["video"],"-frames:v","1","/tmp/q.png"],check=True)
img = cv2.imread("/tmp/q.png"); x0,y0,x1,y1 = tp["painel"]
print("painel", tp["painel"], "passo", tp["passo"], "pid", pid)
pad = 60
c = cv2.copyMakeBorder(img[y0:y1, :], pad, pad, 0, 0, cv2.BORDER_CONSTANT, value=(255,255,255))
for n in tela["notas"]:
    x = int(n.get("x_centro_quadro") or n["x_quadro"])
    cv2.putText(c, f"{n['corda']}:{n['casa']}", (x-10, 12 + 9*(n['corda']-1)), cv2.FONT_HERSHEY_PLAIN, 0.8, (0,150,0), 1)
for n in dados["notas"]:
    if n["tela"] != pid: continue
    x = int(n["x_centro_quadro"])
    cv2.putText(c, f"{n['corda']}:{n['casa']}", (x-10, c.shape[0]-60+12 + 9*(n['corda']-1)), cv2.FONT_HERSHEY_PLAIN, 0.8, (0,0,255), 1)
cv2.rectangle(c, (x0, pad), (x1, pad + y1 - y0), (255, 0, 0), 1)
cv2.imwrite(f"/app/data/saida/fase8/erros/{slug[:12]}_t{tid}.png", c)

# roda na CPU (sem a trava da GPU) os vídeos da 1031 pedidos na linha de comando
import sys
from tab.maos_braco_detector import PASSOS, _carregar_pesos
from tab.maos_braco_localizador import _carregar_localizador
from tab.maos_braco_nut_fora import (ESTAGIO1_1031, ESTAGIO2_1031, destino_jsonl,
    guardar_quadros, videos_1031)
from tab.maos_braco_video import gravar_jsonl, processar_video
loc = _carregar_localizador(ESTAGIO1_1031)
dois, _ = _carregar_pesos(ESTAGIO2_1031, PASSOS)
for nome, video in videos_1031():
    if nome not in sys.argv[1:] or destino_jsonl(nome).exists():
        continue
    regs = processar_video(video, loc, dois)
    dims = guardar_quadros(video, regs, nome)
    for r in regs:
        r["dimensoes"] = dims.get(r["id"])
    gravar_jsonl(destino_jsonl(nome), regs)
    print(nome, len(regs), flush=True)

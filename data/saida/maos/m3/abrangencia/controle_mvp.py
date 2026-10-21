"""Controle: a mesma calibracao no video do MVP (retrato brasileiro), sem alterar o codigo."""

import json
from pathlib import Path

import cv2

from tab.maos_calibrar_braco import VIDEO_PADRAO, desenhar
from rodar_calibracao import calibrar_video

PASTA = Path("/app/data/saida/maos/m3/abrangencia")


def main() -> None:
    out = calibrar_video(VIDEO_PADRAO)
    calib = out["calib"]
    esc = calib["escala"]
    cordas = calib["cordas"]
    det = sum(1 for k in range(1, 15) if esc["trastes"][k]["origem"] == "detectado")
    reg = {
        "video": VIDEO_PADRAO.name,
        "n_cordas": len(cordas),
        "rms_max": round(max(c["rms"] for c in cordas), 3),
        "trastes_detectados": det,
        "razao_mediana": round(esc["razao_mediana"], 4),
    }
    print(json.dumps(reg, ensure_ascii=False))
    cv2.imwrite(str(PASTA / "braco_controle_mvp.jpg"), desenhar(calib["mediana"], calib))


if __name__ == "__main__":
    main()

"""Abrangencia v2: calibra o braco de cada video da amostra com a regiao (sem coordenada fixa).

Mesmos 30 videos e mesmos criterios internos da rodada 1004 (abrangencia v1). A mao do
braco sai dos quadros do cache (presenca_00..11, lidos com cv2); a mediana usa 30 quadros
do video, lidos com ffmpeg, como na v1.
"""

import json
import signal
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from tab.maos_calibrar_braco import (
    calibrar_na_regiao,
    desenhar,
    duracao_e_tamanho,
    quadro_em_cinza,
    regiao_do_braco,
)
from tab.maos_detector import DetectorMaos

PASTA = Path("/app/data/saida/maos/m3/abrangencia_v2")
ACERVO = Path("/acervo")
CACHE = Path("/cache/png")
LIMITE_S = 180
N_QUADROS = 30
INICIO = 240.0


class Estouro(Exception):
    pass


def _estourou(sig, frame):
    raise Estouro()


def quadros_do_cache(pasta_cache: str, largura: int, altura: int) -> list[np.ndarray]:
    """Quadros de presenca do cache (BGR), so os que tem o tamanho do video."""
    quadros = []
    for k in range(12):
        img = cv2.imread(str(CACHE / Path(pasta_cache).name / f"presenca_{k:02d}.png"))
        if img is not None and img.shape[:2] == (altura, largura):
            quadros.append(img)
    return quadros


def main() -> None:
    amostra = json.loads((PASTA.parent / "abrangencia" / "amostra.json").read_text(encoding="utf-8"))
    det = DetectorMaos("cuda")
    signal.signal(signal.SIGALRM, _estourou)
    saida = PASTA / "abrangencia_v2.jsonl"
    with saida.open("w", encoding="utf-8") as f:
        for i, r in enumerate(amostra):
            caminho = ACERVO / r["arquivo"]
            reg = {"n": i, "grupo": r["grupo"], "canal": r["canal"], "arquivo": r["arquivo"]}
            t0 = time.time()
            signal.alarm(LIMITE_S)
            try:
                duracao, largura, altura = duracao_e_tamanho(caminho)
                inicio = INICIO if duracao > INICIO + 30 else 0.1 * duracao
                instantes = np.linspace(inicio, duracao - 1.0, N_QUADROS)
                quadros = [quadro_em_cinza(caminho, float(t), largura, altura) for t in instantes]
                bootstrap = quadros_do_cache(r["_pasta"], largura, altura)
                reg["quadros_maos"] = len(bootstrap)
                regiao = regiao_do_braco(det, bootstrap, (largura, altura))
                mediana = np.round(np.median(np.stack(quadros), axis=0)).astype(np.uint8)
                calib = calibrar_na_regiao(mediana, regiao)
                cordas = calib["cordas"]
                esc = calib["escala"]
                det_tr = sum(1 for k in range(1, 15) if esc["trastes"][k]["origem"] == "detectado")
                reg.update(
                    {
                        "resolucao": [largura, altura],
                        "regiao": calib["regiao"],
                        "inclinacao": round(calib["rotacao"]["inclinacao"], 4),
                        "n_cordas": len(cordas),
                        "rms_max": round(max(c["rms"] for c in cordas), 3),
                        "pontos_min": min(c["n"] for c in cordas),
                        "trastes_detectados": det_tr,
                        "razao_mediana": round(esc["razao_mediana"], 4),
                        "residuo_px": round(esc["residuo_px"], 3),
                        "brilho": [round(c["brilho"], 1) for c in cordas],
                    }
                )
                ok = (
                    len(cordas) == 6
                    and reg["rms_max"] < 1.0
                    and det_tr >= 8
                    and 0.93 <= reg["razao_mediana"] <= 0.96
                )
                reg["sucesso"] = bool(ok)
                reg["motivo"] = "criterios atendidos" if ok else "criterio(s) falhou"
                cv2.imwrite(str(PASTA / f"braco_{i:02d}.jpg"), desenhar(calib))
            except Estouro:
                reg.update({"sucesso": False, "motivo": f"estourou {LIMITE_S}s (pulado)"})
            except Exception as e:  # erro registrado, nao escondido
                reg.update({"sucesso": False, "motivo": f"{type(e).__name__}: {str(e)[:200]}"})
            finally:
                signal.alarm(0)
            reg["tempo_s"] = round(time.time() - t0, 1)
            f.write(json.dumps(reg, ensure_ascii=False) + "\n")
            f.flush()
            print(i, reg["sucesso"], reg["motivo"][:100], reg["tempo_s"], flush=True)


if __name__ == "__main__":
    sys.exit(main())

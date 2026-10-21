"""Roda a calibracao do braco (tab.maos_calibrar_braco, sem alterar o codigo) em cada video da amostra."""

import json
import signal
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from tab.maos_calibrar_braco import (
    calibrar,
    desenhar,
    duracao_e_tamanho,
    quadro_em_cinza,
)

PASTA = Path("/app/data/saida/maos/m3/abrangencia")
ACERVO = Path("/acervo")
LIMITE_S = 180
N_QUADROS = 30
INICIO = 240.0


class Estouro(Exception):
    pass


def _estourou(sig, frame):
    raise Estouro()


def calibrar_video(caminho: Path) -> dict:
    duracao, largura, altura = duracao_e_tamanho(caminho)
    inicio = INICIO if duracao > INICIO + 30 else 0.1 * duracao
    instantes = np.linspace(inicio, duracao - 1.0, N_QUADROS)
    quadros = [quadro_em_cinza(caminho, float(t), largura, altura) for t in instantes]
    calib = calibrar(quadros)
    return {"calib": calib, "resolucao": [largura, altura], "duracao": duracao}


def main() -> None:
    amostra = json.loads((PASTA / "amostra.json").read_text(encoding="utf-8"))
    saida = PASTA / "abrangencia.jsonl"
    signal.signal(signal.SIGALRM, _estourou)
    with saida.open("w", encoding="utf-8") as f:
        for i, r in enumerate(amostra):
            caminho = ACERVO / r["arquivo"]
            reg = {"n": i, "grupo": r["grupo"], "canal": r["canal"], "arquivo": r["arquivo"]}
            t0 = time.time()
            signal.alarm(LIMITE_S)
            try:
                out = calibrar_video(caminho)
                calib = out["calib"]
                esc = calib["escala"]
                cordas = calib["cordas"]
                det = sum(1 for k in range(1, 15) if esc["trastes"][k]["origem"] == "detectado")
                reg.update(
                    {
                        "resolucao": out["resolucao"],
                        "n_cordas": len(cordas),
                        "rms_max": round(max(c["rms"] for c in cordas), 3),
                        "pontos_min": min(c["n"] for c in cordas),
                        "trastes_detectados": det,
                        "razao_mediana": round(esc["razao_mediana"], 4),
                        "residuo_px": round(esc["residuo_px"], 3),
                        "brilho": [round(c["brilho"], 1) for c in cordas],
                    }
                )
                ok = (
                    len(cordas) == 6
                    and reg["rms_max"] < 1.0
                    and det >= 8
                    and 0.93 <= reg["razao_mediana"] <= 0.96
                )
                reg["sucesso"] = bool(ok)
                reg["motivo"] = "criterios atendidos" if ok else "criterio(s) falhou: " + ", ".join(
                    m for m, c in [
                        ("cordas", len(cordas) == 6),
                        ("rms", reg["rms_max"] < 1.0),
                        ("trastes>=8", det >= 8),
                        ("razao", 0.93 <= reg["razao_mediana"] <= 0.96),
                    ] if not c
                )
                cv2.imwrite(str(PASTA / f"braco_{i:02d}.jpg"), desenhar(calib["mediana"], calib))
            except Estouro:
                reg.update({"sucesso": False, "motivo": f"estourou {LIMITE_S}s (pulado)"})
            except Exception as e:  # erro da calibracao: registrado, nao escondido
                reg.update({"sucesso": False, "motivo": f"{type(e).__name__}: {str(e)[:200]}"})
            finally:
                signal.alarm(0)
            reg["tempo_s"] = round(time.time() - t0, 1)
            f.write(json.dumps(reg, ensure_ascii=False) + "\n")
            f.flush()
            print(i, reg["sucesso"], reg["motivo"][:100], reg["tempo_s"], flush=True)


if __name__ == "__main__":
    sys.exit(main())

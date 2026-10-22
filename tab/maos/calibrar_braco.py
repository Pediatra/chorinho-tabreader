"""Calibra o braço do violão de um vídeo: cordas, trastes e nut (M3).

Lê ~30 quadros espalhados entre ``--inicio`` e o fim do vídeo com ffmpeg (AV1 não
decodifica no OpenCV), tira a mediana (a mão se mexe e a mediana a apaga) e acha no
braço as cordas, o nut e os trastes com ``tab.maos_braco``. Também confere se a câmera
está fixa: compara a posição dos trastes no começo e no fim do vídeo.

Grava ``braco.json`` e ``braco.jpg`` (cordas e trastes numerados sobre a mediana) em
``data/saida/maos/m3``. A imagem tem que ser aberta e conferida a olho antes de usar.

Uso::

    python -m tab.maos_calibrar_braco
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np

from tab.comum.caminhos import MAOS_M3, acervo
from tab.maos.braco.braco import (
    achar_cordas,
    achar_nut,
    achar_trastes,
    ajustar_escala,
    numerar_cordas,
)

#: Vídeo do M3 (o mesmo do M2) dentro do acervo montado.
VIDEO_PADRAO = acervo() / "sky guitar" / "retrato brasileiro - tab & lesson.mp4"

#: Região das cordas: colunas de x 720 a 1520 (sem a mão, que entra por volta de 1560).
X_CORDAS = (720, 1520)

#: Faixa de linhas onde as cordas são procuradas.
Y_CORDAS = (700, 930)

#: Faixa de linhas para os trastes e o nut: fica acima da mão, que cobre as cordas
#: de baixo a partir de x ~1560. Medido na mediana.
Y_TRASTES = (745, 790)

#: Colunas dos trastes (de 690 a 1755) e do nut (de 1745 a 1790, a faixa branca).
X_TRASTES = (690, 1755)
X_NUT = (1745, 1790)

#: Quadros usados na mediana e, no começo e no fim, para checar a câmera.
N_QUADROS = 30
N_GRUPO = 10


def duracao_e_tamanho(video: Path) -> tuple[float, int, int]:
    """Duração e resolução do vídeo, via ffprobe.

    Args:
        video: arquivo de vídeo.

    Returns:
        ``(duracao_s, largura, altura)``.
    """
    saida = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height:format=duration",
            "-of",
            "json",
            str(video),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    dados = json.loads(saida.stdout)
    fluxo = dados["streams"][0]
    return float(dados["format"]["duration"]), int(fluxo["width"]), int(fluxo["height"])


def quadro_em_cinza(
    video: Path, instante: float, largura: int, altura: int
) -> np.ndarray:
    """Um quadro do vídeo no instante dado, em tons de cinza, lido pelo ffmpeg.

    Args:
        video: arquivo de vídeo.
        instante: segundo do quadro.
        largura: largura do quadro, em px.
        altura: altura do quadro, em px.

    Returns:
        Matriz ``uint8`` ``(altura, largura)``.
    """
    bruto = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            f"{instante:.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "gray",
            "-",
        ],
        check=True,
        capture_output=True,
    ).stdout
    return np.frombuffer(bruto, dtype=np.uint8).reshape(altura, largura)


def calibrar(quadros: list[np.ndarray]) -> dict:
    """Acha cordas, nut e trastes sobre a mediana de um conjunto de quadros.

    Args:
        quadros: quadros em cinza, ``uint8``, todos do mesmo tamanho.

    Returns:
        ``cordas`` (lista com ``corda``, ``a``, ``b``, ``rms``, ``n``, ``brilho``),
        ``escala`` (saída de :func:`tab.maos_braco.ajustar_escala`) e ``mediana``.
    """
    mediana = np.round(np.median(np.stack(quadros), axis=0)).astype(np.uint8)
    cordas = numerar_cordas(achar_cordas(mediana, *X_CORDAS, *Y_CORDAS))
    nut = achar_nut(mediana, *Y_TRASTES, *X_NUT)
    trastes = achar_trastes(mediana, *Y_TRASTES, *X_TRASTES)
    escala = ajustar_escala(nut, trastes)
    return {"cordas": cordas, "escala": escala, "mediana": mediana}


def desenhar(mediana: np.ndarray, calib: dict) -> np.ndarray:
    """Imagem de conferência: cordas e trastes numerados sobre o braço.

    Args:
        mediana: quadro em cinza, ``uint8``.
        calib: saída de :func:`calibrar`.

    Returns:
        Recorte do braço, em BGR e ampliado 1,5 vez.
    """
    cor = cv2.cvtColor(mediana, cv2.COLOR_GRAY2BGR)
    x0, x1, y0, y1 = 680, 1800, 690, 940
    for reta in calib["cordas"]:
        xa, xb = x0, x1
        ya = round(reta["a"] + reta["b"] * xa)
        yb = round(reta["a"] + reta["b"] * xb)
        cv2.line(cor, (xa, ya), (xb, yb), (0, 255, 255), 1)
        cv2.putText(
            cor,
            str(reta["corda"]),
            (x0 + 4, ya - 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )
    for k, traste in calib["escala"]["trastes"].items():
        x = round(traste["x"])
        cor_traste = (255, 0, 255) if traste["origem"] == "detectado" else (255, 128, 0)
        cv2.line(cor, (x, y0), (x, y1), cor_traste, 1)
        cv2.putText(
            cor,
            str(k),
            (x - 6, y1 - 6),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            cor_traste,
            1,
            cv2.LINE_AA,
        )
    recorte = cor[y0:y1, x0:x1]
    return cv2.resize(recorte, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)


def deriva_da_camera(quadros: list[np.ndarray], calib: dict) -> dict:
    """Confere se a câmera ficou fixa, comparando o começo e o fim do vídeo.

    Args:
        quadros: quadros em ordem de tempo.
        calib: calibração do conjunto inteiro (para saber quais trastes existem).

    Returns:
        Diferença máxima, em px, das posições dos trastes detectados e das cordas
        no meio do braço entre o primeiro e o último grupo.
    """
    grupo_ini = calibrar(quadros[:N_GRUPO])
    grupo_fim = calibrar(quadros[-N_GRUPO:])
    # Só trastes DETECTADOS nos dois grupos: um traste previsto não mede a câmera.
    difs_trastes = []
    for k in range(1, 9):
        ini = grupo_ini["escala"]["trastes"][k]
        fim = grupo_fim["escala"]["trastes"][k]
        if ini["origem"] == "detectado" and fim["origem"] == "detectado":
            difs_trastes.append(abs(ini["x"] - fim["x"]))
    difs_cordas = []
    for ci, cf in zip(grupo_ini["cordas"], grupo_fim["cordas"], strict=True):
        meio = 1100
        difs_cordas.append(abs((ci["a"] + ci["b"] * meio) - (cf["a"] + cf["b"] * meio)))
    return {
        "max_dif_trastes_px": float(max(difs_trastes)) if difs_trastes else None,
        "trastes_comparados": len(difs_trastes),
        "max_dif_cordas_px": float(max(difs_cordas)),
        "quadros_por_grupo": N_GRUPO,
    }


def main() -> None:
    """Calibra o braço, grava o JSON e a imagem de conferência e imprime o resumo."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--video", type=Path, default=VIDEO_PADRAO)
    parser.add_argument("--inicio", type=float, default=240.0)
    parser.add_argument("--quadros", type=int, default=N_QUADROS)
    parser.add_argument("--pasta", type=Path, default=MAOS_M3)
    args = parser.parse_args()

    duracao, largura, altura = duracao_e_tamanho(args.video)
    instantes = np.linspace(args.inicio, duracao - 1.0, args.quadros)
    quadros = [
        quadro_em_cinza(args.video, float(t), largura, altura) for t in instantes
    ]
    calib = calibrar(quadros)
    deriva = deriva_da_camera(quadros, calib)

    escala = calib["escala"]
    registro = {
        "video": str(args.video),
        "instantes": [round(float(t), 2) for t in instantes],
        "resolucao": [largura, altura],
        "cordas": [
            {
                "corda": c["corda"],
                "a": c["a"],
                "b": c["b"],
                "rms": c["rms"],
                "n": c["n"],
                "brilho": c["brilho"],
            }
            for c in calib["cordas"]
        ],
        "ordem_cordas": (
            "fisica: camera frontal, cabeca do violao a direita; a mao esquerda chega "
            "por BAIXO do braco, pelo lado das agudas. A linha mais perto da mao (a de "
            "baixo na imagem) e a corda 1; a de cima e a 6. Conferencia: bordoes (4-6) "
            "de metal brilham e primas (1-3) de naylon ficam escuras; o topo tem que ser "
            "mais claro que a base (numerar_cordas levanta erro se nao for)."
        ),
        "nut_x": escala["trastes"][0]["x"],
        "trastes": {str(k): v for k, v in escala["trastes"].items()},
        "x0": escala["x0"],
        "L_px": escala["L"],
        "residuo_px": escala["residuo_px"],
        "razao_mediana": escala["razao_mediana"],
        "razao_teorica": 2 ** (-1 / 12),
        "trastes_casados": escala["casados"],
        "deriva_camera": deriva,
    }
    args.pasta.mkdir(parents=True, exist_ok=True)
    (args.pasta / "braco.json").write_text(
        json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    cv2.imwrite(str(args.pasta / "braco.jpg"), desenhar(calib["mediana"], calib))

    print("| corda | a | b | rms | pontos | brilho |")
    print("|---|---|---|---|---|---|")
    for c in registro["cordas"]:
        print(
            f"| {c['corda']} | {c['a']:.1f} | {c['b']:.4f} | {c['rms']:.2f} | "
            f"{c['n']} | {c['brilho']:.0f} |"
        )
    print(
        f"nut x={registro['nut_x']:.1f}, L={registro['L_px']:.1f} px, "
        f"casados {registro['trastes_casados']}/14, resíduo "
        f"{registro['residuo_px']:.2f} px, razão mediana "
        f"{registro['razao_mediana']:.4f} (teórica {registro['razao_teorica']:.4f})"
    )
    print(f"deriva da câmera: {deriva}")
    print(f"JSON: {args.pasta / 'braco.json'}")


if __name__ == "__main__":
    main()

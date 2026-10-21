"""Rodada 2018: material das 4 telas de acorde cheio para ``tab.ouro_video servir``.

Mesmo caminho do ``data/saida/t82/material_ferramenta.py`` (trilha tablatura): cada tela
vira uma "tela" da ferramenta, com as notas do produto (leitor ``rede``) pré-carregadas,
todas ``conferida: false``. Sem instantes: aqui só se confere corda e casa. O dono escolheu
as 4 telas em 2026-10-21. A ferramenta grava o arquivo de ouro quando o dono clica; este
script não grava nada em ``data/gold/``.

Uso (container base): python data/saida/audio/r2018/material_acordes.py
"""

import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ))
from tab.ouro_video import ESCALA_TELA  # noqa: E402

R2018 = RAIZ / "data" / "saida" / "audio" / "r2018"
PROD = RAIZ / "data" / "saida" / "audio" / "r2017" / "produtos"
SAIDA = R2018 / "ferramenta_acordes"
ESCOLHIDAS = [
    ("paolo_those_who_wait", 4),
    ("robert_lunn_5_beautiful_easy", 5),
    ("transcriptor_charagua", 6),
    ("guitarous_sakura", 5),
]


def linhas_da_tab(cinza: np.ndarray, passo: float) -> list[float]:
    """Acha as 6 linhas da tablatura: o grupo mais baixo de 6 linhas com o passo dado.

    Args:
        cinza: recorte do painel em cinza.
        passo: distância esperada entre cordas, em px.

    Returns:
        O y de cada corda (1 a 6) no recorte.
    """
    # linha da tab = linha de pixels cuja mediana fica bem abaixo da vizinhança (±4 px);
    # vale para linha preta cheia e para linha cinza clara (sakura)
    med = np.median(cinza, axis=1).astype(float)
    viz = np.array([med[max(0, y - 4) : y + 5].max() for y in range(len(med))])
    cand = [y for y in range(1, len(med) - 1) if viz[y] - med[y] > 20]
    linhas: list[list[int]] = []
    for y in cand:
        if linhas and y - linhas[-1][-1] <= 2:
            linhas[-1].append(y)
        else:
            linhas.append([y])
    ys = [float(np.mean(g)) for g in linhas]
    melhor = None
    for i in range(len(ys)):
        grupo = [ys[i]]
        for y in ys[i + 1 :]:
            if abs(y - grupo[-1] - passo) <= 0.25 * passo:
                grupo.append(y)
            if len(grupo) == 6:
                break
        if len(grupo) == 6:
            melhor = grupo
    if melhor is None:
        raise RuntimeError(f"6 linhas não achadas (passo {passo}); linhas: {ys}")
    return melhor


def main() -> None:
    """Grava ``telas/NNN.png``, ``pre.json`` e ``indice.json`` em ``SAIDA``."""
    (SAIDA / "telas").mkdir(parents=True, exist_ok=True)
    pre_telas, estado_telas, indice = [], [], []
    for k, (nome, tela_id) in enumerate(ESCOLHIDAS, start=1):
        d = json.loads((PROD / f"{nome}.json").read_text(encoding="utf-8"))
        video = d["video"]["arquivo"]
        tela = next(t for t in d["telas"] if t["id"] == tela_id)
        ex = tela["exibicoes"][0]
        t = round(ex["t0"] + 0.3 * (ex["t1"] - ex["t0"]), 3)
        png = SAIDA / f"quadro_{k:03d}.png"
        subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i",
             f"/acervo/{video}", "-frames:v", "1", str(png)],
            check=True,
        )
        quadro = cv2.imread(str(png))
        passo = float(tela["passo"])
        px0, py0, px1, py1 = tela["painel"]
        cinza = cv2.cvtColor(quadro[py0:py1, px0:px1], cv2.COLOR_BGR2GRAY)
        ly = [py0 + y for y in linhas_da_tab(cinza, passo)]
        y0 = max(0, int(ly[0] - 2.5 * passo))
        y1 = min(quadro.shape[0], int(ly[5] + 2.5 * passo))
        x0, x1 = px0, px1
        cv2.imwrite(
            str(SAIDA / f"telas/{k:03d}.png"),
            cv2.resize(quadro[y0:y1, x0:x1], None, fx=ESCALA_TELA, fy=ESCALA_TELA,
                       interpolation=cv2.INTER_CUBIC),
        )
        notas = []
        for n in d["notas"]:
            if n["tela"] != tela_id:
                continue
            x, y = n["x_centro_quadro"], ly[n["corda"] - 1]
            notas.append(
                {
                    "corda": n["corda"],
                    "casa": str(n["casa"]),
                    "x_quadro": round(x - 0.3 * passo, 1),
                    "x_centro_quadro": x,
                    "caixa": [round(x - 0.3 * passo, 1), round(y - 0.42 * passo, 1),
                              round(x + 0.3 * passo, 1), round(y + 0.42 * passo, 1)],
                    "confianca": n["confianca"],
                }
            )
        pre_telas.append(
            {
                "id": k, "arquivo": f"telas/{k:03d}.png", "quadro_ref_s": t,
                "t_ini": t, "t_fim": t, "exibicoes": [[t, t]], "modo": "paginado",
                "painel": [x0, y0, x1, y1], "escala": ESCALA_TELA, "passo": passo,
                "linhas_y": ly, "notas": notas, "nao_nota": [],
            }
        )
        estado_telas.append(
            {
                "id": k, "conferida": False, "junta_em": None,
                "origem": "rede — a conferir", "v1_telas": [],
                "notas": [
                    {"id": f"m{i}", "corda": n["corda"], "casa": n["casa"],
                     "x_quadro": n["x_quadro"], "x_centro_quadro": n["x_centro_quadro"],
                     "origem": "modelo", "removida": False, "caixa": n["caixa"]}
                    for i, n in enumerate(notas)
                ],
            }
        )
        indice.append({"id": k, "produto": nome, "tela_produto": tela_id,
                       "video": video, "t": t})
        print(k, nome, tela_id, t, len(notas), "notas; linhas", [round(v) for v in ly])
    pre = {
        "video": "rodada 2018 (áudio): 4 telas de acorde cheio de 4 vídeos (ver indice.json)",
        "modelo": "artefatos/detector_tab_final_s1_ger (leitor rede, produtos da 2017)",
        "preparado_em": "2026-10-21", "duracao_s": 0.0, "codec": "",
        "segmentacao": "produto chorinho/video@1",
        "como_foi_rotulado": (
            "Rodada 2018 (áudio): uma tela por vídeo, escolhida pelo dono por ter acorde "
            "de 5-6 notas. Notas pré-lidas pela rede; o dono confere corda e casa. Sem "
            "instantes."
        ),
        "telas": pre_telas, "instantes": [],
        "estado_inicial": {"proximo": 1, "tela_atual": 1, "inst_atual": 0,
                           "telas": estado_telas, "instantes": []},
        "fusao": {"sem_v1": True, "n_instantes": 0},
    }
    (SAIDA / "pre.json").write_text(json.dumps(pre, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
    (SAIDA / "indice.json").write_text(json.dumps(indice, ensure_ascii=False, indent=1),
                                       encoding="utf-8")


if __name__ == "__main__":
    main()

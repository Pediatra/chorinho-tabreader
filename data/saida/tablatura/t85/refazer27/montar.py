"""Refaz a tela 27 da T8.5 com o recorte certo, para o dono conferir de novo.

O painel achado (y 406–584) cortou a corda 6 e a grade pôs a corda 1 na borda de cima:
as cordas ficaram deslocadas de uma. Aqui o recorte vai de y 440 a 612 e as cordas
vêm do perfil de tinta, medidas no quadro limpo (sem o retângulo verde). A rede do
produto relê as notas com essa grade. Grava uma ferramenta de uma tela só em
``data/saida/tablatura/t85/refazer27/ferramenta/``.

Uso (container): python data/saida/tablatura/t85/refazer27/montar.py
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(RAIZ))
from tab.comum import caminhos, leitor  # noqa: E402
from tab.tablatura.leitura import detector_tab  # noqa: E402
from tab.tablatura.ouro.ouro_video import ESCALA_TELA  # noqa: E402

AQUI = Path(__file__).resolve().parent
SAIDA = AQUI / "ferramenta"
VIDEO = "transcriptor/retrato brasileño - baden powell - tablatura ⧸ partitura.mp4"
T = 133.04
Y0, Y1 = 440, 612


def linhas_da_tab(roi: np.ndarray) -> list[float]:
    """Acha as 6 cordas pelo perfil horizontal de tinta escura.

    Args:
        roi: recorte BGR do painel.

    Returns:
        y de cada corda no recorte, da 1 à 6.
    """
    cinza = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    perfil = (cinza < 120).mean(axis=1)
    picos = [
        y
        for y in range(1, len(perfil) - 1)
        if perfil[y] > 0.5 and perfil[y] >= perfil[y - 1] and perfil[y] > perfil[y + 1]
    ]
    grupos: list[list[int]] = []
    for y in picos:
        if grupos and y - grupos[-1][-1] <= 3:
            grupos[-1].append(y)
        else:
            grupos.append([y])
    return [float(np.mean(g)) for g in grupos]


def main() -> None:
    """Grava ``ferramenta/telas/001.png``, ``pre.json`` e ``indice.json``."""
    quadro = leitor.quadro_em(str(caminhos.acervo() / VIDEO), T)
    roi = quadro[Y0:Y1]
    ly = linhas_da_tab(roi)
    print("linhas no recorte:", [round(y, 1) for y in ly])
    assert len(ly) == 6, ly
    passo = float(np.mean(np.diff(ly)))
    modelo = detector_tab.carregar(caminhos.DETECTOR_PADRAO)
    det = detector_tab.detectar(modelo, roi, ly, passo)
    lyq = [round(Y0 + y, 1) for y in ly]
    notas = []
    for i, d in enumerate(sorted(det, key=lambda d: (d["x"], d["corda"]))):
        x, y = float(d["x"]), lyq[int(d["corda"]) - 1]
        notas.append(
            {
                "id": f"m{i}",
                "corda": int(d["corda"]),
                "casa": str(d["rotulo"]),
                "x_quadro": round(x - 0.3 * passo, 1),
                "x_centro_quadro": round(x, 1),
                "origem": "modelo",
                "removida": False,
                "caixa": [
                    round(x - 0.3 * passo, 1),
                    round(y - 0.42 * passo, 1),
                    round(x + 0.3 * passo, 1),
                    round(y + 0.42 * passo, 1),
                ],
            }
        )
    (SAIDA / "telas").mkdir(parents=True, exist_ok=True)
    x1 = quadro.shape[1]
    cv2.imwrite(
        str(SAIDA / "telas" / "001.png"),
        cv2.resize(roi, None, fx=ESCALA_TELA, fy=ESCALA_TELA, interpolation=cv2.INTER_CUBIC),
    )
    estado = {
        "id": 1,
        "conferida": False,
        "junta_em": None,
        "origem": "rede — a conferir (tela 27 da T8.5, recorte refeito)",
        "v1_telas": [],
        "notas": notas,
    }
    pre = {
        "video": "t85, tela 27 refeita: " + VIDEO,
        "modelo": str(caminhos.DETECTOR_PADRAO),
        "preparado_em": "",
        "duracao_s": 0.0,
        "codec": "",
        "segmentacao": "t85_refazer27",
        "como_foi_rotulado": "Tela 27 da T8.5 com o recorte refeito (corda 6 estava cortada).",
        "telas": [
            {
                "id": 1,
                "arquivo": "telas/001.png",
                "quadro_ref_s": T,
                "t_ini": T,
                "t_fim": T,
                "exibicoes": [[T, T]],
                "modo": "paginado",
                "painel": [0, Y0, x1, Y1],
                "escala": ESCALA_TELA,
                "passo": round(passo, 2),
                "linhas_y": lyq,
                "notas": [
                    {k: n[k] for k in ("corda", "casa", "x_quadro", "x_centro_quadro", "caixa")}
                    for n in notas
                ],
                "nao_nota": [],
            }
        ],
        "instantes": [],
        "estado_inicial": {
            "proximo": 1, "tela_atual": 1, "inst_atual": 0, "telas": [estado], "instantes": [],
        },
        "fusao": {"sem_v1": True, "n_instantes": 0},
    }
    (SAIDA / "pre.json").write_text(json.dumps(pre, ensure_ascii=False, indent=1), "utf-8")
    (SAIDA / "indice.json").write_text(
        json.dumps([{"id": 1, "t85_id": 27, "video": VIDEO, "t": T}], ensure_ascii=False),
        "utf-8",
    )
    print(len(notas), "notas;", [(n["corda"], n["casa"], n["x_centro_quadro"]) for n in notas])


if __name__ == "__main__":
    main()
